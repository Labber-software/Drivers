#!/usr/bin/env python

import InstrumentDriver
from VISA_Driver import VISA_Driver
import numpy as np

class Driver(VISA_Driver):
    """ This class implements the Agilen 33250 AWG"""
    

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # add compatibility with pre-python 3 version of Labber
        if not hasattr(self, 'write_raw'):
            self.write_raw = self.write
        # start by calling the generic VISA open to make sure we have a connection
        VISA_Driver.performOpen(self, options)
        # clear value of waveform
        self.setValue('Arb. Waveform', [])


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # keep track of if waveform is updated, to avoid sending it many times
        if self.isFirstCall(options):
            self.bWaveUpdated = False
        if quant.name in ('Arb. Waveform',):
            # set value, then mark that waveform needs an update
            quant.setValue(value)
            self.bWaveUpdated = True
        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performSetValue(self, quant, value, sweepRate,
                                                options=options)
        # if final call and wave is updated, send it to AWG
        if self.isFinalCall(options) and self.bWaveUpdated:
            self.sendWaveform()
        return value


    def sendWaveform(self):
        """Rescale and send waveform data to the Tek"""
        # get data
        vData = self.getValueArray('Arb. Waveform')
        # get range and scale to U16
        Vpp = self.getValue('Voltage')
        vI16 = self.scaleWaveformToI16(vData, Vpp)
        length = len(vI16)
        # create data as bytes with header
        sLen = b'%d' % (2*length)
        sHead = b':DATA:DAC VOLATILE, #%d%s' % (len(sLen), sLen)
        # write header + data
        self.write_raw(sHead + vI16.tobytes())
        # select volatile waveform
        self.write(':FUNC:USER VOLATILE')

        
    def scaleWaveformToI16(self, vData, dVpp):
        """Scales the waveform and returns data in a string of I16"""
        # clip waveform and store in-place
        np.clip(vData, -dVpp/2., dVpp/2., vData)
        vI16 = np.array(2047 * vData / (dVpp/2.), dtype=np.int16)
        return vI16


if __name__ == '__main__':
    pass
