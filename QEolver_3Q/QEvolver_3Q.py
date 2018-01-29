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
		lStateOutput = []
		# dPolarization = {'Polarization - X': 0, 'Polarization - Y': 1, 'Polarization - Z': 2, '3rd Level Population': 3}
		# check type of quantity
		if quant.name in lStateOutput:
			if self.isConfigUpdated():
				self.qubitsim = Simulation()
				self.qubitsim.generateSeqOutput()
			d0 = self.qubitsim.tlist[0]
			dt = self.qubitsim.tlist[1] - self.qubitsim.tlist[0]
			value = {
			'Seq: Q1 Frequency': quant.getTraceDict(self.qubitsim.v_Q1_Freq*1E9, t0=t0, dt=dt),
			'Seq: Q2 Frequency': quant.getTraceDict(self.qubitsim.v_Q2_Freq*1E9, t0=t0, dt=dt),
			'Seq: Q3 Frequency': quant.getTraceDict(self.qubitsim.v_Q3_Freq*1E9, t0=t0, dt=dt),
			'Seq: Q1 P-Drive': quant.getTraceDict(self.qubitsim.v_Q1_DriveP*1E9, t0=t0, dt=dt),
			'Seq: Q2 P-Drive': quant.getTraceDict(self.qubitsim.v_Q2_DriveP*1E9, t0=t0, dt=dt),
			'Seq: Q3 P-Drive': quant.getTraceDict(self.qubitsim.v_Q3_DriveP*1E9, t0=t0, dt=dt)
			}[quant.name]


		if quant.name in list({'Eigenenergies unlabel'}) + list({'Eigenenergies label'}):
			# output data, check if simulation needs to be performed
			if self.isConfigUpdated():
				self.performInitialization()
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
		self.qubitsim = Simulation()
		self.qubitsim.generateHamiltonian_3Q_cap()
		vals, vecs = eigensolve(self.qubitsim.H_sys)
		
		self.rho0 = 
		qubitsim.list_label_select = ["000","100","010","001","110","101","011","200","020","002"]
		qubitsim.generateHamiltonian_3Q_cap()
		

			self.multiqubit.generateLabel_3Q()
			self.multiqubit.list_label_select = ["000","100","010","001","110","101","011","200","020","002"]
			self.multiqubit.generateHamiltonian_3Q_cap()

					vals, vecs = ch.getEnergyLevels(H_idle.full(), opt_sparse = False)
vals_select, vecs_select = level_sort(vals, vecs, label_select, list_label_table)


		qubitsim.rho0 = 
		qubitsim.tlist = 
		qubitsim.generateCollapse_3Q()
		self.tlist = np.linspace(self.dTimeStart, self.dTimeEnd, self.nTimeList)
		self.rho_input_lab = T(rho_input_rot, U(self.H_sys, t_start))
		self.sequence = Sequence()
		qubitsim.rhoEvolver_3Q()
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

