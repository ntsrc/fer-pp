from mpi4py import MPI
from enum import IntEnum, auto

comm  = MPI.COMM_WORLD
myRank = comm.Get_rank()
numWorkers = comm.Get_size() - 1

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

def make_tasks_rec(board, player, col, task, tasks, depth, task_depth):
    if board.win(player, col):
        return

    task.append(col)

    if depth == task_depth:
        tasks.append(task)
        return

    next_player = other_player(player)

    for c in range(board.width):
        if board.legal_move(c):
            board.move(next_player, c)
            make_tasks_rec(board, next_player, c, task.copy(), tasks, depth - 1, task_depth)
            board.undo_move(c)

def make_tasks(board, player, full_depth, task_depth):
    tasks = []

    for c in range(board.width):
        if board.legal_move(c):
            board.move(player, c)
            make_tasks_rec(board, player, c, [], tasks, full_depth - 1, task_depth)
            board.undo_move(c)

    return tasks

task_grades = dict()

def move_grade(board, player, col, task, depth, task_depth):
    if board.win(player, col):
        return 1.0 if player == 'C' else -1.0

    task.append(col)

    if depth == task_depth:
        return task_grades[tuple(task)]

    if depth == 0:
        return 0.0

    next_player = other_player(player)
    sum = 0.0
    num_moves = 0
    all_win, all_lose = True, True

    for c in range(board.width):
        if board.legal_move(c):
            num_moves += 1
            board.move(next_player, c)
            res = move_grade(board, next_player, c, task.copy(), depth - 1, task_depth)
            board.undo_move(c)

            if res != -1.0:
                all_lose = False
            if res != 1.0:
                all_win = False
            if res == 1.0 and next_player == 'C':
                return 1.0
            if res == -1.0 and next_player == 'P':
                return -1.0

            sum += res

    if all_win:
        return 1.0

    if all_lose:
        return -1.0

    return sum / num_moves

class Tag(IntEnum):
    TASK_REQUEST = auto()
    TASK_GRADE = auto()
    TASK = auto()
    NO_MORE_TASKS = auto()

def move_grades(board, player, full_depth, task_depth):
    tasks = make_tasks(board, player, full_depth, task_depth)
    tasks_left = len(tasks)

    while True:
        status = MPI.Status()
        if comm.Iprobe(status = status):
            rank = status.Get_source()
            tag = status.Get_tag()
            if tag == Tag.TASK_GRADE:
                (task, grade) = comm.recv(source = rank, tag = tag)
                task_grades[tuple(task)] = grade
                tasks_left -= 1

                if not tasks_left:
                    break

            elif tag == Tag.TASK_REQUEST:
                comm.recv(source = rank, tag = tag)
            if tasks:
                task = tasks.pop()
                comm.send((board, player, task), dest = rank, tag = Tag.TASK)

    for rank in range(1, numWorkers + 1):
        comm.send([], dest = rank, tag = Tag.NO_MORE_TASKS)

    grades = [-2.0] * board.width

    for c in range(board.width):
        if board.legal_move(c):
            board.move(player, c)
            grades[c] = move_grade(board, player, c, [], full_depth - 1, task_depth)
            board.undo_move(c)

    task_grades.clear()

    return grades;

if myRank == 0:
    board = Board(7, 7)
    print(board)

while True:
    if myRank == 0:
        col = int(input())
        board.move('P', col)
        print(board, flush = True)
        grades = move_grades(board, 'C', FULL_DEPTH, TASK_DEPTH)
        print(' '.join('-' if grade < -1.0 else str(grade) for grade in grades), flush = True)
        move = max(zip(grades, range(len(grades))))[1]
        board.move('C', move)
        print(board)
    else:
        comm.send([], dest = 0, tag = Tag.TASK_REQUEST)
        status = MPI.Status()
        if comm.Iprobe(status = status, source = 0):
            tag = status.Get_tag()
            if tag == Tag.TASK:
                board, player, task = comm.recv(source = 0, tag = tag)
                print(task, flush = True)
                while True:
                    for move in task:
                        board.move(player, move)
                        player = other_player(player)

                    grade = move_grade(board, player, move, [], TASK_DEPTH - 1, TASK_DEPTH)

                    comm.send((task, grade), dest = 0, tag = Tag.TASK_GRADE)
                    if comm.Iprobe(status = status, source = 0):
                        tag = status.Get_tag()
                        if tag == Tag.NO_MORE_TASKS:
                            comm.recv(source = 0, tag = tag)
                            break
                        else:
                            board, player, task = comm.recv(source = 0, tag = tag)
            else:
                comm.recv(source = 0, tag = tag)
