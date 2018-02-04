# -*- coding: utf-8 -*-
"""
@author: Fei Yan
"""

import numpy as np

import logging
log = logging.getLogger('LabberDriver')

List_sQubit = ['Q1', 'Q2', 'Q3']
List_sQubitParam = ['Frequency', 'Anharmonicity', 'Type', 'Ej', 'Ec', 'Asymmetry', 'Flux']
List_sCapParam = ['C1', 'C2', 'C3', 'C12', 'C23', 'C13']
List_sSeqType = ['Frequency', 'Anharmonicity', 'DriveP']
List_sPulseParam = ['Shape', 'PlateauStart', 'Rise', 'Plateau', 'Fall', 'Stretch', 'Amplitude', 'Frequency', 'Phase', 'DragCoeff']


### basic functions ###
def Ej_SQUID(flux,Ej_sum,d):
	# effective Ej of a SQUID
	return Ej_sum * np.abs(np.cos(np.pi*flux)) * np.sqrt(1+d**2*np.tan(np.pi*flux)**2) #[GHz]

def freq_SQUID(Ej, Ec):
	return np.sqrt(8 * Ej * Ec) - Ec

def freq_LC(L,C):
	# frequency of LC oscillator
	# L [H]
	# C [H]
	return 1/(2*np.pi)/np.sqrt(L*C)   #[GHz]

def Z_LC(L,C):
	# impedence of LC oscillator
	return np.sqrt(L/C)   #[Ohm]



### sequence generating fucnctions ###
# rise/fall generating functions
def UNIT_RAMP(t):
	return 1-t

def UNIT_COS(t):
	return np.cos(np.pi*t)

# exception for GAUSS/EXP/REVERSEEXP
def UNIT_GAUSS(t):
	return np.exp(-t**2)

def UNIT_EXP(t):
	return np.exp(-t)

def UNIT_REVERSEEXP(t):
	return np.exp(-np.abs(t))

#
def gen_fall(t, pulseCfg):
	return {
	'RAMP': UNIT_RAMP(t),
	'COS': UNIT_COS(t/pulseCfg.Stretch),
	'GAUSS': UNIT_GAUSS(t/pulseCfg.Stretch),
	'EXP': UNIT_EXP(t/pulseCfg.Stretch),
	'EXPFLIP': 1-UNIT_EXP((1-t)/pulseCfg.Stretch)
	}[pulseCfg.Shape]

def add_fall(t, pulseCfg):
	return (gen_fall(t/pulseCfg.Fall, pulseCfg) - gen_fall(1, pulseCfg)) / (gen_fall(0, pulseCfg) - gen_fall(1, pulseCfg))

def add_rise(t, pulseCfg):
	return (gen_fall(-t/pulseCfg.Rise, pulseCfg) - gen_fall(1, pulseCfg)) / (gen_fall(0, pulseCfg) - gen_fall(1, pulseCfg))

def add_pulse(t, pulseCfg):
	# add single pulse
	pulseCfg.Start = pulseCfg.PlateauStart - pulseCfg.Rise
	pulseCfg.PlateauEnd = pulseCfg.PlateauStart + pulseCfg.Plateau
	pulseCfg.End = pulseCfg.PlateauEnd + pulseCfg.Fall
	if t < pulseCfg.Start:
		y = 0
	elif pulseCfg.Start <= t < pulseCfg.PlateauStart:
		y = add_rise(t - pulseCfg.PlateauStart, pulseCfg)
	elif pulseCfg.PlateauStart <= t < pulseCfg.PlateauEnd:
		y = 1
	elif pulseCfg.PlateauEnd <= t < pulseCfg.End:
		y = add_fall(t - pulseCfg.PlateauEnd, pulseCfg)
	elif t >= pulseCfg.End:
		y = 0
	return y * pulseCfg.Amplitude * np.cos(2 * np.pi * pulseCfg.Frequency * t + pulseCfg.Phase)

def add_sequence(t, seqCfg):
	# add a sequence
	y = 0
	for n in range(seqCfg.nPulses):
		y += add_pulse(t, seqCfg.lpulseCfg[n])
	return y



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
			for sPulseParam in List_sPulseParam:
				pulseCfg = PulseConfiguration()
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
				setattr(self, sName, SequenceConfiguration(sQubit, sSeqType, CONFIG))
		#
		self.dTimeStart = CONFIG.get('Time Start')
		self.dTimeEnd = CONFIG.get('Time End')
		self.nTimeList = int(CONFIG.get('Number of Times'))
		self.tlist = np.linspace(self.dTimeStart, self.dTimeEnd, self.nTimeList)
		self.dt = self.tlist[1] - self.tlist[0]	


	### generate coefficient ###
	def	timeFunc_Q1_Frequency(self,t,args=None):
		return add_sequence(t, self.seqCfg_Q1_Frequency) + self.qubitCfg_Q1.Frequency

	def	timeFunc_Q1_Anharmonicity(self,t,args=None):
		return add_sequence(t, self.seqCfg_Q1_Anharmonicity) + self.qubitCfg_Q1.Anharmonicity

	def	timeFunc_Q1_DriveP(self,t,args=None):
		return add_sequence(t, self.seqCfg_Q1_DriveP)

	def	timeFunc_Q2_Frequency(self,t,args=None):
		return add_sequence(t, self.seqCfg_Q2_Frequency) + self.qubitCfg_Q2.Frequency

	def	timeFunc_Q2_Anharmonicity(self,t,args=None):
		return add_sequence(t, self.seqCfg_Q2_Anharmonicity) + self.qubitCfg_Q2.Anharmonicity

	def	timeFunc_Q2_DriveP(self,t,args=None):
		return add_sequence(t, self.seqCfg_Q2_DriveP)

	def	timeFunc_Q3_Frequency(self,t,args=None):
		return add_sequence(t, self.seqCfg_Q3_Frequency) + self.qubitCfg_Q3.Frequency

	def	timeFunc_Q3_Anharmonicity(self,t,args=None):
		return add_sequence(t, self.seqCfg_Q3_Anharmonicity) + self.qubitCfg_Q3.Anharmonicity

	def	timeFunc_Q3_DriveP(self,t,args=None):
		return add_sequence(t, self.seqCfg_Q3_DriveP)

	def	timeFunc_g12_pp(self,t,args=None):
		return 0.5 * self.capCfg.r12 * np.sqrt(self.timeFunc_Q1_Frequency(t) * self.timeFunc_Q2_Frequency(t))

	def	timeFunc_g23_pp(self,t,args=None):
		return 0.5 * self.capCfg.r23 * np.sqrt(self.timeFunc_Q2_Frequency(t) * self.timeFunc_Q3_Frequency(t))

	def	timeFunc_g13_pp(self,t,args=None):
		return 0.5 * self.capCfg.r13 * np.sqrt(self.timeFunc_Q1_Frequency(t) * self.timeFunc_Q3_Frequency(t))


	def generateSeqDisplay(self):
		#
		sPre = 'Time Series: '
		self.dict_Seq = {}
		for sQubit in List_sQubit:
			for sSeqType in List_sSeqType:
				sName = sPre + sQubit + ' ' + sSeqType
				self.dict_Seq[sName] = []
		#
		# self.dict_Seq = {sPreS + s : [] for s in self.lSeq}
		for sQubit in List_sQubit:
			for sSeqType in List_sSeqType:
				sName = sPre + sQubit + ' ' + sSeqType
				sCallName = 'timeFunc_' + sQubit + '_' + sSeqType
				methodToCall = getattr(self, sCallName)
				for t in self.tlist:
					self.dict_Seq[sName].append(methodToCall(t,[]))