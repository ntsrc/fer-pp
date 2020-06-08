#include <cstddef>
#include <mpi.h>
#include "board.h"
#include <iostream>
#include <array>
#include <algorithm>
#include <vector>
#include <map>
#include <cstring>

namespace connect4
{

template<ssize_t height, ssize_t width, ssize_t depth, ssize_t task_depth>
struct tasks
{
	static void make(board<height, width> b, player p, ssize_t col, std::vector<ssize_t> path, std::vector<std::vector<ssize_t>> &paths);
};

template<ssize_t height, ssize_t width, ssize_t depth, ssize_t task_depth>
inline void tasks<height, width, depth, task_depth>::make(board<height, width> b, player p, ssize_t col, std::vector<ssize_t> path, std::vector<std::vector<ssize_t>> &paths)
{
	if (b.win(p, col))
		return;

	path.push_back(col);
	
	auto next_player = other_player(p);

	for (auto c = 0; c < width; ++c)
	{
		if (b.legal_move(c))
		{
			b.move(next_player, c);
			tasks<height, width, depth - 1, task_depth>::make(b, next_player, c, path, paths);
			b.undo_move(c);
		}
	}
}

template<ssize_t height, ssize_t width, ssize_t task_depth>
struct tasks<height, width, task_depth, task_depth>
{
	static void make(board<height, width> b, player p, ssize_t col, std::vector<ssize_t> path, std::vector<std::vector<ssize_t>> &paths);
};


template<ssize_t height, ssize_t width, ssize_t task_depth>
inline void tasks<height, width, task_depth, task_depth>::make(board<height, width> b, player p, ssize_t col, std::vector<ssize_t> path, std::vector<std::vector<ssize_t>> &paths)
{
	path.push_back(col);
	paths.push_back(path);
}

template<ssize_t height, ssize_t width, ssize_t depth, ssize_t task_depth>
inline std::vector<std::vector<ssize_t>> make_tasks(board<height, width> b, player p)
{
	std::vector<std::vector<ssize_t>> paths;

	for (auto c = 0; c < width; ++c)
	{
		if (b.legal_move(c))
		{
			b.move(p, c);
			tasks<height, width, depth - 1, task_depth>::make(b, p, c, {}, paths);
			b.undo_move(c);
		}
	}

	return paths;
}

template<ssize_t height, ssize_t width, ssize_t depth, ssize_t task_depth>
struct move_grade
{
	static double get(board<height, width> b, player p, ssize_t col, std::vector<ssize_t> path);
};

template<ssize_t height, ssize_t width, ssize_t depth, ssize_t task_depth>
inline double move_grade<height, width, depth, task_depth>::get(board<height, width> b, player p, ssize_t col, std::vector<ssize_t> path)
{
	if (b.win(p, col))
		return p == cpu ? 1.0 : -1.0;

	auto next_player = other_player(p);
	auto sum = 0.0;
	auto num_moves = 0;
	auto all_win = true, all_lose = false;

	path.push_back(col);

	for (auto c = 0; c < width; ++c)
	{
		if (b.legal_move(c))
		{
			++num_moves;
			b.move(next_player, c);
			double res = move_grade<height, width, depth - 1, task_depth>::get(b, next_player, c, path);
			b.undo_move(c);

			if (res > -1.0)
				all_lose = false;
			if (res != 1.0)
				all_win = false;
			if (res == 1.0 && next_player == cpu)
				return 1.0;
			if (res == -1.0 && next_player == human)
				return -1.0;

			sum += res;
		}
	}

	if (all_win)
		return 1.0;

	if (all_lose)
		return -1.0;

	return sum / num_moves;
}

std::map<std::vector<ssize_t>, double> task_grades;

template<ssize_t height, ssize_t width, ssize_t task_depth>
struct move_grade<height, width, task_depth, task_depth>
{
	static double get(board<height, width> b, player p, ssize_t col, std::vector<ssize_t> path) { path.push_back(col); return task_grades[path]; }
};

template<ssize_t height, ssize_t width, ssize_t task_depth>
struct move_grade<height, width, 0, task_depth>
{
	static double get(board<height, width> b, player p, ssize_t col, std::vector<ssize_t> path) { return 0.0; }
};

enum tag : int
{
	TASK, STOP
};

template<ssize_t height, size_t width>
inline void send_task(int rank, const board<height, width> &b, const std::vector<ssize_t> &path)
{
	auto board_data_sz = height * width;
	auto board_top_sz = width * sizeof(ssize_t);
	auto path_sz = path.size() * sizeof(ssize_t);
	std::vector<char> msg(board_data_sz + board_top_sz + path_sz);
	std::memcpy(msg.data(), b.data_.data(), board_data_sz);
	std::memcpy(msg.data() + board_data_sz, b.top_row_.data(), board_top_sz);
	std::memcpy(msg.data() + board_data_sz + board_top_sz, path.data(), path_sz);

	MPI_Send();
}

template<ssize_t height, ssize_t width, ssize_t full_depth, ssize_t task_depth>
inline std::array<double, width> move_grades(board<height, width> b, player p)
{
	std::array<double, width> grades;
	grades.fill(-2.0);

	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);

	int num_procs;
	MPI_Comm_size(MPI_COMM_WORLD, &num_procs);


	if (rank == 0)
	{
		auto num_workers = num_procs - 1;

		auto tasks = make_tasks<height, width, full_depth, task_depth>(b, p);

		while (!tasks.empty())
		{
			auto path = tasks.back();
			tasks.pop_back();
			int worker = 1 + tasks.size() % num_workers;


			send_task(worker, const board &b, task);
			std::vector<char> msg(height*width + width*sizeof(ssize_t));
			std::memcpy(msg.data(), b.data_.data(), height*width);
			std::memcpy(msg.data() + height*width, static_cast<char*>(b.top_.data()), width*sizeof(ssize_t));

			
		}

		for (auto c = 0; c < width; ++c)
		{
			if (b.legal_move(c))
			{
				b.move(p, c);
				grades[c] = move_grade<height, width, full_depth - 1, task_depth>::get(b, p, c, {});
				b.undo_move(c);
			}
		}
	}

	return grades;
}

template<ssize_t height, ssize_t width, ssize_t full_depth, ssize_t task_depth>
inline void run()
{
	MPI_Init(nullptr, nullptr);

	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);

	if (rank == 0)
	{
		board<height, width> b;
		std::cout << b;

		for (ssize_t col; std::cin >> col; )
		{
			b.move(human, col);
			std::cout << b;

			auto grades = move_grades<height, width, full_depth, task_depth>(b, cpu);
			std::for_each(grades.cbegin(), grades.cend(), [](auto g){ std::cout << (g < -1.0 ? '-' : g) << ' '; });
			auto best_move = std::distance(grades.cbegin(), std::max_element(grades.cbegin(), grades.cend()));
			b.move(cpu, best_move);
			std::cout << '\n' << b;
		}
	}

	MPI_Finalize();
}

}
