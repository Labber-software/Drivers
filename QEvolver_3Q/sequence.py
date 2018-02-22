# -*- coding: utf-8 -*-
"""
@author: Fei Yan
"""

import numpy as np
from basicfunc import *

import logging
log = logging.getLogger('LabberDriver')

List_sQubit = ['Q1', 'Q2', 'Q3']
List_sQubitParam = ['Frequency', 'Anharmonicity', 'Type', 'Ej', 'Ec', 'Asymmetry', 'Flux']
List_sCapParam = ['C1', 'C2', 'C3', 'C12', 'C23', 'C13']
List_sSeqType = ['Frequency', 'Anharmonicity', 'DriveP']
List_sPulseParam = ['Shape', 'PlateauStart', 'Rise', 'Plateau', 'Fall', 'Stretch', 'Amplitude', 'Frequency', 'Phase', 'DragCoeff']

# dict_Seq = {'Time Series: Q1 Frequency': [], 
# 			'Time Series: Q1 Anharmonicity': [], 
# 			'Time Series: Q1 DriveP': [], 
# 			'Time Series: Q2 Frequency': [], 
# 			'Time Series: Q2 Anharmonicity': [], 
# 			'Time Series: Q2 DriveP': [], 
# 			'Time Series: Q3 Frequency': [], 
# 			'Time Series: Q3 Anharmonicity': [], 
# 			'Time Series: Q3 DriveP': [], 
# 			'Time Series: Q3 DriveP': [], 
# 			'Time Series: g12 pp': [], 
# 			'Time Series: g23 pp': [], 
# 			'Time Series: g13 pp': []}

dict_timeFunc = {'timeFunc_Q1_Frequency':timeFunc_Q1_Frequency,
				'timeFunc_Q1_Anharmonicity':timeFunc_Q1_Anharmonicity,
				'timeFunc_Q1_DriveP':timeFunc_Q1_DriveP,
				'timeFunc_Q2_Frequency':timeFunc_Q2_Frequency,
				'timeFunc_Q2_Anharmonicity':timeFunc_Q2_Anharmonicity,
				'timeFunc_Q2_DriveP':timeFunc_Q2_DriveP,
				'timeFunc_Q3_Frequency':timeFunc_Q3_Frequency,
				'timeFunc_Q3_Anharmonicity':timeFunc_Q3_Anharmonicity,
				'timeFunc_Q3_DriveP':timeFunc_Q3_DriveP,
				'timeFunc_g12_pp':timeFunc_g12_pp,
				'timeFunc_g23_pp':timeFunc_g23_pp,
				'timeFunc_g13_pp':timeFunc_g13_pp}


class QubitConfiguration():

	def __init__(self, sQubit, CONFIG):
		self.sQubit = sQubit
		self.bUseDesignParam = CONFIG.get(sQubit + ' Use Design Parameter')
		for sQubitParam in List_sQubitParam:
			sCallName = sQubit + ' ' + sQubitParam
			setattr(self, sQubitParam, CONFIG.get(sCallName))


class CapacitanceConfiguration():

	def __init__(self, CONFIG):
		for sCapParam in List_sCapParam:
			sCallName = 'Capacitance ' + sCapParam.replace("C", "")
			setattr(self, sCapParam, CONFIG.get(sCallName))
		self.r12 = self.C12 / np.sqrt(self.C1 * self.C2)
		self.r23 = self.C23 / np.sqrt(self.C2 * self.C3)
		self.r13 = self.r12 * self.r23 + self.C13 / np.sqrt(self.C1 * self.C3)


class PulseConfiguration():

	def __init__(self):
		self.Shape = 'GAUSS'
		self.PlateauStart = 0.0E-9
		self.Rise = 5.0E-9
		self.Plateau = 0.0E-9
		self.Fall = 5.0E-9
		self.Stretch = 1.0
		self.Amplitude = 1.0E9
		self.Frequency = 5.0E9
		self.Phase = 0.0
		self.DragCoeff = 0.0


class SequenceConfiguration():

	def __init__(self, sQubit, sSeqType, CONFIG):
		self.sQubit = sQubit
		self.sSeqType = sSeqType
		sSeqName = 'Seq ' + sQubit + ' ' + sSeqType + ': '
		self.nPulses = int(CONFIG.get(sSeqName + 'Pulse Number'))
		self.lpulseCfg = []
		for n in range(self.nPulses):
			pulseCfg = PulseConfiguration()
			for sPulseParam in List_sPulseParam:
				sCallName = sSeqName + sPulseParam + ' #%d' %(n+1)
				setattr(pulseCfg, sPulseParam, CONFIG.get(sCallName))
			self.lpulseCfg.append(pulseCfg)



class sequence():

	def __init__(self, CONFIG):
		# generate qubit idling config.
		for sQubit in List_sQubit:
			sName = 'qubitCfg_' + sQubit
			setattr(self, sName, QubitConfiguration(sQubit, CONFIG))
		# generate capacitance network config.
		self.capCfg = CapacitanceConfiguration(CONFIG)
		# generate sequence config.
		for sQubit in List_sQubit:
			for sSeqType in List_sSeqType:
				sName = 'seqCfg_' + sQubit + '_' + sSeqType
				seqCfg = SequenceConfiguration(sQubit, sSeqType, CONFIG)
				setattr(self, sName, seqCfg)
		#
		self.dTimeStart = CONFIG.get('Time Start')
		self.dTimeEnd = CONFIG.get('Time End')
		# self.nTimeList = int(CONFIG.get('Number of Times'))
		self.dSampleFreq = CONFIG.get('Sampling Frequency')
		self.nTimeList = int((self.dTimeEnd - self.dTimeStart) * self.dSampleFreq + 1)
		self.tlist = np.linspace(self.dTimeStart, self.dTimeEnd, self.nTimeList)
		self.dt = self.tlist[1] - self.tlist[0]
		#
		self.dict_Seq = {}


	def generateSeqDisplay(self):
		#
		for key, method in dict_timeFunc.items():
			sName = 'Time Series: ' + key.replace('timeFunc_','').replace('_',' ')
			self.dict_Seq[sName] = []
		#
		for key, method in dict_timeFunc.items():
			sName = 'Time Series: ' + key.replace('timeFunc_','').replace('_',' ')
			for t in self.tlist:
				self.dict_Seq[sName].append(method(t,self))
