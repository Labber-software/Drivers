#!/usr/bin/env python

import Predistortion_helper_functions
import InstrumentDriver
import numpy as np
from numpy.fft import fft, fftshift, fftfreq, ifft, ifftshift
from scipy.interpolate import interp1d
import h5py
from scipy.ndimage.filters import gaussian_filter
from cmath import phase as complex_phase
# import sys, os
# sys.path.append('/Applications/Labber/Script')

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements a Single-qubit pulse generator"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # init variables

        self.oPredistort = Predistortion_helper_functions.Predistortion()

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # do nothing, just return value
        if quant.name in ('Trace - I', 'Trace - Q'):
            quant.setValue(value)
        return value

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check type of quantity
        if quant.isVector():
            # traces, check if waveform needs to be re-calculated
            if self.isConfigUpdated():
                self.updatePredistort()
                self.calculateWaveform()
                # get correct data and return as trace dict

            vData, t0, dt = self.getWaveformFromMemory(quant)
            value = quant.getTraceDict(vData, t0=t0, dt=dt)
        else:
            # for all other cases, do nothing
            value = quant.getValue()
        return value

    # Needed function for Predistortion
    def updatePredistort(self):
        dParams = \
        {\
        'ROI start time': self.getValue('ROI start time'),\
        'ROI deltaT': self.getValue('ROI deltaT'),\
        'DeltaT with reduced smoothing': self.getValue('DeltaT with reduced smoothing'),\
        'Smoothing sigma': self.getValue('Smoothing sigma'),\
        'Reduced smoothing sigma': self.getValue('Reduced smoothing sigma'),\
        'Search for new file': self.getValue('Search for new file'),\
        'Bandwidth': self.getValue('Bandwidth'),\
        'Bandcutoff': self.getValue('Bandcutoff'),\
        'Load response': self.getValue('Load response'),\
        }
        self.oPredistort.SetParams(dParams)


    def getWaveformFromMemory(self, quant):
        """Return data from already calculated waveforms"""
        # special case for readout (only one vector available)

        if quant.name == 'Response I':
            vData = self.oPredistort.vFilteredResponse_I
            dt = self.oPredistort.vRTime_I[1]-self.oPredistort.vRTime_I[0]
            t0 = self.oPredistort.vRTime_I[0]
        elif quant.name == 'Response Q':
            vData = self.oPredistort.vFilteredResponse_Q
            dt = self.oPredistort.vRTime_I[1]-self.oPredistort.vRTime_I[0]
            t0 = self.oPredistort.vRTime_I[0]
        elif quant.name == 'Raw Response I':
            vData = self.oPredistort.vResponse_I
            dt = self.oPredistort.vRTime_I[1]-self.oPredistort.vRTime_I[0]
            t0 = self.oPredistort.vRTime_I[0]
        elif quant.name == 'Raw Response Q':
            vData = self.oPredistort.vResponse_Q
            dt = self.oPredistort.vRTime_I[1]-self.oPredistort.vRTime_I[0]
            t0 = self.oPredistort.vRTime_I[0]
        elif quant.name == 'Response FFT I':
            vData = self.oPredistort.vFilteredResponse_FFT_I
            dt = self.oPredistort.vResponse_freqs[1]-self.oPredistort.vResponse_freqs[0]
            t0 = self.oPredistort.vResponse_freqs[0]
        elif quant.name == 'Response FFT Q':
            vData = self.oPredistort.vFilteredResponse_FFT_Q
            dt = self.oPredistort.vResponse_freqs[1]-self.oPredistort.vResponse_freqs[0]
            t0 = self.oPredistort.vResponse_freqs[0]
        else:
            pass
        return vData, t0, dt

    def calculateWaveform(self):
        if self.getValue('Predistortion'):
            self.oPredistort.generateResponse()
        ###################################################


if __name__ == '__main__':
    sPath = '/Users/orlando3018/Dropbox (MIT)/MIT-shared/People/Dan/Labber Data/2017/03/Data_0324/Generate_Response_5.4GHz_10k_PSG_IQ_2.hdf5'
    with h5py.File(sPath, 'r') as f:
        Data_Q = np.array(f['Traces/Predistortion - Response'].value)
        t0dt = np.array(f['Traces/Predistortion - Response_t0dt'].value)
        length = float(f['Traces/Predistortion - Response_N'].value)
        vResponse_Q = complex(1,0)*Data_Q[:,0,0].ravel()+complex(0,1)*Data_Q[:,1,0].ravel()
        vRTime_Q = np.linspace(t0dt[0,0], length*t0dt[0,1], length)
        print(Data_Q.shape)
