#!/usr/bin/env python

import mcl_switch_wrapper as MCL
import InstrumentDriver
from InstrumentConfig import InstrumentQuantity

__version__ = "0.0.1"

class Error(Exception):
    pass

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements the MiniCircuits USB Switch Matrix driver"""
    
    switchLabels = {'A':0,'B':1,'C':2,'D':3,'E':4,'F':5,'G':6,'H':7}    
    

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        try:
            # open connection
            self.switch = MCL.MiniCircuitsSwitch()
            self.switch.Connect(self.comCfg.address)
        except Exception as e:
            # re-cast afdigitizer errors as a generic communication error
            msg = str(e)
            raise InstrumentDriver.CommunicationError(msg)

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # check if digitizer object exists
        try:
            if self.switch is None:
                # do nothing, object doesn't exist (probably was never opened)
                return
        except:
            # never return error here, do nothing, object doesn't exist
            return
        try:
            # close and remove object
            self.switch.Disconnect()
            del self.switch
        except:
            # never return error here
            pass


    def performSetValue(self, quant, value, sweepRate = 0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # start with setting current quant value
        quant.setValue(value)
        # get values from relevant quants
        if quant.name == 'SP9T Set':
            self.switch.Set_SP9T(value)
            self.updateStateAndCounters()
        elif quant.name == 'DP5T Set':
            self.switch.Set_DP5T(value)
            self.updateStateAndCounters()
        elif quant.name == 'Custom State Set':
            self.switch.Set_SwitchesPort(int(value,2))
            self.updateStateAndCounters()
        else:
             # do nothing for these quantities, the value will be stored in local quant
             pass
        # finish set value with get value, to make sure we catch any coercing
        return self.performGetValue(quant)


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        if quant.name == 'SP9T Set':
            value = str(self.switch.Get_SP9T())
        elif quant.name == 'DP5T Set':
            value = str(self.switch.Get_DP5T())
        elif quant.name == 'Custom State Set':
            value = "{0:08b}".format(self.switch.GetSwitchesStatus())
        elif quant.name in self.switchLabels:
            countarray = self.switch.GetAllSwitchCounters()
            value = countarray[self.switchLabels.get(quant.name)]
        elif quant.name == 'Current Switch State (HGFEDCBA->)':
            state = "{0:08b}".format(self.switch.GetSwitchesStatus())
            value = state
        else:
            value = quant.getValue()
        return value


    def updateStateAndCounters(self):    
        for name in ['Current Switch State (HGFEDCBA->)'] + self.switchLabels.keys():        
            self.readValueFromOther(name)


if __name__ == '__main__':
    pass
