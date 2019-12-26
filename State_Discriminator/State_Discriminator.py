#!/usr/bin/env python

from BaseDriver import LabberDriver
import numpy as np
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score


class Error(Exception):
    pass


class Driver(LabberDriver):
    """ This class implements a Labber driver"""

    MAX_QUBITS = 9

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # define variables for training data sets
        self.training_cfg = {}
        self.init_training_data()

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        pass

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""

        # initialize training data
        if quant.name in (
                'Training type', 'Number of qubits', 'Number of states'):
            # update local variable, then re-init training data, if needed
            quant.setValue(value)
            self.init_training_data()

        # store training data
        elif (quant.name.startswith('Input data, QB') and
              self.getValue('Training source') == 'Input traces' and
              self.getValue('Perform training')):
            # before updating values, mark current training as invalid
            self.training_valid = False
            # get input data as numpy vector
            quant.setValue(value)
            training_vector = quant.getValueArray()
            # get qubit/state for which data is valid
            qubit = int(quant.name[-1])
            state = int(self.getValue('Training, input state'))
            all_states = self.getValue('Train all states at once')

            # do nothing and return directly if the call is for the wrong qubit
            if (self.getValue('Training type') == 'Specific qubit' and
                    qubit != int(self.getValue('Training, qubit'))):
                return value

            # reshape input data if training for all states at once
            if all_states:
                n_data = len(training_vector) // self.n_total_states
                training_vector = training_vector.reshape(
                    n_data, self.n_total_states)
                for m in range(self.n_total_states):
                    self.training_data[qubit - 1][m] = training_vector[:, m]
            else:
                # one state at a time
                self.training_data[qubit - 1][state] = training_vector

        # if changing to use median, flag that re-training is necessary
        elif quant.name.startswith('Use median value'):
            self.training_valid = False

        # if changing pointer states, flag need for for re-training
        elif (quant.name.startswith('Training source') or
                (self.getValue('Training source') == 'Pointer states' and
                    quant.name.startswith('Pointer,'))):
            self.training_valid = False

        return value

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # get traces if first call
        if self.isFirstCall(options):
            self.calculate_states()
        # check input
        if quant.name.startswith('QB'):
            # qubit = int(quant.name[2]) - 1
            qubit = int(quant.name.split("QB")[1].split(' ')[0]) - 1
            value = self.qubit_states[qubit]
        elif quant.name.startswith('Average QB'):
            # qubit = int(quant.name[10]) - 1
            qubit = int(quant.name.split('QB')[1].split(' ')[0]) - 1
            value = np.mean(self.qubit_states[qubit])
        elif quant.name.startswith('Assignment fidelity QB'):
            #qubit = int(quant.name[22]) - 1
            qubit = int(quant.name.split('QB')[1].split(' ')[0]) - 1
            value = self.assignment_fidelity[qubit]
        elif quant.name.startswith('Average state vector'):
            # states are encoded in array of ints
            m = self.n_state ** self.n_qubit
            value = (np.bincount(self.state_vector, minlength=m) /
                     len(self.state_vector))

        elif quant.name.startswith('System state'):
            value = self.state_vector

        else:
            # just return the quantity value
            value = quant.getValue()
        return value

    def init_training_data(self):
        """Init training data"""
        # check if training config has changed since last call
        d = dict(
            n_qubit=self.getValueIndex('Number of qubits') + 1,
            n_state=self.getValueIndex('Number of states') + 2,
            training_type=self.getValue('Training type'),
        )
        if d == self.training_cfg:
            return
        # store new config
        self.training_cfg = d
        self.training_valid = False
        self.n_qubit = d['n_qubit']
        self.n_state = d['n_state']
        # determine size of training data and allocate variables
        if d['training_type'] in ('Specific qubit', 'All qubits at once'):
            n_total = d['n_state']
        elif d['training_type'] == 'All combinations':
            n_total = d['n_state'] ** d['n_qubit']
        self.n_total_states = int(n_total)
        self.training_data = [
            [None for n1 in range(n_total)] for n2 in range(d['n_qubit'])]
        self.assignment_fidelity = [0.0] * self.MAX_QUBITS

    def _prepare_data(self, qubit, data, use_median=False):
        """Prepare data to right format for SVM"""
        # initialize training data
        n_data = 0
        for x in data:
            n_data += (1 if use_median else len(x))
        X = np.zeros((n_data, 2))
        y = np.zeros(n_data, dtype=int)
        k = 0
        # collect training data
        for m, x in enumerate(data):
            # if using median, calculate real and imaginary separately
            if use_median:
                x = np.array([np.median(x.real) + 1j * np.median(x.imag)])
                if m <= self.n_state:
                    self.setValue('Pointer, QB%d-S%d' % (qubit + 1, m), x[0])

            X[k:(k + len(x)), 0] = x.real
            X[k:(k + len(x)), 1] = x.imag
            if self.training_cfg['training_type'] == 'All combinations':
                # if using all combinations, figure out what the state is
                state = np.base_repr(m, self.n_state, self.MAX_QUBITS)
                state = state[::-1]
                y[k:(k + len(x))] = int(state[qubit])

            else:
                y[k:(k + len(x))] = m
            # increase counter
            k += len(x)
        return (X, y)

    def train_discriminator(self):
        """Train discriminator based on training data"""
        # don't do anything is training data is unchanged
        if self.training_valid:
            return

        # get SVM configuration
        kwargs = dict(
            kernel=self.getValue('Kernel'),
            degree=self.getValue('Degree'),
            gamma=self.getValue('Gamma'),
            coef0=self.getValue('Coef0'),
            C=self.getValue('C-parameter'),
            shrinking=self.getValue('Shrinking')
        )
        use_median = self.getValue('Use median value')

        # special case if training from pointer states
        if self.getValue('Training source') == 'Pointer states':
            self.train_from_pointer_states(kwargs)
            return

        # train for all active qubits
        self.svm = [None] * self.n_qubit
        self.assignment_fidelity = [0.0] * self.n_qubit
        for qubit, data in enumerate(self.training_data):
            # prepare data both for full set and just median
            if np.any([x is None for x in data]):
                continue
            (X, y) = self._prepare_data(qubit, data, use_median=False)
            (Xm, ym) = self._prepare_data(qubit, data, use_median=True)

            # create SVM and fit data
            svc = SVC(**kwargs)
            if use_median:
                svc.fit(Xm, ym)
            else:
                svc.fit(X, y)
            # store in list of SVMs
            self.svm[qubit] = svc
            # calculate assignment fidelity using full data set
            self.assignment_fidelity[qubit] = accuracy_score(y, svc.predict(X))

        # mark training as valid
        self.training_valid = True


    def train_from_pointer_states(self, kwargs):
        """Train discriminator based on pointer states"""
        # train for all active qubits
        self.svm = []
        for qubit in range(self.n_qubit):
            X = np.zeros((self.n_state, 2))
            y = np.zeros(self.n_state, dtype=int)
            # collect training data
            for m in range(self.n_state):
                # get pointer value
                x = self.getValue('Pointer, QB%d-S%d' % (qubit + 1, m))
                X[m, 0] = x.real
                X[m, 1] = x.imag
                y[m] = m

            # create SVM and fit data
            svc = SVC(**kwargs)
            svc.fit(X, y)
            # store in list of SVMs
            self.svm.append(svc)

        # mark training as valid
        self.training_valid = True


    def calculate_states(self):
        """Calculate states using training data"""
        # train discriminator, if necessary
        self.train_discriminator()
        self.state_vector = np.array([], dtype=int)
        # calculate states for all active qubits
        self.qubit_states = [[]] * self.MAX_QUBITS
        for n, svm in enumerate(self.svm):
            x = self.getValueArray('Input data, QB%d' % (n + 1))
            if len(x) > 0:
                if svm is None:
                    output = np.zeros(len(x), dtype=int)
                else:
                    input_data = np.zeros((len(x), 2))
                    input_data[:, 0] = x.real
                    input_data[:, 1] = x.imag
                    output = svm.predict(input_data)
            else:
                output = np.array([], dtype=int)
            self.qubit_states[n] = output

            # update mean value controls
            self.setValue('Average QB%d state' % (n + 1), np.mean(output))

            # calculate state vector, in integer form
            if n == 0:
                self.state_vector = np.zeros(len(output), dtype=int)
            self.state_vector += (output * (self.n_state ** n))


if __name__ == '__main__':
    pass
