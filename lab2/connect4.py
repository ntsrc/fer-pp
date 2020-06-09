from mpi4py import MPI

comm  = MPI.COMM_WORLD
rank = comm.Get_rank()

class Board:
    def __init__(self, height, width):
        self.height = height
        self.width = width
        self.data = [list('=' * width) for r in range(height)]
        self.top_row = [-1] * width

    def __str__(self):
        return '\n'.join([''.join(self.data[r]) for r in range(self.height - 1, -1, -1)])

    def legal_move(self, col):
        return self.top_row[col] < self.height - 1

    def legal_position(self, row, col):
        return row >= 0 and row < self.height and col >= 0 and col < self.width

    def move(self, player, col):
        self.top_row[col] += 1
        self.data[self.top_row[col]][col] = player

    def undo_move(self, col):
        self.data[self.top_row[col]][col] = '='
        self.top_row[col] -= 1

    def vertical_win(self, player, col):
        row = self.top_row[col]

        for i in range(1, 4):
            row_idx = row - i
            if row_idx < 0 or self.data[row_idx][col] != player:
                return False

        return True

    def horizontal_win(self, player, col):
        row = self.top_row[col]
        n = 1

        for dir in [-1, 1]:
            for i in range(1, 4):
                col_idx = col + dir * i
                if col_idx < 0 or col_idx >= self.width or self.data[row][col_idx] != player:
                    break
                n += 1

        return n >= 4

    def diagonal_win(self, player, col):
        row = self.top_row[col]
        n = 1

        for dir in [-1, 1]:
            for i in range(1, 4):
                row_idx = row + dir * i
                col_idx = col + dir * i
                if not self.legal_position(row_idx, col_idx) or self.data[row_idx][col_idx] != player:
                    break
                n += 1

        if n >= 4:
            return True

        n = 1

        for dir in [-1, 1]:
            for i in range(1, 4):
                row_idx = row - dir * i
                col_idx = col + dir * i
                if not self.legal_position(row_idx, col_idx) or self.data[row_idx][col_idx] != player:
                    break
                n += 1

        return n >= 4

    def win(self, player, col):
        return self.vertical_win(player, col) or self.horizontal_win(player, col) or self.diagonal_win(player, col)

def other_player(player):
    return 'C' if player == 'P' else 'P'

TASK_DEPTH = 6
FULL_DEPTH = 8

def make_tasks(board, player, col, task, tasks, depth):
    if board.win(player, col):
        return

    task.append(col)

    if depth == TASK_DEPTH:
        tasks.append(task)
        return

    next_player = other_player(player)

    for c in range(board.width):
        if board.legal_move(c):
            board.move(next_player, c)
            make_tasks(board, next_player, c, task.copy(), tasks, depth - 1)
            board.undo_move(c)

def get_tasks(board, player):
    tasks = []

    for c in range(board.width):
        if board.legal_move(c):
            board.move(player, c)
            make_tasks(board, player, c, [], tasks, FULL_DEPTH - 1)
            board.undo_move(c)

    return tasks

def move_grade()

if rank == 0:
    board = Board(7,7)
    tasks = get_tasks(board, 'C')
    print(tasks)
