#!/usr/bin/env python

from VISA_Driver import VISA_Driver
import numpy as np


class Driver(VISA_Driver):
    """ This class implements the Keysight 33622A AWG"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # add compatibility with pre-python 3 version of Labber
        if not hasattr(self, 'write_raw'):
            self.write_raw = self.write
        # Call the generic VISA open to make sure we have a connection
        VISA_Driver.performOpen(self, options)
        # clear value of waveforms
        self.write('SOUR1:DATA:VOL:CLE')
        self.write('SOUR2:DATA:VOL:CLE')
        self.setValue('Channel 1 Arb. Waveform', [])
        self.setValue('Channel 2 Arb. Waveform', [])
        self.waves = [None]*2

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # keep track of if waveform is updated, to avoid sending it many times
        if self.isFirstCall(options):
            self.bWaveUpdated = False
        if quant.name in ('Channel 1 Arb. Waveform',
                          'Channel 2 Arb. Waveform'):
            # set value, then mark that waveform needs an update
            quant.setValue(value)
            self.bWaveUpdated = True
        else:

            # for all other cases, call VISA driver
            value = VISA_Driver.performSetValue(self, quant, value, sweepRate,
                                                options=options)
        # if final call and wave is updated, send it to AWG
        if self.isFinalCall(options) and self.bWaveUpdated:
            # Double check that the waveforms truly changed
            for channel in [1, 2]:
                if not np.array_equal(self.getValueArray('Channel ' + str(channel) + ' Arb. Waveform'), self.waves[channel-1]):
                    # store and send waveforms
                    self.waves[channel-1] = np.copy(self.getValueArray('Channel ' + str(channel) + ' Arb. Waveform'))
                    self.sendWaveform(channel)
        # Sync ARBs
        if self.isFinalCall(options):
            self.write(':FUNC:ARB:SYNC')
        return value

    def sendWaveform(self, channel):
        """Rescale and send waveform data to the AWG"""
        channel = str(int(channel))
        Vpp = self.getValue('Channel ' + channel + ' Voltage')
        self.log(Vpp)
        self.write('SOUR' + channel + ':DATA:VOL:CLE')
        # get data
        data = self.getValueArray('Channel ' + channel + ' Arb. Waveform')
        # get range and scale to U16
        data16 = self.scaleWaveformToI16(data, Vpp)
        length = len(data16)
        # create data as bytes with header
        length = b'%d' % (2*length)
        header = b':SOUR' + channel.encode('utf-8') + b':DATA:ARB:DAC LABBER, #%d%s' % (len(length), length)
        # write header + data
        self.write_raw(header + data16.tobytes())
        # select  waveform
        self.write(':SOUR' + channel + ':FUNC:ARB LABBER')
        # Setting ARB resets amplitude and offset, so we set those again
        self.sendValueToOther('Channel ' + channel + ' Voltage', Vpp)
        self.sendValueToOther('Channel ' + channel + ' Offset', self.getValue('Channel ' + channel + ' Offset'))
        # Sync ARBs
        self.write(':FUNC:ARB:SYNC')

    def scaleWaveformToI16(self, data, Vpp):
        """Scales the waveform and returns data in a string of I16"""
        # scale waveform to use full DAC range
        data = np.array(data)/np.max(data)
        return np.array(32767*data, dtype=np.int16)


if __name__ == '__main__':
    pass
