#!/usr/bin/env python3
from sequence import Sequence
from gates import Gate
import random as rnd
import numpy as np
# add logger, to allow logging to Labber's instrument log 
import logging
log = logging.getLogger('LabberDriver')



class SingleQubit_RB(Sequence):
    """Sequence for benchmarking single qubit gates in multiple qubits"""

    prev_randomize = -999.999 #store the previous value
    prev_N_cliffords = -999.999 #store the previous value

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms"""
        # get parameters
        N_cliffords = int(config['Number of Cliffords']) # Number of Cliffords to generate
        randomize = config['Randomize'] 

        # generate new randomized clifford gates only if "Randomize" changes or "Number of Cliffords" changes
        if (self.prev_randomize != randomize or self.prev_N_cliffords != N_cliffords):
            self.prev_randomize = randomize
            self.prev_N_cliffords = N_cliffords
            multi_gate_seq = []
            for n in range(self.n_qubit):
                #Generate 1QB RB sequence 
                single_gate_seq = []
                for i in range(N_cliffords):
                    rndnum  = rnd.randint(1, 24)
                    ### Paulis
                    if rndnum == 1:
                        single_gate_seq.append(Gate.I)
                    elif rndnum == 2:
                        single_gate_seq.append(Gate.Xp)
                    elif rndnum == 3:
                        single_gate_seq.append(Gate.Yp)
                    elif rndnum == 4:
                        single_gate_seq.append(Gate.Xp)
                        single_gate_seq.append(Gate.Yp)
                    ### 2pi/3 rotations
                    elif rndnum == 5:
                        single_gate_seq.append(Gate.Y2p)
                        single_gate_seq.append(Gate.X2p)
                    elif rndnum == 6:
                        single_gate_seq.append(Gate.Y2m)
                        single_gate_seq.append(Gate.X2p)
                    elif rndnum == 7:
                        single_gate_seq.append(Gate.Y2p)
                        single_gate_seq.append(Gate.X2m)
                    elif rndnum == 8:
                        single_gate_seq.append(Gate.Y2m)
                        single_gate_seq.append(Gate.X2m)
                    elif rndnum == 9:
                        single_gate_seq.append(Gate.X2p)
                        single_gate_seq.append(Gate.Y2p)
                    elif rndnum == 10:
                        single_gate_seq.append(Gate.X2m)
                        single_gate_seq.append(Gate.Y2p)
                    elif rndnum == 11:
                        single_gate_seq.append(Gate.X2p)
                        single_gate_seq.append(Gate.Y2m)
                    elif rndnum == 12:
                        single_gate_seq.append(Gate.X2m)
                        single_gate_seq.append(Gate.Y2m)
                    ### pi/2 rotations
                    elif rndnum == 13:
                        single_gate_seq.append(Gate.X2p)
                    elif rndnum == 14:
                        single_gate_seq.append(Gate.X2m)
                    elif rndnum == 15:
                        single_gate_seq.append(Gate.Y2p)
                    elif rndnum == 16:
                        single_gate_seq.append(Gate.Y2m)
                    elif rndnum == 17:
                        single_gate_seq.append(Gate.X2p)
                        single_gate_seq.append(Gate.Y2p)
                        single_gate_seq.append(Gate.X2m)
                    elif rndnum == 18:
                        single_gate_seq.append(Gate.X2p)
                        single_gate_seq.append(Gate.Y2m)
                        single_gate_seq.append(Gate.X2m)
                    ### Hadamard-Like
                    elif rndnum == 19:
                        single_gate_seq.append(Gate.Y2p)
                        single_gate_seq.append(Gate.Xp)
                    elif rndnum == 20:
                        single_gate_seq.append(Gate.Y2m)
                        single_gate_seq.append(Gate.Xp)
                    elif rndnum == 21:
                        single_gate_seq.append(Gate.X2p)
                        single_gate_seq.append(Gate.Yp)
                    elif rndnum == 22:
                        single_gate_seq.append(Gate.X2m)
                        single_gate_seq.append(Gate.Yp)
                    elif rndnum == 23:
                        single_gate_seq.append(Gate.X2p)
                        single_gate_seq.append(Gate.Y2p)
                        single_gate_seq.append(Gate.X2p)
                    elif rndnum == 24:
                        single_gate_seq.append(Gate.X2m)
                        single_gate_seq.append(Gate.Y2p)
                        single_gate_seq.append(Gate.X2m)

                recovery_gate = self.get_recovery_gate(single_gate_seq)
                single_gate_seq.append(recovery_gate)
                multi_gate_seq.append(single_gate_seq)

            multi_gate_seq = list(map(list, zip(*multi_gate_seq))) #transpose list of lists
            self.add_gates(multi_gate_seq)



    def get_recovery_gate(self,gate_seq):
        """calculate recovery gate"""
        qubit_state = np.matrix('1; 0') # initial state: ground state
        for i in range(len(gate_seq)):
            if (gate_seq[i] == Gate.I):
                qubit_state = qubit_state
            elif (gate_seq[i] == Gate.X2p):
                qubit_state = np.matmul(np.matrix([[1,-1j],[-1j,1]])/np.sqrt(2), qubit_state)
            elif (gate_seq[i] == Gate.X2m):
                qubit_state = np.matmul(np.matrix([[1,1j],[1j,1]])/np.sqrt(2), qubit_state)
            elif (gate_seq[i] == Gate.Y2p):
                qubit_state = np.matmul(np.matrix([[1,-1],[1,1]])/np.sqrt(2), qubit_state)
            elif (gate_seq[i] == Gate.Y2m):
                qubit_state = np.matmul(np.matrix([[1,1],[-1,1]])/np.sqrt(2), qubit_state)
            elif (gate_seq[i] == Gate.Xp):
                qubit_state = np.matmul(np.matrix([[0,1],[1,0]]), qubit_state)
            elif (gate_seq[i] == Gate.Xm):
                qubit_state = np.matmul(np.matrix([[0,1j],[1j,0]]), qubit_state)
            elif (gate_seq[i] == Gate.Yp):
                qubit_state = np.matmul(np.matrix([[0,-1],[1,0]]), qubit_state)
            elif (gate_seq[i] == Gate.Ym):
                qubit_state = np.matmul(np.matrix([[0,1],[-1,0]]), qubit_state)

        #find recovery gate which makes qubit_state return to the initial state
        if (np.abs(np.linalg.norm(qubit_state.item((0, 0))) - 1) < 0.1): # ground state -> I 
             recovery_gate = Gate.I
        elif (np.abs(np.linalg.norm(qubit_state.item((1, 0))) - 1) < 0.1): # excited state -> X Pi
             recovery_gate = Gate.Xp
        elif (np.linalg.norm(qubit_state.item((1, 0)) / qubit_state.item((0,0)) - 1) < 0.1): # X State  -> Y -Pi/2
             recovery_gate = Gate.Y2m
        elif (np.linalg.norm(qubit_state.item((1, 0)) / qubit_state.item((0,0)) + 1) < 0.1): # -X State -> Y +Pi/2
             recovery_gate = Gate.Y2p
        elif (np.linalg.norm(qubit_state.item((1, 0)) / qubit_state.item((0,0)) - 1j) < 0.1): # Y State -> X -Pi/2
             recovery_gate = Gate.X2p
        elif (np.linalg.norm(qubit_state.item((1, 0)) / qubit_state.item((0,0)) + 1j) < 0.1): # -Y State -> X +Pi/2
             recovery_gate = Gate.X2m
        else:
            raise InstrumentDriver.Error('Error in calculating recovery gate. qubit state:' + str(qubit_state))
        return recovery_gate


if __name__ == '__main__':
    pass
