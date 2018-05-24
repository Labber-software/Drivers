#!/usr/bin/env python3
import numpy as np
from enum import Enum
import logging
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
    shape : type
        Description of parameter `shape` (the default is PulseShape.GAUSSIAN).
    pulse_type : type
        Description of parameter `pulse_type` (the default is PulseType.XY).

    Attributes
    ----------
    amplitude : type
        Description of attribute `amplitude`.
    width : type
        Description of attribute `width`.
    plateau : type
        Description of attribute `plateau`.
    frequency : type
        Description of attribute `frequency`.
    phase : type
        Description of attribute `phase`.
    use_drag : type
        Description of attribute `use_drag`.
    drag_coefficient : type
        Description of attribute `drag_coefficient`.
    drag_detuning : type
        Description of attribute `drag_detuning`.
    truncation_range : type
        Description of attribute `truncation_range`.
    start_at_zero : type
        Description of attribute `start_at_zero`.
    def __init__(self, shape : type
        Description of attribute `def __init__(self, shape`.
    shape        pulse_type

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

        # For gating of the pulse
        self.gated = False
        self.gate_delay = 0.0
        self.gate_amplitude = 1.0

        self.gate_duration = self.total_duration()

        # For CZ pulses
        self.F_Terms = 1
        self.Coupling = 20E6
        self.Offset = 300E6
        self.Lcoeff = np.array([0.3])
        self.dfdV = 500E6
        self.qubit_spectrum = None

        # For IQ mixer corrections
        self.iq_ratio = 1.0
        self.iq_skew = 0.0
        self.i_offset = 0.0
        self.q_offset = 0.0

    def total_duration(self):
        """Short summary.

        Returns
        -------
        type
            Description of returned object.

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

            # Initial and final angles on the |11>-|02> bloch sphere
            theta_i = np.arctan(self.Coupling / self.Offset)
            theta_f = np.arctan(self.Coupling / self.amplitude)

            # Normalize fouriere coefficients to initial and final angles
            self.Lcoeff *= ((theta_f - theta_i) /
                            (2 * np.sum(self.Lcoeff[range(0,
                                                          self.F_Terms, 2)])))

            # defining helper variabels
            n = np.arange(1, self.F_Terms + 1, 1)
            n_points = 1000  # Number of points in the numerical integration

            # Calculate pulse width in tau variable - See paper for details
            tau = np.linspace(0, 1, n_points)
            theta_tau = np.zeros(n_points)
            for i in range(n_points):
                theta_tau[i] = np.sum((self.Lcoeff *
                                       (1 - np.cos(2 * np.pi * n * tau[i]))) +
                                      theta_i)
            t_tau = np.trapz(np.sin(theta_tau), x=tau)
            Width_tau = self.width / t_tau

            # Calculating angle and time as functions of tau
            tau = np.linspace(0, Width_tau, n_points)
            t_tau = np.zeros(n_points)
            for i in range(n_points):
                theta_tau[i] = np.sum((self.Lcoeff *
                                       (1 - np.cos(2 * np.pi * n * tau[i] /
                                                   Width_tau))) + theta_i)
                if i > 0:
                    t_tau[i] = np.trapz(np.sin(theta_tau[0:i]), x=tau[0:i])

            # Plateau is added as an extra extension of theta_f.
            theta_t = np.ones(len(t)) * theta_i
            for i in range(len(t)):
                if 0 < (t[i] - t0 + self.plateau / 2) < self.plateau:
                    theta_t[i] = theta_f
                elif (0 < (t[i] - t0 + self.width / 2 + self.plateau / 2) <
                        (self.width + self.plateau) / 2):
                    theta_t[i] = np.interp(
                        t[i] - t0 + self.width / 2 + self.plateau / 2,
                        t_tau, theta_tau)
                elif (0 < (t[i] - t0 + self.width / 2 + self.plateau / 2) <
                      (self.width + self.plateau)):
                    theta_t[i] = np.interp(
                        t[i] - t0 + self.width / 2 - self.plateau / 2,
                        t_tau, theta_tau)

            df = self.Coupling * (1 / np.tan(theta_t) - 1 / np.tan(theta_i))
            if self.qubit_spectrum is None:
                # Use linear dependence if no qubit spectrum was given
                values = df / self.dfdV
            else:
                values = self.df_to_dV(df)

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

    def calculate_gate(self, t0, t):
        """Calculate pulse gate.

        Parameters
        ----------
        t0 : float
            Pulse position, referenced to center of pulse.

        t : numpy array
            Array with time values for which to calculate the pulse gate.

        Returns
        -------
        waveform : numpy array
            Array containing pulse gate.

        """
        if not self.gated:
            raise ValueError('Waveform is not defined as gated.')
        y = np.zeros_like(t)
        dt = t[1] - t[0]
        start = int(
            np.ceil((t0 - self.total_duration() / 2 + self.gate_delay) / dt))
        stop = int(start + np.floor(self.gate_duration / dt))
        y[start:stop] = self.gate_amplitude
        return y

    def qubit_frequency(self, V):
        """Short summary.

        Parameters
        ----------
        V : type
            Description of parameter `V`.

        Returns
        -------
        type
            Description of returned object.

        """
        Vperiod = self.qubit_spectrum['Vperiod']
        Voffset = self.qubit_spectrum['Voffset']
        V0 = self.qubit_spectrum['V0']

        Ec = self.qubit_spectrum['Ec']
        f01_max = self.qubit_spectrum['f01_max']
        f01_min = self.qubit_spectrum['f01_min']

        EJS = (f01_max + Ec)**2 / (8 * Ec)
        d = (f01_min + Ec)**2 / (8 * EJ * Ec)
        F = np.pi * (V - Voffset) / Vperiod
        f = np.sqrt(8 * EJS * Ec * np.abs(np.cos(F)) *
                    np.sqrt(1 + d**2 * np.tan(F)**2)) - Ec
        return f

    def f_to_V(self, f):
        """Short summary.

        Parameters
        ----------
        f : type
            Description of parameter `f`.

        Returns
        -------
        type
            Description of returned object.

        """
        Vperiod = self.qubit_spectrum['Vperiod']
        Voffset = self.qubit_spectrum['Voffset']
        V0 = self.qubit_spectrum['V0']

        Ec = self.qubit_spectrum['Ec']
        f01_max = self.qubit_spectrum['f01_max']
        f01_min = self.qubit_spectrum['f01_min']

        # Make sure frequencies are inside the possible frequency range
        if np.any(f > f01_max):
            raise ValueError(
                'Frequency requested is outside the qubit spectrum')
        if np.any(f < f01_min):
            raise ValueError(
                'Frequency requested is outside the qubit spectrum')

        # Calculate the JJ parameters
        EJS = (f01_max + Ec)**2 / (8 * Ec)
        d = (f01_min + Ec)**2 / (8 * EJS * Ec)

        # Calculate the required EJ for the given frequencies
        EJ = (f + Ec)**2 / (8 * Ec)

        # Calculate the F=pi*(V-voffset)/vperiod corresponding to that EJ
        F = np.arcsin(np.sqrt((EJ**2 / EJS**2 - 1) / (d**2 - 1)))
        # And finally the voltage
        V = F * Vperiod / np.pi + Voffset

        # Mirror around Voffset, bounding the qubit to one side of the maxima
        if V0 >= Voffset:
            V[V < Voffset] = 2 * Voffset - V[V < Voffset]
        else:
            V[V > Voffset] = 2 * Voffset - V[V > Voffset]

        # Mirror beyond 1 period, bounding the qubit to one side of the minima
        Vminp = Vperiod / 2 + Voffset
        Vminn = -Vperiod / 2 + Voffset
        V[V > Vminp] = 2 * Vminp - V[V > Vminp]
        V[V < Vminn] = 2 * Vminn - V[V < Vminn]

        return V

    def df_to_dV(self, df):
        """Short summary.

        Parameters
        ----------
        df : type
            Description of parameter `df`.

        Returns
        -------
        type
            Description of returned object.

        """
        V0 = self.qubit_spectrum['V0']
        f0 = self.qubit_frequency(V0)
        return self.f_to_V(df + f0) - V0


if __name__ == '__main__':
    pass
