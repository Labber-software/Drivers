#!/usr/bin/env python3


class Crosstalk(object):
    """This class is used to compensate crosstalk qubit Z control

    """

    def __init__(self):
        # define variables
        self.matrix_path = ''
        # TODO(dan): define variables for matrix, etc


    def set_parameters(self, config={}):
        """Set base parameters using config from from Labber driver

        Parameters
        ----------
        config : dict
            Configuration as defined by Labber driver configuration window

        """
        # check if cross-talk matrix has been updated
        path = config.get('Cross-talk matrix')
        # only reload if file changed
        if path != self.matrix_path:
            self.import_crosstalk_matrix(path)


    def import_crosstalk_matrix(self, path):
        """Import crosstalk matrix data 

        Parameters
        ----------
        path : str
            Path to file containing crosstalk matrix data

        """
        # store new path
        self.matrix_path = path
        # TODO(dan): load crosstalk data
        pass


    def compensate(self, waveforms):
        """Compensate crosstalk on Z-control waveforms 

        Parameters
        ----------
        waveforms : list on 1D numpy arrays 
            Input data to apply crosstalk compensation on

        Returns
        -------
        waveforms : list of 1D numpy arrays
            Waveforms with crosstalk compensation

        """
        # TODO(dan): implement crosstalk compensation
        return waveforms



if __name__ == '__main__':
    pass

