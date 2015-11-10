#!/usr/bin/env python

import AlazarTech_Digitizer_Wrapper as AlazarDig
import InstrumentDriver
import numpy as np

class Error(Exception):
    pass

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements the Acqiris card driver"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # init object
        self.dig = None
        # keep track of sampled traces
        self.lTrace = [np.array([]), np.array([])]
        self.lSignalNames = ['Ch1 - Data', 'Ch2 - Data']
        self.dt = 1.0
        # open connection
        boardId = int(self.comCfg.address)
        self.dig = AlazarDig.AlazarTechDigitizer(systemId=1, boardId=boardId)
        self.dig.testLED()


    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        del self.dig


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # start with setting current quant value
        quant.setValue(value) 
         # don't do anything until all options are set, then set complete config
        if self.isFinalCall(options):
            self.setConfiguration()
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # only implmeneted for traces
        if quant.name in self.lSignalNames:
            # check if first call, if so get new traces
            if self.isFirstCall(options):
                self.getTraces()
            indx = self.lSignalNames.index(quant.name)
            # return correct data
            value = quant.getTraceDict(self.lTrace[indx], dt=self.dt)
        else:
            # just return the quantity value
            value = quant.getValue()
        return value


    def setConfiguration(self):
        """Set digitizer configuration based on driver settings"""
        # clock configuration
        SourceId = int(self.getCmdStringFromValue('Clock source'))
        if self.getValue('Clock source') == 'Internal':
            # internal
            SampleRateId = int(self.getCmdStringFromValue('Sample rate'),0)
            lFreq = [1E3, 2E3, 5E3, 10E3, 20E3, 50E3, 100E3, 200E3, 500E3,
                     1E6, 2E6, 5E6, 10E6, 20E6, 50E6, 100E6, 200E6, 500E6, 1E9]
            Decimation = 0
        else:
            # 10 MHz ref, use 1GHz rate + divider. NB!! divide must be 1,2,4,10 
            SampleRateId = int(1E9)
            lFreq = [1E3, 2E3, 5E3, 10E3, 20E3, 50E3, 100E3, 200E3, 500E3,
                     1E6, 2E6, 5E6, 10E6, 20E6, 50E6, 100E6, 250E6, 500E6, 1E9]
            Decimation = int(round(1E9/lFreq[self.getValueIndex('Sample rate')]))
        self.dig.AlazarSetCaptureClock(SourceId, SampleRateId, 0, Decimation)
        # define time step from sample rate
        self.dt = 1/lFreq[self.getValueIndex('Sample rate')]
        # 
        # configure inputs
        for n in range(2):
            if self.getValue('Ch%d - Enabled' % (n+1)):
                # coupling and range
                Coupling = int(self.getCmdStringFromValue('Ch%d - Coupling' % (n+1)))
                InputRange = int(self.getCmdStringFromValue('Ch%d - Range' % (n+1)))
                Impedance = int(self.getCmdStringFromValue('Ch%d - Impedance' % (n+1)))
                self.dig.AlazarInputControl(n+1, Coupling, InputRange, Impedance)
                # bandwidth limit
                BW = int(self.getValue('Ch%d - Bandwidth limit' % (n+1)))
                self.dig.AlazarSetBWLimit(n+1, BW)
        # 
        # configure trigger
        Source = int(self.getCmdStringFromValue('Trig source'))
        Slope = int(self.getCmdStringFromValue('Trig slope'))
        Delay = self.getValue('Trig delay')
        # trig level is relative to full range
        trigLevel = self.getValue('Trig level')
        vAmp = np.array([4, 2, 1, 0.4, 0.2, 0.1, .04], dtype=float)
        if self.getValue('Trig source') == 'Channel 1':
            maxLevel = vAmp[self.getValueIndex('Ch1 - Range')]
        elif self.getValue('Trig source') == 'Channel 2':
            maxLevel = vAmp[self.getValueIndex('Ch2 - Range')]
        elif self.getValue('Trig source') == 'External':
            maxLevel = 5.0
        # convert relative level to U8
        if abs(trigLevel)>maxLevel:
            trigLevel = maxLevel*np.sign(trigLevel)
        Level = int(128 + 127*trigLevel/maxLevel)
        # set config
        self.dig.AlazarSetTriggerOperation(0, 0, Source, Slope, Level)
        # 
        # config external input, if in use
        if self.getValue('Trig source') == 'External':
            Coupling = int(self.getCmdStringFromValue('Trig coupling'))
            self.dig.AlazarSetExternalTrigger(Coupling)
        # 
        # set trig delay and timeout
        Delay = int(self.getValue('Trig delay')/self.dt)
        self.dig.AlazarSetTriggerDelay(Delay)
        timeout = self.dComCfg['Timeout']
        self.dig.AlazarSetTriggerTimeOut(time=timeout)


    def getTraces(self):
        """Resample the data"""
        # get new trace
        self.lTrace = [np.array([]), np.array([])]
        # get channels in use
        bGetCh1 = bool(self.getValue('Ch1 - Enabled'))
        bGetCh2 = bool(self.getValue('Ch2 - Enabled'))
        if (not bGetCh1) and (not bGetCh2):
            return
        # set data and record size
        nPreSize = int(self.getValue('Pre-trig samples'))
        nPostSize = int(self.getValue('Post-trig samples'))
        nRecord = int(self.getValue('Number of records'))
        self.dig.AlazarSetRecordSize(nPreSize, nPostSize)
        self.dig.AlazarSetRecordCount(nRecord)
        # start aquisition
        self.dig.AlazarStartCapture()
        nTry = self.dComCfg['Timeout']/0.05
        while nTry>0 and self.dig.AlazarBusy() and not self.isStopped():
            # sleep for a while to save resources, then try again
            self.thread().msleep(50)
            nTry -= 1
        # check if timeout occurred
        if nTry <= 0:
            self.dig.AlazarAbortCapture()
            raise Error('Acquisition timed out')
        # check if user stopped
        if self.isStopped():
            self.dig.AlazarAbortCapture()
            return
        #
        # read data for channels in use
        if bGetCh1:
            self.lTrace[0] = self.dig.readTraces(1)
        if bGetCh2:
            self.lTrace[1] = self.dig.readTraces(2)



if __name__ == '__main__':
    pass
