#!/usr/bin/env python3
# add logger, to allow logging to Labber's instrument log
import logging
from copy import copy

import numpy as np

from gates import Gate
from sequence import Sequence

log = logging.getLogger('LabberDriver')


class Rabi(Sequence):
    """Sequence for driving Rabi oscillations in multiple qubits."""

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms."""
        # just add pi-pulses for the number of available qubits
        self.add_gate_to_all(Gate.Xp, align='right')


class CPMG(Sequence):
    """Sequence for multi-qubit Ramsey/Echo/CMPG experiments."""

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms."""
        # get parameters
        n_pulse = int(config['# of pi pulses'])
        pi_to_q = config['Add pi pulses to Q']
        duration = config['Sequence duration']
        edge_to_edge = config['Edge-to-edge pulses']

        max_width = np.max([p.total_duration()
                            for p in self.pulses_1qb_xy[:self.n_qubit]])
        # select type of refocusing pi pulse
        gate_pi = Gate.Yp if pi_to_q else Gate.Xp

        # add pulses for all active qubits
        for n, pulse in enumerate(self.pulses_1qb_xy[:self.n_qubit]):
            # get effective pulse durations, for timing purposes
            width = self.pulses_1qb_xy[n].total_duration(
            ) if edge_to_edge else 0.0
            pulse_total = width * (n_pulse + 1)
            # Ensure sufficient pulse spacing in CPMG mode
            t0 = self.first_delay + self.pulses_1qb_xy[n].total_duration() / 2
            # Align to the end of the one with the longest pulse width
            t0 += (max_width - self.pulses_1qb_xy[n].total_duration()) * (
                n_pulse + 1) if edge_to_edge else 0.0
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
    """Sequence for multi-qubit pulse trains, for pulse calibrations."""

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms."""
        # get parameters
        n_pulse = int(config['# of pulses'])
        alternate = config['Alternate pulse direction']

        if n_pulse == 0:
            self.add_gate_to_all(Gate.I)
        for n in range(n_pulse):
            pulse_type = config['Pulse']
            # check if alternate pulses
            if alternate and (n % 2) == 1:
                pulse_type = pulse_type.replace('p', 'm')
                gate = Gate.__getattr__(pulse_type)
            else:
                gate = Gate.__getattr__(pulse_type)
            self.add_gate_to_all(gate)


if __name__ == '__main__':
    pass
