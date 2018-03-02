#!/usr/bin/env python

import InstrumentDriver
import numpy as np
from scipy.signal import resample
from scipy.ndimage.filters import gaussian_filter
from scipy.optimize import leastsq
from numpy.fft import fft, fftshift, fftfreq
import h5py


class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements a Single-qubit pulse generator"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # init variables
        self.vData = np.array([], dtype=float)
        self.cData = np.array([], dtype=complex)


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # do nothing, just return value

        if quant.name is 'Trace In':
            # set value, then mark that waveform needs an update
            quant.setValue(value)
        #elif quant.name is 'Save response data':
        #    self.saveDemodulatedResponse_toFile(value, self.cData)
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check type of quantity
        if quant.isVector():
            # traces, check if waveform needs to be re-calculated
            if self.isConfigUpdated():
                pass
            # get correct data and return as trace dict
            if quant.name in ('Response',):
                waveform = self.getValueArray('Raw Signal')
                dt, self.cData = self.demodulate(waveform)
                #if self.getValue('Save file?'):
                #    self.saveDemodulatedResponse_toFile(self.getValue('Save response data'), self.cData)
                value = quant.getTraceDict(self.cData, t0 = 0.0, dt = dt)
            elif quant.name in ('Trace In',):
                value = quant.getValue()
            else:
                self.log(quant.name, level = 30)
        else:
            # for all other cases, do nothing
            value = quant.getValue()
        return value
        
    def demodulate(self, vWaveform):   
      
        #demodulate
        nModFreq = self.getValue('Modulation Freq')
        nSampleRate = self.getValue('Sample Rate')
        nWavLength = len(vWaveform)
        vTvals = np.linspace(0,nWavLength/nSampleRate, nWavLength, endpoint = False)
        
        
        
        mod_period = 1/nModFreq
        #period_num = int(np.floor((self.vRTime[-1]+dt)/mod_period))
        response_int = []
        t_int = []
        
        period_num = (vTvals[-1] - vTvals[0]) * nModFreq
        samples_period = int(nSampleRate/nModFreq)
        
        vWaveform = resample(vWaveform, int(period_num*samples_period))#sinc function interpolation
        
        vTvals = np.linspace(0, nWavLength/nSampleRate, len(vWaveform), endpoint = False)

        avg = np.mean(vWaveform)
        demod = 2*(vWaveform-avg)*np.exp(-1j*(2*np.pi*(nModFreq)*vTvals))

        #integrate over each modulation period
        vResponse = np.array([], dtype = complex)
        t_int = []
        for n in range(0,int(np.floor(period_num))):
            start = n*samples_period
            end = (n+1)*samples_period
            vResponse = np.append(vResponse, np.mean(demod[start:end]))
            t_int.append(np.mean(vTvals[start:end]))

        return mod_period, vResponse      
      

if __name__ == '__main__':
    pass