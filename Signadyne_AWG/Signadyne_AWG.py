#!/usr/bin/env python

import InstrumentDriver
import signadyne

import numpy as np

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements a Signadyne file handler"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # timeout
        self.timeout_ms = int(1000 * self.dComCfg['Timeout'])
        # create AWG instance
        self.AWG = signadyne.SD_AOU()
        AWGPart = self.AWG.getProductNameBySlot(1, int(self.comCfg.address))
        if not isinstance(AWGPart, (str, unicode)):
            raise InstrumentDriver.Error('Unit not available')
        # check that model is supported
        dOptionCfg = self.dInstrCfg['options']
        for validId, validName in zip(dOptionCfg['model_id'], dOptionCfg['model_str']):
            if AWGPart.find(validId)>=0:
                # id found, stop searching
                break
        else:
            # loop fell through, raise ID error
            raise InstrumentDriver.IdError(AWGPart, dOptionCfg['model_id'])
        # set model
        self.setModel(validName)
        self.AWG.openWithSlot(AWGPart, 1, int(self.comCfg.address))
        # keep track of if waveform was updated
        self.nCh = 4
        self.lWaveUpdated = [False]*self.nCh
        # clear old waveforms
        self.AWG.waveformFlush()
        for ch in range(self.nCh):
            self.AWG.AWGflush(ch)


    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # do not check for error if close was called with an error
        try:
            # clear old waveforms
            self.AWG.waveformFlush()
            for ch in range(self.nCh):
                self.AWG.AWGflush(ch)
                self.AWG.AWGstop(ch)
            # turn off outputs
            for n in range(self.nCh):
                self.AWG.channelWaveShape(n, -1)
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
            ch = int(quant.name[2])
            name = quant.name[6:]
        elif quant.name.startswith('AWG') and len(quant.name)>7:
            ch = int(quant.name[3])
            name = quant.name[7:]
        else:
            ch, name = None, ''
        # proceed depending on command
        if quant.name in ('Trig I/O', 'Trig Sampling Mode'):
            # get direction and sync from index of comboboxes
            direction = int(self.getCmdStringFromValue('Trig I/O'))
            sync = int(self.getCmdStringFromValue('Trig Sampling Mode'))
            self.AWG.triggerIOconfig(direction, sync)
        elif quant.name in ('External Trig Source', 'External Trig Config') or\
                   name in ('External Trig Source', 'External Trig Config'):
            for ch in range(self.nCh):
                # check if separate trigger is used
                if self.getValue('Ch%d - Separate trigger' % ch):
                    # use unique trigger for this channel
                    extSource = int(self.getCmdStringFromValue('Ch%d - External Trig Source' % ch))
                    trigBehavior = int(self.getCmdStringFromValue('Ch%d - External Trig Config' % ch))
                else:
                    # use default
                    extSource = int(self.getCmdStringFromValue('External Trig Source'))
                    trigBehavior = int(self.getCmdStringFromValue('External Trig Config'))
                self.AWG.AWGtriggerExternalConfig(ch, extSource, trigBehavior)
        elif name in ('Function', 'Enabled'):
            if self.getValue('Ch%d - Enabled' % ch):
                func = int(self.getCmdStringFromValue('Ch%d - Function' % ch))
                # start AWG if AWG mode
                if func == 6:
                    self.lWaveUpdated[ch] = True
            else:
                func = -1
                self.AWG.AWGstop(ch)
            self.AWG.channelWaveShape(ch, func)
        elif name == 'Amplitude':
            self.AWG.channelAmplitude(ch, value)
            # if in AWG mode, update waveform to scale to new range
            if self.getValue('Ch%d - Function' % ch) == 'AWG':
                self.lWaveUpdated[ch] = True
        elif name == 'Frequency':
            self.AWG.channelFrequency(ch, value)
        elif name == 'Phase':
            self.AWG.channelPhase(ch, value)
        elif name == 'Offset':
            self.AWG.channelOffset(ch, value)
#        elif name == 'Run mode':
#            if value:
#                self.AWG.AWGstart(ch)
#            else:
#                self.AWG.AWGstop(ch)
        elif name == 'Trig':
            self.AWG.AWGtrigger(ch)
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
                for ch, update in enumerate(self.lWaveUpdated):
                    if update:
                        iChMask += 2**ch
                        lCh.append(ch)
                        self.AWG.AWGstop(ch)
                        self.AWG.AWGflush(ch)
                # clear old waveforms
                self.AWG.waveformFlush()
                # - todo: implement smarter waveform delete/upload
                # update waveforms
                for ch in lCh:
                    self.sendWaveform(ch)
                # turn on outputs
                self.AWG.AWGstartMultiple(iChMask)
        return value

    def sendWaveform(self, nCh):
        """Send waveform to AWG channel"""
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
        self.AWG.AWGfromArray(nCh, trigMode, delay, cycles, prescaler, 
                              waveformType, dataNorm)
        


if __name__ == '__main__':
	pass
