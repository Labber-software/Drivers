#!/usr/bin/env python

import InstrumentDriver
from InstrumentConfig import InstrumentQuantity
import afDigitizerWrapper
import numpy as np
import time
import h5py
 
__version__ = "1.0"

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements a digitizer in the PXI rack"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # check communication
        try:
            # open connection
            self.digitizer = afDigitizerWrapper.afDigitizer()
            self.digitizer.create_object()
            # get address strings
            sVisaDigitizer = self.dComCfg['address']
            sVisaLO = self.getValue('Local oscillator VISA')
            # keep track of number of samples, averages, etc
            self.nSamples = int(self.getValue('Number of samples'))
            self.nTriggers = int(self.getValue('Number of triggers'))
            self.nAverages_per_trigger=int(self.getValue('Averages per trigger'))
            # Variables to store data            
            self.cAvgSignal = None 
            self.cTrace = None
            self.vPTrace = None


            self.dPower = None

            self.nAbove = 0
            
            self.bCutTrace = self.getValue('Cut out part of the trace')
            self.nStartSample = int(self.getValue('Start Sample'))
            self.nStopSample = int(self.getValue('Stop Sample'))
            
            self.dFreq = self.getValue('RF Frequency')
            self.nBins = 0

            self.overloads = 0
            # boot instruments
            self.digitizer.boot_instrument(sVisaLO, sVisaDigitizer)
            # set modulation mode to generic
            self.digitizer.modulation_mode_set(5)
            
        except afDigitizerWrapper.Error as e:
            # re-cast afdigitizer errors as a generic communication error
            msg = str(e)
            raise InstrumentDriver.CommunicationError(msg)


    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # check if digitizer object exists
        if not hasattr(self, 'digitizer'):
            # do nothing, object doesn't exist (probably was never opened)
            return
        try:
            # set max input level to +30dB
            self.digitizer.rf_rf_input_level_set(30)
            # do not check for error if close was called with an error
            self.digitizer.close_instrument(bCheckError=not bError)
        except afDigitizerWrapper.Error as e:
            # do not raise errors if error already exists
            if not bError:
                # re-cast errors as a generic communication error
                msg = str(e)
                raise InstrumentDriver.CommunicationError(msg)
        finally:
            try:
                # destroy dll object
                self.digitizer.destroy_object()
                del self.digitizer
            except:
                # never return error here
                pass

        
    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        try:
            # proceed depending on command
            if quant.name == 'RF Frequency':
                self.dFreq = value
                self.digitizer.rf_centre_frequency_set(value)            
                # Reset the stored traces
                self.cAvgSignal = None 
                self.cTrace = None
                self.vPTrace = None
                self.dPower = None

            elif quant.name == 'Max input level':
                self.digitizer.rf_rf_input_level_set(value)
            elif quant.name == 'Sampling rate':
                self.digitizer.modulation_generic_sampling_frequency_set(value)
            elif quant.name == 'Number of samples':
                self.nSamples = int(value)
            elif quant.name == 'Cut out part of the trace':
                self.bCutTrace = value    
            elif quant.name == 'Start Sample':
                self.nStartSample = int(value)
            elif quant.name == 'Stop Sample':
                self.nStopSample = int(value)
            elif quant.name == 'Remove DC offset':
                self.digitizer.rf_remove_dc_offset_set(bool(value))
            elif quant.name == 'Trigger Source':
                # combo, get index
                if isinstance(value, (str, unicode)):
                    valueIndex = quant.combo_defs.index(value)
                else:
                    valueIndex = long(value)
                self.digitizer.trigger_source_set(valueIndex)             
            elif quant.name == 'Trigger type':
                # Dont do for SW
                TriggerSourceValue = self.digitizer.trigger_source_get()
                if TriggerSourceValue is not 32:                
                    # combo, get index
                    if isinstance(value, (str, unicode)):
                        valueIndex = quant.combo_defs.index(value)
                    else:
                        valueIndex = int(value)
                    self.digitizer.trigger_type_set(valueIndex)
            elif quant.name == 'Trigger polarity':
                 # Dont do for SW
                TriggerSourceValue = self.digitizer.trigger_source_get()
                if TriggerSourceValue is not 32: 
                # combo, get index
                    if isinstance(value, (str, unicode)):
                        valueIndex = quant.combo_defs.index(value)
                    else:
                        valueIndex = int(value)
                    self.digitizer.trigger_polarity_set(valueIndex)
            elif quant.name == 'Number of triggers':
                self.nTriggers = int(value)
            elif quant.name == 'Averages per trigger':
                self.nAverages_per_trigger = int(value)
            elif quant.name == 'LO Reference Mode':
                # combo, get index
                if isinstance(value, (str, unicode)):
                    valueIndex = quant.combo_defs.index(value)
                else:
                    valueIndex = int(value)
                self.digitizer.lo_reference_set(valueIndex)
            elif quant.name == 'LO Above or Below':
                # combo, get index
                if isinstance(value, (str, unicode)):
                    valueIndex = quant.combo_defs.index(value)
                else:
                    valueIndex = int(value)
                self.digitizer.rf_userLOPosition_set(valueIndex)
            return value
        except afDigitizerWrapper.Error as e:
            # re-cast errors as a generic communication error
            msg = str(e)
            raise InstrumentDriver.CommunicationError(msg)


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        try:
            # proceed depending on command
            if quant.name == 'RF Frequency':
                value = self.digitizer.rf_centre_frequency_get()
            elif quant.name == 'Max input level':
                value = self.digitizer.rf_rf_input_level_get()
            elif quant.name == 'Sampling rate':
                value = self.digitizer.modulation_generic_sampling_frequency_get()
            elif quant.name == 'Number of samples':
                value = self.nSamples
            elif quant.name == 'Cut out part of the trace':
                value = self.bCutTrace
            elif quant.name == 'LO Reference Mode':
                value = quant.getValueString(self.digitizer.lo_reference_get())
            elif quant.name == 'Start Sample':
                value = self.nStartSample
            elif quant.name == 'Stop Sample':
                value = self.nStopSample
            elif quant.name == 'Remove DC offset':
                value = self.digitizer.rf_remove_dc_offset_get()
            elif quant.name == 'Trigger Source':
                value = self.digitizer.trigger_source_get()
                value = quant.getValueString(value)
            elif quant.name == 'Trigger type':
                value = self.digitizer.trigger_type_get()
                value = quant.getValueString(value)
            elif quant.name == 'LO Above or Below':
                value = self.digitizer.rf_userLOPosition_get()
                value = quant.getValueString(value)
            elif quant.name == 'Trigger polarity':
                value = self.digitizer.trigger_polarity_get()
                value = quant.getValueString(value)
            elif quant.name == 'Number of triggers':
                value = self.nTriggers
            elif quant.name == 'Averages per trigger':
                value = self.nAverages_per_trigger
            elif quant.name == 'Trace':
                value = self.getTraceDict(self.getIQTrace())   
            elif quant.name == 'Power trace':
                value = self.getTraceDict(self.getPTrace())
            elif quant.name == 'AvgTrace':
                value = self.getTraceAvg()  
            elif quant.name == 'AvgPower':
                value = self.getAvgPower()
            elif quant.name == 'Level correction':
                value = self.digitizer.rf_level_correction_get()

            return value
        except afDigitizerWrapper.Error as e:
            # re-cast errors as a generic communication error
            msg = str(e)
            raise InstrumentDriver.CommunicationError(msg)
            
    # Return the signal along with its time vector
    def getTraceDict(self, vSignal):
        dSampFreq = self.getValue('Sampling rate')
        return InstrumentQuantity.getTraceDict(vSignal, t0=0, dt=1/dSampFreq)
    
    # Check if the ADC overloaded 3 times in a row, and if it did put the max input level to +30dBm and raise an error
    def checkADCOverload(self):
        if self.digitizer.check_ADCOverload():
            self.overloads += 1
        else:
            self.overloads = 0
            
        if self.overloads == 3:
            self.digitizer.rf_rf_input_level_set(30)
            raise InstrumentDriver.CommunicationError('ADC overloaded hence the measurement is stopped and the max input level on the digitizer is put to +30 dBm')
            
            
    def getIQTrace(self):
        """Return I and Q signal in time as a complex vector, resample the signal if needed"""
        # check if old value exists
        if self.cTrace is None:
            # get new trace
            self.sampleAndAverage()
        # return and clear old value for selected signal
        vTrace = self.cTrace
        self.cTrace = None
        return vTrace  
        
    def getPTrace(self):
        """Return the power in time as a vector, resample the signal if needed"""
        # check if old value exists
        if self.vPTrace is None:
            # get new trace
            self.sampleAndAverage()
        # return and clear old value for selected signal
        vTrace = self.vPTrace
        self.vPTrace = None
        return vTrace
    
    def getAvgPower(self):
        """Return the averaged power in Watts, resample the signal if necessary"""
        if self.dPower is None:
            self.sampleAndAverage()
        vPower = self.dPower
        self.dPower = None
        return vPower                     

    def getTraceAvg(self):
        """Return the averaged signal as a complex number I+j*Q, resample the signal if necessary"""
        # check if old value exists
        if self.cAvgSignal is None:
            self.sampleAndAverage()
        # return and clear old value for selected signal
        value = self.cAvgSignal
        self.cAvgSignal = None
        return value  
        

    def sampleAndAverage(self):
        """Sample the signal, calc I+j*Q theta and store it in the driver object"""
        
        # Check which trigger source is being used
        TriggerSourceValue = self.digitizer.trigger_source_get()
        
        self.checkADCOverload()
        
        # Convert the number of samples and triggers to integers
        nAvgPerTrigger = self.nAverages_per_trigger
        nTotalSamples = self.nSamples*nAvgPerTrigger
        dLevelCorrection = self.digitizer.rf_level_correction_get()
        # If the stop sample is set to high, set it to nSamples
        if self.bCutTrace:
            if self.nStopSample > self.nSamples:
                self.nStopSample = self.nSamples
        else: #If we don't want to cut the trace, set start value to 1 and stop value to the last
            self.nStartSample = 1
            self.nStopSample = self.nSamples
        
        # If the Trigger source is not in 32 = SW trigger, we want to arm the trigger
        if TriggerSourceValue is not 32:        
            # Arm the trigger with 2*inSamples        
            self.digitizer.trigger_arm_set(nTotalSamples*2)
            #self.checkADCOverload()
        
        # Define two vectors that will be used to collect the raw data
        vI = np.zeros(self.nStopSample-self.nStartSample+1)
        vQ = np.zeros(self.nStopSample-self.nStartSample+1)         
        vI2 = np.zeros(self.nStopSample-self.nStartSample+1)
        vQ2 = np.zeros(self.nStopSample-self.nStartSample+1) 

        # For each trigger, we collect the data
        for i in range(0, self.nTriggers):
            # number 32 corresponds to SW_TRIG, the only trigger mode without external signal             
            if TriggerSourceValue is not 32:
                while self.digitizer.data_capture_complete_get()==False:
                    #Sleep some time in between checks
                    self.wait(0.001)
                # Get the I and Q data
                (lI, lQ) = self.digitizer.capture_iq_capt_mem(nTotalSamples)
                
                #Re-arm the trigger to prepare the digitizer for the next iteration                                  
                if i < (self.nTriggers-1):
                    self.digitizer.trigger_arm_set(nTotalSamples*2)
            else:
                # Get the I and Q data for SW-trig
                (lI, lQ) = self.digitizer.capture_iq_capt_mem(nTotalSamples)
                
           
            # We add the aquired data and fold it
            reshapedI = np.array(lI).reshape(nAvgPerTrigger, self.nSamples)[:,range(self.nStartSample-1, self.nStopSample)]
            reshapedQ = np.array(lQ).reshape(nAvgPerTrigger, self.nSamples)[:,range(self.nStartSample-1, self.nStopSample)]
            vI = vI + np.mean(reshapedI, axis=0)
            vQ = vQ + np.mean(reshapedQ, axis=0)
            vI2 = vI2 + np.mean(reshapedI**2, axis=0)        
            vQ2 = vQ2 + np.mean(reshapedQ**2, axis=0)   
        
        # Average the sum of vI and vQ using the number of triggers and do level correction
        vI = vI/self.nTriggers*np.power(10,dLevelCorrection/20)
        vQ = vQ/self.nTriggers*np.power(10,dLevelCorrection/20)
        vI2 = vI2/self.nTriggers*np.power(10,dLevelCorrection/10)/1000
        vQ2 = vQ2/self.nTriggers*np.power(10,dLevelCorrection/10)/1000
        
        # Store the data
        self.cTrace = vI+1j*vQ
        self.vPTrace = (vI2+vQ2)  
        self.cAvgSignal = np.average(vI)+1j*np.average(vQ)
        self.dPower = np.average(vI2)+np.average(vQ2)
        


if __name__ == '__main__':
	pass

