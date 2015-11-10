#!/usr/bin/env python

import Vaunix_Attenuator_Wrapper as vx
import InstrumentDriver
from InstrumentConfig import InstrumentQuantity

__version__ = "0.0.1"

class Error(Exception):
    pass

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements the MiniCircuits USB Switch Matrix driver"""
    
        
    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        try:
            # open connection
            self.atten = vx.VaunixAttenuator()
            self.atten.setTestMode(0) # make sure test mode is off
            if self.atten.getNumDevices() == 0:
                raise InstrumentDriver.CommunicationError('No devices connected')         
            devList = self.atten.getDevInfo()
            found = False
            for device in devList:
                if device == 0: # skip bogus devices 
                    break
                if str(self.atten.getSerialNumber(device)) == self.comCfg.address:
                    found = True                    
                else:
                    continue
                if (self.atten.getDeviceStatus(device)) & (vx.DEV_OPENED):
                    raise InstrumentDriver.CommunicationError('Target device already opened')
                    break
                self.atten.initDevice(device)
            if not found:
                raise InstrumentDriver.CommunicationError('Target device not found')
        except Exception as e:
            # re-cast afdigitizer errors as a generic communication error
            msg = str(e)
            raise InstrumentDriver.CommunicationError(msg)

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # check if digitizer object exists
        try:
            if self.atten is None:
                # do nothing, object doesn't exist (probably was never opened)
                return
        except:
            # never return error here, do nothing, object doesn't exist
            return
        try:
            # close and remove object
            self.atten.closeDevice(None)
            del self.atten
        except:
            # never return error here
            pass


    def performSetValue(self, quant, value, sweepRate = 0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # start with setting current quant value
        quant.setValue(value)
        # get values from relevant quants
        if quant.name == 'Attenuation':
            self.atten.setAttenuation(None,value)
        elif quant.name == 'Start attenuation':
            self.atten.setRampStart(None,value)
        elif quant.name == 'End attenuation':
            self.atten.setRampEnd(None,value)
        elif quant.name == 'Step size':
            self.atten.setAttenuationStep(None,value)
        elif quant.name == 'Step dwell':
            self.atten.setDwellTime(None,value)
        elif quant.name == 'Repeat ramp':
            self.atten.setRampMode(None,value)
        elif quant.name == 'Idle time':
            self.atten.setIdleTime(None,value)
        elif quant.name == 'Bidirectional sweep':
            self.atten.setRampBidirectional(None,value)
        elif quant.name == 'Step size phase 2':
            self.atten.setAttenuationStepTwo(None,value)
        elif quant.name == 'Step dwell phase 2':
            self.atten.setDwellTimeTwo(None,value)
        elif quant.name == 'Hold time':
            self.atten.setHoldTime(None,value)
        else:
             # do nothing for these quantities, the value will be stored in local quant
             pass
        # finish set value with get value, to make sure we catch any coercing
        return self.performGetValue(quant)


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        if quant.name == 'Attenuation':
            value = self.atten.getAttenuation(None)
        elif quant.name == 'Start attenuation':
            value = self.atten.getRampStart(None)
        elif quant.name == 'End attenuation':
            value = self.atten.getRampEnd(None)
        elif quant.name == 'Step size':
            value = self.atten.getAttenuationStep(None)
        elif quant.name == 'Step dwell':
            value = self.atten.getDwellTime(None)
        elif quant.name == 'Ramp mode':
            value = (self.atten.getDeviceStatus(None)) & (vx.SWP_REPEAT)
        elif quant.name == 'Idle time':
            value = self.atten.getIdleTime(None)
        elif quant.name == 'Bidirectional sweep':
            value = (self.atten.getDeviceStatus(None)) & (vx.SWP_BIDIRECTIONAL)
        elif quant.name == 'Step size phase 2':
            value = self.atten.getAttenuationStepTwo(None)
        elif quant.name == 'Step dwell phase 2':
            value = self.atten.getDwellTimeTwo(None)
        elif quant.name == 'Hold time':
            value = self.atten.getHoldTime(None)
        elif quant.name == 'Minimum attenuation':
            value = 0.25*self.atten.MinAtten
        elif quant.name == 'Maximum attenuation':
            value = 0.25*self.atten.MaxAtten
        elif quant.name == 'Minimum attenuation step':
            value = 0.25*self.atten.MinAttenStep
        elif quant.name == 'Model':
            value = self.atten.getModelName(None)
        elif quant.name == 'Serial number':
            value = self.atten.getSerialNumber(None)
        elif quant.name == 'Supports bidirectional ramps?':
            value = (self.atten.Features) & (vx.HAS_BIDIR_RAMPS)
        elif quant.name == 'Supports profile ramps?':
            value = (self.atten.Features) & (vx.HAS_PROFILES)
        else:
            value = quant.getValue()
        return value



if __name__ == '__main__':
    pass
