#!/usr/bin/env python3
import numpy as np
from copy import copy
from sequence import Sequence
from gates import Gate, VirtualZGate, CompositeGate, IdentityGate, CustomGate
from pulse import PulseShape, Pulse

# add logger, to allow logging to Labber's instrument log
import logging
log = logging.getLogger('LabberDriver')

class Rabi(Sequence):
    """Sequence for driving Rabi oscillations in multiple qubits"""

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms"""
        # just add pi-pulses for the number of available qubits
        self.add_gate_to_all(Gate.Xp, align='right')



class CPMG(Sequence):
    """Sequence for multi-qubit Ramsey/Echo/CMPG experiments"""

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms"""
        # get parameters
        n_pulse = int(config['# of pi pulses'])
        pi_to_q = config['Add pi pulses to Q']
        duration = config['Sequence duration']
        edge_to_edge = config['Edge-to-edge pulses']
        if self.pulses_1qb_xy[0].shape == PulseShape.GAUSSIAN:
            # Only gaussian pulses has a truncation range
            truncation = config['Truncation range']
        else:
            truncation = 0.0

        max_width = np.max([p.total_duration() for p in self.pulses_1qb_xy[:self.n_qubit]])
        # select type of refocusing pi pulse
        gate_pi = Gate.Yp if pi_to_q else Gate.Xp

        # add pulses for all active qubits
        for n, pulse in enumerate(self.pulses_1qb_xy[:self.n_qubit]):
            # get effective pulse durations, for timing purposes
            width = self.pulses_1qb_xy[n].total_duration() if edge_to_edge else 0.0
            pulse_total = width * (n_pulse + 1)
            # center pulses in add_gates mode; ensure sufficient pulse spacing in CPMG mode
            t0 = self.first_delay + self.pulses_1qb_xy[n].total_duration()/2
            # Align everything to the end of the last pulse of the one with the longest pulse width
            t0 += (max_width - self.pulses_1qb_xy[n].total_duration()) * (n_pulse + 1) if edge_to_edge else 0.0
            t0 += (max_width - self.pulses_1qb_xy[n].total_duration())
            # special case for -1 pulses => T1 experiment
            if n_pulse < 0:
                # add pi pulse
                self.add_single_gate(n, Gate.Xp, t0)
                # delay the reaodut by creating a very small pulse
                small_pulse = copy(pulse)
                small_pulse.amplitude = 1E-6 * pulse.amplitude
                self.add_single_pulse(n, small_pulse, t0 + duration)
                continue

            # add the first pi/2 pulses
            self.add_single_gate(n, Gate.X2p, t0)

            # add more pulses
            if n_pulse == 0:
                # no pulses = ramsey
                time_pi = []
            elif n_pulse == 1:
                # one pulse, echo experiment
                time_pi = [t0 + width + 0.5 * duration, ]
            elif n_pulse > 1:
                # figure out timing of pi pulses
                period = duration / n_pulse
                time_pi = (t0 + width + 0.5 * period +
                           (period + width) * np.arange(n_pulse))
            # add pi pulses, one by one
            for t in time_pi:
                self.add_single_gate(n, gate_pi, t)

            # add the last pi/2 pulses
            self.add_single_gate(n, Gate.X2p, t0 + duration + pulse_total)


class PulseTrain(Sequence):
    """Sequence for multi-qubit pulse trains, for pulse calibrations"""

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms"""
        # get parameters
        n_pulse = int(config['# of pulses'])
        alternate = config['Alternate pulse direction']


        # create list with gates
        gates = []
        if n_pulse == 0:
            gates.append([Gate.I for q in range(self.n_qubit)])
        for n in range(n_pulse):
            # check if alternate pulses
            if alternate and (n % 2) == 1:
                gate = Gate.Xm
            else:
                gate = Gate.Xp
            # create list with same gate for all active qubits
            gate_qubits = [gate for q in range(self.n_qubit)]
            # append to list of gates
            gates.append(gate_qubits)

        # add list of gates to sequence
        self.add_gates(gates)

class CZgates(Sequence):
    """Sequence for multi-qubit pulse trains, for pulse calibrations"""

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms"""
        # get parameters
        n_pulse = int(config['# of pulses, CZgates'])

        # create list with gates
        gates = []
        for n in range(n_pulse):
            gate = Gate.CPh
            # create list with same gate for all active qubits
            gate_qubits = [gate for q in range(self.n_qubit)]
            # append to list of gates
            gates.append(gate_qubits)

        # add list of gates to sequence
        self.add_gates(gates)


class VZ(Sequence):
    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms"""
        # get parameters
        duration = config['Sequence duration']
        z_angle = config['Z Phase']*np.pi/180
        edge_to_edge = config['Edge-to-edge pulses']

        width = 0 if edge_to_edge else self.pulses_1qb[0].total_duration()
        vz = VirtualZGate(angle=z_angle)
        # self.add_gate_to_all(Gate.X2p)
        self.add_gate_to_all(vz)
        self.add_gate_to_all(Gate.Xp)


class Timing(Sequence):
    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms"""
        # get parameters
        duration = config['Timing - Delay']
        max_width = np.max([[p.total_duration() for p in self.pulses_1qb_xy[:self.n_qubit]],
                           [p.total_duration() for p in self.pulses_1qb_z[:self.n_qubit]]])
        first_delay = self.first_delay+max_width/2
        self.add_gate_to_all(Gate.Zp, t0=first_delay)
        self.add_gate_to_all(Gate.Xp, t0=first_delay-duration)


class Anharmonicity(Sequence):
    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms"""
        self.add_gate_to_all(Gate.Xp)
        pulse12 = copy(self.pulses_1qb_xy[0])
        pulse12.shape = PulseShape(config.get('Anharmonicity - Pulse type'))
        pulse12.amplitude = config.get('Anharmonicity - Amplitude')
        pulse12.width = config.get('Anharmonicity - Width')
        pulse12.plateau = config.get('Anharmonicity - Plateau')
        pulse12.frequency = config.get('Anharmonicity - Frequency')
        pulse12.truncation_range = config.get('Anharmonicity - Truncation range')
        gate = CustomGate(pulse12)
        self.add_gate_to_all(gate)
        self.add_gate_to_all(Gate.Xp)





if __name__ == '__main__':
    pass
