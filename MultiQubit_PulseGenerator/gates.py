#!/usr/bin/env python3
import logging
from copy import copy
from enum import Enum

import numpy as np

log = logging.getLogger('LabberDriver')


class BaseGate:
    """Base class for a qubit gate.

    Attributes
    ----------
    phase_shift : float
        The phase shift applied when compiling into pulsesself.
        For example used for virutal Z gates.

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


class SingleQubitRotation(BaseGate):
    """Single qubit rotations.

    Parameters
    ----------
    axis : str {'X', 'Y', 'Z'}
        Rotation axis.
    angle : float
        Roation angle.

    """

    def __init__(self, axis, angle):
        super().__init__()
        self.axis = axis
        self.angle = angle

    def get_waveform(self, pulse, t0, t):  # noqa D102
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
        # pi pulse correspond to the full amplitude
        pulse.amplitude *= self.angle / np.pi
        return super().get_waveform(pulse, t0, t)


class IdentityGate(BaseGate):
    """Identity gate.

    Does nothing to the qubit. The width can be specififed to
    implement a delay in the sequence. If no width is given, the identity gate
    inherits the width of the given pulse.

    Parameters
    ----------
    width : float
        Width of the I gate in seconds,
        None uses the XY width (the default is None).

    """

    def __init__(self, width=None):
        super().__init__()
        self.width = width

    def get_waveform(self, pulse, t0, t):  # noqa: D102
        pulse = copy(pulse)
        pulse.amplitude = 0
        pulse.use_drag = False
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

    def get_waveform(self, pulse, t0, t):  # noqa: D102
        return super().get_waveform(pulse, t0, t)


class CustomGate(BaseGate):
    """A gate using a given :obj:`Pulse`.

    Parameters
    ----------
    pulse : :obj:`Pulse`
        The corresponding pulse.

    """

    def __init__(self, pulse):
        super().__init__()
        self.pulse = pulse

    def get_waveform(self, pulse, t0, t):  # noqa: D102
        return super().get_waveform(self.pulse, t0, t)


class RabiGate(BaseGate):
    """Creates the Rabi gate used in the spin-locking sequence.

    Parameters
    ----------
    amplitude : Amplitude of the pulse
    plateau : The duration of the pulse.
    phase : Phase of the Rabi gate. 0 corresponds to rotation around X axis.
    """

    def __init__(self, amplitude, plateau, phase):
        super().__init__()
        self.amplitude = amplitude
        self.plateau = plateau
        self.phase = phase


class CompositeGate:
    """Multiple gates in one object.

    Parameters
    ----------
    n_qubit : int
        Number of qubits involved in the composite gate (the default is 1).

    Attributes
    ----------
    sequence : list of :obj:`BaseGate`
        Holds the gates involved.

    """

    def __init__(self, n_qubit=1):
        self.n_qubit = n_qubit
        self.sequence = []

    def add_gate(self, gate, t0=None, dt=None, align='center'):
        """Add one or multiple gates to the composite gate.

        Parameters
        ----------
        gate : :obj:`BaseGate` or list of :obj:`BaseGate`
            The gates to be added. The length of `gate` must equal `n_qubit`.
        t0 : float, optional
            Absolute gate position (the default is None).
        dt : float, optional
            Gate spacing, referenced to the previous pulse
            (the default is None).
        align : str, optional
            If two or more qubits have differnt pulse lengths, `align`
            specifies how those pulses should be aligned. 'Left' aligns the
            start, 'center' aligns the centers, and 'right' aligns the end,
            (the default is 'center').

        """
        if not isinstance(gate, list):
            gate = [gate]
        if len(gate) != self.n_qubit:
            raise ValueError('Number of gates not equal to number of qubits')

        self.sequence.append(gate)

    def get_gate_at_index(self, i):
        """Get the gates at a certain step in the composite gate.

        Parameters
        ----------
        i : int
            The step position.

        Returns
        -------
        list of :obj:`BaseGate`
            The gates at the `i`:th position.

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
    """CPHASE gate followed by single qubit Z rotations.

    Parameters
    ----------
    phi1 : float
        Z rotation angle for qubit 1.
    phi2 : float
        Z rotation angle for qubit 2.

    """

    def __init__(self, phi1, phi2):
        super().__init__(n_qubit=2)
        self.add_gate([TwoQubitGate(), IdentityGate()])
        self.add_gate([VirtualZGate(phi1), VirtualZGate(phi2)])

    def new_angles(self, phi1, phi2):
        """Update the angles of the single qubit rotations.

        Parameters
        ----------
        phi1 : float
            Z rotation angle for qubit 1.
        phi2 : float
            Z rotation angle for qubit 2.

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

    CZ = CZ(0, 0)  # Start with 0, 0 as the single qubit phase shifts.


if __name__ == '__main__':
    pass
