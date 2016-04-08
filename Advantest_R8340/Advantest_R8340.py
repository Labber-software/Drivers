#!/usr/bin/env python

from VISA_Driver import VISA_Driver


class Driver(VISA_Driver):
    """ The driver re-implements the VISA driver with some more options"""


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # do special case get value for some quantities
        if quant.name in ('Current', 'Resistance'):
            # check if charge/discharge
            discharge = self.getValue('Discharge/charge before measuring')
            if discharge:
                delay_time = self.getValue('Delay between charging/measuring') 
                # start by discharging, then charging
                self.writeAndLog('MD2')
                self.writeAndLog('OT1')
                self.writeAndLog('MD1')
                # wait some time
                self.wait(delay_time)
            # after charging/discharing, run the visa driver case to get value
            return VISA_Driver.performGetValue(self, quant, options=options)
        else:
            # run the generic visa driver case
            return VISA_Driver.performGetValue(self, quant, options=options)



if __name__ == '__main__':
    pass
