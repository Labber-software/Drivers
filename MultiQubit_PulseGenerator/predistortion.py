#!/usr/bin/env python3


class Predistortion(object):
    """This class is used to predistort I/Q waveforms for qubit XY control

    """

    def __init__(self, waveform_number=0):
        # define variables
        self.transfer_path = ''
        # keep track of which Labber waveform this predistortion refers to
        self.waveform_number = waveform_number
        # TODO(dan): define variables for predistortion algorithm


    def set_parameters(self, config={}):
        """Set base parameters using config from from Labber driver

        Parameters
        ----------
        config : dict
            Configuration as defined by Labber driver configuration window

        """
        # Labber configuration contains multiple predistortions, get right one
        path = config.get('Transfer function #%d' % (self.waveform_number + 1))
        # only reload tranfser function if file changed
        if path != self.transfer_path:
            self.import_transfer_function(path)


    def import_transfer_function(self, path):
        """Import transfer function data 

        Parameters
        ----------
        path : str
            Path to file containing transfer function data

        """
        # store new path
        self.transfer_path = path
        # TODO(dan): load transfer function data
        pass


    def predistort(self, waveform):
        """Predistort input waveform 

        Parameters
        ----------
        waveform : complex numpy array
            Waveform data to be pre-distorted

        Returns
        -------
        waveform : complex numpy array 
            Pre-distorted waveform

        """
        # TODO(dan): implement predistortion
        return waveform



if __name__ == '__main__':
    pass

