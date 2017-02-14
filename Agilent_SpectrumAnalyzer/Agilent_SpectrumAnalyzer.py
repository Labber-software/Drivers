#!/usr/bin/env python

import InstrumentDriver
from VISA_Driver import VISA_Driver
from InstrumentConfig import InstrumentQuantity
import numpy as np

class Error(Exception):
    pass

class Driver(VISA_Driver):
    """ This class implements the Agilen 4470 Spectrum Analyzer driver"""

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
#        if quant.name in ('Zero-span mode',):
        if quant.name in ('Range type',):
            if quant.getValueString(value) == 'Zero-span mode':
                # set span to zero
                self.sendValueToOther('Span', 0.0)
                self.sendValueToOther('# of points', 2.0)
                # sweep time should be set to a small value (for example, 10 ms)
                self.writeAndLog(':SWE:TIME:AUTO 0;:SWE:TIME 10E-3;')
            else:
                # set lowest possible span to get out of zero-span mode
                self.sendValueToOther('Span', 100.0)
                # sweep time should be set to auto
                self.writeAndLog(':SWE:TIME:AUTO 1;')
        elif quant.name in ('Wait for new trace',):
            # turn on continous acquisition if not waiting     
            if value == False:
                self.writeAndLog(':INIT:CONT ON;')
        else:
            # run standard VISA case 
            value = VISA_Driver.performSetValue(self, quant, value, sweepRate, options)
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check type of quantity
#        if quant.name in ('Zero-span mode',):
        if quant.name in ('Range type',):
            # check if span is zero
            span = self.readValueFromOther('Span')
            if span == 0:
                value = 'Zero-span mode'
            else:
                # return old value if not in zero span
                value = quant.getValueString()
                if value == 'Zero-span mode':
                    value = 'Center - Span'
        elif quant.name in ('Signal', 'Signal - Zero span'):
            # if not in continous mode, trig from computer
            bWaitTrace = self.getValue('Wait for new trace')
            bAverage = self.getValue('Average')
            # wait for trace, either in averaging or normal mode
            if bWaitTrace:
                if bAverage:
                    # clear averages
                    self.writeAndLog(':SENS:AVER:CLE;')
                self.writeAndLog(':ABOR;:INIT:CONT OFF;:INIT:IMM;*OPC')
                # wait some time before first check
                self.wait(0.03)
                bDone = False
                while (not bDone) and (not self.isStopped()):
                    # check if done
                    stb = int(self.askAndLog('*ESR?'))
                    bDone = (stb & 1) > 0
                    if not bDone:
                        self.wait(0.05)
                # if stopped, don't get data
                if self.isStopped():
                    self.writeAndLog('*CLS;:INIT:CONT ON;')
                    return []
            # get data as float32, convert to numpy array
            self.write(':FORM REAL,32;TRAC:DATA? TRACE1', bCheckError=False)
            sData = self.read(ignore_termination=True)
            if bWaitTrace and not bAverage:
                self.writeAndLog(':INIT:CONT ON;')
            # strip header to find # of points
            i0 = sData.find(b'#')
            nDig = int(sData[i0+1:i0+2])
            nByte = int(sData[i0+2:i0+2+nDig])
            nPts = nByte/4
            # get data to numpy array
            vData = np.frombuffer(sData[(i0+2+nDig):(i0+2+nDig+nByte)], 
                                  dtype='>f', count=nPts)
            # get start/stop frequencies
            startFreq = self.readValueFromOther('Start frequency')
            stopFreq = self.readValueFromOther('Stop frequency')
            sweepType = self.readValueFromOther('Sweep type')
            # if log scale, take log of start/stop frequencies
            if sweepType == 'Log':
                startFreq = np.log10(startFreq)
                stopFreq = np.log10(stopFreq)
            # check if return trace or trace average
            if quant.name == 'Signal - Zero span':
                # return average
                value = np.average(vData)
            else:
                # create a trace dict
                value = InstrumentQuantity.getTraceDict(vData, t0=startFreq,
                                               dt=(stopFreq-startFreq)/(nPts-1))
        elif quant.name in ('Wait for new trace',):
            # do nothing, return local value
            value = quant.getValue()
        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performGetValue(self, quant, options)
        return value
        

if __name__ == '__main__':
    pass
