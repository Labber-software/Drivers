#!/usr/bin/env python
import sys
from BaseDriver import LabberDriver, Error, IdError
import numpy as np
sys.path.append('C:\\Program Files (x86)\\Keysight\\SD1\\Libraries\\Python')
import keysightSD1


class UploadFailed(Error):
    """Handling AWG out-of-memory exception"""
    pass

class Driver(LabberDriver):
    """Keysigh PXI AWG"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # add compatibility with pre-1.5.4 version of Labber
        if not hasattr(self, 'getTrigChannel'):
            self.getTrigChannel = self._getTrigChannel
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
        self.waveform_updated = [False] * self.nCh
        self.previous_upload = dict()
        self.waveform_sizes = dict()

        # get hardware version - changes numbering of channels
        hw_version = self.AWG.getHardwareVersion()
        if hw_version >= 4:
            # KEYSIGHT - channel numbers start with 1
            self.ch_index_zero = 1
        else:
            # SIGNADYNE - channel numbers start with 0
            self.ch_index_zero = 0

        # clear old waveforms
        self.clearOldWaveforms()


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
                self.AWG.AWGstop(self.getHwCh(ch))
                self.AWG.AWGflush(self.getHwCh(ch))
                self.AWG.channelWaveShape(self.getHwCh(ch), -1)

            # close instrument
            self.AWG.close()
        except Exception:
            # never return error here
            pass


    def initSetConfig(self):
        """This function is run before setting values in Set Config"""
        # clear AWG memory
        self.clearOldWaveforms()
        # clear waveforms
        for n in range(self.nCh):
            self.setValue('Ch%d - Waveform' % (n + 1), [])


    def performArm(self, quant_names, options={}):
        """Perform the instrument arm operation"""
        # restart AWG to make sure queue is at first element
        channel_mask = self.getEnabledChannelsMask()
        self.AWG.AWGstopMultiple(channel_mask)
        # don't start AWG if trig channel is "Run", which will start it later
        if self.getTrigChannel(options) != 'Run':
            self.AWG.AWGstartMultiple(channel_mask)
        # wait a ms to allow AWG to start
        self.wait(0.001)


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        if self.isFirstCall(options):
            self.waveform_updated = [False] * self.nCh
        # set current value, necessary since we later use getValue to get config
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
            # start if value is True or not given, else stop
            if value is None or value:
                self.AWG.AWGstartMultiple(self.getEnabledChannelsMask())
            else:
                self.AWG.AWGstopMultiple(self.getEnabledChannelsMask())

        elif quant.name in ('Trig All',):
            if value:
                # mask to trig all AWG channels
                nMask = int(2**self.nCh - 1)
                self.AWG.AWGtriggerMultiple(nMask)

        elif quant.name in ('Trig delay', 'Delay after end',
                            'Waveform alignment'):
            # TODO doesn't strictly require re-uploading, just re-queue
            self.waveform_updated = [True] * self.nCh

        elif name in ('Function', 'Enabled'):
            if self.getChannelValue(ch, 'Enabled'):
                func = int(self.getChannelCmd(ch, 'Function'))
                # set channel as updated if AWG mode
                if func == 6:
                    self.waveform_updated[ch] = True
            else:
                func = -1
                self.AWG.AWGstop(self.getHwCh(ch))
            # turn off amplitude if in DC mode
            if self.getChannelValue(ch, 'Function') == 'DC':
                self.sendValueToOther('Ch%d - Amplitude' % (ch + 1), 0.0)

            self.AWG.channelWaveShape(self.getHwCh(ch), func)

        elif name == 'Amplitude':
            self.AWG.channelAmplitude(self.getHwCh(ch), value)
            # if in AWG mode, update waveform to scale to new range
            if self.getChannelValue(ch, 'Function') == 'AWG':
                self.waveform_updated[ch] = True

        elif name == 'Frequency':
            self.AWG.channelFrequency(self.getHwCh(ch), value)

        elif name == 'Phase':
            self.AWG.channelPhase(self.getHwCh(ch), value)

        elif name == 'Offset':
            self.AWG.channelOffset(self.getHwCh(ch), value)

        elif name in ('Trig mode', 'Cycles', 'Waveform'):
            # mark waveform as updated, so that it gets re-uploaded
            self.waveform_updated[ch] = True

        elif name.startswith('Marker'):
            # marker changed, wavefom needs to be re-uploaded
            self.waveform_updated[ch] = True

        elif name in ('External Trig Source', 'External Trig Config'):
            # configure external trigger mdde
            self.configureExternalTrigger(ch)

        elif quant.name == 'Trig Sync Mode':
            # re-configure triggers for all channels
            for ch in range(self.nCh):
                self.configureExternalTrigger(ch)

        # For effiency, we only upload the waveform at the final call
        if self.isFinalCall(options) and np.any(self.waveform_updated):
            # get list of AWG channels in use
            awg_channels = self.getAWGChannelsInUse()

            # do different uploading depending on normal or hardware loop
            if self.isHardwareLoop(options):
                seq_no, n_seq = self.getHardwareLoopIndex(options)
                # Reset waveform ID counter if this is the first sequence
                if seq_no == 0:
                    self.waveform_counter = 0  # WaveformID counter
                    self.clearOldWaveforms()
                # report status
                self.reportStatus(
                    'Sending waveform (%d/%d)' % (seq_no + 1, n_seq))

                # always upload all channels in use, regardless of updated
                for ch in awg_channels:
                    # waveform counter is unique id
                    self.waveform_counter += 1
                    self.sendWaveform(ch, self.waveform_counter)
                    self.queueWaveform(ch, self.waveform_counter)
                    # configure channel-specific markers
                    self.configureMarker(ch)
                    # configure queue to run in cyclic mode
                    self.AWG.AWGqueueConfig(self.getHwCh(ch), 1)

            else:
                # standard, non-hardware loop upload, stop all
                self.AWG.AWGstopMultiple(self.getEnabledChannelsMask())
                # try to upload and queue
                try:
                    self.uploadAndQueueWaveforms()
                except UploadFailed:
                    # if upload fail, flush and try again (may be out of memory)
                    self.log('Upload failed, flushing old waveforms!')
                    self.clearOldWaveforms()
                    self.uploadAndQueueWaveforms()

                # don't start AWG if hardware trig, will be done when arming
                if not self.isHardwareTrig(options):
                    self.AWG.AWGstartMultiple(self.getEnabledChannelsMask())

        return value


    def configureExternalTrigger(self, ch):
        """Configure external trig for given channel"""
        # get parameters
        extSource = int(self.getChannelCmd(ch, 'External Trig Source'))
        trigBehavior = int(self.getChannelCmd(ch, 'External Trig Config'))
        sync = int(self.getCmdStringFromValue('Trig Sync Mode'))
        self.AWG.AWGtriggerExternalConfig(
            self.getHwCh(ch), extSource, trigBehavior, sync)


    def clearOldWaveforms(self):
        """Flush AWG queue and remove all cached waveforms"""
        self.AWG.waveformFlush()
        self.previous_upload = {(n + 1): np.array([]) for n in range(self.nCh)}
        self.waveform_sizes = dict()
        # waveform zero is a 50 us empty waveform used for delays
        waveform_id = 0
        data_zero = np.zeros(int(round(50E-6 / self.dt)))
        wave = keysightSD1.SD_Wave()
        wave.newFromArrayDouble(0, data_zero)
        self.AWG.waveformLoad(wave, waveform_id)
        # update cached parameters
        self.previous_upload[waveform_id] = data_zero
        self.waveform_sizes[waveform_id] = len(data_zero)


    def uploadAndQueueWaveforms(self):
        """Upload and queue waveforms for all channels in use"""
        awg_channels = self.getAWGChannelsInUse()
        # waveform memory is shared by all channels, use counter to increment
        waveform_counter = 0

        for ch in awg_channels:
            # flush queue
            self.AWG.AWGflush(self.getHwCh(ch))

            # check data dimensions
            data = self.getValueArray('Ch%d - Waveform' % (ch + 1))
            self.log('Data shape', data.shape)
            if len(data.shape) == 1:
                # single traces, upload and queue
                waveform_counter += 1
                self.sendWaveform(ch, waveform_counter)
                self.queueWaveform(ch, waveform_counter)
            else:
                # 2D data, upload and queue traces by trace
                for n in range(data.shape[0]):
                    waveform_counter += 1
                    self.sendWaveform(ch, waveform_counter, data[n])
                    self.queueWaveform(ch, waveform_counter)

            # configure channel-specific markers
            self.configureMarker(ch)
            # configure queue to run in cyclic mode
            self.AWG.AWGqueueConfig(self.getHwCh(ch), 1)


    def getAWGChannelsInUse(self):
        """Get list with all AWG channels in use"""
        awg_channels = []
        for ch in range(self.nCh):
            if (self.getChannelValue(ch, 'Enabled') and
                    self.getChannelValue(ch, 'Function') == 'AWG'):
                awg_channels.append(ch)
        return awg_channels


    def getEnabledChannelsMask(self):
        """ Returns a mask for the enabled channels """
        mask = 0
        for ch in self.getAWGChannelsInUse():
            mask += 2**ch
        return int(mask)


    def sendWaveform(self, ch, waveform_id, data=None):
        """Send waveform to AWG channel"""
        # get data from channel, if not available
        if data is None:
            data = self.getValueArray('Ch%d - Waveform' % (ch + 1))
        # make sure we have at least 30 elements
        if len(data) < 30:
            # pad start or end, depending on trig alignment
            if self.getValue('Waveform alignment') == 'Start at trig':
                data = np.pad(data, (0, 30 - len(data)), 'constant')
            else:
                data = np.pad(data, (30 - len(data), 0), 'constant')
        # granularity of the awg is 10
        if len(data) % 10 > 0:
            # pad start or end, depending on trig alignment
            if self.getValue('Waveform alignment') == 'Start at trig':
                data = np.pad(data, (0, 10 - (len(data) % 10)), 'constant')
            else:
                data = np.pad(data, (10 - (len(data) % 10), 0), 'constant')
        # scale to range
        amp = self.getChannelValue(ch, 'Amplitude')
        data_norm = data / amp
        data_norm = np.clip(data_norm, -1.0, 1.0, out=data_norm)

        # check if data changed compared to last upload
        if waveform_id in self.previous_upload:
            if np.array_equal(data_norm, self.previous_upload[waveform_id]):
                # data has not changed, no need to upload
                return
            # data has changed, update previous value. note: this only happens
            # for pre-defined waveform_id 1-4, to avoid caching hw looping data
            self.previous_upload[waveform_id] = data_norm
        # keep track of waveform lengths
        self.waveform_sizes[waveform_id] = len(data_norm)

        # upload waveform
        wave = keysightSD1.SD_Wave()
        waveformType = 0
        wave.newFromArrayDouble(waveformType, data_norm)
        ret = self.AWG.waveformLoad(wave, waveform_id)
        if ret < 0:
            self.log('Upload error:', keysightSD1.SD_Error.getErrorMessage(ret))
            raise UploadFailed()


    def queueWaveform(self, ch, waveform_id):
        """Queue waveform to AWG channel"""
        # get trig parameters
        trigMode = int(self.getChannelCmd(ch, 'Trig mode'))
        if self.getChannelValue(ch, 'Trig mode') in ('Software / HVI',
                                                     'External'):
            cycles = int(self.getChannelValue(ch, 'Cycles'))
        else:
            cycles = 1
        prescaler = 0
        delay = int(round(self.getValue('Trig delay') / 10E-9))
        # if aligning waveform to end of trig, adjust delay
        if self.getValue('Waveform alignment') == 'End at trig':
            delay -= round(self.waveform_sizes[waveform_id] * self.dt / 10E-9)
            # add extra after waveform ends
            delay -= int(round(self.getValue('Delay after end') / 10E-9))
            # raise error if delay is negative
            if delay < 0:
                raise Error('"Trig delay" must be larger than waveform length')

        # if delay is longer than 50 us, fix bug by using empty waveform
        if delay > 5000:
            # empty waveform is 10 us long, find number of empty waves needed
            (n_empty, final_delay) = divmod(delay, 5000)
            # queue empty waveforms
            s = self.AWG.AWGqueueWaveform(self.getHwCh(ch), 0, trigMode,
                                          0, n_empty, prescaler)
            self.check_keysight_error(s)
            # queue the actual waveform
            s = self.AWG.AWGqueueWaveform(self.getHwCh(ch), waveform_id, 0,
                                          final_delay, cycles, prescaler)
            self.check_keysight_error(s)

        else:
            # queue waveform, inform user if an error happens
            s = self.AWG.AWGqueueWaveform(
                self.getHwCh(ch), waveform_id, trigMode, delay, cycles,
                prescaler)
            self.check_keysight_error(s)


    def configureMarker(self, ch):
        """Configure marker for given channel, must be done after queueing"""
        markerMode = int(self.getChannelCmd(ch, 'Marker Mode'))
        trgIOmask = int(self.getChannelValue(ch, 'Marker External'))
        markerValue = int(self.getChannelCmd(ch, 'Marker Value'))
        syncMode = int(self.getChannelCmd(ch, 'Marker Sync Mode'))
        length = int(round(
            self.getChannelValue(ch, 'Marker Length') / 10e-9))
        delay = int(round(
            self.getChannelValue(ch, 'Marker Delay') / 10e-9))
        # trig mask
        trgPXImask = 0
        for i in range(8):
            if self.getChannelValue(ch, 'Marker PXI%d' % i):
                trgPXImask += 2**i
        # configure
        self.AWG.AWGqueueMarkerConfig(nAWG=self.getHwCh(ch),
                                      markerMode=markerMode,
                                      trgPXImask=trgPXImask,
                                      trgIOmask=trgIOmask,
                                      value=markerValue,
                                      syncMode=syncMode,
                                      length=length,
                                      delay=delay)


    def getChannelValue(self, ch, value):
        """ Returns a channel specific value """
        return self.getValue('Ch{} - {}'.format(ch + 1, value))


    def getChannelCmd(self, ch, value):
        """ Returns a channel specific command string """
        return self.getCmdStringFromValue('Ch{} - {}'.format(ch + 1, value))


    def _getTrigChannel(self, options):
        """Helper function, get trig channel for instrument, or None if N/A"""
        trig_channel = options.get('trig_channel', None)
        return trig_channel


    def check_keysight_error(self, code):
        """Check and raise error"""
        if code >= 0:
            return
        # get error message
        raise Error(keysightSD1.SD_Error.getErrorMessage(code))


if __name__ == '__main__':
    pass
