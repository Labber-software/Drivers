#!/usr/bin/env python3
from enum import Enum
import numpy as np
from copy import copy

# add logger, to allow logging to Labber's instrument log
import logging
log = logging.getLogger('LabberDriver')


class BaseGate:
    """Short summary.

    Attributes
    ----------
    phase_shift : float
        Description of attribute `phase_shift`.

    """

    def __init__(self):
        self.phase_shift = 0

    def add_phase(self, shift):
        """Return a new instance of the gate, but with a phase shift applied.

        Parameters
        ----------
        shift : float
            The angle in radians.

        Returns
        -------
        :obj: BaseGate
            The new instance of the gate.

        """
        new_gate = copy(self)
        new_gate.phase_shift += shift
        return new_gate

    def get_waveform(self, pulse, t0, t):
        """
        Return the waveform corresponding to the gate.

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
        """Return the matrix representation of the gate."""
        # TODO Implement this for each type of gate
        pass


class SingleQubitRotation(BaseGate):
    """Short summary.

    Parameters
    ----------
    axis : type
        Description of parameter `axis`.
    angle : type
        Description of parameter `angle`.

    Attributes
    ----------
    axis        angle

    """

    def __init__(self, axis, angle):
        super().__init__()
        self.axis = axis
        self.angle = angle

    def get_waveform(self, pulse, t0, t):
        """Short summary.

        Parameters
        ----------
        pulse : type
            Description of parameter `pulse`.
        t0 : type
            Description of parameter `t0`.
        t : type
            Description of parameter `t`.

        Returns
        -------
        type
            Description of returned object.

        """
        pulse = copy(pulse)
        if self.axis == 'X':
            pulse.phase += 0
        elif self.axis == 'Y':
            pulse.phase += np.pi / 2
        elif self.axis == 'Z':
            # Z pulses are real valued, i.e. no phase
            pass
        else:
            raise ValueError('Axis must be X, Y, or Z.')
        # pi pulse should correspond to the full amplitude
        pulse.amplitude *= self.angle / np.pi
        return super().get_waveform(pulse, t0, t)


class IdentityGate(BaseGate):
    """Identity gate.

    Does nothing to the qubit. The width can be specififed to
    implement a delay in the sequence. If no width is given, the identity gate
    inherits the width of the given pulse.

    Parameters
    ----------
    width : type
        Description of parameter `width` (the default is None).

    Attributes
    ----------
    width

    """

    def __init__(self, width=None):
        super().__init__()
        self.width = width

    def get_waveform(self, pulse, t0, t):  # noqa: D102
        pulse = copy(pulse)
        pulse.amplitude = 0
        if self.width is not None:
            pulse.width = self.width
            pulse.plateau = 0
        return super().get_waveform(pulse, t0, t)


class VirtualZGate(BaseGate):
    """Virtual Z Gate."""

    def __init__(self, angle):
        super().__init__()
        self.angle = angle


class TwoQubitGate(BaseGate):
    """Two qubit gate."""

    # TODO Make this have two gates. I if nothing on the second waveform
    def __init__(self):
        super().__init__()

    def get_waveform(self, pulse, t0, t):  # noqa: D102
        return super().get_waveform(pulse, t0, t)


class ReadoutGate(BaseGate):
    """Readouts the qubit state."""

    def __init__(self):
        super().__init__()

    def get_waveform(self, pulse, t0, t):  # noqa: D102
        return super().get_waveform(pulse, t0, t)


class CustomGate(BaseGate):
    """Short summary.

    Parameters
    ----------
    pulse : type
        Description of parameter `pulse`.

    Attributes
    ----------
    pulse

    """

    def __init__(self, pulse):
        super().__init__()
        self.pulse = pulse

    def get_waveform(self, pulse, t0, t):  # noqa: D102
        return super().get_waveform(self.pulse, t0, t)


class CompositeGate:
    """Short summary.

    Parameters
    ----------
    n_qubit : type
        Description of parameter `n_qubit` (the default is 1).

    Attributes
    ----------
    sequence : type
        Description of attribute `sequence`.
    def __init__(self, n_qubit : type
        Description of attribute `def __init__(self, n_qubit`.
    n_qubit

    """

    def __init__(self, n_qubit=1):
        self.n_qubit = n_qubit
        self.sequence = []

    def add_gate(self, gate, t0=None, dt=None, align='center'):
        """Short summary.

        Parameters
        ----------
        gate : type
            Description of parameter `gate`.
        t0 : type
            Description of parameter `t0` (the default is None).
        dt : type
            Description of parameter `dt` (the default is None).
        align : type
            Description of parameter `align` (the default is 'center').

        Returns
        -------
        type
            Description of returned object.

        """
        if not isinstance(gate, list):
            gate = [gate]
        if len(gate) != self.n_qubit:
            raise ValueError('Number of gates not equal to number of qubits')

        self.sequence.append(gate)

    def get_gate_at_index(self, i):
        """Short summary.

        Parameters
        ----------
        i : type
            Description of parameter `i`.

        Returns
        -------
        type
            Description of returned object.

        """
        return self.sequence[i]

    def __len__(self):
        return len(self.sequence)


class MeasurementGate(CompositeGate):
    """Measures the qubit along the specified axis.

    Axis should be X, Y, or Z. The sign is either positive (P) or negative (M).
    """

    def __init__(self, axis='Z', sign='P'):
        super().__init__(n_qubit=1)

        if axis == 'Z' and sign == 'P':
            gate = IdentityGate()
        elif axis == 'Z' and sign == 'M':
            gate = SingleQubitRotation(axis='X', angle=np.pi)
        elif axis == 'Y' and sign == 'P':
            gate = SingleQubitRotation(axis='X', angle=np.pi / 2)
        elif axis == 'X' and sign == 'P':
            gate = SingleQubitRotation(axis='Y', angle=-np.pi / 2)
        elif axis == 'Y' and sign == 'M':
            gate = SingleQubitRotation(axis='X', angle=-np.pi / 2)
        elif axis == 'X' and sign == 'M':
            gate = SingleQubitRotation(axis='Y', angle=np.pi / 2)
        else:
            raise ValueError('Axis must be X, Y or Z, and sign P or M.')

        self.add_gate(gate)
        self.add_gate(ReadoutGate())


class CZ(CompositeGate):
    """Short summary.

    Parameters
    ----------
    phi1 : type
        Description of parameter `phi1`.
    phi2 : type
        Description of parameter `phi2`.

    Attributes
    ----------
    add_gate : type
        Description of attribute `add_gate`.
    add_gate : type
        Description of attribute `add_gate`.

    """

    def __init__(self, phi1, phi2):
        super().__init__(n_qubit=2)
        self.add_gate([TwoQubitGate(), IdentityGate()])
        self.add_gate([VirtualZGate(phi1), VirtualZGate(phi2)])

    def new_angles(self, phi1, phi2):
        """Short summary.

        Parameters
        ----------
        phi1 : type
            Description of parameter `phi1`.
        phi2 : type
            Description of parameter `phi2`.

        Returns
        -------
        type
            Description of returned object.

        """
        self.__init__(phi1, phi2)


class Gate(Enum):
    """Define possible qubit gates."""

    I = IdentityGate()

    # X gates
    Xp = SingleQubitRotation(axis='X', angle=np.pi)
    Xm = SingleQubitRotation(axis='X', angle=-np.pi)
    X2p = SingleQubitRotation(axis='X', angle=np.pi / 2)
    X2m = SingleQubitRotation(axis='X', angle=-np.pi / 2)

    # Y gates
    Yp = SingleQubitRotation(axis='Y', angle=np.pi)
    Ym = SingleQubitRotation(axis='Y', angle=-np.pi)
    Y2m = SingleQubitRotation(axis='Y', angle=-np.pi / 2)
    Y2p = SingleQubitRotation(axis='Y', angle=np.pi / 2)

    # Z gates
    Zp = SingleQubitRotation(axis='Z', angle=np.pi)
    Z2p = SingleQubitRotation(axis='Z', angle=np.pi / 2)
    Zm = SingleQubitRotation(axis='Z', angle=-np.pi)
    Z2m = SingleQubitRotation(axis='Z', angle=-np.pi / 2)

    # Virtual Z gates
    VZp = VirtualZGate(angle=np.pi)
    VZ2p = VirtualZGate(angle=np.pi / 2)
    VZm = VirtualZGate(angle=-np.pi)
    VZ2m = VirtualZGate(angle=np.pi / 2)

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
    CZEcho = CompositeGate(n_qubit=2)
    CZEcho.add_gate([X2p, I])
    CZEcho.add_gate([CPh, I])
    CZEcho.add_gate([Xp, Xp])
    CZEcho.add_gate([CPh, I])
    CZEcho.add_gate([X2p, Xp])

    CNOT = CompositeGate(n_qubit=2)
    CNOT.add_gate([I, Y2m])
    CNOT.add_gate([CPh, I])
    CNOT.add_gate([I, Y2p])

    CZ = CZ(0, 0)


if __name__ == '__main__':
    pass
