#!/usr/bin/env python3
import numpy as np


class Pulse:
    """Represents physical pulses played by an AWG.

    Parameters
    ----------
    complex : bool
        If True, pulse has both I and Q, otherwise it's a real valued.

    Attributes
    ----------
    amplitude : float
        Pulse amplitude.
    width : float
        Pulse width.
    plateau : float
        Pulse plateau.
    frequency : float
        SSB frequency.
    phase : float
        Pulse phase.
    use_drag : bool
        If True, applies DRAG correction.
    drag_coefficient : float
        Drag coefficient.
    drag_detuning : float
        Applies a frequnecy detuning for DRAG pulses.
    truncation_range : float
        The truncation range of Gaussian pulses,
        in units of standard deviations.
    start_at_zero : bool
        If True, forces the pulse to start in 0.

    """

    def __init__(self, complex):

        # set variables
        self.amplitude = 0.5
        self.width = 10E-9
        self.plateau = 0.0
        self.frequency = 0.0
        self.phase = 0.0
        self.use_drag = False
        self.drag_coefficient = 0.0
        self.drag_detuning = 0.0
        self.truncation_range = 5.0
        self.start_at_zero = False
        self.complex = complex

    def total_duration(self):
        """Get the total duration for the pulse.

        Returns
        -------
        float
            Total duration in seconds.

        """
        raise NotImplementedError()

    def calculate_envelope(self, t0, t):
        """Calculate pulse envelope.

        Parameters
        ----------
        t0 : float
            Pulse position, referenced to center of pulse.

        t : numpy array
            Array with time values for which to calculate the pulse envelope.

        Returns
        -------
        waveform : numpy array
            Array containing pulse envelope.

        """
        raise NotImplementedError()

    def calculate_waveform(self, t0, t):
        """Calculate pulse waveform including phase shifts and SSB-mixing.

        Parameters
        ----------
        t0 : float
            Pulse position, referenced to center of pulse.

        t : numpy array
            Array with time values for which to calculate the pulse waveform.

        Returns
        -------
        waveform : numpy array
            Array containing pulse waveform.

        """
        y = self.calculate_envelope(t0, t)
        # Make sure the waveform is zero outside the pulse
        y[t < (t0 - self.total_duration() / 2)] = 0
        y[t > (t0 + self.total_duration() / 2)] = 0

        if self.use_drag and self.complex:
            beta = self.drag_coefficient / (t[1] - t[0])
            y = y + 1j * beta * np.gradient(y)
            y = y * np.exp(1j * 2 * np.pi * self.drag_detuning *
                           (t - t0 + self.total_duration() / 2))

        if self.complex:
            # Apply phase and SSB
            phase = self.phase
            # single-sideband mixing, get frequency
            omega = 2 * np.pi * self.frequency
            # apply SSBM transform
            data_i = (y.real * np.cos(omega * t - phase) +
                      - y.imag * np.cos(omega * t - phase +
                      + np.pi / 2))
            data_q = (y.real * np.sin(omega * t - phase) +
                      - y.imag * np.sin(omega * t - phase +
                      + np.pi / 2))
            y = data_i + 1j * data_q
        return y


class Gaussian(Pulse):
    def total_duration(self):
        return self.truncation_range * self.width + self.plateau

    def calculate_envelope(self, t0, t):
        # width is two t std
        # std = self.width/2;
        # alternate; std is set to give total pulse area same as a square
        std = self.width / np.sqrt(2 * np.pi)
        if self.plateau == 0:
            # pure gaussian, no plateau
            if std > 0:
                values = np.exp(-(t - t0)**2 / (2 * std**2))
            else:
                values = np.zeros_like(t)
        else:
            # add plateau
            values = np.array(((t >= (t0 - self.plateau / 2)) &
                               (t < (t0 + self.plateau / 2))), dtype=float)
            if std > 0:
                # before plateau
                values += (
                    (t < (t0 - self.plateau / 2)) *
                    np.exp(-(t - (t0 - self.plateau / 2))**2 /
                            (2 * std**2))
                )
                # after plateau
                values += (
                    (t >= (t0 + self.plateau / 2)) *
                    np.exp(-(t - (t0 + self.plateau / 2))**2 /
                            (2 * std**2))
                )

        if self.start_at_zero:
            values = values - values.min()
            values = values / values.max()
        values = values * self.amplitude

        return values


class Ramp(Pulse):
    def total_duration(self):
        return 2 * self.width + self.plateau

    def calculate_envelope(self, t0, t):
        # rising and falling slopes
        vRise = ((t - (t0 - self.plateau / 2 - self.width)) /
                 self.width)
        vRise[vRise < 0.0] = 0.0
        vRise[vRise > 1.0] = 1.0
        vFall = (((t0 + self.plateau / 2 + self.width) - t) /
                 self.width)
        vFall[vFall < 0.0] = 0.0
        vFall[vFall > 1.0] = 1.0
        values = vRise * vFall

        values = values * self.amplitude

        return values


class Square(Pulse):
    def total_duration(self):
        return self.width + self.plateau

    def calculate_envelope(self, t0, t):
        # reduce risk of rounding errors by putting checks between samples
        if len(t) > 1:
            t0 += (t[1] - t[0]) / 2.0

        values = ((t >= (t0 - (self.width + self.plateau) / 2)) &
                  (t < (t0 + (self.width + self.plateau) / 2)))

        values = values * self.amplitude

        return values


class Cosine(Pulse):
    def total_duration(self):
        return self.width + self.plateau

    def calculate_envelope(self, t0, t):
        tau = self.width
        if self.plateau == 0:
            values = (self.amplitude / 2 *
                      (1 - np.cos(2 * np.pi * (t - t0 + tau / 2) / tau)))
        else:
            values = np.ones_like(t) * self.amplitude
            values[t < t0 - self.plateau / 2] = self.amplitude / 2 * \
                (1 - np.cos(2 * np.pi *
                            (t[t < t0 - self.plateau / 2] - t0 +
                             self.plateau / 2 + tau / 2) / tau))
            values[t > t0 + self.plateau / 2] = self.amplitude / 2 * \
                (1 - np.cos(2 * np.pi *
                            (t[t > t0 + self.plateau / 2] - t0 -
                             self.plateau / 2 + tau / 2) / tau))

        return values
