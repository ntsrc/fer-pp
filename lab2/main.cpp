#include <cstddef>
#include "connect4.h"

constexpr ssize_t full_depth = 8;
constexpr ssize_t task_depth = 6;

constexpr ssize_t height = 7;
constexpr ssize_t width = 7;

int main(int argc, char **argv)
{
	connect4::run<height, width, full_depth, task_depth>();
}
