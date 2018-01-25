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
		self.multiqubit = MultiQubitHamiltonian()
		# self.vPolarization = np.zeros((4,))
		# self.lTrace = [np.array([], dtype=float) for n in range(4)]


	def performSetValue(self, quant, value, sweepRate=0.0, options={}):
		"""Perform the Set Value instrument operation. This function should
		return the actual value set by the instrument"""
		# do nothing, just return value
		return value


	def performGetValue(self, quant, options={}):
		"""Perform the Get Value instrument operation"""
		# dElevels = {'Eigenenergies unlabel': 0, 'Eigenenergies label': 1}
		# dPolarization = {'Polarization - X': 0, 'Polarization - Y': 1, 'Polarization - Z': 2, '3rd Level Population': 3}
		# check type of quantity
		if quant.name in list({'Eigenenergies unlabel'}) + list({'Eigenenergies label'}):
			# output data, check if simulation needs to be performed
			if self.isConfigUpdated():
				self.performSimulation()
			# get new value
			if quant.name == 'Eigenenergies unlabel':
				value = quant.getTraceDict(self.vals_unlabel_show*1E9, dt=1)
			if quant.name == 'Eigenenergies label':
				value = quant.getTraceDict(self.vals_label_show*1E9, dt=1)
		else:
			# otherwise, just return current value
			value = quant.getValue()
		return value


	def performSimulation(self):
		"""Perform simulation"""
		# get config values
		Config = dict(
					nQubit = int(self.getValue('Number of Qubits')),
					nTrunc = int(self.getValue('Degree of Trunction')),
					nShow = int(self.getValue('Max Number of Display')),
					bDesignParam_Q1 = bool(self.getValue('Q1 Use Design Parameter')),
					bDesignParam_Q2 = bool(self.getValue('Q2 Use Design Parameter')),
					bDesignParam_Q3 = bool(self.getValue('Q3 Use Design Parameter')),
					sQubitType_Q1 = self.getValue('Q1 Type'),
					sQubitType_Q2 = self.getValue('Q2 Type'),
					sQubitType_Q3 = self.getValue('Q3 Type'),
					dFreq_Q1 = self.getValue('Q1 Frequency')/1E9,
					dFreq_Q2 = self.getValue('Q2 Frequency')/1E9,
					dFreq_Q3 = self.getValue('Q3 Frequency')/1E9,
					dAnh_Q1 = self.getValue('Q1 Anharmonicity')/1E9,
					dAnh_Q2 = self.getValue('Q2 Anharmonicity')/1E9,
					dAnh_Q3 = self.getValue('Q3 Anharmonicity')/1E9,
					dC1 = self.getValue('Capacitance 1')*1E15,
					dC2 = self.getValue('Capacitance 2')*1E15,
					dC3 = self.getValue('Capacitance 3')*1E15,
					dC12 = self.getValue('Capacitance 12')*1E15,
					dC23 = self.getValue('Capacitance 23')*1E15,
					dC13 = self.getValue('Capacitance 13')*1E15,
					dEj_Q1 = self.getValue('Q1 Ej')/1E9,
					dEj_Q2 = self.getValue('Q2 Ej')/1E9,
					dEj_Q3 = self.getValue('Q3 Ej')/1E9,					
					dEc_Q1 = self.getValue('Q1 Ec')/1E9,
					dEc_Q2 = self.getValue('Q2 Ec')/1E9,
					dEc_Q3 = self.getValue('Q3 Ec')/1E9,
					dAsym_Q1 = self.getValue('Q1 Asymmetry'),
					dAsym_Q2 = self.getValue('Q2 Asymmetry'),
					dAsym_Q3 = self.getValue('Q3 Asymmetry'),
					dFlux_Q1 = self.getValue('Q1 Flux Bias'),
					dFlux_Q2 = self.getValue('Q2 Flux Bias'),
					dFlux_Q3 = self.getValue('Q3 Flux Bias'))
		# update config
		self.multiqubit.updateSimCfg(Config)
		if self.multiqubit.nQubit == 1:
			self.multiqubit.generateLabel_1Q()
			self.multiqubit.list_label_select = ["0","1","2","3"]
			self.multiqubit.generateHamiltonian_1Q_cap()
		if self.multiqubit.nQubit == 2:
			self.multiqubit.generateLabel_2Q()
			self.multiqubit.list_label_select = ["00","10","01","11","20","02"]
			self.multiqubit.generateHamiltonian_2Q_cap()
		elif self.multiqubit.nQubit == 3:
			self.multiqubit.generateLabel_3Q()
			self.multiqubit.list_label_select = ["000","100","010","001","110","101","011","200","020","002"]
			self.multiqubit.generateHamiltonian_3Q_cap()
		# log.info(str(self.multiqubit.dC1))
		#
		# find eigensolution of system Hamiltonian
		self.multiqubit.vals_unlabel, self.multiqubit.vecs_unlabel = eigensolve(self.multiqubit.H_sys)
		self.multiqubit.vals_label, self.multiqubit.vecs_label = level_identify(self.multiqubit.vals_unlabel, self.multiqubit.vecs_unlabel, self.multiqubit.list_label_table, self.multiqubit.list_label_select)
		self.vals_unlabel_show = self.multiqubit.vals_unlabel[:self.multiqubit.nShow]
		self.vals_label_show = self.multiqubit.vals_label[:self.multiqubit.nShow]


if __name__ == '__main__':
	pass

