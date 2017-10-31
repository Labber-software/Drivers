#!/usr/bin/env python3

import numpy as np
from gates import Gate

class Tomography(object):
    """This class handles qubit control pulses for tomography

    """

    def __init__(self):
        # define variables
        self.tomograph_index = 0
        # TODO(morten): define variables tomography index, qubits to use, etc


    def set_parameters(self, config={}):
        """Set base parameters using config from from Labber driver

        Parameters
        ----------
        config : dict
            Configuration as defined by Labber driver configuration window

        """
        # get parameters
        # TODO(morten): set variables from GUI settings
        # self.tomograph_index = config.get('Tomography index')
        pass


    def add_pulses(self, sequence, t):
        """Compensate crosstalk on Z-control waveforms

        Parameters
        ----------
        sequence : :obj: `Sequence`
            Sequence to which add tomography pulses

        time : float
            Time of tomography pulse

        """
        # add tomography pulses
        # TEST: add to qubit 0
        qubit = 0
        sequence.add_single_gate(qubit, Gate.X2p, t, align_left=True)



if __name__ == '__main__':
    pass
