#!/usr/bin/env python

import InstrumentDriver
import numpy as np


class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements a Single-qubit pulse generator"""


    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # init variables
        nTrace = 4
        self.lI = [np.array([], dtype=float) for n in range(nTrace)]
        self.lQ = [np.array([], dtype=float) for n in range(nTrace)]
        self.lGate = [np.array([], dtype=float) for n in range(nTrace)]
        self.vTime = np.array([], dtype=float)
        self.vReadout = np.array([], dtype=float)


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # do nothing, just return value
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check type of quantity
        if quant.isVector():
            # traces, check if waveform needs to be re-calculated
            if self.isConfigUpdated():
                self.calculateWaveform()
            # get correct data and return as trace dict
            vData = self.getWaveformFromMemory(quant)
            dt = 1/self.getValue('Sample rate')
            value = quant.getTraceDict(vData, dt=dt)
        else:
            # for all other cases, do nothing
            value = quant.getValue()
        return value


    def getWaveformFromMemory(self, quant):
        """Return data from already calculated waveforms"""
        if quant.name[-1] in ('1','2','3','4'):
            name = quant.name[:-1]
            n = int(quant.name[-1]) - 1
        else:
            name = quant.name
            n = 0
        # special case for readout (only one vector available)
        if quant.name == 'Trace - Readout':
            vData = self.vReadout
        else:
            dTrace = {'Trace - I': self.lI, 'Trace - Q': self.lQ,
                      'Trace - Gate': self.lGate}
            vData = dTrace[name][n]
        return vData


    def getPulseEnvelope(self, nType, dTime, bTimeStart=False):
        """Get pulse envelope for a given pulse"""
        sPulseType = self.getValue('Pulse type')
        dSampleRate = self.getValue('Sample rate')
        truncRange = self.getValue('Truncation range')
        start_at_zero = self.getValue('Start at zero')
        # get pulse params
        dAmp = self.getValue('Amplitude #%d' % nType)
        dWidth = self.getValue('Width #%d' % nType)
        dPlateau = self.getValue('Plateau #%d' % nType)
        # get pulse width
        if sPulseType == 'Square':
            dTotTime = dWidth+dPlateau
        elif sPulseType == 'Ramp':
            dTotTime = 2*dWidth+dPlateau
        elif sPulseType == 'Gaussian':
            dTotTime = truncRange*dWidth + dPlateau
        # shift time to mid point if user gave start point
        if bTimeStart:
            dTime = dTime + dTotTime/2
        # get the range of indices in use
        vIndx = np.arange(max(np.round((dTime-dTotTime/2)*dSampleRate), 0),
                          min(np.round((dTime+dTotTime/2)*dSampleRate), len(self.vTime)))
        vIndx = np.int0(vIndx)
        # calculate time values for the pulse indices
        vTime = vIndx/dSampleRate
        # calculate the actual value for the selected indices
        if sPulseType == 'Square':
            vPulse = (vTime >= (dTime-(dWidth+dPlateau)/2)) & \
                 (vTime < (dTime+(dWidth+dPlateau)/2))
        elif sPulseType == 'Ramp':
            # rising and falling slopes
            vRise = (vTime-(dTime-dPlateau/2-dWidth))/dWidth
            vRise[vRise<0.0] = 0.0
            vRise[vRise>1.0] = 1.0
            vFall = ((dTime+dPlateau/2+dWidth)-vTime)/dWidth
            vFall[vFall<0.0] = 0.0
            vFall[vFall>1.0] = 1.0
            vPulse = vRise * vFall
#            vPulse = np.min(1, np.max(0, (vTime-(dTime-dPlateau/2-dWidth))/dWidth)) * \
#               np.min(1, np.max(0, ((dTime+dPlateau/2+dWidth)-vTime)/dWidth))
        elif sPulseType == 'Gaussian':
            # width is two times std
            #dStd = dWidth/2;
            # alternate def; std is set to give total pulse area same as a square
            dStd = dWidth/np.sqrt(2*np.pi)
            # cut the tail part and increase the amplitude, if necessary
            dOffset = 0
            if dPlateau > 0:
                # add plateau
                vPulse = (vTime >= (dTime-dPlateau/2)) & \
                    (vTime < (dTime+dPlateau/2))
                if dStd > 0:
                    # before plateau
                    vPulse = vPulse + (vTime < (dTime-dPlateau/2)) * \
                        (np.exp(-(vTime-(dTime-dPlateau/2))**2/(2*dStd**2))-dOffset)/(1-dOffset)
                    # after plateau
                    vPulse = vPulse + (vTime >= (dTime+dPlateau/2)) * \
                        (np.exp(-(vTime-(dTime+dPlateau/2))**2/(2*dStd**2))-dOffset)/(1-dOffset)
            else:
                if dStd > 0:
                    vPulse = (np.exp(-(vTime-dTime)**2/(2*dStd**2))-dOffset)/(1-dOffset)
                else:
                    vPulse = np.zeros_like(vTime)
#        # add the pulse to the previous ones
#        vY[iPulse] = vY[iPulse] + dAmp * vPulse
        vPulse = dAmp * vPulse
        if start_at_zero:
            vPulse = vPulse - vPulse.min()
            vPulse = vPulse/vPulse.max()*dAmp
        # return both time, envelope, and indices
        return (vTime, vPulse, vIndx)


    def addPulse(self, nType, dTime, nOutput=None, bTimeStart=False, phase=None):
        """Add pulse to waveform"""
        # check if output is given, if not take from pulse cfg
        if nOutput is None:
            nOutput = self.getValueIndex('Output #%d' % nType)
        # make sure output exists, otherwise put on output 1
        if nOutput > self.getValueIndex('Number of outputs'):
            nOutput = 0
        # get phase either from control or from function input
        if phase is None:
            phase = self.getValue('Phase #%d' % nType) * np.pi/180.
        # get reference to data
        vI, vQ = self.lI[nOutput], self.lQ[nOutput]
        # get pulse envelope
        vTime, vPulse, vIndx = self.getPulseEnvelope(nType, dTime, bTimeStart)
        if len(vTime) == 0:
            return
        # apply DRAG, if wanted
        if self.getValue('Use DRAG'):
            beta = self.getValue('DRAG scaling')*self.getValue('Sample rate')
            vIout = vPulse
            vQout = beta * np.gradient(vPulse)
        else:
            vIout, vQout = vPulse, np.zeros_like(vPulse)
        # continue depending on SSB or envelope mixing
        if self.getValue('Use SSB mixing'):
            # SSB mixing, get parameters
            freq = 2*np.pi*self.getValue('Mod. frequency #%d' % nType)
            ratioIQ = self.getValue('Ratio I/Q #%d' % nType)
            phaseDiff = self.getValue('Phase diff. #%d' % nType) * np.pi/180.
            # apply SSBM pretransform (and phase correction to Q channel)
            vI_ssbm = vIout * (np.cos(freq*vTime - phase)) + \
                     -vQout * (np.cos(freq*vTime - phase + np.pi/2))
            vQ_ssbm =-vIout * (np.sin(freq*vTime - phase + phaseDiff)) + \
                      vQout * (np.sin(freq*vTime - phase + np.pi/2 + phaseDiff))
            # apply amplitude correction to Q channel
            vQ_ssbm = ratioIQ * vQ_ssbm
            # store result
            vI[vIndx] += vI_ssbm
            vQ[vIndx] += vQ_ssbm
        else:
            # just add envelopes to I/Q
            vI[vIndx] += vIout*np.cos(-phase) - vQout*np.cos(-phase + np.pi/2)
            vQ[vIndx] += -vIout*np.sin(-phase) + vQout*np.sin(-phase + np.pi/2)


    def getPulseDuration(self, nType):
        """Get total pulse duration waveform, for timimg purposes"""
        # check if edge-to-edge
        if self.getValue('Edge-to-edge pulses'):
            width = self.getValue('Width #%d' % nType)
            plateau = self.getValue('Plateau #%d' % nType)
            pulseEdgeWidth = self.getValue('Edge position')
            return pulseEdgeWidth * width + plateau
        else:
            return 0.0


    def generatePrePulses(self, startTime):
        """Add pre-pulses, return time after pre-pulses end"""
        # get params
        if not self.getValue('Add pre-pulses'):
            return startTime
        nPulse = int(self.getValue('Number of pre-pulses'))
        period = self.getValue('Pre-pulse period')
        iPulseDef = 1 + self.getValueIndex('Pre-pulse definition')
        # add pulses, spaced by the period
        t = startTime
        for n in range(nPulse):
            self.addPulse(iPulseDef, t)
            t += period
        return t


    def generateStateTomography(self, startTime=0.0):
        """Generate state tomography pulse"""
        # get params, state index is cycled 0,1,2,0,1,2,0,1, ....
        stateIndex = int(self.getValue('State index')) % 3
        delay = self.getValue('Tomography delay')
        iPulseDef = 1 + self.getValueIndex('Definition, pi/2 pulse')
        if not self.getValue('Generate tomography pulse') or stateIndex==0:
            return
        # get time for tomography pulse by finding last non-zero vector entry
        vAny = np.zeros_like(self.vTime)
        for (vI, vQ) in zip(self.lI, self.lQ):
            vAny += np.abs(vI)+np.abs(vQ)
        lNonZero = np.where(vAny>0)[0]
        # if data is not all zero, add state pulses after last pulse
        if len(lNonZero)>0:
            startTime = self.vTime[lNonZero[-1]]
        # update pi/2 pulse to be either 0 or pi/2 phase
        phase = 0.0 if stateIndex==1 else np.pi/2
        self.addPulse(iPulseDef, startTime+delay, phase=phase, bTimeStart=True)


    def generateReadout(self, startTime=0.0):
        """Generate readout waveform"""
        # get parameters
        if not self.getValue('Generate readout'):
            return
        delay = self.getValue('Readout delay')
        amp = self.getValue('Readout amplitude')
        duration = self.getValue('Readout duration')
        sampleRate = self.getValue('Sample rate')
        # create interpolation vectors
        if self.getValue('Sample-and-hold readout'):
            prebias = self.getValue('Pre-bias')
            hold = self.getValue('Hold')
            retrap = self.getValue('Re-trap')
            prebias_t = self.getValue('Pre-bias time')
            rise_t = self.getValue('Rise time')
            fall_t = self.getValue('Fall time')
            hold_t = self.getValue('Hold time')
            retrap_t =self.getValue('Re-trap time')
            lAmp = [0.0]
            lTime = [0.0]
            # add to interpolation vectors
            if prebias_t>0:
                lAmp += [prebias, prebias]
                lTime += [rise_t, prebias_t]
            lAmp += [amp, amp, hold, hold]
            lTime += [rise_t, duration, fall_t, hold_t]
            if retrap_t>0:
                lAmp += [retrap, retrap]
                lTime += [fall_t, retrap_t]
            lAmp += [0.0]
            lTime += [fall_t]
            # sum up times
            for n in range(len(lTime)-1):
                lTime[n+1] += lTime[n]
        else:
            lAmp = [0.0, amp, amp, 0.0]
            lTime = [0.0, 0.0, duration, duration]
        # calculate data
        nData = int(np.round(lTime[-1]*sampleRate))
        vTime = np.arange(nData, dtype=float)/sampleRate
        vAmp = np.interp(vTime, lTime, lAmp)
        # get time for read-out pulse by finding last non-zero vector entry
        vAny = np.zeros_like(self.vTime)
        for (vI, vQ) in zip(self.lI, self.lQ):
            vAny += np.abs(vI)+np.abs(vQ)
        lNonZero = np.where(vAny>0)[0]
        # if data is not all zero, add state pulses after last pulse
        if len(lNonZero)>0:
            startTime = self.vTime[lNonZero[-1]]
        # add data to read-out vector
        iStart = 1 + int(np.round((startTime + delay)*sampleRate))
        nTot = min(nData, len(self.vReadout)-iStart)
        self.vReadout[iStart:(iStart+nTot)] = vAmp[:nTot]


    def generateGate(self):
        """Generate gate waveform"""
        # get config values
        delay = self.getValue('Gate delay')
        overlap = self.getValue('Gate overlap')
        sampleRate = self.getValue('Sample rate')
        minTime = self.getValue('Minimal gate time')
        # the uniform gate is all ones, except for first/last
        if self.getValue('Uniform gate'):
            for n in range(len(self.lGate)):
                self.lGate[n] = np.ones_like(self.vTime)
                self.lGate[n][0] = 0.0
                self.lGate[n][-1] = 0.0
            return
        # normal gate
        for n, (vI, vQ) in enumerate(zip(self.lI, self.lQ)):
            vGate = np.array((np.abs(vI)+np.abs(vQ))>0.0, dtype=float)
            # fix gate overlap
            nOverlap = int(np.round(overlap*sampleRate))
            vDiff = np.diff(vGate)
            vUp = np.nonzero(vDiff>0.0)[0]
            vDown = np.nonzero(vDiff<0.0)[0]
            # special case for first one
            if len(vUp)>0 and vUp[0]<nOverlap:
                vGate[:vUp[0]+1] = 1.0
            for indx in vUp:
                vGate[indx-nOverlap:indx+1] = 1.0
            for indx in vDown:
                vGate[indx:indx+nOverlap+1] = 1.0
            # fix gaps in gate shorter than min (look for 1>0)
            vDiff = np.diff(vGate)
            vUp = np.nonzero(vDiff>0.0)[0]
            vDown = np.nonzero(vDiff<0.0)[0]
            if vGate[0]==0:
                vUp = vUp[1:]
            nDownUp = min(len(vDown), len(vUp))
            vLenDown = vUp[:nDownUp] - vDown[:nDownUp]
            # find short gaps
            vShort = np.nonzero(vLenDown < minTime*sampleRate)[0]
            for indx in vShort:
                vGate[vDown[indx]:(1+vUp[indx])] = 1.0
            # shift gate in time
            nDelay = int(np.round(delay*sampleRate))
            if nDelay<0:
                nDelay = abs(nDelay)
                vGate = np.r_[vGate[nDelay:], np.zeros((nDelay,))]
            elif nDelay>0:
                vGate = np.r_[np.zeros((nDelay,)), vGate[:(-nDelay)]]
            # make sure gate starts/ends in 0
            vGate[0] = 0.0
            vGate[-1] = 0.0
            self.lGate[n] = vGate



    def calculateWaveform(self):
        """Generate waveforms, including pre-pulses, readout and gates"""
        # get config values
        nPoints = int(self.getValue('Number of points'))
        sampleRate = self.getValue('Sample rate')
        firstDelay = self.getValue('First pulse delay')
        bReadout = self.getValue('Generate readout')
        bGate = self.getValue('Generate gate')
        nOutput = 1 + int(self.getValueIndex('Number of outputs'))
        # start with allocating time and amplitude vectors
        self.vTime = np.arange(nPoints, dtype=float)/sampleRate
        if bReadout:
            self.vReadout = np.zeros_like(self.vTime)
        else:
            self.vReadout = np.array([], dtype=float)
        # create list of output vectors
        self.lI = [np.zeros_like(self.vTime) for n in range(nOutput)]
        self.lQ = [np.zeros_like(self.vTime) for n in range(nOutput)]
        self.lGate = [np.array([], dtype=float) for n in range(nOutput)]
        # add pre-pulses
        timePos = self.generatePrePulses(startTime=firstDelay)
        # go on depending on with sequence
        self.generateSequence(startTime=timePos)
        # generate tomography pulse
        self.generateStateTomography(startTime=timePos)
        # generate readout pulse
        if bReadout:
            self.generateReadout(startTime=timePos)
        # generate gate
        if bGate:
            self.generateGate()
        # check is swap IQ
        if self.getValue('Swap IQ'):
            self.lI, self.lQ = self.lQ, self.lI
        # trim the waveforms to actual length
        if self.getValue('Trim waveform to sequence'):
            # find last index where any of the waveforms is on
            vAny = np.zeros_like(self.vTime)
            for (vI, vQ) in zip(self.lI, self.lQ):
                vAny += np.abs(vI)+np.abs(vQ)
            if bReadout:
                vAny += np.abs(self.vReadout)
            if bGate and not self.getValue('Uniform gate'):
                for vGate in self.lGate:
                    vAny += vGate
            lNonZero = np.where(vAny>0)[0]
            # don't trim if all data is zero
            if len(lNonZero)>0:
                # check first part, add one element, unless the index is first
                iFirst = lNonZero[0]
                iFirst = max(iFirst-1, 0)
                # end part, add one element, unless the index is the last element
                iLast = lNonZero[-1]
                iLast = min(iLast+2, len(vAny))
                # resize the vectors
                self.vTime = self.vTime[iFirst:iLast]
                for n, (vI, vQ) in enumerate(zip(self.lI, self.lQ)):
                    self.lI[n] = vI[iFirst:iLast]
                    self.lQ[n] = vQ[iFirst:iLast]
                    if bGate:
                        self.lGate[n] = self.lGate[n][iFirst:iLast]
                        self.lGate[n][0] = 0.0
                        self.lGate[n][-1] = 0.0
                if bReadout:
                    self.vReadout = self.vReadout[iFirst:iLast]
        # add zeros to front of waveform, if wanted
        if self.getValue('Buffer start to restore size'):
            vBuf = np.zeros(nPoints - len(self.lI[0]))
            self.vTime = np.r_[vBuf, self.vTime]
            for n, (vI, vQ) in enumerate(zip(self.lI, self.lQ)):
                self.lI[n] = np.r_[vBuf, vI]
                self.lQ[n] = np.r_[vBuf, vQ]
                if bGate:
                    self.lGate[n] = np.r_[vBuf, self.lGate[n]]
            if bReadout:
                self.vReadout = np.r_[vBuf, self.vReadout]



    def generateSequence(self, startTime):
        # get config values
        sSequence = self.getValue('Sequence')
        nPulses = int(self.getValue('# of pulses'))
        seqPeriod = self.getValue('Pulse period')
        # go on depending on waveform
        if sSequence == 'Rabi':
            # Rabi is just one pulse, add it at the start
            self.addPulse(1, startTime, bTimeStart=True)
        elif sSequence == 'CP/CPMG':
            # get length of actual pulses
            dPulseT1 = self.getPulseDuration(1)
            dPulseT2 = self.getPulseDuration(2)
            dPulseTot = 2*dPulseT1 + dPulseT2*nPulses
            # add the first pi/2 pulses
            self.addPulse(1, startTime + dPulseT1/2)
            # add more pulses
            if nPulses <= 0:
                # no pulses = ramsey
                vTimePi = []
                # second pi/2 pulse
                self.addPulse(1, startTime + seqPeriod + dPulseTot - dPulseT1/2)
            elif nPulses == 1:
                # one pulse, echo experiment
                vTimePi = [startTime + dPulseT1 + seqPeriod/2 + dPulseT2/2]
                # second pi/2 pulse
                self.addPulse(1, startTime + seqPeriod + dPulseTot - dPulseT1/2)
            elif nPulses > 1:
                # figure out timing of pi pulses
                vTimePi = startTime  + dPulseT1 + seqPeriod/2 + dPulseT2/2 + \
                          (seqPeriod + dPulseT2)*np.arange(nPulses)
                # second pi/2 pulse
                self.addPulse(1, startTime + nPulses*seqPeriod + dPulseTot - dPulseT1/2)
            # add pi pulses, one by one
            for dTimePi in vTimePi:
                self.addPulse(2, dTimePi)
        elif sSequence == 'Pulse train':
            # check if alternating pulses
            nAlternate = int(self.getValue('# of alternating pulses'))
            # keep track of time
            t = startTime
            for n1 in range(nPulses):
                # add each different pulse type
                for n2 in range(nAlternate):
                    # get length of current pulses
                    dPulseT = self.getPulseDuration(n2+1)
                    self.addPulse(n2+1, t + dPulseT/2)
                    # add current pulse length
                    t += seqPeriod + dPulseT
        elif sSequence == 'Generic sequence':
            # generic pulse sequence, add the pulses specified in the pulse list
            t = startTime
            for n in range(nPulses):
                pulseType = 1 + (n % 8)
                # get length of current pulse
                dPulseT = self.getPulseDuration(pulseType)
                self.addPulse(pulseType, t + dPulseT/2)
                # add spacing as defined for this pulse
                t += dPulseT + self.getValue('Spacing #%d' % (pulseType))


if __name__ == '__main__':
    pass
