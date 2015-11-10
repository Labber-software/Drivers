#!/usr/bin/env python

import InstrumentDriver
from VISA_Driver import VISA_Driver
import numpy as np

class Driver(VISA_Driver):
    """ This class implements the Tektronix AWG5014 driver"""
    
    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # start by calling the generic VISA open to make sure we have a connection
        VISA_Driver.performOpen(self, options)
        # check for strange bug by reading the status bit
        try:
            status = self.askAndLog('*STB?', bCheckError=False)
            status = int(status)
        except:
            # if conversion to int failed, re-read instrument buffer to clear
            sBuffer = self.read()
            self.logInstr.log(15, 'Extra data read from Tek: %s, %s' % 
                              (str(status), sBuffer))
        # get model name and number of channels
        sModel = self.getModel()
        nCh = 4 if sModel in ('5004', '5014') else 2
        # turn off run mode
        self.writeAndLog(':AWGC:STOP;')
        # init vectors with old values
        self.bWaveUpdated = False
        self.lOldU16 = [np.array([], dtype=np.uint16)]*nCh
        # clear old waveforms
        self.lInUse = [False]*nCh
        for n in range(nCh):
            self.createWaveformOnTek(n+1, 0, bOnlyClear=True)


    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # close VISA connection
        VISA_Driver.performClose(self, bError, options)


    def initSetConfig(self):
        """This function is run before setting values in Set Config"""
        # get model name and number of channels
        sModel = self.getModel()
        nCh = 4 if sModel in ('5004', '5014') else 2
        # turn off run mode
        self.writeAndLog(':AWGC:STOP;')
        # init vectors with old values
        self.bWaveUpdated = False
        self.lOldU16 = [np.array([], dtype=np.uint16)]*nCh
        # clear old waveforms
        self.lInUse = [False]*nCh
        for n in range(nCh):
            self.createWaveformOnTek(n+1, 0, bOnlyClear=True)


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # keep track of if waveform is updated, to avoid sending it many times
        if self.isFirstCall(options):
            self.bWaveUpdated = False
        if quant.name in ('Ch 1', 'Ch 2', 'Ch 3', 'Ch 4',
                          'Ch 1 - Marker 1', 'Ch 1 - Marker 2',
                          'Ch 2 - Marker 1', 'Ch 2 - Marker 2',
                          'Ch 3 - Marker 1', 'Ch 3 - Marker 2',
                          'Ch 4 - Marker 1', 'Ch 4 - Marker 2'):
            # set value, then mark that waveform needs an update
            quant.setValue(value)
            self.bWaveUpdated = True
        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performSetValue(self, quant, value, sweepRate,
                                                options=options)
        # if final call and wave is updated, send it to AWG
        if self.isFinalCall(options) and self.bWaveUpdated:
            self.sendWaveformToTek()
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check type of quantity
        if quant.name in ('Ch 1', 'Ch 2', 'Ch 3', 'Ch 4',
                          'Ch 1 - Marker 1', 'Ch 1 - Marker 2',
                          'Ch 2 - Marker 1', 'Ch 2 - Marker 2',
                          'Ch 3 - Marker 1', 'Ch 3 - Marker 2',
                          'Ch 4 - Marker 1', 'Ch 4 - Marker 2'):
            # do nothing here
            value = quant.getValue()
        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performGetValue(self, quant, options)
        return value


    def sendWaveformToTek(self):
        """Rescale and send waveform data to the Tek"""
        # get model name and number of channels
        sModel = self.getModel()
        nCh = 4 if sModel in ('5004', '5014') else 2
        nPrevData = 0
        bIsStopped = False
#        # go through all channels
        for n in range(nCh):
            # channels are numbered 1-4
            channel = n+1
            vData = self.getValueArray('Ch %d' % channel)
            vMark1 = self.getValueArray('Ch %d - Marker 1' % channel)
            vMark2 = self.getValueArray('Ch %d - Marker 2' % channel)
            if len(vData)==0:
                if len(vMark1)==0 and len(vMark2)==0:
                    # if channel in use, turn off, clear, go to next channel
                    if self.lInUse[n]:
                        self.createWaveformOnTek(channel, 0, bOnlyClear=True)
                        self.lOldU16[n] = np.array([], dtype=np.uint16)
                        self.lInUse[n] = False
                    continue
                else:
                    # no data, but markers exist, output zeros for data
                    nMark = max(len(vMark1), len(vMark2))
                    vData = np.zeros((nMark,), dtype=float)
            # make sure length of data is the same
            if (len(vMark1)>0 and len(vData)!=len(vMark1)) or \
               (len(vMark2)>0 and len(vData)!=len(vMark2)) or \
               (nPrevData>0 and len(vData)!=nPrevData):
                raise InstrumentDriver.Error('All channels need to have the same number of elements')
            nPrevData = len(vData)
            # channel in use, mark
            self.lInUse[n] = True
            # get range and scale to U16
            Vpp = self.getValue('Ch%d - Range' % channel)
            vU16 = self.scaleWaveformToU16(vData, Vpp)
            # check for marker traces
            for m, marker in enumerate([vMark1, vMark2]):
                if len(marker)==len(vU16):
                    # get marker trace
                    vMU16 = np.array(marker != 0, dtype=np.uint16)
                    # add marker trace to data trace, with bit shift
                    vU16 += 2**(14+m) * vMU16
            start, length = 0, len(vU16)
            # compare to previous trace
            if length != len(self.lOldU16[n]):
                # stop AWG if still running
                if not bIsStopped:
                    self.writeAndLog(':AWGC:STOP;')
                    bIsStopped = True
                # len has changed, del old waveform and create new
                self.createWaveformOnTek(channel, length)
            else:
                # same length, check for similarities
                vIndx = np.nonzero(vU16 != self.lOldU16[n])[0]
                if len(vIndx) == 0:
                    # nothing changed, don't update, go on to next
                    continue
                # some elements changed, find start and length
                start = vIndx[0]
                length = vIndx[-1] - vIndx[0] + 1
            # stop AWG if still running
            if not bIsStopped:
                self.writeAndLog(':AWGC:STOP;')
                bIsStopped = True
            # send waveform, get name
            name = 'Labber_%d' % channel
            # create data as string with header
            sLen = '%d' % (2*length)
            sHead = '#%d%s' % (len(sLen), sLen)
            # send to tek, start by turning off output
            sSend = ':OUTP%d:STAT 0;' % channel
            sSend += ':WLIS:WAV:DATA "%s",%d,%d,%s' % (name, start, length,
                     sHead + vU16[start:start+length].tostring())
            self.write(sSend)
            # (re-)set waveform to channel
            self.writeAndLog(':SOUR%d:WAV "%s"' % (channel, name))
            # store new waveform for next call
            self.lOldU16[n] = vU16
        # turn on channels in use 
        sOutput = ''
        for n, bUpdate in enumerate(self.lInUse):
            if bUpdate:
                sOutput += (':OUTP%d:STAT 1;' % (n+1))
        if sOutput != '':
            self.writeAndLog(sOutput)
        # check if AWG has been stopped, if not return here
        if not bIsStopped:
            # no waveforms updated, just turn on output, no need to wait for run
            return
        # send command to turn on run mode to tek
        self.writeAndLog(':AWGC:RUN;')
        # wait for output to be turned on again
        iRunState = int(self.askAndLog(':AWGC:RST?'))
        nTry = 100
        while nTry>0 and iRunState==0 and not self.isStopped():
            # sleep for while to save resources, then try again
            self.thread().msleep(50)
            # try again
            iRunState = int(self.askAndLog(':AWGC:RST?'))
            nTry -= 1
        # check if timeout occurred
        if nTry <= 0:
            # timeout
            raise InstrumentDriver.Error('Cannot turn on Run mode')
        # turn on channels again, to avoid issues when turning on/off run mode
        if sOutput != '':
            self.writeAndLog(sOutput)


    def scaleWaveformToU16(self, vData, dVpp):
        """Scales the waveform and returns data in a string of U16"""
        # clip waveform and store in-place
        np.clip(vData, -dVpp/2., dVpp/2., vData)
        vU16 = np.array(16382 * (vData + dVpp/2.)/dVpp, dtype=np.uint16)
        return vU16


    def createWaveformOnTek(self, channel, length, bOnlyClear=False):
        """Remove old and create new waveform on the Tek. The waveform is named
        by the channel nunber"""
        name = 'Labber_%d' % channel
        # first, turn off output
        self.writeAndLog(':OUTP%d:STAT 0;' % channel)
        if bOnlyClear:
            # just clear this channel
            self.writeAndLog(':SOUR%d:WAV ""' % channel)
        else:
            # remove old waveform, ignoring errors, then create new
            self.writeAndLog(':WLIS:WAV:DEL "%s"; *CLS' % name, bCheckError=False)
            self.writeAndLog(':WLIS:WAV:NEW "%s",%d,INT;' % (name, length))



if __name__ == '__main__':
    pass
