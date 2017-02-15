#!/usr/bin/env python

from VISA_Driver import VISA_Driver
import numpy as np

__version__ = "0.0.1"

class Error(Exception):
    pass

class Driver(VISA_Driver):
    """ This class implements the Rohde&Schwarz Network Analyzer driver"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # init meas param dict
        self.dMeasParam = {}
        # calling the generic VISA open to make sure we have a connection
        VISA_Driver.performOpen(self, options=options)


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
		# create new channels if needed
        if quant.name in ('Wait for new trace',):
            # do nothing
            pass
        else:
            # run standard VISA case 
            value = VISA_Driver.performSetValue(self, quant, value, sweepRate, options)
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check type of quantity
        if quant.name in ('Signal',):
            # check if channel is on
            if True: #quant.name in self.dMeasParam:
                # if not in continous mode, trig from computer
                bWaitTrace = self.getValue('Wait for new trace')
                bAverage = self.getValue('Average')
                # wait for trace, either in averaging or normal mode
                if bWaitTrace:
                    if bAverage:
                        nAverage = self.getValue('# of averages')
#                        self.writeAndLog(':SENS:AVER:CLE;:ABOR;:INIT;*WAI')
                        self.writeAndLog(':ABOR;:INIT:CONT OFF;:SENS:AVER:COUN %d;:INIT:IMM;*OPC' % nAverage)
                    else:
                        self.writeAndLog(':ABOR;:INIT:CONT OFF;:SENS:AVER:COUN 1;:INIT:IMM;*OPC')
                    # wait some time before first check
                    self.wait(0.03)
                    bDone = False
                    while (not bDone) and (not self.isStopped()):
                        # check if done
                        if bAverage:
#                            sAverage = self.askAndLog('SENS:AVER:COUN:CURR?')
#                            bDone = (int(sAverage) >= nAverage)
                            stb = int(self.askAndLog('*ESR?'))
                            bDone = (stb & 1) > 0
                        else:
                            stb = int(self.askAndLog('*ESR?'))
                            bDone = (stb & 1) > 0
                        if not bDone:
                            self.wait(0.1)
                    # if stopped, don't get data
                    if self.isStopped():
                        self.writeAndLog('*CLS;:INIT:CONT ON;')
                        return []
                # get data as float32, convert to numpy array
                sData = self.ask(':FORM REAL,32;TRAC1? TRACE1')
                if bWaitTrace and not bAverage:
                    self.writeAndLog(':INIT:CONT ON;')
                # strip header to find # of points
                i0 = sData.find(b'#')
                nDig = int(sData[i0+1:i0+2])
                nByte = int(sData[i0+2:i0+2+nDig])
                nData = int(nByte/4)
                # get data to numpy array
                vData = np.frombuffer(sData[(i0+2+nDig):(i0+2+nDig+nByte)], 
                                      dtype='<f', count=nData)
                # get start/stop frequencies
#                if self.getValue('Range type')=='Center - Span':
#                    startFreq = self.getValue('Center frequency') - self.getValue('Span')/2.0
#                    stopFreq = self.getValue('Center frequency') + self.getValue('Span')/2.0
#                else:
#                    startFreq = self.getValue('Start frequency')
#                    stopFreq = self.getValue('Stop frequency')
                startFreq = self.readValueFromOther('Start frequency')
                stopFreq = self.readValueFromOther('Stop frequency')
#                sweepType = self.getValue('Sweep type')
                # if log scale, take log of start/stop frequencies
#                if sweepType == 'Log':
#                    startFreq = np.log10(startFreq)
#                    stopFreq = np.log10(stopFreq)
                # if log scale, take log of start/stop frequencies

                # create a trace dict
                value = quant.getTraceDict(vData, x0=startFreq, x1=stopFreq)
            else:
                # not enabled, return empty array
                value = quant.getTraceDict([])
        elif quant.name in ('Wait for new trace',):
            # do nothing, return local value
            value = quant.getValue()
        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performGetValue(self, quant, options)
        return value
        


if __name__ == '__main__':
    pass
