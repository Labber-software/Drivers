#!/usr/bin/env python

from VISA_Driver import VISA_Driver
import SG_String

__version__ = "0.0.1"

class Error(Exception):
    pass

class Driver(VISA_Driver):
    """ This class re-implements special cases of the Holzworth HS9000 driver"""

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # simple workaround to deal with status queries not matching cmd_def vals
        if quant.name == 'Reference':
            # common method for these quants
            
            s1 = self.askAndLog(':CH0:STATUS?')
            # check for errors and raise exception if necesary
            self.queryErrors()
            if s1 == 'Internal 100MHz':
                return 'INT:100MHz'
            elif s1 == 'External 10MHz':
                return 'EXT:10MHz'
            else:
                return 'EXT:100MHz'
        elif quant.name in [('Ch%d - Frequency' % (n+1)) for n in range(8)]:
            sCh = quant.name[2]
            s1 = self.askAndLog(':CH%s:FREQ?' % sCh)
            s2 = s1.split('Hz')[0]
            return SG_String.getValueFromSIString(s2)
        else:
            # run the generic visa driver case
            return VISA_Driver.performGetValue(self, quant, options=options)

if __name__ == '__main__':
    pass