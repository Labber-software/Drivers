#!/usr/bin/env python3
import logging

from gates import Gate

log = logging.getLogger('LabberDriver')


class ProcessTomography(object):
    """This class handles qubit control prepulses for process tomography."""

    def __init__(self, prepulse_index=0, qubit1ID=0, qubit2ID=1,
                 nProcessTomoQubits=1, tomoscheme='Single qubit'):

        self.prepulse_index = prepulse_index
        self. qubit1ID = qubit1ID
        self.qubit2ID = qubit2ID
        self.nProcessTomoQubits = nProcessTomoQubits
        self.tomography_scheme = tomoscheme

    def set_parameters(self, config={}):
        """Set base parameters using config from Labber driver.

        Parameters
        ----------
        config: dict
            Configuration as defined by Labber driver configuration window

        """

        # determine which tomography scheme is in use
        self.tomography_scheme = config.get('Tomography scheme')
        self.nProcessTomoQubits = 1 if self.tomography_scheme \
            == 'Single qubit' else 2

        # Prep dictionary to translate string 'one' into int(1) etc.:
        dnQubitsTranslate = {
            'One': int(1),
            'Two': int(2),
            'Three': int(3),
            'Four': int(4),
            'Five': int(5),
            'Six': int(6),
            'Seven': int(7),
            'Eight': int(8),
            'Nine': int(9)
        }

        # Update which-qubit variable
        if self.nProcessTomoQubits is 1:
            self.qubit1ID = dnQubitsTranslate[
                config.get('Qubit for tomography')]
            self.prepulse_index = config.get(
                'Process tomography prepulse index 1-QB')
        elif self.nProcessTomoQubits is 2:
            self.qubit1ID = dnQubitsTranslate[
                config.get('Qubit 1 # tomography')]
            self.qubit2ID = dnQubitsTranslate[
                config.get('Qubit 2 # tomography')]
            self.prepulse_index = config.get(
                'Process tomography prepulse index 2-QB')

    def add_pulses(self, sequence):
        """Add prepulses to the sequencer.

        Parameters
        ----------
        sequence: :obj: `Sequence`
            Sequence to which to add the prepulses

        """
        if self.tomography_scheme == 'Single qubit':
            qubitID1 = self.qubit1ID - 1
            gate = [None]

            whichGate = self.prepulse_index[0]
            gate = self.gate_from_index(whichGate)

            sequence.add_gate(qubitID1, gate)

        elif self.tomography_scheme in ['Two qubit (9 pulse set)',
                                        'Two qubit (30 pulse set)',
                                        'Two qubit (36 pulse set)']:
            qubitID1 = self.qubit1ID - 1
            qubitID2 = self.qubit2ID - 1
            gate = [None, None]

            whichGate = self.prepulse_index[:2]
            gate = self.gate_from_index(whichGate)

            sequence.add_gate([qubitID1, qubitID2], gate)

    def gate_from_index(self, whichGate):
        """Help function to translate prepulse index into gate.

        Parameters
        ----------
        whichGate: str
            Elements of list should be in ['0', '1', 'X', 'Y'],
            indicating which state to prepare

        """
        indices = list(whichGate)
        gates = []
        for index in indices:
            if index == '0':
                gates.append(Gate.I)
            elif index == '1':
                gates.append(Gate.Xp)
            elif index == 'X':
                gates.append(Gate.Y2p)
            elif index == 'Y':
                gates.append(Gate.X2m)
            else:
                raise ValueError("Gate should be in ['0', '1', 'X', or 'Y']")

        return gates


class StateTomography(object):
    """This class handles qubit control pulses for state tomography."""

    def __init__(self, tomography_index=0, singleQBtomoID=0,
                 twoQBtomoID1=0, twoQBtomoID2=1,
                 tomography_scheme='Single qubit'):
        # define variables
        self.tomography_index = tomography_index
        self.singleQBtomoID = 0
        self.twoQBtomoID1 = 0
        self.twoQBtomoID2 = 1
        self.tomography_scheme = 'Single qubit'

    def set_parameters(self, config={}):
        """Set base parameters using config from from Labber driver.

        Parameters
        ----------
        config : dict
            Configuration as defined by Labber driver configuration window

        """

        # Load tomo scheme into local variable:
        self.tomography_scheme = config.get('Tomography scheme')
        # Prep dictionary to translate string 'one' into int(1) etc.:
        dnQubitsTranslate = {
            'One': int(1),
            'Two': int(2),
            'Three': int(3),
            'Four': int(4),
            'Five': int(5),
            'Six': int(6),
            'Seven': int(7),
            'Eight': int(8),
            'Nine': int(9)
        }

        # depending on 1 or 2 QB tomography:
        if self.tomography_scheme == 'Single qubit':
            # Determine which qubit to route 1QB tomo signal to:
            self.singleQBtomoID = dnQubitsTranslate[config.get(
                'Qubit for tomography')]
            self.tomography_index = config.get('Tomography pulse index 1-QB')

        elif self.tomography_scheme in ['Two qubit (9 pulse set)',
                                        'Two qubit (30 pulse set)',
                                        'Two qubit (36 pulse set)']:
            self.twoQBtomoID1 = dnQubitsTranslate[config.get(
                'Qubit 1 # tomography')]
            self.twoQBtomoID2 = dnQubitsTranslate[config.get(
                'Qubit 2 # tomography')]

            # Format: Tomography pulse index 2-QB (n pulse set)
            pulseCall = 'Tomography pulse index 2-QB' + \
                        self.tomography_scheme[9:]

            self.tomography_index = config.get(pulseCall)

        pass

    def add_pulses(self, sequence):
        """Add tomography pulses.

        Parameters
        ----------
        sequence : :obj: `Sequence`
            Sequence to which add tomography pulses

        """
        if self.tomography_scheme == 'Single qubit':
            qubitID = self.singleQBtomoID - 1
            gate = [None]

            if self.tomography_index == 'Z: I':
                gate = Gate.I  # measure Z polarization
            elif self.tomography_index == 'Y: X2p':
                gate = Gate.X2p  # measure Y polarization
            elif self.tomography_index == 'X: Y2m':
                gate = Gate.Y2m  # measure X polarization
            sequence.add_gate(qubitID, gate)

        elif self.tomography_scheme == 'Two qubit (9 pulse set)':
            qubitID1 = self.twoQBtomoID1 - 1
            qubitID2 = self.twoQBtomoID2 - 1
            gate = [None, None]

            if self.tomography_index == 'XX: Y2m-Y2m':
                gate = [Gate.Y2m, Gate.Y2m]
            elif self.tomography_index == 'YX: X2p-Y2m':
                gate = [Gate.X2p, Gate.Y2m]
            elif self.tomography_index == 'ZX: I-Y2m':
                gate = [Gate.I, Gate.Y2m]
            elif self.tomography_index == 'XY: Y2m-X2p':
                gate = [Gate.Y2m, Gate.X2p]
            elif self.tomography_index == 'YY: X2p-X2p':
                gate = [Gate.X2p, Gate.X2p]
            elif self.tomography_index == 'ZY: I-X2p':
                gate = [Gate.I, Gate.X2p]
            elif self.tomography_index == 'XZ: Y2m-I':
                gate = [Gate.Y2m, Gate.I]
            elif self.tomography_index == 'YZ: X2p-I':
                gate = [Gate.X2p, Gate.I]
            elif self.tomography_index == 'ZZ: I-I':
                gate = [Gate.I, Gate.I]
            sequence.add_gate([qubitID1, qubitID2], gate)

        elif self.tomography_scheme == 'Two qubit (30 pulse set)':
            qubitID1 = self.twoQBtomoID1 - 1
            qubitID2 = self.twoQBtomoID2 - 1
            gate = [None, None]

            if self.tomography_index == 'I-I':
                gate = [Gate.I, Gate.I]
            elif self.tomography_index == 'Xp-I':
                gate = [Gate.Xp, Gate.I]
            elif self.tomography_index == 'I-Xp':
                gate = [Gate.I, Gate.Xp]
            elif self.tomography_index == 'X2p-I':
                gate = [Gate.X2p, Gate.I]
            elif self.tomography_index == 'X2p-X2p':
                gate = [Gate.X2p, Gate.X2p]
            elif self.tomography_index == 'X2p-Y2p':
                gate = [Gate.X2p, Gate.Y2p]
            elif self.tomography_index == 'X2p-Xp':
                gate = [Gate.X2p, Gate.Xp]
            elif self.tomography_index == 'Y2p-I':
                gate = [Gate.Y2p, Gate.I]
            elif self.tomography_index == 'Y2p-X2p':
                gate = [Gate.Y2p, Gate.X2p]
            elif self.tomography_index == 'Y2p-Y2p':
                gate = [Gate.Y2p, Gate.Y2p]
            elif self.tomography_index == 'Y2p-Xp':
                gate = [Gate.Y2p, Gate.Xp]
            elif self.tomography_index == 'I-X2p':
                gate = [Gate.I, Gate.X2p]
            elif self.tomography_index == 'Xp-X2p':
                gate = [Gate.Xp, Gate.X2p]
            elif self.tomography_index == 'I-Y2p':
                gate = [Gate.I, Gate.Y2p]
            elif self.tomography_index == 'Xp-Y2p':
                gate = [Gate.Xp, Gate.Y2p]
            elif self.tomography_index == 'I-I':
                gate = [Gate.I, Gate.I]
            elif self.tomography_index == 'Xm-I':
                gate = [Gate.Xm, Gate.I]
            elif self.tomography_index == 'I-Xm':
                gate = [Gate.I, Gate.Xm]
            elif self.tomography_index == 'X2m-I':
                gate = [Gate.X2m, Gate.I]
            elif self.tomography_index == 'X2m-X2m':
                gate = [Gate.X2m, Gate.X2m]
            elif self.tomography_index == 'X2m-Y2m':
                gate = [Gate.X2m, Gate.Y2m]
            elif self.tomography_index == 'X2m-Xm':
                gate = [Gate.X2m, Gate.Xm]
            elif self.tomography_index == 'Y2m-I':
                gate = [Gate.Y2m, Gate.I]
            elif self.tomography_index == 'Y2m-X2m':
                gate = [Gate.Y2m, Gate.X2m]
            elif self.tomography_index == 'Y2m-Y2m':
                gate = [Gate.Y2m, Gate.Y2m]
            elif self.tomography_index == 'Y2m-Xm':
                gate = [Gate.Y2m, Gate.Xm]
            elif self.tomography_index == 'I-X2m':
                gate = [Gate.I, Gate.X2m]
            elif self.tomography_index == 'Xm-X2m':
                gate = [Gate.Xm, Gate.X2m]
            elif self.tomography_index == 'I-Y2m':
                gate = [Gate.I, Gate.Y2m]
            elif self.tomography_index == 'Xm-Y2m':
                gate = [Gate.Xm, Gate.Y2m]
            sequence.add_gate([qubitID1, qubitID2], gate)

        elif self.tomography_scheme == 'Two qubit (36 pulse set)':
            qubitID1 = self.twoQBtomoID1 - 1
            qubitID2 = self.twoQBtomoID2 - 1
            gate = [None, None]

            if self.tomography_index == 'I-I':
                gate = [Gate.I, Gate.I]
            elif self.tomography_index == 'Xp-I':
                gate = [Gate.Xp, Gate.I]
            elif self.tomography_index == 'X2p-I':
                gate = [Gate.X2p, Gate.I]
            elif self.tomography_index == 'X2m-I':
                gate = [Gate.X2m, Gate.I]
            elif self.tomography_index == 'Y2p-I':
                gate = [Gate.Y2p, Gate.I]
            elif self.tomography_index == 'Y2m-I':
                gate = [Gate.Y2m, Gate.I]
            elif self.tomography_index == 'Id-Xp':
                gate = [Gate.I, Gate.Xp]
            elif self.tomography_index == 'Xp-Xp':
                gate = [Gate.Xp, Gate.Xp]
            elif self.tomography_index == 'X2p-Xp':
                gate = [Gate.X2p, Gate.Xp]
            elif self.tomography_index == 'X2m-Xp':
                gate = [Gate.X2m, Gate.Xp]
            elif self.tomography_index == 'Y2p-Xp':
                gate = [Gate.Y2p, Gate.Xp]
            elif self.tomography_index == 'Y2m-Xp':
                gate = [Gate.Y2m, Gate.Xp]
            elif self.tomography_index == 'I-X2p':
                gate = [Gate.I, Gate.X2p]
            elif self.tomography_index == 'Xp-X2p':
                gate = [Gate.Xp, Gate.X2p]
            elif self.tomography_index == 'X2p-X2p':
                gate = [Gate.X2p, Gate.X2p]
            elif self.tomography_index == 'X2m-X2p':
                gate = [Gate.X2m, Gate.X2p]
            elif self.tomography_index == 'Y2p-Y2p':
                gate = [Gate.Y2p, Gate.Y2p]
            elif self.tomography_index == 'Y2m-Y2p':
                gate = [Gate.Y2m, Gate.Y2p]
            elif self.tomography_index == 'I-X2m':
                gate = [Gate.I, Gate.X2m]
            elif self.tomography_index == 'Xp-X2m':
                gate = [Gate.Xp, Gate.X2m]
            elif self.tomography_index == 'X2p-X2m':
                gate = [Gate.X2p, Gate.X2m]
            elif self.tomography_index == 'X2m-X2m':
                gate = [Gate.X2m, Gate.X2m]
            elif self.tomography_index == 'Y2p-X2m':
                gate = [Gate.Y2p, Gate.X2m]
            elif self.tomography_index == 'Y2m-X2m':
                gate = [Gate.Y2m, Gate.X2m]
            elif self.tomography_index == 'I-Y2p':
                gate = [Gate.I, Gate.Y2p]
            elif self.tomography_index == 'Xp-Y2p':
                gate = [Gate.Xp, Gate.Y2p]
            elif self.tomography_index == 'X2p-Y2p':
                gate = [Gate.X2p, Gate.Y2p]
            elif self.tomography_index == 'X2m-Y2p':
                gate = [Gate.X2m, Gate.Y2p]
            elif self.tomography_index == 'Y2p-Y2p':
                gate = [Gate.Y2p, Gate.Y2p]
            elif self.tomography_index == 'Y2m-Y2p':
                gate = [Gate.Y2m, Gate.Y2p]
            elif self.tomography_index == 'I-Y2m':
                gate = [Gate.I, Gate.Y2m]
            elif self.tomography_index == 'Xp-Y2m':
                gate = [Gate.Xp, Gate.Y2m]
            elif self.tomography_index == 'X2p-Y2m':
                gate = [Gate.X2p, Gate.Y2m]
            elif self.tomography_index == 'X2m-Y2m':
                gate = [Gate.X2m, Gate.Y2m]
            elif self.tomography_index == 'Y2p-Y2m':
                gate = [Gate.Y2p, Gate.Y2m]
            elif self.tomography_index == 'Y2m-Y2m':
                gate = [Gate.Y2m, Gate.Y2m]
            sequence.add_gate([qubitID1, qubitID2], gate)


if __name__ == '__main__':
    pass
