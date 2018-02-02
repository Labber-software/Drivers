# -*- coding: utf-8 -*-
"""
@author: Fei Yan
"""
import InstrumentDriver
import numpy as np
from simulation import *
from sequence import *

import logging
log = logging.getLogger('LabberDriver')



class Driver(InstrumentDriver.InstrumentWorker):
	""" This class implements eigensolver of a multi-qubit system"""

	def performOpen(self, options={}):
		"""Perform the operation of opening the instrument connection"""
		# init variables
		self.qubitsim = Simulation()
		self.bShowFrequency = bool(self.getValue('Show Frequency'))
		self.bShowDrive = bool(self.getValue('Show Drive'))
		self.bShowMeasurement = bool(self.getValue('Show Measurement'))
		# self.vPolarization = np.zeros((4,))
		# self.lTrace = [np.array([], dtype=float) for n in range(4)]


	def performSetValue(self, quant, value, sweepRate=0.0, options={}):
		"""Perform the Set Value instrument operation. This function should
		return the actual value set by the instrument"""
		# do nothing, just return value
		return value


	def performGetValue(self, quant, options={}):
		"""Perform the Get Value instrument operation"""
		sPre = 'Time Series: '
		lFreqOutput = [sTimeSeries + s for s in ['Q1 Frequency', 'Q2 Frequency', 'Q3 Frequency']]
		lDriveOutput = [sTimeSeries + s for s in ['Q1 DriveP', 'Q2 DriveP', 'Q3 DriveP']]
		#
		list_pauli_label = ['I','X','Y','Z']
		lpauli2 = []
		for k1 in range(4):
			for k2 in range(4):
				lpauli2.append(list_pauli_label[k1] + list_pauli_label[k2])
		lStateOutput = [sTimeSeries + s for s in lpauli2]
		#
		# check type of quantity
		if self.bShowFrequency and (quant.name in lFreqOutput):
			if self.isConfigUpdated():
				self.qubitsim = Simulation()
				self.qubitsim.generateSeqOutput()
			# get new value
			value = quant.getTraceDict(self.qubitsim.dict_seq[quant.name]*1E9, t0=self.qubitsim.tlist[0]*1E-9, dt=self.qubitsim.dt*1E-9)
		#
		# check type of quantity
		if self.bShowDrive and (quant.name in lDriveOutput):
			if self.isConfigUpdated():
				self.qubitsim = Simulation()
				self.qubitsim.generateSeqOutput()
			# get new value
			value = quant.getTraceDict(self.qubitsim.dict_seq[quant.name]*1E9, t0=self.qubitsim.tlist[0]*1E-9, dt=self.qubitsim.dt*1E-9)
		#
		# check type of quantity
		if self.bShowMeasurement and (quant.name in lStateOutput):
			# output data, check if simulation needs to be performed
			if self.isConfigUpdated():
				self.performSimulation()
			# get new value
			value = quant.getTraceDict(self.qubitsim.dict_tomo[quant.name], t0=self.qubitsim.tlist[0]*1E-9, dt=self.qubitsim.dt*1E-9)
		else:
			# otherwise, just return current value
			value = quant.getValue()
		return value

		
	def performSimulation(self):
		"""Perform simulation"""
		self.qubitsim = simulation()
		self.sequence = sequence()
		self.qubitsim.generateHamiltonian_3Q_cap()
		# self.qubitsim.generateLabel_3Q()
		self.qubitsim.generateInitialState()
		self.qubitsim.rhoEvolver_3Q()
		self.qubitsim.generateObservables()


if __name__ == '__main__':
	pass

