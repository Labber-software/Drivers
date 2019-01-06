#!/usr/bin/env python3
import logging
from enum import Enum

import numpy as np

log = logging.getLogger('LabberDriver')


class PulseShape(Enum):
    """Define possible qubit pulses shapes."""

    GAUSSIAN = 'Gaussian'
    SQUARE = 'Square'
    RAMP = 'Ramp'
    CZ = 'CZ'
    COSINE = 'Cosine'


class PulseType(Enum):
    """Define possible qubit pulse types."""

    XY = 'XY'
    Z = 'Z'
    READOUT = 'Readout'


class Pulse(object):
    """Represents physical pulses played by an AWG.

    Parameters
    ----------
    shape : :obj:`PulseShape`
        Pulse shape (the default is PulseShape.GAUSSIAN).
    pulse_type : :obj:`PulseType`
        Pulse type (the default is PulseType.XY).

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

    def __init__(self, shape=PulseShape.GAUSSIAN, pulse_type=PulseType.XY):

        # set variables
        self.amplitude = 0.5
        self.width = 10E-9
        self.plateau = 0.0
        self.frequency = 0.0
        self.phase = 0.0
        self.shape = shape
        self.use_drag = False
        self.drag_coefficient = 0.0
        self.drag_detuning = 0.0
        self.truncation_range = 5.0
        self.start_at_zero = False
        self.pulse_type = pulse_type

        # For CZ pulses
        self.F_Terms = 1
        self.Coupling = 20E6
        self.Offset = 300E6
        self.Lcoeff = np.array([0.3])
        self.dfdV = 500E6
        self.qubit = None

        # For IQ mixer corrections
        self.iq_ratio = 1.0
        self.iq_skew = 0.0

    def total_duration(self):
        """Get the total duration for the pulse.

        Returns
        -------
        float
            Total duration in seconds.

        """
        # calculate total length of pulse
        if self.shape == PulseShape.SQUARE:
            duration = self.width + self.plateau
        elif self.shape == PulseShape.RAMP:
            duration = 2 * self.width + self.plateau
        elif self.shape == PulseShape.GAUSSIAN:
            duration = self.truncation_range * self.width + self.plateau
        elif self.shape == PulseShape.CZ:
            duration = self.width + self.plateau
        elif self.shape == PulseShape.COSINE:
            duration = self.width + self.plateau
        return duration

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
        # calculate the actual value for the selected indices
        if self.shape == PulseShape.SQUARE:
            # reduce risk of rounding errors by putting checks between samples
            if len(t) > 1:
                t0 += (t[1] - t[0]) / 2.0

            values = ((t >= (t0 - (self.width + self.plateau) / 2)) &
                      (t < (t0 + (self.width + self.plateau) / 2)))

            values = values * self.amplitude

        elif self.shape == PulseShape.RAMP:
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

        elif self.shape == PulseShape.GAUSSIAN:
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

        elif self.shape == PulseShape.CZ:
            # notation and calculations are based on
            # "Fast adiabatic qubit gates using only sigma_z control"
            # PRA 90, 022307 (2014)
            # self.calculate_cz_waveform()

            # Plateau is added as an extra extension of theta_f.
            theta_t = np.ones(len(t)) * self.theta_i
            for i in range(len(t)):
                if 0 < (t[i] - t0 + self.plateau / 2) < self.plateau:
                    theta_t[i] = self.theta_f
                elif (0 < (t[i] - t0 + self.width / 2 + self.plateau / 2) <
                        (self.width + self.plateau) / 2):
                    theta_t[i] = np.interp(
                        t[i] - t0 + self.width / 2 + self.plateau / 2,
                        self.t_tau, self.theta_tau)
                elif (0 < (t[i] - t0 + self.width / 2 + self.plateau / 2) <
                      (self.width + self.plateau)):
                    theta_t[i] = np.interp(
                        t[i] - t0 + self.width / 2 - self.plateau / 2,
                        self.t_tau, self.theta_tau)

            df = self.Coupling * (
                1 / np.tan(theta_t) - 1 / np.tan(self.theta_i))
            if self.qubit is None:
                # Use linear dependence if no qubit was given
                values = df / self.dfdV
            else:
                values = self.qubit.df_to_dV(df)

        elif self.shape == PulseShape.COSINE:
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

        # Make sure the waveform is zero outside the pulse
        values[t < (t0 - self.total_duration() / 2)] = 0
        values[t > (t0 + self.total_duration() / 2)] = 0
        return values


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
        if self.use_drag:
            beta = self.drag_coefficient / (t[1] - t[0])
            y = y + 1j * beta * np.gradient(y)
            y = y * np.exp(1j * 2 * np.pi * self.drag_detuning *
                           (t - t0 + self.total_duration() / 2))

        if self.pulse_type in (PulseType.XY, PulseType.READOUT):
            # Apply phase and SSB
            phase = self.phase
            # single-sideband mixing, get frequency
            omega = 2 * np.pi * self.frequency
            # apply SSBM transform
            data_i = self.iq_ratio * (y.real * np.cos(omega * t - phase) +
                                      - y.imag * np.cos(omega * t - phase +
                                                        np.pi / 2))
            data_q = (y.real * np.sin(omega * t - phase + self.iq_skew) +
                      -y.imag * np.sin(omega * t - phase + self.iq_skew +
                                       np.pi / 2))
            y = data_i + 1j * data_q
        return y

    def calculate_cz_waveform(self):
        """Calculate waveform for c-phase and store in object"""
        # notation and calculations are based on
        # "Fast adiabatic qubit gates using only sigma_z control"
        # PRA 90, 022307 (2014)
        # Initial and final angles on the |11>-|02> bloch sphere
        self.theta_i = np.arctan(self.Coupling / self.Offset)
        self.theta_f = np.arctan(self.Coupling / self.amplitude)

        # Normalize fouriere coefficients to initial and final angles
        Lcoeff = self.Lcoeff * (
            (self.theta_f - self.theta_i) /
            (2 * np.sum(self.Lcoeff[range(0, self.F_Terms, 2)])))

        # defining helper variabels
        n = np.arange(1, self.F_Terms + 1, 1)
        n_points = 1000  # Number of points in the numerical integration

        # Calculate pulse width in tau variable - See paper for details
        tau = np.linspace(0, 1, n_points)
        self.theta_tau = np.zeros(n_points)
        for i in range(n_points):
            self.theta_tau[i] = np.sum(
                (Lcoeff * (1 - np.cos(2 * np.pi * n * tau[i]))) + self.theta_i)
        t_tau = np.trapz(np.sin(self.theta_tau), x=tau)
        Width_tau = self.width / t_tau

        # Calculating angle and time as functions of tau
        tau = np.linspace(0, Width_tau, n_points)
        self.t_tau = np.zeros(n_points)
        for i in range(n_points):
            self.theta_tau[i] = np.sum(
                (Lcoeff * (1 - np.cos(2 * np.pi * n * tau[i] / Width_tau))) +
                self.theta_i)
            if i > 0:
                self.t_tau[i] = np.trapz(
                    np.sin(self.theta_tau[0:i]), x=tau[0:i])

if __name__ == '__main__':
    pass
