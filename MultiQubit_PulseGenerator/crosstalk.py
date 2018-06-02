#!/usr/bin/env python3

import numpy as np
from scipy.linalg import inv


class Crosstalk(object):
    """This class is used to compensate crosstalk qubit Z control."""

    def __init__(self):
        # define variables
        self.matrix_path = ''
        # TODO(dan): define variables for matrix, etc

    def set_parameters(self, config={}):
        """Set base parameters using config from from Labber driver.

        Parameters
        ----------
        config : dict
            Configuration as defined by Labber driver configuration window

        """
        # return directly if not in use
        if not config.get('Compensate cross-talk'):
            return
        # check if cross-talk matrix has been updated
        path = config.get('Cross-talk (CT) matrix')
        # only reload if file changed
        if path != self.matrix_path:
            path = config.get('Cross-talk (CT) matrix')
            self.import_crosstalk_matrix(path)

        dTranslate = {'One': int(1), 'Two': int(
            2), 'Three': int(3), 'Four': int(4), 'Five': int(5)}
        nQBs = dTranslate[config.get('Number of qubits')]

        if config.get('1-1 QB <--> Crosstalk matrix'):
            self.Sequence = []
            for QB in range(0, nQBs):
                self.Sequence.append(QB + 1)
        else:
            self.Sequence = []
            if nQBs > 0:
                for QB in range(0, nQBs):
                    element = config.get('CT-matrix element #%d' % (QB + 1))
                    if element == 'None':
                        continue
                    else:
                        self.Sequence.append(dTranslate[element])
                    if self.compensation_matrix.shape[0] < dTranslate[element]:
                        raise 'Element of Cross-talk matrix is too large for '\
                            'actual matrix size'

        mat_length = len(self.Sequence)
        self.phi0_vs_voltage = np.matrix(np.zeros((mat_length, mat_length)))

        for index_r, element_r in enumerate(self.Sequence):
            for index_c, element_c in enumerate(self.Sequence):
                self.phi0_vs_voltage[index_r, index_c] = \
                    self.compensation_matrix[element_r - 1, element_c - 1]

    def import_crosstalk_matrix(self, path):
        """Import crosstalk matrix data.

        Parameters
        ----------
        path : str
            Path to file containing crosstalk matrix data

        """
        # store new path
        self.matrix_path = path
        self.compensation_matrix = np.matrix(np.loadtxt(path))
        # TODO(dan): load crosstalk data

    def compensate(self, waveforms):
        """Compensate crosstalk on Z-control waveforms.

        Parameters
        ----------
        waveforms : list on 1D numpy arrays
            Input data to apply crosstalk compensation on

        Returns
        -------
        waveforms : list of 1D numpy arrays
            Waveforms with crosstalk compensation

        """
        mat_voltage_vs_phi0 = inv(self.phi0_vs_voltage)

        wavform_length = len(waveforms[0])
        wavform_num = len(self.Sequence)
        wav_array = np.array(np.zeros((wavform_num, wavform_length)))
        wav_toCorrect = []
        for index, waveform in enumerate(waveforms):
            if index + 1 in self.Sequence:
                wav_array[index] = waveform
                wav_toCorrect.append(index)

        # new_array = np.dot(mat_voltage_vs_phi0, wav_array)

        # dot product between the matrix and the waveforms at each timestep
        new_array = np.einsum('ij,jk->ik', mat_voltage_vs_phi0, wav_array)

        for Corr_index, index in zip(wav_toCorrect,
                                     range(0, len(self.Sequence))):
            waveforms[Corr_index] = new_array[index]

        return waveforms


if __name__ == '__main__':
    pass
