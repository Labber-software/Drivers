#!/usr/bin/env python3
import logging
from copy import copy
from enum import Enum

import numpy as np

from crosstalk import Crosstalk
from gates import (CompositeGate, CustomGate, Gate, IdentityGate, ReadoutGate,
                   SingleQubitRotation, TwoQubitGate, VirtualZGate, RabiGate)
from predistortion import ExponentialPredistortion, Predistortion
from pulse import Pulse, PulseShape, PulseType
from qubits import Qubit, Transmon
from readout import Readout
from tomography import ProcessTomography, StateTomography

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
            if isinstance(gate[i], Enum):
                # We need the gate object, not the enum
                self.gates[qubit[i]] = gate[i].value
            else:
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
        self._process_tomography = ProcessTomography()

        # state tomography
        self.perform_state_tomography = False
        self._state_tomography = StateTomography()

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
            delay = IdentityGate(width=self.readout_delay)
            self.add_gate_to_all(delay, dt=0)
        self.add_gate_to_all(ReadoutGate(), dt=0, align='left')

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
        if isinstance(gate, Enum):
            gate = gate.value
        if isinstance(gate, CompositeGate):
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
            if isinstance(g, Enum):
                g = g.value
            if isinstance(g, CompositeGate):
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
            if isinstance(g, Enum):
                g = g.value
            if isinstance(g, CompositeGate):
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
                if isinstance(g, Enum):
                    g = g.value
                if isinstance(g, CompositeGate):
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


class SequenceToWaveforms:
    """Compile a multi qubit sequence into waveforms.

    Parameters
    ----------
    n_qubit : type
        The maximum number of qubits (the default is 5).

    Attributes
    ----------
    dt : float
        Pulse spacing, in seconds.
    local_xy : bool
        If False, collate all waveforms into one.
    simultaneous_pulses : bool
        If False, seperate all pulses in time.
    sample_rate : float
        AWG Sample rate.
    n_pts : float
        Number of points in the waveforms.
    first_delay : float
        Delay between start of waveform and start of the first pulse.
    trim_to_sequence : bool
        If True, adjust `n_points` to just fit the sequence.
    align_to_end : bool
        Align the whole sequence to the end of the waveforms.
        Only relevant if `trim_to_sequence` is False.
    sequences : list of :obj:`Step`
        The qubit sequences.
    qubits : list of :obj:`Qubit`
        Parameters of each qubit.
    wave_xy_delays : list of float
        Indiviudal delays for the XY waveforms.
    wave_z_delays : list of float
        Indiviudal delays for the Z waveforms.
    n_qubit

    """

    def __init__(self, n_qubit=5):
        self.n_qubit = n_qubit
        self.dt = 10E-9
        self.local_xy = True
        self.simultaneous_pulses = True

        # waveform parameter
        self.sample_rate = 1.2E9
        self.n_pts = 240E3
        self.first_delay = 100E-9
        self.trim_to_sequence = True
        self.align_to_end = False

        self.sequences = []
        self.qubits = [Qubit() for n in range(MAX_QUBIT)]

        # waveforms
        self._wave_xy = [np.zeros(0, dtype=np.complex)
                         for n in range(MAX_QUBIT)]
        self._wave_z = [np.zeros(0) for n in range(MAX_QUBIT)]
        self._wave_gate = [np.zeros(0) for n in range(MAX_QUBIT)]

        # waveform delays
        self.wave_xy_delays = np.zeros(MAX_QUBIT)
        self.wave_z_delays = np.zeros(MAX_QUBIT)

        # define pulses
        self.pulses_1qb_xy = [Pulse() for n in range(MAX_QUBIT)]
        self.pulses_1qb_z = [Pulse() for n in range(MAX_QUBIT)]
        self.pulses_2qb = [Pulse() for n in range(MAX_QUBIT - 1)]
        self.pulses_readout = [Pulse(pulse_type=PulseType.READOUT)
                               for n in range(MAX_QUBIT)]

        # cross-talk
        self.compensate_crosstalk = False
        self._crosstalk = Crosstalk()

        # predistortion
        self.perform_predistortion = False
        self._predistortions = [Predistortion(n) for n in range(MAX_QUBIT)]
        self._predistortions_z = [
            ExponentialPredistortion(n) for n in range(MAX_QUBIT)]

        # gate switch waveform
        self.generate_gate_switch = False
        self.uniform_gate = False
        self.gate_delay = 0.0
        self.gate_overlap = 20E-9
        self.minimal_gate_time = 20E-9

        # readout trig settings
        self.readout_trig_generate = False

        # readout wave object and settings
        self.readout = Readout(max_qubit=MAX_QUBIT)
        self.readout_trig = np.array([], dtype=float)
        self.readout_iq = np.array([], dtype=np.complex)

    def get_waveforms(self, sequences):
        """Compile the given sequence into waveforms.

        Parameters
        ----------
        sequences : list of :obj:`Step`
            The qubit sequence to be compiled.

        Returns
        -------
        type
            Description of returned object.

        """
        self.sequences = sequences
        self._seperate_gates()

        self._add_timings()
        self._init_waveforms()

        if self.align_to_end:
            shift = self._round((self.n_pts - 2) / self.sample_rate -
                                self.sequences[-1].t_end)
            for step in self.sequences:
                step.time_shift(shift)

        self._perform_virtual_z()
        self._generate_waveforms()
        # collapse all xy pulses to one waveform if no local XY control
        if not self.local_xy:
            # sum all waveforms to first one
            self._wave_xy[0] = np.sum(self._wave_xy[:self.n_qubit], 0)
            # clear other waveforms
            for n in range(1, self.n_qubit):
                self._wave_xy[n][:] = 0.0

        self._perform_crosstalk_compensation()
        self._predistort_waveforms()
        self._add_readout_trig()
        self._add_microwave_gate()

        # Apply offsets
        self.readout_iq += self.readout_i_offset + 1j * self.readout_q_offset

        # create and return dictionary with waveforms
        waveforms = dict()
        waveforms['xy'] = self._wave_xy
        waveforms['z'] = self._wave_z
        waveforms['gate'] = self._wave_gate
        waveforms['readout_trig'] = self.readout_trig
        waveforms['readout_iq'] = self.readout_iq
        return waveforms

    def _seperate_gates(self):
        if not self.simultaneous_pulses:
            new_sequences = []
            for step in self.sequences:
                if any(isinstance(gate, (ReadoutGate, IdentityGate))
                    for gate in step.gates):
                    # Don't seperate I gates or readouts since we do
                    # multiplexed readout
                    new_sequences.append(step)
                    continue
                for i, gate in enumerate(step.gates):
                    if gate is not None:
                        new_step = Step(n_qubit=step.n_qubit, t0=step.t0,
                                        dt=step.dt, align=step.align)
                        new_step.add_gate(i, gate)
                        new_sequences.append(new_step)
            self.sequences = new_sequences

        # Replace any missing gates with I
        for step in self.sequences:
            for i, gate in enumerate(step.gates):
                if gate is None:
                    step.gates[i] = IdentityGate(width=0)

    def _add_timings(self):
        for step in self.sequences:
            if step.dt is None and step.t0 is None:
                # Use global pulse spacing
                step.dt = self.dt
        if self.sequences[0].t0 is None:
            t_start = self.first_delay - self.sequences[0].dt

        # Longest pulse in the step needed for correct timing
        for step in self.sequences:
            max_duration = -np.inf
            for q, g in enumerate(step.gates):
                duration = 0
                if isinstance(g, IdentityGate) and g.width is not None:
                    duration = g.width
                else:
                    pulse = self._get_pulse_for_gate(q, g)
                    if pulse is not None:
                        duration = pulse.total_duration()
                if duration > max_duration:
                    max_duration = duration
            if step.t0 is None:
                step.t_start = t_start + step.dt
                if max_duration == 0:
                    step.t_start -= step.dt
            else:
                step.t_start = step.t0 - max_duration / 2
            step.t_start = self._round(step.t_start)
            step.t_end = self._round(step.t_start + max_duration)
            step.t_middle = step.t_start + max_duration / 2
            t_start = step.t_end

        # Make sure that the sequence is sorted chronologically.
        self.sequences.sort(key=lambda x: x.t_start)

        # Make sure that the sequnce start on first delay
        time_diff = self._round(self.first_delay-self.sequences[0].t_start)
        if np.abs(time_diff) > 1e-10:
            for step in self.sequences:
                step.time_shift(time_diff)

    def _get_pulse_for_gate(self, qubit, gate):
        # Virtual Z is special since it has no length
        if isinstance(gate, VirtualZGate):
            pulse = None
        # Get the corresponding pulse for other gates
        elif isinstance(gate, SingleQubitRotation):
            if gate.axis in ('X', 'Y'):
                pulse = self.pulses_1qb_xy[qubit]
            elif gate.axis == 'Z':
                pulse = self.pulses_1qb_z[qubit]
        elif isinstance(gate, IdentityGate):
            if gate.width is None:
                pulse = copy(self.pulses_1qb_xy[qubit])
            else:
                pulse = copy(self.pulses_1qb_xy[qubit])
                pulse.width = gate.width
        elif isinstance(gate, RabiGate):
            pulse = copy(self.pulses_1qb_xy[qubit])
            pulse.amplitude = gate.amplitude
            pulse.plateau = gate.plateau
            pulse.phase = gate.phase
        elif isinstance(gate, TwoQubitGate):
            pulse = self.pulses_2qb[qubit]
        elif isinstance(gate, ReadoutGate):
            pulse = self.pulses_readout[qubit]
        elif isinstance(gate, CustomGate):
            pulse = gate.pulse
        else:
            raise ValueError('Please provide a pulse for {}'.format(gate))

        return pulse

    def _predistort_waveforms(self):
        """Pre-distort the waveforms."""
        if self.perform_predistortion:
            # go through and predistort all waveforms
            n_wave = self.n_qubit if self.local_xy else 1
            for n in range(n_wave):
                self._wave_xy[n] = self._predistortions[n].predistort(
                    self._wave_xy[n])

        if self.perform_predistortion_z:
            # go through and predistort all waveforms
            for n in range(self.n_qubit):
                self._wave_z[n] = self._predistortions_z[n].predistort(
                    self._wave_z[n])

    def _perform_crosstalk_compensation(self):
        """Compensate for Z-control crosstalk."""
        if not self.compensate_crosstalk:
            return
        self._wave_z = self._crosstalk.compensate(self._wave_z)

    def _perform_virtual_z(self):
        """Shifts the phase of pulses subsequent to virutal z gates."""
        for qubit in range(self.n_qubit):
            phase = 0
            for m, step in enumerate(self.sequences):
                gate = step.gates[qubit]
                if isinstance(gate, VirtualZGate):
                    phase += gate.angle
                    continue
                if not isinstance(gate, ReadoutGate):
                    step.gates[qubit] = gate.add_phase(phase)

    def _add_microwave_gate(self):
        """Create waveform for gating microwave switch."""
        if not self.generate_gate_switch:
            return
        n_wave = self.n_qubit if self.local_xy else 1
        # go through all waveforms
        for n, wave in enumerate(self._wave_xy[:n_wave]):
            if self.uniform_gate:
                # the uniform gate is all ones
                gate = np.ones_like(wave)
                # if creating readout trig, turn off gate during readout
                if self.readout_trig_generate:
                    gate[-int((self.readout_trig_duration -
                               self.gate_overlap -
                               self.gate_delay) * self.sample_rate):] = 0.0
            else:
                # non-uniform gate, find non-zero elements
                gate = np.array(np.abs(wave) > 0.0, dtype=float)
                # fix gate overlap
                n_overlap = int(np.round(self.gate_overlap * self.sample_rate))
                diff_gate = np.diff(gate)
                indx_up = np.nonzero(diff_gate > 0.0)[0]
                indx_down = np.nonzero(diff_gate < 0.0)[0]
                # add extra elements to left and right for overlap
                for indx in indx_up:
                    gate[max(0, indx - n_overlap):(indx + 1)] = 1.0
                for indx in indx_down:
                    gate[indx:(indx + n_overlap + 1)] = 1.0

                # fix gaps in gate shorter than min (look for 1>0)
                diff_gate = np.diff(gate)
                indx_up = np.nonzero(diff_gate > 0.0)[0]
                indx_down = np.nonzero(diff_gate < 0.0)[0]
                # ignore first transition if starting in zero
                if gate[0] == 0:
                    indx_up = indx_up[1:]
                n_down_up = min(len(indx_down), len(indx_up))
                len_down = indx_up[:n_down_up] - indx_down[:n_down_up]
                # find short gaps
                short_gaps = np.nonzero(len_down < (self.minimal_gate_time *
                                                    self.sample_rate))[0]
                for indx in short_gaps:
                    gate[indx_down[indx]:(1 + indx_up[indx])] = 1.0

                # shift gate in time
                n_shift = int(np.round(self.gate_delay * self.sample_rate))
                if n_shift < 0:
                    n_shift = abs(n_shift)
                    gate = np.r_[gate[n_shift:], np.zeros((n_shift,))]
                elif n_shift > 0:
                    gate = np.r_[np.zeros((n_shift,)), gate[:(-n_shift)]]
            # make sure gate starts/ends in 0
            gate[0] = 0.0
            gate[-1] = 0.0
            # store results
            self._wave_gate[n] = gate

    def _round(self, t, acc=1E-12):
        """Round the time `t` with a certain accuarcy `acc`.

        Parameters
        ----------
        t : float
            The time to be rounded.
        acc : float
            The accuarcy (the default is 1E-12).

        Returns
        -------
        float
            The rounded time.

        """
        return int(np.round(t / acc)) * acc

    def _add_readout_trig(self):
        """Create waveform for readout trigger."""
        if not self.readout_trig_generate:
            return
        trig = np.zeros_like(self.readout_iq)
        start = (np.abs(self.readout_iq) > 0.0).nonzero()[0][0]
        end = int(np.min((start +
                          self.readout_trig_duration * self.sample_rate,
                          self.n_pts_readout)))
        trig[start:end] = self.readout_trig_amplitude

        # make sure trig starts and ends in 0.
        trig[0] = 0.0
        trig[-1] = 0.0
        self.readout_trig = trig

    def _init_waveforms(self):
        """Initialize waveforms according to sequence settings."""
        # To keep the first pulse delay, use the smallest delay as reference.
        min_delay = np.min([self.wave_xy_delays[:self.n_qubit],
                            self.wave_z_delays[:self.n_qubit]])
        self.wave_xy_delays -= min_delay
        self.wave_z_delays -= min_delay
        max_delay = np.max([self.wave_xy_delays[:self.n_qubit],
                            self.wave_z_delays[:self.n_qubit]])

        # find the end of the sequence
        # only include readout in size estimate if all waveforms have same size
        if self.readout_match_main_size:
            end = np.max([s.t_end for s in self.sequences]) + max_delay
        else:
            end = np.max([s.t_end for s in self.sequences[0:-1]]) + max_delay

        # create empty waveforms of the correct size
        if self.trim_to_sequence:
            self.n_pts = int(np.ceil(end * self.sample_rate)) + 1
            if self.n_pts % 2 == 1:
                # Odd n_pts give spectral leakage in FFT
                self.n_pts += 1
        for n in range(self.n_qubit):
            self._wave_xy[n] = np.zeros(self.n_pts, dtype=np.complex)
            self._wave_z[n] = np.zeros(self.n_pts, dtype=float)
            self._wave_gate[n] = np.zeros(self.n_pts, dtype=float)

        # Waveform time vector
        self.t = np.arange(self.n_pts) / self.sample_rate

        # readout trig and i/q waveforms
        if self.readout_match_main_size:
            # same number of points for readout and main waveform
            self.n_pts_readout = self.n_pts
        else:
            # different number of points for readout and main waveform
            self.n_pts_readout = 1 + int(
                np.ceil(self.sample_rate *
                (self.sequences[-1].t_end - self.sequences[-1].t_start)))
            if self.n_pts_readout % 2 == 1:
                # Odd n_pts give spectral leakage in FFT
                self.n_pts_readout += 1

        self.readout_trig = np.zeros(self.n_pts_readout, dtype=float)
        self.readout_iq = np.zeros(self.n_pts_readout, dtype=np.complex)

    def _generate_waveforms(self):
        """Generate the waveforms corresponding to the sequence."""
        # find out if CZ pulses are used, if so pre-calc envelope to save time
        pulses_cz = set()
        # find set of all CZ pulses in use
        for step in self.sequences:
            for qubit, gate in enumerate(step.gates):
                pulse = self._get_pulse_for_gate(qubit, gate)
                if pulse is not None and pulse.shape == PulseShape.CZ:
                    pulses_cz.add(pulse)
        # once we've gone through all pulses, pre-calculate the waveforms
        for pulse in pulses_cz:
            pulse.calculate_cz_waveform()

        for step in self.sequences:
            for qubit, gate in enumerate(step.gates):
                pulse = self._get_pulse_for_gate(qubit, gate)
                if pulse is None:
                    continue
                if pulse.pulse_type == PulseType.Z:
                    waveform = self._wave_z[qubit]
                    delay = self.wave_z_delays[qubit]
                elif pulse.pulse_type == PulseType.XY:
                    waveform = self._wave_xy[qubit]
                    delay = self.wave_xy_delays[qubit]
                elif pulse.pulse_type == PulseType.READOUT:
                    waveform = self.readout_iq
                    delay = 0

                # get the range of indices in use
                if (pulse.pulse_type == PulseType.READOUT and not
                        self.readout_match_main_size):
                    # special case for readout if not matching main wave size
                    start = 0.0
                    middle = self._round(step.t_middle - step.t_start)
                    end = self._round(step.t_end - step.t_start)
                else:
                    start = self._round(step.t_start + delay)
                    middle = self._round(step.t_middle + delay)
                    end = self._round(step.t_end + delay)

                indices = np.arange(
                    max(np.floor(start * self.sample_rate), 0),
                    min(np.ceil(end * self.sample_rate), len(waveform)),
                    dtype=int
                )

                # return directly if no indices
                if len(indices) == 0:
                    continue

                # calculate time values for the pulse indices
                t = indices / self.sample_rate
                max_duration = end - start
                if step.align == 'center':
                    t0 = middle
                elif step.align == 'left':
                    t0 = middle - (max_duration - pulse.total_duration()) / 2
                elif step.align == 'right':
                    t0 = middle + (max_duration - pulse.total_duration()) / 2
                # calculate the pulse waveform for the selected indices
                waveform[indices] += gate.get_waveform(pulse, t0, t)

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
        self.dt = config.get('Pulse spacing')
        self.local_xy = config.get('Local XY control')
        self.simultaneous_pulses = config.get('Simultaneous pulses')

        # waveform parameters
        self.sample_rate = config.get('Sample rate')
        self.n_pts = int(config.get('Number of points', 0))
        self.first_delay = config.get('First pulse delay')
        self.trim_to_sequence = config.get('Trim waveform to sequence')
        self.trim_start = config.get('Trim both start and end')
        self.align_to_end = config.get('Align pulses to end of waveform')

        # qubit spectra
        for n in range(self.n_qubit):
            m = n + 1  # pulses are indexed from 1 in Labber
            qubit = Transmon(config.get('f01 max #{}'.format(m)),
                             config.get('f01 min #{}'.format(m)),
                             config.get('Ec #{}'.format(m)),
                             config.get('Vperiod #{}'.format(m)),
                             config.get('Voffset #{}'.format(m)),
                             config.get('V0 #{}'.format(m)),)
            self.qubits[n] = qubit

        # single-qubit pulses XY
        for n, pulse in enumerate(self.pulses_1qb_xy):
            m = n + 1  # pulses are indexed from 1 in Labber
            # global parameters
            pulse.shape = PulseShape(config.get('Pulse type'))
            pulse.truncation_range = config.get('Truncation range')
            pulse.start_at_zero = config.get('Start at zero')
            pulse.use_drag = config.get('Use DRAG')
            pulse.pulse_type = PulseType.XY
            # pulse shape
            if config.get('Uniform pulse shape'):
                pulse.width = config.get('Width')
                pulse.plateau = config.get('Plateau')
            else:
                pulse.width = config.get('Width #%d' % m)
                pulse.plateau = config.get('Plateau #%d' % m)

            if config.get('Uniform amplitude'):
                pulse.amplitude = config.get('Amplitude')
            else:
                pulse.amplitude = config.get('Amplitude #%d' % m)

            # pulse-specific parameters
            pulse.frequency = config.get('Frequency #%d' % m)
            pulse.drag_coefficient = config.get('DRAG scaling #%d' % m)
            pulse.drag_detuning = config.get('DRAG frequency detuning #%d' % m)

        # single-qubit pulses Z
        for n, pulse in enumerate(self.pulses_1qb_z):
            # pulses are indexed from 1 in Labber
            m = n + 1
            # global parameters
            pulse.shape = PulseShape(config.get('Pulse type, Z'))
            pulse.truncation_range = config.get('Truncation range, Z')
            pulse.start_at_zero = config.get('Start at zero, Z')
            pulse.pulse_type = PulseType.Z
            # pulse shape
            if config.get('Uniform pulse shape, Z'):
                pulse.width = config.get('Width, Z')
                pulse.plateau = config.get('Plateau, Z')
            else:
                pulse.width = config.get('Width #%d, Z' % m)
                pulse.plateau = config.get('Plateau #%d, Z' % m)

            if config.get('Uniform amplitude, Z'):
                pulse.amplitude = config.get('Amplitude, Z')
            else:
                pulse.amplitude = config.get('Amplitude #%d, Z' % m)

        # two-qubit pulses
        for n, pulse in enumerate(self.pulses_2qb):
            # pulses are indexed from 1 in Labber
            s = ' #%d%d' % (n + 1, n + 2)
            # global parameters
            pulse.shape = PulseShape(config.get('Pulse type, 2QB'))
            pulse.pulse_type = PulseType.Z

            if config.get('Pulse type, 2QB') == 'CZ':
                pulse.F_Terms = d[config.get('Fourier terms, 2QB')]
                if config.get('Uniform 2QB pulses'):
                    pulse.width = config.get('Width, 2QB')
                    pulse.plateau = config.get('Plateau, 2QB')
                else:
                    pulse.width = config.get('Width, 2QB' + s)
                    pulse.plateau = config.get('Plateau, 2QB')

                # spectra
                if config.get('Assume linear dependence' + s, True):
                    pulse.qubit = None
                else:
                    pulse.qubit = self.qubits[n]

                # Get Fourier values
                if d[config.get('Fourier terms, 2QB')] == 4:
                    pulse.Lcoeff = np.array([config.get('L1, 2QB' + s),
                                             config.get('L2, 2QB' + s),
                                             config.get('L3, 2QB' + s),
                                             config.get('L4, 2QB' + s)])
                elif d[config.get('Fourier terms, 2QB')] == 3:
                    pulse.Lcoeff = np.array([config.get('L1, 2QB' + s),
                                             config.get('L2, 2QB' + s),
                                             config.get('L3, 2QB' + s)])
                elif d[config.get('Fourier terms, 2QB')] == 2:
                    pulse.Lcoeff = np.array([config.get('L1, 2QB' + s),
                                             config.get('L2, 2QB' + s)])
                elif d[config.get('Fourier terms, 2QB')] == 1:
                    pulse.Lcoeff = np.array([config.get('L1, 2QB' + s)])

                pulse.Coupling = config.get('Coupling, 2QB' + s)
                pulse.Offset = config.get('f11-f20 initial, 2QB' + s)
                pulse.amplitude = config.get('f11-f20 final, 2QB' + s)
                pulse.dfdV = config.get('df/dV, 2QB' + s)
                pulse.negative_amplitude = config.get('Negative amplitude' + s)

            else:
                pulse.truncation_range = config.get('Truncation range, 2QB')
                pulse.start_at_zero = config.get('Start at zero, 2QB')
                # pulse shape
                if config.get('Uniform 2QB pulses'):
                    pulse.width = config.get('Width, 2QB')
                    pulse.plateau = config.get('Plateau, 2QB')
                else:
                    pulse.width = config.get('Width, 2QB' + s)
                    pulse.plateau = config.get('Plateau, 2QB' + s)
                # pulse-specific parameters
                pulse.amplitude = config.get('Amplitude, 2QB' + s)

            Gate.CZ.value.new_angles(config.get('QB1 Phi 2QB #12'),
                                     config.get('QB2 Phi 2QB #12'))

        # predistortion
        self.perform_predistortion = config.get('Predistort waveforms', False)
        # update all predistorting objects
        for p in self._predistortions:
            p.set_parameters(config)

        # Z predistortion
        self.perform_predistortion_z = config.get('Predistort Z')
        for p in self._predistortions_z:
            p.set_parameters(config)

        # crosstalk
        self.compensate_crosstalk = config.get('Compensate cross-talk', False)
        self._crosstalk.set_parameters(config)

        # gate switch waveform
        self.generate_gate_switch = config.get('Generate gate')
        self.uniform_gate = config.get('Uniform gate')
        self.gate_delay = config.get('Gate delay')
        self.gate_overlap = config.get('Gate overlap')
        self.minimal_gate_time = config.get('Minimal gate time')

        # readout
        self.readout_match_main_size = config.get(
            'Match main sequence waveform size')
        self.readout_i_offset = config.get('Readout offset - I')
        self.readout_q_offset = config.get('Readout offset - Q')
        self.readout_trig_generate = config.get('Generate readout trig')
        self.readout_trig_amplitude = config.get('Readout trig amplitude')
        self.readout_trig_duration = config.get('Readout trig duration')
        self.readout_predistort = config.get('Predistort readout waveform')
        self.readout.set_parameters(config)

        # get readout pulse parameters
        phases = 2 * np.pi * np.array([0.8847060, 0.2043214, 0.9426104,
                                       0.6947334, 0.8752361, 0.2246747,
                                       0.6503154, 0.7305004, 0.1309068])
        for n, pulse in enumerate(self.pulses_readout):
            # pulses are indexed from 1 in Labber
            m = n + 1
            pulse.shape = PulseShape(config.get('Readout pulse type'))
            pulse.truncation_range = config.get('Readout truncation range')
            pulse.start_at_zero = config.get('Readout start at zero')
            pulse.iq_skew = config.get('Readout IQ skew') * np.pi / 180
            pulse.iq_ratio = config.get('Readout I/Q ratio')

            if config.get('Distribute readout phases'):
                pulse.phase = phases[n]
            else:
                pulse.phase = 0

            if config.get('Uniform readout pulse shape'):
                pulse.width = config.get('Readout width')
                pulse.plateau = config.get('Readout duration')
            else:
                pulse.width = config.get('Readout width #%d' % m)
                pulse.plateau = config.get('Readout duration #%d' % m)

            if config.get('Uniform readout amplitude') is True:
                pulse.amplitude = config.get('Readout amplitude')
            else:
                pulse.amplitude = config.get('Readout amplitude #%d' % (n + 1))

            pulse.frequency = config.get('Readout frequency #%d' % m)

        # Delays
        self.wave_xy_delays = np.zeros(self.n_qubit)
        self.wave_z_delays = np.zeros(self.n_qubit)
        for n in range(self.n_qubit):
            m = n + 1
            self.wave_xy_delays[n] = config.get('Qubit %d XY Delay' % m)
            self.wave_z_delays[n] = config.get('Qubit %d Z Delay' % m)


if __name__ == '__main__':
    pass
