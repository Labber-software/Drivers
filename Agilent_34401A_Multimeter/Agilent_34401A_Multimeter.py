#!/usr/bin/env python

from VISA_Driver import VISA_Driver
from InstrumentConfig import InstrumentComCfg
import visa

class Driver(VISA_Driver):

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # if gpib, go to local before closing
        if self.dComCfg['interface'] == InstrumentComCfg.GPIB:
            # force local, then close communication
            visa.vpp43.gpib_control_ren(self.com.vi, visa.VI_GPIB_REN_ADDRESS_GTL)
            self.com.close()
        else:
            # standard close
            VISA_Driver.performClose(self, bError=bError, options=options)


if __name__ == '__main__':
    pass
