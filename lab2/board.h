#ifndef BOARD_H
#define BOARD_H

#include <cstddef>
#include <array>
#include <ostream>

template<size_t rows, size_t cols>
class board
{
public:
	board() { b_.fill('='); top_.fill(0); }

	void move(size_t col, char player) { b_[top_[col] * rows + col] = player; ++top_[col]; }
	void undo(size_t col) { --top_[col]; b_[top_[col] * rows + col] = '='; }

	char at(size_t r, size_t c) const { return b_[r * cols + c]; }

	bool vertical_win(char player, size_t col) const;
	bool horizontal_win(char player, size_t col) const;
	bool diagonal_win(char player, size_t col) const;

	bool win(char player, size_t col) const { return vertical_win(player, col) || horizontal_win(player, col) || diagonal_win(player, col); }
	
	std::array<double, cols> move_grades();

private:
	std::array<char, rows*cols> b_;
	std::array<size_t, cols> top_;
};

template<size_t rows, size_t cols>
inline bool board<rows, cols>::vertical_win(char player, size_t col) const
{
	auto row = top_[col];
	auto down = 0u;
	while (down < 3u)
	{
		auto idx = row - down - 1;
		if (at(idx, col) != player)
			break;
		++down;
		if (idx == 0u)
			break;
	}

	return down == 3u;
}

template<size_t rows, size_t cols>
inline bool board<rows, cols>::horizontal_win(char player, size_t col) const
{
	auto row = top_[col];
	auto left = 0u;
	while (left < 3u)
	{
		auto idx = col - left - 1;
		if (at(row, idx) != player)
			break;
		++left;
		if (idx == 0u)
			break;
	}

	auto right = 0u;
	while (right < 3u)
	{
		auto idx = col + right + 1;
		if (idx == cols || at(row, idx) != player)
			break;
		++right;
	}

	return left + right >= 3u;
}

template<size_t rows, size_t cols>
inline bool board<rows, cols>::diagonal_win(char player, size_t col) const
{
	auto row = top_[col];
	auto upleft = 0u;
	while (upleft < 3u)
	{
		auto row_idx = row + upleft + 1;
		auto col_idx = col - upleft - 1;
		if (at(row_idx, col_idx) != player)
			break;
		++upleft;
		if (row_idx == rows || col_idx == 0u)
			break;
	}

	auto downright = 0u;
	while (downright < 3u)
	{
		auto row_idx = row - downright - 1;
		auto col_idx = col + downright + 1;
		if (at(row_idx, col_idx) != player)
			break;
		++downright;
		if (row_idx == 0u || col_idx == cols)
			break;
	}

	if (upleft + downright >= 3u)
		return true;

	auto upright = 0u;
	while (upright < 3u)
	{
		auto row_idx = row + upright + 1;
		auto col_idx = col + upleft + 1;
		if (at(row_idx, col_idx) != player)
			break;
		++upright;
		if (row_idx == rows || col_idx == cols)
			break;
	}

	auto downleft = 0u;
	while (downleft < 3u)
	{
		auto row_idx = row - downleft - 1;
		auto col_idx = col - downleft - 1;
		if (at(row_idx, col_idx) != player)
			break;
		++downleft;
		if (row_idx == 0u || col_idx == 0u)
			break;
	}

	return upright + downleft >= 3u;
}

template<size_t rows, size_t cols>
inline std::ostream &operator<<(std::ostream &os, const board<rows, cols> &b)
{
	for (auto i = rows; i > 0u; --i)
	{
		for (auto j = 0u; j < cols; ++j)
			os << b.at(i - 1u, j);
		os << '\n';
	}

	return os;
}

#endif
