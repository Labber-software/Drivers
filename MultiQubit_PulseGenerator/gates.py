#!/usr/bin/env python3

from enum import Enum
import numpy as np
from copy import copy

class BaseGate:
    def __init__(self):
        pass

    def get_waveform(self, pulse, t0, t):
        pulse = copy(pulse)
        return pulse.calculate_waveform(t0, t)


class SingleQubitGate(BaseGate):
    def __init__(self, axis, angle):
        self.axis = axis
        self.angle = angle

    def get_waveform(self, pulse, t0, t):
        pulse = copy(pulse)
        if self.axis == 'X':
            pulse.phase += 0
        elif self.axis == 'Y':
            pulse.phase += np.pi/2
        elif self.axis == 'Z':
            # Z pulses are real valued, i.e. no phase
            pass
        # pi pulse should correspond to the full amplitude
        pulse.amplitude *= self.angle/np.pi
        return super().get_waveform(pulse, t, t0)


class TwoQubitGate(BaseGate):
    pass
    # Am I control or target?

class MeasurementGate(BaseGate):
    def __init__(self):
        pass

    def get_waveform(self, pulse, t0, t):
        return super().get_waveform(pulse, t0, t)

class CompositeGate:
    def __init__(self, gates=[], t=[]):
        pass

class Gate(Enum):
    """Define possible qubit gates"""
    # single-qubit gates
    I = SingleQubitGate(axis='X', angle=0)
    Xp = SingleQubitGate(axis='X', angle=np.pi)
    Xm = SingleQubitGate(axis='X', angle=-np.pi)
    X2p = SingleQubitGate(axis='X', angle=np.pi/2)
    X2m = SingleQubitGate(axis='X', angle=-np.pi/2)
    Yp = SingleQubitGate(axis='Y', angle=np.pi)
    Ym = SingleQubitGate(axis='Y', angle=-np.pi)
    Y2m = SingleQubitGate(axis='Y', angle=-np.pi/2)
    Y2p = SingleQubitGate(axis='Y', angle=np.pi)
    # two-qubit gates
    CPh = 8


# define set of one- and two-qubit gates
ONE_QUBIT_GATES = (Gate.Xp, Gate.Xm, Gate.X2p, Gate.X2m,
                   Gate.Yp, Gate.Ym, Gate.Y2p, Gate.Y2m,
                   Gate.I)
TWO_QUBIT_GATES = (Gate.CPh,)





if __name__ == '__main__':
    pass
