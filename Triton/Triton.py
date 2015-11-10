#!/usr/bin/env python

from VISA_Driver import VISA_Driver
#import visa

__version__ = "0.0.1"

class Error(Exception):
    pass

class Driver(VISA_Driver):
    """ This class implements the Triton 200 driver"""
  
#    def performOpen(self, options={}):
#        """Perform the operation of opening the instrument connection"""
#        # calling the generic VISA open to make sure we have a connection
#        VISA_Driver.performOpen(self, options=options)
#        # fix issue with termination for read
#        visa.vpp43.set_attribute(self.com.vi, visa.VI_ATTR_SUPPRESS_END_EN, visa.VI_FALSE)

		
    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check type of quantity
        if quant.name in ('T1', 'T2'):
            # temperatures, get value strings
            sAns = self.askAndLog(quant.get_cmd).strip()
            # convert string to float by taking everything after last colon, ignoring final 'K'
            value = float(sAns.rsplit(':',1)[1][:-1])
        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performGetValue(self, quant, options)
        return value

		
if __name__ == '__main__':
    pass
