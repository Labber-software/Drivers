# -*- coding: utf-8 -*-
"""
@author: Fei Yan
"""

import numpy as np

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

def	timeFunc_Q1_Frequency(t,args=None):
	return add_sequence(t, args.seqCfg_Q1_Frequency) + args.qubitCfg_Q1.Frequency

def	timeFunc_Q1_Anharmonicity(t,args=None):
	return add_sequence(t, args.seqCfg_Q1_Anharmonicity) + args.qubitCfg_Q1.Anharmonicity

def	timeFunc_Q1_DriveP(t,args=None):
	return add_sequence(t, args.seqCfg_Q1_DriveP)

def	timeFunc_Q2_Frequency(t,args=None):
	return add_sequence(t, args.seqCfg_Q2_Frequency) + args.qubitCfg_Q2.Frequency

def	timeFunc_Q2_Anharmonicity(t,args=None):
	return add_sequence(t, args.seqCfg_Q2_Anharmonicity) + args.qubitCfg_Q2.Anharmonicity

def	timeFunc_Q2_DriveP(t,args=None):
	return add_sequence(t, args.seqCfg_Q2_DriveP)

def	timeFunc_Q3_Frequency(t,args=None):
	return add_sequence(t, args.seqCfg_Q3_Frequency) + args.qubitCfg_Q3.Frequency

def	timeFunc_Q3_Anharmonicity(t,args=None):
	return add_sequence(t, args.seqCfg_Q3_Anharmonicity) + args.qubitCfg_Q3.Anharmonicity

def	timeFunc_Q3_DriveP(t,args=None):
	return add_sequence(t, args.seqCfg_Q3_DriveP)

def	timeFunc_g12_pp(t,args=None):
	return 0.5 * args.capCfg.r12 * np.sqrt(timeFunc_Q1_Frequency(t,args) * timeFunc_Q2_Frequency(t,args))

def	timeFunc_g23_pp(t,args=None):
	return 0.5 * args.capCfg.r23 * np.sqrt(timeFunc_Q2_Frequency(t,args) * timeFunc_Q3_Frequency(t,args))

def	timeFunc_g13_pp(t,args=None):
	return 0.5 * args.capCfg.r13 * np.sqrt(timeFunc_Q1_Frequency(t,args) * timeFunc_Q3_Frequency(t,args))