#!/usr/bin/env python3
from copy import copy
import numpy as np


class BaseGate:
    """Base class for a qubit gate.

    """

    def get_adjusted_pulse(self, pulse):
        pulse = copy(pulse)
        return pulse


class SingleQubitXYRotation(BaseGate):
    """Single qubit rotations around the XY axes.

    Angles defined as in https://en.wikipedia.org/wiki/Bloch_sphere.

    Parameters
    ----------
    phi : float
        Rotation axis.
    theta : float
        Roation angle.

    """

    def __init__(self, phi, theta):
        self.phi = phi
        self.theta = theta

    def get_adjusted_pulse(self, pulse):
        pulse = copy(pulse)
        pulse.phase = self.phi
        # pi pulse correspond to the full amplitude
        pulse.amplitude *= self.theta / np.pi
        return pulse

class SingleQubitZRotation(BaseGate):
    """Single qubit rotation around the Z axis.

    Parameters
    ----------
    theta : float
        Roation angle.

    """

    def __init__(self, theta):
        self.theta = theta

    def get_adjusted_pulse(self, pulse):
        pulse = copy(pulse)
        # pi pulse correspond to the full amplitude
        pulse.amplitude *= self.theta / np.pi
        return pulse


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
        self.width = width

    def get_adjusted_pulse(self, pulse):
        pulse = copy(pulse)
        pulse.amplitude = 0
        pulse.use_drag = False # Avoids bug
        if self.width is not None:
            pulse.width = self.width
            pulse.plateau = 0
        return pulse


class VirtualZGate(BaseGate):
    """Virtual Z Gate."""

    def __init__(self, theta):
        self.theta = theta


class TwoQubitGate(BaseGate):
    """Two qubit gate."""
    # TODO Make this have two gates. I if nothing on the second waveform


class ReadoutGate(BaseGate):
    """Readouts the qubit state."""


class CustomGate(BaseGate):
    """A gate using a given :obj:`Pulse`.

    Parameters
    ----------
    pulse : :obj:`Pulse`
        The corresponding pulse.

    """

    def __init__(self, pulse):
        self.pulse = pulse


class RabiGate(BaseGate):
    """Creates the Rabi gate used in the spin-locking sequence.

    Parameters
    ----------
    amplitude : Amplitude of the pulse
    plateau : The duration of the pulse.
    phase : Phase of the Rabi gate. 0 corresponds to rotation around X axis.
    """

    def __init__(self, amplitude, plateau, phase):
        self.amplitude = amplitude
        self.plateau = plateau
        self.phase = phase

    def get_adjusted_pulse(self, pulse):
        pulse = copy(pulse)
        pulse.amplitude = self.amplitude
        pulse.plateau = self.plateau
        pulse.phase = self.phase
        return pulse


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


I = IdentityGate()

# X gates
Xp = SingleQubitXYRotation(phi=0, theta=np.pi)
Xm = SingleQubitXYRotation(phi=0, theta=-np.pi)
X2p = SingleQubitXYRotation(phi=0, theta=np.pi/2)
X2m = SingleQubitXYRotation(phi=0, theta=-np.pi/2)

# Y gates
Yp = SingleQubitXYRotation(phi=np.pi/2, theta=np.pi)
Ym = SingleQubitXYRotation(phi=np.pi/2, theta=-np.pi)
Y2m = SingleQubitXYRotation(phi=np.pi/2, theta=-np.pi/2)
Y2p = SingleQubitXYRotation(phi=np.pi/2, theta=np.pi/2)

# Z gates
Zp = SingleQubitZRotation(np.pi)
Z2p = SingleQubitZRotation(np.pi/2)
Zm = SingleQubitZRotation(-np.pi)
Z2m = SingleQubitZRotation(-np.pi/2)

# Virtual Z gates
VZp = VirtualZGate(theta=np.pi)
VZ2p = VirtualZGate(theta=np.pi/2)
VZm = VirtualZGate(theta=-np.pi)
VZ2m = VirtualZGate(theta=np.pi/2)

# two-qubit gates
CPh = TwoQubitGate()

# Readout
# TODO Make these with composite gates just
# Mxp = MeasurementGate(axis='X', sign='P')
# Myp = MeasurementGate(axis='Y', sign='P')
# Mzp = MeasurementGate(axis='Z', sign='P')
# Mxm = MeasurementGate(axis='X', sign='M')
# Mym = MeasurementGate(axis='Y', sign='M')
# Mzm = MeasurementGate(axis='Z', sign='M')

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
