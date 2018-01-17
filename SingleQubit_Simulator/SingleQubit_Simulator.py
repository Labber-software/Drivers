#!/usr/bin/env python

import InstrumentDriver
import numpy as np
from QubitSimulator_ForDriver import NoiseCfg, QubitSimulator


class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements a Single-qubit simulator"""
    

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # init variables
        self.qubitSim = QubitSimulator()
        self.vPolarization = np.zeros((3,))
        self.lTrace = [np.array([], dtype=float) for n in range(3)]
        self.dTimeStepOut = 0.0


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # do nothing, just return value
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        dPol = {'Polarization - X': 0, 'Polarization - Y': 1, 'Polarization - Z': 2}
        dTrace = {'Trace - Px': 0, 'Trace - Py': 1, 'Trace - Pz': 2}
        # check type of quantity
        if quant.name in (list(dPol.keys()) + list(dTrace.keys())):
            # output data, check if simulation needs to be performed
            if self.isConfigUpdated():
                self.performSimulation()
            # get new value
            if quant.name in dPol:
                value = self.vPolarization[dPol[quant.name]]
            elif quant.name in dTrace:
                # get correct data and return as trace dict
                vData = self.lTrace[dTrace[quant.name]]
                value = quant.getTraceDict(vData, dt=self.dTimeStepOut)
        else:
            # otherwise, just return current value
            value = quant.getValue()
        return value


    def performSimulation(self):
        """Perform simulation"""
        # get config values
        dConfig = dict(dDelta=self.getValue('Delta')/1E9,
                       dRabiAmp=self.getValue('Drive amplitude')/1E9,
                       dTimeStep=1E9*self.getValue('Time step, simulation'),
                       dDetuning=self.getValue('Epsilon')/1E9,
                       nRep=int(self.getValue('Number of randomizations')),
                       dDriveFreq=self.getValue('Drive frequency')/1E9,
                       bRelFreq=bool(self.getValue('Drive relative to qubit frequency')),
                       bRotFrame=bool(self.getValue('Use rotating frame')),
                       bRWA=bool(self.getValue('Use rotating-wave approximation')))
        # get noise config
        nNoise = int(self.getValueIndex('Noise sources'))
        lNoiseCfg = []
        for n in range(nNoise):
            Noise = NoiseCfg()
            # noise type
            sType = self.getValue('Noise type %d' % (n+1))
            if sType == 'Static':
                Noise.model = NoiseCfg.NOISESTATIC
            elif sType == '1/f':
                Noise.model = NoiseCfg.NOISE1F
            elif sType == 'White':
                Noise.model = NoiseCfg.NOISEWHITE
            # other cfg values
            Noise.deltaAmp = self.getValue('Noise, Delta %d' % (n+1))
            Noise.epsAmp = self.getValue('Noise, Epsilon %d' % (n+1))
            Noise.driveAmp = self.getValue('Noise, Drive %d' % (n+1))
            Noise.hiCutOff = self.getValue('High-freq cut-off %d' % (n+1))
            Noise.bAddStatic = self.getValue('Include 1/f at low frequencies %d' % (n+1))
            Noise.repRate = self.getValue('Pulse sequence rep. rate %d' % (n+1))
            # add to list
            lNoiseCfg.append(Noise)
        dConfig['lNoiseCfg'] = lNoiseCfg
        # update config
        self.qubitSim.updateSimCfg(dConfig)
        # get I/Q from input data
        vI = self.getValue('Trace - I')['y']
        vQ = self.getValue('Trace - Q')['y']
        dTimeStepIn = 1E9 * self.getValue('Trace - I')['dt']
        dTimeStepOut = 1E9 * self.getValue('Time step, output traces')
        # do simulation
        if len(vI)>0 and len(vQ)>0:
            (vPz, vPx, vPy, dTimeStepOut) = self.qubitSim.performSimulation(
                                            vI, vQ, dTimeStepIn, dTimeStepOut)
            self.vPolarization = np.array([vPx[-1], vPy[-1], vPz[-1]])
            self.lTrace = [vPx, vPy, vPz]
            self.dTimeStepOut = 1E-9 * dTimeStepOut


if __name__ == '__main__':
    pass
