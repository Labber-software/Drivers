#!/usr/bin/env python

import InstrumentDriver
import LabBrick_LMS_Wrapper


class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements a Lab Brick generator"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        self.SG = None
        # open connection
        self.SG = LabBrick_LMS_Wrapper.LabBrick_Synthesizer(bTestMode=False)
        self.SG.initDevice(self.comCfg.address.strip())


    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # do not check for error if close was called with an error
        try:
            self.SG.closeDevice()
        except:
            # never return error here
            pass

        
    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # start with setting current quant value
        quant.setValue(value)
        # proceed depending on command
        if quant.name == 'Frequency':
            # make sure value is in range
            value = self.SG.setFrequency(value)
        elif quant.name == 'Power':
            self.SG.setPowerLevel(value)
        elif quant.name == 'Output':
            self.SG.setRFOn(bool(value))
        elif quant.name == 'Use internal reference':
            self.SG.setUseInternalRef(bool(value))
        elif quant.name == 'External pulse modulation':
            self.SG.setExternalPulseMod(bool(value))
        elif quant.name in ('Internal pulse modulation', 'Pulse time', 'Pulse period'):
            # special case for internal pulse modulation, set all config at once
            bOn = self.getValue('Internal pulse modulation')
            pulseTime = self.getValue('Pulse time')
            pulsePeriod = self.getValue('Pulse period')
            self.SG.setInternalPulseMod(pulseTime, pulsePeriod, bOn)
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # proceed depending on command
        if quant.name == 'Frequency':
            value = self.SG.getFrequency()
        elif quant.name == 'Power':
            value = self.SG.getPowerLevel()
        elif quant.name == 'Output':
            value = self.SG.getRFOn()
        elif quant.name == 'Use internal reference':
            value = self.SG.getUseInternalRef()
        elif quant.name == 'Internal pulse modulation':
            value = self.SG.getInternalPulseMod()
        elif quant.name == 'Pulse time':
            value = self.SG.getPulseOnTime()
        elif quant.name == 'Pulse period':
            value = self.SG.getPulsePeriod()
        elif quant.name == 'External pulse modulation':
            value = self.SG.getExternalPulseMod()
        # return value
        return value


           

if __name__ == '__main__':
	pass

