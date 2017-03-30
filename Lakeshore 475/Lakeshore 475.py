#!/usr/bin/env python

import InstrumentDriver
from VISA_Driver import VISA_Driver
import visa
from InstrumentConfig import InstrumentQuantity

__version__ = "0.0.1"

class Error(Exception):
    pass

class Driver(VISA_Driver):
    """ This class implements the Lakeshore 475 driver"""
  
    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        VISA_Driver.performOpen(self, options=options)
        

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        value = VISA_Driver.performGetValue(self, quant, options)
        return value
        
    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the set value operation"""
        # check type of quantity
        if quant.name[:7] in ('B-Field'):
            #We do not want the driver to return before the field has reched its target
            #within the precision selected by the user
            precision = self.instrCfg.getQuantity('StopThreshold').getValue()
            self.writeAndLog(quant.set_cmd.replace('<*>', str(value)))
            diff = abs(float(self.askAndLog("RDGFIELD?")) - value)
            while diff > precision:
                self.wait(0.1)
                diff = abs(float(self.askAndLog("RDGFIELD?")) - value)
            value = float(self.askAndLog("RDGFIELD?"))
        return value
        
if __name__ == '__main__':
    pass
