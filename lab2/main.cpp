#include "board.h"
#include <iostream>
#include <cstddef>

constexpr char human = 'P';
constexpr char comp = 'C';

int main()
{
	board<7, 7> b;

	while (true)
	{
		size_t col;
		std::cin >> col;

		b.move(col, human);

		std::cout << b;
	}
}
