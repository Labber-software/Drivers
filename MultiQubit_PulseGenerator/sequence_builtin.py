#!/usr/bin/env python3
# add logger, to allow logging to Labber's instrument log
import logging
import numpy as np

import gates
from sequence import Sequence

log = logging.getLogger('LabberDriver')


class Rabi(Sequence):
    """Sequence for driving Rabi oscillations in multiple qubits."""

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms."""
        # just add pi-pulses for the number of available qubits
        self.add_gate_to_all(gates.Xp, align='right')


class CPMG(Sequence):
    """Sequence for multi-qubit Ramsey/Echo/CMPG experiments."""

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms."""
        # get parameters
        n_pulse = int(config['# of pi pulses'])
        pi_to_q = config['Add pi pulses to Q']
        duration = config['Sequence duration']
        edge_to_edge = config['Edge-to-edge pulses']
        if config['Add last pi/2 pulse to Q']:
            pi2_final = gates.Y2p
        else:
            pi2_final = gates.X2p

        # select type of refocusing pi pulse
        gate_pi = gates.Yp if pi_to_q else gates.Xp

        # always do T1 same way, regardless if edge-to-edge or center-center
        if n_pulse < 0:
            self.add_gate_to_all(gate_pi)
            self.add_gate_to_all(gates.IdentityGate(width=duration), dt=0)

        elif edge_to_edge:
            # edge-to-edge pulsing, set pulse separations
            self.add_gate_to_all(gates.X2p)
            # for ramsey, just add final pulse
            if n_pulse == 0:
                self.add_gate_to_all(gates.X2p, dt=duration)
            else:
                dt = duration / n_pulse
                # add first pi pulse after half duration
                self.add_gate_to_all(gate_pi, dt=dt/2)
                # add rest of pi pulses
                for i in range(n_pulse - 1):
                    self.add_gate_to_all(gate_pi, dt=dt)
                # add final pi/2 pulse
                self.add_gate_to_all(pi2_final, dt=dt/2)

        else:
            # center-to-center spacing, set absolute pulse positions
            self.add_gate_to_all(gates.X2p, t0=0)
            # add pi pulses at right position
            for i in range(n_pulse):
                self.add_gate_to_all(gate_pi,
                                     t0=(i + 0.5) * (duration / n_pulse))
            # add final pi/2 pulse
            self.add_gate_to_all(pi2_final, t0=duration)


class PulseTrain(Sequence):
    """Sequence for multi-qubit pulse trains, for pulse calibrations."""

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms."""
        # get parameters
        n_pulse = int(config['# of pulses'])
        alternate = config['Alternate pulse direction']

        if n_pulse == 0:
            self.add_gate_to_all(gates.I)
        for n in range(n_pulse):
            pulse_type = config['Pulse']
            if pulse_type == 'CPh':
                for i in range(self.n_qubit-1):
                    self.add_gate([i, i+1], gates.CPh)
            else:
                if alternate and (n % 2) == 1:
                    pulse_type = pulse_type.replace('p', 'm')
                gate = getattr(gates, pulse_type)
                self.add_gate_to_all(gate)


class SpinLocking(Sequence):
    """ Sequence for spin-locking experiment.

    """

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms."""

        pulse_amps = []
        for ii in range(9):
            pulse_amps.append(
                float(config['Drive pulse amplitude #' + str(ii + 1)]))
        pulse_duration = float(config['Drive pulse duration'])
        pulse_phase = float(config['Drive pulse phase']) / 180.0 * np.pi
        pulse_sequence = config['Pulse sequence']

        if pulse_sequence == 'SL-3':
            self.add_gate_to_all(gates.Y2p)
        if pulse_sequence == 'SL-5a':
            self.add_gate_to_all(gates.Y2m)
        if pulse_sequence == 'SL-5b':
            self.add_gate_to_all(gates.Y2p)

        if pulse_sequence != 'SL-3':
            self.add_gate_to_all(gates.Xp)

        rabi_gates = []
        for ii in range(self.n_qubit):
            rabi_gates.append(
                gates.RabiGate(pulse_amps[ii], pulse_duration, pulse_phase))
        self.add_gate(list(range(self.n_qubit)), rabi_gates)
        if pulse_sequence != 'SL-3':
            self.add_gate_to_all(gates.Xp)

        if pulse_sequence == 'SL-3':
            self.add_gate_to_all(gates.Y2p)
        if pulse_sequence == 'SL-5a':
            self.add_gate_to_all(gates.Y2m)
        if pulse_sequence == 'SL-5b':
            self.add_gate_to_all(gates.Y2p)

        return


class ReadoutTraining(Sequence):
    """Sequence for training readout state discriminator.

    """

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms."""

        training_type = config['Training type']
        state = int(config['Training, input state'])
        # currently only supports two states
        n_state = 2

        if training_type == 'Specific qubit':
            # specific qubit, just add gate
            qubit = int(config['Training, qubit']) - 1
            if state:
                self.add_gate(qubit, gates.Xp)

        elif training_type == 'All qubits at once':
            # add to all qubits
            if state:
                self.add_gate_to_all(gates.Xp)

        elif training_type == 'All combinations':
            # get bitstring for current state
            bitstring = np.base_repr(state, n_state, self.n_qubit)
            bitstring = bitstring[::-1][:self.n_qubit]
            qubit_list = []
            gate_list = []
            for n in range(self.n_qubit):
                if int(bitstring[n]):
                    qubit_list.append(n)
                    gate_list.append(gates.Xp)

            self.add_gate(qubit_list, gate_list)


if __name__ == '__main__':
    pass
