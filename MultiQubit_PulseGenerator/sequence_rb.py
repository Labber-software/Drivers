#!/usr/bin/env python3
import logging
import random as rnd

import numpy as np

from gates import Gate
from sequence import Sequence

log = logging.getLogger('LabberDriver')


def add_singleQ_clifford(index, gate_seq, pad_with_I=True):
    """Add single qubit clifford (24)."""
    length_before = len(gate_seq)
    # Paulis
    if index == 0:
        gate_seq.append(Gate.I)
    elif index == 1:
        gate_seq.append(Gate.Xp)
    elif index == 2:
        gate_seq.append(Gate.Yp)
    elif index == 3:
        gate_seq.append(Gate.Xp)
        gate_seq.append(Gate.Yp)

    # 2pi/3 rotations
    elif index == 4:
        gate_seq.append(Gate.Y2p)
        gate_seq.append(Gate.X2p)
    elif index == 5:
        gate_seq.append(Gate.Y2m)
        gate_seq.append(Gate.X2p)
    elif index == 6:
        gate_seq.append(Gate.Y2p)
        gate_seq.append(Gate.X2m)
    elif index == 7:
        gate_seq.append(Gate.Y2m)
        gate_seq.append(Gate.X2m)
    elif index == 8:
        gate_seq.append(Gate.X2p)
        gate_seq.append(Gate.Y2p)
    elif index == 9:
        gate_seq.append(Gate.X2m)
        gate_seq.append(Gate.Y2p)
    elif index == 10:
        gate_seq.append(Gate.X2p)
        gate_seq.append(Gate.Y2m)
    elif index == 11:
        gate_seq.append(Gate.X2m)
        gate_seq.append(Gate.Y2m)

    # pi/2 rotations
    elif index == 12:
        gate_seq.append(Gate.X2p)
    elif index == 13:
        gate_seq.append(Gate.X2m)
    elif index == 14:
        gate_seq.append(Gate.Y2p)
    elif index == 15:
        gate_seq.append(Gate.Y2m)
    elif index == 16:
        gate_seq.append(Gate.X2p)
        gate_seq.append(Gate.Y2p)
        gate_seq.append(Gate.X2m)
    elif index == 17:
        gate_seq.append(Gate.X2p)
        gate_seq.append(Gate.Y2m)
        gate_seq.append(Gate.X2m)

    # Hadamard-Like
    elif index == 18:
        gate_seq.append(Gate.Y2p)
        gate_seq.append(Gate.Xp)
    elif index == 19:
        gate_seq.append(Gate.Y2m)
        gate_seq.append(Gate.Xp)
    elif index == 20:
        gate_seq.append(Gate.X2p)
        gate_seq.append(Gate.Yp)
    elif index == 21:
        gate_seq.append(Gate.X2m)
        gate_seq.append(Gate.Yp)
    elif index == 22:
        gate_seq.append(Gate.X2p)
        gate_seq.append(Gate.Y2p)
        gate_seq.append(Gate.X2p)
    elif index == 23:
        gate_seq.append(Gate.X2m)
        gate_seq.append(Gate.Y2p)
        gate_seq.append(Gate.X2m)
    else:
        raise ValueError(
            'index is out of range. it should be smaller than 24 and greater'
            ' or equal to 0: ', str(index))

    length_after = len(gate_seq)
    if pad_with_I:
        # Force the clifford to have a length of 3 gates
        for i in range(3-(length_after-length_before)):
            gate_seq.append(Gate.I)


def add_twoQ_clifford(index, gate_seq_1, gate_seq_2):
    """Add single qubit clifford (11520 = 576 + 5184 + 5184 + 576)."""
    if (index < 0):
        raise ValueError(
            'index is out of range. it should be smaller than 11520 and '
            'greater or equal to 0: ', str(index))
    elif (index < 576):
        add_singleQ_based_twoQ_clifford(index, gate_seq_1, gate_seq_2)
    elif (index < 5184 + 576):
        add_CNOT_like_twoQ_clifford(index, gate_seq_1, gate_seq_2)
    elif (index < 5184 + 5184 + 576):
        add_iSWAP_like_twoQ_clifford(index, gate_seq_1, gate_seq_2)
    elif (index < 576 + 5184 + 5184 + 576):
        add_SWAP_like_twoQ_clifford(index, gate_seq_1, gate_seq_2)
    else:
        raise ValueError(
            'index is out of range. it should be smaller than 11520 and '
            'greater or equal to 0: ', str(index))

    pass


def add_singleQ_S1(index, gate_seq):
    """Add single qubit clifford from S1.

    (I-like-subset of single qubit clifford group) (3)
    """
    if index == 0:
        gate_seq.append(Gate.I)
        gate_seq.append(Gate.I)  # auxiliary
        gate_seq.append(Gate.I)  # auxiliary
    elif index == 1:
        gate_seq.append(Gate.X2p)
        gate_seq.append(Gate.Y2p)
        gate_seq.append(Gate.I)  # auxiliary
    elif index == 2:
        gate_seq.append(Gate.Y2m)
        gate_seq.append(Gate.X2m)
        gate_seq.append(Gate.I)  # auxiliary


def add_singleQ_S1_X2p(index, gate_seq):
    """Add single qubit clifford from S1_X2p.

    (X2p-like-subset of single qubit clifford group) (3)
    """
    if index == 0:
        gate_seq.append(Gate.X2p)
        gate_seq.append(Gate.I)  # auxiliary
        gate_seq.append(Gate.I)  # auxiliary
    elif index == 1:
        gate_seq.append(Gate.X2p)
        gate_seq.append(Gate.Y2p)
        gate_seq.append(Gate.X2p)
    elif index == 2:
        gate_seq.append(Gate.Y2m)
        gate_seq.append(Gate.I)  # auxiliary
        gate_seq.append(Gate.I)  # auxiliary


def add_singleQ_S1_Y2p(index, gate_seq):
    """Add single qubit clifford from S1_Y2p.

    (Y2p-like-subset of single qubit clifford group) (3)
    """
    if index == 0:
        gate_seq.append(Gate.Y2p)
        gate_seq.append(Gate.I)  # auxiliary
        gate_seq.append(Gate.I)  # auxiliary
    elif index == 1:
        gate_seq.append(Gate.X2p)
        gate_seq.append(Gate.Yp)
        gate_seq.append(Gate.I)  # auxiliary
    elif index == 2:
        gate_seq.append(Gate.X2p)
        gate_seq.append(Gate.Y2m)
        gate_seq.append(Gate.X2m)


def add_singleQ_based_twoQ_clifford(index, gate_seq_1, gate_seq_2, **kwargs):
    """Add single-qubit-gates-only-based two Qubit Clifford.

    (24*24 = 576)
    (gate_seq_1: gate seq. of qubit #1, gate_seq_t: gate seq. of qubit #2)
    """
    index_1 = index % 24  # randomly sample from single qubit cliffords (24)
    # randomly sample from single qubit cliffords (24)
    index_2 = (index // 24) % 24
    add_singleQ_clifford(index_1, gate_seq_1)
    add_singleQ_clifford(index_2, gate_seq_2)


def add_CNOT_like_twoQ_clifford(index, gate_seq_1, gate_seq_2, **kwargs):
    """Add CNOT like two Qubit Clifford.

    (24*24*3*3 = 5184)
    (gate_seq_1: gate seq. of qubit #1, gate_seq_t: gate seq. of qubit #2)
    """
    index_1 = index % 3  # randomly sample from S1 (3)
    index_2 = (index // 3) % 3  # randomly sample from S1 (3)
    # randomly sample from single qubit cliffords (24)
    index_3 = (index // 3 // 3) % 24
    # randomly sample from single qubit cliffords (24)
    index_4 = (index // 3 // 3 // 24) % 24

    generator = kwargs.get('generator', 'CZ')
    if generator == 'CZ':
        add_singleQ_S1(index_1, gate_seq_1)
        add_singleQ_S1_Y2p(index_2, gate_seq_2)
        gate_seq_1.append(Gate.I)
        gate_seq_2.append(Gate.CZ)
        add_singleQ_clifford(index_3, gate_seq_1)
        add_singleQ_clifford(index_4, gate_seq_2)
    elif generator == 'iSWAP':
        pass


def add_iSWAP_like_twoQ_clifford(index, gate_seq_1, gate_seq_2, **kwargs):
    """Add iSWAP like two Qubit Clifford.

    (24*24*3*3 = 5184)
    (gate_seq_1: gate seq. of qubit #1, gate_seq_t: gate seq. of qubit #2)
    """
    generator = kwargs.get('generator', 'CZ')
    index_1 = index % 3  # randomly sample from S1_Y2p (3)
    index_2 = (index // 3) % 3  # randomly sample from S1_X2p(3)
    # randomly sample from single qubit cliffords (24)
    index_3 = (index // 3 // 3) % 24
    # randomly sample from single qubit cliffords (24)
    index_4 = (index // 3 // 3 // 24) % 24

    if generator == 'CZ':
        add_singleQ_S1_Y2p(index_1, gate_seq_1)
        add_singleQ_S1_X2p(index_2, gate_seq_2)
        gate_seq_1.append(Gate.I)
        gate_seq_2.append(Gate.CZ)
        gate_seq_1.append(Gate.Y2p)
        gate_seq_2.append(Gate.X2m)
        gate_seq_1.append(Gate.I)
        gate_seq_2.append(Gate.CZ)
        add_singleQ_clifford(index_3, gate_seq_1)
        add_singleQ_clifford(index_4, gate_seq_2)
    elif generator == 'iSWAP':
        pass


def add_SWAP_like_twoQ_clifford(index, gate_seq_1, gate_seq_2, **kwargs):
    """Add SWAP like two Qubit Clifford.

    (24*24*= 576)
    (gate_seq_1: gate seq. of qubit #1, gate_seq_t: gate seq. of qubit #2)
    """
    index_1 = index % 24  # randomly sample from single qubit cliffords (24)
    # randomly sample from single qubit cliffords (24)
    index_2 = (index // 24) % 24
    generator = kwargs.get('generator', 'CZ')
    if generator == 'CZ':
        gate_seq_1.append(Gate.I)
        gate_seq_2.append(Gate.Y2p)
        gate_seq_1.append(Gate.I)
        gate_seq_2.append(Gate.CZ)
        gate_seq_1.append(Gate.Y2p)
        gate_seq_2.append(Gate.Y2m)
        gate_seq_1.append(Gate.I)
        gate_seq_2.append(Gate.CZ)
        gate_seq_1.append(Gate.Y2m)
        gate_seq_2.append(Gate.Y2p)
        gate_seq_1.append(Gate.I)
        gate_seq_2.append(Gate.CZ)
        add_singleQ_clifford(index_1, gate_seq_1)
        add_singleQ_clifford(index_2, gate_seq_2)

    elif generator == 'iSWAP':
        pass


class SingleQubit_RB(Sequence):
    """Single qubit randomized benchmarking."""

    prev_randomize = -999.999  # store the previous value
    prev_N_cliffords = -999.999  # store the previous value
    prev_interleave = -999.999  # store the previous value
    prev_interleaved_gate = -999.999  # store the previous value
    prev_sequence = ''
    prev_gate_seq = []

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms."""
        # get parameters
        sequence = config['Sequence']
        # Number of Cliffords to generate
        N_cliffords = int(config['Number of Cliffords'])
        randomize = config['Randomize']
        interleave = config['Interleave 1-QB Gate']
        if interleave is True:
            interleaved_gate = config['Interleaved 1-QB Gate']
        else:
            interleaved_gate = -999.999
        # generate new randomized clifford gates only if configuration changes
        if (self.prev_sequence != sequence or
            self.prev_randomize != randomize or
            self.prev_N_cliffords != N_cliffords or
            self.prev_interleave != interleave or
                self.prev_interleaved_gate != interleaved_gate):

            self.prev_randomize = randomize
            self.prev_N_cliffords = N_cliffords
            self.prev_interleave = interleave
            self.prev_sequence = sequence

            multi_gate_seq = []
            for n in range(self.n_qubit):
                # Generate 1QB RB sequence
                single_gate_seq = []
                for i in range(N_cliffords):
                    rndnum = rnd.randint(0, 23)
                    add_singleQ_clifford(rndnum, single_gate_seq,
                                         pad_with_I=False)
                    # If interleave gate,
                    if interleave is True:
                        self.prev_interleaved_gate = interleaved_gate
                        single_gate_seq.append(
                            Gate.__getattr__(interleaved_gate))

                recovery_gate = self.get_recovery_gate(single_gate_seq)
                single_gate_seq.append(recovery_gate)
                multi_gate_seq.append(single_gate_seq)

            # transpose list of lists
            multi_gate_seq = list(map(list, zip(*multi_gate_seq)))
            self.add_gates(multi_gate_seq)
            self.prev_gate_seq = multi_gate_seq
        else:
            self.add_gates(self.prev_gate_seq)

    def evaluate_sequence(self, gate_seq):
        """Evaluate Single Qubit Gate Sequence."""
# http://www.vcpc.univie.ac.at/~ian/hotlist/qc/talks/bloch-sphere-rotations.pdf
        singleQ_gate = np.matrix([[1, 0], [0, 1]])
        for i in range(len(gate_seq)):
            if (gate_seq[i] == Gate.I):
                pass
            elif (gate_seq[i] == Gate.X2p):
                singleQ_gate = np.matmul(
                    np.matrix([[1, -1j], [-1j, 1]]) / np.sqrt(2), singleQ_gate)
            elif (gate_seq[i] == Gate.X2m):
                singleQ_gate = np.matmul(
                    np.matrix([[1, 1j], [1j, 1]]) / np.sqrt(2), singleQ_gate)
            elif (gate_seq[i] == Gate.Y2p):
                singleQ_gate = np.matmul(
                    np.matrix([[1, -1], [1, 1]]) / np.sqrt(2), singleQ_gate)
            elif (gate_seq[i] == Gate.Y2m):
                singleQ_gate = np.matmul(
                    np.matrix([[1, 1], [-1, 1]]) / np.sqrt(2), singleQ_gate)
            elif (gate_seq[i] == Gate.Xp):
                singleQ_gate = np.matmul(
                    np.matrix([[0, -1j], [-1j, 0]]), singleQ_gate)
            elif (gate_seq[i] == Gate.Xm):
                singleQ_gate = np.matmul(
                    np.matrix([[0, 1j], [1j, 0]]), singleQ_gate)
            elif (gate_seq[i] == Gate.Yp):
                singleQ_gate = np.matmul(
                    np.matrix([[0, -1], [1, 0]]), singleQ_gate)
            elif (gate_seq[i] == Gate.Ym):
                singleQ_gate = np.matmul(
                    np.matrix([[0, 1], [-1, 0]]), singleQ_gate)
            elif (gate_seq[i] in (Gate.Zp, Gate.VZp)):
                singleQ_gate = np.matmul(
                    np.matrix([[-1j, 0], [0, 1j]]), singleQ_gate)
        return singleQ_gate

    def get_recovery_gate(self, gate_seq):
        """Get recovery gate."""
        qubit_state = np.matrix('1; 0')
        # initial state: ground state, following the QC community's convention
        qubit_state = np.matmul(self.evaluate_sequence(gate_seq), qubit_state)
        # find recovery gate which makes qubit_state return to initial state
        if (np.abs(np.linalg.norm(qubit_state.item((0, 0))) - 1) < 0.1):
            # ground state -> I
            recovery_gate = Gate.I
        elif (np.abs(np.linalg.norm(qubit_state.item((1, 0))) - 1) < 0.1):
            # excited state -> X Pi
            recovery_gate = Gate.Xp
        elif (np.linalg.norm(qubit_state.item((1, 0)) /
                             qubit_state.item((0, 0)) + 1) < 0.1):
            # X State  -> Y +Pi/2
            recovery_gate = Gate.Y2p
        elif (np.linalg.norm(qubit_state.item((1, 0)) /
                             qubit_state.item((0, 0)) - 1) < 0.1):
            # -X State -> Y -Pi/2
            recovery_gate = Gate.Y2m
        elif (np.linalg.norm(qubit_state.item((1, 0)) /
                             qubit_state.item((0, 0)) + 1j) < 0.1):
            # Y State -> X -Pi/2
            recovery_gate = Gate.X2m
        elif (np.linalg.norm(qubit_state.item((1, 0)) /
                             qubit_state.item((0, 0)) - 1j) < 0.1):
            # -Y State -> X +Pi/2
            recovery_gate = Gate.X2p
        else:
            raise InstrumentDriver.Error(
                'Error in calculating recovery gate. qubit state:' +
                str(qubit_state))
        return recovery_gate


class TwoQubit_RB(Sequence):
    """Two qubit randomized benchmarking."""

    prev_randomize = -999.999  # store the previous value
    prev_N_cliffords = -999.999  # store the previous value
    prev_interleave = -999.999  # store the previous value
    prev_interleaved_gate = -999.999  # store the previous value
    prev_sequence = ''
    prev_gate_seq = []

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms."""
        # get parameters
        sequence = config['Sequence']
        qubits_to_benchmark = np.fromstring(
            config['Qubits to Benchmark'], dtype=int, sep='-')
        # Number of Cliffords to generate
        N_cliffords = int(config['Number of Cliffords'])
        randomize = config['Randomize']
        interleave = config['Interleave 2-QB Gate']
        if interleave is True:
            interleaved_gate = config['Interleaved 2-QB Gate']
        else:
            interleaved_gate = -999.999

        # generate new randomized clifford gates only if configuration changes
        if (self.prev_sequence != sequence or
            self.prev_randomize != randomize or
            self.prev_N_cliffords != N_cliffords or
            self.prev_interleave != interleave or
                self.prev_interleaved_gate != interleaved_gate):

            self.prev_randomize = randomize
            self.prev_N_cliffords = N_cliffords
            self.prev_interleave = interleave
            self.prev_sequence = sequence

            multi_gate_seq = []

            # Generate 2QB RB sequence
            gate_seq_1 = []
            gate_seq_2 = []
            for i in range(N_cliffords):
                rndnum = rnd.randint(0, 11519)
                add_twoQ_clifford(rndnum, gate_seq_1, gate_seq_2)
                # If interleave gate,
                if interleave is True:
                    self.prev_interleaved_gate = interleaved_gate
                    if interleaved_gate == 'CZ':
                        gate_seq_1.append(Gate.I)
                        gate_seq_2.append(Gate.CZ)
                    elif interleaved_gate == 'CZEcho':
                        # CZEcho is a composite gate, so get each gate
                        gate = Gate.CZEcho.value
                        for g in gate.sequence:
                            gate_seq_1.append(g[0])
                            gate_seq_2.append(g[1])

            # get recovery gate seq
            (recovery_seq_1, recovery_seq_2) = self.get_recovery_gate(
                gate_seq_1, gate_seq_2)
            gate_seq_1.extend(recovery_seq_1)
            gate_seq_2.extend(recovery_seq_2)

            # Assign two qubit gate sequence to where we want
            if (self.n_qubit > qubits_to_benchmark[0]):
                for i in range(qubits_to_benchmark[0] - 1):
                    multi_gate_seq.append([None] * len(gate_seq_1))
                multi_gate_seq.append(gate_seq_2)
                multi_gate_seq.append(gate_seq_1)
                for i in range(self.n_qubit - qubits_to_benchmark[1]):
                    multi_gate_seq.append([None] * len(gate_seq_1))
            else:
                raise ValueError(
                    '"Number of qubits" should be bigger than'
                    '"Qubits to Benchmark"')

            # transpose list of lists
            multi_gate_seq = list(map(list, zip(*multi_gate_seq)))

            # self.add_gates(multi_gate_seq)
            for gates in multi_gate_seq:
                if gates[0] == Gate.CZ:
                    self.add_gate(qubit=[0, 1], gate=gates[0])
                else:
                    self.add_gate(qubit=[0, 1], gate=gates)
            self.prev_gate_seq = multi_gate_seq
        else:
            for gates in self.prev_gate_seq:
                if gates[0] == Gate.CZ:
                    self.add_gate(qubit=[0, 1], gate=gates[0])
                else:
                    self.add_gate(qubit=[0, 1], gate=gates)

    def evaluate_sequence(self, gate_seq_1, gate_seq_2):
        """Evaulate Two Qubit Gate Sequence."""
        twoQ_gate = np.matrix(
            [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
        for i in range(len(gate_seq_1)):
            gate_1 = np.matrix([[1, 0], [0, 1]])
            gate_2 = np.matrix([[1, 0], [0, 1]])
            if (gate_seq_1[i] == Gate.I):
                pass
            elif (gate_seq_1[i] == Gate.X2p):
                gate_1 = np.matmul(
                    np.matrix([[1, -1j], [-1j, 1]]) / np.sqrt(2), gate_1)
            elif (gate_seq_1[i] == Gate.X2m):
                gate_1 = np.matmul(
                    np.matrix([[1, 1j], [1j, 1]]) / np.sqrt(2), gate_1)
            elif (gate_seq_1[i] == Gate.Y2p):
                gate_1 = np.matmul(
                    np.matrix([[1, -1], [1, 1]]) / np.sqrt(2), gate_1)
            elif (gate_seq_1[i] == Gate.Y2m):
                gate_1 = np.matmul(
                    np.matrix([[1, 1], [-1, 1]]) / np.sqrt(2), gate_1)
            elif (gate_seq_1[i] == Gate.Xp):
                gate_1 = np.matmul(np.matrix([[0, -1j], [-1j, 0]]), gate_1)
            elif (gate_seq_1[i] == Gate.Xm):
                gate_1 = np.matmul(np.matrix([[0, 1j], [1j, 0]]), gate_1)
            elif (gate_seq_1[i] == Gate.Yp):
                gate_1 = np.matmul(np.matrix([[0, -1], [1, 0]]), gate_1)
            elif (gate_seq_1[i] == Gate.Ym):
                gate_1 = np.matmul(np.matrix([[0, 1], [-1, 0]]), gate_1)

            if (gate_seq_2[i] == Gate.I):
                pass
            elif (gate_seq_2[i] == Gate.X2p):
                gate_2 = np.matmul(
                    np.matrix([[1, -1j], [-1j, 1]]) / np.sqrt(2), gate_2)
            elif (gate_seq_2[i] == Gate.X2m):
                gate_2 = np.matmul(
                    np.matrix([[1, 1j], [1j, 1]]) / np.sqrt(2), gate_2)
            elif (gate_seq_2[i] == Gate.Y2p):
                gate_2 = np.matmul(
                    np.matrix([[1, -1], [1, 1]]) / np.sqrt(2), gate_2)
            elif (gate_seq_2[i] == Gate.Y2m):
                gate_2 = np.matmul(
                    np.matrix([[1, 1], [-1, 1]]) / np.sqrt(2), gate_2)
            elif (gate_seq_2[i] == Gate.Xp):
                gate_2 = np.matmul(np.matrix([[0, -1j], [-1j, 0]]), gate_2)
            elif (gate_seq_2[i] == Gate.Xm):
                gate_2 = np.matmul(np.matrix([[0, 1j], [1j, 0]]), gate_2)
            elif (gate_seq_2[i] == Gate.Yp):
                gate_2 = np.matmul(np.matrix([[0, -1], [1, 0]]), gate_2)
            elif (gate_seq_2[i] == Gate.Ym):
                gate_2 = np.matmul(np.matrix([[0, 1], [-1, 0]]), gate_2)

            gate_12 = np.kron(gate_1, gate_2)
            if (gate_seq_1[i] == Gate.CZ or gate_seq_2[i] == Gate.CZ):
                gate_12 = np.matmul(
                    np.matrix([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0],
                               [0, 0, 0, -1]]), gate_12)

            twoQ_gate = np.matmul(gate_12, twoQ_gate)

        return twoQ_gate

    def get_recovery_gate(self, gate_seq_1, gate_seq_2):
        """Get recovery 2QB gate."""
        qubit_state = np.matrix(
            '1; 0; 0; 0')  # initial state: ground state |00>
        # initial state: ground state |00>
        qubit_state = np.matmul(self.evaluate_sequence(
            gate_seq_1, gate_seq_2), qubit_state)

        # find recovery gate which makes qubit_state return to initial state
        total_num_cliffords = 11520
        recovery_seq_1 = []
        recovery_seq_2 = []
        # Search recovery gate in two Qubit clifford group
        for i in range(total_num_cliffords):
            add_twoQ_clifford(i, recovery_seq_1, recovery_seq_2)
            qubit_final_state = np.matmul(self.evaluate_sequence(
                recovery_seq_1, recovery_seq_2), qubit_state)
            # numerical error threshold: 1e-4
            if np.abs(np.abs(qubit_final_state[0]) - 1) < 1e-6:
                break
            else:
                recovery_seq_1 = []
                recovery_seq_2 = []

        if (recovery_seq_1 == [] and recovery_seq_2 == []):
            recovery_seq_1 = [None]
            recovery_seq_2 = [None]
        return (recovery_seq_1, recovery_seq_2)


if __name__ == '__main__':
    pass
