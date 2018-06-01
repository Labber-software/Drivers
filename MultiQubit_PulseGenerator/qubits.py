#!/usr/bin/env python3
import numpy as np


class Qubit:
    def __init__(self):
        pass

    def f_to_V(self, f):
        pass

    def V_to_f(self, V):
        pass

    def df_to_dV(self, df):
        pass


class Transmon(Qubit):
    def __init__(self, f01_max, f01_min, Ec, Vperiod, Voffset, V0):
        self.f01_max = f01_max
        self.f01_min = f01_min
        self.Ec = Ec
        self.Vperiod = Vperiod
        self.Voffset = Voffset
        self.V0 = V0

        # Calculate the JJ parameters
        self.EJS = (self.f01_max + self.Ec)**2 / (8 * self.Ec)
        self.d = (self.f01_min + self.Ec)**2 / (8 * self.EJS * self.Ec)

    def V_to_f(self, V):
        F = np.pi * (V - self.Voffset) / self.Vperiod
        f = np.sqrt(8 * self.EJS * self.Ec * np.abs(np.cos(F)) *
                    np.sqrt(1 + self.d**2 * np.tan(F)**2)) - self.Ec
        return f

    def f_to_V(self, f):
        # Make sure frequencies are inside the possible frequency range
        if np.any(f > self.f01_max):
            raise ValueError(
                'Frequency requested is outside the qubit spectrum')
        if np.any(f < self.f01_min):
            raise ValueError(
                'Frequency requested is outside the qubit spectrum')

        # Calculate the required EJ for the given frequencies
        EJ = (f + self.Ec)**2 / (8 * self.Ec)

        # Calculate the F=pi*(V-voffset)/vperiod corresponding to that EJ
        F = np.arcsin(np.sqrt((EJ**2 / self.EJS**2 - 1) / (self.d**2 - 1)))
        # And finally the voltage
        V = F * self.Vperiod / np.pi + self.Voffset

        # Mirror around Voffset, bounding the qubit to one side of the maxima
        if self.V0 >= self.Voffset:
            V[V < self.Voffset] = 2 * self.Voffset - V[V < self.Voffset]
        else:
            V[V > self.Voffset] = 2 * self.Voffset - V[V > self.Voffset]

        # Mirror beyond 1 period, bounding the qubit to one side of the minima
        Vminp = self.Vperiod / 2 + self.Voffset
        Vminn = -self.Vperiod / 2 + self.Voffset
        V[V > Vminp] = 2 * Vminp - V[V > Vminp]
        V[V < Vminn] = 2 * Vminn - V[V < Vminn]

        return V

    def df_to_dV(self, df):
        f0 = self.V_to_f(self.V0)
        return self.f_to_V(df + f0) - self.V0
