#!/usr/bin/env python

from VISA_Driver import VISA_Driver

# the Oxford PS does not seem to be able to handle commands any faster
# a delay between commands is needed
delayTime = 0.02

class Driver(VISA_Driver):
    """ This class implements the Oxford PS driver"""
    

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # check quantity
        if quant.name == 'Magnetic Field':
            # conversion from T -> mT
            valueT = int(value*1000)
            # send value as integer of mT
            self.wait(delayTime)
            if sweepRate > 0:
                # convert sweep rate from T/s to mT/min
                valueR = int(sweepRate*60000)
                self.writeAndLog('$T%.5d' %  valueR)
            self.wait(delayTime)
            self.writeAndLog('$J%.5d' %  valueT)
            self.wait(delayTime)
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
            self.wait(delayTime)
            # conversion from mT -> T
            reply = self.askAndLog('R7')
            # strip first character
            reply = reply[1:]
            # convert to float, scale from mT to T
            value = 1E-3 * float(reply)
        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performGetValue(self, quant, options)
        return value
        
    def checkIfSweeping(self, quant, options={}):
	self.wait(delayTime)
        target = self.askAndLog('R8')
	# strip first character,scale from mT to T
        target = 1E-3*float(target[1:])
	self.wait(delayTime)
        currentValue = Driver.performGetValue(self,quant,options)
        if abs(target-currentValue) < float(quant.sweep_res):
            return(False)
        return(True)

    def performStopSweep(self, quant, options={}):
	self.writeAndLog('$A0')

if __name__ == '__main__':
    pass
