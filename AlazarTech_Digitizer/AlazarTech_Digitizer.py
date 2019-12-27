#!/usr/bin/env python

import AlazarTech_Digitizer_Wrapper as AlazarDig
import InstrumentDriver
import numpy as np
from scipy.interpolate import interp1d

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
        self.signal_index = {
            'Ch1 - Data': 0,
            'Ch2 - Data': 1,
            'FFT - Data': 0}
        # add single-frequency values
        for n in range(9):
            self.signal_index['FFT - Value %d' % (n+1)] = 0
        self.dt = 1.0
        # open connection
        boardId = int(self.comCfg.address)
        timeout = self.dComCfg['Timeout']
        self.dig = AlazarDig.AlazarTechDigitizer(
            systemId=1, boardId=boardId, timeout=timeout)
        self.dig.testLED()
        options = []
        if self.dig.fft_enabled:
            options.append('FFT')
        self.setInstalledOptions(options)


    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # try to remove buffers
        try:
            self.dig.removeBuffersDMA()
        except:
            pass
        # remove digitizer object
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
        if quant.name in self.signal_index:
            # special case for hardware looping
            if self.isHardwareLoop(options):
                return self.getSignalHardwareLoop(quant, options)
            # check if first call, if so get new traces
            if self.isFirstCall(options):
                # clear trace buffer
                self.lTrace = [np.array([]), np.array([])]
                # read traced to buffer, proceed depending on model
                if self.getModel() in ('9870',):
                    self.getTracesNonDMA()
                else:
                    self.getTracesDMA(hardware_trig=self.isHardwareTrig(options))
            value = self.extract_trace_value(quant)
        else:
            # just return the quantity value
            value = quant.getValue()
        return value


    def performArm(self, quant_names, options={}):
        """Perform the instrument arm operation"""
        # arming is only implemented for DMA reaoud
        if self.getModel() in ('9870',):
            return
        # make sure we are arming for reading traces, if not return
        signals = [name in self.signal_index for name in quant_names]
        if not np.any(signals):
            return
        # get config
        bGetCh1 = bool(self.getValue('Ch1 - Enabled'))
        bGetCh2 = bool(self.getValue('Ch2 - Enabled'))
        nSample = int(self.getValue('Number of samples'))
        nRecord = int(self.getValue('Number of records'))
        nAverage = int(self.getValue('Number of averages'))
        nBuffer = int(self.getValue('Records per Buffer'))
        nMemSize = int(self.getValue('Max buffer size'))
        nMaxBuffer = int(self.getValue('Max number of buffers'))
        fft_config = self.get_fft_config()
        if (not bGetCh1) and (not bGetCh2):
            return
        # configure and start acquisition
        if self.isHardwareLoop(options):
            # in hardware looping, number of records is set by the hardware looping
            (seq_no, n_seq) = self.getHardwareLoopIndex(options)
            # disable trig timeout (set to 3 minutes)
            self.dig.AlazarSetTriggerTimeOut(self.dComCfg['Timeout'] + 180.0)
            # need to re-configure the card since record size was not known at config
            self.dig.readTracesDMA(bGetCh1, bGetCh2, nSample, n_seq, nBuffer, nAverage,
                                   bConfig=True, bArm=True, bMeasure=False, 
                                   bufferSize=nMemSize, maxBuffers=nMaxBuffer,
                                   fft_config=fft_config)
        else:
            # if not hardware looping, just trig the card, buffers are already configured 
            self.dig.readTracesDMA(bGetCh1, bGetCh2, nSample, nRecord, nBuffer, nAverage,
                                   bConfig=False, bArm=True, bMeasure=False,
                                   bufferSize=nMemSize, maxBuffers=nMaxBuffer,
                                   fft_config=fft_config)


    def _callbackProgress(self, progress):
        """Report progress to server, as text string"""
        s = 'Acquiring traces (%.0f%%)' % (100*progress)
        self.reportStatus(s)


    def getSignalHardwareLoop(self, quant, options):
        """Get data from round-robin type averaging"""
        (seq_no, n_seq) = self.getHardwareLoopIndex(options)
        # if first sequence call, get data
        if seq_no == 0 and self.isFirstCall(options):
            bGetCh1 = bool(self.getValue('Ch1 - Enabled'))
            bGetCh2 = bool(self.getValue('Ch2 - Enabled'))
            nSample = int(self.getValue('Number of samples'))
            nAverage = int(self.getValue('Number of averages'))
            nBuffer = int(self.getValue('Records per Buffer'))
            nMemSize = int(self.getValue('Max buffer size'))
            nMaxBuffer = int(self.getValue('Max number of buffers'))
            fft_config = self.get_fft_config()
            # show status before starting acquisition
            self.reportStatus('Digitizer - Waiting for signal')
            # get data
            (vCh1, vCh2) = self.dig.readTracesDMA(bGetCh1, bGetCh2,
                           nSample, n_seq, nBuffer, nAverage,
                           bConfig=False, bArm=False, bMeasure=True,
                           funcStop=self.isStopped,
                           funcProgress=self._callbackProgress,
                           firstTimeout=self.dComCfg['Timeout']+180.0,
                           bufferSize=nMemSize,
                           maxBuffers=nMaxBuffer,
                           fft_config=fft_config)
            # re-shape data and place in trace buffer
            nSample = len(vCh1) / n_seq
            self.lTrace[0] = vCh1.reshape((n_seq, nSample))
            self.lTrace[1] = vCh2.reshape((n_seq, nSample))
        # after getting data, pick values to return
        value = self.extract_trace_value(quant, seq_no)
        return value


    def setConfiguration(self):
        """Set digitizer configuration based on driver settings"""
        # clock configuration
        SourceId = int(self.getCmdStringFromValue('Clock source'))
        if self.getValue('Clock source') == 'Internal':
            # internal
            SampleRateId = int(self.getCmdStringFromValue('Sample rate'),0)
            lFreq = [1E3, 2E3, 5E3, 10E3, 20E3, 50E3, 100E3, 200E3, 500E3,
                     1E6, 2E6, 5E6, 10E6, 20E6, 50E6, 100E6, 200E6, 500E6, 1E9,
                     1.2E9, 1.5E9, 2E9, 2.4E9, 3E9, 3.6E9, 4E9]
            Decimation = 0
        elif self.getValue('Clock source') == '10 MHz Reference' and self.getModel() in ('9373','9360'):
            # 10 MHz ref, for 9373 - decimation is 1
            #for now don't allow DES mode; talk to Simon about best implementation
            lFreq = [1E3, 2E3, 5E3, 10E3, 20E3, 50E3, 100E3, 200E3, 500E3,
                     1E6, 2E6, 5E6, 10E6, 20E6, 50E6, 100E6, 200E6, 500E6, 1E9,
                     1.2E9, 1.5E9, 2E9, 2.4E9, 3E9, 3.6E9, 4E9]
            SampleRateId = int(lFreq[self.getValueIndex('Sample rate')])
            Decimation = 0
        else:
            # 10 MHz ref, use 1GHz rate + divider. NB!! divide must be 1,2,4, or mult of 10 
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
                if self.getModel() in ('9373', '9360'):
                    # these options are not available for these models, set to default
                    Coupling = 2
                    InputRange = 7
                    Impedance = 2
                else:
                    Coupling = int(self.getCmdStringFromValue('Ch%d - Coupling' % (n+1)))
                    InputRange = int(self.getCmdStringFromValue('Ch%d - Range' % (n+1)))
                    Impedance = int(self.getCmdStringFromValue('Ch%d - Impedance' % (n+1)))
                #set coupling, input range, impedance
                self.dig.AlazarInputControl(n+1, Coupling, InputRange, Impedance)
                # bandwidth limit, only for model 9870
                if self.getModel() in ('9870',):
                    BW = int(self.getValue('Ch%d - Bandwidth limit' % (n+1)))
                    self.dig.AlazarSetBWLimit(n+1, BW)
        # 
        # configure trigger
        Source = int(self.getCmdStringFromValue('Trig source'))
        Slope = int(self.getCmdStringFromValue('Trig slope'))
        Delay = self.getValue('Trig delay')
        timeout = self.dComCfg['Timeout']
        # trig level is relative to full range
        trigLevel = self.getValue('Trig level')
        vAmp = np.array([4, 2, 1, 0.4, 0.2, 0.1, .04], dtype=float)
        if self.getValue('Trig source') == 'Channel 1':
            maxLevel = vAmp[self.getValueIndex('Ch1 - Range')]
        elif self.getValue('Trig source') == 'Channel 2':
            maxLevel = vAmp[self.getValueIndex('Ch2 - Range')]
        elif self.getValue('Trig source') == 'External':
            if self.getModel() in ('9373', '9360'):
                maxLevel = 2.5
                ExtTrigRange = 3
            else:
                maxLevel = 5.0
                ExtTrigRange = 0
        elif self.getValue('Trig source') == 'Immediate':
            maxLevel = 5.0
            # set timeout to very short with immediate triggering
            timeout = 0.001
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
            self.dig.AlazarSetExternalTrigger(Coupling, ExtTrigRange)
        # 
        # set trig delay and timeout
        Delay = int(self.getValue('Trig delay')/self.dt)
        self.dig.AlazarSetTriggerDelay(Delay)
        self.dig.AlazarSetTriggerTimeOut(time=timeout)
        # config memeory buffers, only possible for cards using DMA read
        if self.getModel() not in ('9360', '9373'):
            return
        bGetCh1 = bool(self.getValue('Ch1 - Enabled'))
        bGetCh2 = bool(self.getValue('Ch2 - Enabled'))
        nPostSize = int(self.getValue('Number of samples'))
        nRecord = int(self.getValue('Number of records'))
        nAverage = int(self.getValue('Number of averages'))
        nBuffer = int(self.getValue('Records per Buffer'))
        nMemSize = int(self.getValue('Max buffer size'))
        nMaxBuffer = int(self.getValue('Max number of buffers'))
        fft_config = self.get_fft_config()
        # set ignore error flag
        self.dig.ignore_buffer_overflow = bool(
            self.getValue('Ignore buffer overflow'))
        # configure DMA read
        self.dig.readTracesDMA(bGetCh1, bGetCh2,
                               nPostSize, nRecord, nBuffer, nAverage,
                               bConfig=True, bArm=False, bMeasure=False,
                               bufferSize=nMemSize,
                               maxBuffers=nMaxBuffer,
                               fft_config=fft_config)


    def getTracesDMA(self, hardware_trig=False):
        """Resample the data for units with DMA"""
        # get channels in use
        bGetCh1 = bool(self.getValue('Ch1 - Enabled'))
        bGetCh2 = bool(self.getValue('Ch2 - Enabled'))
        nPostSize = int(self.getValue('Number of samples'))
        nRecord = int(self.getValue('Number of records'))
        nAverage = int(self.getValue('Number of averages'))
        nBuffer = int(self.getValue('Records per Buffer'))
        nMemSize = int(self.getValue('Max buffer size'))
        nMaxBuffer = int(self.getValue('Max number of buffers'))
        fft_config = self.get_fft_config()
        # in hardware trig mode, there is no noed to re-arm the card
        bArm = not hardware_trig
        # get data
        self.lTrace[0], self.lTrace[1] = self.dig.readTracesDMA(
            bGetCh1, bGetCh2,
            nPostSize, nRecord, nBuffer, nAverage,
            bConfig=False, bArm=bArm, bMeasure=True,
            funcStop=self.isStopped,
            bufferSize=nMemSize,
            maxBuffers=nMaxBuffer,
            fft_config=fft_config)


    def getTracesNonDMA(self):
        """Resample the data"""
        # get channels in use
        bGetCh1 = bool(self.getValue('Ch1 - Enabled'))
        bGetCh2 = bool(self.getValue('Ch2 - Enabled'))
        nPreSize = int(self.getValue('Pre-trig samples'))
        nPostSize = int(self.getValue('Number of samples'))
        nRecord = int(self.getValue('Number of records'))
        nAverage = int(self.getValue('Number of averages'))
        nBuffer = int(self.getValue('Records per Buffer'))
        if (not bGetCh1) and (not bGetCh2):
            return
        
        self.dig.AlazarSetRecordSize(nPreSize, nPostSize)
        self.dig.AlazarSetRecordCount(nRecord, nAverage)
        # start aquisition
        self.dig.AlazarStartCapture()
        nTry = self.dComCfg['Timeout']/0.05
        while nTry>0 and self.dig.AlazarBusy() and not self.isStopped():
            # sleep for a while to save resources, then try again
            self.wait(0.050)
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

    def get_fft_config(self):
        """Get FFT configuration in format suitable for Alazartech settings"""
        d = {}
        d['enabled'] = self.dig.fft_enabled and self.getValue('FFT - Enabled')
        d['window'] = self.getValueIndex('FFT - Window')
        d['output'] = int(self.getCmdStringFromValue('FFT - Output'))
        # get frequency
        n_sample = int(self.getValue('Number of samples'))
        fft_length = 1
        while fft_length < n_sample:
            fft_length *= 2
        d['df'] = 1 / (self.dt*fft_length)
        return d

    def extract_trace_value(self, quant, record=None):
        """Get value from traces, either as pure data, fft, or fft value
        
        Parameters
        ----------
        quant : Quantity
            Quantity to extract
        record : int, optional
            Record to get, by default None
        """
        indx = self.signal_index[quant.name]
        # return correct data
        fft_config = self.get_fft_config()
        dt = fft_config['df'] if fft_config['enabled'] else self.dt
        if record is None:
            value = quant.getTraceDict(self.lTrace[indx], dt=dt)
        else:
            value = quant.getTraceDict(self.lTrace[indx][record], dt=dt)
        if quant.name.startswith('FFT - Value'):
            if not fft_config['enabled']:
                return 0.0
            indx_fft = int(quant.name.split('FFT - Value ')[1])
            freq = self.getValue('FFT - Frequency %d' % indx_fft)
            # find closest frequency
            (fx, fy) = quant.getTraceXY(value)
            interp1 = interp1d(
                fx, fy, kind='linear', copy=False, assume_sorted=True)
            value = float(interp1(freq))
        return value


if __name__ == '__main__':
    pass
