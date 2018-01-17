#!/usr/bin/env python

from VISA_Driver import VISA_Driver

class Driver(VISA_Driver):
    """ The SRS 830 driver re-implements the VISA driver with extra options"""

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # perform special getValue for reading complex value
        name = str(quant.name)
        if name == 'Value':
            # get complex value in one instrument reading
            sCmd = 'SNAP?1,2'
            sAns = self.askAndLog(sCmd).strip()
            lData =  sAns.split(',')

            #Sometimes, we receive the value twice
            #(0.12e-3,4.56e-70.12e-3,4.56e-7 instead of 0.12e-3,4.56e-7)
            #This is a simple fix:
            if len(lData) > 2:
                lData =  sAns[:int(len(sAns)/2)].split(',')
            #Also, sometimes we receive an additional "-" at the end of a value
            #(0.12e-3,4.56e-7- instead of 0.12e-3,4.56e-7)
            #Hence, another simple fix:
            if lData[1][-1] == "-":
                lData[1] = lData[1][:-1]

            # return complex values
            return complex(float(lData[0].strip()), float(lData[1].strip()))
        else:
            # run the generic visa driver case
            return VISA_Driver.performGetValue(self, quant, options=options)


if __name__ == '__main__':
    pass
