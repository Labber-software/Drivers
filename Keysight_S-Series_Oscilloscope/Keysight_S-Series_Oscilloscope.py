#!/usr/bin/env python

import InstrumentDriver
from VISA_Driver import VISA_Driver
from InstrumentConfig import InstrumentQuantity
import numpy as np

class Error(Exception):
    pass

class Driver(VISA_Driver):

    """ This class implements the Keysight N90xx instrument driver"""
    def performOpen(self, options={}):
        VISA_Driver.performOpen(self, options=options)

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should return the actual value set by the instrument"""
        try:
            if quant.name in ('Trigger level',):
                sourcename = self.getValue('Trigger source')
                if sourcename[:7] == 'Channel':
                    nChannel = int(sourcename[-1])
                    cmdstring = ':TRIG:LEV CHAN{}, {}'.format(int(sourcename[-1]), value)
                elif sourcename[:3] == 'AUX':
                    cmdstring = ':TRIG:LEV AUX, {}'.format(value)
                else:
                    pass
                self.writeAndLog(cmdstring)
                return self.performGetValue(quant)
            else:
                # run standard VISA case 
                value = VISA_Driver.performSetValue(self, quant, value, sweepRate, options)
                return self.performGetValue(quant)
        except Exception as e:
            msg = str(e)
            raise InstrumentDriver.CommunicationError(msg)


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check type of quantity
        if quant.name in ('Ch1 - Data', 'Ch2 - Data', 'Ch3 - Data', 'Ch4 - Data'):
            # traces, get channel
            channel = int(quant.name[2])
            
            # check if channel is on
            if self.getValue('Ch%d - Enabled' % channel):

                if self.isFirstCall(options):
                    self.acquireData()

                # the following code obtains the waveforms from memory.

                self.writeAndLog(':WAV:SOUR CHAN{}'.format(channel)) # Identifies the channel that we read out

                self.write(':WAV:DATA?', bCheckError=False) # tells the oscilloscope to send the data to the computer
                sData = self.read() # tells the computer to read its buffer; data is a string '1.059E-3, 2.032E-3, ... '
                lData = sData.split(',') # data is a list of strings: ['1.059E-3', '2.032E-3', ... ]
                vData = np.array(lData[:-1], dtype = float) # data is a numpy array of floats; lData[-1] is a newline character

                dt = float(self.ask(':WAV:XINC?'))
                value = quant.getTraceDict(vData, dt = dt)
            else:
                # not enabled, return empty array
                value = quant.getTraceDict([])
        elif quant.name in ('Trigger level',):
            sourcename = self.getValue('Trigger source')
            if sourcename[:7] == 'Channel':
                nChannel = int(sourcename[-1])
                cmdstring = ':TRIG:LEV? CHAN{}'.format(int(sourcename[-1]))
                value = self.askAndLog(cmdstring, bCheckError = False)
            elif sourcename[:3] == 'AUX':
                cmdstring = ':TRIG:LEV? AUX'
                value = self.askAndLog(cmdstring, bCheckError = False)
            else:
                raise
        elif quant.name in ('Ch1 - Enabled', 'Ch2 - Enabled', 'Ch3 - Enabled', 'Ch4 - Enabled'):
            value = VISA_Driver.performGetValue(self, quant, options)
            BW = self.readValueFromOther('Bandwidth')
            self.setValue('Bandwidth', BW)
            samplePoints = self.readValueFromOther('Sample points')
            self.setValue('Sample points', samplePoints)
            sampleRate = self.readValueFromOther('Sample rate')
            self.setValue('Sample rate', sampleRate)
            timeRange = self.readValueFromOther('Time range')
            self.setValue('Time range', timeRange)
        elif quant.name in ('Sample rate',):
            value = VISA_Driver.performGetValue(self, quant, options)
            BW = self.readValueFromOther('Bandwidth')
            self.setValue('Bandwidth', BW)
        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performGetValue(self, quant, options)
        return value

    def nEnabledChannels(self):
        count = 0
        for channel in range(1,5):
            if self.getValue('Ch{} - Enabled'.format(channel)):
                count = count + 1
        return count

    def acquireData(self):
        self.write(':SYST:HEAD OFF; :ACQ:MODE RTIME; :ACQ:COMP 100; :WAV:FORM ASC; :TRIG:SWE AUTO')
        for channelstr in ('Ch1 - Data', 'Ch2 - Data', 'Ch3 - Data', 'Ch4 - Data'):
            channel = int(channelstr[2])
            self.writeAndLog(':WMEM{}:CLE'.format(channel))
        # Blocking client. Fast but if a trigger event does not arrive. Labber will spin its wheels until a timeout occurs.   
        # bFinished = self.askAndLog(':DIG; *OPC?')

        #non-blocking client.

        if self.getValue('Averaging'):
            self.ask(':STOP;*OPC?')
            self.ask(':TER?') # trigger event register
            self.write('*CLS; :SING')
            Status = int(self.ask(':PDER?'))
            count = 0
            while (count < self.getValue('Number of averages') or Status == 0):
                self.wait(wait_time = 0.1)
                Status = int(self.ask(':PDER?'))
                count = int(self.ask(':WAV:COUN?'))
                if self.isStopped():
                    self.writeAndLog('*CLS')
                    Status = 1
            self.ask(':STOP; *OPC?')
        else:
            self.write('*CLS; :SING')
            Status = int(self.ask(':PDER?'))
            while Status == 0:
                Status = int(self.ask(':PDER?'))
                self.wait(wait_time = 0.1)
                if self.isStopped():
                    self.writeAndLog('*CLS')
                    Status = 1


if __name__ == '__main__':
    pass