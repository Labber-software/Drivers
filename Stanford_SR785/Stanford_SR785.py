#!/usr/bin/env python

import InstrumentDriver
from VISA_Driver import VISA_Driver
from InstrumentConfig import InstrumentQuantity
import numpy as np
from struct import *
import time

# version 0.1

#class Error(Exception):
#    pass

class Driver(VISA_Driver):
    """ This class implements the Stanford SR785 Spectrum Analyzer driver"""

    def performOpen (self , options ={}):
        """ Perform the operation of opening the instrument connection """
        #self.writeAndLog('*CLS')
        VISA_Driver.performOpen(self, options=options)
        self.writeAndLog('*CLS')
        self.writeAndLog('OUTX0') # set output to GPIB
        self.writeAndLog('PDST 3') #set Print/Plot/Dump destination to GPIB
        self.writeAndLog('DISP 2, 1') # set displays live
        self.writeAndLog('DFMT 1') # set displays to dual display
        self.writeAndLog('ACTD 0') # set active display to displayA
        self.writeAndLog('RPMF 0') # set Hz as frequency units (not RPM)		
        self.writeAndLog('A1RG 1') # Autoranges Channel 1
        self.writeAndLog('A2RG 1') # Autoranges Channel 2
        self.writeAndLog('I1AR 1') # Autotracks Channel 1
        self.writeAndLog('I2AR 1') # Autotracks Channel 2		
        self.writeAndLog('ASCL 0') # Autoscales Display 0
        self.writeAndLog('ASCL 1') # Autoscales Display 1	
        self.writeAndLog('STRT') # Starts measurement
        #self.writeAndLog('PLAY 1') # Play Sound
		
    def performClose(self, bError=False, options={}):
		time.sleep(1)
		#self.writeAndLog('PAUS')

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
		"""Perform the Set Value instrument operation. This function should
		return the actual value set by the instrument"""        
		#self.writeAndLog(str(quant.name)+str(value)+str(sweepRate)+str(options),) for error logging
		
		if quant.name in ('Reset Device To Default'):
			if value:
				self.writeAndLog('*RST',)
				time.sleep(15) #sleep 15 seconds until device resets
				
				
				
		if quant.name in ('Measurement Group'):
			self.writeAndLog('MGRP 2, ' +value[0],)
		if quant.name in ('FFT','Correlation','Octave','Swept Sine','Order', 'Time Histogram'):
			if value in ('Inapplicable'):
				return value
			if value[1] is not (' '): #i.e. value to set is <10
				self.writeAndLog('MEAS 2, '+value[0]+value[1],)
			else:
				self.writeAndLog('MEAS 2, '+value[0],)
		if quant.name in ('View Type'):
			self.writeAndLog('VIEW 2, ' +value[0],)
		if quant.name in ('Unit dB'):
			self.writeAndLog('UNDB 2, ' +value[0],)
		if quant.name in ('Unit pk'):
			self.writeAndLog('UNPK 2, ' +value[0],)
		if quant.name in ('Unit psd'):
			self.writeAndLog('PSDU 2, ' +value[0],)
		if quant.name in ('phase units'):
			self.writeAndLog('UNPH 2, ' +value[0],)
		if quant.name in ('SS Start Frequency'):
			self.writeAndLog('SSTR 2, ' +str(value),)
		if quant.name in ('SS Stop Frequency'):
			self.writeAndLog('SSTP 2, ' +str(value),)
		if quant.name in ('SS Continuous Scan'):
			if value:
				self.writeAndLog('SRPT 2, ' +"1",)
			else:
				self.writeAndLog('SRPT 2, ' +"0",)
		if quant.name in ('SS Sweep Type'):
			self.writeAndLog('SSTY 2, ' +value[0],)
		if quant.name in ('SS Number Of Points'):
			self.writeAndLog('SNPS 2, ' +str(value),)
		if quant.name in ('SS Auto Resolution'):
			if value:
				self.writeAndLog('SARS 2, ' +"1",)
			else:
				self.writeAndLog('SARS 2, ' +"0",)
		if quant.name in ('SS Maximum Skips'):
			self.writeAndLog('SSKP 2, ' +str(value),)
		if quant.name in ('SS Faster Threshold'):
			self.writeAndLog('SFST 2,' +str(value),)
		if quant.name in ('SS Lower Threshold'):
			self.writeAndLog('SSLO 2,' +str(value),)
		if quant.name in ('SS Auto Level Reference*'):
			self.writeAndLog('SSAL ' +value[0],)
		if quant.name in ('SS Amplitude*'):
			self.writeAndLog('SSAM ' +str(value),)
		if quant.name in ('SS Ideal Reference*'):
			self.writeAndLog('SSRF ' +str(value),)
		if quant.name in ('SS Source Ramping*'):
			if value:
				self.writeAndLog('SRMP ' +"1",)
			else:
				self.writeAndLog('SRMP ' +"0",)
		if quant.name == 'SS Source Ramping Rate*':
			#self.writeAndLog(str(quant.name))
			self.writeAndLog('SRAT ' +str(value),)
		if quant.name in ('SS Reference Upper Limit*'):
			self.writeAndLog('SSUL ' +str(value),)
		if quant.name in ('SS Reference Lower Limit*'):
			self.writeAndLog('SSLL ' +str(value),)
		if quant.name in ('SS Maximum Level*'):
			self.writeAndLog('SMAX ' +str(value),)
		if quant.name in ('SS Offset*'):
			self.writeAndLog('SOFF ' +str(value),)
		if quant.name in ('SS Settle Time'):
			self.writeAndLog('SSTM 2, ' +str(value),)			
		if quant.name in ('SS Settle Cycles'):
			self.writeAndLog('SSCY 2, ' +str(value),)			
		if quant.name in ('SS Integration Time'):
			self.writeAndLog('SITM 2, ' +str(value),)			
		if quant.name in ('SS Integration Cycles'):
			self.writeAndLog('SICY 2, ' +str(value),)	
		if quant.name in ('Source On/Off'):
			if value:
				self.writeAndLog('SRCO 1',)
			else:
				self.writeAndLog('SRCO 0',)
		if quant.name in ('Source Type'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber
			dict = ["0 Sine","1 Chirp", "2 Noise", "3 Arbitrary"]
			value = self.askAndLog('STYP?',)
			return value + " " + dict[int(value)]
		if quant.name in ('FC Frequency Span'):
			self.writeAndLog('FSPN 2, ' +str(value),)
		if quant.name in ('FC Resolution'):
			self.writeAndLog('FLIN 2, ' +value[0],)			
		if quant.name in ('FC Base Frequency'):
			self.writeAndLog('FBAS 2, ' +value[0],)
		if quant.name in ('F Center Frequency'):
			self.writeAndLog('FCTR 2, ' +str(value),)
		if quant.name in ('F Unsettle Measurement'):
			if value:
				self.writeAndLog('UNST 2',)
				time.sleep(10)
		if quant.name in ('FC Compute Average'):
			if value:
				self.writeAndLog('FAVG 2, 1',)
			else:
				self.writeAndLog('FAVG 2, 0',)
		if quant.name in ('FC Type Of Averaging'):
			self.writeAndLog('FAVM 2, ' +value[0],)
		if quant.name in ('FC FFT Average Type'):
			self.writeAndLog('FAVT 2, ' +value[0],)
		if quant.name in ('FC Number Of Averages'):
			self.writeAndLog('FAVN 2, ' +str(value),)
		if quant.name in ('F Time Record Increment'):
			self.writeAndLog('FOVL 2, ' +str(value),)			
		if quant.name in ('FC Overload Reject'):
			if value:
				self.writeAndLog('FREJ 2, 1',)
			else:
				self.writeAndLog('FREJ 2, 0',)
		if quant.name in ('FC Trigger Average Mode'):
			self.writeAndLog('TAVM 2,' +value[0],)
		if quant.name in ('FC Average Preview*'):
			self.writeAndLog('PAVO ' +value[0],)
		if quant.name in ('FC Preview Time*'):
			self.writeAndLog('PAVT ' +str(value),)
		if quant.name in ('Analyzer Configuration*'):
			self.writeAndLog('LINK ' +value[0],)
		if quant.name in ('Input Auto Offset*'):
			if value:
				self.writeAndLog('IAOM 1',)
			else:
				self.writeAndLog('IAOM 0',)
		if quant.name in ('Ch1 Input Mode*'):
			self.writeAndLog('I1MD ' +value[0],)
		if quant.name in ('Ch1 Input Grounding*'):
			self.writeAndLog('I1GD ' +value[0],)
		if quant.name in ('Ch1 Input Coupling*'):
			self.writeAndLog('I1CP ' +value[0],)
		if quant.name in ('Ch1 Anti-Aliasing Filter*'):
			if value:
				self.writeAndLog('I1AF 1',)
			else:
				self.writeAndLog('I1AF 0',)
		if quant.name in ('Ch1 Weighting Filter*'):
			if value:
				self.writeAndLog('I1AW 1',)
			else:
				self.writeAndLog('I1AW 0',)
		if quant.name in ('Ch2 Input Mode*'):
			self.writeAndLog('I2MD ' +value[0],)
		if quant.name in ('Ch2 Input Grounding*'):
			self.writeAndLog('I2GD ' +value[0],)
		if quant.name in ('Ch2 Input Coupling*'):
			self.writeAndLog('I2CP ' +value[0],)
		if quant.name in ('Ch2 Anti-Aliasing Filter*'):
			if value:
				self.writeAndLog('I2AF 1',)
			else:
				self.writeAndLog('I2AF 0',)
		if quant.name in ('Ch2 Weighting Filter*'):
			if value:
				self.writeAndLog('I2AW 1',)
			else:
				self.writeAndLog('I2AW 0',)		
		if quant.name in ('Start New Measurement'):				
			if value:
				self.writeAndLog('STRT',)




			
		time.sleep(0.1)
		return self.performGetValue(quant)

			

		#else:
	#		self.writeAndLog("ERROR ERROR ERROR: " + str(quant.name))
#			return null			
	
		#else:
			#run standard VISA case 
			#value = VISA_Driver.performSetValue(self, quant, value, sweepRate, options)


    def performGetValue(self, quant, options={}):
		"""Perform the Get Value instrument operation"""
        # check type of quantity
		#        if quant.name in ('Zero-span mode',)
		time.sleep(0.1)	
		if quant.name == "Reset Device To Default":
			return False
		if quant.name in ('Measurement Group'):
			dict = ["FFT","Correlation","Octave","Swept Sine","Order","Time Histogram"]
			
			time.sleep(0.1)
			value = self.askAndLog('MGRP ? 0',)
			time.sleep(0.1)
			return value+" "+dict[int(value)]
		if quant.name in ('FFT','Correlation','Octave','Swept Sine','Order', 'Time Histogram'):
			dict = ["FFT 1","FFT 2","Power Spectrum 1","Power Spectrum 2","Time 1","Time 2","Windowed Time 1","Windowed Time 2","Orbit","Coherence","Cross Spectrum","Frequency Response","Capture Buffer 1","Capture Buffer 2","FFT User Function 1","FFT User Function 2","FFT User Function 3","FFT User Function 4","FFT User Function 5","Auto Correlation 1","Auto Correlation 2","Cross Correlation","Time 1","Time 2","Windowed Time 1","Windowed Time 2","Capture Buffer 1","Capture Buffer 2","Correlation Function 1","Correlation Function 2","Correlation Function 3","Correlation Function 4","Correlation Function 5","Octave 1","Octave 2","Capture 1Capture 2","Octave User Function 1","Octave User Function 2","Octave User Function 3","Octave User Function 4","Octave User Function 5","Spectrum 1","Spectrum 2","Normalized Variance 1","Normalized Variance 2","Cross Spectrum","Frequency Response","Swept Sine User Function 1","Swept Sine User Function 2","Swept Sine User Function 3","Swept Sine User Function 4","Swept Sine User Function 5","Linear Spectrum 1","Linear Spectrum 2","Power Spectrum 1","Power Spectrum 2","Time 1","Time 2","Windowed Time 1","Windowed Time 2","RPM Profile","Orbit","Track 1","Track 2","Capture Buffer 1","Capture Buffer 2","Order User Function 1","Order User Function 2","Order User Function 3","Order User Function 4","Order User Function 5","Histogram 1","Histogram 2","PDF 1","PDF 2","CDF 1","CDF 2","Time 1","Time 2","Capture Buffer 1","Capture Buffer 2","Histogram User Function 1","Histogram User Function 2","Histogram User Function 3","Histogram User Function 4","Histogram User Function 5"]
			time.sleep(0.1)
			value = self.askAndLog('MEAS ? 0',)
			time.sleep(0.1)
			return value+" "+dict[int(value)]
		if quant.name in ('View Type'):
			dict = ["Log Magnitude","Linear Magnitude","Magnitude Squared","Real Part","Imaginary Part","Phase","Unwrapped Phase","Nyquist","Nichols"]
			value = self.askAndLog('VIEW ? 0',)
			time.sleep(0.1)
			return value+" "+dict[int(value)]
		if quant.name in ('Unit dB'):
			dict = ["Off","dB","dBm","dBspl"]
			value = self.askAndLog('UNDB ? 0',)
			time.sleep(0.1)
			return value+" "+dict[int(value)]
		if quant.name in ('Unit pk'):
			dict = ["Off","pk","rms","pp"]
			value = self.askAndLog('UNPK ? 0',)	
			time.sleep(0.1)		
			# self.writeAndLog(value)
			return value+" "+dict[int(value)]
		if quant.name in ('Unit psd'):
			dict = ["Off","psd"]
			value = self.askAndLog('PSDU ? 0',)
			time.sleep(0.1)
			self.writeAndLog(value)			
			return value+" "+dict[int(value)]
		if quant.name in ('phase units'):
			dict = ["Degrees","Radians"]
			value = self.askAndLog('UNPH ? 0',)
			time.sleep(0.1)
			return value+" "+dict[int(value)]
		if quant.name in ('SS Start Frequency'):
			return self.askAndLog('SSTR ? 0',)
		if quant.name in ('SS Stop Frequency'):
			return self.askAndLog('SSTP ? 0',)
		if quant.name in ('SS Continuous Scan'):
			dict = [False,True]
			value = self.askAndLog('SRPT ? 0',)
			return dict[int(value)]
		if quant.name in ('SS Sweep Type'):
			return self.askAndLog('SSTY ? 0',)
		if quant.name in ('SS Number Of Points'):
			return self.askAndLog('SNPS ? 0',)
		if quant.name in ('SS Auto Resolution'):
			dict = [False,True]
			value = self.askAndLog('SARS ? 0',)
			return dict[int(value)]
		if quant.name in ('SS Maximum Skips'):
			return self.askAndLog('SSKP ? 0',)
		if quant.name in ('SS Faster Threshold'):
			return self.askAndLog('SFST ? 0',)
		if quant.name in ('SS Lower Threshold'):
			return self.askAndLog('SSLO ? 0',)
		if quant.name in ('SS Auto Level Reference*'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber
			dict = ["Off","Channel 1", "Channel 2"]
			value = self.askAndLog('SSAL?',)
			return value + " " + dict[int(value)]
		if quant.name in ('SS Amplitude*'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber
			return self.askAndLog('SSAM ?',)
		if quant.name in ('SS Ideal Reference*'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber
			return self.askAndLog('SSRF ?',)
		if quant.name == 'SS Source Ramping*':
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber
			return self.askAndLog('SRMP ?',)
		if quant.name == 'SS Source Ramping Rate*':
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber
			return self.askAndLog('SRAT ?',)
		if quant.name in ('SS Reference Upper Limit*'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber
			return self.askAndLog('SSUL ?',)
		if quant.name in ('SS Reference Lower Limit*'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber
			return self.askAndLog('SSLL ?',)
		if quant.name in ('SS Maximum Level*'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber
			return self.askAndLog('SMAX ?',)
		if quant.name in ('SS Offset*'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber
			return self.askAndLog('SOFF ?',)
		if quant.name in ('SS Settle Time'):
			return self.askAndLog('SSTM ? 0',)			
		if quant.name in ('SS Settle Cycles'):
			return self.askAndLog('SSCY ? 0',)			
		if quant.name in ('SS Integration Time'):
			return self.askAndLog('SITM ? 0',)
		if quant.name in ('SS Integration Cycles'):
			return self.askAndLog('SICY ? 0',)		
		if quant.name in ('Source On/Off'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber
			if int(self.askAndLog('SRCO ?',)) == 1:
				return True
			return False
		if quant.name in ('Source Type'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber
			dict = ["0 Sine","1 Chirp", "2 Noise", "3 Arbitrary"]
			value = self.askAndLog('STYP?',)
			return value + " " + dict[int(value)]
		if quant.name in ('FC Frequency Span'):
			return self.askAndLog('FSPN ? 0',)		
		if quant.name in ('FC Resolution'):
			dict = ["100","200","400","800"]
			value = self.askAndLog("FLIN ? 0",)
			return value + " " + dict[int(value)]
		if quant.name in ('FC Base Frequency'):
			dict = ["100 kHz","102.4 kHz"]
			value = self.askAndLog("FBAS ? 0",)
			return value + " " + dict[int(value)]
		if quant.name in ('F Center Frequency'):
			return self.askAndLog('FCTR ? 0',)		
		if quant.name in ('F Unsettle Measurement'):
			return False #
		if quant.name in ('FC Compute Average'):
			if int(self.askAndLog("FAVG ? 0",))==1:
				return True
			return False
		if quant.name in ('FC Type Of Averaging'):			
			dict = ["None","Vector","RMS","Peak Hold"]
			value = self.askAndLog("FAVM ? 0",)
			return value + " " + dict[int(value)]
		if quant.name in ('FC FFT Average Type'):			
			dict = ["Linear/Fixed Length","Exponential/Continuous"]
			value = self.askAndLog('FAVT ? 0',)
			return value + " " + dict[int(value)]
		if quant.name in ('FC Number Of Averages'):
			return self.askAndLog('FAVN ? 0',)
		if quant.name in ('F Time Record Increment'):
			return self.askAndLog('FOVL ? 0',)			
		if quant.name in ('FC Overload Reject'):
			return self.askAndLog('FREJ ? 0',)
		if quant.name in ('FC Trigger Average Mode'):
			dict = ["Time Records","Averages"]
			value = self.askAndLog("TAVM ? 0",)
			return value + " " + dict[int(value)]
		if quant.name in ('FC Average Preview*'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber
			dict = ["Off","Manual","Timed"]
			value = self.askAndLog("PAVO ?",)
			return value + " " + dict[int(value)]		
		if quant.name in ('FC Preview Time*'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber
			return self.askAndLog('PAVT ? 0',)			
		if quant.name in ('Analyzer Configuration*'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber
			dict = ["Independent Channels","Dual Channels"]
			value= self.askAndLog('LINK ?',)
			return value + " " + dict[int(value)]		
		if quant.name in ('Input Auto Offset*'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber		
			if int(self.askAndLog('IAOM ?',)) == 1:
				return True
			return False
		if quant.name in ('Ch1 Input Mode*'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber		
			dict=["A (single-ended)","A-B (differential)"]
			value = self.askAndLog('I1MD ?' ,)
			return value + " " + dict[int(value)]		
		if quant.name in ('Ch1 Input Grounding*'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber		
			dict=["Float","Ground"]
			value=self.askAndLog('I1GD ?',)
			return value + " " + dict[int(value)]		
		if quant.name in ('Ch1 Input Coupling*'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber
			dict=["DC","AC","ICP"]
			value = self.askAndLog('I1CP ?',)
			return value + " " + dict[int(value)]		
		if quant.name in ('Ch1 Anti-Aliasing Filter*'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber		
			if int(self.askAndLog('I1AF ?',)) == 1:
				return True
			return False
		if quant.name in ('Ch1 A-Weighting Filter*'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber		
			if int(self.askAndLog('I1AW ?',)) == 1:
				return True
			return False
		if quant.name in ('Ch2 Input Mode*'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber		
			dict=["A (single-ended)","A-B (differential)"]
			value = self.askAndLog('I2MD ?' ,)
			return value + " " + dict[int(value)]		
		if quant.name in ('Ch2 Input Grounding*'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber		
			dict=["Float","Ground"]
			value=self.askAndLog('I2GD ?',)
			return value + " " + dict[int(value)]		
		if quant.name in ('Ch2 Input Coupling*'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber		
			dict=["DC","AC","ICP"]
			value = self.askAndLog('I2CP ?',)
			return value + " " + dict[int(value)]		
		if quant.name in ('Ch2 Anti-Aliasing Filter*'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber		
			if int(self.askAndLog('I2AF ?',)) == 1:
				return True
			return False
		if quant.name in ('Ch2 A-Weighting Filter*'):
			return self.getValue(quant.name) # return internal value, since SSAL? not working in Labber		
			if int(self.askAndLog('I2AW ?',)) == 1:
				return True
			return False			
		if quant.name in ('Start New Measurement'):
			return True
			
		if quant.name in ('Signal'): 
				#self.writeAndLog('SVTR 0, 1') # save trace from display 0 to trace 1
				#self.write('TLOD ? 1') # get trace 1
				#self.write('TGET ? 1') # get trace 1, multiples of 4-byte binary, start: bin 0, followed by floating point numbers
				#self.write('DSPY ? 0') # read data as ASCII, separated by commas
				#	if sData[i] == -3.4028235e+38:
			#		nirvana = sData.pop(i)
			#		self.writeAndLog(str(sData[i]))
			#self.writeAndLog(str(sData))
			sData = self.askAndLog("DSPY ? 0",)
			sData = sData.split(",")
			for i in range(len(sData)):
				sData[i] = float(sData[i])
			xData = sData
			if self.getValue('Measurement Group') == '3 Swept Sine':
				del sData[-1]
				while -3.4028235e+38 in xData:
					xData.remove(-3.4028235e+38)
				while 0 in sData:
					xData.remove(0)
				xData = np.asarray(xData)
				startFreq = self.getValue('SS Start Frequency')
				stopFreq = self.getValue('SS Stop Frequency')
				nPts = self.getValue('SS Number Of Points')
			if self.getValue('Measurement Group') == '0 FFT':
				while -3.4028235e+38 in xData:
					xData.remove(-3.4028235e+38)
				while 0 in sData:
					xData.remove(0)
				xData = np.asarray(xData)
				startFreq = self.getValue('F Center Frequency') - self.getValue('FC Frequency Span')/2.0
				stopFreq = self.getValue('F Center Frequency') + self.getValue('FC Frequency Span')/2.0
				nPts = len(sData)
			if self.getValue('Measurement Group') == '1 Correlation':
				# while -3.4028235e+38 in xData:
					# xData.remove(-3.4028235e+38)
				# while 0 in sData:
					# xData.remove(0)
				xData = np.asarray(xData)
				startFreq = 0
				stopFreq = self.getValue('FC Frequency Span')
				nPts = len(sData)

			value = InstrumentQuantity.getTraceDict(xData, t0=startFreq, dt=(stopFreq-startFreq)/(nPts-1))
			return value
		else:
			self.writeAndLog("ERROR ERROR ERROR: " + str(quant.name))
			return None
            # for all other cases, call VISA driver
			#value = VISA_Driver.performGetValue(self, quant, options)
		return value
        

if __name__ == '__main__':
    pass
