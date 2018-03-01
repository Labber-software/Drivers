#!/usr/bin/env python
import sys
sys.path.append('C:\Program Files (x86)\Keysight\SD1\Libraries\Python')
import os
from BaseDriver import LabberDriver, Error, IdError
import keysightSD1
import numpy as np

class Driver(LabberDriver):
    """Keysigh PXI AWG"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # timeout
        self.timeout_ms = int(1000 * self.dComCfg['Timeout'])
        # create AWG instance
        # get PXI chassis
        self.chassis = int(self.dComCfg.get('PXI chassis', 1))
        self.AWG = keysightSD1.SD_AOU()
        AWGPart = self.AWG.getProductNameBySlot(self.chassis,
                                                int(self.comCfg.address))
        if not isinstance(AWGPart, str):
            raise Error('Unit not available')
        # check that model is supported
        dOptionCfg = self.dInstrCfg['options']
        for validId, validName in zip(dOptionCfg['model_id'], dOptionCfg['model_str']):
            if AWGPart.find(validId)>=0:
                # id found, stop searching
                break
        else:
            # loop fell through, raise ID error
            raise IdError(AWGPart, dOptionCfg['model_id'])
        # set model
        self.setModel(validName)
        self.AWG.openWithSlot(AWGPart, self.chassis, int(self.comCfg.address))
        # sampling rate and number of channles is set by model
        if validName in ('M3202', 'H3344'):
            # 1GS/s models
            self.dt = 1E-9
            self.nCh = 4
        elif validName in ('M3302',):
            # two-channel, 500 MS/s model
            self.dt = 2E-9
            self.nCh = 2
        else:
            # assume 500 MS/s for all other models
            self.dt = 2E-9
            self.nCh = 4
        # keep track of if waveform was updated
        self.lWaveUpdated = [False]*self.nCh
        # get hardware version - changes numbering of channels
        hw_version = self.AWG.getHardwareVersion()
        if hw_version >= 4:
            # KEYSIGHT - channel numbers start with 1
            self.ch_index_zero = 1
        else:
            # SIGNADYNE - channel numbers start with 0
            self.ch_index_zero = 0
        self.log('HW:', hw_version)
        # clear old waveforms
        self.AWG.waveformFlush()

        # Create and open HVI 
        self.HVI= keysightSD1.SD_HVI()
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.HVI.open(os.path.join(dir_path, 'InternalTrigger.HVI'))
        self.HVI.assignHardwareWithIndexAndSlot(0, self.chassis, int(self.comCfg.address));


    def getHwCh(self, n):
        """Get hardware channel number for channel n. n starts at 0"""
        return n + self.ch_index_zero


    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # do not check for error if close was called with an error
        try:
            # clear old waveforms
            self.AWG.waveformFlush()
            for n in range(self.nCh):
                self.AWG.AWGflush(self.getHwCh(n))
                self.AWG.AWGstop(self.getHwCh(n))
            # turn off outputs
            for n in range(self.nCh):
                self.AWG.channelWaveShape(self.getHwCh(n), -1)
            # close instrument
            self.AWG.close()
            self.HVI.stop()
            self.HVI.close()
        except:
            # never return error here
            pass


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        if self.isFirstCall(options):
            self.lWaveUpdated = [False]*self.nCh
            if self.isHardwareTrig(options):
                # Stop all channels
                self.AWG.AWGstopMultiple(int(2**self.nCh - 1))
        # start with setting current quant value
        quant.setValue(value)
        # check if channel-specific, if so get channel + name
        if quant.name.startswith('Ch') and len(quant.name)>6:
            ch = int(quant.name[2]) - 1
            name = quant.name[6:]
        elif quant.name.startswith('AWG') and len(quant.name)>7:
            ch = int(quant.name[3]) - 1
            name = quant.name[7:]
        else:
            ch, name = None, ''
        # proceed depending on command
        if quant.name in ('Trig I/O',):
            # get direction and sync from index of comboboxes
            direction = int(self.getCmdStringFromValue('Trig I/O'))
            self.AWG.triggerIOconfig(direction)
        elif quant.name in ('External Trig Source', 'External Trig Config',
                            'Trig Sync Mode') or\
                   name in ('External Trig Source', 'External Trig Config'):
            sync = int(self.getCmdStringFromValue('Trig Sync Mode'))
            for ch in range(self.nCh):
                # check if separate trigger is used
                if self.getValue('Ch%d - Separate trigger' % (ch + 1)):
                    # use unique trigger for this channel
                    extSource = int(self.getCmdStringFromValue('Ch%d - External Trig Source' % (ch + 1)))
                    trigBehavior = int(self.getCmdStringFromValue('Ch%d - External Trig Config' % (ch + 1)))
                else:
                    # use default
                    extSource = int(self.getCmdStringFromValue('External Trig Source'))
                    trigBehavior = int(self.getCmdStringFromValue('External Trig Config'))
                self.AWG.AWGtriggerExternalConfig(self.getHwCh(ch), extSource, trigBehavior, sync)
        # software trig for all channels
        elif quant.name in ('Trig All',):
            # mask to trig all AWG channels
            nMask = int(2**self.nCh - 1)
            self.AWG.AWGtriggerMultiple(nMask)
        elif quant.name == 'Run':
            for n in range(self.nCh):
                self.AWG.AWGqueueConfig(self.getHwCh(n), 1)
            # TODO: only for enabled channels
            self.AWG.AWGstartMultiple(self.getEnabledChannelsMask())
        elif quant.name in ('Generate internal trigger', 'Internal trigger time'):
            if self.getValue('Generate internal trigger'):
                self.HVI.stop()
                # Update and start HVI
                wait = round(self.getValue('Internal trigger time')/10e-9)-11 #110ns delay in HVI
                self.HVI.writeIntegerConstantWithIndex(0, 'Wait time', wait)
                self.HVI.compile()
                self.HVI.load()
                self.HVI.start()

        elif name in ('Function', 'Enabled'):
            if self.getValue('Ch%d - Enabled' % (ch + 1)):
                func = int(self.getCmdStringFromValue('Ch%d - Function' % (ch + 1)))
                # start AWG if AWG mode
                if func == 6:
                    self.lWaveUpdated[ch] = True
            else:
                func = -1
                self.AWG.AWGstop(self.getHwCh(ch))
            self.AWG.channelWaveShape(self.getHwCh(ch), func)
        elif name == 'Amplitude':
            self.AWG.channelAmplitude(self.getHwCh(ch), value)
            # if in AWG mode, update waveform to scale to new range
            if self.getValue('Ch%d - Function' % (ch + 1)) == 'AWG':
                self.lWaveUpdated[ch] = True
        elif name == 'Frequency':
            self.AWG.channelFrequency(self.getHwCh(ch), value)
        elif name == 'Phase':
            self.AWG.channelPhase(self.getHwCh(ch), value)
        elif name == 'Offset':
            self.AWG.channelOffset(self.getHwCh(ch), value)
        elif name == 'Trig':
            self.AWG.AWGtrigger(self.getHwCh(ch))
        elif name in ('Trig mode', 'Cycles', 'Waveform'):
            # mark wavefom as updated
            self.lWaveUpdated[ch] = True
        # if final call and wave is updated, send it to AWG
        if self.isFinalCall(options):
            # check if any wave is updated (needed since we flush all)
            self.log(self.lWaveUpdated)
            for n, updated in enumerate(self.lWaveUpdated):
                if updated:
                    (seq_no, n_seq) = self.getHardwareLoopIndex(options)
                    if seq_no == 0:
                        self.log("Flush")
                        self.AWG.AWGflush(self.getHwCh(n))
                    seq_no = None if n_seq == 0 else seq_no
                    # update waveforms
                    self.sendWaveform(n, seq_no, n_seq)

            # Configure markers
            for n in range(self.nCh):
                # conversion to front panel numbering
                N = n + 1 
                markerMode = int(self.getCmdStringFromValue('Ch%d - Marker Mode' % N))
                trgPXImask = 0
                trgIOmask = 1 if self.getValue('Ch%d - Marker External' % N) else 0
                markerValue = int(self.getCmdStringFromValue('Ch%d - Marker Value' % N))
                syncMode = int(self.getCmdStringFromValue('Ch%d - Marker Sync Mode' % N))
                length = int(round(self.getValue('Ch%d - Marker Length' % N)/10e-9))
                delay = int(round(self.getValue('Ch%d - Marker Delay' % N)/10e-9))
                if length == 0:
                    length = 1
                for i in range(8):
                    if self.getValue('Ch%d - Marker PXI%d' % (N, i)):
                        trgPXImask += 2**i
                self.AWG.AWGqueueMarkerConfig(nAWG=self.getHwCh(n), markerMode=markerMode, 
                                              trgPXImask=int(trgPXImask), trgIOmask=int(trgIOmask), 
                                              value=markerValue, syncMode=syncMode, length=length,
                                              delay=delay)
            # turn on outputs
            if not self.isHardwareTrig(options):
                for n in range(self.nCh):
                    self.AWG.AWGqueueConfig(self.getHwCh(n), 1)
                self.AWG.AWGstartMultiple(self.getEnabledChannelsMask())
        return value

    def getEnabledChannelsMask(self):
        mask = 0
        for ch in range(self.nCh):
            if self.getValue('Ch%d - Enabled' % (ch + 1)):
                        func = int(self.getCmdStringFromValue('Ch%d - Function' % (ch + 1)))
                        # start AWG if AWG mode
                        if func == 6:
                            mask += 2**ch
        return int(mask)

    def sendWaveform(self, ch, seq_no=None, n_seq=0):
        """Send waveform to AWG channel"""
        # conversion to front panel numbering
        nCh = ch + 1
        
        trigMode = int(self.getCmdStringFromValue('AWG%d - Trig mode' % nCh))
        delay = int(0)

        if seq_no is None:
            seq_no = 0
            if self.getValue('AWG%d - Trig mode' % nCh) in ('Software', 'External'):
                cycles = int(self.getValue('AWG%d - Cycles' % nCh))
            else:
                cycles = int(0)
        else:
            # Ignore cycle setting if hardware looping
            cycles = 1
        prescaler = int(0)
        waveformType = int(0)
        quant = self.getQuantity('AWG%d - Waveform' % nCh)
        data = quant.getValueArray()
        # make sure we have at least 256 elements (limit might be 236)
        if len(data)<256:
            data = np.pad(data, (0, 256-len(data)), 'constant')
        # scale to range
        amp =  self.getValue('Ch%d - Amplitude' % nCh)
        dataNorm = data / amp
        dataNorm = np.clip(dataNorm, -1.0, 1.0, out=dataNorm)
        
        n = self.uploadWaveform(ch, dataNorm, waveformType, seq_no)
        self.AWG.AWGqueueWaveform(self.getHwCh(ch), n, trigMode, delay, cycles, prescaler)

        if trigMode == 0:
            # If internally triggerd, get rep rate and calculate delay
            delay = int(6.5e3)
            rep_rate = 1e3
            zero_pad_length = round(1/(rep_rate*self.dt))-len(dataNorm)
            zero_pad = np.zeros(256)
            n_zero_pad = round(zero_pad_length//len(zero_pad)) - 1
            n_zero_pad_reminder = zero_pad_length % len(zero_pad) + len(zero_pad)
            zero_pad_reminder = np.zeros(n_zero_pad_reminder)

            self.log(zero_pad_length)
            self.log(n_zero_pad)
            self.log(n_zero_pad_reminder)
            # Upload the zero padded waveform with a unique ID (n_seq+1)
            if n_zero_pad > 0:
                n = self.uploadWaveform(ch, zero_pad, waveformType, n_seq+1)
                self.AWG.AWGqueueWaveform(self.getHwCh(ch), n, trigMode, 0, n_zero_pad, prescaler)
            n = self.uploadWaveform(ch, zero_pad_reminder, waveformType, n_seq+2)
            self.AWG.AWGqueueWaveform(self.getHwCh(ch), n, trigMode, 0, 1, prescaler)

    def uploadWaveform(self, ch, data, waveformType, seq=0):
        n = self.getWaveformId(ch, seq)
        wave = keysightSD1.SD_Wave()
        wave.newFromArrayDouble(waveformType, data)
        self.AWG.waveformLoad(wave, n)
        return n

    def getWaveformId(self, ch, seq):
        # Create a unique waveform number using Szudzik's pairing method
        if ch >= seq:
            n = ch*ch+ch*seq
        else:
            n = ch+seq*seq
        return n


if __name__ == '__main__':
    pass
