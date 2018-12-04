#!/usr/bin/env python

from VISA_Driver import VISA_Driver


class Driver(VISA_Driver):
    """ This class implements the Oxford Mercury IPS driver"""
    

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # check quantity
        if quant.name == 'Magnetic Field':
            if sweepRate != 0:
                # sweep rate should be in T/min
                self.writeAndLog('$T'+ str(sweepRate*60.0))
            self.writeAndLog('$J'+  str(value))
            self.writeAndLog('$A1')
        else:
            # run standard VISA case 
            value = VISA_Driver.performSetValue(self, quant, value, sweepRate, options)
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check type of quantity
        # check quantity
        if quant.name == 'Magnetic Field':
            reply = self.askAndLog('R7')
            # strip first character
            value = float(reply[1:])
        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performGetValue(self, quant, options)
        return value
        
    def checkIfSweeping(self, quant, options={}):
        target = self.askAndLog('R8')
        self.wait(0.1)
        # strip first character
        target = float(target[1:])
        currentValue = Driver.performGetValue(self,quant,options)
        if abs(target-currentValue) < float(quant.sweep_res):
            status = self.askAndLog('X')
            # check that power supply is in hold mode
            if float(status[4])==0:
                return(False)
        self.wait(0.1)
        return(True)

    def performStopSweep(self, quant, options={}):
        self.writeAndLog('$A0')

if __name__ == '__main__':
    pass
