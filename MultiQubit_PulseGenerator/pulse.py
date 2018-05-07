#!/usr/bin/env python3
import numpy as np
from enum import Enum
import logging
from scipy.optimize import fmin
log = logging.getLogger('LabberDriver')

class PulseShape(Enum):
    """Define possible qubit pulses shapes"""
    GAUSSIAN = 'Gaussian'
    SQUARE = 'Square'
    RAMP = 'Ramp'
    CZ = 'CZ'
    COSINE = 'Cosine'


class PulseType(Enum):
    """Define possible qubit pulse types"""
    XY = 'XY'
    Z = 'Z'
    READOUT = 'Readout'

class Pulse(object):
    """This class represents a pulse for qubit rotations.

    Attributes
    ----------
    amplitude : float
        Pulse amplitude.

    width : float
        Pulse rise/fall duration.  The parameter is defined so that the pulse
        gives the same integrated area as a square pulse with the given width.

    plateau : float
        Pulse duration, not counting rise/fall.

    frequency : float
        Pulse frequency. Set to zero for baseband pulses.

    phase : float
        Pulse phase, in radians.

    shape : enum, {'Gaussian', 'Square', 'Ramp', 'CZ', 'Cosine'}
        Pulse shape.

    use_drag : bool
        If True, apply DRAG correction to pulse.

    drag_coefficient : float
        DRAG coefficient scaling.

    truncation_range : float
        Truncation range for Gaussian pulses,
        measured in units of the `width` parameter.

    pulse_type : enum, {'XY', 'Z', 'Readout'}
        What type of waveform the pulse is used for.

    start_at_zero : bool
        If True, forces the pulse to start at zero amplitude.

    gated : bool
        If True, generates a gate for the pulse. Can also be used as a trig.

    """

    def __init__(self,F_Terms=1,Coupling=20E6,Offset=300E6,
                 Lcoeff = np.array([0.3]),dfdV=0.5E9,period_2qb=50E-9,
                 amplitude=0.5, width=10E-9, plateau=0.0,
                 frequency=0.0, phase=0.0, shape=PulseShape.GAUSSIAN,
                 use_drag=False, drag_coefficient=0.0, truncation_range=5.0,
                 pulse_type=PulseType.XY, start_at_zero=False, gated=False,
                 gate_delay=0, gate_amplitude=1, gate_duration=None,
                 iq_ratio=1, iq_skew=0, i_offset=0, q_offset=0,
                 qubit_spectrum=None):

        # set variables
        self.amplitude = amplitude
        self.width = width
        self.plateau = plateau
        self.frequency = frequency
        self.phase = phase
        self.shape = shape
        self.use_drag = use_drag
        self.drag_coefficient = drag_coefficient
        self.truncation_range = truncation_range
        self.start_at_zero = start_at_zero
        self.pulse_type = pulse_type

        # For gating of the pulse
        self.gated = gated
        self.gate_delay = gate_delay
        self.gate_amplitude = gate_amplitude
        if gate_duration is None:
            self.gate_duration = self.total_duration()
        else:
            self.gate_duration = gate_duration

        # For CZ pulses
        self.F_Terms = F_Terms
        self.Coupling = Coupling
        self.Offset = Offset
        self.Lcoeff = Lcoeff
        self.dfdV = dfdV
        self.period_2qb = period_2qb
        self.qubit_spectrum = qubit_spectrum

        # For IQ mixer corrections
        self.iq_ratio = iq_ratio
        self.iq_skew = iq_skew
        self.i_offset = i_offset
        self.q_offset = q_offset

    def total_duration(self):
        """Calculate total pulse duration"""
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
        """Calculate pulse envelope

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

            values = values*self.amplitude

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

            values = values*self.amplitude

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
                        np.exp(-(t - (t0 - self.plateau / 2))**2 / (2 * std**2))
                    )
                    # after plateau
                    values += (
                        (t >= (t0 + self.plateau / 2)) *
                        np.exp(-(t - (t0 + self.plateau / 2))**2 / (2 * std**2))
                    )

            if self.start_at_zero:
                values = values - values.min()
                values = values/values.max()
            values = values*self.amplitude

        elif self.shape == PulseShape.CZ:
            # notation and calculations are based on the Paper "Fast adiabatic qubit gates using only sigma_z control" PRA 90, 022307 (2014)
            # pulse.Offset = config.get('f11-f20 initial, 2QB' + s)
            # pulse.amplitude = config.get('f11-f20 final, 2QB' + s)
            # Defining initial and final angles

            theta_i = np.arctan(self.Coupling/self.Offset) # Initial angle of on the |11>-|02> bloch sphere
            theta_f = np.arctan(self.Coupling/(self.amplitude)) # Final angle before moving back to initial angle

            # Normalize fouriere coefficients to initial and final angles
            self.Lcoeff *= (theta_f-theta_i)/(2*np.sum(self.Lcoeff[range(0,self.F_Terms,2)]))

            # defining helper variabels
            n = np.arange(1,self.F_Terms+1,1)
            n_points = 1000 # Number of points in the numerical integration

            # Calculate pulse width in tau variable - See paper for details
            tau = np.linspace(0,1,n_points)
            theta_tau = np.zeros(n_points)
            for i in range(n_points) :
                theta_tau[i] = np.sum(self.Lcoeff*(1 - np.cos(2*np.pi*n*tau[i]))) + theta_i
            t_tau = np.trapz(np.sin(theta_tau),x=tau)
            Width_tau = self.width/t_tau

            # Calculating angle and time as functions of tau
            tau = np.linspace(0,Width_tau,n_points)
            t_tau = np.zeros(n_points)
            for i in range(n_points) :
                theta_tau[i] = np.sum(self.Lcoeff*(1 - np.cos(2*np.pi*n*tau[i]/Width_tau) )) + theta_i
                if i > 0 :
                    t_tau[i] = np.trapz(np.sin(theta_tau[0:i]),x=tau[0:i])

            # Adding frequency pulse to waveform using 2Q pulse period. Padding waveform with theta_i if pulse width is less than 2Q pulse period.
            # Plateau is added as an extra extension of theta_f in the middle of the pulse.
            theta_t = np.ones(len(t))*theta_i
            for i in range(len(t)):
                if 0<(t[i]-t0+self.plateau/2)<self.plateau:
                    theta_t[i] = theta_f
                elif 0<(t[i]-t0+self.width/2+self.plateau/2)<(self.width + self.plateau)/2:
                    theta_t[i] = np.interp(t[i]-t0+self.width/2+self.plateau/2,t_tau,theta_tau)
                elif 0<(t[i]-t0+self.width/2+self.plateau/2)<(self.width + self.plateau):
                    theta_t[i] = np.interp(t[i]-t0+self.width/2-self.plateau/2,t_tau,theta_tau)

            df = self.Coupling*(1/np.tan(theta_t) - 1/np.tan(theta_i))
            if self.qubit_spectrum is None:
                # Use linear dependence if no qubit spectrum was given
                values = df/self.dfdV
            else:
                values = self.df_to_dV(df)

        elif self.shape == PulseShape.COSINE:
            tau = self.width
            if self.plateau == 0:
                values = self.amplitude/2*(1-np.cos(2*np.pi*(t-t0+tau/2)/tau))
            else:
                values = np.ones_like(t) * self.amplitude
                values[t<t0-self.plateau/2] = self.amplitude/2*(1-np.cos(2*np.pi*(t[t<t0-self.plateau/2]-t0+self.plateau/2+tau/2)/tau))
                values[t>t0+self.plateau/2] = self.amplitude/2*(1-np.cos(2*np.pi*(t[t>t0+self.plateau/2]-t0-self.plateau/2+tau/2)/tau))

        # Make sure the waveform is zero outside the pulse
        values[t<(t0-self.total_duration()/2)] = 0
        values[t>(t0+self.total_duration()/2)] = 0
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
            beta = self.drag_coefficient/(t[1]-t[0])
            y = y + 1j*beta*np.gradient(y)

        if self.pulse_type in (PulseType.XY, PulseType.READOUT):
            # Apply phase and SSB
            phase = self.phase
            # single-sideband mixing, get frequency
            omega = 2*np.pi*self.frequency
            # apply SSBM transform
            data_i = self.iq_ratio*(y.real * np.cos(omega*t-phase) +
                      -y.imag * np.cos(omega*t-phase+np.pi/2))
            data_q = (y.real * np.sin(omega*t-phase+self.iq_skew) +
                      -y.imag * np.sin(omega*t-phase+self.iq_skew+np.pi/2))
            y = data_i + 1j*data_q
        return y

    def calculate_gate(self, t0, t):
        """Calculate pulse gate

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
        dt = t[1]-t[0]
        start = int(np.ceil((t0-self.total_duration()/2+self.gate_delay)/dt))
        stop = int(start + np.floor(self.gate_duration/dt))
        y[start:stop] = self.gate_amplitude
        return y


    def qubit_frequency(self, V):
        """
            Qubit frequency as a function of voltage, including SQUID assymetry.
        """
        Vperiod = self.qubit_spectrum['Vperiod']
        Voffset = self.qubit_spectrum['Voffset']
        V0 = self.qubit_spectrum['V0']

        Ec = self.qubit_spectrum['Ec']
        f01_max = self.qubit_spectrum['f01_max']
        f01_min = self.qubit_spectrum['f01_min']

        EJ = (f01_max+Ec)**2/(8*Ec)
        d = (f01_min+Ec)**2/(8*EJ*Ec)
        F = np.pi*(V - Voffset)/Vperiod
        f = np.sqrt(8*EJ*Ec*np.abs(np.cos(F))*np.sqrt(1+d**2*np.tan(F)**2))-Ec
        return f


    def f_to_V(self, f):
        """
            Finds the voltages corresponding to the frequencies f.
        """
        Vperiod = self.qubit_spectrum['Vperiod']
        Voffset = self.qubit_spectrum['Voffset']
        V0 = self.qubit_spectrum['V0']

        if not isinstance(f, (list, np.ndarray)):
            f = [f]

        def g(V, f0):
            """
                Function to minimize.
            """
            return (f0-self.qubit_frequency(V))**2

        # Make sure that starting guess is on a slope.
        if V0 >= Voffset:
            V_start = Vperiod/4+Voffset
        else:
            V_start = -Vperiod/4+Voffset

        V = np.zeros_like(f)
        for n, f0 in enumerate(f):
            V[n] = fmin(g, V_start, args=(f0,))[0]

        # Mirror points around Voffset, bounding the qubit to one side of the maxima
        if V_start >= 0:
            V[V<Voffset] = 2*Voffset - V[V<Voffset]
        else:
            V[V>Voffset] = 2*Voffset - V[V>Voffset]

        # Mirror points beyond 1 period, bounding the qubit to one side of the minma
        Vminp = Vperiod/2+Voffset
        Vminn = -Vperiod/2+Voffset
        V[V>Vminp] = 2*Vminp - V[V>Vminp]
        V[V<Vminn] = 2*Vminn - V[V<Vminn]

        return V

    def df_to_dV(self, df):
        V0 = self.qubit_spectrum['V0']
        f0 = self.qubit_frequency(V0)
        f01_max = self.qubit_spectrum['f01_max']
        f01_min = self.qubit_spectrum['f01_min']
        if np.any(f0+df > f01_max):
            raise ValueError('Frequency requested is outside the qubit spectrum')
        if np.any(f0+df < f01_min):
            raise ValueError('Frequency requested is outside the qubit spectrum')
        return self.f_to_V(df+f0)-V0


if __name__ == '__main__':
    pass
