#!/usr/bin/env python

import AcqirisWrapper as Aq
import InstrumentDriver
from InstrumentConfig import InstrumentQuantity
import numpy as np

class Error(Exception):
    pass

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements the Acqiris card driver"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # init object
        self.dig = None
        # keep track of sampled traces, elements are I, Q, signal, single shot
        self.lTrace = [np.array([]), np.array([]), 0.0, np.array([], dtype=complex)]
        self.lSignalNames = ['Ch1 - Data', 'Ch2 - Data', 'Signal', 'Signal - Single shot']
        self.dt = 1.0
        try:
            # open connection
            self.dig = Aq.AcqirisDigitizer()
            self.dig.init(self.comCfg.address, True, True)
        except Exception as e:
            # re-cast afdigitizer errors as a generic communication error
            msg = str(e)
            raise InstrumentDriver.CommunicationError(msg)


    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # check if digitizer object exists
        try:
            if self.dig is None:
                # do nothing, object doesn't exist (probably was never opened)
                return
        except:
            # never return error here, do nothing, object doesn't exist
            return
        try:
            # close and remove object
            self.dig.close()
            self.dig.closeAll()
            del self.dig
        except:
            # never return error here
            pass


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # start with setting current quant value
        quant.setValue(value)
        # get values from relevant quants
        if quant.name == 'Acquisition type':
            mode = int(quant.getCmdStringFromValue(value))
            self.dig.configMode(mode)
            # update # of samples parameter, since it may change when averaging
            self.readValueFromOther('Number of samples')
        elif quant.name in ('Number of samples', 'Number of segments'):
            # first, single trace cfg, get values from relevant quants and set all
            nSample = int(self.getValue('Number of samples'))
            nSegment = int(self.getValue('Number of segments'))
            self.dig.configMemory(nSample, nSegment)
            # set averager settings
            if quant.name == 'Number of samples':
                self.dig.configAvgConfig(1, 'NbrSamples',  int(value))
                self.dig.configAvgConfig(2, 'NbrSamples',  int(value))
            elif quant.name == 'Number of segments':
                self.dig.configAvgConfig(1, 'NbrSegments',  int(value))
                self.dig.configAvgConfig(2, 'NbrSegments',  int(value))
        elif quant.name == 'Number of averages':
            self.dig.configAvgConfig(1, 'NbrWaveforms',  int(value))
            self.dig.configAvgConfig(2, 'NbrWaveforms',  int(value))
        elif quant.name in ('Sample interval', 'Delay time'):
            sampInterval = self.getValue('Sample interval')
            delayTime = self.getValue('Delay time')
            # set single trace or sample interval
            self.dig.configHorizontal(sampInterval, delayTime)
            if quant.name == 'Delay time':
                # for averaging mode, set delay in data points
                self.dig.configAvgConfig(1, 'StartDelay', int(value/sampInterval))
                self.dig.configAvgConfig(2, 'StartDelay', int(value/sampInterval))
        elif quant.name in ('Trig source', 'Trig coupling', 'Trig slope', 'Trig level'):
            # get values from relevant quants and set all
            trigSource = int(self.getCmdStringFromValue('Trig source'))
            trigCoupling = int(self.getCmdStringFromValue('Trig coupling'))
            trigSlope = int(self.getCmdStringFromValue('Trig slope'))
            trigLevel = self.getValue('Trig level')
            # trig level is in percentage if trig is Ch1/Ch2, convert to voltage
            if trigSource == 1:
                fullRange = float(self.getCmdStringFromValue('Ch1 - Range'))
                offset = float(self.getValue('Ch1 - Offset'))
                trigLevel = 100*(0.5 - (offset + fullRange/2.0 - trigLevel)/fullRange)
            elif trigSource == 2:
                fullRange = float(self.getCmdStringFromValue('Ch2 - Range'))
                offset = float(self.getValue('Ch2 - Offset'))
                trigLevel = 100*(0.5 - (offset + fullRange/2.0 - trigLevel)/fullRange)
            else:
                # trig level is in millivolt
                trigLevel = trigLevel*1000.0
            self.dig.configTrigSource(trigSource, trigCoupling, trigSlope, trigLevel,
                         trigLevel2=0.0)
            # change active trigger if source was changed 
            if quant.name == 'Trig source':
                dPattern = {1: 0x00000001, 2: 0x00000002, -1: 0x80000000}
                self.dig.configTrigClass(dPattern[trigSource])
        elif quant.name == 'Ch1 - Enabled':
            # do nothing for enabling/disabling
            pass 
        elif quant.name in ('Ch1 - Coupling', 'Ch1 - Bandwidth', 'Ch1 - Range',  'Ch1 - Offset'):
            # get values from relevant quants and set all
            fullScale = float(self.getCmdStringFromValue('Ch1 - Range'))
            offset = float(self.getValue('Ch1 - Offset'))
            coupling = int(self.getCmdStringFromValue('Ch1 - Coupling'))
            bandwidth = int(self.getCmdStringFromValue('Ch1 - Bandwidth'))
            self.dig.configVertical(1, fullScale, -offset, coupling, bandwidth)
            # re-set trigger level, if needed (to reflect new offset/range)
            trigSource = int(self.getCmdStringFromValue('Trig source'))
            if trigSource == 1:
                trigLev = float(self.getValue('Trig level'))
                self.sendValueToOther('Trig level', trigLev)
        elif quant.name == 'Ch2 - Enabled':
            # do nothing
            pass
        elif quant.name in ('Ch2 - Coupling', 'Ch2 - Bandwidth', 'Ch2 - Range',  'Ch2 - Offset'):
            # get values from relevant quants and set all
            fullScale = float(self.getCmdStringFromValue('Ch2 - Range'))
            offset = float(self.getValue('Ch2 - Offset'))
            coupling = int(self.getCmdStringFromValue('Ch2 - Coupling'))
            bandwidth = int(self.getCmdStringFromValue('Ch2 - Bandwidth'))
            self.dig.configVertical(2, fullScale, -offset, coupling, bandwidth)
            # re-set trigger level, if needed (to reflect new offset/range)
            trigSource = int(self.getCmdStringFromValue('Trig source'))
            if trigSource == 2:
                trigLev = float(self.getValue('Trig level'))
                self.sendValueToOther('Trig level', trigLev)
        elif quant.name in ('Modulation frequency', 'Skip start', 'Length',
                            'Use Ch2 as reference'):
             # do nothing for these quantities, the value will be stored in local quant
             pass
        # finish set value with get value, to make sure we catch any coercing
        return self.performGetValue(quant)


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        aqType = self.getValue('Acquisition type')
        if quant.name == 'Acquisition type':
            value = quant.getValueFromCmdString(str(self.dig.getMode()[0]))
        elif quant.name == 'Number of samples':
            if aqType == 'Normal':
                value = float(self.dig.getMemory()[0])
            else:
                value = float(self.dig.getAvgConfig(1, 'NbrSamples'))
        elif quant.name == 'Number of segments':
            if aqType == 'Normal':
                value = float(self.dig.getMemory()[1])
            else:
                value = float(self.dig.getAvgConfig(1, 'NbrSegments'))
        elif quant.name == 'Number of averages':
            value = float(self.dig.getAvgConfig(1, 'NbrWaveforms'))
        elif quant.name == 'Sample interval':
            value = float(self.dig.getHorizontal()[0])
        elif quant.name == 'Delay time':
            if aqType == 'Normal':
                value = float(self.dig.getHorizontal()[1])
            else:
                # convert from delay in points to delay in time
                sampInterval = self.getValue('Sample interval')
                value = sampInterval * self.dig.getAvgConfig(1, 'StartDelay')
        elif quant.name == 'Trig source':
            pattern = abs(self.dig.getTrigClass()[0])
            dPattern = {0x00000001L: 1, 0x00000002L: 2, 0x80000000L: -1}
            value = quant.getValueFromCmdString(str(dPattern[pattern]))
        elif quant.name == 'Trig coupling':
            # get from current trig source
            trigSource = int(self.getCmdStringFromValue('Trig source'))
            value = quant.getValueFromCmdString( \
                    str(self.dig.getTrigSource(trigSource)[0]))
        elif quant.name == 'Trig slope':
            # get from current trig source
            trigSource = int(self.getCmdStringFromValue('Trig source'))
            value = quant.getValueFromCmdString( \
                    str(self.dig.getTrigSource(trigSource)[1]))
        elif quant.name == 'Trig level':
            # get from current trig source
            trigSource = int(self.getCmdStringFromValue('Trig source'))
            trigLevel = self.dig.getTrigSource(trigSource)[2]
            # if Ch1/Ch2, trig level is percentage of full range
            if trigSource == 1:
                fullRange = float(self.getCmdStringFromValue('Ch1 - Range'))
                offset = float(self.getValue('Ch1 - Offset'))
                value = offset + fullRange*trigLevel/100.0
            elif trigSource == 2:
                fullRange = float(self.getCmdStringFromValue('Ch2 - Range'))
                offset = float(self.getValue('Ch2 - Offset'))
                value = offset + fullRange*trigLevel/100.0
            else:
                # trig level is in millivolt
                value = trigLevel/1000.0
        elif quant.name == 'Ch1 - Enabled':
            # do nothing for enabling/disabling
            value = quant.getValue()
        elif quant.name == 'Ch1 - Coupling':
            value = quant.getValueFromCmdString(str(self.dig.getVertical(1)[2]))
        elif quant.name == 'Ch1 - Bandwidth':
            value = quant.getValueFromCmdString(str(self.dig.getVertical(1)[3]))
        elif quant.name == 'Ch1 - Range':
            value = quant.getValueFromCmdString('%.2f' % self.dig.getVertical(1)[0])
        elif quant.name == 'Ch1 - Offset':
            value = - self.dig.getVertical(1)[1]
        elif quant.name == 'Ch2 - Enabled':
            # do nothing
            value = quant.getValue()
        elif quant.name == 'Ch2 - Coupling':
            value = quant.getValueFromCmdString(str(self.dig.getVertical(2)[2]))
        elif quant.name == 'Ch2 - Bandwidth':
            value = quant.getValueFromCmdString(str(self.dig.getVertical(2)[3]))
        elif quant.name == 'Ch2 - Range':
            value = quant.getValueFromCmdString('%.2f' % self.dig.getVertical(2)[0])
        elif quant.name == 'Ch2 - Offset':
            value = - self.dig.getVertical(2)[1]
        # signals
        elif quant.name in self.lSignalNames:
            indx = self.lSignalNames.index(quant.name)
            # check if first call, if so get new traces
            if self.isFirstCall(options):
                self.getTraces()
            # return correct data
            if quant.name in ('Ch1 - Data', 'Ch2 - Data'):
                value = InstrumentQuantity.getTraceDict(self.lTrace[indx], dt=self.dt)
            else:
                value = self.lTrace[indx]
        elif quant.name in ('Modulation frequency', 'Skip start', 'Length',
                            'Use Ch2 as reference', 'Enable demodulation'):
            # just return the quantity value
            value = quant.getValue()
        return value


    def getTraces(self):
        """Resample the data"""
        self.lTrace = [np.array([]), np.array([]), 0.0, np.array([], dtype=complex)]
        # get new trace
        nSample = int(self.getValue('Number of samples'))
        nSegment = int(self.getValue('Number of segments'))
        nAverage = int(self.getValue('Number of averages'))
        bDemodulation = bool(self.getValue('Enable demodulation'))
        bGetCh1 = bool(self.getValue('Ch1 - Enabled'))
        bGetCh2 = bool(self.getValue('Ch2 - Enabled'))
        if (not bGetCh1) and (not bGetCh2):
            return
        lChannel = []
        if bGetCh1:
            lChannel.append(1)
        if bGetCh2:
            lChannel.append(2)
        aqType = self.getValue('Acquisition type')
        bAverageMode = True if aqType == 'Average' else False
        (vData, self.dt) = self.dig.readChannelsToNumpy(nSample, lChannel=lChannel, nAverage=nAverage,
                        nSegment=nSegment, timeout=10000, bAverageMode=bAverageMode)
        # put the resulting data in arrays for Ch1/Ch2
        if bGetCh1:
            self.lTrace[0] = vData[0]
            if bGetCh2:
                self.lTrace[1] = vData[1]
        else:
            self.lTrace[1] = vData[0]
        # temporary, calculate I/Q signal here
        if bDemodulation and self.dt>0:
            self.lTrace[3] = self.getIQAmplitudes()
            self.lTrace[2] = np.mean(self.lTrace[3])
        else:
            self.lTrace[3] = np.array([], dtype=complex)
            self.lTrace[2] = 0.0 + 0j


    def getIQAmplitudes(self):
        """Calculate complex signal from data and reference"""
        # get parameters
        dFreq = self.getValue('Modulation frequency')
        skipStart = self.getValue('Skip start')
        nSegment = int(self.getValue('Number of segments'))
        skipIndex = int(round(skipStart/self.dt))
        nTotLength = self.lTrace[0].size
        length = 1 + int(round(self.getValue('Length')/self.dt))
        length = min(length, nTotLength/nSegment-skipIndex)
        bUseRef = bool(self.getValue('Use Ch2 as reference'))
        # define data to use, put in 2d array of segments
        vData = np.reshape(self.lTrace[0], (nSegment, nTotLength/nSegment))
        # calculate cos/sin vectors, allow segmenting
        vTime = self.dt * (skipIndex + np.arange(length, dtype=float))
        vCos = np.cos(2*np.pi * vTime * dFreq)
        vSin = np.sin(2*np.pi * vTime * dFreq)
        # calc I/Q
        dI = 2. * np.trapz(vCos * vData[:,skipIndex:skipIndex+length]) / float(length-1)
        dQ = 2. * np.trapz(vSin * vData[:,skipIndex:skipIndex+length]) / float(length-1)
        signal = dI + 1j*dQ
        if bUseRef:
            vRef = np.reshape(self.lTrace[1], (nSegment, nTotLength/nSegment))
            dIref = 2. * np.trapz(vCos * vRef[:,skipIndex:skipIndex+length]) / float(length-1)
            dQref = 2. * np.trapz(vSin * vRef[:,skipIndex:skipIndex+length]) / float(length-1)
            # subtract the reference angle
            dAngleRef = np.arctan2(dQref, dIref)
            signal /= (np.cos(dAngleRef) + 1j*np.sin(dAngleRef))
#        elif nSegment>1:
#            # return absolute value if segmenting without reference
#            signal = np.abs(signal)
#        signal = np.mean(signal)
        return signal



if __name__ == '__main__':
    pass
