#!/usr/bin/env python3

import numpy as npl
from gates import Gate
from copy import copy

class Tomography(object):
    """This class handles qubit control pulses for tomography

    """

    def __init__(self,tomography_index=0,nQubits = 1, singleQBtomoID = 0, twoQBtomoID1=0, twoQBtomoID2=1):
        # define variables
        self.tomography_index = tomography_index
        self.nQubits = nQubits
        self.singleQBtomoID = 0
        self.twoQBtomoID1 = 0
        self.twoQBtomoID2 = 1
        
    def set_parameters(self, config={}):    
        """Set base parameters using config from from Labber driver

        Parameters
        ----------
        config : dict
            Configuration as defined by Labber driver configuration window

        """
        # double-check that we actually want to do tomography:
        if not config.get('Generate tomography pulse'):
            return

        # First figure out how many qubits we're dealing with:
        dnQubitsTranslate = {'One': int(1), 'Two': int(2), 'Three': int(3), 'Four': int(4), 'Five': int(5), 'Six': int(6), 'Seven': int(7), 'Eight': int(8), 'Nine': int(9)}
        self.nQubits = dnQubitsTranslate[config.get('Qubits for tomography')]# nQubits now contain number of qubits as an integer

        # depending on 1 or 2 QB tomography:
        if self.nQubits == 1:
            # Determine which qubit to route 1QB tomo signal to:
            self.singleQBtomoID = dnQubitsTranslate[config.get('Qubit for tomography')]

            # Index into string identifying which pauli-matrix prefactor we're measuring:
            dictToPulse1QB = {'0 - Z': 'Z', '1 - Y': 'Y', '2 - X': 'X'} 
            self.tomography_index = dictToPulse1QB[config.get('Tomography pulse index 1-QB')]

        elif self.nQubits ==  2:
            self.twoQBtomoID1 = dnQubitsTranslate[config.get('Qubit 1 # tomography')]
            self.twoQBtomoID2 = dnQubitsTranslate[config.get('Qubit 2 # tomography')]

            dictToPulse2QB = {'1 - XX': 'XX', '2 - YX': 'YX', '3 - ZX': 'ZX', '4 - XY': 'XY', '5 - YY': 'YY', '6 - ZY': 'ZY', '7 - XZ': 'XZ', '8 - YZ': 'YZ', '9 - ZZ': 'ZZ'}
            self.tomography_index = dictToPulse2QB[config.get('Tomography pulse index 2-QB')]
        pass

    def add_pulses(self, sequence, t):
        """Add tomography pulses

        Parameters
        ----------
        sequence : :obj: `Sequence`
            Sequence to which add tomography pulses

        time : float
            Time of tomography pulse

        """
        if self.nQubits == 1:
            qubitID = self.singleQBtomoID - 1
            if self.tomography_index == 'Z':
                # small_pulse = copy(Gate.X2p)
                # small_pulse.amplitude = 1E-6 * Gate.X2p.amplitude
                sequence.add_single_gate(qubitID, Gate.I, t, align_left=True) # measure Z polarization
            elif self.tomography_index == 'Y':
                sequence.add_single_gate(qubitID, Gate.X2p, t, align_left=True) # measure Y polarization
            elif self.tomography_index == 'X':
                sequence.add_single_gate(qubitID, Gate.Y2m, t, align_left=True) # measure X polarization

        elif self.nQubits == 2:
            qubitID1 = self.twoQBtomoID1 - 1 
            qubitID2 = self.twoQBtomoID2 - 1
            if self.tomography_index == 'XX':
                sequence.add_single_gate(qubitID1,Gate.Y2m,t, align_left=True)
                sequence.add_single_gate(qubitID2,Gate.Y2m,t, align_left=True)
            elif self.tomography_index == 'YX':
                sequence.add_single_gate(qubitID1,Gate.X2p,t, align_left=True)
                sequence.add_single_gate(qubitID2,Gate.Y2m,t, align_left=True)
            elif self.tomography_index == 'ZX':
                sequence.add_single_gate(qubitID1,Gate.I  ,t, align_left=True)
                sequence.add_single_gate(qubitID2,Gate.Y2m,t, align_left=True)
            elif self.tomography_index == 'XY':
                sequence.add_single_gate(qubitID1,Gate.Y2m,t, align_left=True)
                sequence.add_single_gate(qubitID2,Gate.X2p,t, align_left=True)
            elif self.tomography_index == 'YY':
                sequence.add_single_gate(qubitID1,Gate.X2p,t, align_left=True)
                sequence.add_single_gate(qubitID2,Gate.X2p,t, align_left=True)
            elif self.tomography_index == 'ZY':
                sequence.add_single_gate(qubitID1,Gate.I  ,t, align_left=True)
                sequence.add_single_gate(qubitID2,Gate.X2p,t, align_left=True)
            elif self.tomography_index == 'XZ':
                sequence.add_single_gate(qubitID1,Gate.Y2m,t, align_left=True)
                sequence.add_single_gate(qubitID2,Gate.I  ,t, align_left=True)
            elif self.tomography_index == 'YZ':
                sequence.add_single_gate(qubitID1,Gate.X2p,t, align_left=True)
                sequence.add_single_gate(qubitID2,Gate.I  ,t, align_left=True)
            elif self.tomography_index == 'ZZ':
                sequence.add_single_gate(qubitID1,Gate.I  ,t, align_left=True)
                sequence.add_single_gate(qubitID2,Gate.I  ,t, align_left=True)
        pass
        

if __name__ == '__main__':
    pass
