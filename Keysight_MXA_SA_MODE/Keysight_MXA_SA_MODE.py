#!/usr/bin/env python

from VISA_Driver import VISA_Driver
import numpy as np

class Error(Exception):
    pass

class Driver(VISA_Driver):
    """ This class implements the Keysight N90xx instrument driver"""
    
    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should return the actual value set by the instrument"""
        if quant.name in ('Range type',):
            if quant.getValueString(value) == 'Zero-span mode':
                # set span to zero
                self.sendValueToOther('Span', 0.0)
                self.sendValueToOther('# of points', 2.0)
                #sweep time should be set to a small value (for example, 10 ms)
                self.writeAndLog(':SWE:TIME 1E-3;')
            else:
                # set lowest possible span to get out of zero-span mode
                if self.getValue('Span') < 10:
                    self.sendValueToOther('Span', 1000000)
                if self.getValue('# of points') == 2:
                    self.sendValueToOther('# of points', 1001)
                # sweep time should be set to auto
                self.writeAndLog(':SWE:TIME:AUTO 1;')
        elif quant.name in ('Wait for new trace',):
            # turn on continous acquisition if not waiting     
            if value == False:
                self.writeAndLog(':INIT:CONT ON;')
        elif quant.name in ('Trace type CS', 'Trace type CW', 'Measurement Type'):
            pass
        else:
            # run standard VISA case 
            value = VISA_Driver.performSetValue(self, quant, value, sweepRate, options)
        return value
    
    
    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check type of quantity
        #if quant.name in ('Zero-span mode',):
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
            if bAverage:
                # clear averages
                self.writeAndLog(':SENS:AVER:CLE;')
                self.writeAndLog(':ABOR;:INIT:CONT OFF;:INIT:IMM;*OPC')
                # wait some time before first check
                self.thread().msleep(30)
                bDone = False
                while (not bDone) and (not self.isStopped()):
                    # check if done
                    stb = int(self.askAndLog('*ESR?'))
                    bDone = (stb & 1) > 0
                    if not bDone:
                        self.thread().msleep(50)
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
            # sweepType = self.readValueFromOther('Sweep type')
            # # if log scale, take log of start/stop frequencies
            # if sweepType == 'Log':
                # startFreq = np.log10(startFreq)
                # stopFreq = np.log10(stopFreq)
            # check if return trace or trace average
            if quant.name == 'Signal - Zero span':
                # return average
                value = np.average(vData)
            else:
                # create a trace dict
                value = quant.getTraceDict(vData, x0=startFreq, x1=stopFreq)
        elif quant.name in ('Signal - CW'):
            # if not in continous mode, trig from computer
            bWaitTrace = self.getValue('Wait for new trace')
            bAverage = self.getValue('Average CW')
            # wait for trace, either in averaging or normal mode
            if bAverage:
                # clear averages
                self.writeAndLog(':WAV:AVER:CLE;')
                self.writeAndLog(':ABOR;:INIT:CONT OFF;:INIT:IMM;*OPC')
                # wait some time before first check
                self.thread().msleep(30)
                bDone = False
                while (not bDone) and (not self.isStopped()):
                    # check if done
                    stb = int(self.askAndLog('*ESR?'))
                    bDone = (stb & 1) > 0
                    if not bDone:
                        self.thread().msleep(50)
                # if stopped, don't get data
                if self.isStopped():
                    self.writeAndLog('*CLS;:INIT:CONT ON;')
                    return []
            # get data as float32, convert to numpy array
            sTraceNum = self.getTraceDict(quant)
            sWrite = ':FORM REAL,32;READ:WAV'+sTraceNum+'?'
            self.write(sWrite, bCheckError=False)
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
            #duration = self.readValueFromOther('Measurement Time IQ')
            sampleFreq = self.readValueFromOther('Sample Rate CW')
            # sweepType = self.readValueFromOther('Sweep type')
            # # if log scale, take log of start/stop frequencies
            # if sweepType == 'Log':
                # startFreq = np.log10(startFreq)
                # stopFreq = np.log10(stopFreq)
            # check if return trace or trace average
            # create a trace dict
            if self.getValue('Trace type CW') == 'unprocessed IQ trace data (V)':
                #the trace is complex.  I values are even indices while Q values are odd indices.
                realData = vData[0:nPts:2]
                imagData = vData[1:nPts:2]
                cData = realData +1j*imagData
                samplePeriod = (2/sampleFreq)
            else:
                #the trace is a simple vector.
                cData = vData +1j*np.zeros(vData.shape)
                samplePeriod = (1/sampleFreq)
            
            value = quant.getTraceDict(cData, x0=0.0, dx=samplePeriod)
            
        elif quant.name in ('Signal - CS'):
            # if not in continous mode, trig from computer
            bWaitTrace = self.getValue('Wait for new trace')
            bAverage = self.getValue('Average CS')
            # wait for trace, either in averaging or normal mode
            if bAverage:
                # clear averages
                self.writeAndLog(':SPEC:AVER:CLE;')
                self.writeAndLog(':ABOR;:INIT:CONT OFF;:INIT:IMM;*OPC')
                # wait some time before first check
                self.thread().msleep(30)
                bDone = False
                while (not bDone) and (not self.isStopped()):
                    # check if done
                    stb = int(self.askAndLog('*ESR?'))
                    bDone = (stb & 1) > 0
                    if not bDone:
                        self.thread().msleep(50)
                # if stopped, don't get data
                if self.isStopped():
                    self.writeAndLog('*CLS;:INIT:CONT ON;')
                    return []
            # get data as float32, convert to numpy array
            sTraceNum = self.getTraceDict(quant)
            sWrite = ':FORM REAL,32;READ:SPEC'+sTraceNum+'?'
            self.write(sWrite, bCheckError=False)
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
            #duration = self.readValueFromOther('Measurement Time IQ')
            centerFreq = self.getValue('Center frequency CS')
            span = self.getValue('Span CS')
            startFreq = centerFreq - span/2
            stopFreq = centerFreq + span/2
            # sweepType = self.readValueFromOther('Sweep type')
            # # if log scale, take log of start/stop frequencies
            # if sweepType == 'Log':
                # startFreq = np.log10(startFreq)
                # stopFreq = np.log10(stopFreq)
            # check if return trace or trace average
            # create a trace dict
            if self.getValue('Trace type CS') in ('unprocessed IQ trace data (V)', 'processed I/Q trace vs. time'):
                #the trace is complex.  I values are even indices while Q values are odd indices.
                realData = vData[0:nPts:2]
                imagData = vData[1:nPts:2]
                cData = realData +1j*imagData
                nPts_new = nPts/2
            else:
                #the trace is a simple vector.
                cData = vData +1j*np.zeros(vData.shape)
                nPts_new = nPts
                
            if self.getValue('Trace type CS') in ('log-mag vs. Freq.', 'avged log-mag vs. Freq.', 'phase of FFT vs. Freq.', 'linear spectrum (V RMS)', 'avged linear spectrum (V RMS)'):
                startValue=startFreq
                delta=(stopFreq-startFreq)/(nPts_new-1)
            else:
                startValue=0
                delta = 1
                
                
            value = quant.getTraceDict(cData, x0=startValue, dx=delta)
            
        elif quant.name in ('Wait for new trace',):
            # do nothing, return local value
            value = quant.getValue()
        elif quant.name in ('Trace type CS', 'Trace type CW', 'Measurement Type'):
            value = self.getValue(quant.name)
        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performGetValue(self, quant, options)
        return value
        
    def getTraceDict(self, quant):
        if quant.name in ('Signal - CS'):
            traceDict = {'unprocessed IQ trace data (V)': '0',
                              'log-mag vs. time': '2',
                              'processed I/Q trace vs. time': '3',
                              'log-mag vs. Freq.': '4',
                              'avged log-mag vs. Time': '5',
                              'avged log-mag vs. Freq.': '7',
                              'shape of FFT window': '9',
                              'phase of FFT vs. Freq.': '10',
                              'linear spectrum (V RMS)': '11',
                              'avged linear spectrum (V RMS)': '12'
                              }
            sTraceType = self.getValue('Trace type CS')
        elif quant.name in ('Signal - CW'):
            traceDict = {'unprocessed IQ trace data (V)': '0',
                              'log-mag vs. time': '2',
                              }
            sTraceType = self.getValue('Trace type CW')
        return traceDict[sTraceType]
            
            

if __name__ == '__main__':
    pass
