#!/usr/bin/env python
import sys
from BaseDriver import LabberDriver, Error, IdError
import numpy as np
import os
sys.path.append('C:\Program Files (x86)\Keysight\SD1\Libraries\Python')
import keysightSD1


class Driver(LabberDriver):
    """Keysigh PXI AWG"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # timeout
        self.timeout_ms = int(1000 * self.dComCfg['Timeout'])
        # get PXI chassis
        self.chassis = int(self.dComCfg.get('PXI chassis', 1))
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
        for validId, validName in zip(dOptionCfg['model_id'],
                                      dOptionCfg['model_str']):
            if AWGPart.find(validId) >= 0:
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
        elif validName == 'M3302':
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

        # clear old waveforms
        self.AWG.waveformFlush()

        # Create and open HVI for internal triggering
        self.HVI = keysightSD1.SD_HVI()
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.HVI.open(os.path.join(dir_path, 'InternalTrigger.HVI'))
        self.HVI.assignHardwareWithIndexAndSlot(0, self.chassis,
                                                int(self.comCfg.address))

    def getHwCh(self, n):
        """Get hardware channel number for channel n. n starts at 0"""
        return n + self.ch_index_zero

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # do not check for error if close was called with an error
        try:
            # clear old waveforms and stop awg
            self.AWG.waveformFlush()
            for ch in range(self.nCh):
                self.AWG.AWGflush(self.getHwCh(ch))
                self.AWG.AWGstop(self.getHwCh(ch))
                self.AWG.channelWaveShape(self.getHwCh(ch), -1)
                
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
            # Stop all channels
            self.AWG.AWGstopMultiple(int(2**self.nCh - 1))
        # start with setting current quant value
        quant.setValue(value)
        # check if channel-specific, if so get channel + name
        if quant.name.startswith('Ch') and len(quant.name) > 6:
            ch = int(quant.name[2]) - 1
            name = quant.name[6:]
        else:
            ch, name = None, ''
        # proceed depending on command
        if quant.name in ('Trig I/O',):
            # get direction and sync from index of comboboxes
            direction = int(self.getCmdStringFromValue('Trig I/O'))
            self.AWG.triggerIOconfig(direction)
        elif quant.name == 'Run':
            self.AWG.AWGstartMultiple(self.getEnabledChannelsMask())
        elif quant.name in ('Generate internal trigger',
                            'Internal trigger time'):
            if self.getValue('Generate internal trigger'):
                self.HVI.stop()
                # Update and start HVI
                # 110ns delay in HVI
                wait = round(self.getValue('Internal trigger time')/10e-9)-11
                self.HVI.writeIntegerConstantWithIndex(0, 'Wait time', wait)
                self.HVI.compile()
                self.HVI.load()
                self.HVI.start()

        elif name in ('Function', 'Enabled'):
            if self.getChannelValue(ch, 'Enabled'):
                func = int(self.getChannelCmd(ch, 'Function'))
                # set channel as updated if AWG mode
                if func == 6:
                    self.lWaveUpdated[ch] = True
            else:
                func = -1
                self.AWG.AWGstop(self.getHwCh(ch))
            self.AWG.channelWaveShape(self.getHwCh(ch), func)
        elif name == 'Amplitude':
            self.AWG.channelAmplitude(self.getHwCh(ch), value)
            # if in AWG mode, update waveform to scale to new range
            if self.getChannelValue(ch, 'Function') == 'AWG':
                self.lWaveUpdated[ch] = True
        elif name == 'Frequency':
            self.AWG.channelFrequency(self.getHwCh(ch), value)
        elif name == 'Phase':
            self.AWG.channelPhase(self.getHwCh(ch), value)
        elif name == 'Offset':
            self.AWG.channelOffset(self.getHwCh(ch), value)
        elif name in ('Trig mode', 'Cycles', 'Waveform'):
            # mark wavefom as updated, so that it gets re-uploaded
            self.lWaveUpdated[ch] = True
        elif name in ('External Trig Source', 'External Trig Config'):
            sync = int(self.getCmdStringFromValue('Trig Sync Mode'))
            for ch in range(self.nCh):
                # check if external trigger is used
                if self.getChannelValue(ch, 'Trig mode') in ('External', 'Software'):
                    extSource = int(self.getChannelCmd(ch, 'External Trig Source'))
                    trigBehavior = int(self.getChannelCmd(ch, 'External Trig Config'))
                    self.AWG.AWGtriggerExternalConfig(self.getHwCh(ch),
                                                      extSource,
                                                      trigBehavior,
                                                      sync)
        # For effiency, we only upload the waveform at the final call
        if self.isFinalCall(options):
            seq_no, n_seq = self.getHardwareLoopIndex(options)
            if np.any(self.lWaveUpdated):
                # Reset waveform ID counter if this is the first sequence
                if seq_no == 0:
                    self.i = 1  # WaveformID counter
                    self.AWG.waveformFlush()

            for ch, updated in enumerate(self.lWaveUpdated):
                if updated:
                    if seq_no == 0:
                        # Flush the AWG memory if this is the first sequence
                        self.AWG.AWGflush(self.getHwCh(ch))
                    if self.isHardwareLoop(options):
                        self.reportStatus('Sending waveform (%d/%d)'
                                          % (seq_no+1, n_seq))
                    self.sendWaveform(ch, self.i)
                    self.i += 1


            # Configure channel specific markers
            for ch in range(self.nCh):
                markerMode = int(self.getChannelCmd(ch, 'Marker Mode'))
                trgPXImask = 0
                trgIOmask = 1 if self.getChannelValue(ch, 'Marker External') else 0
                markerValue = int(self.getChannelCmd(ch, 'Marker Value'))
                syncMode = int(self.getChannelCmd(ch, 'Marker Sync Mode'))
                length = int(round(self.getChannelValue(ch, 'Marker Length')/10e-9))
                delay = int(round(self.getChannelValue(ch, 'Marker Delay')/10e-9))

                for i in range(8):
                    if self.getChannelValue(ch, 'Marker PXI%d' % i):
                        trgPXImask += 2**i
                self.AWG.AWGqueueMarkerConfig(nAWG=self.getHwCh(ch),
                                              markerMode=markerMode,
                                              trgPXImask=trgPXImask,
                                              trgIOmask=trgIOmask,
                                              value=markerValue,
                                              syncMode=syncMode,
                                              length=length,
                                              delay=delay)
                self.AWG.AWGqueueConfig(self.getHwCh(ch), 1) # Cyclic mode

            # In hardware trigger mode, outputs are turned on by the run button
            if not self.isHardwareTrig(options):
                self.AWG.AWGstartMultiple(self.getEnabledChannelsMask())
        return value

    def performArm(self, quant_names, options={}):
        """Perform the instrument arm operation"""
        # Stop all channels
        self.AWG.AWGstopMultiple(int(2**self.nCh - 1))

    def getEnabledChannelsMask(self):
        """ Returns a mask for the enabled channels """
        mask = 0
        for ch in range(self.nCh):
            if self.getValue('Ch%d - Enabled' % (ch + 1)):
                        func = int(self.getChannelCmd(ch, 'Function'))
                        # start AWG if AWG mode
                        if func == 6:
                            mask += 2**ch
        return int(mask)

    def sendWaveform(self, ch, i):
        """Send waveform to AWG channel"""

        trigMode = int(self.getChannelCmd(ch, 'Trig mode'))
        delay = int(0)

       
        if self.getChannelValue(ch, 'Trig mode') in ('Software',
                                                     'External'):
            cycles = int(self.getChannelValue(ch, 'Cycles'))
        else:
            cycles = 1

        prescaler = 0
        waveformType = 0
        quant = self.getQuantity('Ch%d - Waveform' % (ch+1))
        data = quant.getValueArray()
        # make sure we have at least 30 elements
        if len(data) < 30:
            data = np.pad(data, (0, 30-len(data)), 'constant')
        # granularity of the awg is 10
        if len(data) % 10 > 0:
            data = np.pad(data, (0, 10-(len(data) % 10)), 'constant')
        # scale to range
        amp = self.getChannelValue(ch, 'Amplitude')
        dataNorm = data / amp
        dataNorm = np.clip(dataNorm, -1.0, 1.0, out=dataNorm)

        self.uploadWaveform(dataNorm, waveformType, i)
        self.AWG.AWGqueueWaveform(self.getHwCh(ch), i, trigMode, delay,
                                  cycles, prescaler)

    def uploadWaveform(self, data, waveformType, i):
        """ Uploads the given waveform with an id i """
        wave = keysightSD1.SD_Wave()
        wave.newFromArrayDouble(waveformType, data)
        self.AWG.waveformLoad(wave, i)

    def getChannelValue(self, ch, value):
        """ Returns a channel specific value """
        return self.getValue('Ch{} - {}'.format(ch+1, value))

    def getChannelCmd(self, ch, value):
        """ Returns a channel specific command string """
        return self.getCmdStringFromValue('Ch{} - {}'.format(ch+1, value))


if __name__ == '__main__':
    pass
