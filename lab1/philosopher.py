from enum import IntEnum, auto
from mpi4py import MPI
import sys
import random
import time
import signal

class Fork:
    def __init__(self, here = True, clean = False, requested = False):
        self.here = here
        self.clean = clean
        self.requested = requested

class Tag(IntEnum):
    REQUEST_FORK = auto()
    SEND_FORK = auto()

MAXLEN = 26

MINTIME = 2
MAXTIME = 5

comm = MPI.COMM_WORLD

numPhils = comm.Get_size()
if (numPhils < 2):
    sys.exit("There must be at least 2 philosophers at the table")

myRank = comm.Get_rank()
leftRank = (myRank - 1 + numPhils) % numPhils
rightRank = (myRank + 1) % numPhils

forks = {leftRank : Fork(myRank == 0, False, False), rightRank : Fork(myRank != (numPhils - 1), False, False)}

def printMsg(msg):
    print('|'.join([('{:^%d}' % MAXLEN).format(msg if r == myRank else '') for r in range(numPhils)]), flush = True)

def sendFork(rank):
    forks[rank].clean = True
    printMsg("Sending fork to " + str(rank))
    comm.send([], dest = rank, tag = Tag.SEND_FORK)
    forks[rank].here = False

def think():
    thinking = random.randint(MINTIME, MAXTIME)
    printMsg("I'm thinking...")

    while thinking:
        time.sleep(1)

        status = MPI.Status()
        if comm.Iprobe(tag = Tag.REQUEST_FORK, status = status):
            rank = status.Get_source()
            comm.recv(source = rank, tag = Tag.REQUEST_FORK)
            sendFork(rank)

        thinking -= 1

    printMsg('Done thinking')

def acquireForks():
    printMsg("I'm hungry")

    for rank in forks:
        if not forks[rank].here:
            printMsg('Requesting fork from ' + str(rank))
            comm.send([], dest = rank, tag = Tag.REQUEST_FORK)

    while not forks[leftRank].here or not forks[rightRank].here:
        status = MPI.Status()
        if comm.Iprobe(status = status):
            rank = status.Get_source()
            tag = status.Get_tag()
            comm.recv(source = rank, tag = tag)

            if tag == Tag.REQUEST_FORK:
                forks[rank].requested = True
            elif tag == Tag.SEND_FORK:
                forks[rank].here = True
                printMsg("Received fork from " + str(rank))

def eat():
    eating = random.randint(MINTIME, MAXTIME)
    printMsg("I'm eating...")

    time.sleep(eating)

    for rank in forks:
        forks[rank].clean = False

    printMsg("Done eating") 

def handleRequests():
    for rank in forks:
        if forks[rank].requested:
            sendFork(rank)
            forks[rank].requested = False

def signalHandler(sig, frame):
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signalHandler)

    random.seed(int(time.time()) ^ (myRank << leftRank))

    if myRank == 0:
        print('|'.join([('{:^%d}' % MAXLEN).format('Philosopher {}'.format(r)) for r in range(numPhils)]))
        print('-' * ((MAXLEN + 1) * numPhils - 1), flush = True)
    comm.Barrier()

    while True:
        think() 
        acquireForks()
        eat()
        handleRequests() 

        printMsg('-' * MAXLEN)

if __name__ == "__main__":
    main()
