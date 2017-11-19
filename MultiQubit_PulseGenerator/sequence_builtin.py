#!/usr/bin/env python3
import numpy as np
from copy import copy
from sequence import Sequence
from gates import Gate

# add logger, to allow logging to Labber's instrument log 
import logging
log = logging.getLogger('LabberDriver')



class Rabi(Sequence):
    """Sequence for driving Rabi oscillations in multiple qubits"""

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms"""
        # get parameters
        uniform_amplitude = config['Uniform pulse ampiltude for all qubits']
        # just add pi-pulses for the number of available qubits
        for n in range(self.n_qubit):
            # get pulse to use
            pulse = self.pulses_1qb[n]
            # if using uniform amplitude, copy from pulse 1
            if uniform_amplitude:
                pulse.amplitude = self.pulses_1qb[0].amplitude
            # add pulse to sequence
            self.add_single_pulse(n, pulse, self.first_delay, align_left=True)



class CPMG(Sequence):
    """Sequence for multi-qubit Ramsey/Echo/CMPG experiments"""

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms"""
        # get parameters
        n_pulse = int(config['# of pi pulses'])
        pi_to_q = config['Add pi pulses to Q']
        duration = config['Sequence duration']
        edge_to_edge = config['Edge-to-edge pulses']
        t0 = self.first_delay + (self.pulses_1qb[0].width + self.pulses_1qb[0].plateau)*0.5
        # select type of refocusing pi pulse
        gate_pi = Gate.Yp if pi_to_q else Gate.Xp

        # add pulses for all active qubits
        for n, pulse in enumerate(self.pulses_1qb[:self.n_qubit]):
            # get effective pulse durations, for timing purposes
            width = (pulse.width + pulse.plateau) if edge_to_edge else 0.0
            pulse_total = width * (n_pulse + 1)

            # special case for -1 pulses => T1 experiment
            if n_pulse < 0:
                # add pi pulse
                self.add_single_gate(n, Gate.Xp, t0)
                # delay the reaodut by creating a very small pulse
                small_pulse = copy(pulse)
                small_pulse.amplitude = 1E-6 * pulse.amplitude
                self.add_single_pulse(n, small_pulse, t0 + duration)
                continue

            # add the first and last pi/2 pulses
            self.add_single_gate(n, Gate.X2p, t0)
            self.add_single_gate(n, Gate.X2p, t0 + duration + pulse_total)
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



class PulseTrain(Sequence):
    """Sequence for multi-qubit pulse trains, for pulse calibrations"""

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms"""
        # get parameters
        n_pulse = int(config['# of pulses'])
        alternate = config['Alternate pulse direction']

        # create list with gates
        gates = []
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


class CZecho(Sequence):
    """Sequence for multi-qubit pulse trains, for pulse calibrations"""

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms"""
        
        # create list with gates
        self.add_single_gate(0, Gate.X2p, self.first_delay + self.period_1qb/2)
        self.add_single_gate(0, Gate.CPh, self.first_delay + self.period_1qb + self.period_2qb/2)
        self.add_single_gate(0, Gate.Xp, self.first_delay + 3*self.period_1qb/2 + self.period_2qb)
        self.add_single_gate(1, Gate.Xp, self.first_delay + 5*self.period_1qb/2 + self.period_2qb)
        self.add_single_gate(0, Gate.CPh, self.first_delay + 3*self.period_1qb + 3*self.period_2qb/2)
        self.add_single_gate(0, Gate.X2p, self.first_delay + 7*self.period_1qb/2 + 2*self.period_2qb)
        self.add_single_gate(1, Gate.Xp, self.first_delay + 9*self.period_1qb/2 + 2*self.period_2qb)


if __name__ == '__main__':
    pass






