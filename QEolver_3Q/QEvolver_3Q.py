# -*- coding: utf-8 -*-
"""
Created on Wed Jan 24 2018

@author: Fei Yan
"""
import InstrumentDriver
import numpy as np
from QSolver_ForDriver_beta import *

# import logging
# log = logging.getLogger('LabberDriver')

class Driver(InstrumentDriver.InstrumentWorker):
	""" This class implements eigensolver of a multi-qubit system"""

	def performOpen(self, options={}):
		"""Perform the operation of opening the instrument connection"""
		# init variables
		self.qubitsim = Simulation()
		# self.vPolarization = np.zeros((4,))
		# self.lTrace = [np.array([], dtype=float) for n in range(4)]


	def performSetValue(self, quant, value, sweepRate=0.0, options={}):
		"""Perform the Set Value instrument operation. This function should
		return the actual value set by the instrument"""
		# do nothing, just return value
		return value


	def performGetValue(self, quant, options={}):
		"""Perform the Get Value instrument operation"""
		# lSeqOutput = ['Seq: Q1 Frequency', 'Seq: Q1 Anharmonicity', 'Seq: Q2 Frequency', 'Seq: Q2 Anharmonicity', 'Seq: Q3 Frequency', 'Seq: Q3 Anharmonicity', 'Seq: Q1 P-Drive', 'Seq: Q2 P-Drive', 'Seq: Q3 P-Drive'] 
		lSeqOutput = ['Seq: Q1 Frequency', 'Seq: Q2 Frequency', 'Seq: Q3 Frequency', 'Seq: Q1 P-Drive', 'Seq: Q2 P-Drive', 'Seq: Q3 P-Drive'] 
		lStateOutput = ['ZI','IZ','ZZ']
		# dPolarization = {'Polarization - X': 0, 'Polarization - Y': 1, 'Polarization - Z': 2, '3rd Level Population': 3}
		# check type of quantity
		if quant.name in lStateOutput:
			if self.isConfigUpdated():
				self.qubitsim = Simulation()
				self.qubitsim.generateSeqOutput()
			d0 = self.qubitsim.tlist[0]
			dt = self.qubitsim.dt
			value = {
			'Seq: Q1 Frequency': quant.getTraceDict(self.qubitsim.v_Q1_Freq*1E9, t0=t0, dt=dt),
			'Seq: Q2 Frequency': quant.getTraceDict(self.qubitsim.v_Q2_Freq*1E9, t0=t0, dt=dt),
			'Seq: Q3 Frequency': quant.getTraceDict(self.qubitsim.v_Q3_Freq*1E9, t0=t0, dt=dt),
			'Seq: Q1 P-Drive': quant.getTraceDict(self.qubitsim.v_Q1_DriveP*1E9, t0=t0, dt=dt),
			'Seq: Q2 P-Drive': quant.getTraceDict(self.qubitsim.v_Q2_DriveP*1E9, t0=t0, dt=dt),
			'Seq: Q3 P-Drive': quant.getTraceDict(self.qubitsim.v_Q3_DriveP*1E9, t0=t0, dt=dt)
			}[quant.name]
		#
		if quant.name in lStateOutput:
			# output data, check if simulation needs to be performed
			if self.isConfigUpdated():
				self.performSimulation()
			d0 = self.qubitsim.tlist[0]
			dt = self.qubitsim.dt
			# get new value
			value = quant.getTraceDict(self.qubitsim.dict_tomo[quant.name], t0=t0, dt=dt)
		else:
			# otherwise, just return current value
			value = quant.getValue()
		return value

		
	def performSimulation(self):
		"""Perform simulation"""
		self.qubitsim = Simulation()
		self.qubitsim.generateHamiltonian_3Q_cap()
		# self.qubitsim.generateLabel_3Q()
		self.qubitsim.generateInitialState()
		self.qubitsim.rhoEvolver_3Q()
		self.qubitsim.generateObservables()


if __name__ == '__main__':
	pass

