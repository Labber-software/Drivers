#!/usr/bin/env python3
import logging

import gates

log = logging.getLogger('LabberDriver')


class ProcessTomography(object):
    """This class handles qubit control prepulses for process tomography."""

    def __init__(self, prepulse_index=0, qubit1ID=0, qubit2ID=1,
                 nProcessTomoQubits=1, tomoscheme='Single qubit'):

        self.prepulse_index = prepulse_index
        self.qubit1ID = qubit1ID
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
            gate = None

            whichGate = self.prepulse_index[0]
            gate = self.gate_from_index(whichGate)

            log.info('Gate is: {}'.format(gate))
            sequence.add_gate(qubitID1, gate)

        elif self.tomography_scheme in ['Two qubit (9 pulse set)',
                                        'Two qubit (30 pulse set)',
                                        'Two qubit (36 pulse set)']:
            qubitID1 = self.qubit1ID - 1
            qubitID2 = self.qubit2ID - 1

            whichGate = self.prepulse_index[:2]
            gate = self.gate_from_index(whichGate)

            sequence.add_gate([qubitID1, qubitID2], gate)
            # sequence.add_gate(qubitID1, gate)
            # sequence.add_gate(qubitID2, gate)

    def gate_from_index(self, whichGate):
        """Help function to translate prepulse index into gate.
        Parameters
        ----------
        whichGate: str
            Elements of list should be in ['0', '1', 'X', 'Y'],
            indicating which state to prepare
        """

        if self.tomography_scheme == 'Single qubit':
            indices = list(whichGate)
            gate = None
            for index in indices:
                if index == '0':
                    gate = gates.I
                elif index == '1':
                    gate = gates.Xp
                elif index == 'X':
                    gate = gates.Y2p
                elif index == 'Y':
                    gate = gates.X2m
                else:
                    raise ValueError("Gate should be in ['0', '1', 'X', or 'Y']")
        else:
            indices = list(whichGate)
            gate = []
            for index in indices:
                if index == '0':
                    gate.append(gates.I)
                elif index == '1':
                    gate.append(gates.Xp)
                elif index == 'X':
                    gate.append(gates.Y2p)
                elif index == 'Y':
                    gate.append(gates.X2m)
                else:
                    raise ValueError("Gate should be in ['0', '1', 'X', or 'Y']")

        return gate


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
                gate = gates.I  # measure Z polarization
            elif self.tomography_index == 'Y: X2p':
                gate = gates.X2p  # measure Y polarization
            elif self.tomography_index == 'X: Y2m':
                gate = gates.Y2m  # measure X polarization
            sequence.add_gate(qubitID, gate)

        elif self.tomography_scheme == 'Two qubit (9 pulse set)':
            qubitID1 = self.twoQBtomoID1 - 1
            qubitID2 = self.twoQBtomoID2 - 1
            gate = [None, None]

            if self.tomography_index == 'XX: Y2m-Y2m':
                gate = [gates.Y2m, gates.Y2m]
            elif self.tomography_index == 'YX: X2p-Y2m':
                gate = [gates.X2p, gates.Y2m]
            elif self.tomography_index == 'ZX: I-Y2m':
                gate = [gates.I, gates.Y2m]
            elif self.tomography_index == 'XY: Y2m-X2p':
                gate = [gates.Y2m, gates.X2p]
            elif self.tomography_index == 'YY: X2p-X2p':
                gate = [gates.X2p, gates.X2p]
            elif self.tomography_index == 'ZY: I-X2p':
                gate = [gates.I, gates.X2p]
            elif self.tomography_index == 'XZ: Y2m-I':
                gate = [gates.Y2m, gates.I]
            elif self.tomography_index == 'YZ: X2p-I':
                gate = [gates.X2p, gates.I]
            elif self.tomography_index == 'ZZ: I-I':
                gate = [gates.I, gates.I]
            sequence.add_gate([qubitID1, qubitID2], gate)

        elif self.tomography_scheme == 'Two qubit (30 pulse set)':
            qubitID1 = self.twoQBtomoID1 - 1
            qubitID2 = self.twoQBtomoID2 - 1
            gate = [None, None]

            if self.tomography_index == 'I-I':
                gate = [gates.I, gates.I]
            elif self.tomography_index == 'Xp-I':
                gate = [gates.Xp, gates.I]
            elif self.tomography_index == 'I-Xp':
                gate = [gates.I, gates.Xp]
            elif self.tomography_index == 'X2p-I':
                gate = [gates.X2p, gates.I]
            elif self.tomography_index == 'X2p-X2p':
                gate = [gates.X2p, gates.X2p]
            elif self.tomography_index == 'X2p-Y2p':
                gate = [gates.X2p, gates.Y2p]
            elif self.tomography_index == 'X2p-Xp':
                gate = [gates.X2p, gates.Xp]
            elif self.tomography_index == 'Y2p-I':
                gate = [gates.Y2p, gates.I]
            elif self.tomography_index == 'Y2p-X2p':
                gate = [gates.Y2p, gates.X2p]
            elif self.tomography_index == 'Y2p-Y2p':
                gate = [gates.Y2p, gates.Y2p]
            elif self.tomography_index == 'Y2p-Xp':
                gate = [gates.Y2p, gates.Xp]
            elif self.tomography_index == 'I-X2p':
                gate = [gates.I, gates.X2p]
            elif self.tomography_index == 'Xp-X2p':
                gate = [gates.Xp, gates.X2p]
            elif self.tomography_index == 'I-Y2p':
                gate = [gates.I, gates.Y2p]
            elif self.tomography_index == 'Xp-Y2p':
                gate = [gates.Xp, gates.Y2p]
            elif self.tomography_index == 'I-I':
                gate = [gates.I, gates.I]
            elif self.tomography_index == 'Xm-I':
                gate = [gates.Xm, gates.I]
            elif self.tomography_index == 'I-Xm':
                gate = [gates.I, gates.Xm]
            elif self.tomography_index == 'X2m-I':
                gate = [gates.X2m, gates.I]
            elif self.tomography_index == 'X2m-X2m':
                gate = [gates.X2m, gates.X2m]
            elif self.tomography_index == 'X2m-Y2m':
                gate = [gates.X2m, gates.Y2m]
            elif self.tomography_index == 'X2m-Xm':
                gate = [gates.X2m, gates.Xm]
            elif self.tomography_index == 'Y2m-I':
                gate = [gates.Y2m, gates.I]
            elif self.tomography_index == 'Y2m-X2m':
                gate = [gates.Y2m, gates.X2m]
            elif self.tomography_index == 'Y2m-Y2m':
                gate = [gates.Y2m, gates.Y2m]
            elif self.tomography_index == 'Y2m-Xm':
                gate = [gates.Y2m, gates.Xm]
            elif self.tomography_index == 'I-X2m':
                gate = [gates.I, gates.X2m]
            elif self.tomography_index == 'Xm-X2m':
                gate = [gates.Xm, gates.X2m]
            elif self.tomography_index == 'I-Y2m':
                gate = [gates.I, gates.Y2m]
            elif self.tomography_index == 'Xm-Y2m':
                gate = [gates.Xm, gates.Y2m]
            sequence.add_gate([qubitID1, qubitID2], gate)

        elif self.tomography_scheme == 'Two qubit (36 pulse set)':
            qubitID1 = self.twoQBtomoID1 - 1
            qubitID2 = self.twoQBtomoID2 - 1
            gate = [None, None]

            if self.tomography_index == 'I-I':
                gate = [gates.I, gates.I]
            elif self.tomography_index == 'Xp-I':
                gate = [gates.Xp, gates.I]
            elif self.tomography_index == 'X2p-I':
                gate = [gates.X2p, gates.I]
            elif self.tomography_index == 'X2m-I':
                gate = [gates.X2m, gates.I]
            elif self.tomography_index == 'Y2p-I':
                gate = [gates.Y2p, gates.I]
            elif self.tomography_index == 'Y2m-I':
                gate = [gates.Y2m, gates.I]
            elif self.tomography_index == 'Id-Xp':
                gate = [gates.I, gates.Xp]
            elif self.tomography_index == 'Xp-Xp':
                gate = [gates.Xp, gates.Xp]
            elif self.tomography_index == 'X2p-Xp':
                gate = [gates.X2p, gates.Xp]
            elif self.tomography_index == 'X2m-Xp':
                gate = [gates.X2m, gates.Xp]
            elif self.tomography_index == 'Y2p-Xp':
                gate = [gates.Y2p, gates.Xp]
            elif self.tomography_index == 'Y2m-Xp':
                gate = [gates.Y2m, gates.Xp]
            elif self.tomography_index == 'I-X2p':
                gate = [gates.I, gates.X2p]
            elif self.tomography_index == 'Xp-X2p':
                gate = [gates.Xp, gates.X2p]
            elif self.tomography_index == 'X2p-X2p':
                gate = [gates.X2p, gates.X2p]
            elif self.tomography_index == 'X2m-X2p':
                gate = [gates.X2m, gates.X2p]
            elif self.tomography_index == 'Y2p-Y2p':
                gate = [gates.Y2p, gates.Y2p]
            elif self.tomography_index == 'Y2m-Y2p':
                gate = [gates.Y2m, gates.Y2p]
            elif self.tomography_index == 'I-X2m':
                gate = [gates.I, gates.X2m]
            elif self.tomography_index == 'Xp-X2m':
                gate = [gates.Xp, gates.X2m]
            elif self.tomography_index == 'X2p-X2m':
                gate = [gates.X2p, gates.X2m]
            elif self.tomography_index == 'X2m-X2m':
                gate = [gates.X2m, gates.X2m]
            elif self.tomography_index == 'Y2p-X2m':
                gate = [gates.Y2p, gates.X2m]
            elif self.tomography_index == 'Y2m-X2m':
                gate = [gates.Y2m, gates.X2m]
            elif self.tomography_index == 'I-Y2p':
                gate = [gates.I, gates.Y2p]
            elif self.tomography_index == 'Xp-Y2p':
                gate = [gates.Xp, gates.Y2p]
            elif self.tomography_index == 'X2p-Y2p':
                gate = [gates.X2p, gates.Y2p]
            elif self.tomography_index == 'X2m-Y2p':
                gate = [gates.X2m, gates.Y2p]
            elif self.tomography_index == 'Y2p-Y2p':
                gate = [gates.Y2p, gates.Y2p]
            elif self.tomography_index == 'Y2m-Y2p':
                gate = [gates.Y2m, gates.Y2p]
            elif self.tomography_index == 'I-Y2m':
                gate = [gates.I, gates.Y2m]
            elif self.tomography_index == 'Xp-Y2m':
                gate = [gates.Xp, gates.Y2m]
            elif self.tomography_index == 'X2p-Y2m':
                gate = [gates.X2p, gates.Y2m]
            elif self.tomography_index == 'X2m-Y2m':
                gate = [gates.X2m, gates.Y2m]
            elif self.tomography_index == 'Y2p-Y2m':
                gate = [gates.Y2p, gates.Y2m]
            elif self.tomography_index == 'Y2m-Y2m':
                gate = [gates.Y2m, gates.Y2m]
            sequence.add_gate([qubitID1, qubitID2], gate)


if __name__ == '__main__':
    pass
