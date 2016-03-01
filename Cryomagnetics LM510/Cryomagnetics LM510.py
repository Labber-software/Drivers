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
        # calling the generic VISA open to make sure we have a connection
        VISA_Driver.performOpen(self, options=options)
        

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check type of quantity
        self.write(quant.get_cmd, bCheckError=True)
        self.read(None, ignore_termination=False)
        value = self.read(None, ignore_termination=False)
        if quant.name in ('LHe Level'):
            value = value[:-3]
        if quant.name in ('Interval'):
            hms = value.split(":")
            value = int(hms[0]) * 3600 + int(hms[1])*60 + int(hms[2])
        return value
        
    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the set value operation"""
        self.write("REMOTE")
        self.read(None, ignore_termination=False)
        if quant.name in ('Interval'):
            m, s = divmod(value, 60)
            h, m = divmod(m, 60)
            cmd = quant.set_cmd + " " + ("%02d:%02d:%02d" % (h, m, s))
            self.writeAndLog(cmd, bCheckError=True)
            self.read(None, ignore_termination=False)
        self.write("LOCAL")
        self.read(None, ignore_termination=False)
        return value
        
if __name__ == '__main__':
    pass
