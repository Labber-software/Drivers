#!/usr/bin/env python3

# Note from/to Dan. This driver appears to take a premade transfer function for
# each mixer. The trick is then to load in the transfer function and perform the
# actual predistortion. We therefore need to find the correct transfer function
# and save this transfer function to file. These transfer functions need to be
# saved as Transfer function #1, etc.

# The predistoriton program as it stands only produces the transfer function of
# one mixer at a time. A challenge will be finding a good way to add the
# transfer functions to a common file in a convenient way.

import numpy as np
from numpy.fft import fft, fftfreq, fftshift, ifft, ifftshift
from scipy.interpolate import interp1d


class Predistortion(object):
    """This class is used to predistort I/Q waveforms for qubit XY control."""

    def __init__(self, waveform_number=0):
        # define variables
        self.transfer_path = ''
        # keep track of which Labber waveform this predistortion refers to
        self.waveform_number = waveform_number
        # TODO(dan): define variables for predistortion algorithm

    def set_parameters(self, config={}):
        """Set base parameters using config from from Labber driver.

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

        self.dt = 1 / config.get('Sample rate')

    def import_transfer_function(self, path):
        """Import transfer function data.

        Parameters
        ----------
        path : str
            Path to file containing transfer function data

        """
        # store new path
        self.transfer_path = path

        # return directly if not in use, look for both '' and '.'
        if self.transfer_path.strip() in ('', '.'):
            return
        import Labber
        f = Labber.LogFile(self.transfer_path)
        self.vResponse_freqs, self.vFilteredResponse_FFT_I = f.getTraceXY(
            y_channel=0)
        self.vResponse_freqs, self.vFilteredResponse_FFT_Q = f.getTraceXY(
            y_channel=1)
        # TODO(dan): load transfer function data

    def predistort(self, waveform):
        """Predistort input waveform.

        Parameters
        ----------
        waveform : complex numpy array
            Waveform data to be pre-distorted

        Returns
        -------
        waveform : complex numpy array
            Pre-distorted waveform

        """
        # find timespan of waveform
        self.tvals = np.arange(0, self.dt * len(waveform), self.dt)

        response_I = ifft(ifftshift(self.vFilteredResponse_FFT_I))
        response_FFT_I_r = fftshift(fft(complex(1, 0) * response_I.real))
        response_FFT_I_i = fftshift(fft(complex(1, 0) * response_I.imag))

        response_Q = ifft(ifftshift(self.vFilteredResponse_FFT_Q))
        response_FFT_Q_r = fftshift(fft(complex(1, 0) * response_Q.real))
        response_FFT_Q_i = fftshift(fft(complex(1, 0) * response_Q.imag))

        # {{a, b},{c, d}}, determinant is ad-bc, plus sign comes from
        # additional i tacked on to the Q by the IQ mixer.
        # I removed this factor of i from the FFT of the response function.
        determinant = response_FFT_I_r * response_FFT_Q_i - \
            response_FFT_Q_r * response_FFT_I_i

        Za = response_FFT_Q_i / determinant
        Zb = -response_FFT_Q_r / determinant
        Zc = -response_FFT_I_i / determinant
        Zd = response_FFT_I_r / determinant

        Inverse_A = interp1d(self.vResponse_freqs, Za)
        Inverse_B = interp1d(self.vResponse_freqs, Zb)
        Inverse_C = interp1d(self.vResponse_freqs, Zc)
        Inverse_D = interp1d(self.vResponse_freqs, Zd)

        # applies the interpolated inverse function to the AWG signal

        fft_vals, fft_signal_r = self.apply_FFT(
            self.tvals, complex(1, 0) * waveform.real)
        fft_vals, fft_signal_i = self.apply_FFT(
            self.tvals, complex(1, 0) * waveform.imag)

        fft_signal = (fft_signal_r * Inverse_A(fft_vals) + fft_signal_i *
                      Inverse_B(fft_vals) + 1j *
                      (fft_signal_r * Inverse_C(fft_vals) +
                       fft_signal_i * Inverse_D(fft_vals)))
        corr_signal = ifft(ifftshift(fft_signal))

        vI = np.array(corr_signal.real, dtype='float64')
        vQ = np.array(corr_signal.imag, dtype='float64')

        return vI + 1j * vQ

    def apply_FFT(self, tvals, signal):
        fft_signal = fftshift(fft(signal))
        fft_vals = fftshift(fftfreq(len(signal), tvals[1] - tvals[0]))
        return fft_vals, fft_signal


class ExponentialPredistortion:
    """Implement a four-pole predistortion on the Z waveforms.

    Parameters
    ----------
    waveform_number : int
        The waveform number to predistort.

    Attributes
    ----------
    A1 : float
        Amplitude for the first pole.
    tau1 : float
        Time constant for the first pole.
    A2 : float
        Amplitude for the second pole.
    tau2 : float
        Time constant for the second pole.
    A3 : float
        Amplitude for the third pole.
    tau3 : float
        Time constant for the third pole.
    A4 : float
        Amplitude for the fourth pole.
    tau4 : float
        Time constant for the fourth pole.
    dt : float
        Sample spacing for the waveform.

    """

    def __init__(self, waveform_number):
        self.A1 = 0
        self.tau1 = 0
        self.A2 = 0
        self.tau2 = 0
        self.A3 = 0
        self.tau3 = 0
        self.A4 = 0
        self.tau4 = 0
        self.dt = 1
        self.n = int(waveform_number)

    def set_parameters(self, config={}):
        """Set base parameters using config from from Labber driver.

        Parameters
        ----------
        config : dict
            Configuration as defined by Labber driver configuration window

        """
        m = self.n + 1
        self.A1 = config.get('Predistort Z{} - A1'.format(m))
        self.tau1 = config.get('Predistort Z{} - tau1'.format(m))
        self.A2 = config.get('Predistort Z{} - A2'.format(m))
        self.tau2 = config.get('Predistort Z{} - tau2'.format(m))

        self.A3 = config.get('Predistort Z{} - A3'.format(m))
        self.tau3 = config.get('Predistort Z{} - tau3'.format(m))
        self.A4 = config.get('Predistort Z{} - A4'.format(m))
        self.tau4 = config.get('Predistort Z{} - tau4'.format(m))

        self.dt = 1 / config.get('Sample rate')

    def predistort(self, waveform):
        """Predistort input waveform.

        Parameters
        ----------
        waveform : complex numpy array
            Waveform data to be pre-distorted

        Returns
        -------
        waveform : complex numpy array
            Pre-distorted waveform

        """
        # pad with zeros at end to make sure response has time to go to zero
        pad_time = 6 * max([self.tau1, self.tau2, self.tau3])
        padded = np.zeros(len(waveform) + round(pad_time / self.dt))
        padded[:len(waveform)] = waveform

        Y = np.fft.rfft(padded, norm='ortho')

        omega = 2 * np.pi * np.fft.rfftfreq(len(padded), self.dt)
        H = (1 +
             (1j * self.A1 * omega * self.tau1) /
             (1j * omega * self.tau1 + 1) +
             (1j * self.A2 * omega * self.tau2) /
             (1j * omega * self.tau2 + 1) +
             (1j * self.A3 * omega * self.tau3) /
             (1j * omega * self.tau3 + 1) +
             (1j * self.A4 * omega * self.tau4) /
             (1j * omega * self.tau4 + 1))

        Yc = Y / H

        yc = np.fft.irfft(Yc, norm='ortho')
        return yc[:len(waveform)]


if __name__ == '__main__':
    pass
