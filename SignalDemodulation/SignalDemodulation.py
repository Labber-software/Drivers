#!/usr/bin/env python

import InstrumentDriver
import numpy as np


class Error(Exception):
    pass

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements a demodulation driver"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        pass


    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        pass


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # do nothing here
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        if quant.name == 'Value':
            # calculate I/Q signal here
            value = np.mean(self.getIQAmplitudes())
        elif quant.name == 'Value - Single shot':
            # calculate I/Q signal here
            value = self.getIQAmplitudes()
        elif quant.name.startswith('Value #'):
            index = int(quant.name[-1])
            sDemodFreq = 'Mod. frequency #' + str(index)
            dFreq = self.getValue(sDemodFreq)
            value = np.mean(self.getIQAmplitudes_MultiFreq(dFreq))
        else:
            # just return the quantity value
            value = quant.getValue()
        return value

    def getIQAmplitudes(self):
        """Calculate complex signal from data and reference"""
        # get parameters
        dFreq = self.getValue('Modulation frequency')
        skipStart = self.getValue('Skip start')
        nSegment = int(self.getValue('Number of segments'))
        # get input data from dict, with keys {'y': value, 't0': t0, 'dt': dt}
        traceIn = self.getValue('Input data')
        if traceIn is None:
            return complex(0.0)
        vY = traceIn['y']     
        dt = traceIn['dt']
        # get shape of input data
        shape = traceIn.get('shape', vY.shape)
        # override segment parameter if input data has more than one dimension
        if len(shape) > 1:
            nSegment = shape[0]
        # avoid exceptions if no time step is given
        if dt==0:
            dt = 1.0
        skipIndex = int(round(skipStart/dt))
        nTotLength = vY.size
        length = 1 + int(round(self.getValue('Length')/dt))
        length = min(length, int(nTotLength/nSegment)-skipIndex)
        if length <=1:
            return complex(0.0)
        bUseRef = bool(self.getValue('Use phase reference signal'))
        # define data to use, put in 2d array of segments
        vData = np.reshape(vY, (nSegment, int(nTotLength/nSegment)))
        # calculate cos/sin vectors, allow segmenting
        vTime = dt * (skipIndex + np.arange(length, dtype=float))
        vCos = np.cos(2*np.pi * vTime * dFreq)
        vSin = np.sin(2*np.pi * vTime * dFreq)
        # calc I/Q
        dI = 2. * np.trapz(vCos * vData[:,skipIndex:skipIndex+length]) / float(length-1)
        dQ = 2. * np.trapz(vSin * vData[:,skipIndex:skipIndex+length]) / float(length-1)
        signal = dI + 1j*dQ
        if bUseRef:
            traceRef = self.getValue('Reference data')
            # skip reference if trace length doesn't match
            if len(traceRef['y']) != len(vY):
                return signal
            vRef = np.reshape(traceRef['y'], (nSegment, int(nTotLength/nSegment)))
            dIref = 2. * np.trapz(vCos * vRef[:,skipIndex:skipIndex+length]) / float(length-1)
            dQref = 2. * np.trapz(vSin * vRef[:,skipIndex:skipIndex+length]) / float(length-1)
            # subtract the reference angle
            dAngleRef = np.arctan2(dQref, dIref)
            signal /= (np.cos(dAngleRef) + 1j*np.sin(dAngleRef))
        return signal
    


    def getIQAmplitudes_MultiFreq(self,dFreq):
        """Calculate complex signal from data and reference"""
        # get parameters
        skipStart = self.getValue('Skip start')
        nSegment = int(self.getValue('Number of segments'))
        # get input data from dict, with keys {'y': value, 't0': t0, 'dt': dt}
        traceIn = self.getValue('Input data')
        if traceIn is None:
            return complex(0.0)
        vY = traceIn['y']     
        dt = traceIn['dt']
        # get shape of input data
        shape = traceIn.get('shape', vY.shape)
        # override segment parameter if input data has more than one dimension
        if len(shape) > 1:
            nSegment = shape[0]
        # avoid exceptions if no time step is given
        if dt==0:
            dt = 1.0
        skipIndex = int(round(skipStart/dt))
        nTotLength = vY.size
        length = 1 + int(round(self.getValue('Length')/dt))
        length = min(length, int(nTotLength/nSegment)-skipIndex)
        if length <=1:
            return complex(0.0)
        bUseRef = bool(self.getValue('Use phase reference signal'))
        # define data to use, put in 2d array of segments
        vData = np.reshape(vY, (nSegment, int(nTotLength/nSegment)))
        # calculate cos/sin vectors, allow segmenting
        vTime = dt * (skipIndex + np.arange(length, dtype=float))
        vCos = np.cos(2*np.pi * vTime * dFreq)
        vSin = np.sin(2*np.pi * vTime * dFreq)
        # calc I/Q
        dI = 2. * np.trapz(vCos * vData[:,skipIndex:skipIndex+length]) / float(length-1)
        dQ = 2. * np.trapz(vSin * vData[:,skipIndex:skipIndex+length]) / float(length-1)
        signal = dI + 1j*dQ
        if bUseRef:
            traceRef = self.getValue('Reference data')
            # skip reference if trace length doesn't match
            if len(traceRef['y']) != len(vY):
                return signal
            vRef = np.reshape(traceRef['y'], (nSegment, int(nTotLength/nSegment)))
            dIref = 2. * np.trapz(vCos * vRef[:,skipIndex:skipIndex+length]) / float(length-1)
            dQref = 2. * np.trapz(vSin * vRef[:,skipIndex:skipIndex+length]) / float(length-1)
            # subtract the reference angle
            dAngleRef = np.arctan2(dQref, dIref)
            signal /= (np.cos(dAngleRef) + 1j*np.sin(dAngleRef))
        return signal


if __name__ == '__main__':
    pass
