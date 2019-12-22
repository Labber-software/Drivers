import InstrumentDriver
import numpy as np
import sys, time

from time import perf_counter as timer

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements a simple signal generator driver"""
    

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        self.timeStart = None


    def initSetConfig(self):
        """Reset the timer before setting configuration (tyically at startup)"""
        self.timeStart = timer()

        
    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # proceed depending on quantity
        if quant.name == 'Timer':
            # reset timer if setting to zero
            if value == 0.0 or self.timeStart is None:
                # save the timer value for initialization
                self.timeStart = timer()
            else:
                # loop for waiting for time
                while True:
                    # check if stopped
                    if self.isStopped():
                        value = timer() - self.timeStart
                        break
                    dt = value - (timer() - self.timeStart)
                    if dt > 0.2:
                        # sleep 200 ms at a time, to allow interrupts
                        time.sleep(0.2)
                        self.reportCurrentValue(quant, timer() - self.timeStart)
                    elif dt > 0:
                        # sleep remaining time, then break
                        time.sleep(dt)
                        break
                    else:
                        # break directly if no time left 
                        break
            return value
        else:
            # for other quantities, just return current value of control
            return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # proceed depending on quantity
        if quant.name in ('Timer', 'Clock'):
            if self.timeStart is None:
                # if first call, init timer
                self.timeStart = timer()
                return 0.0
            else:
                return timer() - self.timeStart
        else: 
            # for other quantities, just return current value of control
            return quant.getValue()


