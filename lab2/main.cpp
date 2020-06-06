#include "board.h"
#include <iostream>
#include <cstddef>

constexpr ssize_t height = 7;
constexpr ssize_t width = 7;

int main()
{
	connect4::board<width, height> b;
	auto player = connect4::human;

	for (ssize_t col; std::cin >> col; )
	{
		b.move(player, col);
		std::cout << b << b.vertical_win(player, col) << ' ' << b.horizontal_win(player, col) << ' ' << b.diagonal_win(player, col) << '\n';
		player = connect4::other_player(player);
	}
}
