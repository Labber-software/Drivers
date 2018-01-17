#!/usr/bin/env python3

from enum import Enum

class Gate(Enum):
    """Define possible qubit gates"""
    # single-qubit gates
    I = -1
    Xp = 0
    Xm = 1
    X2p = 2
    X2m = 3
    Yp = 4
    Ym = 5
    Y2m = 6
    Y2p = 7
    # two-qubit gates
    CPh = 8


# define set of one- and two-qubit gates
ONE_QUBIT_GATES = (Gate.Xp, Gate.Xm, Gate.X2p, Gate.X2m,
                   Gate.Yp, Gate.Ym, Gate.Y2p, Gate.Y2m,
                   Gate.I)
TWO_QUBIT_GATES = (Gate.CPh,)



if __name__ == '__main__':
    pass
