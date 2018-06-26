#!/usr/bin/env python

from VISA_Driver import VISA_Driver


class Driver(VISA_Driver):
    """ This class implements the Keysight PXI LO"""


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # start with setting local quant value
        # proceed depending on command
        if quant.name == 'Clock source':
            # for clock source, first read current value
            old_clock = self.askAndLog(':CLK:SOUR?')
            # get command string for new value, check if they match
            new_clock = quant.getCmdStringFromValue(value)
            if old_clock != new_clock:
                # clock has changed, update
                self.writeAndLog(':CLK:SOUR %s' % new_clock)
                # if internal, make sure clock frequency is 19.2 GHz
                if new_clock == 'CLKIN':
                    self.writeAndLog(':CLK:FREQ 19.2E9')
                # after clock change, we need to calibrate the system clock
                self.writeAndLog(':CAL:SCLK')

        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performSetValue(self, quant, value, sweepRate,
                                                options=options)
        return value



if __name__ == '__main__':
    pass
