#!/usr/bin/env python3
from sequence import Gate, Sequence

# add logger, to allow logging to Labber's instrument log 
import logging
log = logging.getLogger('LabberDriver')



class SingleQubit_RB(Sequence):
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




if __name__ == '__main__':
    pass
