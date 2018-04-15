#!/usr/bin/env python3

from enum import Enum
import numpy as np
from copy import copy

# add logger, to allow logging to Labber's instrument log
import logging
log = logging.getLogger('LabberDriver')

class BaseGate:
    def __init__(self):
        self.phase_shift = 0

    def add_phase(self, shift):
        return self

    def get_waveform(self, pulse, t0, t):
        pulse = copy(pulse)
        pulse.phase += self.phase_shift
        return pulse.calculate_waveform(t0, t)

    def get_matrix(self):
        # TODO Implement this for each type of gate
        pass


class SingleQubitGate(BaseGate): # TODO SingleQubitRotation
    def __init__(self, axis, angle):
        super().__init__()
        self.axis = axis
        self.angle = angle

    def add_phase(self, shift):
        new_gate = copy(self)
        new_gate.phase_shift += shift
        return new_gate

    def get_waveform(self, pulse, t0, t):
        pulse = copy(pulse)
        if self.axis == 'X':
            pulse.phase += 0
        elif self.axis == 'Y':
            pulse.phase += np.pi/2
        elif self.axis == 'Z':
            # Z pulses are real valued, i.e. no phase
            # TODO Implement this
            # TODO Button for Z or VZ
            pass
        else:
            raise ValueError('Axis must be X, Y, or Z.')
        # pi pulse should correspond to the full amplitude
        pulse.amplitude *= self.angle/np.pi
        return super().get_waveform(pulse, t0, t)


class IdentityGate(BaseGate):
    def __init__(self, width=None):
        super().__init__()
        self.width = width

    def get_waveform(self, pulse, t0, t):
        pulse = copy(pulse)
        pulse.amplitude = 0
        if self.width is not None:
            pulse.width = self.width
            pulse.plateau = 0
        return super().get_waveform(pulse, t0, t)


class VirtualZGate(BaseGate):
    def __init__(self, angle):
        super().__init__()
        self.angle = angle


class TwoQubitGate(BaseGate):
    # TODO Make this have two gates. I if nothing on the second waveform
    def __init__(self):
        super().__init__()

    def add_phase(self, shift):
        # TODO Implement this!
        pass

    def get_waveform(self, pulse, t0, t):
        return super().get_waveform(pulse, t0, t)


class ReadoutGate(BaseGate):
    def __init__(self):
        super().__init__()

    def get_waveform(self, pulse, t0, t):
        return super().get_waveform(pulse, t0, t)


class CustomGate(BaseGate):
        def __init__(self, pulse):
            super().__init__()
            self.pulse = pulse

        def get_waveform(self, pulse, t0, t):
            return super().get_waveform(self.pulse, t0, t)


class CompositeGate:
    def __init__(self, n_qubit=1):
        self.n_qubit = n_qubit
        self.sequence = []

    def add_gate(self, gate, t0=None, dt=None, align='center'):
        if not isinstance(gate, list):
            gate = [gate]
        if t0 is not None:
            raise NotImplementedError('t0 alignment not implemented yet')
        if len(gate) != self.n_qubit:
            raise ValueError('Number of gates not equal to number of qubits')

        g = {
            'gate': gate,
            'dt': dt,
            'align': align
        }
        self.sequence.append(g)


    def get_gate_dict_at_index(self, i):
        return copy(self.sequence[i])

    def __len__(self):
        return len(self.sequence)


class SingleMeasurementGate(CompositeGate):
    def __init__(self, axis='Z', sign='P'):
        # TODO Ask Morten about conventions here
        super().__init__(n_qubit=1)

        if axis == 'Z' and sign == 'P':
            gate = IdentityGate()
        elif axis == 'Z' and sign == 'M':
            gate = SingleQubitGate(axis='X', angle=np.pi)
        elif axis == 'Y' and sign == 'P':
            gate = SingleQubitGate(axis='X', angle=np.pi/2)
        elif axis == 'X' and sign == 'P':
            gate = SingleQubitGate(axis='Y', angle=-np.pi/2)
        elif axis == 'Y' and sign == 'M':
            gate = SingleQubitGate(axis='X', angle=-np.pi/2)
        elif axis == 'X' and sign == 'M':
            gate = SingleQubitGate(axis='Y', angle=np.pi/2)
        else:
            raise ValueError('Axis must be X, Y or Z, and sign must be P or M.')

        self.add_gate(gate)
        self.add_gate(ReadoutGate())



class Gate(Enum):
    """Define possible qubit gates"""
    # single-qubit gates
    I = IdentityGate()
    Xp = SingleQubitGate(axis='X', angle=np.pi)
    Xm = SingleQubitGate(axis='X', angle=-np.pi)
    X2p = SingleQubitGate(axis='X', angle=np.pi/2)
    X2m = SingleQubitGate(axis='X', angle=-np.pi/2)
    Yp = SingleQubitGate(axis='Y', angle=np.pi)
    Ym = SingleQubitGate(axis='Y', angle=-np.pi)
    Y2m = SingleQubitGate(axis='Y', angle=-np.pi/2)
    Y2p = SingleQubitGate(axis='Y', angle=np.pi/2)

    # two-qubit gates
    CPh = TwoQubitGate()

    # Readout
    Rxp = SingleMeasurementGate(axis='X', sign='P')
    Ryp = SingleMeasurementGate(axis='Y', sign='P')
    Rzp = SingleMeasurementGate(axis='Z', sign='P')
    Rxm = SingleMeasurementGate(axis='X', sign='M')
    Rym = SingleMeasurementGate(axis='Y', sign='M')
    Rzm = SingleMeasurementGate(axis='Z', sign='M')


if __name__ == '__main__':
    pass
