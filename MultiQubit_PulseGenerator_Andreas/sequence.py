#!/usr/bin/env python3
import logging
from copy import copy

import numpy as np

import gates
import pulses
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
        raise NotImplementedError()

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

        # waveforms
        self._wave_xy = [np.zeros(0, dtype=np.complex)
                         for n in range(MAX_QUBIT)]

        # define pulses
        self.pulses_1qb_xy = [None]*MAX_QUBIT
        self.pulses_2qb = [None]*MAX_QUBIT
        self.pulses_readout = [None]*MAX_QUBIT

        # readout trig settings
        self.readout_trig_generate = False

        # readout wave object and settings
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

        self._add_readout_trig()

        # create and return dictionary with waveforms
        waveforms = dict()
        waveforms['xy'] = self._wave_xy
        waveforms['readout_trig'] = self.readout_trig
        waveforms['readout_iq'] = self.readout_iq
        return waveforms

    def _seperate_gates(self):
        if not self.simultaneous_pulses:
            new_sequences = []
            for step in self.sequences:
                if any(isinstance(gate, (gates.ReadoutGate, gates.IdentityGate))
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
        t_start = 0
        # Longest pulse in the step needed for correct timing
        for step in self.sequences:
            max_duration = -np.inf
            for q, g in enumerate(step.gates):
                duration = 0
                if isinstance(g, gates.IdentityGate) and g.width is not None:
                    duration = g.width
                else:
                    pulse = self._get_pulse_for_gate(q, g)
                    if pulse is not None:
                        duration = pulse.total_duration()
                if duration > max_duration:
                    max_duration = duration
            if step.t0 is None:
                step.t_start = t_start + step.dt
            else:
                step.t_start = step.t0 - max_duration / 2
            step.t_start = self._round(step.t_start)
            step.t_end = self._round(step.t_start + max_duration)
            step.t_middle = step.t_start + max_duration / 2
            t_start = step.t_end # Next step starts where this one ends

        # Make sure that the sequence is sorted chronologically.
        self.sequences.sort(key=lambda x: x.t_start)

        # Make sure that the sequnce start on first delay
        time_diff = self._round(self.first_delay-self.sequences[0].t_start)
        for step in self.sequences:
            step.time_shift(time_diff)

    def _get_pulse_for_gate(self, qubit, gate):
        # Virtual Z is special since it has no length
        if isinstance(gate, gates.VirtualZGate):
            pulse = None
        # Get the corresponding pulse for other gates
        elif isinstance(gate, gates.SingleQubitXYRotation):
            pulse = gate.get_adjusted_pulse(self.pulses_1qb_xy[qubit])
        elif isinstance(gate, gates.IdentityGate):
            pulse = gate.get_adjusted_pulse(self.pulses_1qb_xy[qubit])
        elif isinstance(gate, gates.RabiGate):
            pulse = gate.get_adjusted_pulse(self.pulses_1qb_xy[qubit])
        elif isinstance(gate, gates.TwoQubitGate):
            pulse = gate.get_adjusted_pulse(self.pulses_2qb[qubit])
        elif isinstance(gate, gates.ReadoutGate):
            pulse = gate.get_adjusted_pulse(self.pulses_readout[qubit])
        elif isinstance(gate, gates.CustomGate):
            pulse = gate.get_adjusted_pulse(gate.pulse)
        else:
            raise ValueError('Please provide a pulse for {}'.format(gate))

        return pulse

    def _perform_virtual_z(self):
        """Shifts the phase of pulses subsequent to virutal z gates."""
        for qubit in range(self.n_qubit):
            phase = 0
            for m, step in enumerate(self.sequences):
                gate = step.gates[qubit]
                if isinstance(gate, gates.VirtualZGate):
                    phase += gate.angle
                    continue
                if not isinstance(gate, gates.ReadoutGate):
                    step.gates[qubit] = gate.add_phase(phase)

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

        # find the end of the sequence
        # only include readout in size estimate if all waveforms have same size
        if self.readout_match_main_size:
            end = np.max([s.t_end for s in self.sequences])
        else:
            end = np.max([s.t_end for s in self.sequences[0:-1]])

        # create empty waveforms of the correct size
        if self.trim_to_sequence:
            self.n_pts = int(np.ceil(end * self.sample_rate)) + 1
            if self.n_pts % 2 == 1:
                # Odd n_pts give spectral leakage in FFT
                self.n_pts += 1
        for n in range(self.n_qubit):
            self._wave_xy[n] = np.zeros(self.n_pts, dtype=np.complex)

        # Waveform time vector
        self.t = np.arange(self.n_pts) / self.sample_rate

        # readout trig and i/q waveforms
        if self.readout_match_main_size:
            # same number of points for readout and main waveform
            self.n_pts_readout = self.n_pts
        else:
            # different number of points for readout and main waveform
            self.n_pts_readout = 1 + int(
                np.ceil(
                    self.sample_rate *
                    (self.sequences[-1].t_end - self.sequences[-1].t_start))
                )
            if self.n_pts_readout % 2 == 1:
                # Odd n_pts give spectral leakage in FFT
                self.n_pts_readout += 1

        self.readout_trig = np.zeros(self.n_pts_readout, dtype=float)
        self.readout_iq = np.zeros(self.n_pts_readout, dtype=np.complex)

    def _generate_waveforms(self):
        """Generate the waveforms corresponding to the sequence."""
        for step in self.sequences:
            for qubit, gate in enumerate(step.gates):
                pulse = self._get_pulse_for_gate(qubit, gate)
                if pulse is None:
                    continue
                if isinstance(gate,
                             (gates.SingleQubitXYRotation, gates.IdentityGate)):
                    waveform = self._wave_xy[qubit]
                elif isinstance(gate, gates.ReadoutGate):
                    waveform = self.readout_iq

                # get the range of indices in use
                if (isinstance(gate, gates.ReadoutGate) and not
                        self.readout_match_main_size):
                    # special case for readout if not matching main wave size
                    start = 0.0
                    middle = self._round(step.t_middle - step.t_start)
                    end = self._round(step.t_end - step.t_start)
                else:
                    start = self._round(step.t_start)
                    middle = self._round(step.t_middle)
                    end = self._round(step.t_end)

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

        # single-qubit pulses XY
        for n in range(MAX_QUBIT):
            m = n + 1  # pulses are indexed from 1 in Labber
            # global parameters
            pulse = (getattr(pulses, config.get('Pulse type'))
                     (complex=True))

            pulse.truncation_range = config.get('Truncation range')
            pulse.start_at_zero = config.get('Start at zero')
            pulse.use_drag = config.get('Use DRAG')

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
            self.pulses_1qb_xy[n] = pulse

        # two-qubit pulses
        # for n, pulse in enumerate(self.pulses_2qb):
        #     # pulses are indexed from 1 in Labber
        #     s = ' #%d%d' % (n + 1, n + 2)
        #     # global parameters
        #     pulse.shape = PulseShape(config.get('Pulse type, 2QB'))
        #     pulse.pulse_type = PulseType.REAL
        #
        #     pulse.truncation_range = config.get('Truncation range, 2QB')
        #     pulse.start_at_zero = config.get('Start at zero, 2QB')
        #     # pulse shape
        #     if config.get('Uniform 2QB pulses'):
        #         pulse.width = config.get('Width, 2QB')
        #         pulse.plateau = config.get('Plateau, 2QB')
        #     else:
        #         pulse.width = config.get('Width, 2QB' + s)
        #         pulse.plateau = config.get('Plateau, 2QB' + s)
        #     # pulse-specific parameters
        #     pulse.amplitude = config.get('Amplitude, 2QB' + s)

        # readout
        self.readout_match_main_size = config.get(
            'Match main sequence waveform size')
        self.readout_trig_generate = config.get('Generate readout trig')
        self.readout_trig_amplitude = config.get('Readout trig amplitude')
        self.readout_trig_duration = config.get('Readout trig duration')

        # get readout pulse parameters
        phases = 2 * np.pi * np.array([0.8847060, 0.2043214, 0.9426104,
                                       0.6947334, 0.8752361, 0.2246747,
                                       0.6503154, 0.7305004, 0.1309068])
        for n in range(MAX_QUBIT):
            # pulses are indexed from 1 in Labber
            m = n + 1
            pulse = (getattr(pulses, config.get('Readout pulse type'))
                     (complex=True))
            pulse.truncation_range = config.get('Readout truncation range')
            pulse.start_at_zero = config.get('Readout start at zero')

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
            self.pulses_readout[n] = pulse


if __name__ == '__main__':
    pass
