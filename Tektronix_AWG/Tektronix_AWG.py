#!/usr/bin/env python

import InstrumentDriver
from VISA_Driver import VISA_Driver
import numpy as np

class Driver(VISA_Driver):
    """ This class implements the Tektronix AWG5014 driver"""
    
    def _getTrigChannel(self, options):
        """Helper function, get trig channel for instrument, or None if N/A"""
        trig_channel = options.get('trig_channel', None)
        return trig_channel

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # add compatibility with pre-python 3 version of Labber
        if not hasattr(self, 'write_raw'):
            self.write_raw = self.write
        # add compatibility with pre-1.5.4 version of Labber
        if not hasattr(self, 'getTrigChannel'):
            self.getTrigChannel = self._getTrigChannel
        # start by calling the generic VISA open to make sure we have a connection
        VISA_Driver.performOpen(self, options)
        # check for strange bug by reading the status bit
        try:
            status = self.askAndLog('*STB?', bCheckError=False)
            status = int(status)
        except:
            # if conversion to int failed, re-read instrument buffer to clear
            sBuffer = self.read()
            self.log('Extra data read from Tek: %s, %s' % (str(status), sBuffer))
        # get model name and number of channels
        sModel = self.getModel()
        self.nCh = 4 if sModel in ('5004', '5014') else 2
        # turn off run mode
        self.writeAndLog(':AWGC:STOP;')
        # init vectors with old values
        self.bWaveUpdated = False
        self.nOldSeq = -1
        self.lOldU16 = [[np.array([], dtype=np.uint16) \
                       for n1 in range(self.nCh)] for n2 in range(1)]
        # clear old waveforms
        self.lInUse = [False]*self.nCh
        for n in range(self.nCh):
            self.createWaveformOnTek(n+1, 0, bOnlyClear=True)


    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # close VISA connection
        VISA_Driver.performClose(self, bError, options)


    def initSetConfig(self):
        """This function is run before setting values in Set Config"""
        # turn off run mode
        self.writeAndLog(':AWGC:STOP;')
        # init vectors with old values
        self.bWaveUpdated = False
        self.nOldSeq = -1
        self.lOldU16 = [[np.array([], dtype=np.uint16) \
                       for n1 in range(self.nCh)] for n2 in range(1)]
        # clear old waveforms
        self.lInUse = [False]*self.nCh
        for n in range(self.nCh):
            channel = n+1
            self.setValue('Ch %d' % channel, [])
            self.setValue('Ch %d - Marker 1' % channel, [])
            self.setValue('Ch %d - Marker 2' % channel, [])
            self.createWaveformOnTek(channel, 0, bOnlyClear=True)


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # keep track of if waveform is updated, to avoid sending it many times
        if self.isFirstCall(options):
            self.bWaveUpdated = False
            # if sequence mode, make sure the buffer contains enough waveforms
            if self.isHardwareLoop(options):
                (seq_no, n_seq) = self.getHardwareLoopIndex(options)
                # if first call, clear sequence and create buffer
                if seq_no==0:
                    # variable for keepin track of sequence updating
                    self.writeAndLog(':AWGC:STOP;')
                    self.bSeqUpdate = False
                # if different sequence length, re-create buffer
                if seq_no==0 and n_seq != len(self.lOldU16):
                    self.lOldU16 = [[np.array([], dtype=np.uint16) \
                                   for n1 in range(self.nCh)] for n2 in range(n_seq)]
            elif self.isHardwareTrig(options):
                # if hardware triggered, always stop outputting before setting
                self.writeAndLog(':AWGC:STOP;')
        if quant.name in ('Ch 1', 'Ch 2', 'Ch 3', 'Ch 4',
                          'Ch 1 - Marker 1', 'Ch 1 - Marker 2',
                          'Ch 2 - Marker 1', 'Ch 2 - Marker 2',
                          'Ch 3 - Marker 1', 'Ch 3 - Marker 2',
                          'Ch 4 - Marker 1', 'Ch 4 - Marker 2'):
            # set value, then mark that waveform needs an update
            quant.setValue(value)
            self.bWaveUpdated = True
        elif quant.name in ('Run'):
            if value:
                self.writeAndLog(':AWGC:RUN')
                # turn on channels again, to avoid issues when switch run mode
                sOutput = ''
                for n, bUpdate in enumerate(self.lInUse):
                    if bUpdate:
                        sOutput += (':OUTP%d:STAT 1;' % (n + 1))
                if sOutput != '':
                    self.writeAndLog(sOutput)
            else:
                # stop AWG
                self.writeAndLog(':AWGC:STOP;')
        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performSetValue(self, quant, value, sweepRate,
                                                options=options)
        # if final call and wave is updated, send it to AWG
        if self.isFinalCall(options) and self.bWaveUpdated:
            (seq_no, n_seq) = self.getHardwareLoopIndex(options)
            if self.isHardwareLoop(options):
                seq = seq_no
                self.reportStatus('Sending waveform (%d/%d)' % (seq_no+1, n_seq))
            else:
                seq = None

            # in trig mode, don't start AWG if trig channel will start it later
            if ((self.isHardwareTrig(options) and
                 self.getTrigChannel(options) == 'Run')):
                bStart = False
            else:
                bStart = True
            self.sendWaveformAndStartTek(seq=seq, n_seq=n_seq, bStart=bStart)
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


    def sendWaveformAndStartTek(self, seq=None, n_seq=1, bStart=True):
        """Rescale and send waveform data to the Tek"""
        # get model name and number of channels
        self.nPrevData = 0
        self.bIsStopped = False
        # go through all channels
        for n in range(self.nCh):
            # channels are numbered 1-4
            channel = n+1
            vData = self.getValueArray('Ch %d' % channel)
            vMark1 = self.getValueArray('Ch %d - Marker 1' % channel)
            vMark2 = self.getValueArray('Ch %d - Marker 2' % channel)
            bWaveUpdate = self.sendWaveformToTek(channel, vData, vMark1, vMark2, seq)
        # check if sequence mode
        if seq is not None:
            # if not final seq call, just return here
            self.bSeqUpdate = self.bSeqUpdate or bWaveUpdate
            if (seq+1) < n_seq:
                return
            # final call, check if sequence has changed
            if self.bSeqUpdate or n_seq != self.nOldSeq:
                # create sequence list, first clear to reset old values
                self.writeAndLog('SEQ:LENG 0')
                self.writeAndLog('SEQ:LENG %d' % n_seq)
                for n1 in range(n_seq):
                    for n2, bUpdate in enumerate(self.lInUse):
                        if bUpdate:
                            name = 'Labber_%d_%d' % (n2+1, n1+1)
                            self.writeAndLog('SEQ:ELEM%d:WAV%d "%s"' % \
                                             (n1+1, n2+1, name))
                    # always wait for trigger 
                    self.writeAndLog('SEQ:ELEM%d:TWA 1' % (n1+1))
                # for last element, set jump to first
                self.writeAndLog('SEQ:ELEM%d:GOTO:STAT 1' % n_seq)
                self.writeAndLog('SEQ:ELEM%d:GOTO:IND 1' % n_seq)
                # save old sequence length
                self.nOldSeq = n_seq
            # turn on sequence mode
            self.writeAndLog(':AWGC:RMOD SEQ')
            # turn on channels in use 
            sOutput = ''
            for n, bUpdate in enumerate(self.lInUse):
                if bUpdate:
                    sOutput += (':OUTP%d:STAT 1;' % (n+1))
            if sOutput != '':
                self.writeAndLog(sOutput)
            return
        # turn on channels in use 
        sOutput = ''
        for n, bUpdate in enumerate(self.lInUse):
            if bUpdate:
                sOutput += (':OUTP%d:STAT 1;' % (n+1))
        if sOutput != '':
            self.writeAndLog(sOutput)
        # if not starting, make sure AWG is not running, then return
        if not bStart:
            iRunState = int(self.askAndLog(':AWGC:RST?'))
            nTry = 1000
            while nTry>0 and iRunState!=0 and not self.isStopped():
                # sleep for while to save resources, then try again
                self.wait(0.05)
                # try again
                iRunState = int(self.askAndLog(':AWGC:RST?'))
                nTry -= 1
            return
        # check if AWG has been stopped, if not return here
        if not self.bIsStopped:
            # no waveforms updated, just turn on output, no need to wait for run
            return
        # send command to turn on run mode to tek
        self.writeAndLog(':AWGC:RUN;')
        # wait for output to be turned on again
        iRunState = int(self.askAndLog(':AWGC:RST?'))
        nTry = 1000
        while nTry>0 and iRunState==0 and not self.isStopped():
            # sleep for while to save resources, then try again
            self.wait(0.05)
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


    def scaleWaveformToU16(self, vData, dVpp, ch):
        """Scales the waveform and returns data in a string of U16"""
        # make sure waveform data is within the voltage range 
        if np.sum(vData > dVpp/2) or np.sum(vData < -dVpp/2):
            raise InstrumentDriver.Error(
                ('Waveform for channel %d contains values that are ' % ch) + 
                'outside the channel voltage range.')
        # clip waveform and store in-place
        np.clip(vData, -dVpp/2., dVpp/2., vData)
        vU16 = np.array(16382 * (vData + dVpp/2.)/dVpp, dtype=np.uint16)
        return vU16


    def createWaveformOnTek(self, channel, length, seq=None, bOnlyClear=False):
        """Remove old and create new waveform on the Tek. The waveform is named
        by the channel nunber"""
        if seq is None:
            name = 'Labber_%d' % channel
        else:
            name = 'Labber_%d_%d' % (channel, seq+1)
        # first, turn off output
        self.writeAndLog(':OUTP%d:STAT 0;' % channel)
        if bOnlyClear:
            # just clear this channel
            self.writeAndLog(':SOUR%d:WAV ""' % channel)
        else:
            # remove old waveform, ignoring errors, then create new
            self.writeAndLog(':WLIS:WAV:DEL "%s"; *CLS' % name, bCheckError=False)
            self.writeAndLog(':WLIS:WAV:NEW "%s",%d,INT;' % (name, length))


    def sendWaveformToTek(self, channel, vData, vMark1, vMark2, seq=None):
        """Send waveform to Tek"""
        # check if sequence
        if seq is None:
            iSeq = 0
        else:
            iSeq = seq
        # channels are named 1-4
        n = channel-1
        if len(vData)==0:
            if len(vMark1)==0 and len(vMark2)==0:
                # if channel in use, turn off, clear, go to next channel
                if self.lInUse[n]:
                    self.createWaveformOnTek(channel, 0, seq, bOnlyClear=True)
                    self.lOldU16[iSeq][n] = np.array([], dtype=np.uint16)
                    self.lInUse[n] = False
                return False
            else:
                # no data, but markers exist, output zeros for data
                nMark = max(len(vMark1), len(vMark2))
                vData = np.zeros((nMark,), dtype=float)
        # make sure length of data is the same
        if (len(vMark1)>0 and len(vData)!=len(vMark1)) or \
           (len(vMark2)>0 and len(vData)!=len(vMark2)) or \
           (self.nPrevData>0 and len(vData)!=self.nPrevData):
            raise InstrumentDriver.Error(\
                  'All channels need to have the same number of elements')
        self.nPrevData = len(vData)
        # channel in use, mark
        self.lInUse[n] = True
        # get range and scale to U16
        Vpp = self.getValue('Ch%d - Range' % channel)
        vU16 = self.scaleWaveformToU16(vData, Vpp, channel)
        # check for marker traces
        for m, marker in enumerate([vMark1, vMark2]):
            if len(marker)==len(vU16):
                # get marker trace
                vMU16 = np.array(marker != 0, dtype=np.uint16)
                # add marker trace to data trace, with bit shift
                vU16 += 2**(14+m) * vMU16
        start, length = 0, len(vU16)
        # compare to previous trace
        if length != len(self.lOldU16[iSeq][n]):
            # stop AWG if still running
            if not self.bIsStopped:
                self.writeAndLog(':AWGC:STOP;')
                self.bIsStopped = True
            # len has changed, del old waveform and create new
            self.createWaveformOnTek(channel, length, seq)
        else:
            # same length, check for similarities
            vIndx = np.nonzero(vU16 != self.lOldU16[iSeq][n])[0]
            if len(vIndx) == 0:
                # nothing changed, don't update, go on to next
                return False
            # some elements changed, find start and length
            start = vIndx[0]
            length = vIndx[-1] - vIndx[0] + 1
        # stop AWG if still running
        if not self.bIsStopped:
            self.writeAndLog(':AWGC:STOP;')
            self.bIsStopped = True
        # create binary data as bytes with header
        sLen = b'%d' % (2*length)
        sHead = b'#%d%s' % (len(sLen), sLen)
        # send to tek, start by turning off output
        if seq is None:
            # non-sequence mode, get name
            name = b'Labber_%d' % channel
            sSend = b':OUTP%d:STAT 0;' % channel
            sSend += b':WLIS:WAV:DATA "%s",%d,%d,%s' % (name, start, length,
                     sHead + vU16[start:start+length].tobytes())
            self.write_raw(sSend)
            # (re-)set waveform to channel
            self.writeAndLog(':SOUR%d:WAV "%s"' % (channel, name.decode()))
        else:
            # sequence mode, get name
            name = b'Labber_%d_%d' % (channel, seq+1)
            sSend = b':OUTP%d:STAT 0;' % channel
            sSend += b':WLIS:WAV:DATA "%s",%d,%d,%s' % (name, start, length,
                     sHead + vU16[start:start+length].tobytes())
            self.write_raw(sSend)
        # store new waveform for next call
        self.lOldU16[iSeq][n] = vU16
        return True
        


if __name__ == '__main__':
    pass
