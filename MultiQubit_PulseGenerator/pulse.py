#!/usr/bin/env python3
import numpy as np
from enum import Enum


class PulseShape(Enum):
    """Define possible qubit pulses shapes"""
    GAUSSIAN = 'Gaussian'
    SQUARE = 'Square'
    RAMP = 'Ramp'


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

    z_pulse : bool
        If True, the pulse will be used for qubit Z control.

    """

    def __init__(self, amplitude=1.0, width=10E-9, plateau=0.0,
                 frequency=0.0, phase=0.0, shape=PulseShape.GAUSSIAN,
                 use_drag=False, drag_coefficient=0.0, truncation_range=5.0,
                 z_pulse=False):
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


    def total_duration(self):
        """Calculate total pulse duration"""
        # calculate total length of pulse
        if self.shape == PulseShape.SQUARE:
            duration = self.width + self.plateau
        elif self.shape == PulseShape.RAMP:
            duration = 2 * self.width + self.plateau
        elif self.shape == PulseShape.GAUSSIAN:
            duration = self.truncation_range * self.width + self.plateau
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
            values = ((t >= (t0 - (self.width + self.plateau) / 2)) &
                      (t < (t0 + (self.width + self.plateau) / 2)))

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

        # scale to correct amplitude
        values = self.amplitude * values
        # return pulse envelope
        return values


if __name__ == '__main__':
    pass

