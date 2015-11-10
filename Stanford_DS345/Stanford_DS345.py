#!/usr/bin/env python

from VISA_Driver import VISA_Driver

class Driver(VISA_Driver):
    """ The DS 345 driver re-implements the VISA driver for taking care of units"""

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # perform special getValue for amplitude command
        if quant.name == 'Amplitude':
            # get voltage string from instrument
            sAns = self.askAndLog('AMPL? VP').strip()
            # strip "VP" from string 
            sData =  sAns.split('VP')[0]
            # return float
            return float(sData)
        else:
            # for all other cases, just run the generic visa driver
            return VISA_Driver.performGetValue(self, quant, options=options)

