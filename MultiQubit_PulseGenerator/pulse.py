#!/usr/bin/env python3
import numpy as np
from enum import Enum


class PulseShape(Enum):
    """Define possible qubit pulses shapes"""
    GAUSSIAN = 'Gaussian'
    SQUARE = 'Square'
    RAMP = 'Ramp'
    CZ = 'CZ'

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

    shape : enum, {'Gaussian', 'Square', 'Ramp'}
        Pulse shape.

    use_drag : bool
        If True, apply DRAG correction to pulse.

    drag_coefficient : float
        DRAG coefficient scaling.

    truncation_range : float
        Truncation range, measured in units of the `width` parameter.

    start_at_zero : bool
        If True, forces the pulse to start at zero amplitude

    z_pulse : bool
        If True, the pulse will be used for qubit Z control.

    """

    def __init__(self,F_Terms=1,Coupling=20E6,Offset=300E6,Lcoeff = np.array([0.3]),dfdV=0.5E9,period_2qb=50E-9, amplitude=0.5, width=10E-9, plateau=0.0,
                 frequency=0.0, phase=0.0, shape=PulseShape.GAUSSIAN,
                 use_drag=False, drag_coefficient=0.0, truncation_range=5.0,
                 z_pulse=False, start_at_zero=False):
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
        self.z_pulse = z_pulse
        self.start_at_zero = start_at_zero

        # For 2-qubit gates
        self.F_Terms = F_Terms
        self.Coupling = Coupling
        self.Offset = Offset
        self.Lcoeff = Lcoeff
        self.dfdV = dfdV
        self.period_2qb = period_2qb

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
            values = values*self.amplitude
            if self.start_at_zero:
                values = values - values.min()
                values = values/values.max()*self.amplitude

        elif self.shape == PulseShape.CZ:
            # notation and calculations are based on the Paper "Fast adiabatic qubit gates using only sigma_z control" PRA 90, 022307 (2014)

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

            # Going from frequency to voltage assuming a linear dependence. Should be improved in the future.
            values = (self.Coupling/np.tan(theta_t))/self.dfdV - (self.Coupling/np.tan(theta_i))/self.dfdV

        # return pulse envelope
        return values


if __name__ == '__main__':
    pass
