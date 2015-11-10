import ctypes, warnings
from ctypes import byref
import numpy as np

# treat timout errors seperately
ACQIRIS_ERROR_ACQ_TIMEOUT = 0xBFFA4900L
ACQIRIS_ERROR_PROC_TIMEOUT = 0xBFFA4902L
# ignore error codes below the warning limit
WARNING_LIMIT = 0x40000000L

# error type returned by this class
class Error(Exception):
    pass
        
class TimeoutError(Error):
    pass

# open dll
AgDLL = ctypes.WinDLL('AgMD1Fundamental.dll')

# define data types used by this dll
ViString = ctypes.c_char_p
ViBoolean = ctypes.c_bool
ViSession = ctypes.c_uint32
ViStatus = ctypes.c_int32
ViInt32 = ctypes.c_int32
ViUInt32 = ctypes.c_uint32
ViReal64 = ctypes.c_double
ViRsrc = ViString
ViChar = ctypes.c_char_p

# structs
class AqReadParameters(ctypes.Structure):
    _fields_ = [('dataType', ViInt32),
                ('readMode', ViInt32),
                ('firstSegment', ViInt32),
                ('nbrSegments', ViInt32),
                ('firstSampleInSeg', ViInt32),
                ('nbrSamplesInSeg', ViInt32),
                ('segmentOffset', ViInt32),
                ('dataArraySize', ViInt32),
                ('segDescArraySize', ViInt32),
                ('flags', ViInt32),
                ('reserved', ViInt32),
                ('reserved2', ViReal64),
                ('reserved3', ViReal64)]

class AqSegmentDescriptor(ctypes.Structure):
    _fields_ = [('horPos', ViReal64),
                ('timeStampLo', ViUInt32),
                ('timeStampHi', ViUInt32)]

class AqSegmentDescriptorAvg(ctypes.Structure):
    _fields_ = [('horPos', ViReal64),
                ('timeStampLo', ViUInt32),
                ('timeStampHi', ViUInt32),
                ('actualTriggersInSeg', ViUInt32),
                ('avgOvfl', ViInt32),
                ('avgStatus', ViInt32),
                ('avgMax', ViInt32),
                ('flags', ViUInt32),
                ('reserved', ViInt32)]

class AqSegmentDescriptorSeqRaw(ctypes.Structure):
    _fields_ = [('horPos', ViReal64),
                ('timeStampLo', ViUInt32),
                ('timeStampHi', ViUInt32),
                ('indexFirstPoint', ViUInt32),
                ('actualSegmentSize', ViUInt32),
                ('reserved', ViInt32)]

class AqDataDescriptor(ctypes.Structure):
    _fields_ = [('returnedSamplesPerSeg', ViInt32),
                ('indexFirstPoint', ViInt32),
                ('sampTime', ViReal64),
                ('vGain', ViReal64),
                ('vOffset', ViReal64),
                ('returnedSegments', ViInt32),
                ('nbrAvgWforms', ViInt32),
                ('actualTriggersInAcqLo', ViUInt32),
                ('actualTriggersInAcqHi', ViUInt32),
                ('actualDataSize', ViUInt32),
                ('reserved2', ViInt32),
                ('reserved3', ViReal64)]



class AcqirisDigitizer():
    """Represent the Acqiris digitizer, redefines the dll functions in python"""

    def __init__(self):
        """The init case defines a session ID, used to identify the instrument"""
        # create a session id
        self.session = ViSession()


    def callFunc(self, sFunc, *args, **kargs):
        """General function caller with restype=ViStatus, also checks for errors"""
        # get function from DLL
        func = getattr(AgDLL, sFunc)
        func.restype = ViStatus
        # call function, raise error if needed
        status = func(*args)
        if 'bIgnoreError' in kargs:
            bIgnoreError = kargs['bIgnoreError']
        else:
            bIgnoreError = False
        if status and not bIgnoreError and status>WARNING_LIMIT:
            sError = self.getError(status)
            # special treatment of TimeoutError
            if status in (ACQIRIS_ERROR_ACQ_TIMEOUT, ACQIRIS_ERROR_PROC_TIMEOUT):
                raise TimeoutError(sError)
            else:
                raise Error(sError)

    
    def getError(self, status):
        """Convert the error in status to a string"""
        nBuffer = 512
        msgBuffer = ctypes.create_string_buffer(nBuffer)
        # ViStatus status = Acqrs_errorMessage(ViSession instrumentID,
        # ViStatus errorCode, ViChar errorMessage[],ViInt32 errorMessageSize);
        AgDLL['Acqrs_errorMessage'](self.session, status, msgBuffer,
                                    ViInt32(nBuffer))
        return msgBuffer.value


    def init(self, sResource='', bIdQuery=False, bReset=False):
        # ViStatus status = Acqrs_init(ViRsrc resourceName, ViBoolean IDQuery,
        # ViBoolean resetDevice, ViSession* instrumentID)
        self.callFunc('Acqrs_init', ViRsrc(sResource), ViBoolean(bIdQuery),
                      ViBoolean(bReset), byref(self.session))


    def InitWithOptions(self, sResource='', bIdQuery=False, bReset=False,
                         sOption='CAL=FALSE'):
        # ViStatus status = Acqrs_InitWithOptions(ViRsrc resourceName, ViBoolean IDQuery,
        # ViBoolean resetDevice, ViString optionsString, ViSession* instrumentID);
        self.callFunc('Acqrs_InitWithOptions', ViRsrc(sResource), ViBoolean(bIdQuery),
                      ViBoolean(bReset), ViString(sOption), byref(self.session))


    def close(self):
        # ViStatus status = Acqrs_close(ViSession instrumentID);
        self.callFunc('Acqrs_close', self.session, bIgnoreError=True)


    def closeAll(self):
        # ViStatus status = Acqrs_closeAll(void);
        self.callFunc('Acqrs_closeAll', bIgnoreError=True)


    def configHorizontal(self, sampInterval, delayTime):
        # ViStatus status = AcqrsD1_configHorizontal(ViSession instrumentID,
        # ViReal64 sampInterval, ViReal64 delayTime);
        self.callFunc('AcqrsD1_configHorizontal', self.session, ViReal64(sampInterval),
                      ViReal64(delayTime))


    def getHorizontal(self):
        # ViStatus status = AcqrsD1_getHorizontal(ViSession instrumentID,
        # ViReal64* sampInterval, ViReal64* delayTime);
        sampInterval = ViReal64()
        delayTime = ViReal64()
        self.callFunc('AcqrsD1_getHorizontal', self.session, byref(sampInterval),
                      byref(delayTime))
        # return both results
        return (sampInterval.value, delayTime.value)
        

    def configMemory(self, nbrSamples, nbrSegments):
        # ViStatus status = AcqrsD1_configMemory(ViSession instrumentID, 
        # ViInt32 nbrSamples, ViInt32 nbrSegments)
        self.callFunc('AcqrsD1_configMemory', self.session,
                      ViInt32(nbrSamples), ViInt32(nbrSegments))
        

    def getMemory(self):
        # ViStatus status = AcqrsD1_getMemory(ViSession instrumentID,
        # ViInt32* nbrSamples, ViInt32* nbrSegments);
        nbrSamples = ViInt32()
        nbrSegments = ViInt32()
        self.callFunc('AcqrsD1_getMemory', self.session,
                      byref(nbrSamples), byref(nbrSegments))
        return (nbrSamples.value, nbrSegments.value)


    def configTrigSource(self, channel, trigCoupling, trigSlope, trigLevel1,
                         trigLevel2=0.0):
        """Channel is negative for externa trig.
        Trig coupling:    0, DC
                          1, AC
                          2, HF Reject (if available)
                          3, DC, 50 Ohm (ext. trigger only, if available)
                          4, AC, 50 Ohm (ext. trigger only, if available)
        Trig slope:       0, Positive
                          1, Negative"""
        # ViStatus status = AcqrsD1_configTrigSource(ViSession instrumentID, 
        # ViInt32 channel, ViInt32 trigCoupling, ViInt32 trigSlope, 
        # ViReal64 trigLevel1, ViReal64 trigLevel2);
        trigLevel2 = 0.0
        self.callFunc('AcqrsD1_configTrigSource', self.session,
                      ViInt32(channel), ViInt32(trigCoupling), ViInt32(trigSlope),
                      ViReal64(trigLevel1), ViReal64(trigLevel2))


    def getTrigSource(self, channel):
        """Channel is negative for externa trig.
        Trig coupling:    0, DC
                          1, AC
                          2, HF Reject (if available)
                          3, DC, 50 Ohm (ext. trigger only, if available)
                          4, AC, 50 Ohm (ext. trigger only, if available)
        Trig slope:       0, Positive
                          1, Negative"""
        # ViStatus status = AcqrsD1_getTrigSource(ViSession instrumentID, ViInt32 channel,
        # ViInt32* trigCoupling,
        # ViInt32* trigSlope, ViReal64* trigLevel1, ViReal64* trigLevel2);   
        trigCoupling = ViInt32()
        trigSlope = ViInt32()
        trigLevel1 = ViReal64()
        trigLevel2 = ViReal64()
        self.callFunc('AcqrsD1_getTrigSource', self.session, ViInt32(channel),
                      byref(trigCoupling), byref(trigSlope),
                      byref(trigLevel1), byref(trigLevel2))
        return (trigCoupling.value, trigSlope.value, trigLevel1.value, trigLevel2.value)


    def configTrigClass(self, sourcePattern):
        """
        Source pattern: Ch1 = 0x00000001 
                        Ch2 = 0x00000002 
                        Ext1 = 0x80000000 
        """
        # ViStatus status = AcqrsD1_configTrigClass(ViSession instrumentID,
        # ViInt32 trigClass, ViInt32 sourcePattern, ViInt32 validatePattern, 
        # ViInt32 holdType, ViReal64 holdoffTime, ViReal64 reserved)
        self.callFunc('AcqrsD1_configTrigClass', self.session,
                      ViInt32(0), ViInt32(sourcePattern), ViInt32(0),
                      ViInt32(0), ViReal64(0.0), ViReal64(0.0))

    def getTrigClass(self):
        """
        Source pattern: Ch1 = 0x00000001 
                        Ch2 = 0x00000002 
                        Ext1 = 0x80000000 
        """
        # ViStatus status = AcqrsD1_getTrigClass(ViSession instrumentID,
        # ViInt32* trigClass, ViInt32* sourcePattern, ViInt32* validatePattern,
        # ViInt32* holdType, ViReal64* holdoffTime, ViReal64* reserved);
        trigClass = ViInt32()
        sourcePattern = ViInt32()
        validatePattern = ViInt32()
        holdType = ViInt32()
        holdoffTime = ViReal64()
        reserved = ViReal64()
        self.callFunc('AcqrsD1_getTrigClass', self.session,
                      byref(trigClass), byref(sourcePattern),
                      byref(validatePattern), byref(holdType),
                      byref(holdoffTime), byref(reserved))
        return (sourcePattern.value, trigClass.value)


    def configVertical(self, channel, fullScale, offset, coupling, bandwidth):
        """
        Coupling:   0: Ground (Averagers ONLY)
                    1: DC, 1 MOhm
                    2: AC, 1 MOhm
                    3: DC, 50 Ohm
                    4: AC, 50 Ohm
        Bandwidth:  0: Full
                    1: 25 MHz
                    2: 700 MHz
                    3: 200 MHz
                    4: 20 MHz
                    5: 35 MHz
        """
        # ViStatus status = AcqrsD1_configVertical(ViSession instrumentID,
        # ViInt32 channel,ViReal64 fullScale, ViReal64 offset, ViInt32 coupling,
        # ViInt32 bandwidth)
        self.callFunc('AcqrsD1_configVertical', self.session,
                      ViInt32(channel), ViReal64(fullScale), ViReal64(offset),
                      ViInt32(coupling), ViInt32(bandwidth))


    def getVertical(self, channel):
        """
        Coupling:   0: Ground (Averagers ONLY)
                    1: DC, 1 MOhm
                    2: AC, 1 MOhm
                    3: DC, 50 Ohm
                    4: AC, 50 Ohm
        Bandwidth:  0: Full
                    1: 25 MHz
                    2: 700 MHz
                    3: 200 MHz
                    4: 20 MHz
                    5: 35 MHz
        """
        # ViStatus status = AcqrsD1_getVertical(ViSession instrumentID,
        # ViInt32 channel, ViReal64* fullScale,
        # ViReal64* offset, ViInt32* coupling, ViInt32* bandwidth);
        fullScale = ViReal64()
        offset = ViReal64()
        coupling = ViInt32()
        bandwidth = ViInt32()
        self.callFunc('AcqrsD1_getVertical', self.session, ViInt32(channel),
                      byref(fullScale), byref(offset),
                      byref(coupling), byref(bandwidth))
        return (fullScale.value, offset.value, coupling.value, bandwidth.value)


    def configMode(self, mode, modifier=0, flags=0):
        """
        0 = normal data acquisition
        1 = AC/SC stream data to DPU
        2 = averaging mode (only in real-time averagers)
        3 = buffered data acquisition (only in AP101/AP201
        analyzers)
        5 = PeakTDC mode
        6 = frequency counter mode
        7 = SSR mode (AP235/240)/ Zero-Suppress (U1084)
        12 = DDC mode (M9202A)
        14 = Custom firmware
        """
        # ViStatus status = AcqrsD1_configMode(ViSession instrumentID,
        # ViInt32 mode, ViInt32 modifier, ViInt32 flags);
        self.callFunc('AcqrsD1_configMode', self.session,
                      ViInt32(mode), ViInt32(modifier), ViInt32(flags))


    def getMode(self):
        """
        0 = normal data acquisition
        1 = AC/SC stream data to DPU
        2 = averaging mode (only in real-time averagers)
        3 = buffered data acquisition (only in AP101/AP201
        analyzers)
        5 = PeakTDC mode
        6 = frequency counter mode
        7 = SSR mode (AP235/240)/ Zero-Suppress (U1084)
        12 = DDC mode (M9202A)
        14 = Custom firmware
        """
        # ViStatus status = AcqrsD1_getMode(ViSession instrumentID,
        # ViInt32* mode, ViInt32* modifier, ViInt32* flags)
        mode = ViInt32()
        modifier = ViInt32()
        flags = ViInt32()
        self.callFunc('AcqrsD1_getMode', self.session,
                      byref(mode), byref(modifier), byref(flags))
        return (mode.value, modifier.value, flags.value)


    def configAveraging(self, channel, **params):
        """Setup parameters for averaging mode"""
        for key, value in params.items():
            self.configAvgConfig(channel, key, value)


    def configAvgConfig(self, channelNbr, parameterString, value):
        lFloat = ("NoiseBase", "StartDeltaPosPeakV", "Threshold", "ValidDeltaPosPeakV")
        # proceed depending on Int or Float
        if parameterString in lFloat:
            # ViStatus status = AcqrsD1_configAvgConfigReal64(ViSession instrumentID,
            # ViInt32 channelNbr, ViString parameterString, ViReal64 value);
            self.callFunc('AcqrsD1_configAvgConfigReal64', self.session,
                          ViInt32(channelNbr), ViString(parameterString), ViReal64(value))
        else:
            # ViStatus status = AcqrsD1_configAvgConfigInt32(ViSession instrumentID,
            # ViInt32 channelNbr, ViString parameterString, ViInt32 value);
            self.callFunc('AcqrsD1_configAvgConfigInt32', self.session,
                          ViInt32(channelNbr), ViString(parameterString), ViInt32(value))
            

    def getAvgConfig(self, channelNbr, parameterString):
        lFloat = ("NoiseBase", "StartDeltaPosPeakV", "Threshold", "ValidDeltaPosPeakV")
        # proceed depending on Int or Float
        if parameterString in lFloat:
            # ViStatus status = AcqrsD1_getAvgConfigReal64(ViSession instrumentID,
            # ViInt32 channelNbr, ViString parameterString, ViReal64 *value);
            value = ViReal64()
            self.callFunc('AcqrsD1_getAvgConfigReal64', self.session, ViInt32(channelNbr),
                          ViString(parameterString), byref(value))
        else:
            # AcqrsD1_getAvgConfigInt32(ViSession instrumentID, ViInt32 channelNbr,
            # ViString parameterString, ViInt32 *value);
            value = ViInt32()
            self.callFunc('AcqrsD1_getAvgConfigInt32', self.session, ViInt32(channelNbr),
                          ViString(parameterString), byref(value))
        return value.value


    def waitForEndOfAcquisition(self, timeout=10000):
        # ViStatus status = AcqrsD1_waitForEndOfAcquisition (ViSession instrumentID,
        # ViInt32 timeout);
        # max timout is 10 second
        iMaxTime = 10000
        # do multiple calls to fix max timeout of 10 seconds
        while timeout > 0:
            try:
                self.callFunc('AcqrsD1_waitForEndOfAcquisition', self.session,
                              ViInt32(timeout))
                # completed, break out of loop
                break
            except TimeoutError:
                timeout -= iMaxTime
                if timeout > 0:
                    # try again
                    continue
                else:
                    self.stopAcquisition()
                    # re-raise timeout error
                    raise
    

    def acquire(self):
        # ViStatus status = AcqrsD1_acquire(ViSession instrumentID);
        self.callFunc('AcqrsD1_acquire', self.session)


    def stopAcquisition(self):
        # ViStatus status = AcqrsD1_stopAcquisition(ViSession instrumentID);
        self.callFunc('AcqrsD1_stopAcquisition', self.session)


    def stopProcessing(self):
        # ViStatus status = AcqrsD1_stopProcessing(ViSession instrumentID);
        self.callFunc('AcqrsD1_stopProcessing', self.session)


    # define datatype
    DATATYPE_BYTE = 0
    DATATYPE_SHORT = 1
    DATATYPE_INT = 2
    DATATYPE_DOUBLE = 3
    
    def readData(self, channel, readPar):
        """
        readPar.dataType:
            DATATYPE_BYTE = 0
            DATATYPE_SHORT = 1
            DATATYPE_INT = 2
            DATATYPE_DOUBLE = 3
        """
        #
        nbrSegments = readPar.nbrSegments
        nbrSamples = readPar.nbrSamplesInSeg * nbrSegments
        
        # allocate data array based on the requested type
        if readPar.dataType == self.DATATYPE_BYTE:
            dataType = ctypes.c_byte
        elif readPar.dataType == self.DATATYPE_SHORT:
            dataType = ctypes.c_short
        elif readPar.dataType == self.DATATYPE_INT:
            dataType = ctypes.c_int
        elif readPar.dataType == self.DATATYPE_DOUBLE:
            dataType = ctypes.c_double
        dataArray = (dataType * (nbrSamples + 32))()
        # allocate data descriptor struct
        descriptor = AqDataDescriptor()
        # allocate segment descriptor array
        if readPar.readMode in [0, 1, 3]:
            segDescType = AqSegmentDescriptor
        elif readPar.readMode in [2, 5, 6]:
            segDescType = AqSegmentDescriptorAvg
        elif readPar.readMode in [11]:
            segDescType = AqSegmentDescriptorSeqRaw
        else:
            raise Exception('Unknown readMode: %d' % (readPar.readMode))
        segDesc = (segDescType * nbrSegments)()
        
        # set the sizes of data and segment descriptor arrays
        readPar.dataArraySize = ctypes.sizeof(dataArray)
        readPar.segDescArraySize = ctypes.sizeof(segDesc)
        # 
        # ViStatus status = AcqrsD1_readData(ViSession instrumentID,
        # ViInt32 channel, AqReadParameters* readPar, ViAddr dataArray,
        # AqDataDescriptor* descriptor, ViAddr segDesc);
        self.callFunc('AcqrsD1_readData', self.session, ViInt32(channel),
                      byref(readPar), dataArray, byref(descriptor), segDesc)
        return (dataArray, descriptor, segDesc)
        

    def readChannelsToNumpy(self, nSample, lChannel=[1], nAverage=1,
                            nSegment=1, timeout=10000, bAverageMode=False):
        """Convenience method for getting multiple channels to a list of numpy
        arrays"""
        if bAverageMode:
            # average
            readPar = AqReadParameters(dataType=self.DATATYPE_DOUBLE,
                                              readMode=2, 
                                              nbrSegments=nSegment,
                                              nbrSamplesInSeg=nSample,
                                              firstSegment=0,
                                              firstSampleInSegment=0)
        else:
            # single trace
            readPar = AqReadParameters(dataType=self.DATATYPE_DOUBLE,
                                              readMode=0, 
                                              nbrSegments=nSegment,
                                              nbrSamplesInSeg=nSample,
                                              firstSegment=0,
                                              firstSampleInSegment=0)
        # start acquisition
        self.acquire()
        self.waitForEndOfAcquisition(timeout)
        # get waveforms for all channels
        lData = []
        for channel in lChannel:
            (dataArray, descriptor, segDesc) = self.readData(channel, readPar)
            vData = self.getResultAsNumpyArray(dataArray, descriptor)
            lData.append(vData)
        # get time data
        dt = descriptor.sampTime
        # return new numpy 2d array
        return (lData, dt)
#        return (np.array(lData), dt)


    def getResultAsNumpyArray(self, dataArray, descriptor):
        """Return the result from the Acqiris card to a numpy array"""
        indexFirstPoint = descriptor.indexFirstPoint
        nbrSamplesPerSeg = descriptor.returnedSamplesPerSeg
        nbrSegments = descriptor.returnedSegments
        # don't show warnings about wrong data size
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            vData = np.ctypeslib.as_array(dataArray)
        vData = vData[indexFirstPoint:indexFirstPoint + nbrSamplesPerSeg*nbrSegments]
        return vData



if __name__ == '__main__':
    #
#    descriptor = AqDataDescriptor()
#    for s in descriptor._fields_:
#        print s[0], getattr(descriptor, s[0])
    
    # test driver
    Digitizer = AcqirisDigitizer()
    Digitizer.init('PCI::INSTR0')
    # trigger
    Digitizer.configTrigSource(0, 0, 1, 0.3)
    Digitizer.configTrigClass(0x80000000L)
#    Digitizer.configTrigSource(2, 0, 1, 0.05)
#    Digitizer.configTrigClass(0x00000002L)
    # test, single trace
    Digitizer.configMode(0, 0, 0) 
    vRes = Digitizer.readChannelsToNumpy(nSample=1000, lChannel=[1], bAverageMode=False)[0]
    print vRes
    # test, average
    Digitizer.configMode(2, 0, 0)
    Digitizer.configAveraging(1, NbrSamples=1024, NbrSegments=1,
                         NbrWaveforms=100, StartDelay=0, StopDelay=0)
    vRes2 = Digitizer.readChannelsToNumpy(nSample=1000, lChannel=[1], bAverageMode=True)[0]
    # close digitizer
    Digitizer.close()
    Digitizer.closeAll()

    # plot data
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 1)
    ax.plot(vRes[0], 'r-', label='raw')
    ax.plot(vRes2[0], 'k-', label='averaged')
    plt.show()



    


