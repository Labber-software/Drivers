#!/usr/bin/env python

import InstrumentDriver
import numpy as np
from numpy.fft import fft, fftshift, fftfreq, ifft, ifftshift
from scipy.interpolate import interp1d
import h5py
from scipy.ndimage.filters import gaussian_filter
from cmath import phase as complex_phase
import Labber

# def performGetValue(self, quant, options={}):
#     """Perform the Get Value instrument operation"""
#     # check type of quantity
#     if quant.isVector():
#         # traces, check if waveform needs to be re-calculated
#         if self.isConfigUpdated():
#             self.calculateWaveform()
#             # get correct data and return as trace dict
#
#         vData, t0, dt = self.getWaveformFromMemory(quant)
#         value = quant.getTraceDict(vData, t0=t0, dt=dt)
#     else:
#         # for all other cases, do nothing
#         value = quant.getValue()
#     return value


class Predistortion():
    """ This class predistorts input signals"""
    def __init__(self, nChannelNum = 1):
        """Perform the operation of opening the instrument connection"""
        # init variables

        # at the moment I assume that all the pulses are the same size.
        self.vTime = np.array([], dtype=float)
        self.vResponse_I = np.array([], dtype=complex)
        self.vResponse_Q = np.array([], dtype=complex)
        self.vFilteredResponse_I = np.array([], dtype=complex)
        self.vFilteredResponse_Q = np.array([], dtype=complex)
        self.vRTime_I = np.array([], dtype=float)
        self.vRTime_Q = np.array([], dtype=float)
        self.vFilteredResponse_FFT_I = np.array([], dtype=float)
        self.vFilteredResponse_FFT_Q = np.array([], dtype=float)
        self.vResponse_freqs = np.array([], dtype=float)

    def SetParams(self, dParams = None):

        defaultParams = {'ROI start time': 65e-9, \
        'ROI deltaT': 3e-9, \
        'DeltaT with reduced smoothing': 5e-9,\
        'Smoothing sigma': 5e-9, \
        'Reduced smoothing sigma': 0.5e-9, \
        'Search for new file': False,\
        'Bandwidth': 0.1e9, \
        'Bandcutoff': 0.1e9,\
        'Load response': r'C:/Program Files (x86)/Labber/Data/2016/04/Data_0421/Generate_Response_5.4GHz_10k_PSG.hdf5'}

        if dParams is None:
            self.dParams = defaultParams
        else:
            self.dParams = dParams

    def generateResponse(self):

		#get filter parameters.  Gaussian filter?
        nCenter = self.dParams['ROI start time']
        nDeltaROI = self.dParams['ROI deltaT']
        nDeltaTLight = self.dParams['DeltaT with reduced smoothing']
        #sigma_t = self.dParams['Filter standard deviation')
        nSmoothing = self.dParams['Smoothing sigma']
        nSmoothingLight = self.dParams['Reduced smoothing sigma']


        #load response data (produced using a different scan)
        #This line of code seems useless, but it combats a bug in the path feature in Labber (see .ini file)
        if self.dParams['Search for new file']:
            self.load_demod_response()

        self.vFilteredResponse_I = self.vResponse_I.copy()
        self.vFilteredResponse_Q = self.vResponse_Q.copy()

        #Applies a Gaussian smooth, eliminating high frequency noise.  Not applied in a small region following nCenter.
        self.Smooth_response(nCenter, nDeltaROI, nDeltaTLight, nSmoothingLight, nSmoothing, 'I')
        self.Smooth_response(nCenter, nDeltaROI, nDeltaTLight, nSmoothingLight, nSmoothing, 'Q')

		#find the fft of the filtered response.
        signal_len = len(np.diff(self.vFilteredResponse_I))
        if (signal_len % 2) == 1: # FFTs with an odd number of points can take a long time.
            signal_len = signal_len - 1
        self.vResponse_freqs, FilteredResponse_FFT_I = self.apply_FFT(self.vRTime_I[:signal_len], np.diff(self.vFilteredResponse_I)[:signal_len])

        # a precessing complex phase generates a time delay.  We want to remove as much of this as possible.
        self.vFilteredResponse_FFT_I = FilteredResponse_FFT_I*np.exp(1j*2*np.pi*self.vResponse_freqs*nCenter)

        signal_len = len(np.diff(self.vFilteredResponse_Q))
        if (signal_len % 2) == 1:
            signal_len = signal_len - 1
        self.vResponse_freqs, FilteredResponse_FFT_Q = self.apply_FFT(self.vRTime_Q[:signal_len], np.diff(self.vFilteredResponse_Q)[:signal_len])

        self.vFilteredResponse_FFT_Q = FilteredResponse_FFT_Q*np.exp(1j*2*np.pi*self.vResponse_freqs*nCenter)
        #self.vResponse_freqs = self.vResponse_freqs

        #normalizes the FFT
        centerval_I = np.sum(np.diff(self.vFilteredResponse_I))
        self.vFilteredResponse_FFT_I = self.vFilteredResponse_FFT_I / centerval_I


        centerval_Q = np.sum(np.diff(self.vFilteredResponse_Q))
        centerval_Q = centerval_Q * np.abs(centerval_I) / np.abs(centerval_Q)
        self.vFilteredResponse_FFT_Q = self.vFilteredResponse_FFT_Q / centerval_I#* np.exp(-1j*np.pi/2) / centerval_I

        #applies a relative time delay and overall phase shift between I and Q response functions.
        #The phase shift is needed because the SSB mixers do not necessarily have 90 degrees phase shift between I and Q.
        #phase = self.dParams['I/Q phase']
        #timedelay = self.dParams['I/Q time delay']
        phase = 0
        timedelay = 0
        self.vFilteredResponse_FFT_Q = self.vFilteredResponse_FFT_Q * np.exp(1j*2*np.pi*self.vResponse_freqs*timedelay+1j*phase)
        #get bandwidth values
        #separate FFT into different regions.  1 & 5 utterly ignores FFT response, 2 & 4 uses a Gaussian curve to smoothly connect the unfiltered response (3) to 1 & 5.
        self.piecewiseFFT('I')
        self.piecewiseFFT('Q')

    def piecewiseFFT(self, name_str):

        if name_str == 'I':
            filteredresponseFFT = self.vFilteredResponse_FFT_I
        elif name_str == 'Q':
            filteredresponseFFT = self.vFilteredResponse_FFT_Q

        nBandwidth = self.dParams['Bandwidth']
        nBandcutoff = self.dParams['Bandcutoff']

        df = self.vResponse_freqs[1].real-self.vResponse_freqs[0].real

        argFFTcenter = np.argmin(abs(self.vResponse_freqs))
        argFFTradius = int(nBandwidth/df)
        argFFTfalloff = int(nBandcutoff/df)

        slice2 = filteredresponseFFT[(argFFTcenter-argFFTradius-argFFTfalloff):(argFFTcenter-argFFTradius)]

        slicefreqs2 = self.vResponse_freqs[(argFFTcenter-argFFTradius-argFFTfalloff):(argFFTcenter-argFFTradius)]

        piece1 = (slice2[0]/np.abs(slice2[0]))*np.ones(self.vResponse_freqs[:(argFFTcenter-argFFTradius-argFFTfalloff)].shape)

        piece2 = self.gaussian_ramp(slicefreqs2, -nBandwidth-nBandcutoff, nBandcutoff)

        piece2 = (slice2/np.abs(slice2)-slice2)*piece2 + slice2

        piece3 = filteredresponseFFT[(argFFTcenter-argFFTradius):(argFFTcenter+argFFTradius)]

        slice4 = filteredresponseFFT[(argFFTcenter+argFFTradius):(argFFTcenter+argFFTradius+argFFTfalloff)]

        slicefreqs4 = self.vResponse_freqs[(argFFTcenter+argFFTradius):(argFFTcenter+argFFTradius+argFFTfalloff)]

        piece4 = self.gaussian_ramp(slicefreqs4, nBandwidth+nBandcutoff, nBandcutoff)

        piece4 = (slice4/np.abs(slice4)-slice4)*piece4+slice4

        piece5 = (slice4[-1]/np.abs(slice4[-1]))*np.ones(self.vResponse_freqs[(argFFTcenter+argFFTradius+argFFTfalloff):].shape)

        if name_str == 'I':
            self.vFilteredResponse_FFT_I = np.concatenate((piece1, piece2, piece3, piece4, piece5))
        elif name_str == 'Q':
            self.vFilteredResponse_FFT_Q = np.concatenate((piece1, piece2, piece3, piece4, piece5))

    def apply_FFT(self, tvals, signal):
        fft_signal = fftshift(fft(signal))
        fft_vals = fftshift(fftfreq(len(signal), tvals[1]-tvals[0]))
        return fft_vals, fft_signal

    def apply_filter(self, tvals, signal, rolloff_freq, rolloff_width):
        fft_signal = fftshift(fft(signal))
        fft_vals = fftshift(fftfreq(len(tvals), tvals[1]-tvals[0]))
        sfilter = self.sigmoid(fft_vals, rolloff_freq, rolloff_width)
        return ifft(ifftshift(fft_signal*sfilter))
        #return ifft(ifftshift(fft_signal))

    def sigmoid(self, freqs, fcenter, width, cutoff):
        freqs = freqs.real
        return 1/(1+np.exp(-8*(freqs-fcenter+(width+cutoff/2))/cutoff))+1/(1+np.exp(8*(freqs-fcenter-(width+cutoff/2))/cutoff))-np.ones(freqs.shape)

    def Smooth_response(self, offsetT, deltaROI, deltaTlight, dtsmoothlight, dtsmooth, name_str):

        if name_str == 'I':
            time = self.vRTime_I
            response = self.vResponse_I
        elif name_str == 'Q':
            time = self.vRTime_Q
            response = self.vResponse_Q
        else:
            print('Invalid input')
            raise
        dt = time[1]-time[0]
        ROI = int((deltaROI/dt))
        referenceROI = int(offsetT/dt)
        sigma = dtsmooth/dt
        sigmalight = dtsmoothlight/dt
        postROIfilter = int(deltaTlight/dt)

        ROIvals = response[referenceROI:referenceROI+ROI]
        ROIright = response[referenceROI+ROI:]
        ROIrightLight = response[referenceROI+ROI:]
        ROIleft = response[:referenceROI]

        #nothing interesting is happening on the left side of the distribution so we will apply the full smooth
        ROIleft = complex(1,0)*gaussian_filter(ROIleft.real, sigma) + complex(0,1)*gaussian_filter(ROIleft.imag, sigma)

        #let's smooth in the ROI region as well . . . because
        #ROIvals = (complex(1,0)*gaussian_filter(self.vResponse.real, sigmalight) + complex(0,1)*gaussian_filter(self.vResponse.imag, sigmalight))[referenceROI:referenceROI+ROI]

        #
        ROIrightLight = complex(1,0)*gaussian_filter(ROIrightLight.real, sigmalight) + complex(0,1)*gaussian_filter(ROIrightLight.imag, sigmalight)

        ROIright = complex(1,0)*gaussian_filter(ROIright.real, sigma) + complex(0,1)*gaussian_filter(ROIright.imag, sigma)

        filteredresponse = np.concatenate((ROIleft, ROIvals, ROIrightLight[:postROIfilter-ROI], ROIright[postROIfilter-ROI:]))

        if name_str == 'I':
            self.vFilteredResponse_I = filteredresponse
        elif name_str == 'Q':
            self.vFilteredResponse_Q = filteredresponse

        #self.vFilteredResponse = self.vFilteredResponse.conj()

    def generate_tvals(self, init_size, offsetT, deltaT, dtprime, dt):
        offset = offsetT/dt
        width = deltaT/dtprime - deltaT/dt
        b = np.log((2*dt-dtprime)/dtprime)
        a = 2 * b / width
        new_size = init_size + width
        vals = np.linspace(0, np.floor(new_size) - 1 , np.floor(new_size))
        return dt * (a * vals + np.log(np.exp(b)+np.exp(a*(vals - offset))) - np.log(1+np.exp(b+a*(vals - offset)))) / a

    def gaussian_ramp(self, fvals, f_0, width):
        return (np.exp(-5*(fvals-f_0)**2/width**2)-np.exp(-5))/(1-np.exp(-5))

    def exp_ramp(self, fvals, f_0, width):
        return (np.exp(-5*(abs(fvals-f_0))/width)-np.exp(-5))/(1-np.exp(-5))

    # def load_demod_response(self):
    #     sPath = self.dParams['Load I response']
    #
    #     # f = Labber.LogFile(sPath)
    #     # (x,y) = f.getTraceXY(entry = 0)
    #     # self.vResponse_I = y
    #     # self.vRTime_I = x.real
    #     # (x,y) = f.getTraceXY(entry = 1)
    #     # self.vResponse_Q = y
    #     # self.vRTime_Q = x.real
    #     #
    #     # self.log(y, level = 30)
    #     # self.log(x, level = 30)
    #
    #     try:
    #         with h5py.File(sPath, 'r') as f:
    #             Data_I = np.array(f['Traces/Predistortion - Response'].value)
    #             t0dt = np.array(f['Traces/Predistortion - Response_t0dt'].value)
    #             length = float(f['Traces/Predistortion - Response_N'].value)
    #             self.vResponse_I = complex(1,0)*Data_I[:,0,0].ravel()+complex(0,1)*Data_I[:,1,0].ravel()
    #             self.vRTime_I = np.linspace(t0dt[0,0], length*t0dt[0,1], length)
    #     except Exception as inst:
    #         self.log(inst, level = 30)
    #         raise
    #
    #     #sPath = self.dParams['Load Q response')
    #     try:
    #         with h5py.File(sPath, 'r') as f:
    #             Data_Q = np.array(f['Traces/Predistortion - Response'].value)
    #             t0dt = np.array(f['Traces/Predistortion - Response_t0dt'].value)
    #             length = float(f['Traces/Predistortion - Response_N'].value)
    #             self.vResponse_Q = complex(1,0)*Data_Q[:,0,1].ravel()+complex(0,1)*Data_Q[:,1,1].ravel()
    #             self.vRTime_Q = np.linspace(t0dt[0,0], length*t0dt[0,1], length)
    #     except Exception as inst:
    #         self.log(inst, level = 30)
    #         raise

    def load_demod_response(self):
        sPath = self.dParams['Load response']

        # f = Labber.LogFile(sPath)
        # (x,y) = f.getTraceXY(entry = 0)
        # self.vResponse_I = y
        # self.vRTime_I = x.real
        # (x,y) = f.getTraceXY(entry = 1)
        # self.vResponse_Q = y
        # self.vRTime_Q = x.real
        #
        # self.log(y, level = 30)
        # self.log(x, level = 30)

        f = Labber.LogFile(sPath)
        self.vRTime_I, self.vResponse_I = f.getTraceXY(entry = 0)
        self.vRTime_Q, self.vResponse_Q = f.getTraceXY(entry = 1)

    def correctWaveform(self, t0, dt, vI, vQ):

        #generate inverse
        Inverse_I = complex(1,0) / self.vFilteredResponse_FFT_I
        #generate linear interpolation function (we think the AWG signal has a much lower sampling rate than our response function-->limited by 1/2 the LO freq)
        Inverse_interp_I = interp1d(self.vResponse_freqs, Inverse_I)

        Inverse_Q = complex(1,0) / self.vFilteredResponse_FFT_Q

        Inverse_interp_Q = interp1d(self.vResponse_freqs, Inverse_Q)

        #applies the interpolated inverse function to the AWG signal
        dt = 1 / self.dParams['Sample rate']

        tvals = np.arange(0, dt*len(vI), dt)
        #ratioIQ = self.dParams['Ratio I/Q')
        #timeDelay = self.dParams['Time delay')

        fft_vals, fft_signal_I = self.apply_FFT(tvals, complex(1,0)*vI)
        fft_vals, fft_signal_Q = self.apply_FFT(tvals, complex(0,1)*vQ)
        fft_signal = (fft_signal_I * Inverse_interp_I(fft_vals) + fft_signal_Q * Inverse_interp_Q(fft_vals))
        corr_signal = ifft(ifftshift(fft_signal))

        #fft_vals, fft_signal = self.apply_FFT(tvals, (self.lI[n]+1j*self.lQ[n]))
        #fft_signal = fft_signal * Inverse_interp_Q(fft_vals)# * np.exp(-1j * 2 * np.pi * fft_vals)
        #corr_signal_Q = ifft(ifftshift(fft_signal))

        vI = np.array(corr_signal.real, dtype = 'float64')
        vQ = np.array(corr_signal.imag, dtype = 'float64')

        return vI, vQ

    def correctWaveform_IQ(self, t0, dt, vI, vQ):

        response_I = ifft(ifftshift(self.vFilteredResponse_FFT_I))
        response_FFT_I_r = fftshift(fft(complex(1,0)*response_I.real))
        response_FFT_I_i = fftshift(fft(complex(1,0)*response_I.imag))

        response_Q = ifft(ifftshift(self.vFilteredResponse_FFT_Q))
        response_FFT_Q_r = fftshift(fft(complex(1,0)*response_Q.real))
        response_FFT_Q_i = fftshift(fft(complex(1,0)*response_Q.imag))

        #{{a, b},{c, d}}, determinant is ad-bc, plus sign comes from additional i tacked on to the Q by the IQ mixer.  I removed this factor of i from the FFT of the response function.
        determinant = response_FFT_I_r * response_FFT_Q_i - response_FFT_Q_r * response_FFT_I_i

        Za =  response_FFT_Q_i / determinant
        Zb =  -response_FFT_Q_r / determinant
        Zc =  -response_FFT_I_i / determinant
        Zd =  response_FFT_I_r / determinant

        Inverse_A = interp1d(self.vResponse_freqs, Za)
        Inverse_B = interp1d(self.vResponse_freqs, Zb)
        Inverse_C = interp1d(self.vResponse_freqs, Zc)
        Inverse_D = interp1d(self.vResponse_freqs, Zd)

        #applies the interpolated inverse function to the AWG signal
        dt = 1 / self.dParams['Sample rate']

        tvals = np.arange(0, dt*len(vI), dt)

        fft_vals, fft_signal_r = self.apply_FFT(tvals,complex(1,0)*vI)
        fft_vals, fft_signal_i = self.apply_FFT(tvals,complex(1,0)*vQ)

        fft_signal = fft_signal_r * Inverse_A(fft_vals) + fft_signal_i * Inverse_B(fft_vals) + 1j * (fft_signal_r * Inverse_C(fft_vals) + fft_signal_i * Inverse_D(fft_vals))
        corr_signal = ifft(ifftshift(fft_signal))

        vI = np.array(corr_signal.real, dtype = 'float64')
        vQ = np.array(corr_signal.imag, dtype = 'float64')

        return vI, vQ

    def applyRatioTimeOffset(self):

        dt = 1 / self.dParams['Sample rate']
        nOutput = 1 + int(self.getValueIndex('Number of outputs'))

        for n in range(nOutput):

            tvals = np.arange(0, dt*len(self.vI), dt)
            ratioIQ = self.dParams['Ratio I/Q']
            timeDelay = self.dParams['Time delay']

            fft_vals, fft_signal = self.apply_FFT(tvals, (self.vI+1j*self.vQ))
            fft_signal = fft_signal * np.exp(-1j * 2 * np.pi * fft_vals * timeDelay)
            corr_signal_Q = ratioIQ * ifft(ifftshift(fft_signal))

            self.vQ[n] = np.array(corr_signal_Q.imag, dtype = 'float64')


if __name__ == '__main__':
    sPath = '/Users/orlando3018/Dropbox (MIT)/MIT-shared/People/Dan/Labber Data/2017/03/Data_0324/Generate_Response_5.4GHz_10k_PSG_IQ_2.hdf5'
    with h5py.File(sPath, 'r') as f:
        Data_Q = np.array(f['Traces/Predistortion - Response'].value)
        t0dt = np.array(f['Traces/Predistortion - Response_t0dt'].value)
        length = float(f['Traces/Predistortion - Response_N'].value)
        vResponse_Q = complex(1,0)*Data_Q[:,0,0].ravel()+complex(0,1)*Data_Q[:,1,0].ravel()
        vRTime_Q = np.linspace(t0dt[0,0], length*t0dt[0,1], length)
        print(Data_Q.shape)
