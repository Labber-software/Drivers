#!/usr/bin/env python

import InstrumentDriver
import numpy as np
import ctypes


class Driver(InstrumentDriver.InstrumentWorker):
	# This class implements the SignalHound Spectrum Analyzer driver

	def performOpen(self,options={}):
		#import the dll file sa_api.dll from the Spike software from SignalHound
		self.sighound = ctypes.CDLL("C:\\Program Files (x86)\\Signal Hound\\Spike\\sa_api.dll");
		self.handle = ctypes.c_int();
		self.sweepLen = ctypes.c_int();
		self.startFreq = ctypes.c_double();
		self.binSize = ctypes.c_double();
		self.min = np.empty(1,dtype="float32");
		self.max = np.empty(1,dtype="float32");
		self.initiateFlag = True;
		if(self.sighound.saOpenDevice(ctypes.byref(self.handle))!=0):
			print("Unable to open device SignalHound")
		else:
			self.sighound.saConfigAcquisition(self.handle,ctypes.c_int(1),ctypes.c_int(0))
			

	def performClose(self, bError=False, options={}):
		self.sighound.saCloseDevice(self.handle);
		
	def performSetValue(self, quant, value, sweepRate=0.0, options={}):
		#Perform the Set Value instrument operation. This function should return the actual value set by the instrument
		quant.setValue(value)
		if quant.name=="Center frequency" or quant.name=="Span":
			self.sighound.saConfigCenterSpan(self.handle,ctypes.c_double(self.getValue("Center frequency")),ctypes.c_double(self.getValue("Span")));
		if quant.name=="Bandwidth":
			self.sighound.saConfigSweepCoupling(self.handle,ctypes.c_double(self.getValue("Bandwidth")),ctypes.c_double(self.getValue("Bandwidth")),ctypes.c_int(1));
		if quant.name=="Input Power Level":
			self.sighound.saConfigLevel(self.handle,ctypes.c_double(self.getValue("Input Power Level")));
		#if self.isLastCall(options):
		self.initiateFlag = True;
		return value;


	def performGetValue(self, quant, options={}):
		#Perform the Get Value instrument operation
		if quant.name=="Center frequency":
			return quant.getValue();
		if quant.name=="Span":
			return quant.getValue();
		if quant.name=="Bandwidth":
			return quant.getValue();
		
		if quant.name=="Signal" or quant.name=="Signal - Zero span":
			if(self.isFirstCall(options)) :
				if self.initiateFlag:
					self.sighound.saInitiate(self.handle,ctypes.c_int(0),ctypes.c_int(0));
					self.sighound.saQuerySweepInfo(self.handle,ctypes.byref(self.sweepLen),ctypes.byref(self.startFreq),ctypes.byref(self.binSize));
					self.min = np.empty(self.sweepLen.value,dtype="float32");
					self.max = np.empty(self.sweepLen.value,dtype="float32");
					self.initiateFlag = False;
				self.sighound.saGetSweep_32f(self.handle,self.min.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),self.max.ctypes.data_as(ctypes.POINTER(ctypes.c_double)));
			if quant.name=="Signal":
				return quant.getTraceDict(self.min, x0=self.startFreq.value, dx=self.binSize.value);
			else:
				return 10.0*np.log10(np.average(10.0**(self.min/10.0)));
				

if __name__ == '__main__':
	pass
