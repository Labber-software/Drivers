#!/usr/bin/env python3
import numpy as np

class Readout(object):
    """This class is used to generate multi-tone qubit readout pulses

    """

    def __init__(self, max_qubit=9):
        # define variables
        self.max_qubit = max_qubit
        self.frequencies = np.zeros(self.max_qubit)
        self.amplitudes = np.zeros(self.max_qubit)
        self.duration = 0.0
        # TODO: define more variables for readout, etc


    def set_parameters(self, config={}):
        """Set base parameters using config from from Labber driver

        Parameters
        ----------
        config : dict
            Configuration as defined by Labber driver configuration window

        """
        # get frequencies and amplitudes
        for n in range(self.max_qubit):
            self.frequencies[n] = config.get('Readout frequency #%d' % (n + 1))
            # amplitudes are currently same for all
            self.amplitudes[n] = config.get('Readout amplitude')
        # get other parameters
        self.duration = config.get('Readout duration')


    def create_waveform(self, n_qubit, t_start=0.0):
        """Generate readout waveform

        Parameters
        ----------
        n_qubit : int 
            Number of qubits to read out

        t_start : float 
            Start time for readout waveform, relative to start of sequence

        Returns
        -------
        waveform : complex numpy array
            Complex waveforms with I/Q signal for qubit reaodut

        """
        # TODO: create readout waveform
        waveform = np.array([], dtype=complex)
        return waveform



if __name__ == '__main__':
    pass

