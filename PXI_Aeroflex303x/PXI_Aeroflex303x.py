#!/usr/bin/env python

import InstrumentDriver
from InstrumentConfig import InstrumentQuantity
import afDigitizerWrapper

__version__ = "0.0.1"


class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements a signal generator in the PXI rack"""

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
            # keep track of number of samples and old I,Q,R and theta values
            self.nSamples = self.getValue('Number of samples')
            self.lOldValueIQ = [None] * 4 
            self.lTrace= [None] * 4 
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
                self.digitizer.rf_centre_frequency_set(value)
            elif quant.name == 'Max input level':
                self.digitizer.rf_rf_input_level_set(value)
            elif quant.name == 'Sampling rate':
                self.digitizer.modulation_generic_sampling_frequency_set(value)
            elif quant.name == 'Number of samples':
                self.nSamples = value
            elif quant.name == 'Remove DC offset':
                self.digitizer.rf_remove_dc_offset_set(bool(value))
            elif quant.name == 'Trigger':
                # combo, get index
                if isinstance(value, (str, unicode)):
                    valueIndex = quant.combo_defs.index(value)
                else:
                    valueIndex = int(value)
                self.digitizer.trigger_source_set(valueIndex)
#                self.digitizer.trigger_source_set(quant.getValueIndex(value))
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
            elif quant.name == 'Remove DC offset':
                value = self.digitizer.rf_remove_dc_offset_get()
            elif quant.name == 'Trigger':
                value = self.digitizer.trigger_source_get()
                value = quant.getValueString(value)
            elif quant.name == 'Trace - I':
                value = self.getIQTraces(signal=0)
            elif quant.name == 'Trace - Q':
                value = self.getIQTraces(signal=1)
            elif quant.name == 'Amplitude - I':
                value = self.getIQAmplitudes(signal=0)
            elif quant.name == 'Amplitude - Q':
                value = self.getIQAmplitudes(signal=1)
            elif quant.name == 'Amplitude - R':
                value = self.getIQAmplitudes(signal=2)
            elif quant.name == 'Signal - theta':
                value = self.getIQAmplitudes(signal=3)
            # return value
            return value
        except afDigitizerWrapper.Error as e:
            # re-cast errors as a generic communication error
            msg = str(e)
            raise InstrumentDriver.CommunicationError(msg)
            

    def getIQTraces(self, signal):
        """Return I or Q signal, resample the signal if needed"""
        # check if old value exists
        if self.lTrace[signal] is None:
            # get new trace
            self.sampleAndAverage()
        # return and clear old value for selected signal
        vTrace = self.lTrace[signal]
        self.lTrace[signal] = None
        return vTrace                           


    def getIQAmplitudes(self, signal):
        """Return I, Q, R and theta, resample the signal if necessary"""
        # check if old value exists
        if self.lOldValueIQ[signal] is None:
            # get new trace
            self.sampleAndAverage()
        # return and clear old value for selected signal
        value = self.lOldValueIQ[signal]
        self.lOldValueIQ[signal] = None
        return value                           


    def sampleAndAverage(self):
        """Sample the signal, calc I, Q, R, theta and store it in the driver object"""
        # get new trace
        (lI, lQ) = self.digitizer.capture_iq_capt_mem(self.nSamples)
        # calc values
        import numpy as np
        vI = np.array(lI)
        vQ = np.array(lQ)
        # keep data in object
        self.lTrace = [vI, vQ]
        self.lOldValueIQ = [np.average(vI), np.average(vQ),
                            np.sqrt(np.average(vI**2) + np.average(vQ**2)),
                            np.angle(np.average(vI)+1j*np.average(vQ), deg=True)]


           

if __name__ == '__main__':
	pass

