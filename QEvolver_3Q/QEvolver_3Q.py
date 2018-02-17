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
		lSeqOutput = ['Time Series: ' + s for s in ['Q1 Frequency', 'Q1 Anharmonicity', 'Q1 DriveP', 'Q2 Frequency', 'Q2 Anharmonicity', 'Q2 DriveP', 'Q3 Frequency', 'Q3 Anharmonicity', 'Q3 DriveP', 'g12 pp', 'g23 pp', 'g13 pp']]
		#
		List_sPauli = ['I','X','Y','Z']
		lTraceOutput = ['Time Series: ' + s1 + s2 for s1 in List_sPauli for s2 in List_sPauli]
		#
		# check type of quantity
		if quant.name in lSeqOutput:
			if self.isConfigUpdated():
				self.performSequence()
			# get new value
			value = quant.getTraceDict(self.SEQ.dict_Seq[quant.name], t0=self.SEQ.tlist[0], dt=self.SEQ.dt)
		#
		elif quant.name in ['Final State']:
			if self.isConfigUpdated():
				self.performSimulation()
			value = quant.getTraceDict(self.SIM.final_state, x0=0, dx=1)
		#
		elif quant.name in ['Final Pauli-16']:
			if self.isConfigUpdated():
				self.performSimulation()
			value = quant.getTraceDict(self.SIM.final_pauli16, x0=0, dx=1)
		#
		elif quant.name in lTraceOutput:
			# output data, check if simulation needs to be performed
			if self.isConfigUpdated():
				self.performSimulation()
			# get new value
			value = quant.getTraceDict(self.SIM.dict_Trace[quant.name], t0=self.SIM.tlist[0], dt=self.SIM.dt)
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
		self.SIM.generateInitialState()
		#
		self.bUseT1Collapse = bool(CONFIG.get('Use T1 Collapse'))
		if self.bUseT1Collapse:
			self.SIM.generateCollapse_3Q()
			self.bUseDensityMatrix == True
		else:
			self.bUseDensityMatrix = bool(CONFIG.get('Use Density Matrix'))
		#
		self.bShowTrace = bool(CONFIG.get('Show Trace'))
		log.info(self.bUseDensityMatrix)
		log.info(self.bShowTrace)
		if self.bUseDensityMatrix:
			self.SIM.rhoEvolver_3Q()
			self.SIM.generateFinalRho()
			if self.bShowTrace:
				self.SIM.generateTraceRho()
		else:
			self.SIM.psiEvolver_3Q()
			self.SIM.generateFinalPsi()
			if self.bShowTrace:
				self.SIM.generateTracePsi()


if __name__ == '__main__':
	pass

