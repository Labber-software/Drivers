#!/usr/bin/env python

from VISA_Driver import VISA_Driver

class Driver(VISA_Driver):
    """ The SRS 844 driver re-implements the VISA driver with extra options"""

#    def performOpen(self, options={}):
#        """Perform the operation of opening the instrument connection"""
#        # calling the generic VISA open to make sure we have a connection
#        VISA_Driver.performOpen(self, options=options)
#        # set termination character
#        self.com.term_chars = '\r'
	
    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # perform special getValue for reading complex value
        name = str(quant.name)
        if name == 'Value':
            # get complex value in one instrument reading
            sCmd = 'SNAP?1,2'
            sAns = self.askAndLog(sCmd).strip()
            lData =  sAns.split(',')
            # return complex values
            return complex(float(lData[0].strip()), float(lData[1].strip()))
        else:
            # run the generic visa driver case
            return VISA_Driver.performGetValue(self, quant, options=options)


if __name__ == '__main__':
    pass
