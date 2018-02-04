# -*- coding: utf-8 -*-
"""
@author: Fei Yan
"""
import InstrumentDriver
from simulation import *
from sequence import *

import logging
log = logging.getLogger('LabberDriver')


class Driver(InstrumentDriver.InstrumentWorker):
	""" This class implements eigensolver of a multi-qubit system"""

	def performOpen(self, options={}):
		"""Perform the operation of opening the instrument connection"""
		# init variables
		# self.SEQ = None
		# self.SIM = None
		CONFIG = self.instrCfg.getValuesDict()
		self.SEQ = sequence(CONFIG)
		self.SIM = simulation_3Q(CONFIG)		


	def performSetValue(self, quant, value, sweepRate=0.0, options={}):
		"""Perform the Set Value instrument operation. This function should
		return the actual value set by the instrument"""
		# do nothing, just return value
		return value


	def performGetValue(self, quant, options={}):
		"""Perform the Get Value instrument operation""" 
		lSeqOutput = ['Time Series: ' + s for s in ['Q1 Frequency', 'Q1 Anharmonicity', 'Q1 DriveP', 'Q2 Frequency', 'Q2 Anharmonicity', 'Q2 DriveP', 'Q3 Frequency', 'Q3 Anharmonicity', 'Q3 DriveP']]
		#
		List_sPauli = ['I','X','Y','Z']
		List_sPauli2 = []
		for k1 in range(4):
			for k2 in range(4):
				List_sPauli2.append(List_sPauli[k1] + List_sPauli[k2])
		lStateFinal = ['Final ' + s for s in List_sPauli2]
		lStateTrace = ['Time Series: ' + s for s in List_sPauli2]
		#
		# check type of quantity
		if quant.name in lSeqOutput:
			if self.isConfigUpdated():
				self.performSequence()
			# get new value
			value = quant.getTraceDict(self.SEQ.dict_Seq[quant.name], t0=self.SEQ.tlist[0], dt=self.SEQ.dt)
		#
		# check type of quantity
		elif quant.name in lStateFinal:
			# output data, check if simulation needs to be performed
			# if self.isConfigUpdated():
			log.info(self.isConfigUpdated())
			self.performSimulation()
			# get new value
			value = self.SIM.dict_StateFinal[quant.name]
		#
		# check type of quantity
		elif quant.name in lStateTrace:
			# output data, check if simulation needs to be performed
			# if self.isConfigUpdated():
			self.performSimulation()
			# get new value
			value = quant.getTraceDict(self.SIM.dict_StateTrace[quant.name], t0=self.SIM.tlist[0], dt=self.SIM.dt)
		else:
			# otherwise, just return current value
			value = quant.getValue()
		return value

	def performSequence(self):
		CONFIG = self.instrCfg.getValuesDict()
		self.SEQ = sequence(CONFIG)
		self.SEQ.generateSeqDisplay()


		
	def performSimulation(self):
		"""Perform simulation"""
		CONFIG = self.instrCfg.getValuesDict()
		self.SEQ = sequence(CONFIG)
		self.SEQ.generateSeqDisplay()
		#
		self.SIM = simulation_3Q(CONFIG)
		self.SIM.updateSequence(self.SEQ)
		self.SIM.generateHamiltonian_3Q_cap()
		self.SIM.generateCollapse_3Q()
		self.SIM.generateInitialState()
		self.SIM.rhoEvolver_3Q()
		self.SIM.generateObservable()


if __name__ == '__main__':
	pass

