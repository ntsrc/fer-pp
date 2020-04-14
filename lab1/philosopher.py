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

comm = MPI.COMM_WORLD

num_phils = comm.Get_size()
if (num_phils < 2):
    sys.exit("There must be at least 2 philosophers at the table")

my_rank = comm.Get_rank()
left_rank = (my_rank - 1 + num_phils) % num_phils
right_rank = (my_rank + 1) % num_phils

forks = {left_rank : Fork(my_rank == 0, False, False), right_rank : Fork(my_rank != (num_phils - 1), False, False)}

def print_msg(msg):
    print('|'.join(['{:^26}'.format(msg if r == my_rank else '') for r in range(num_phils)]), flush = True)

def send_fork(rank):
    forks[rank].clean = True
    print_msg("Sending fork to " + str(rank))
    comm.send([], dest = rank, tag = Tag.SEND_FORK)
    forks[rank].here = False

def think():
    thinking = random.randint(2, 6)
    print_msg("I'm thinking...")

    while thinking:
        time.sleep(1)

        status = MPI.Status()
        if comm.Iprobe(tag = Tag.REQUEST_FORK, status = status):
            rank = status.Get_source()
            comm.recv(source = rank, tag = Tag.REQUEST_FORK)
            send_fork(rank)

        thinking -= 1

    print_msg('Done thinking')

def acquire_forks():
    print_msg("I'm hungry")

    for rank in forks:
        if not forks[rank].here:
            print_msg('Requesting fork from ' + str(rank))
            comm.send([], dest = rank, tag = Tag.REQUEST_FORK)

    while not forks[left_rank].here or not forks[right_rank].here:
        status = MPI.Status()
        if comm.Iprobe(status = status):
            rank = status.Get_source()
            tag = status.Get_tag()
            comm.recv(source = rank, tag = tag)

            if tag == Tag.REQUEST_FORK:
                forks[rank].requested = True
            elif tag == Tag.SEND_FORK:
                forks[rank].here = True

def eat():
    eating = random.randint(2,6)
    print_msg("I'm eating...")

    time.sleep(eating)

    for rank in forks:
        forks[rank].clean = False

    print_msg("Done eating") 

def handle_requests():
    for rank in forks:
        if forks[rank].requested:
            send_fork(rank)
            forks[rank].requested = False

def signal_handler(sig, frame):
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)

    random.seed(int(time.time()) ^ (my_rank << left_rank))

    if my_rank == 0:
        print('|'.join(['{:^26}'.format('Philosopher {}'.format(r)) for r in range(num_phils)]) + '\n' + ('-'*(27*num_phils-1)), flush = True)
    comm.Barrier()

    while True:
        think() 
        acquire_forks()
        eat()
        handle_requests() 

        print_msg('-'*26)

if __name__ == "__main__":
    main()
