#!/usr/bin/env python
import sys
sys.path.append('C:\Program Files (x86)\Keysight\SD1\Libraries\Python')

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
        self.AWG = keysightSD1.SD_AOU()
        AWGPart = self.AWG.getProductNameBySlot(1, int(self.comCfg.address))
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
        self.AWG.openWithSlot(AWGPart, 1, int(self.comCfg.address))
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
        for ch in range(self.nCh):
            self.AWG.AWGflush(self.get_hw_ch(ch))


    def get_hw_ch(self, n):
        """Get hardware channel number for channel n. n starts at 0"""
        return n + self.ch_index_zero


    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # do not check for error if close was called with an error
        try:
            # clear old waveforms
            self.AWG.waveformFlush()
            for n in range(self.nCh):
                self.AWG.AWGflush(self.get_hw_ch(n))
                self.AWG.AWGstop(self.get_hw_ch(n))
            # turn off outputs
            for n in range(self.nCh):
                self.AWG.channelWaveShape(self.get_hw_ch(n), -1)
            # close instrument
            self.AWG.close()
        except:
            # never return error here
            pass


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        if self.isFirstCall(options):
            self.lWaveUpdated = [False]*self.nCh
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
                self.AWG.AWGtriggerExternalConfig(self.get_hw_ch(ch), extSource, trigBehavior, sync)
        # 
        # software trig for all channels
        elif quant.name in ('Trig All',):
            # mask to trig all AWG channels
            nMask = int(2**self.nCh - 1)
            self.AWG.AWGtriggerMultiple(nMask)
        # 
        elif name in ('Function', 'Enabled'):
            if self.getValue('Ch%d - Enabled' % (ch + 1)):
                func = int(self.getCmdStringFromValue('Ch%d - Function' % (ch + 1)))
                # start AWG if AWG mode
                if func == 6:
                    self.lWaveUpdated[ch] = True
            else:
                func = -1
                self.AWG.AWGstop(self.get_hw_ch(ch))
            self.AWG.channelWaveShape(self.get_hw_ch(ch), func)
        elif name == 'Amplitude':
            self.AWG.channelAmplitude(self.get_hw_ch(ch), value)
            # if in AWG mode, update waveform to scale to new range
            if self.getValue('Ch%d - Function' % (ch + 1)) == 'AWG':
                self.lWaveUpdated[ch] = True
        elif name == 'Frequency':
            self.AWG.channelFrequency(self.get_hw_ch(ch), value)
        elif name == 'Phase':
            self.AWG.channelPhase(self.get_hw_ch(ch), value)
        elif name == 'Offset':
            self.AWG.channelOffset(self.get_hw_ch(ch), value)
#        elif name == 'Run mode':
#            if value:
#                self.AWG.AWGstart(ch)
#            else:
#                self.AWG.AWGstop(ch)
        elif name == 'Trig':
            self.AWG.AWGtrigger(self.get_hw_ch(ch))
        elif name in ('Trig mode', 'Cycles'):
            # mark wavefom as updated
            self.lWaveUpdated[ch] = True
        elif name == 'Waveform':
            # mark wavefom as updated
            self.lWaveUpdated[ch] = True
        # if final call and wave is updated, send it to AWG
        if self.isFinalCall(options):
            # check if any wave is updated (needed since we flush all)
            if np.any(self.lWaveUpdated):
                # always update all, since we need to flush waveforms to clear mem
                self.lWaveUpdated = [True]*self.nCh
                # find updated channels, turn off output
                iChMask = 0
                lCh = []
                for n, update in enumerate(self.lWaveUpdated):
                    if update:
                        iChMask += 2**n
                        lCh.append(n)
                        self.AWG.AWGstop(self.get_hw_ch(n))
                        self.AWG.AWGflush(self.get_hw_ch(n))
                # clear old waveforms
                self.AWG.waveformFlush()
                # - todo: implement smarter waveform delete/upload
                # update waveforms
                for n in lCh:
                    self.sendWaveform(n)
                # turn on outputs
                self.AWG.AWGstartMultiple(iChMask)
        return value


    def sendWaveform(self, ch):
        """Send waveform to AWG channel"""
        # conversion to front panel numbering
        nCh = ch + 1
        # get trigger mode
        trigMode = int(self.getCmdStringFromValue('AWG%d - Trig mode' % nCh))
        delay = int(0)
        if self.getValue('AWG%d - Trig mode' % nCh) in ('Software', 'External'):
            cycles = int(self.getValue('AWG%d - Cycles' % nCh))
        else:
            cycles = int(0)
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
        # output waveform
        self.AWG.AWGfromArray(self.get_hw_ch(ch), trigMode, delay, cycles, prescaler, 
                              waveformType, dataNorm)
        


if __name__ == '__main__':
    pass
