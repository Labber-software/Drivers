#!/usr/bin/env python

from BaseDriver import LabberDriver
import numpy as np
import copy
from sklearn.svm import SVC


class Error(Exception):
    pass

class Driver(LabberDriver):
    """ This class implements a Labber driver"""

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
              self.getValue('Perform training')):
            # before updating values, mark current training as invalid
            self.training_valid = False
            # get input data as numpy vector
            quant.setValue(value)
            training_vector = quant.getValueArray()
            # get qubit/state for which data is valid
            qubit = int(quant.name[-1])
            state = int(self.getValue('Training, input state'))
            # store training data data
            if self.getValue('Training type') == 'Specific qubit':
                # training specific qubit, only store if match
                if qubit == int(self.getValue('Training, qubit')):
                    self.training_data[qubit - 1][state] = training_vector
            else:
                # data is for all qubits
                self.training_data[qubit - 1][state] = training_vector

        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # get traces if first call
        if self.isFirstCall(options):
            self.calculate_states()
        # check input
        if quant.name.startswith('QB'):
            qubit = int(quant.name[2])
            value = self.qubit_states[qubit]
        elif quant.name.startswith('Average QB'):
            qubit = int(quant.name[10])
            value = np.mean(self.qubit_states[qubit])
        elif quant.name.startswith('State vector'):
            # states are encoded in array of ints
            m = self.training_cfg['n_state'] ** self.training_cfg['n_qubit']
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
        # determine size of training data and allocate variables
        if d['training_type'] in ('Specific qubit', 'All qubits at once'):
            n_total = d['n_state']
        elif d['training_type'] == 'All combinations':
            n_total = d['n_state'] ** d['n_qubit']
        self.training_data = [
            [None for n1 in range(n_total)] for n2 in range(d['n_qubit'])]


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

        # train for all active qubits
        self.svm = []
        for qubit, data in enumerate(self.training_data):
            # initialize training data
            n_data = 0
            for x in data:
                if x is None:
                    return
                n_data += len(x)
            X = np.zeros((n_data, 2))
            y = np.zeros(n_data, dtype=int)
            k = 0
            # collect training data
            for m, x in enumerate(data):
                X[k:(k + len(x)), 0] = x.real
                X[k:(k + len(x)), 1] = x.imag
                if self.training_cfg['training_type'] == 'All combinations':
                    # if using all combinations, figure out what the state is
                    state = np.base_repr(m, self.training_cfg['n_state'], 9)
                    y[k:(k + len(x))] = int(state[qubit])

                else:
                    y[k:(k + len(x))] = m
                # increase counter
                k += len(x)

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
        # calculate states for all active qubits
        self.qubit_states = []
        for n, svm in enumerate(self.svm):
            x = self.getValueArray('Input data, QB%d' % (n + 1))
            input_data = np.zeros((len(x), 2))
            input_data[:, 0] = x.real
            input_data[:, 1] = x.imag
            output = svm.predict(input_data)
            self.qubit_states.append(output)

            # calculate state vector, in integer form
            if n == 0:
                self.state_vector = np.zeros(len(output), dtype=int)
            self.state_vector += (output * (self.training_cfg['n_state'] ** n))


if __name__ == '__main__':
    pass
