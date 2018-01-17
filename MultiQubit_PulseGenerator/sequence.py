#!/usr/bin/env python3
import numpy as np
from copy import copy

from pulse import PulseShape, Pulse
from predistortion import Predistortion
from crosstalk import Crosstalk
from readout import Readout
from gates import Gate, ONE_QUBIT_GATES, TWO_QUBIT_GATES
from tomography import Tomography

# add logger, to allow logging to Labber's instrument log
import logging
log = logging.getLogger('LabberDriver')


# Maximal number of qubits controllable by this class
MAX_QUBIT = 9


class Sequence(object):
    """This class represents a multi-qubit control sequence

    The class supports two ways of defining pulse sequences:

    (1) Use the functions `add_single_pulse` or `add_single_gate` to add pulses
        to individual qubit waveforms at arbitrary time positions, or,

    (2) Use the function `add_gates` to add a list of pulses to all qubits. The
        pulses will be separated by a fixed pulse period.

    Attributes
    ----------
    n_qubit : int
        Number of qubits controlled by the sequence.

    period_1qb : float
        Period for single-qubit gates.

    period_2qb : float
        Period for two-qubit gates.

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

    generate_readout_trig : bool
        If True, generate waveform with readout trig at the end of the waveform.

    readout_delay : float
        Readout trig delay.

    readout_amplitude : float
        Amplitude of readout trig pulse.

    readout_duration : float
        Duration of readout trig pulse.

    generate_readout_iq : bool
        If True, generate complex waveform with multi-qubit I/Q readout signals.

    compensate_crosstalk : bool
        If True, Z-control waveforms will be compensated for cross-talk.

    """

    def __init__(self, n_qubit=5, period_1qb=30E-9, period_2qb=30E-9,
                 sample_rate=1.2E9, n_pts=240E3, first_delay=100E-9,
                 local_xy=True):
        # define parameters
        self.n_qubit = n_qubit
        self.period_1qb = period_1qb
        self.period_2qb = period_2qb
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

        # waveforms
        self.wave_xy = [np.zeros(0, dtype=np.complex)
                        for n in range(MAX_QUBIT)]
        self.wave_z = [np.zeros(0) for n in range(MAX_QUBIT)]
        self.wave_gate = [np.zeros(0) for n in range(MAX_QUBIT)]
        # define pulses
        self.pulses_1qb = [Pulse() for n in range(MAX_QUBIT)]
        self.pulses_2qb = [Pulse() for n in range(MAX_QUBIT - 1)]

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
        self.generate_readout_trig = False
        self.readout_delay = 0.0
        self.readout_amplitude = 1.0
        self.readout_duration = 20E-9

        # readout wave object and settings
        self.generate_readout_iq = False
        self.readout = Readout(max_qubit=MAX_QUBIT)
        self.readout_trig = np.array([], dtype=float)
        self.readout_iq = np.array([], dtype=np.complex)


    def init_waveforms(self):
        """Initialize waveforms according to sequence settings"""
        # clear waveforms
        for n in range(self.n_qubit):
            self.wave_xy[n] = np.zeros(self.n_pts, dtype=np.complex)
            self.wave_z[n] = np.zeros(self.n_pts, dtype=float)
            self.wave_gate[n] = np.zeros(self.n_pts, dtype=float)

        # readout trig
        pts = self.n_pts if self.generate_readout_trig else 0
        self.readout_trig = np.zeros(pts, dtype=float)
        # readout i/q waveform
        pts = self.n_pts if self.generate_readout_iq else 0
        self.readout_iq = np.zeros(pts, dtype=np.complex)

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
        # start by initializing the waveforms
        self.init_waveforms()

        # generate sequence
        self.generate_sequence(config)

        # add tomography
        self.add_tomography_pulses()

        # collapse all xy pulses to one waveform if no local XY control
        if not self.local_xy:
            # sum all waveforms to first one
            self.wave_xy[0] = np.sum(self.wave_xy[:self.n_qubit], 0)
            # clear other waveforms
            for n in range(1, self.n_qubit):
                self.wave_xy[n][:] = 0.0

        # cross-talk compensation
        self.perform_crosstalk_compensation()

        # read-out signals
        self.generate_readout()

        # trim waveforms, if wanted
        self.trim_waveforms()

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


    def add_single_pulse(self, qubit, pulse, t0, align_left=False):
        """Add single pulse to specified qubit waveform

        Parameters
        ----------
        qubit : int or numpy array
            Qubit number, indexed from 0. If a numpy array is given, pulses will
            be added to the specified waveform instead of the qubit waveform.

        pulse : :obj:`Pulse`
            Definition of pulse to add.

        t0 : float
            Pulse position, referenced to center of pulse.

        align_left : bool, optional
            If True, the pulse position is referenced to the left edge of the
            pulse, otherwise to the center. Default is False.

        """
        # find waveform to add pulse to
        if isinstance(qubit, np.ndarray):
            waveform = qubit
        else:
            if pulse.z_pulse:
                waveform = self.wave_z[qubit]
            else:
                waveform = self.wave_xy[qubit]
        # calculate total length of pulse
        duration = pulse.total_duration()
        # shift time to mid point if user gave start point
        if align_left:
            t0 = t0 + duration / 2
        # get the range of indices in use
        indices = np.arange(
            max(np.floor((t0 - duration / 2) * self.sample_rate), 0),
            min(np.ceil((t0 + duration / 2) * self.sample_rate), self.n_pts),
            dtype=int
        )
        # return directly if no indices
        if len(indices) == 0:
            return

        # calculate time values for the pulse indices
        t = indices / self.sample_rate
        # calculate the pulse envelope for the selected indices
        y = pulse.calculate_envelope(t0, t)

        # proceed depending on Z- or XY gate
        if pulse.z_pulse or waveform.dtype != np.complex:
            # Z pulse, add directly to Z waveform
            waveform[indices] += y

        else:
            # XY pulse, apply DRAG, if wanted
            if pulse.use_drag:
                beta = pulse.drag_coefficient * self.sample_rate
                y = y + 1j * beta * np.gradient(y)

            # single-sideband mixing, get frequency
            omega = 2 * np.pi * pulse.frequency
            # apply SSBM transform
            data_i = (y.real * np.cos(omega * t - pulse.phase) +
                      -y.imag * np.cos(omega * t - pulse.phase + np.pi / 2))
            data_q = (y.real * np.sin(omega * t - pulse.phase) +
                      -y.imag * np.sin(omega * t - pulse.phase + np.pi / 2))
            # # apply SSBM transform
            # data_i = (-y.real * np.sin(omega * t - pulse.phase) +
            #           y.imag * np.sin(omega * t - pulse.phase + np.pi / 2))
            # data_q = (y.real * np.cos(omega * t - pulse.phase) +
            #           -y.imag * np.cos(omega * t - pulse.phase + np.pi / 2))

            # store result
            waveform[indices] += (data_i + 1j * data_q)


    def add_single_gate(self, qubit, gate, t0, align_left=False):
        """Add single gate to specified qubit waveform

        Parameters
        ----------
        qubit : int
            Qubit number, indexed from 0.

        gate : :enum:`Gate`
            Definition of gate to add.

        t0 : float
            Pulse position, referenced to center of pulse.

        align_left : bool, optional
            If True, the pulse position is referenced to the left edge of the
            pulse, otherwise to the center. Default is False.

        """
        # check if one- or two-qubit gate
        if gate in ONE_QUBIT_GATES:
            # get copy of pulse to use
            pulse = copy(self.pulses_1qb[qubit])

            # scale pulse by 0.5 if pi/2
            if gate in (Gate.X2p, Gate.Y2p, Gate.X2m, Gate.Y2m):
                pulse.amplitude *= 0.5
            # rotate by 90 deg if pulse is in Y
            if gate in (Gate.Yp, Gate.Y2p, Gate.Ym, Gate.Y2m):
                pulse.phase += np.pi / 2
            # negate if negative pulse
            if gate in (Gate.Xm, Gate.X2m, Gate.Ym, Gate.Y2m):
                pulse.amplitude = -pulse.amplitude
            if gate is (Gate.I):
                pulse.amplitude = 0

            # add pulse to waveform
            self.add_single_pulse(qubit, pulse, t0, align_left=align_left)

        else:
            # two-qubit gate, get pulse
            pulse = copy(self.pulses_2qb[qubit])
            # add pulse to waveform
            self.add_single_pulse(qubit, pulse, t0, align_left=align_left)
            # TODO (simon): Update two-qubit pulse to include phase correction,
            # compensation pulses to neighboring qubits, etc.


    def add_gates(self, gates):
        """Add multiple gates to qubit waveforms

        Add multiple gates to the qubit waveform.  Pulses are added to the end
        of the sequence, with gate period set by single- and two-qubit gate
        period parameters.

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
            # check if any two-qubit gates
            two_qubit = np.any([g in TWO_QUBIT_GATES for g in gates_qubits])
            # pulse period may be different for two-qubi gates
            period = self.period_2qb if two_qubit else self.period_1qb
            # go through all qubits
            for n, g in enumerate(gates_qubits):
                # ignore if gate is None
                if g is None:
                    continue
                # add gate to specific qubit waveform
                self.add_single_gate(n, g, t0=self.time_pulse)
            # after adding all pulses, increment current gate time
            self.time_pulse += period


    def add_tomography_pulses(self):
        """Add tomography pulses to the end of the qubit xy waveforms

        """
        if not self.perform_tomography:
            return
        # get time for adding tomograph pulse
        t = self.find_range_of_sequence()[1]
        # TODO(morten): add code to add tomography pulses
        self.tomography.add_pulses(self, t)


    def predistort_waveforms(self):
        """Add tomography pulses to the end of the qubit xy waveforms

        """
        if not self.perform_predistortion:
            return
        # go through and predistort all waveforms
        n_wave = self.n_qubit if self.local_xy else 1
        for n in range(n_wave):
            self.wave_xy[n] = self.predistortions[n].predistort(self.wave_xy[n])


    def perform_crosstalk_compensation(self):
        """Compensate for Z-control crosstalk

        """
        if not self.compensate_crosstalk:
            return
        self.wave_z = self.crosstalk.compensate(self.wave_z)


    def find_range_of_sequence(self):
        """Find and return time at start and end of gate sequence

        Returns
        -------
        times : list
            List with two elements - Time at start and end of sequence.

        """
        # disable check based on pulses, always check actual waveforms
        if False:  # self.time_pulse > self.first_delay:
            # if pulses have been added with add_gates, get from pulse period
            t0 = self.first_delay - self.period_1qb
            t1 = self.time_pulse

        else:
            # find end by searching for last non-zero element
            sum_all = np.zeros_like(self.wave_xy[0])
            for n in range(self.n_qubit):
                sum_all += np.abs(self.wave_xy[n])
                sum_all += np.abs(self.wave_z[n])
            non_zero = np.where(sum_all > self.readout_noise)[0]
            # if data is not all zero, add after last pulse
            if len(non_zero) > 0:
                t0 = max(0.0, (non_zero[0] - 1) / self.sample_rate)
                t1 = (non_zero[-1] + 1) / self.sample_rate
            else:
                t0 = 0.0
                t1 = len(sum_all) / self.sample_rate
        return [t0, t1]


    def generate_readout(self):
        """Create read-out trig and waveform signals

        """
        # get positon of readout
        if self.generate_readout_trig or self.generate_readout_iq:
            t = self.find_range_of_sequence()[1] + self.readout_delay
            i0 = int(round(t * self.sample_rate))
        # start with readout trig signal
        if self.generate_readout_trig:
            # create trig waveform directly
            i1 = min(int(round((t + self.readout_duration) * self.sample_rate)),
                     len(self.readout_trig) - 1)
            self.readout_trig[i0:i1] = self.readout_amplitude

            # # create pulse object and insert into trig waveform
            # trig = Pulse(amplitude=self.readout_amplitude,
            #              width=0.0,
            #              plateau=self.readout_duration,
            #              shape=PulseShape.SQUARE)
            # self.add_single_pulse(self.readout_trig, trig, t, align_left=True)

        # readout I/Q waveform
        if self.generate_readout_iq:
            # ignore readout timestamp if pulses are aligned to end of waveform
            if self.align_to_end:
                wave = self.readout.create_waveform(t_start=0.0)
            else:
                wave = self.readout.create_waveform(t_start=t)
            # if not matching wave sizes, simply replace initialized waveform
            if not self.readout.match_main_size:
                self.readout_iq = wave
            else:
                i1 = min(len(self.readout_iq), i0 + len(wave))
                self.readout_iq[i0:i1] = wave[:(i1 - i0)]
            # add IQ offsets
            self.readout_iq.real += self.i_offset
            self.readout_iq.imag += self.q_offset


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
                if self.generate_readout_trig:
                    gate[-int((self.readout_duration - self.gate_overlap -
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


    def trim_waveforms(self):
        """Trim waveforms to match length of sequence

        """
        if not (self.trim_to_sequence or self.align_to_end):
            return
        # find range of sequence
        (t0, t1) = self.find_range_of_sequence()
        # don't trim past extent of microwave gate and readout trig, if in use
        dt_start = 0.0
        dt_end = 0.0
        if self.generate_gate_switch:
            dt_start = min(0.0, (self.gate_delay - self.gate_overlap))
            dt_end = max(0.0, (self.gate_delay + self.gate_overlap))
        if self.generate_readout_trig:
            # add a few extra points, to ensure read-out trig doesn't end high
            dt_end = max(dt_end, self.readout_delay + self.readout_duration +
                         1.0 / self.sample_rate)
        # same thing for I/Q readout
        if self.generate_readout_iq and self.readout.match_main_size:
            dt_end = max(dt_end, self.readout_delay + self.readout.duration +
                         1.0 / self.sample_rate)
        t0 += dt_start
        t1 += dt_end

        # get indices for start/end
        i0 = max(0, int(np.floor(t0 * self.sample_rate)))
        # check if don't trim beginning of waveform
        if not self.trim_start:
            i0 = 0
        i1 = min(self.n_pts, int(np.ceil(t1 * self.sample_rate)))

        if self.align_to_end:
            # align pulses to end of waveform
            m = self.n_pts - (i1 - i0)
            for n in range(self.n_qubit):
                self.wave_xy[n] = np.r_[np.zeros(m), self.wave_xy[n][i0:i1]]
                self.wave_z[n] = np.r_[np.zeros(m), self.wave_z[n][i0:i1]]
                self.wave_gate[n] = np.r_[np.zeros(m), self.wave_gate[n][i0:i1]]
            if self.generate_readout_trig:
                self.readout_trig = np.r_[np.zeros(m), self.readout_trig[i0:i1]]
                # force readout trig to end in zero
                self.readout_trig[-1] = 0.0
            if self.generate_readout_iq and self.readout.match_main_size:
                self.readout_iq = np.r_[np.zeros(m), self.readout_iq[i0:i1]]

        else:
            # trim waveforms
            for n in range(self.n_qubit):
                self.wave_xy[n] = self.wave_xy[n][i0:i1]
                self.wave_z[n] = self.wave_z[n][i0:i1]
                self.wave_gate[n] = self.wave_gate[n][i0:i1]
            if self.generate_readout_trig:
                self.readout_trig = self.readout_trig[i0:i1]
                # force readout trig to end in zero
                self.readout_trig[-1] = 0.0
            if self.generate_readout_iq and self.readout.match_main_size:
                self.readout_iq = self.readout_iq[i0:i1]


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
        self.period_1qb = config.get('Pulse period, 1-QB')
        self.period_2qb = config.get('Pulse period, 2-QB')
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
        self.generate_gate_switch = config.get('Generate gate')
        self.uniform_gate = config.get('Uniform gate')
        self.gate_delay = config.get('Gate delay')
        self.gate_overlap = config.get('Gate overlap')
        self.minimal_gate_time = config.get('Minimal gate time')

        # readout, trig settings
        self.generate_readout_trig = config.get('Generate readout trig')
        self.readout_delay = config.get('Readout delay')
        self.readout_amplitude = config.get('Readout trig amplitude')
        self.readout_duration = config.get('Readout trig duration')
        self.iq_skew = config.get('Readout IQ skew')
        self.i_offset = config.get('Readout offset - I')
        self.q_offset = config.get('Readout offset - Q')

        # readout, wave settings
        self.generate_readout_iq = config.get('Generate readout waveform')
        self.readout.set_parameters(config)


if __name__ == '__main__':
    pass
    Pulse()
