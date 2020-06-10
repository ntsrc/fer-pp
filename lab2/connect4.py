from mpi4py import MPI
from enum import Enum, IntEnum, auto
import sys
import time
import signal

comm  = MPI.COMM_WORLD
myRank = comm.Get_rank()
numWorkers = comm.Get_size() - 1

TASK_DEPTH = 6
FULL_DEPTH = 8

HEIGHT = 7
WIDTH = 7

class Player(Enum):
    CPU = 'C'
    HUMAN = 'P'
    NONE = '='

def otherPlayer(player):
    return Player.CPU if player == Player.HUMAN else (Player.HUMAN if player == Player.CPU else Player.NONE)

class Board:
    def __init__(self, height, width):
        self.height = height
        self.width = width
        self.data = [[Player.NONE] * width for r in range(height)]
        self.topRow = [-1] * width
        self.TO_WIN = 4

    def __str__(self):
        return '\n'.join([''.join(row[c].value for c in range(self.width)) for row in reversed(self.data)])

    def legalMove(self, col):
        return self.topRow[col] < self.height - 1

    def legalPosition(self, row, col):
        return row >= 0 and row < self.height and col >= 0 and col < self.width

    def move(self, player, col):
        self.topRow[col] += 1
        self.data[self.topRow[col]][col] = player

    def undoMove(self, col):
        self.data[self.topRow[col]][col] = Player.NONE
        self.topRow[col] -= 1

    def verticalWin(self, player, col):
        row = self.topRow[col]

        for i in range(1, self.TO_WIN):
            rowIdx = row - i
            if rowIdx < 0 or self.data[rowIdx][col] != player:
                return False

        return True

    def horizontalWin(self, player, col):
        row = self.topRow[col]
        n = 1

        for dir in [-1, 1]:
            for i in range(1, self.TO_WIN):
                colIdx = col + dir * i
                if colIdx < 0 or colIdx >= self.width or self.data[row][colIdx] != player:
                    break
                n += 1

        return n >= self.TO_WIN

    def diagonalWin(self, player, col):
        row = self.topRow[col]
        n = 1

        for dir in [-1, 1]:
            for i in range(1, self.TO_WIN):
                rowIdx = row + dir * i
                colIdx = col + dir * i
                if not self.legalPosition(rowIdx, colIdx) or self.data[rowIdx][colIdx] != player:
                    break
                n += 1

        if n >= self.TO_WIN:
            return True

        n = 1

        for dir in [-1, 1]:
            for i in range(1, self.TO_WIN):
                rowIdx = row - dir * i
                colIdx = col + dir * i
                if not self.legalPosition(rowIdx, colIdx) or self.data[rowIdx][colIdx] != player:
                    break
                n += 1

        return n >= self.TO_WIN

    def win(self, player, col):
        return self.verticalWin(player, col) or self.horizontalWin(player, col) or self.diagonalWin(player, col)



def makeTasksRec(board, player, col, task, tasks, depth, taskDepth):
    if board.win(player, col):
        return

    task.append(col)

    if depth == taskDepth:
        tasks.append(task)
        return

    next_player = otherPlayer(player)

    for c in range(board.width):
        if board.legalMove(c):
            board.move(next_player, c)
            makeTasksRec(board, next_player, c, task.copy(), tasks, depth - 1, taskDepth)
            board.undoMove(c)

def makeTasks(board, player, fullDepth, taskDepth):
    tasks = []

    for c in range(board.width):
        if board.legalMove(c):
            board.move(player, c)
            makeTasksRec(board, player, c, [], tasks, fullDepth - 1, taskDepth)
            board.undoMove(c)

    return tasks

taskGrades = dict()

def moveGrade(board, player, col, task, depth, taskDepth):
    if board.win(player, col):
        return 1.0 if player == Player.CPU else -1.0

    task.append(col)

    if depth == taskDepth:
        return taskGrades[tuple(task)]

    if depth == 0:
        return 0.0

    next_player = otherPlayer(player)
    sum = 0.0
    num_moves = 0
    all_win, all_lose = True, True

    for c in range(board.width):
        if board.legalMove(c):
            num_moves += 1
            board.move(next_player, c)
            res = moveGrade(board, next_player, c, task.copy(), depth - 1, taskDepth)
            board.undoMove(c)

            if res > -1.0:
                all_lose = False
            if res < 1.0:
                all_win = False
            if res == 1.0 and next_player == Player.CPU:
                return 1.0
            if res == -1.0 and next_player == Player.HUMAN:
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
    STOP = auto()

def moveGrades(board, player, fullDepth, taskDepth):
    tasks = makeTasks(board, player, fullDepth, taskDepth)
    tasksLeft = len(tasks)

    start = time.time()

    while True:
        status = MPI.Status()
        if comm.Iprobe(status = status):
            rank = status.Get_source()
            tag = status.Get_tag()

            if tag == Tag.TASK_GRADE:
                (task, grade) = comm.recv(source = rank, tag = tag)
                taskGrades[tuple(task)] = grade
                tasksLeft -= 1

                if not tasksLeft:
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
        if board.legalMove(c):
            board.move(player, c)
            grades[c] = moveGrade(board, player, c, [], fullDepth - 1, taskDepth)
            board.undoMove(c)

    end = time.time()
    print('duration = %.3f' % (1000.0 * float(end - start)))

    taskGrades.clear()

    return grades;

def bestMove(moveGrades):
    return max(zip(moveGrades, range(len(moveGrades))))[1]

def solveTask(taskDepth):
    board, player, task = comm.recv(source = 0, tag = Tag.TASK)

    while True:
        for i in range(len(task) - 1):
            board.move(player, task[i])
            player = otherPlayer(player)

        grade = moveGrade(board, player, task[-1], [], taskDepth, -1)
        comm.send((task, grade), dest = 0, tag = Tag.TASK_GRADE)

        comm.probe(status = status)
        tag = status.Get_tag()

        if tag == Tag.STOP:
            sys.exit(0)

        if tag == Tag.NO_MORE_TASKS:
            comm.recv(source = 0, tag = Tag.NO_MORE_TASKS)
            break

        board, player, task = comm.recv(source = 0, tag = Tag.TASK)

def signalHandler(sig, frame):
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signalHandler)

    if myRank == 0:
        board = Board(HEIGHT, WIDTH)
        print(board, flush = True)

        while True:
            humanMove = int(input())
            board.move(Player.HUMAN, humanMove)

            print(board, flush = True)

            if board.win(Player.HUMAN, humanMove):
            break

            grades = moveGrades(board, Player.CPU, FULL_DEPTH, TASK_DEPTH)
            print(' '.join(['-' if grade < -2.0 else ('%.3f' % grade) for grade in grades]), flush = True)

            cpuMove = bestMove(grades)
            board.move(Player.CPU, cpuMove)

            print(board, flush = True)

            if board.win(Player.CPU, cpuMove):
                break

        for rank in range(1, numWorkers + 1):
            comm.send([], dest = rank, tag = Tag.STOP)
    else:
        while True:
            comm.send([], dest = 0, tag = Tag.TASK_REQUEST)

            status = MPI.Status()
            comm.probe(status = status)
            tag = status.Get_tag()

            if tag == Tag.STOP:
                comm.recv(source = 0, tag = Tag.STOP)
                break
            if tag == Tag.NO_MORE_TASKS:
                comm.recv(source = 0, tag = Tag.NO_MORE_TASKS)
            else:
                solveTask(TASK_DEPTH)   
