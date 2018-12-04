#!/usr/bin/env python

from VISA_Driver import VISA_Driver


class Driver(VISA_Driver):
    """ The MuSwitch driver"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # start by calling the generic VISA open to make sure we have a connection
        VISA_Driver.performOpen(self, options=options)
        #Reads out the Arduino upon start        
        reply = self.read()
        self.log('Response at startup: ' + reply)

        
    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        if quant.name in ('A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'a1',
                          'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'b1'):
            sSet = 's' if value else 'r'
            sBank = quant.name[0]
            sChannel = quant.name[1]
            dPulse = self.getValue('Pulse Length %s' % quant.name[0])*1E3
            sCmd = '%s%s%s,%d' % (sSet, sBank, sChannel, dPulse)
            self.writeAndLog(sCmd)
            reply = self.read()
            self.log('Response: ' + reply)
            return value
        else:
            # for all other quantities, call the generic VISA driver
            return VISA_Driver.performSetValue(self, quant, value, sweepRate,
                                               options=options)


if __name__ == '__main__':
    pass
