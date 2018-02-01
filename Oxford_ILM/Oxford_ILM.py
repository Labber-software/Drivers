#!/usr/bin/env python

from VISA_Driver import VISA_Driver

# the Oxford ILM does not seem to be able to handle commands any faster
# a delay between commands is needed

class Driver(VISA_Driver):
    """ This class implements the Oxford ILM driver"""
    

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check quantity
        if quant.name == 'He level':
            self.wait(0.1)
            # switch instrument to fast mode
            self.writeAndLog('$T1')
            self.wait(0.1)
            reply = self.askAndLog('R1')
            self.wait(0.1)
            # switch instrument to slow mode
            self.writeAndLog('$S1')
            # strip first character
            reply = reply[1:]
            # convert to float, scale to percentage
            value = 0.1 * float(reply)
        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performGetValue(self, quant, options)
        return value
        


if __name__ == '__main__':
    pass
