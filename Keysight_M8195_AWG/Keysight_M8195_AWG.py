#!/usr/bin/env python

import InstrumentDriver
from VISA_Driver import VISA_Driver
import numpy as np

class Driver(VISA_Driver):
    """This class implements the Keysight M8195
    
    The driver currently only implements operations on extended memory.
    """

    # define channels and markers used in various configurations
    CHANNEL_MARKER = {'Single channel (1)': ([1], []),
                      'Single channel (1) + markers (3,4)': ([1], [3, 4]),
                      'Dual channel (1,4)': ([1, 4], []),
                      'Dual channel duplicate (1-3,2-4)': ([1, 2], []),
                      'Dual channel (1,2) + markers (3,4)': ([1, 2], [3, 4]),
                      'Four channel': ([1, 2, 3, 4], [])}

    
    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # start by calling the generic VISA open to make sure we have a connection
        VISA_Driver.performOpen(self, options)
        # configure AWG settings
        self.configure_awg()


    def initSetConfig(self):
        """This function is run before setting values in Set Config"""
        # re-configure AWG before setting values
        self.configure_awg()

            
    def configure_awg(self):
        """Clear waveform and configure AWG to work with Labber"""
        # init vectors with old values
        self.n_ch = 4
        self.wave_updated = False
        self.n_prev_seq = -1
        self.is_running = False
        self.data = [np.array([], dtype=np.int8) for n1 in range(self.n_ch)] 
        # turn off run mode and delete all old data
        self.writeAndLog(':ABOR')
        self.writeAndLog(':TRAC:DEL:ALL')
        # make all channels use external memory
        self.writeAndLog(':TRACE1:MMOD EXT')
        self.writeAndLog(':TRACE2:MMOD EXT')
        self.writeAndLog(':TRACE3:MMOD EXT')
        self.writeAndLog(':TRACE4:MMOD EXT')
        # turn off waveform scaling
        self.writeAndLog(':TRACE1:IMP:SCAL 0')
        self.writeAndLog(':TRACE2:IMP:SCAL 0')
        self.writeAndLog(':TRACE3:IMP:SCAL 0')
        self.writeAndLog(':TRACE4:IMP:SCAL 0')
        # use arbitrary mode, and automatically advance after waveform ends
        self.writeAndLog(':FUNC:MODE ARB')


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # keep track of if waveform is updated, to avoid sending it many times
        if self.isFirstCall(options):
            self.wave_updated = False
#            # if sequence mode, make sure the buffer contains enough waveforms
#            if self.isHardwareLoop(options):
#                (seq_no, n_seq) = self.getHardwareLoopIndex(options)
#                # if first call, clear sequence and create buffer
#                if seq_no==0:
#                    # variable for keepin track of sequence updating
#                    self.writeAndLog(':AWGC:STOP;')
#                    self.bSeqUpdate = False
#                # if different sequence length, re-create buffer
#                if seq_no==0 and n_seq != len(self.lOldU16):
#                    self.lOldU16 = [[np.array([], dtype=np.uint16) \
#                                   for n1 in range(self.n_ch)] for n2 in range(n_seq)]
#            elif self.isHardwareTrig(options):
#                # if hardware triggered, always stop outputting before setting
#                self.writeAndLog(':AWGC:STOP;')

        # check what type of quantity to set
        if quant.name == 'Run mode':
            # run mode is handled by two commands
            indx = quant.getValueIndex(value)
            self.writeAndLog(':INIT:CONT ' + ('1' if indx == 0 else '0'))
            self.writeAndLog(':INIT:GATE ' + ('1' if indx == 2 else '0'))

        elif quant.name == 'Channel mode':
            # stop AWG
            self.stop_awg()
            # before changing, make sure sample rate divider is compatible
            self.writeAndLog(':INST:DACM SING')
            n_ch = len(self.CHANNEL_MARKER[value][0])
            if n_ch >= 4:
                # four channels, force divider to be 4
                self.writeAndLog(':INST:MEM:EXT:RDIV DIV4')
            elif n_ch >= 2: 
                # two channels, force divider to be 2
                self.writeAndLog(':INST:MEM:EXT:RDIV DIV2')
            self.writeAndLog(':TRACE1:MMOD EXT')
            self.writeAndLog(':TRACE2:MMOD EXT')
            self.writeAndLog(':TRACE3:MMOD EXT')
            self.writeAndLog(':TRACE4:MMOD EXT')
            # run standard VISA case for setting channel mode
            value = VISA_Driver.performSetValue(self, quant, value, sweepRate,
                                                options=options)
            # after setting, update memory mode for all channels
            self.writeAndLog(':TRACE1:MMOD EXT')
            self.writeAndLog(':TRACE2:MMOD EXT')
            self.writeAndLog(':TRACE3:MMOD EXT')
            self.writeAndLog(':TRACE4:MMOD EXT')

        elif quant.name.startswith('Sample rate divider'):
            # stop AWG before changing
            self.stop_awg()
            value = VISA_Driver.performSetValue(self, quant, value, sweepRate,
                                                options=options)

        elif quant.name in ('Ch 1', 'Ch 2', 'Ch 3', 'Ch 4'):
            # convert and store new waveform, then mark as need of update
            ch = int(quant.name.split('Ch ')[1])
            v_amp = self.getValue('Ch%d - Range' % ch)
            self.data[ch - 1] = self.scaleWaveformToI8(value['y'], v_amp, ch)
            self.wave_updated = True

        elif quant.name in ('Run'):
            self.start_awg(wait_for_start=False)

        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performSetValue(self, quant, value, sweepRate,
                                                options=options)
        # if final call and wave is updated, send it to AWG
        if self.isFinalCall(options) and self.wave_updated:
            # send waveforms, check if hardware loop
            if self.isHardwareLoop(options):
                (seq, n_seq) = self.getHardwareLoopIndex(options)
                self.reportStatus('Sending waveform (%d/%d)' % (seq+1, n_seq))
                self.send_waveforms(seq=seq, n_seq=n_seq)
            else:
                self.send_waveforms()
            # start if not triggered
            if not self.isHardwareTrig(options):
                self.start_awg()
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check type of quantity
        if quant.name in ('Ch 1', 'Ch 2', 'Ch 3', 'Ch 4'):
            # do nothing here
            value = quant.getValue()
        if quant.name == 'Run mode':
            # run mode is handled by two commands
            cont = int(self.askAndLog(':INIT:CONT?'))
            gate = int(self.askAndLog(':INIT:GATE?'))
            if cont:
                value = 'Continuous'
            elif gate:
                value = 'Gated'
            else:
                value = 'Triggered'
        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performGetValue(self, quant, options)
        return value


    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        try:
            # try to stop awg before closing communication
            for n in range(self.n_ch):
                self.writeAndLog(':OUTP%d 0' % (n + 1))
            self.stop_awg()
        except:
            pass
        # close VISA connection
        VISA_Driver.performClose(self, bError, options)


    def stop_awg(self):
        """Stop AWG and mark as stopped"""
        if self.is_running:
            self.writeAndLog(':ABOR')
            self.is_running = False


    def start_awg(self, wait_for_start=True):
        """Start AWG and make sure instrument is running"""
        if wait_for_start:
            # send command to turn on run mode to AWG
            self.writeAndLog('*CLS')
            self.writeAndLog('INIT:IMM')
            # wait for output to be turned on again
            iRunState = int(self.askAndLog(':STAT:OPER:COND?'))
            nTry = 20
            while nTry>0 and iRunState==0 and not self.isStopped():
                # sleep for while to save resources, then try again
                self.wait(0.1)
                # try again
                iRunState = int(self.askAndLog(':STAT:OPER:COND?'))
                nTry -= 1
            # check if timeout occurred
            if nTry <= 0:
                # timeout
                raise InstrumentDriver.Error('Cannot turn on Run mode')
        else:
            # don't wait for run, just start 
            self.writeAndLog('INIT:IMM')
        #  mark as running
        self.is_running = True


    def send_waveforms(self, seq=None, n_seq=1):
        """Rescale and send waveform data to the AWG"""
        # check channels in use
        channels = self.CHANNEL_MARKER[self.getValue('Channel mode')][0]
        # get number of elements
        n_elements = [len(self.data[ch - 1]) for ch in channels]
        self.n_elem = max(n_elements)
        
        # check if sequence mode or normal run mode
        if seq is None:
            # stop AWG, delete all segments, create empty waveforms
            self.stop_awg()
            self.writeAndLog(':TRAC:DEL:ALL')
            # go through and send waveform on  all channels in use
            for ch in channels:
                self.sendWaveformToAWG(ch)
            # set up segment
            self.writeAndLog(':TRAC:ADV AUTO')
            self.writeAndLog(':TRAC:SEL 1')
            self.writeAndLog(':TRAC:COUN 1')
        else:
            # sequence mode, set up sequences
            pass


    def sendWaveformToAWG(self, ch, seq=None):
        """Send waveform to AWG"""
        # check if sequence
        if seq is None:
            seq = 1
        # get data and markers
        vI8 = self.data[ch - 1]
        markers = self.CHANNEL_MARKER[self.getValue('Channel mode')][1]
        if ch == 1 and len(markers) > 0:
            # markers are always ch 3 and ch 4
            m1 = self.data[2]
            m2 = self.data[3]
            if len(vI8) == 0:
                # no data, but output zeros to match markers
                vI8 = np.zeros((self.n_elem,), dtype=np.int8)
        else:
            m1 = []
            m2 = []
            
        # seems like a zero waveform need to be sent to remove old data
        if len(vI8) == 0:
            vI8 = np.zeros((self.n_elem,), dtype=np.int8)
#            self.writeAndLog(':TRAC%d:DEF 1,%d,0' % (ch, self.n_elem))
#            return

        # make sure length of all data and markeres are the same
        if (len(m1) > 0 and len(vI8) != len(m1)) or \
           (len(m2) > 0 and len(vI8) != len(m2)) or \
           (self.n_elem > 0 and len(vI8) != self.n_elem):
            raise InstrumentDriver.Error(\
                'All channels need to have the same number of elements')


        # proceed depending on marker or no marker
        if ch == 1 and len(markers) > 0:
            # create marker vector
            mI8 = np.zeros((self.n_elem,), dtype=np.int8)
            for m, marker in enumerate([m1, m2]):
                # only add if marker has data
                if len(marker) == len(vI8):
                    # get marker trace, with bit shifts
                    mI8 += (2 ** m) * np.array(marker != 0, dtype=np.int8)
            # combine data and marker to one vector
            vI8 = np.reshape(np.c_[vI8, mI8], [2 * self.n_elem,])

        # define trace
        self.writeAndLog(':TRAC%d:DEF 1,%d' % (ch, self.n_elem))
        # create binary data as bytes with header
        start, length = 0, len(vI8)
        sLen = b'%d' % length
        sHead = b'#%d%s' % (len(sLen), sLen)
        # send to AWG
        sCmd = b':TRAC%d:DATA %d,%d,' % (ch, seq, start)
        self.write_raw(sCmd + sHead + vI8[start:start+length].tobytes())
        

    def scaleWaveformToI8(self, vData, Vamp, ch):
        """Scales the waveform and returns data in a string of U16"""
        # make sure waveform data is within the voltage range 
        truncate = self.getValue('Truncate waveform if out of range')
        if (not truncate) and (np.sum(vData > Vamp) or np.sum(vData < -Vamp)):
            raise InstrumentDriver.Error(
                ('Waveform for channel %d contains values that are ' % ch) + 
                'outside the channel voltage range.')
        # clip waveform and store in-place
        np.clip(vData, -Vamp, Vamp, vData)
        # make sure data is integer number of 256 entries
        tot_size = 256 * (1 + divmod(len(vData) - 1, 256)[0])
        vI8 = np.zeros(tot_size, dtype=np.int8)
        vI8[:len(vData)] = np.array(127 * vData / Vamp, dtype=np.int8)
        return vI8


if __name__ == '__main__':
    pass
