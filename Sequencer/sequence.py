#!/usr/bin/env python3
import logging
from copy import copy
import numpy as np

import gates
import tomography

# Allow logging to Labber's instrument log
log = logging.getLogger('LabberDriver')

# Maximal number of qubits controllable by this class
MAX_QUBIT = 9


class Step:
    """Represent one step in a sequence.

    Parameters
    ----------
    n_qubit : int
        Number of qubits in the sequece (the default is MAX_QUBIT).
    t0 : float
        Start of the sequence in seconds (the default is None).
    dt : float
        End of the sequence in seconds (the default is None).
    align : str {'left', 'center', 'right'}
        The alignment of pulses if they have different lengths,
        (the default is 'center').

    Attributes
    ----------
    gates : list of :obj:`BaseGate`
        The different gates in the step.
    t_middle : float
        Center of the sequence in seconds.

    """

    def __init__(self, n_qubit=MAX_QUBIT, t0=None, dt=None, align='center'):
        self.n_qubit = n_qubit
        self.gates = [None for n in range(self.n_qubit)]
        self.align = align
        self.t0 = t0
        self.dt = dt
        self.t_start = None
        self.t_end = None
        self.t_middle = None

    def add_gate(self, qubit, gate):
        """Add the given gate(s) to the specified qubit(s).

        The number of gates must equal the number of qubits.

        If the number of qubits given are less than the number of qubits in the
        step, I gates are added to the other qubits.
        Parameters
        ----------
        qubit : int or list of int
            The qubit indices.
        gate : :obj:`BaseGate` or list of :obj:`BaseGate`
            The gate(s).

        """
        if not isinstance(qubit, list):
            qubit = [qubit]
        if not isinstance(gate, list):
            gate = [gate]
        for i in range(len(gate)):
            self.gates[qubit[i]] = gate[i]

    def time_shift(self, shift):
        """Shift the timings of the step.

        Parameters
        ----------
        shift : float
            The amount of shift to apply in seconds.

        """
        self.t_start += shift
        self.t_middle += shift
        self.t_end += shift


class Sequence:
    """A multi qubit seqence.

    Parameters
    ----------
    n_qubit : type
        The number of qubits in the sequence (the default is 5).

    Attributes
    ----------
    sequences : list of :obj:`Step`
        Holds the steps of the sequence.
    perform_process_tomography : bool
        Flag for performing process tomography.
    perform_state_tomography : bool
        Flag for performing state tomography.
    readout_delay : float
        Delay time between last pulse and readout, in seconds.
    n_qubit

    """

    def __init__(self, n_qubit=5):
        self.n_qubit = n_qubit

        self.sequences = []

        # process tomography
        self.perform_process_tomography = False
        self._process_tomography = tomography.ProcessTomography()

        # state tomography
        self.perform_state_tomography = False
        self._state_tomography = tomography.StateTomography()

        # readout
        self.readout_delay = 0.0

    # Public methods
    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms.

        Parameters
        ----------
        config : dict
            Configuration as defined by Labber driver configuration window.

        """
        # this function should be overloaded by specific sequence
        pass

    def get_sequence(self, config):
        """Compile sequence and return it.

        Parameters
        ----------
        config : dict
            Labber instrument configuration.

        Returns
        -------
        list of :obj:`Step`
            The compiled qubit sequence.

        """
        self.sequences = []

        if self.perform_process_tomography:
            self._process_tomography.add_pulses(self)

        self.generate_sequence(config)

        if self.perform_state_tomography:
            self._state_tomography.add_pulses(self)

        if self.readout_delay > 0:
            delay = gates.IdentityGate(width=self.readout_delay)
            self.add_gate_to_all(delay, dt=0)
        self.add_gate_to_all(gates.ReadoutGate(), dt=0, align='left')

        return self.sequences

    # Public methods for adding pulses and gates to the sequence.
    def add_single_pulse(self, qubit, pulse, t0=None, dt=None,
                         align_left=False):
        """Add single qubit pulse to specified qubit.

        This function still exist to not break existing
        funcationallity. You should really use the add_gate method.

        t0 or dt can be used to override the global pulse spacing.

        Parameters
        ----------
        qubit : int
            Qubit number, indexed from 0.

        pulse : :obj:`Pulse`
            Definition of pulse to add.

        t0 : float, optional
            Absolute pulse position.

        dt : float, optional
            Pulse spacing, referenced to the previous pulse.

        align_left: bool, optional
            If True, aligns the pulse to the left. Defaults to False.

        """
        gate = CustomGate(pulse)
        if align_left is True:
            self.add_gate(qubit, gate, t0, dt, 'left')
        else:
            self.add_gate(qubit, gate, t0, dt, 'center')

    def add_single_gate(self, qubit, gate, t0=None, dt=None, align_left=False):
        """Add single gate to specified qubit sequence.

        Note, this function still exist is to not break existing
        funcationallity. You should really use the add_gate method.

        t0 or dt can be used to override the global pulse spacing.

        Parameters
        ----------
        qubit : int
            Qubit number, indexed from 0.

        gate : :obj:`Gate`
            Definition of gate to add.

        t0 : float, optional
            Absolute pulse position.

        dt : float, optional
            Pulse spacing, referenced to the previous pulse.

        align_left : boolean, optional
            If True, t0 is the start of the pulse, otherwise it is the center
            of the pulse. False is the default.

        """
        if align_left is True:
            self.add_gate(qubit, gate, t0, dt, 'left')
        else:
            self.add_gate(qubit, gate, t0, dt, 'center')

    def add_gate(self, qubit, gate, t0=None, dt=None, align='center'):
        """Add a set of gates to the given qubit sequences.

        For the qubits with no specificied gate, an IdentityGate will be given.
        The length of the step is given by the longest pulse.

        Parameters
        ----------
        qubit : int or list of int
            The qubit(s) to add the gate(s) to.
        gate : :obj:`BaseGate` or list of :obj:`BaseGate`
            The gate(s) to add.
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
        if isinstance(gate, gates.CompositeGate):
            self._add_composite_gate(qubit, gate, t0, dt, align)
            return
        if not isinstance(qubit, list):
            qubit = [qubit]
        if not isinstance(gate, list):
            gate = [gate]
        if len(gate) != len(qubit):
            raise ValueError('Length of qubit and gate list must be equal.')

        # If any of the gates is a composite gate, special care is needed
        for g in gate:
            if isinstance(g, gates.CompositeGate):
                self._add_multiple_composite_gates(qubit, gate, t0, dt, align)
                return

        self._add_step(qubit, gate, t0, dt, align)

    def add_gate_to_all(self, gate, t0=None, dt=None, align='center'):
        """Add a single gate to all qubits.

        Pulses are added at the end
        of the sequence, with the gate spacing set by the spacing parameter.
        """
        self.add_gate([n for n in range(self.n_qubit)],
                      [gate for n in range(self.n_qubit)], t0=t0, dt=dt,
                      align=align)

    def add_gates(self, gates):
        """Add multiple gates to the qubit waveform.

        Pulses are added at the end of the sequence, with the gate spacing set
        by the spacing parameter.

        Examples
        --------
        Add three gates to a two-qubit sequence, first a positive pi-pulse
        around X to qubit 1, then a negative pi/2-pulse to qubit 2, finally
        simultaneous positive pi-pulses to qubits 1 and 2.

        >>> add_gates([[Gate.Xp,  None    ],
                       [None,     Gate.Y2m],
                       [Gate.Xp,  Gate.Xp]])

        Parameters
        ----------
        gates : list of list of :obj:`BaseGate`
            List of lists defining gates to add. The innermost list should
            have the same length as number of qubits in the sequence.

        """
        # make sure we have correct input
        if not isinstance(gates, (list, tuple)):
            raise Exception('The input must be a list of list with gates')
        if len(gates) == 0:
            return
        if not isinstance(gates[0], (list, tuple)):
            raise Exception('The input must be a list of list with gates')
        # add gates sequence to waveforms
        for gates_qubits in gates:
            # add gate to specific qubit waveform
            self.add_gate([n for n in range(len(gates_qubits))], gates_qubits)

    # Internal methods for adding pulses and gates to the sequence.
    def _add_step(self, qubit, gate, t0=None, dt=None, align='center'):
        """Turn the given gates into a step and append to sequence.

        Parameters
        ----------
        qubit : int or list of int
            The target qubits.
        gate : :obj:`BaseGate` or list of :obj:`BaseGate`
            Gates to be added to sequence.
        t0 : float, optional
            If specified, the time position of the gates (the default is None).
        dt : float, optional
            If specified, overwrites the global spacing between the previous
            pulse and the new (the default is None).
        align : str, optional
            If two or more qubits have differnt pulse lengths, `align`
            specifies how those pulses should be aligned. 'Left' aligns the
            start, 'center' aligns the centers, and 'right' aligns the end,
            (the default is 'center').

        """
        if not isinstance(qubit, list):
            qubit = [qubit]
        if not isinstance(gate, list):
            gate = [gate]

        step = Step(self.n_qubit, t0=t0, dt=dt, align=align)
        step.add_gate(qubit, gate)

        self.sequences.append(step)

    def _add_composite_gate(self, qubit, gate, t0=None, dt=None,
                            align='center'):
        """Add a composite gate to the sequence."""
        if isinstance(qubit, int):
            qubit = [qubit]
        if len(qubit) != gate.n_qubit:
            raise ValueError('For composite gates the length of the qubit \
            list must match the number of qubits in the composite gate.')

        for i in range(len(gate)):
            self.add_gate(qubit, gate.get_gate_at_index(i))

    def _add_multiple_composite_gates(self, qubit, gate, t0=None, dt=None,
                                      align='center'):
        """Add multiple composite gates to the sequence.

        The composite gates need
        to have the same length. Single qubit gates are also allowed, and will
        be padded with I gates to have the same length as the composite gate.
        """
        gate_length = 0
        for i, g in enumerate(gate):
            if isinstance(g, gates.CompositeGate):
                if gate_length == 0:
                    gate_length = len(g)
                elif gate_length != len(g):
                    raise ValueError(
                        'For now, composite gates added at the same time needs'
                        ' to have the same length')

        sequence = []
        for i in range(gate_length):
            step = [Gate.I for n in range(self.n_qubit)]
            for q, g in zip(qubit, gate):
                if isinstance(g, gates.CompositeGate):
                    for k, G in enumerate(g.get_gate_at_index(i)):
                        if isinstance(q, int):
                            q = [q]
                        step[q[k]] = G
                else:
                    step[q] = g
            sequence.append(step)
        self.add_gates(sequence)

    def set_parameters(self, config={}):
        """Set base parameters using config from from Labber driver.

        Parameters
        ----------
        config : dict
            Configuration as defined by Labber driver configuration window

        """
        # sequence parameters
        d = dict(Zero=0, One=1, Two=2, Three=3, Four=4, Five=5, Six=6, Seven=7,
                 Eight=8, Nine=9)
        self.n_qubit = d[config.get('Number of qubits')]

        # Readout
        self.readout_delay = config.get('Readout delay')

        # process tomography prepulses
        self.perform_process_tomography = \
            config.get('Generate process tomography prepulse', False)
        self._process_tomography.set_parameters(config)

        # state tomography
        self.perform_state_tomography = config.get(
            'Generate state tomography postpulse', False)
        self._state_tomography.set_parameters(config)


if __name__ == '__main__':
    pass
