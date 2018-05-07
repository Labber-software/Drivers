#!/usr/bin/env python3
from enum import Enum
import numpy as np
from copy import copy

# add logger, to allow logging to Labber's instrument log
import logging
log = logging.getLogger('LabberDriver')

class BaseGate:
    """
    Acts as a base class for different gates. Not to be instantiated.
    """
    def __init__(self):
        self.phase_shift = 0

    def add_phase(self, shift):
        """
        Adds the desired phase shift to a new instance of the gate, and returns
        that instance.
        """
        new_gate = copy(self)
        new_gate.phase_shift += shift
        return new_gate

    def get_waveform(self, pulse, t0, t):
        """
        Returns the waveform corresponding to the gate.

        Parameters
        ----------
        pulse : Pulse object
            The pulse object to use for the gate.
        t0 : float
            The time of the pulse center.
        t : numpy array
            The time vector to use for the waveform.

        Returns
        ----------
        waveform : numpy array
            The calculated waveform.
        """
        pulse = copy(pulse)
        pulse.phase += self.phase_shift
        return pulse.calculate_waveform(t0, t)

    def get_matrix(self):
        """
        Returns the matrix representation of the gate.
        """
        # TODO Implement this for each type of gate
        pass


class SingleQubitRotation(BaseGate):
    """
    Single qubit rotation gate. Rotates the qubit around a given axis(X, Y, Z),
    with a specified angle.
    """
    def __init__(self, axis, angle):
        super().__init__()
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
            # TODO Implement this
            pass
        else:
            raise ValueError('Axis must be X, Y, or Z.')
        # pi pulse should correspond to the full amplitude
        pulse.amplitude *= self.angle/np.pi
        return super().get_waveform(pulse, t0, t)


class IdentityGate(BaseGate):
    """
    Identity gate. Does nothing to the qubit. The width can be specififed to
    implement a delay in the sequence. If no width is given, the identity gate
    inherits the width of the given pulse.
    """
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
    """
    A virtual Z gate. Rotates the subsequent pulses with the given angle.
    """
    def __init__(self, angle):
        super().__init__()
        self.angle = angle


class TwoQubitGate(BaseGate):
    # TODO Make this have two gates. I if nothing on the second waveform
    def __init__(self):
        super().__init__()

    def get_waveform(self, pulse, t0, t):
        # TODO How to implement phase shift
        return super().get_waveform(pulse, t0, t)


class ReadoutGate(BaseGate):
    """
    Readouts the qubit state.
    """
    def __init__(self):
        super().__init__()

    def get_waveform(self, pulse, t0, t):
        return super().get_waveform(pulse, t0, t)


class CustomGate(BaseGate):
    """
    A custom gate that uses the given pulse.
    """
    def __init__(self, pulse):
        super().__init__()
        self.pulse = pulse

    def get_waveform(self, pulse, t0, t):
        return super().get_waveform(self.pulse, t0, t)


class CompositeGate:
    """
    Implements composite gates, that is a gate consisting of many other gates.
    """
    def __init__(self, n_qubit=1):
        self.n_qubit = n_qubit
        self.sequence = []

    def add_gate(self, gate, t0=None, dt=None, align='center'):
        """
        Adds gate to the composite gate.
        """
        if not isinstance(gate, list):
            gate = [gate]
        if len(gate) != self.n_qubit:
            raise ValueError('Number of gates not equal to number of qubits')

        self.sequence.append(gate)

    def get_gate_at_index(self, i):
        """
        Returns the gates at a given index in the sequence.
        """
        return self.sequence[i]

    def __len__(self):
        return len(self.sequence)


class MeasurementGate(CompositeGate):
    """
    Measures the qubit along the specified axis.
    Axis should be X, Y, or Z. The sign is either positive (P) or negative (M).
    """
    def __init__(self, axis='Z', sign='P'):
        # TODO Ask Morten about conventions here
        super().__init__(n_qubit=1)

        if axis == 'Z' and sign == 'P':
            gate = IdentityGate()
        elif axis == 'Z' and sign == 'M':
            gate = SingleQubitRotation(axis='X', angle=np.pi)
        elif axis == 'Y' and sign == 'P':
            gate = SingleQubitRotation(axis='X', angle=np.pi/2)
        elif axis == 'X' and sign == 'P':
            gate = SingleQubitRotation(axis='Y', angle=-np.pi/2)
        elif axis == 'Y' and sign == 'M':
            gate = SingleQubitRotation(axis='X', angle=-np.pi/2)
        elif axis == 'X' and sign == 'M':
            gate = SingleQubitRotation(axis='Y', angle=np.pi/2)
        else:
            raise ValueError('Axis must be X, Y or Z, and sign must be P or M.')

        self.add_gate(gate)
        self.add_gate(ReadoutGate())


class Gate(Enum):
    """Define possible qubit gates"""
    # single-qubit gates
    I = IdentityGate()
    Xp = SingleQubitRotation(axis='X', angle=np.pi)
    Xm = SingleQubitRotation(axis='X', angle=-np.pi)
    X2p = SingleQubitRotation(axis='X', angle=np.pi/2)
    X2m = SingleQubitRotation(axis='X', angle=-np.pi/2)
    Yp = SingleQubitRotation(axis='Y', angle=np.pi)
    Ym = SingleQubitRotation(axis='Y', angle=-np.pi)
    Y2m = SingleQubitRotation(axis='Y', angle=-np.pi/2)
    Y2p = SingleQubitRotation(axis='Y', angle=np.pi/2)
    Zp = SingleQubitRotation(axis='Z', angle=np.pi)
    Z2p = SingleQubitRotation(axis='Z', angle=np.pi/2)
    Zm = SingleQubitRotation(axis='Z', angle=-np.pi)
    Z2m = SingleQubitRotation(axis='Z', angle=-np.pi/2)

    # two-qubit gates
    CPh = TwoQubitGate()

    # Readout
    Mxp = MeasurementGate(axis='X', sign='P')
    Myp = MeasurementGate(axis='Y', sign='P')
    Mzp = MeasurementGate(axis='Z', sign='P')
    Mxm = MeasurementGate(axis='X', sign='M')
    Mym = MeasurementGate(axis='Y', sign='M')
    Mzm = MeasurementGate(axis='Z', sign='M')

    # Composite gates
    ZZEcho = CompositeGate(n_qubit=2)
    ZZEcho.add_gate([X2p, I])
    ZZEcho.add_gate([CPh, I])
    ZZEcho.add_gate([Xp, Xp])
    ZZEcho.add_gate([CPh, I])
    ZZEcho.add_gate([X2p, Xp])

    CNOT = CompositeGate(n_qubit=2)
    CNOT.add_gate([I, Y2m])
    CNOT.add_gate([CPh, I])
    CNOT.add_gate([I, Y2p])


if __name__ == '__main__':
    pass
