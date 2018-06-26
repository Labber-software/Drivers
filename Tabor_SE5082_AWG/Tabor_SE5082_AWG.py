#!/usr/bin/env python
from BaseDriver import Error
from VISA_Driver import VISA_Driver
from pyvisa.constants import (
    VI_ATTR_WR_BUF_OPER_MODE, VI_ATTR_RD_BUF_OPER_MODE, VI_FLUSH_ON_ACCESS,
    VI_READ_BUF, VI_WRITE_BUF)
import numpy as np

from pyte16 import download_binary_data

class Driver(VISA_Driver):
    """Tabor Labber driver"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # open visa communication
        VISA_Driver.performOpen(self, options)

        # set additional flags
        self.com.set_visa_attribute(
            VI_ATTR_WR_BUF_OPER_MODE, VI_FLUSH_ON_ACCESS)
        self.com.set_visa_attribute(
            VI_ATTR_RD_BUF_OPER_MODE, VI_FLUSH_ON_ACCESS)

        read_buff_size_bytes = 4096
        write_buff_size_bytes = 4096

        self.com.visalib.set_buffer(
            self.com.session, VI_READ_BUF, read_buff_size_bytes)
        self.com.__dict__['read_buff_size'] = read_buff_size_bytes
        self.com.visalib.set_buffer(
            self.com.session, VI_WRITE_BUF, write_buff_size_bytes)
        self.com.__dict__['write_buff_size'] = write_buff_size_bytes


        # timeout
        self.timeout_ms = int(1000 * self.dComCfg['Timeout'])
        self.nCh = 2
        self.lWaveUpdated = [False] * self.nCh
        # clear all waveforms
        self.writeAndLog(':TRAC:DEL:ALL')


    def initSetConfig(self):
        """This function is run before setting values in Set Config"""
        # clear old waveforms
        self.lInUse = [False] * self.nCh
        for n in range(self.nCh):
            channel = n + 1
            self.setValue('Ch %d' % channel, [])
            self.setValue('Ch %d - Marker 1' % channel, [])
            self.setValue('Ch %d - Marker 2' % channel, [])
            # clear all
            self.writeAndLog(':INST %d;:TRAC:DEL:ALL' % channel)


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        if self.isFirstCall(options):
            self.lWaveUpdated = [False] * self.nCh

        # check if channel-specific, if so get channel + name
        if quant.name.startswith('Ch') and len(quant.name) > 6:
            ch = int(quant.name[2]) - 1
            name = quant.name[6:]
            ch_str = ':INST %d;' % (ch + 1)
        else:
            ch, name = None, ''
            ch_str = ''


        # proceed depending on command
        if name in ('Run mode',):
            # run mode, different call types
            if value == 'Continuous':
                self.writeAndLog(ch_str + ':INIT:CONT 1; :INIT:GATE 0')
            elif value == 'Gated':
                self.writeAndLog(ch_str + ':INIT:CONT 0; :INIT:GATE 1')
            elif value == 'Triggered':
                self.writeAndLog(ch_str + ':INIT:CONT 0; :INIT:GATE 0')

        elif quant.name in ('Ch 1', 'Ch 2',
                            'Ch 1 - Marker 1', 'Ch 1 - Marker 2',
                            'Ch 2 - Marker 1', 'Ch 2 - Marker 2'):
            # set value, then mark that waveform needs an update
            quant.setValue(value)
            ch = int(quant.name[3]) - 1
            self.lWaveUpdated[ch] = True

        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performSetValue(
                self, quant, value, sweepRate, options)

        # For effiency, we only upload the waveform at the final call
        if self.isFinalCall(options) and np.any(self.lWaveUpdated):
            self.sendWaveformAndStart()

        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check if channel-specific, if so get channel + name
        if quant.name.startswith('Ch') and len(quant.name) > 6:
            ch = int(quant.name[2]) - 1
            name = quant.name[6:]
            ch_str = ':INST %d;' % (ch + 1)
        else:
            ch, name = None, ''
            ch_str = ''


        # check type of quantity
        if name in ('Run mode',):
            # run mode, different call types
            if self.askAndLog(ch_str + ':INIT:CONT?') == 'ON':
                value = 'Continuous'
            elif self.askAndLog(ch_str + ':INIT:GATE?') == 'ON':
                value = 'Gated'
            else:
                value = 'Triggered'
        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performGetValue(self, quant, options)
        return value


    def sendWaveformAndStart(self):
        """Rescale and send waveform data to the Tek"""
        # go through all channels
        for n in range(self.nCh):
            # channels are numbered 1-4
            channel = n + 1
            vData = self.getValueArray('Ch %d' % channel)
            vMark1 = self.getValueArray('Ch %d - Marker 1' % channel)
            vMark2 = self.getValueArray('Ch %d - Marker 2' % channel)
            self.sendWaveformToAWG(channel, vData, vMark1, vMark2)

        # turn on channels in use
        sOutput = ''
        for n, bUpdate in enumerate(self.lInUse):
            if bUpdate:
                sOutput += (':INST %d;:OUTP 1;' % (n + 1))
        if sOutput != '':
            self.writeAndLog(sOutput)
        # check for operation complete before returning
        self.askAndLog('*OPC?')


    def scaleWaveformToU16(self, vData, dVpp, ch):
        """Scales the waveform and returns data in a string of U16"""
        # make sure waveform data is within the voltage range
        if np.sum(vData > dVpp / 2) or np.sum(vData < -dVpp / 2):
            raise Error(
                ('Waveform for channel %d contains values that are ' % ch) +
                'outside the channel voltage range.')
        # clip waveform and store in-place
        np.clip(vData, -dVpp / 2., dVpp / 2., vData)
        vU16 = np.array(4094 * (vData + dVpp / 2.) / dVpp, dtype=np.uint16)
        return vU16


    def sendWaveformToAWG(self, channel, vData, vMark1, vMark2):
        """Send waveform to Tek"""
        # turn off output and clear old traces
        self.writeAndLog(':INST %d;:OUTP 0' % channel)
        self.writeAndLog(':TRAC:DEL:ALL')
        # if output is disabled, stop here
        if not self.getValue('Ch%d - Enabled' % channel):
            return False

        # channels are named 1-2
        n = channel - 1
        if len(vData) == 0:
            if len(vMark1) == 0 and len(vMark2) == 0:
                # turn off, clear, go to next channel
                self.lInUse[n] = False
                return False
            else:
                # no data, but markers exist, output zeros for data
                nMark = max(len(vMark1), len(vMark2))
                vData = np.zeros((nMark,), dtype=float)
        # make sure length of data is the same
        if (len(vMark1) > 0 and len(vData) != len(vMark1)) or \
           (len(vMark2) > 0 and len(vData) != len(vMark2)):
            raise Error('All channels need to have the same number of elements')
        self.nPrevData = len(vData)
        # channel in use, mark
        self.lInUse[n] = True
        # get range and scale to U16
        Vpp = self.getValue('Ch%d - Range' % channel)
        vU16 = self.scaleWaveformToU16(vData, Vpp, channel)
        # check for marker traces
        for m, marker in enumerate([vMark1, vMark2]):
            if len(marker) == len(vU16):
                # get marker trace
                vMU16 = np.array(marker != 0, dtype=np.uint16)
                # add marker trace to data trace, with bit shift
                vU16 += 2**(12 + m) * vMU16
        # granularity of the awg is 32
        if len(vU16) % 32 > 0:
            vU16 = np.pad(vU16, (0, 32 - (len(vU16) % 32)), 'constant',
                          constant_values=2047)

        self.writeAndLog(':TRAC:DEF 1, %d' % len(vU16))
        self.writeAndLog(':TRAC:SEL 1')
        download_binary_data(self.com, 'TRAC:DATA', vU16, len(vU16) * 2,
                             paranoia_level=0)
        return True




if __name__ == '__main__':
    pass
