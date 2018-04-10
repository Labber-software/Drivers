#!/usr/bin/env python3
import numpy as np
from copy import copy

from pulse import PulseShape, Pulse, PulseType
from predistortion import Predistortion
from crosstalk import Crosstalk
from readout import Readout
from gates import *
from tomography import Tomography
from enum import Enum

# add logger, to allow logging to Labber's instrument log
import logging
log = logging.getLogger('LabberDriver')


# Maximal number of qubits controllable by this class
MAX_QUBIT = 9
# TODO (simon): Update two-qubit pulse to include phase correction,
# compensation pulses to neighboring qubits, etc.


class Step:
    def __init__(self, n_qubit=MAX_QUBIT, t_start=0, t_end=0, align='right'):
        self.n_qubit = n_qubit
        self.gates = [Gate.I.value for n in range(self.n_qubit)]
        self.align = align
        self.t_start = t_start
        self.t_end = t_end
        self.t_middle = t_end-(t_end-t_start)/2

    def add_gate(self, qubit, gate):
        if not isinstance(qubit, list):
            qubit = [qubit]
        if not isinstance(gate, list):
            gate = [gate]
        for i in range(len(gate)):
            # We need the gate object, not the enum
            if isinstance(gate[i], Enum):
                self.gates[qubit[i]] = gate[i].value
            else:
                self.gates[qubit[i]] = gate[i]


class Sequence(object):
    """This class represents a multi-qubit control sequence

    The class supports two ways of defining pulse sequences:

    (1) Use the functions `add_single_pulse` or `add_single_gate` to add pulses
        to individual qubit waveforms at arbitrary time positions, or,

    (2) Use the function `add_gates` to add a list of pulses to all qubits. The
        pulses will be separated by a fixed pulse spacing.

    Attributes
    ----------
    n_qubit : int
        Number of qubits controlled by the sequence.

    local_xy : bool
        Define if qubits have local XY control lines.  If False, all control
        pulses are added to a single output waveform.

    sample_rate : float
        Sample rate of output waveforms.

    n_pts : int
        Length of output waveforms. Note that the resulting waveform may be
        different if the waveforms are trimmed.

    first_delay : float
        Position of first pulse

    trim_to_sequence : bool
        If True, waveform is trimmed to fit sequence

    trim_start : bool
        If True, waveform is trimmed at both start and end (default is just end)

    perform_tomography : bool
        If True, tomography pulses will be added to the end of the qubit xy
        control waveforms.

    perform_predistortion : bool
        If True, the control waveforms will be pre-distorted.

    generate_gate_switch  : bool
        If True, generate waveform for microwave gate switch

    uniform_gate : bool
        If True, the gate is open during the entire xy waveform

    gate_delay : float
        Delay of gate switch wave relative to the I/Q pulse

    gate_overlap : float
        Extra time before/after I/Q pulse during which the gate switch is open

    minimal_gate_time : float
        Shortest time the gate switch will stay open/closed.

    readout_trig_generate : bool
        If True, generate waveform with readout trig at the end of the waveform.

    readout_delay : float
        Readout trig delay.

    readout_amplitude : float
        Amplitude of readout trig pulse.

    readout_duration : float
        Duration of readout trig pulse.

    readout_iq_generate : bool
        If True, generate complex waveform with multi-qubit I/Q readout signals.

    compensate_crosstalk : bool
        If True, Z-control waveforms will be compensated for cross-talk.

    """

    def __init__(self, n_qubit=5, sample_rate=1.2E9, n_pts=240E3,
                 first_delay=100E-9, local_xy=True, dt=0):
        # define parameters
        self.n_qubit = n_qubit
        self.dt = dt
        self.local_xy = local_xy
        # waveform parameter
        self.sample_rate = sample_rate
        self.n_pts = n_pts
        self.first_delay = first_delay
        self.trim_to_sequence = True
        self.trim_start = False
        self.align_to_end = False
        # parameter for keeping track of current gate pulse time
        self.time_pulse = 0.0

        self.sequences = []

        # waveforms
        self.wave_xy = [np.zeros(0, dtype=np.complex)
                        for n in range(MAX_QUBIT)]
        self.wave_z = [np.zeros(0) for n in range(MAX_QUBIT)]
        self.wave_gate = [np.zeros(0) for n in range(MAX_QUBIT)]
        # define pulses
        self.pulses_1qb = [Pulse() for n in range(MAX_QUBIT)]
        self.pulses_2qb = [Pulse() for n in range(MAX_QUBIT - 1)]
        self.pulses_readout = [Pulse(pulse_type = PulseType.READOUT) for n in range(MAX_QUBIT)]

        # tomography
        self.perform_tomography = False
        self.tomography = Tomography()

        # cross-talk object
        self.compensate_crosstalk = False
        self.crosstalk = Crosstalk()

        # predistortion objects
        self.perform_predistortion = False
        self.predistortions = [Predistortion(n) for n in range(MAX_QUBIT)]

        # gate switch waveform
        self.generate_gate_switch = False
        self.uniform_gate = False
        self.gate_delay = 0.0
        self.gate_overlap = 20E-9
        self.minimal_gate_time = 20E-9

        # readout trig settings
        self.readout_trig_generate = False
        self.readout_trig_delay = 0.0
        self.readout_trig_amplitude = 1.0
        self.readout_trig_duration = 20E-9

        # readout wave object and settings
        self.readout_iq_generate = False
        self.readout = Readout(max_qubit=MAX_QUBIT)
        self.readout_trig = np.array([], dtype=float)
        self.readout_iq = np.array([], dtype=np.complex)


    def init_waveforms(self):
        """Initialize waveforms according to sequence settings"""
        # create empty waveforms of the correct size
        if self.trim_to_sequence:
            self.n_pts = int(np.ceil(self.sequences[-1].t_end*self.sample_rate))+1
        for n in range(self.n_qubit):
            self.wave_xy[n] = np.zeros(self.n_pts, dtype=np.complex)
            self.wave_z[n] = np.zeros(self.n_pts, dtype=float)
            self.wave_gate[n] = np.zeros(self.n_pts, dtype=float)

        # Universal time vector
        self.t = np.arange(self.n_pts)/self.sample_rate

        # readout trig
        self.readout_trig = np.zeros(self.n_pts, dtype=float)
        # readout i/q waveform
        self.readout_iq = np.zeros(self.n_pts, dtype=np.complex)

        # reset gate position counter
        self.time_pulse = self.first_delay


    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms

        Parameters
        ----------
        config : dict
            Configuration as defined by Labber driver configuration window

        """
        # this function should be overloaded by specific sequence
        pass


    def calculate_waveforms(self, config):
        """Calculate waveforms for all qubits

        The function will initialize the waveforms, generate the qubit pulse
        sequence, create gates and readout pulses, perform pre-distortion,
        and finally return the qubit control waveforms.

        Parameters
        ----------
        config : dict
            Configuration as defined by Labber driver configuration window

        Returns
        -------
        waveforms : dict with numpy arrays
            Dictionary with qubit waveforms. Depending on the sequence
            configuration, the dictionary will have the following keys:
                wave_xy : list of complex numpy arrays
                    Waveforms for qubit XY control.
                wave_z : list of numpy arrays
                    Waveforms for qubit Z control.
                wave_gate : list of numpy arrays
                    Waveforms for gating qubit XY pulses.
                readout_trig : numpy array
                    Waveform for triggering/gating qubit readout
                readout_iq : complex numpy array
                    Waveform for readout IQ control

        """
        self.sequences = []
        self.generate_sequence(config)
        self.init_waveforms()
        self.add_tomography()
        self.add_readout() # TODO Move to each sequence?
        self.perform_virtual_z()
        self.generate_waveforms()


        # collapse all xy pulses to one waveform if no local XY control
        if not self.local_xy:
            # sum all waveforms to first one
            self.wave_xy[0] = np.sum(self.wave_xy[:self.n_qubit], 0)
            # clear other waveforms
            for n in range(1, self.n_qubit):
                self.wave_xy[n][:] = 0.0

        self.perform_crosstalk_compensation()

        # trim waveforms, if wanted
        # self.trim_waveforms()

        # microwave gate switch waveform
        self.add_microwave_gate(config)

        # I/Q waveform predistortion
        self.predistort_waveforms()

        # create and return dictionary with waveforms
        data = dict()
        data['wave_xy'] = self.wave_xy
        data['wave_z'] = self.wave_z
        data['wave_gate'] = self.wave_gate
        data['readout_trig'] = self.readout_trig
        data['readout_iq'] = self.readout_iq
        return data

    def generate_waveforms(self):
        for step in self.sequences:
            for qubit, gate in enumerate(step.gates):
                # Virtual Z gate is special since it has no waveform
                if isinstance(gate, VirtualZGate):
                    continue

                # Get the corresponding pulse
                if isinstance(gate, (IdentityGate, SingleQubitGate)):
                    pulse = self.pulses_1qb[qubit]
                elif isinstance(gate, TwoQubitGate):
                    pulse = self.pulses_2qb[qubit]
                elif isinstance(gate, ReadoutGate):
                    pulse = self.pulses_readout[qubit]
                else:
                    raise ValueError('Please provide a pulse for this gate type.')


                if pulse.pulse_type == PulseType.Z:
                        waveform = self.wave_z[qubit]
                elif pulse.pulse_type == PulseType.XY:
                        waveform = self.wave_xy[qubit]
                        gate_waveform = self.wave_gate
                elif pulse.pulse_type == PulseType.READOUT:
                        waveform = self.readout_iq
                        gate_waveform = self.readout_trig


                # get the range of indices in use
                indices = np.arange(
                    max(np.floor(step.t_start*self.sample_rate), 0),
                    min(np.ceil(step.t_end*self.sample_rate), self.n_pts),
                    dtype=int
                )
                # return directly if no indices
                if len(indices) == 0:
                    continue

                # calculate time values for the pulse indices
                t = indices/self.sample_rate
                max_duration = step.t_end - step.t_start
                if step.align == 'center':
                    t0 = step.t_middle
                elif step.align == 'left':
                    t0 = step.t_middle - (max_duration-pulse.total_duration())/2
                elif step.align == 'right':
                    t0 = step.t_middle + (max_duration-pulse.total_duration())/2
                # calculate the pulse waveform for the selected indices
                waveform[indices] += gate.get_waveform(pulse, t0, t)

                if pulse.gated:
                    gate_waveform += pulse.calculate_gate(t0, self.t)

    def add_single_pulse(self, qubit, pulse, t0=None, dt=0, align_left=False):
        """Add single qubit pulse to specified qubit

        Parameters
        ----------
        qubit : int
            Qubit number, indexed from 0.

        pulse : :obj:`Pulse`
            Definition of pulse to add.

        dt : float
            Pulse spacing, referenced to the previous pulse.

        """

        self.add_single_gate(qubit, BaseGate(), t0, dt, pulse)

    def add_single_gate(self, qubit, gate, t0=None, dt=None, align_left=False):
        """Add single gate to specified qubit waveform

        Parameters
        ----------
        qubit : int
            Qubit number, indexed from 0.

        gate : :obj:`Gate`
            Definition of gate to add.

        dt : float
            Pulse spacing, referenced to the previous pulse.

        """


        if align_left is True:
            self.add_gate(qubit, gate, t0, dt, 'left')
        else:
            self.add_gate(qubit, gate, t0, dt, 'center')
        # If t0 was used as time reference, we need to make sure that the sequence is still sorted correctly
        # if t0 is not None:
        #     self.sort_qubit_sequence(qubit)

    def add_gate(self, qubit, gate, t0=None, dt=None, align='center'):
            if isinstance(gate, Enum):
                gate = gate.value
            log.log(20, str(gate))
            # If any of the gates is a composite gate, find it and add it first.
            # Keep track of its length in steps and time, then add matching I gates to compoensate
            # How to handle multiple composite gates?
            # Composite gates consit of multiple gates. Add one by one.
            # Test with 2 Rx gates
            if isinstance(gate, CompositeGate):
                log.log(20, 'Comp comp')
                if isinstance(qubit, int):
                    qubit = [qubit]
                if len(qubit) != gate.n_qubit:
                    raise ValueError('For composite gates the length of the qubit \
                    list must match the number of qubits in the composite gate.')

                comp_start = 0
                comp_end = 0
                for i in range(len(gate)):
                    kwargs = gate.get_gate_dict_at_index(i)
                    if i == 0 and dt is not None:
                        if kwargs['dt'] is None:
                            kwargs['dt'] = dt
                        else:
                            kwargs['dt'] += dt
                    self.add_gate(qubit, **kwargs)
                    if i == 0:
                        comp_start = self.sequences[-1].t_start
                comp_end = self.sequences[-1].t_end
                return

            if not isinstance(qubit, list):
                qubit = [qubit]
            if not isinstance(gate, list):
                gate = [gate]
            if len(gate) != len(qubit):
                raise ValueError('Length of qubit and gate list must be equal.')

            step = Step(self.n_qubit, align=align)
            step.add_gate(qubit, gate)
            # Longest pulse in the step needed for correct timing
            if len(self.sequences) == 0:
                t_start = self.first_delay-self.dt
            else:
                t_start = self.sequences[-1].t_end
            t_end = t_start

            max_duration = 0
            for qubit, gate in enumerate(step.gates):
                # Virtual Z gate is special since it has no length
                if isinstance(gate, VirtualZGate):
                    continue
                # Get the corresponding pulse
                if isinstance(gate, SingleQubitGate):
                    pulse = self.pulses_1qb[qubit]
                elif isinstance(gate, IdentityGate):
                    if gate.width is None:
                        pulse = self.pulses_1qb[qubit]
                    else:
                        duration = gate.width
                        pulse = None
                elif isinstance(gate, TwoQubitGate):
                    pulse = self.pulses_2qb[qubit]
                elif isinstance(gate, ReadoutGate):
                    pulse = self.pulses_readout[qubit]
                else:
                    raise ValueError('Please provide a pulse for this gate type.')

                # calculate timings
                if pulse is not None:
                    duration = pulse.total_duration()
                if duration > max_duration:
                    max_duration = duration
            if t0 is None:
                if dt is None:
                    step.t_start = t_end+self.dt
                else:
                    step.t_start = t_end+dt

            else:
                step.t_start = t0-max_duration/2
                step.t_end = t0+max_duration/2
            step.t_end = step.t_start+max_duration
            step.t_middle = step.t_start+max_duration/2

            self.sequences.append(step)

    def add_gate_to_all(self, gate, dt=0, align='right'):
            self.add_gate([n for n in range(self.n_qubit)],
                          [gate for n in range(self.n_qubit)])


    def add_gates(self, gates):
        """Add multiple gates to qubit waveforms

        Add multiple gates to the qubit waveform.  Pulses are added to the end
        of the sequence, with gate spacing set by spacing parameter.

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
        gates : list of list of :enum:`gate`
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



    def add_tomography(self):
        """Add tomography pulses at the end of the qubit xy waveforms.

        """
        if not self.perform_tomography:
            return
        # Add pulses
        self.tomography.add_pulses(self)


    def predistort_waveforms(self):
        """Pre-distort the waveforms.

        """
        if not self.perform_predistortion:
            return
        # go through and predistort all waveforms
        n_wave = self.n_qubit if self.local_xy else 1
        for n in range(n_wave):
            self.wave_xy[n] = self.predistortions[n].predistort(self.wave_xy[n])

    def sort_qubit_sequence(self, qubit):
        undecorated = self.qubit_sequences[qubit]
        sort_on = "t_end"
        decorated = [(dict_[sort_on], dict_) for dict_ in undecorated]
        decorated.sort()
        self.qubit_sequences[qubit] = [dict_ for (key, dict_) in decorated]


    def perform_crosstalk_compensation(self):
        """Compensate for Z-control crosstalk

        """
        if not self.compensate_crosstalk:
            return
        self.wave_z = self.crosstalk.compensate(self.wave_z)

    def perform_virtual_z(self):
        """Shifts the phase of pulses subsequent to virutal z gates
        """
        for qubit in range(self.n_qubit):
            for m, step in enumerate(self.sequences):
                gate = step.gates[qubit]
                if isinstance(gate, VirtualZGate):
                    for subsequent_step in self.sequences[m+1:len(self.sequences)]:
                        subsequent_step.gates[qubit] = subsequent_step.gates[qubit].add_phase(gate.angle)

    def add_readout(self):
        """Create read-out trig and waveform signals at the end of the sequence

        """
        if self.readout_iq_generate:
            readout = ReadoutGate()
            delay = IdentityGate(width=self.readout_delay)
            self.add_gate([n for n in range(self.readout_n)],
                          [delay for n in range(self.readout_n)], dt=0)
            self.add_gate([n for n in range(self.readout_n)],
                          [readout for n in range(self.readout_n)], dt=0)

    def add_microwave_gate(self, config):
        """Create waveform for gating microwave switch

        """
        if not self.generate_gate_switch:
            return
        n_wave = self.n_qubit if self.local_xy else 1
        # go through all waveforms
        for n, wave in enumerate(self.wave_xy[:n_wave]):
            if self.uniform_gate:
                # the uniform gate is all ones
                gate = np.ones_like(wave)
                # if creating readout trig, turn off gate during readout
                if self.readout_trig_generate:
                    gate[-int((self.readout_trig_duration - self.gate_overlap -
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
            self.wave_gate[n] = gate


    def set_parameters(self, config={}):
        """Set base parameters using config from from Labber driver

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

        # waveform parameters
        self.sample_rate = config.get('Sample rate')
        self.readout_noise = 0.0
        self.n_pts = int(config.get('Number of points'))
        self.first_delay = config.get('First pulse delay')
        self.trim_to_sequence = config.get('Trim waveform to sequence')
        self.trim_start = config.get('Trim both start and end')
        self.align_to_end = config.get('Align pulses to end of waveform')

        # single-qubit pulses
        for n, pulse in enumerate(self.pulses_1qb):
            # pulses are indexed from 1 in Labber
            m = n + 1
            # global parameters
            pulse.shape = PulseShape(config.get('Pulse type'))
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
            # pulse-specific parameters
            pulse.amplitude = config.get('Amplitude #%d' % m)
            pulse.frequency = config.get('Frequency #%d' % m)
            pulse.drag_coefficient = config.get('DRAG scaling #%d' % m)
            pulse.gated = config.get('Generate gate')

        # two-qubit pulses
        for n, pulse in enumerate(self.pulses_2qb):
            # pulses are indexed from 1 in Labber
            s = ' #%d%d' % (n + 1, n + 2)
            # global parameters
            pulse.shape = PulseShape(config.get('Pulse type, 2QB'))
            pulse.z_pulse = True
            if config.get('Pulse type, 2QB') == 'CZ':
                pulse.F_Terms = d[config.get('Fourier terms, 2QB')]
                if config.get('Uniform 2QB pulses'):
                    pulse.width = config.get('Width, 2QB')
                    pulse.plateau = config.get('Plateau, 2QB')
                else:
                    pulse.width = config.get('Width, 2QB' + s)
                    pulse.plateau = config.get('Plateau, 2QB')

                # Get Fourier values
                if d[config.get('Fourier terms, 2QB')] == 4 :
                    pulse.Lcoeff = np.array([config.get('L1, 2QB' + s),config.get('L2, 2QB' + s),config.get('L3, 2QB' + s),config.get('L4, 2QB' + s)])
                elif d[config.get('Fourier terms, 2QB')] == 3 :
                    pulse.Lcoeff = np.array([config.get('L1, 2QB' + s),config.get('L2, 2QB' + s),config.get('L3, 2QB' + s)])
                elif d[config.get('Fourier terms, 2QB')] == 2 :
                    pulse.Lcoeff = np.array([config.get('L1, 2QB' + s),config.get('L2, 2QB' + s)])
                elif d[config.get('Fourier terms, 2QB')] == 1 :
                    pulse.Lcoeff = np.array([config.get('L1, 2QB' + s)])

                pulse.Coupling = config.get('Coupling, 2QB' + s)
                pulse.Offset = config.get('f11-f20 initial, 2QB' + s)
                pulse.amplitude = config.get('f11-f20 final, 2QB' + s)
                pulse.dfdV = config.get('df/dV, 2QB' + s)

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

        # tomography
        self.perform_tomography = config.get('Generate tomography pulse', False)
        self.tomography.set_parameters(config)

        # predistortion
        self.perform_predistortion = config.get('Predistort waveforms', False)
        # update all predistorting objects
        for p in self.predistortions:
            p.set_parameters(config)

        # crosstalk
        self.compensate_crosstalk = config.get('Compensate cross-talk', False)
        self.crosstalk.set_parameters(config)

        # gate switch waveform
        self.uniform_gate = config.get('Uniform gate')
        self.gate_delay = config.get('Gate delay')
        self.gate_overlap = config.get('Gate overlap')
        self.minimal_gate_time = config.get('Minimal gate time')

        # readout
        self.readout_n = int(config.get('Number of readout tones'))
        self.readout_match_main_size = config.get('Match main sequence waveform size')
        self.readout_distribute_phases = config.get('Distribute readout phases')

        # predistortion
        self.predistort = config.get('Predistort readout waveform')
        if self.predistort:
            for n in range(self.max_qubit):
                # pre-distortion settings are currently same for all qubits
                linewidth = config.get('Resonator linewidth')
                self.measured_rise[n] = 1.0 / (2 * np.pi * linewidth)
                self.target_rise[n] = config.get('Target rise time')

        # readout settings
        self.readout_iq_generate = config.get('Generate readout waveform')
        self.readout_delay = config.get('Readout delay')
        self.readout_i_offset = config.get('Readout offset - I')
        self.readout_q_offset = config.get('Readout offset - Q')
        self.readout_trig_generate = config.get('Generate readout trig')
        self.readout.set_parameters(config)

        # get readout pulse parameters
        phases = 2 * np.pi * np.array([0.8847060, 0.2043214, 0.9426104,
            0.6947334, 0.8752361, 0.2246747, 0.6503154, 0.7305004, 0.1309068])
        for n, pulse in enumerate(self.pulses_readout):
            # pulses are indexed from 1 in Labber
            m = n + 1
            pulse.shape = PulseShape(config.get('Readout pulse type'))
            pulse.truncation_range = config.get('Readout truncation range')
            pulse.start_at_zero = config.get('Readout start at zero')
            pulse.iq_skew = config.get('Readout IQ skew')*np.pi/180
            pulse.iq_ratio = config.get('Readout I/Q ratio')
            pulse.phase = phases[n]

            # if config.get('Uniform pulse shape'):
            #     pulse.width = config.get('Width')
            #     pulse.plateau = config.get('Plateau')
            # else:
            #     pulse.width = config.get('Width #%d' % m)
            #     pulse.plateau = config.get('Plateau #%d' % m)
            # pulse-specific parameters

            pulse.frequency = config.get('Readout frequency #%d' % m)
            if config.get('Uniform readout amplitude') is True:
                pulse.amplitude = config.get('Readout amplitude')
            else:
                pulse.amplitude = config.get('Readout amplitude #%d' % (n + 1))

            pulse.width = config.get('Readout width')
            pulse.plateau = config.get('Readout duration')
            pulse.gated = self.readout_trig_generate
            pulse.gate_amplitude = config.get('Readout trig amplitude')
            pulse.gate_duration = config.get('Readout trig duration')




if __name__ == '__main__':
    pass
