import numpy as np

# Allow logging to Labber's instrument log
import logging
log=logging.getLogger('LabberDriver')

class FluxControl:

    def __init__(self, numQubits=3):
        self.numQubits = numQubits

        #sensitivity will be a matrix holding the inverse of vpPhi0 xtalk values
        self.sensitivity = np.zeros((numQubits, numQubits))
        self.flux_offsets = np.zeros(numQubits)

    def load_matrix(self, matrix):
        if matrix.shape != (self.numQubits, self.numQubits):
            log.error('Matrix shape does not match specified number of qubits!')
            raise ValueError('ERROR: Matrix shape does not match specified number of qubits!')
        else:
            self.sensitivity = 1./matrix

    def set_flux_offsets(self, flux_offsets):
        self.flux_offsets = flux_offsets

    def set_flux_offset(self, index, flux_offset):
        self.flux_offsets[index] = flux_offset

    def get_voltages(self, fluxes):
        if fluxes.size != self.numQubits:
            raise ValueError('ERROR: number of fluxes has to match number of channels!')
        else:
            #np.savetxt(r'C:\Users\Lab\Downloads\inverse_test.txt', np.linalg.inv(self.sensitivity))
            return np.dot(np.linalg.inv(self.sensitivity), fluxes + self.flux_offsets)

    def get_fluxes(self, voltages):
        if voltages.size != self.numQubits:
            raise ValueError('ERROR: number of voltages has to match number of channels!')
        else:
            return np.dot(self.sensitivity, voltages) - self.flux_offsets