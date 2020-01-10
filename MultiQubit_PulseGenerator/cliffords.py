import numpy as np
from numpy import matmul as mul
from numpy.linalg import inv as inv
from numpy.linalg import eig as eig
from numpy import tensordot as tensor
from numpy import dot
import pickle

import itertools
import sequence_rb
import gates


# list of Paulis in string representation
list_sSign = ['+','-'] #
list_sPauli = ['I','X','Y','Z']
list_s2QBPauli = list(itertools.product(list_sSign,list_sPauli, list_sPauli))

# list of Paulis, 1QB-gates, and 2QB-gates in np.matrix representation
dict_mPauli = {'I': np.matrix('1,0;0,1'),
    'X': np.matrix('0,1;1,0'),
    'Y': np.matrix('0,-1j;1j,0'),
    'Z': np.matrix('1,0;0,-1')}

dict_m1QBGate = {'I': np.matrix('1,0;0,1'),
    'X2p': 1/np.sqrt(2)*np.matrix('1,-1j;-1j,1'),
    'X2m': 1/np.sqrt(2)*np.matrix('1,1j;1j,1'),
    'Y2p': 1/np.sqrt(2)*np.matrix('1,-1;1,1'),
    'Y2m': 1/np.sqrt(2)*np.matrix('1,1;-1,1'),
    'Z2p': np.matrix('1,0;0,1j'),
    'Z2m': np.matrix('1,0;0,-1j'),
    'Xp': np.matrix('0,-1j;-1j,0'),
    'Xm': np.matrix('0,1j;1j,0'),
    'Yp': np.matrix('0,-1;1,0'),
    'Ym': np.matrix('0,1;-1,0'),
    'Zp': np.matrix('1,0;0,-1'),
    'Zm': np.matrix('1,0;0,-1')
    }
dict_m2QBGate = {'SWAP': np.matrix('1,0,0,0; 0,0,1,0; 0,1,0,0; 0,0,0,1'),
    'CZ': np.matrix('1,0,0,0; 0,1,0,0; 0,0,1,0; 0,0,0,-1'),
    'iSWAP': np.matrix('1,0,0,0; 0,0,1j,0; 0,1j,0,0; 0,0,0,1'),
    'CNOT': np.matrix('1,0,0,0; 0,1,0,0; 0,0,0,1; 0,0,1,0')}


def expect(_psi, _op):
    """
    Get the expectation value of the operator, given the quantum state

    Parameters
    ----------
    _psi: np.matrix
        the state vector of a quantum state
    _op: np.matrix
        a quantum operator

    Returns
    -------
    e_val: expectation value
    """
    return dot(_psi.H, dot(_op, _psi))[0,0]

def sPauli_to_mPauli(_sPaulis):
    """
    Convert from string-type Paulis to matrix-type Paulis

    Parameters
    ----------
    _sPaulis: string
        string representation of a quantum state
    _op: np.matrix
        quantum operator

    Returns
    -------
    e_val: expectation value
    """
    sign = _sPaulis[0]
    dim = len(_sPaulis) - 1
    _mPaulis = np.matrix([1])
    for i in range(1,len(_sPaulis)):
        if _sPaulis[i] == 'I':
            _mPaulis = np.kron(_mPaulis, dict_mPauli['I'])
        elif _sPaulis[i] == 'X':
            _mPaulis = np.kron(_mPaulis, dict_mPauli['X'])
        elif _sPaulis[i] == 'Y':
            _mPaulis = np.kron(_mPaulis, dict_mPauli['Y'])
        elif _sPaulis[i] == 'Z':
            _mPaulis = np.kron(_mPaulis, dict_mPauli['Z'])

    if sign == '+':
        return _mPaulis
    else:
        return -1.0 * _mPaulis

def Gate_to_strGate(_Gate):
    """
    represent Gate (defined in "gates.py") object in string-format.

    Parameters
    ----------
    Gate: gates.Gate
        Gate object

    Returns
    -------
    str_Gate: string
        string representation of the Gate
    """
    if (_Gate == gates.I):
        str_Gate = 'I'
    elif (_Gate == gates.Xp):
        str_Gate = 'Xp'
    elif (_Gate == gates.Xm):
        str_Gate = 'Xm'
    elif (_Gate == gates.X2p):
        str_Gate = 'X2p'
    elif (_Gate == gates.X2m):
        str_Gate = 'X2m'
    elif (_Gate == gates.Yp):
        str_Gate = 'Yp'
    elif (_Gate == gates.Ym):
        str_Gate = 'Ym'
    elif (_Gate == gates.Y2p):
        str_Gate = 'Y2p'
    elif (_Gate == gates.Y2m):
        str_Gate = 'Y2m'
    elif (_Gate == gates.Zp):
        str_Gate = 'Zp'
    elif (_Gate == gates.Zm):
        str_Gate = 'Zm'
    elif (_Gate == gates.Z2p):
        str_Gate = 'Z2p'
    elif (_Gate == gates.Z2m):
        str_Gate = 'Z2m'
    elif (_Gate == gates.CZ):
        str_Gate = 'CZ'
    elif (_Gate == gates.iSWAP):
        str_Gate = 'iSWAP'

    return str_Gate


def strGate_to_Gate(_strGate):
    """
    Convert from string-type Gates to Gate (defined in "gates.py") object

    Parameters
    ----------
    str_Gate: string
        string representation of the Gate

    Returns
    -------
    Gate: gates.Gate
        Gate object
    """
    if (_strGate == 'I'):
        g = gates.I
    elif (_strGate == 'Xp'):
        g = gates.Xp
    elif (_strGate == 'Xm'):
        g = gates.Xm
    elif (_strGate == 'X2p'):
        g = gates.X2p
    elif (_strGate == 'X2m'):
        g = gates.X2m
    elif (_strGate == 'Yp'):
        g = gates.Yp
    elif (_strGate == 'Ym'):
        g = gates.Ym
    elif (_strGate == 'Y2p'):
        g = gates.Y2p
    elif (_strGate == 'Y2m'):
        g = gates.Y2m
    elif (_strGate == 'Zp'):
        g = gates.Zp
    elif (_strGate == 'Zm'):
        g = gates.Zm
    elif (_strGate == 'Z2p'):
        g = gates.Z2p
    elif (_strGate == 'Z2m'):
        g = gates.Z2m
    elif (_strGate == 'CZ'):
        g = gates.CZ
    elif (_strGate == 'iSWAP'):
        g = gates.iSWAP

    return g

def get_stabilizer(_psi):
    """
    Get the stabilizer group corresponding the qubit_state

    Parameters
    ----------
    _psi: np.matrix
        The state vector of the qubit.
    Returns
    -------
    stabilizer: list
        The stabilizer group
    """
    stabilizer = []
    for _sPauli in list_s2QBPauli:
        _mPauli = sPauli_to_mPauli(_sPauli)
        _identity = np.identity(_mPauli.shape[0], dtype = complex)
        # if (np.abs(expect(_psi, _mPauli - _identity) - 0) < 1e-1): # check whether _mPauli is the stabilizer.
        if (np.abs(expect(_psi, _mPauli ) - 1) < 1e-6): # check whether _mPauli is the stabilizer.
            stabilizer.append(_sPauli)

    return stabilizer

def generate_2QB_Cliffords(_index, **kwargs):
    seq_QB1 = []
    seq_QB2 = []
    generator = kwargs.get('generator', 'CZ')
    sequence_rb.add_twoQ_clifford(_index, seq_QB1, seq_QB2, generator = generator)
    m2QBClifford = np.identity(4, dtype = complex)
    for i in range(len(seq_QB1)):
        _mGate = np.matrix([1])
        if (seq_QB1[i] == gates.CZ or seq_QB2[i] == gates.CZ ): # two qubit gates
            _mGate = np.kron(dict_m2QBGate['CZ'], _mGate)
        elif (seq_QB1[i] == gates.iSWAP or seq_QB2[i] == gates.iSWAP ): 
            _mGate = np.kron(dict_m2QBGate['iSWAP'], _mGate)
        else: # 1QB gates
            for g in [seq_QB2[i], seq_QB1[i]]:
                if (g == gates.I):
                    _mGate = np.kron(dict_m1QBGate['I'], _mGate)
                elif (g == gates.Xp):
                    _mGate = np.kron(dict_m1QBGate['Xp'], _mGate)
                elif (g == gates.Xm):
                    _mGate = np.kron(dict_m1QBGate['Xm'], _mGate)
                elif (g == gates.X2p):
                    _mGate = np.kron(dict_m1QBGate['X2p'], _mGate)
                elif (g == gates.X2m):
                    _mGate = np.kron(dict_m1QBGate['X2m'], _mGate)
                elif (g == gates.Yp):
                    _mGate = np.kron(dict_m1QBGate['Yp'], _mGate)
                elif (g == gates.Ym):
                    _mGate = np.kron(dict_m1QBGate['Ym'], _mGate)
                elif (g == gates.Y2p):
                    _mGate = np.kron(dict_m1QBGate['Y2p'], _mGate)
                elif (g == gates.Y2m):
                    _mGate = np.kron(dict_m1QBGate['Y2m'], _mGate)
                elif (g == gates.Zp):
                    _mGate = np.kron(dict_m1QBGate['Zp'], _mGate)
                elif (g == gates.Zm):
                    _mGate = np.kron(dict_m1QBGate['Zm'], _mGate)
                elif (g == gates.Z2p):
                    _mGate = np.kron(dict_m1QBGate['Z2p'], _mGate)
                elif (g == gates.Z2m):
                    _mGate = np.kron(dict_m1QBGate['Z2m'], _mGate)
        m2QBClifford = mul(_mGate, m2QBClifford)
    return (m2QBClifford)

def saveData(file_path, data):

    """
    Create a log file. (Use the built-in pickle module)

    Parameters
    ----------
    file_path: str
        path of the log file

    - data: arbitrary object
        arbitrary Python object which contains data

    Returns
    -------
    """

    with open(file_path, 'wb') as _output:
        pickle.dump(data, _output, pickle.HIGHEST_PROTOCOL)
    print('--- File Save Success! ---')
    print(file_path)

def loadData(file_path):

    """
    Load a log file. (Use the built-in pickle module)

    Parameters
    ----------
    file_path: str
        path of the log file


    Returns
    -------
    - data: arbitrary object
        arbitrary Python object which contains data
    """

    with open(file_path, 'rb') as _input:
        data = pickle.load(_input)
    print('--- File Load Success! --- ')
    print(file_path)
    return data

if __name__ == "__main__":
    # -------------------------------------------------------------------
    # ----- THIS IS FOR GENERATING RECOVERY CLIFFORD LOOK-UP TABLE ------
    # -------------------------------------------------------------------

    # Native 2QB Gate ('CZ' or 'iSWAP')
    generator = 'iSWAP'

    # Start with ground state
    psi_00 = np.matrix('1;0;0;0')
    psi_01 = np.matrix('0;1;0;0')
    psi_10 = np.matrix('0;0;1;0')
    psi_11 = np.matrix('0;0;0;1')

    N_2QBcliffords = 11520
    list_stabilizer = []
    list_psi = []
    list_recovery_gates_QB1 = []
    list_recovery_gates_QB2 = []
    cnt = 0

    # Apply 11520 different 2QB cliffords and get the corresponding stabilizer states
    for i in range(N_2QBcliffords):
        if (i/N_2QBcliffords > cnt):
            print('Running... %d %%'%(cnt*100))
            cnt = cnt+0.01
        g = generate_2QB_Cliffords(i, generator = generator)

        final_psi_00 = dot(g, psi_00)
        final_psi_01 = dot(g, psi_01)
        final_psi_10 = dot(g, psi_10)
        final_psi_11 = dot(g, psi_11)

        stabilizer = get_stabilizer(final_psi_00)

        # append only if the state is not in list_stablizier list.
        if (not (stabilizer in list_stabilizer)):
            list_stabilizer.append(stabilizer)
            list_psi.append(final_psi_00)
            # find the cheapest recovery clifford gates.
            print('stabilizer state: '+ str(stabilizer))
            print('Before recovery, final_psi_00: ' + str(final_psi_00.flatten()))
            print('find the cheapest recovery clifford gate')
            min_N_2QB_gate = np.inf
            min_N_1QB_gate = np.inf
            max_N_I_gate = -np.inf
            cheapest_index = None

            for j in range(N_2QBcliffords):
                recovery_gate = generate_2QB_Cliffords(j, generator = generator)
                seq_QB1 = []
                seq_QB2 = []
                # sequence_rb.add_twoQ_clifford(j, seq_QB1, seq_QB2)
                # print(dot(recovery_gate, final_psi_00))
                # exit()
                if ((np.abs(1-np.abs(dot(recovery_gate, final_psi_00)[0,0])) < 1e-6) and
                    (np.abs(1-np.abs(dot(recovery_gate, final_psi_01)[1,0])) < 1e-6) and
                    (np.abs(1-np.abs(dot(recovery_gate, final_psi_10)[2,0])) < 1e-6) and
                    (np.abs(1-np.abs(dot(recovery_gate, final_psi_11)[3,0])) < 1e-6) and
                    (np.abs(1-dot(recovery_gate, final_psi_01)[1,0]/dot(recovery_gate, final_psi_00)[0,0]) < 1e-6) and
                    (np.abs(1-dot(recovery_gate, final_psi_10)[2,0]/dot(recovery_gate, final_psi_00)[0,0]) < 1e-6) and
                    (np.abs(1-dot(recovery_gate, final_psi_11)[3,0]/dot(recovery_gate, final_psi_00)[0,0]) < 1e-6)
                    ):

                    print(dot(recovery_gate, final_psi_00)[0,0],dot(recovery_gate, final_psi_01)[1,0],dot(recovery_gate, final_psi_10)[2,0],dot(recovery_gate, final_psi_11)[3,0])
                    # if the gate is recovery, check if it is the cheapest.

                    # Less 2QB Gates, Less 1QB Gates, and More I Gates = the cheapest gates.
                    # The priority: less 2QB gates > less 1QB gates > more I gates
                    N_2QB_gate, N_1QB_gate, N_I_gate = 0, 0, 0

                    # count the numbers of the gates
                    for k in range(len(seq_QB1)):
                        if (seq_QB1[k] == gates.CZ or seq_QB2[k] == gates.CZ):
                            N_2QB_gate += 1
                        else:
                            N_1QB_gate += 2
                        if (seq_QB1[k] == gates.I):
                            N_I_gate += 1
                        if (seq_QB2[k] == gates.I):
                            N_I_gate += 1

                    # check whether it is the cheapest
                    # if it has less 2QB gates, always update it.
                    if (N_2QB_gate < min_N_2QB_gate):
                        min_N_2QB_gate, min_N_1QB_gate, max_N_I_gate, cheapest_index = (N_2QB_gate, N_1QB_gate, N_I_gate, j)
                        print('the cheapest sequence update! [N_2QB_gate, N_1QB_gate, N_I_gate, seq. index] ' + str([min_N_2QB_gate, min_N_1QB_gate, max_N_I_gate, cheapest_index]))
                    else:
                        # if it has equal # of 2QB gates and less 1QB gates, update it.
                        if (N_2QB_gate == min_N_2QB_gate and
                            N_1QB_gate < min_N_1QB_gate):
                            min_N_2QB_gate, min_N_1QB_gate, max_N_I_gate, cheapest_index = (N_2QB_gate, N_1QB_gate, N_I_gate, j)
                            print('the cheapest sequence update! [N_2QB_gate, N_1QB_gate, N_I_gate, seq. index] ' + str([min_N_2QB_gate, min_N_1QB_gate, max_N_I_gate, cheapest_index]))
                        else:
                            # if it has equal # of 2QB & 1QB gates, and more 1QB gates, update it.
                            if (N_2QB_gate == min_N_2QB_gate and
                                N_1QB_gate == min_N_1QB_gate and
                                N_I_gate >= max_N_I_gate):
                                min_N_2QB_gate, min_N_1QB_gate, max_N_I_gate, cheapest_index = (N_2QB_gate, N_1QB_gate, N_I_gate, j)
                                print('the cheapest sequence update! [N_2QB_gate, N_1QB_gate, N_I_gate, seq. index] ' + str([min_N_2QB_gate, min_N_1QB_gate, max_N_I_gate, cheapest_index]))



            seq_recovery_QB1 = []
            seq_recovery_QB2 = []
            sequence_rb.add_twoQ_clifford(cheapest_index, seq_recovery_QB1, seq_recovery_QB2)

            # remove redundant Identity gates
            index_identity = [] # find where Identity gates are
            for p in range(len(seq_recovery_QB1)):
                if (seq_recovery_QB1[p] == gates.I and seq_recovery_QB2[p] == gates.I):
                    index_identity.append(p)
            seq_recovery_QB1 = [m for n, m in enumerate(seq_recovery_QB1) if n not in index_identity]
            seq_recovery_QB2 = [m for n, m in enumerate(seq_recovery_QB2) if n not in index_identity]

            # convert the sequences into the text-format (Avoid using customized python class objects)
            for _seq in [seq_recovery_QB1, seq_recovery_QB2]:
                for q in range(len(_seq)):
                    _seq[q] = Gate_to_strGate(_seq[q])
            list_recovery_gates_QB1.append(seq_recovery_QB1)
            list_recovery_gates_QB2.append(seq_recovery_QB2)
            print('The cheapest recovery clifford gate (QB1): ' + str(seq_recovery_QB1))
            print('The cheapest recovery clifford gate (QB2): ' + str(seq_recovery_QB2))
            print('\n')

    # save the results.
    dict_result ={}
    dict_result['psi_stabilizer'] = list_stabilizer
    dict_result['psi'] = list_psi
    dict_result['recovery_gates_QB1'] = list_recovery_gates_QB1
    dict_result['recovery_gates_QB2'] = list_recovery_gates_QB2
    saveData('recovery_rb_table_iSWAP.pickle', dict_result)

    # load the results.
    # dict_result =loadData('recovery_rb_table.dill')
    # print(dict_result['psi_stabilizer'])
