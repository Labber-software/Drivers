#!/usr/bin/env python3
import numpy as np
from copy import copy
from sequence import Sequence
from gates import Gate, VirtualZGate, CompositeGate, IdentityGate
from pulse import PulseShape, Pulse

# add logger, to allow logging to Labber's instrument log
import logging
log = logging.getLogger('LabberDriver')

# TODO Move first delay to sequence

class Rabi(Sequence):
    """Sequence for driving Rabi oscillations in multiple qubits"""

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms"""
        # get parameters
        uniform_amplitude = config['Uniform pulse ampiltude for all qubits']
        # just add pi-pulses for the number of available qubits
        self.add_gate_to_all(Gate.Xp)



class CPMG(Sequence):
    """Sequence for multi-qubit Ramsey/Echo/CMPG experiments"""

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms"""
        # get parameters
        n_pulse = int(config['# of pi pulses'])
        pi_to_q = config['Add pi pulses to Q']
        duration = config['Sequence duration']
        edge_to_edge = config['Edge-to-edge pulses']

        max_width = np.max([p.total_duration() for p in self.pulses_1qb[:self.n_qubit]])
        # select type of refocusing pi pulse
        gate_pi = Gate.Yp if pi_to_q else Gate.Xp

        # add pulses for all active qubits
        for n, pulse in enumerate(self.pulses_1qb[:self.n_qubit]):
            # special case for -1 pulses => T1 experiment
            if n_pulse < 0:
                # add pi pulse
                self.add_single_gate(n, Gate.Xp)
                # delay the reaodut by adding an I gate
                self.add_single_gate(n, IdentityGate(duration))
                continue

            # Calculate the effective dt
            if edge_to_edge:
                # Duration is the total time between pulses
                dt = duration/(n_pulse+1)
            else:
                # Duration is from center to center of pi/2 pulses
                dt = duration/(n_pulse+1) - self.pulses_1qb[n].total_duration()
            # TODO Fix this
            # Align everything to the end of the last pulse of the one with the longest pulse width
            # t0 += (max_width - self.pulses_1qb[n].total_duration()) * (n_pulse + 1) if edge_to_edge else 0.0
            # t0 += (max_width - self.pulses_1qb[n].total_duration())


            # First pi/2 pulse
            self.add_single_gate(n, Gate.X2p)

            # add pi pulses, one by one
            for i in range(n_pulse):
                self.add_single_gate(n, gate_pi, dt=dt)

            # add last pi/2 pulse
            self.add_single_gate(n, Gate.X2p, dt=dt)


class PulseTrain(Sequence):
    """Sequence for multi-qubit pulse trains, for pulse calibrations"""

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms"""
        # get parameters
        n_pulse = int(config['# of pulses'])
        alternate = config['Alternate pulse direction']

        # create list with gates
        gates = []
        for n in range(n_pulse):
            # check if alternate pulses
            if alternate and (n % 2) == 1:
                gate = Gate.Xm
            else:
                gate = Gate.Xp
            # create list with same gate for all active qubits
            gate_qubits = [gate for q in range(self.n_qubit)]
            # append to list of gates
            gates.append(gate_qubits)

        # add list of gates to sequence
        self.add_gates(gates)

class CZgates(Sequence):
    """Sequence for multi-qubit pulse trains, for pulse calibrations"""

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms"""
        # get parameters
        n_pulse = int(config['# of pulses, CZgates'])

        # create list with gates
        gates = []
        for n in range(n_pulse):
            gate = Gate.CPh
            # create list with same gate for all active qubits
            gate_qubits = [gate for q in range(self.n_qubit)]
            # append to list of gates
            gates.append(gate_qubits)

        # add list of gates to sequence
        self.add_gates(gates)


class CZecho(Sequence):
    """Sequence for multi-qubit pulse trains, for pulse calibrations"""

    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms"""

        # create list with gates
        # self.add_single_gate(0, Gate.X2p, self.first_delay + self.period_1qb/2)
        # self.add_single_gate(0, Gate.CPh, self.first_delay + self.period_1qb + self.period_2qb/2)
        # self.add_single_gate(0, Gate.Xp, self.first_delay + 3*self.period_1qb/2 + self.period_2qb)
        # self.add_single_gate(1, Gate.Xp, self.first_delay + 5*self.period_1qb/2 + self.period_2qb)
        # self.add_single_gate(0, Gate.CPh, self.first_delay + 3*self.period_1qb + 3*self.period_2qb/2)
        # self.add_single_gate(0, Gate.X2p, self.first_delay + 7*self.period_1qb/2 + 2*self.period_2qb)
        # self.add_single_gate(1, Gate.Xp, self.first_delay + 9*self.period_1qb/2 + 2*self.period_2qb)

        CZEchoGate = CompositeGate(n_qubit=2)
        CZEchoGate.add_gate([Gate.X2p, Gate.I])
        CZEchoGate.add_gate([Gate.CPh, Gate.I])
        CZEchoGate.add_gate([Gate.Xp, Gate.Xp])
        CZEchoGate.add_gate([Gate.CPh, Gate.I])
        CZEchoGate.add_gate([Gate.X2p, Gate.Xp])
        self.add_gate(qubit=[0, 1], gate=CZEchoGate)


class VZ(Sequence):
    def generate_sequence(self, config):
        """Generate sequence by adding gates/pulses to waveforms"""
        # get parameters
        duration = config['Sequence duration']
        z_angle = config['Z Phase']*np.pi/180
        edge_to_edge = config['Edge-to-edge pulses']
        self.virtual_z_gates = []


        width = 0 if edge_to_edge else self.pulses_1qb[0].total_duration()
        vz = VirtualZGate(angle=z_angle)
        # self.add_gate(0, Gate.X2p)
        # self.add_gate(0, vz)
        # self.add_gate(0, Gate.X2p)
        c = CompositeGate(2)

        c.add_gate([Gate.X2p, Gate.I])
        c.add_gate([Gate.I, Gate.Yp], dt=10e-9)
        c.add_gate([Gate.X2p, Gate.I])


        log.log(20, 'Adding c gate')
        # Handle qubit=[[0, 1], 2], gate=[c, Gate.X2p]
        self.add_gate([0, 1], c)
        self.add_gate([1, 0], c, dt=20e-9)
        self.add_gate(2, Gate.Xm)
        self.add_gate(0, Gate.Ry)




if __name__ == '__main__':
    pass
