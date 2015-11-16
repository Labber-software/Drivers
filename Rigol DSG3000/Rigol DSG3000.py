#!/usr/bin/env python

import InstrumentDriver
from VISA_Driver import VISA_Driver
import visa
from InstrumentConfig import InstrumentQuantity

__version__ = "0.0.1"

class Error(Exception):
    pass

class Driver(VISA_Driver):
    """ This class implements the Rigol DSG3000 driver"""
  
    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # calling the generic VISA open to make sure we have a connection
        VISA_Driver.performOpen(self, options=options)
        

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        if (quant.datatype == quant.DOUBLE):
            value = self.askAndLog(quant.set_cmd+"?")
            value = value.replace(" ", "")
            for i,c in enumerate(value):
                if not c in "0123456789.-eE":
                    break
            number=float(value[:i])
            unit=value[i:]
            
            factor = 1
            cfactor = unit[:1]
            if (cfactor == "G"):
                factor = 1e9
            elif (cfactor == "M"):
                factor = 1e6
            elif (cfactor == "k"):
                factor = 1e3
            elif (cfactor == "m"):
                factor = 1e-3
            elif (cfactor == "u"):
                factor = 1e-6
            elif (cfactor == "n"):
                factor = 1e-9
            elif (cfactor == "p"):
                factor = 1e-12
            v = float(number)*factor
            return v
        else:
            value = VISA_Driver.performGetValue(self, quant, options)
            return value
        
    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the set value operation"""
        # check type of quantity
        value = VISA_Driver.performSetValue(self, quant, value, sweepRate, options)
        return value
        
if __name__ == '__main__':
    pass
