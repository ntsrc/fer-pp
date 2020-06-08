#ifndef CONNECT4_BOARD_H
#define CONNECT4_BOARD_H

#include <cstddef>
#include <array>
#include <ostream>
#include <vector>

namespace connect4
{

enum player : char
{
	cpu = 'C', human = 'P', none = '='
};

inline player other_player(player p)
{
	return p == cpu ? human : (p == human ? cpu : none);
}

template<ssize_t height, ssize_t width>
struct board
{
	board();

	char at(ssize_t row, ssize_t col) const { return data_[row * width + col]; }

	void move(player p, ssize_t col) { at(++top_row_[col], col) = p; }
	void undo_move(ssize_t col) { at(top_row_[col]--, col) = none; }

	static bool legal_position(ssize_t row, ssize_t col) { return row >= 0 && row < height && col >= 0 && col < width; }

	bool legal_move(ssize_t col) { return top_row_[col] < height - 1; }

	bool win(player p, ssize_t col) const { return vertical_win(p, col) || horizontal_win(p, col) || diagonal_win(p, col); }

	bool vertical_win(player p, ssize_t col) const;
	bool horizontal_win(player p, ssize_t col) const;
	bool diagonal_win(player p, ssize_t col) const;

	static constexpr ssize_t to_win = 4;

	std::array<char, height*width> data_;
	std::array<ssize_t, width> top_row_;

	char &at(ssize_t row, ssize_t col) { return data_[row * width + col]; }
};

template<ssize_t height, ssize_t width>
inline board<height, width>::board()
{
	data_.fill(none);
	top_row_.fill(-1);
}

template<ssize_t height, ssize_t width>
inline bool board<height, width>::vertical_win(player p, ssize_t col) const
{
	auto row = top_row_[col];

	for (auto i = 1; i < to_win; ++i)
	{
		auto row_idx = row - i;
		if (row_idx < 0 || at(row_idx, col) != p)
			return false;
	}

	return true;
}

template<ssize_t height, ssize_t width>
inline bool board<height, width>::horizontal_win(player p, ssize_t col) const
{
	auto row = top_row_[col];

	auto n = 1;
	for (auto dir = -1; dir <= 1; dir += 2)
	{
		for (auto i = 1; i < to_win; ++i)
		{
			auto col_idx = col + dir * i;
			if (col_idx < 0 || col_idx >= width || at(row, col_idx) != p)
				break;
			++n;
		}
	}

	return n >= to_win;
}

template<ssize_t height, ssize_t width>
inline bool board<height, width>::diagonal_win(player p, ssize_t col) const
{
	auto row = top_row_[col];

	auto n = 1;
	for (auto dir = -1; dir <= 1; dir += 2)
	{
		for (auto i = 1; i < to_win; ++i)
		{
			auto row_idx = row + dir * i;
			auto col_idx = col + dir * i;
			if (!legal_position(row_idx, col_idx) || at(row_idx, col_idx) != p)
				break;
			++n;
		}
	}

	if (n >= to_win)
		return true;

	n = 1;
	for (auto dir = -1; dir <= 1; dir += 2)
	{
		for (auto i = 1; i < to_win; ++i)
		{
			auto row_idx = row - dir * i;
			auto col_idx = col + dir * i;
			if (!legal_position(row_idx, col_idx) || at(row_idx, col_idx) != p)
				break;
			++n;
		}
	}

	return n >= to_win;
}

template<ssize_t height, ssize_t width>
inline std::ostream &operator<<(std::ostream &os, const board<height, width> &b)
{
	for (auto r = height - 1; r >= 0; --r)
	{
		for (auto c = 0; c < width; ++c)
			os << b.at(r, c);
		os << '\n';
	}

	return os;
}

}

#endif
