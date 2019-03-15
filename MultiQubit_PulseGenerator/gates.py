#!/usr/bin/env python3
from copy import copy
import numpy as np
import logging
from sequence import Step
log = logging.getLogger('LabberDriver')

# TODO remove Step dep from CompositeGate

class BaseGate:
    """Base class for a qubit gate.

    """

    def get_adjusted_pulse(self, pulse):
        pulse = copy(pulse)
        return pulse


class OneQubitGate():
    def number_of_qubits(self):
        return 1


class TwoQubitGate():
    def number_of_qubits(self):
        return 2


class SingleQubitXYRotation(BaseGate, OneQubitGate):
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

    def __str__(self):
        return "Phi: {}, theta: {}".format(self.phi, self.theta)

    def __repr__(self):
        return self.__str__()

class SingleQubitZRotation(BaseGate, OneQubitGate):
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


class IdentityGate(BaseGate, OneQubitGate):
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


class VirtualZGate(BaseGate, OneQubitGate):
    """Virtual Z Gate."""

    def __init__(self, theta):
        self.theta = theta



class CPHASE(BaseGate, TwoQubitGate):
    def __init__(self, negative_amplitude=False):
        self.negative_amplitude = negative_amplitude

    def get_adjusted_pulse(self, pulse):
        pulse = copy(pulse)
        pulse.negative_amplitude = self.negative_amplitude
        return pulse


class ReadoutGate(BaseGate, OneQubitGate):
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


class RabiGate(BaseGate, OneQubitGate):
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
        Number of qubits involved in the composite gate.

    Attributes
    ----------
    sequence : list of :Step:
        Holds the gates involved.

    """

    def __init__(self, n_qubit):
        self.n_qubit = n_qubit
        self.sequence = []

    def add_gate(self, gate, qubit=None):
        """Add a set of gates to the given qubit.

        For the qubits with no specificied gate, an IdentityGate will be given.
        The length of the step is given by the longest pulse.

        Parameters
        ----------
        qubit : int or list of int
            The qubit(s) to add the gate(s) to.
        gate : :obj:`BaseGate` or list of :obj:`BaseGate`
            The gate(s) to add.
        """
        if qubit is None:
            if self.n_qubit == 1:
                qubit = 0
            else:
                qubit = [n for n in range(self.n_qubit)]

        step = Step()
        if isinstance(gate, list):
            if len(gate) == 1:
                raise ValueError("For single gates, don't provide gate as a list.")
            if not isinstance(qubit, list):
                raise ValueError("Please provide qubit indices as a list when adding more thab one gate.")
            if len(gate) != len(qubit):
                raise ValueError("Length of gate list must be equal to length of qubit list.")

            for q, g in zip(qubit, gate):
                step.add_gate(q, g)

        else:
            if gate.number_of_qubits() > 1:
                if not isinstance(qubit, list):
                    raise ValueError("Please provide qubit list for gates with more than one qubit.")
            else:
                if not isinstance(qubit, int):
                    raise ValueError("For single gates, give qubit as int (not list).")
            step.add_gate(qubit, gate)

        self.sequence.append(step)

    def number_of_qubits(self):
        return self.n_qubit

    def __len__(self):
        return len(self.sequence)


class CHASE_with_1qb_phases(CompositeGate):
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
        self.add_gate(CPHASE())
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


I = IdentityGate(width=None)
I0 = IdentityGate(width=0)

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
VZp = VirtualZGate(np.pi)
VZ2p = VirtualZGate(np.pi/2)
VZm = VirtualZGate(-np.pi)
VZ2m = VirtualZGate(np.pi/2)

# two-qubit gates
CPh = CPHASE()

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
CZEcho.add_gate(CPh)
CZEcho.add_gate([Xp, Xp])
CZEcho.add_gate(CPh)
CZEcho.add_gate([X2p, Xp])

NetZero = CompositeGate(n_qubit=2)
NetZero.add_gate(CPHASE(negative_amplitude=False))
NetZero.add_gate(CPHASE(negative_amplitude=True))

H = CompositeGate(n_qubit=1)
H.add_gate(VZp)
H.add_gate(Y2p)

CZ = CHASE_with_1qb_phases(0, 0)  # Start with 0, 0 as the single qubit phase shifts.

CNOT = CompositeGate(n_qubit=2)
CNOT.add_gate(H, 1)
CNOT.add_gate(CZ, [0, 1])
CNOT.add_gate(H, 1)




if __name__ == '__main__':
    pass
