#!/usr/bin/env python

import InstrumentDriver
from VISA_Driver import VISA_Driver

class Driver(VISA_Driver):
    """ The Signal Recovery 726x driver re-implements the VISA driver with extra options"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # calling the generic VISA open to make sure we have a connection
        VISA_Driver.performOpen(self, options=options)
        
        #This device does not respond to *IDN?, so let's check manually
        id = self.askAndLog("ID")
        if not id in ("7260", "7265"):
            raise InstrumentDriver.CommunicationError("ID query did not return 7260 or 7265. Is this the right driver for the device at the right address?")
            return

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # perform special getValue for reading complex value
        name = str(quant.name)
        if name == 'Value':
            # get complex value in one instrument reading
            sAns = self.askAndLog(quant.get_cmd).strip()
            lData =  sAns.split(',')
            #Python float() complains about 0.0E+00
#            if lData[0].strip() == "0.0E+00":
#                lData[0] = "0"
#            if lData[1].strip() == "0.0E+00":
#                lData[1] = "0"
#            self.log("Test: " + lData[1])
#            return complex(0.0, 0.0)
            # return complex values
            return complex(float(lData[0].rstrip(" \r\n\0")), float(lData[1].rstrip(" \r\n\0")))
        else:
            # run the generic visa driver case
            return VISA_Driver.performGetValue(self, quant, options=options)

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the set value operation"""
        # check type of quantity: There seems to be a problem with some float type commands... (i.e. oscillator frequency) Use the fixed point version instead.
        if quant.name in ('Oscillator Frequency'):
            self.writeAndLog(quant.set_cmd + " " + str(int(value*1000))) #Fixed point version uses mHz
        else:
            return VISA_Driver.performSetValue(self, quant, value, sweepRate, options=options)
        return value


if __name__ == '__main__':
    pass
