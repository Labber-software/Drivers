#!/usr/bin/env python
import numpy as np
import scipy.linalg as splin
import time
import sys

# add logger, to allow logging to Labber's instrument log
import logging
log = logging.getLogger('LabberDriver')

MAC = (sys.platform == 'darwin')

if MAC:
    pass
#    import pyximport
#    pyximport.install(setup_args={"include_dirs":np.get_include()},
#                      reload_support=True)
else:
    pass
#    pyximport.install(setup_args={"script_args":["--compiler=mingw32"],
#                      "include_dirs":np.get_include()},
#                      reload_support=True)

from _integrateHNoNumpy_ForDriver import integrateH, integrateH_RWA, goToRotatingFrame

#import matplotlib.pyplot as plt

class NoiseCfg():
    
    # define local variables
    __MODELS__ = ['1/f', 'Static', 'White']
    NOISE1F = 0
    NOISESTATIC = 1
    NOISEWHITE = 2

    def __init__(self, bEmpty=False):
        # init with some default settings
        self.model = self.NOISESTATIC
        self.deltaAmp = 1E6
        self.epsAmp = 0
        self.driveAmp = 0
        self.hiCutOff = 50E9
        self.bAddStatic = False
        self.repRate = 1E3
        if bEmpty:
            self.deltaAmp = 0
            
    def calc1fNoise(self, dTimeStep, nPtsIn=1):
        def nextpow2(i):
            n = 2
            while n < i:
                n = n * 2
            return n
            
        # make nPts even number
#        nPts = 2*np.ceil(nPtsIn/2.)
        nPts = nextpow2(nPtsIn)
        # define frequency information
        # low and high cut-offs
        dFs = 1/(dTimeStep)
        dHighCut = dFs/2
        vFreq = np.linspace(0, dHighCut, nPts+1)
        # remove zero frequency
        vFreq = vFreq[1:]
        # create frequency data
        vFreqData = np.sqrt(np.diff(vFreq[0:2])/vFreq)
        # add random phase factor
        vFreqData = vFreqData*np.exp(1j*2*np.pi*np.random.rand(len(vFreqData)))
        # add zero frequency part
        vFreq = np.r_[0, vFreq[1:-1]]
        vFreqData = np.r_[0, vFreqData, vFreqData[-2::-1]]
        vTimeData = len(vFreqData) * np.real(np.fft.ifft(vFreqData))#, \
#                                             nextpow2(len(vFreqData))))
        # cut extra elements
        vTimeData = vTimeData[0:nPtsIn]
        return vTimeData

            
    def getNoise(self, dTimeStep, nLen=1):
        # caclulates a noise vector
        # 
        if self.model == NoiseCfg.NOISESTATIC:
            # static noise, don't return any time-dependent noise
            return 0.0
        #
        # calculate smallest time step of the noise
        dtNoise = 1./(2.*self.hiCutOff)
        # number of constant elements
        nConst = int(np.around(dtNoise/dTimeStep))
        if nConst<1:
            nConst = 1
            dtNoise = dTimeStep
        # number of unique elements
        nElem = int(np.ceil(nLen/nConst))
        # get the unique noise vector
        if self.model == NoiseCfg.NOISE1F:
            # 1/f noise
            vUnique = self.calc1fNoise(dtNoise, nElem)
        elif self.model == NoiseCfg.NOISEWHITE:
            # white noise, return a vector
            vUnique = np.random.randn(nElem) #*np.sqrt(1/dtNoise)
        # create the full-length vector by keeping constant elements
        vNoise = np.reshape(np.outer(vUnique, np.ones(nConst)), nElem*nConst)
        return vNoise[0:nLen]
#        # create linear interpolation between elements
#        vdNoise = np.diff(vUnique)
#        vdNoise = np.append(vdNoise, 0)
#        vShift = np.reshape(np.outer(vdNoise, np.arange(nConst)/nConst), nElem*nConst)
#        return vNoise[0:nLen] + vShift[0:nLen]


    def addNoise(self, vDelta, vDetuning, dTimeStep, dScale=1):
        # add noise to delta and detuning vectors
        vNoise = self.getNoise(dTimeStep, max(len(vDelta), len(vDetuning)))
        # add noise only if amplitude is not zero
        if self.deltaAmp!=0:
            vDelta += (self.deltaAmp)*vNoise*dScale
        if self.epsAmp!=0:
            vDetuning += (self.epsAmp)*vNoise*dScale
            

    def addStaticNoise(self, vDelta, vDetuning, vStaticDrive, dHighFreq, dScale=1):
        nElem = max(len(vDelta), len(vDetuning))
        if self.model == NoiseCfg.NOISESTATIC:
            # static noise, create noise vector
            vNoise =  np.random.randn(nElem)
        elif self.model == NoiseCfg.NOISE1F and self.bAddStatic:
            # for 1/f, add noise at rep rate
            # calculate noise level from 1/f limits
            dIntNoise = np.sqrt(np.log(10)*(np.log10(dHighFreq) - 
                              np.log10(self.repRate)))
            # add noise to delta and detuning vectors
            vNoise = np.random.randn(nElem)*dIntNoise
        else:
            # all other cases, add no noise
            vNoise = 0.0
        # add noise only if amplitude is not zero
        if self.deltaAmp!=0:
            vDelta += (self.deltaAmp)*vNoise*dScale
        if self.epsAmp!=0:
            vDetuning += (self.epsAmp)*vNoise*dScale
        if self.driveAmp!=0:
            vStaticDrive += (self.driveAmp)*vNoise


    def getNoiseTypes(self):
        return self.__MODELS__


    def getNoiseType(self):
        return self.__MODELS__[self.model]



class QubitSimulator():

    def __init__(self, simCfg = None):
        # init the object variables
        self.dDelta = 5
        self.dRabiAmp = 0.1
        self.dTimeStep = 0.0005
        self.nReshape = 100
        self.dDetuning = 0
        self.nRep = 1
        self.dDriveFreq = 0
        self.bRelFreq = True
        self.bRWA = False
        self.bRotFrame = True
        self.bRemoveNoise = False
        self.lNoiseCfg = [] # [NoiseCfg(bEmpty = True)]
        if simCfg is not None:
            # update simulation options
            self.updateSimCfg(simCfg)

                   
    def updateSimCfg(self, simCfg):
        # update simulation options
        for key, value in simCfg.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
       
    def integrateH(self, vStart, vTime, vDelta, vDetuning, nReshape):
        # simulate the time evolution for the start state vStart
        # a state is defined as [Psi0 Psi1]'
        # a vector of states is a matrix, defined as [state1 state2 ... stateN]
        #
        # pre-allocate space for the output variable
        mState = np.zeros((2,len(vTime)), dtype='complex128')
        # use start vector for the first entry
        mState[:,0] = vStart
        # get time steps
        vDTime = np.diff(vTime)
        # precalc vectors
        vEnergy = 0.5*np.sqrt(vDelta**2 + vDetuning**2)
        vAngle = 2*np.pi*vEnergy[0:-1]*vDTime
        vCos = np.cos(vAngle)
        vSin = np.sin(vAngle)
        # pre-define matrices
        mIdentity = np.eye(2)
        mSx = np.array([[0.,1.],[1.,0.]])
        mSz = np.array([[1.,0.],[0.,-1.]])
        # apply hamiltonian N times
        for n1, dTime in enumerate(vDTime):
           # define hamiltonian
           H = -0.5 * (mSx*vDelta[n1] + mSz*vDetuning[n1])
           # define time-evolution operator
           U = mIdentity * vCos[n1] - 1j*H*vSin[n1]/vEnergy[n1]
           # calculate next state
           mState[:,n1+1] = np.dot(U,mState[:,n1])
        # reshape data to reduce vector size
        if nReshape>1:
           mState = mState[:,0::nReshape]
        return mState
        

    def integrateH_RWA(self, vStart, vTime, vDelta, vDetX, vDetY, nReshape):
        # simulate the time evolution for the start state vStart
        # a state is defined as [Psi0 Psi1]'
        # a vector of states is a matrix, defined as [state1 state2 ... stateN]
        #
        # pre-allocate space for the output variable
        mState = np.zeros((2,len(vTime)), dtype='complex128')
        # use start vector for the first entry
        mState[:,0] = vStart
        # get time steps
        vDTime = np.diff(vTime)
        # precalc vectors
        vEnergy = 1E-200 + 0.5*np.sqrt(vDelta**2 + vDetX**2 + vDetY**2)
        vAngle = 2*np.pi*vEnergy[0:-1]*vDTime
        vCos = np.cos(vAngle)
        vSin = np.sin(vAngle)
        # pre-define matrices
        mIdentity = np.eye(2)
        mSx = np.array([[0.,1.],[1.,0.]])
        mSy = np.array([[0.,-1j],[1j,0.]])
        mSz = np.array([[1.,0.],[0.,-1.]])
        # apply hamiltonian N times
        for n1, dTime in enumerate(vDTime):
           # define hamiltonian
           H = -0.5 * (mSx*vDelta[n1] + mSz*vDetX[n1] + mSy*vDetY[n1])
           # define time-evolution operator
           U = mIdentity * vCos[n1] - 1j*H*vSin[n1]/vEnergy[n1]
           # calculate next state
           mState[:,n1+1] = np.dot(U,mState[:,n1])
        # reshape data to reduce vector size
        if nReshape>1:
           mState = mState[:,0::nReshape]
        return mState


    def goToRotatingFrame(self, mState, vTime, dDriveFreq, dTimeZero):
        vRot = np.exp(-1j*np.pi*dDriveFreq*(vTime-dTimeZero))
        mState[0,:] = vRot*mState[0,:] 
        mState[1,:] = mState[1,:]/vRot 
        return mState
        
#        for n2, dTime in enumerate(vTime):
#            A11 = np.exp(-1j*np.pi*dDriveFreq*(dTime-dTimeZero))
#            A22 = 1/A11
#            mState[0,n2] = A11*mState[0,n2] 
#            mState[1,n2] = A22*mState[1,n2]
#        return mState
        
#        mSz = np.array([[1., 0.],[0., -1.]])
#            mState[:,n2] = np.dot(splin.expm2(-1j*2*np.pi*dDriveFreq * \
#                      (dTime-dTimeZero)*0.5*mSz),mState[:,n2])
           
           
    def convertToEigen(self, mStateIn, dDelta, dDetuning):
        # converts a state in right/left basis to the local basis set by Delta, detuning
        # a state is defined as [Psi0 Psi1]'
        # a vector of states is a matrix, defined as [state1 state2 ... stateN]
        # get hamiltonian
        H = -0.5 * np.array([[dDetuning, dDelta],[dDelta, -dDetuning]])
        # find eigenvalues of H, lowest value first 
        mEigVal,mEigVec = np.linalg.eig(H)
        idx = mEigVal.argsort()
        mEigVec = mEigVec[:,idx]
        # transform using inverse of the eigenvectors
        # if MAC:
        #     A = np.linalg.inv(mEigVec)
        #     return np.dot(A,mStateIn)
        return np.linalg.solve(mEigVec,mStateIn)


    def convertToLeftRight(self, mStateIn, dDelta, dDetuning):
        # converts a state in right/left basis to the local basis set by Delta, detuning
        # a state is defined as [Psi0 Psi1]'
        # a vector of states is a matrix, defined as [state1 state2 ... stateN]
        # get hamiltonian
        H = -0.5 * np.array([[dDetuning, dDelta],[dDelta, -dDetuning]])
        # find eigenvalues of H, lowest value first 
        mEigVal,mEigVec = np.linalg.eig(H)
        idx = mEigVal.argsort()
        mEigVec = mEigVec[:,idx]
        # transform using inverse of the eigenvectors
        return np.dot(mEigVec,mStateIn)

    def simulate(self, vI, vQ, dTimeStep, dDelta, dDetuning, dRabiAmp, \
                            dDriveFreq, nReshape, nRep, lNoise, bRWA=False,
                            bRotFrame=True, hDriveFunc=None,
                            noise_epsilon=None, noise_delta=None):
        # simulate the time evolution for the start state vStart
        # a state is defined as [Psi0 Psi1]'
        # a vector of states is a matrix, defined as [state1 state2 ... stateN]
        #
        # define start state
        vStart = np.r_[1,0]
        dDelta0 = dDelta
        # project the start state to a right/left circulating current basis
        vStart = self.convertToLeftRight(vStart, dDelta0, dDetuning)
        # introduce a drive to the detuning
        vTime = np.arange(len(vI))*dTimeStep
        dTimeZero = 0
        # check if rotating wave approximation
        if bRWA:
            dDelta = dDelta - dDriveFreq
            dDriveFreq = 0
            vDetuning = dDetuning - 1j*dRabiAmp*vI*0.5 + dRabiAmp*vQ*0.5
        else:
            if hDriveFunc is None:
                vDetuning = dDetuning - \
                    dRabiAmp*vI*np.sin(2*np.pi*dDriveFreq*(vTime)) + \
                    dRabiAmp*vQ*np.cos(2*np.pi*dDriveFreq*(vTime))
            else:
                vDetuning = dDetuning + hDriveFunc(vTime, vI, vQ)
        #
        # pre-allocate result vector
        vTimeReshape = vTime[0::nReshape]
        vP1 = np.zeros(len(vTimeReshape))
        vPx = np.zeros(len(vTimeReshape))
        vPy = np.zeros(len(vTimeReshape))
        #
        self.mPx = np.zeros((nRep, len(vTimeReshape)))
        self.mPy = np.zeros((nRep, len(vTimeReshape)))
        self.mPz = np.zeros((nRep, len(vTimeReshape)))
        #
        mSx = np.array([[0., 1.],[1., 0.]])
        mSy = np.array([[0., -1j],[1j, 0.]])
        # create static noise vector
        vStaticDelta = np.zeros(nRep)
        vStaticDet = np.zeros(nRep)
        vStaticDrive = np.zeros(nRep)
        if nRep>1:
            # high-frequency cut-off for static noise is length of waveform
            dStaticHF = 1/(1e-9*vTime[-1])
            for noise in lNoise:
                noise.addStaticNoise(vStaticDelta, vStaticDet, vStaticDrive, 
                                     dStaticHF, 1E-9)

        # figure out resampling of input noise
        if (noise_epsilon is not None):
            n = len(noise_epsilon['y']) // nRep
            noise_epsilon_t = np.arange(n) * noise_epsilon['dt'] * 1E9
            # create matrix with noise data
            noise_eps_m = 1E-9 * noise_epsilon['y'][:(nRep * n)].reshape((nRep, n))

        if (noise_delta is not None):
            n = len(noise_delta['y']) // nRep
            noise_delta_t = np.arange(n) * noise_delta['dt'] * 1E9
            # create matrix with noise data
            noise_delta_m = 1E-9 * noise_delta['y'][:(nRep * n)].reshape((nRep, n))

        # calculate color codes based on total noise
        vColNoise = (vStaticDelta + vStaticDet)
        dNoiseColAmp = np.max(np.abs(vColNoise))
        if dNoiseColAmp>0:
            vColNoise /= dNoiseColAmp
        # rotatation matrice
        mRotX = splin.expm(-1j*0.5*np.pi*0.5*mSx)
        mRotY = splin.expm(-1j*0.5*np.pi*0.5*mSy)
        for n1 in range(nRep):
            # create new vectors for delta and detuning for each time step
            vDelta = dDelta * np.ones(len(vTime)) + vStaticDelta[n1]
            vDetNoise = vDetuning.copy()*(1.0+vStaticDrive[n1]) + vStaticDet[n1]
            # add noise to both delta and epsilon from all noise sources
            if nRep>1:
                for noise in lNoise:
                    noise.addNoise(vDelta, vDetNoise, dTimeStep*1E-9, 1E-9)
            # add externally applied noise for the right rep
            if (noise_epsilon is not None):
                noise_data = np.interp(vTime, noise_epsilon_t, noise_eps_m[n1])
                if self.bRemoveNoise:
                    # remove data where pulses are applied
                    pulse_indx = np.where(np.abs(vDetuning - dDetuning) > 1E-15)[0]
                    noise_data[pulse_indx] = 0.0
                vDetNoise += noise_data
            if (noise_delta is not None):
                noise_data = np.interp(vTime, noise_delta_t, noise_delta_m[n1])
                if self.bRemoveNoise:
                    # remove data where pulses are applied
                    pulse_indx = np.where(np.abs(vDetuning - dDetuning) > 1E-15)[0]
                    noise_data[pulse_indx] = 0.0
                vDelta += noise_data
 
             # do simulation
            if bRWA:
                mState = integrateH_RWA(vStart, vTime, vDelta, np.real(vDetNoise),
                                        np.imag(vDetNoise), nReshape)
                # mState = self.integrateH_RWA(vStart, vTime, vDelta, np.real(vDetNoise),
                #                              np.imag(vDetNoise), nReshape)
            else:
                mState = integrateH(vStart, vTime, vDelta, vDetNoise, nReshape)
                # mState = self.integrateH(vStart, vTime, vDelta, vDetNoise, nReshape)
            # convert the results to an eigenbasis of dDelta, dDetuning
            mState = self.convertToEigen(mState, dDelta0, dDetuning)
            # go to the rotating frame (add timeStep/2 to get the right phase)
            if bRotFrame and not bRWA:
                mState = self.goToRotatingFrame(mState, vTimeReshape, dDriveFreq, dTimeZero+dTimeStep/2)
            # get probablity of measuring p1
            mStateEig = mState
            self.mPz[n1,:] = np.real(mStateEig[1,:]*np.conj(mStateEig[1,:]))
            vP1 += self.mPz[n1,:]
            # get projection on X and Y
            mStateEig = np.dot(mRotX,mState)
            self.mPx[n1,:] = np.real(mStateEig[1,:]*np.conj(mStateEig[1,:]))
            vPx += self.mPx[n1,:]
            mStateEig = np.dot(mRotY,mState)
            self.mPy[n1,:] = np.real(mStateEig[1,:]*np.conj(mStateEig[1,:]))
            vPy += self.mPy[n1,:]
        # divide to get average
        vP1 = vP1/nRep
        vPx = vPx/nRep
        vPy = vPy/nRep
        # convert to projections
        vP1 = -(2*vP1 - 1)
        vPx = 2*vPx - 1
        vPy = 2*vPy - 1
        self.mPz = -(2*self.mPz - 1)
        self.mPx = 2*self.mPx - 1
        self.mPy = 2*self.mPy - 1
        return  (vP1, vPx, vPy, vTimeReshape, vColNoise)


    def getDriveVector(self, dPos = 0, iPos=None):
        if iPos is None:
            iPos = np.floor(dPos * self.vI.shape[0])
        # get frequeny detuning
        dFreq = np.sqrt(self.dDetuning**2+self.dDelta**2)
        if self.bRelFreq:
            dFreqMW = self.dDriveFreq + dFreq
            dFreqDet = self.dDriveFreq
        else:
            dFreqDet = self.dDriveFreq - dFreq
            dFreqMW = self.dDriveFreq
        # check if in rotating frame
        if self.bRotFrame:
            # rotating frame
            vDrive = np.array([self.vI[iPos], self.vQ[iPos],
                              dFreqDet/self.dRabiAmp])/self.AWG.maxAmp
        else:
            # lab frame, add oscillations to drive vector
            vDrive = np.array([ 
                self.vI[iPos]*(np.cos(2*np.pi*dFreqMW*self.vTime[iPos])), 
                self.vQ[iPos]*(np.cos(2*np.pi*dFreqMW*self.vTime[iPos])), 
                dFreqDet/self.dRabiAmp])/self.AWG.maxAmp
        return vDrive
                          


    def performSimulation(self, vI, vQ, dTimeStepIn, dTimeStepOut,
                          noise_epsilon=None, noise_delta=None):
        start_time = time.time()
        # update sample rate to match time step
        if dTimeStepIn != self.dTimeStep:
            # resample drive waveforms
            vTime = dTimeStepIn * np.arange(len(vI), dtype=float)
            vTimeSim = self.dTimeStep * np.arange(int(len(vI)*dTimeStepIn/self.dTimeStep), dtype=float)
            vI = np.interp(vTimeSim, vTime, vI)
            vQ = np.interp(vTimeSim, vTime, vQ)
        # calculate re-shape factor
        if dTimeStepOut > self.dTimeStep:
            self.nReshape = int(np.round(dTimeStepOut/self.dTimeStep))
        else:
            self.nReshape = 1
        dTimeStepOut = self.dTimeStep * self.nReshape
        # update sample rate to match time step
        if self.bRelFreq:
            dFreq = np.sqrt(self.dDetuning**2+self.dDelta**2)
            dDriveFreq = self.dDriveFreq + dFreq
        else:
            dDriveFreq = self.dDriveFreq
        # do simulation
        (vPz, vPx, vPy, vTime, vColNoise) = self.simulate(vI, vQ, self.dTimeStep, self.dDelta, \
             self.dDetuning, 2*self.dRabiAmp, dDriveFreq, self.nReshape, \
             self.nRep, self.lNoiseCfg, self.bRWA, self.bRotFrame,
             noise_epsilon=noise_epsilon, noise_delta=noise_delta)
        end_time = time.time()
        self.simulationTime = end_time-start_time
        return (vPz, vPx, vPy, dTimeStepOut)
 