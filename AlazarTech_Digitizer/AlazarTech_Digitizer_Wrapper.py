import ctypes, os
from ctypes import c_int, c_uint8, c_uint32, c_char_p, c_void_p, c_long, byref
import numpy as np

# match naming convertinos in DLL
U8 = c_uint8
U32 = c_uint32

# error type returned by this class
class Error(Exception):
    pass
        
class TimeoutError(Error):
    pass

# open dll
try:
    DLL = ctypes.CDLL('ATSApi32')
except:
    # if failure, try to open in driver folder
    sPath = os.path.dirname(os.path.abspath(__file__))
    DLL = ctypes.CDLL(os.path.join(sPath, 'ATSApi32'))



class AlazarTechDigitizer():
    """Represent the Alazartech digitizer, redefines the dll functions in python"""

    def __init__(self, systemId=1, boardId=1):
        """The init case defines a session ID, used to identify the instrument"""
        # range settings
        self.dRange = {}
        # create a session id
        func = getattr(DLL, 'AlazarNumOfSystems')
        func.restype = U32 
        print 'Number of systems:', func()
        func = getattr(DLL, 'AlazarGetBoardBySystemID')
        func.restype = c_void_p
        handle = func(U32(systemId), U32(boardId))
        if handle is None:
            raise Error('Device with system ID=%d and board ID=%d could not be found.' % (systemId, boardId))
        self.handle = handle


    def testLED(self):
        import time
        self.callFunc('AlazarSetLED', self.handle, U32(1))
        time.sleep(0.1)
        self.callFunc('AlazarSetLED', self.handle, U32(0))


    def callFunc(self, sFunc, *args, **kargs):
        """General function caller with restype=status, also checks for errors"""
        # get function from DLL
        func = getattr(DLL, sFunc)
        func.restype = c_int
        # call function, raise error if needed
        status = func(*args)
        if 'bIgnoreError' in kargs:
            bIgnoreError = kargs['bIgnoreError']
        else:
            bIgnoreError = False
        if status>512 and not bIgnoreError:
            sError = self.getError(status)
            raise Error(sError)

    
    def getError(self, status):
        """Convert the error in status to a string"""
        func = getattr(DLL, 'AlazarErrorToText')
        func.restype = c_char_p 
        # const char* AlazarErrorToText(RETURN_CODE retCode)
        errorText = func(c_int(status))
        return str(errorText)


    #RETURN_CODE AlazarSetCaptureClock( HANDLE h, U32 Source, U32 Rate, U32 Edge, U32 Decimation);
    def AlazarSetCaptureClock(self, SourceId, SampleRateId, EdgeId=0, Decimation=0):
        self.callFunc('AlazarSetCaptureClock', self.handle, 
                      U32(SourceId), U32(SampleRateId), U32(EdgeId), U32(Decimation))


    #RETURN_CODE AlazarInputControl( HANDLE h, U8 Channel, U32 Coupling, U32 InputRange, U32 Impedance);
    def AlazarInputControl(self, Channel, Coupling, InputRange, Impedance):
        # keep track of input range
        dConv = {12: 4.0, 11: 2.0, 10: 1.0, 7: 0.4, 6: 0.2, 5: 0.1, 2: 0.04}
        self.dRange[Channel] = dConv[InputRange]
        self.callFunc('AlazarInputControl', self.handle, 
                      U8(Channel), U32(Coupling), U32(InputRange), U32(Impedance))


    #RETURN_CODE AlazarSetBWLimit( HANDLE h, U8 Channel, U32 enable);
    def AlazarSetBWLimit(self, Channel, enable):
        self.callFunc('AlazarSetBWLimit', self.handle, U8(Channel), U32(enable))


    #RETURN_CODE AlazarSetTriggerOperation(HANDLE h, U32 TriggerOperation
    #            ,U32 TriggerEngine1/*j,K*/, U32 Source1, U32 Slope1, U32 Level1
    #            ,U32 TriggerEngine2/*j,K*/, U32 Source2, U32 Slope2, U32 Level2);
    def AlazarSetTriggerOperation(self, TriggerOperation=0,
                                  TriggerEngine1=0, Source1=0, Slope1=1, Level1=128,
                                  TriggerEngine2=1, Source2=3, Slope2=1, Level2=128):
        self.callFunc('AlazarSetTriggerOperation', self.handle, U32(TriggerOperation),
                      U32(TriggerEngine1), U32(Source1), U32(Slope1), U32(Level1),
                      U32(TriggerEngine2), U32(Source2), U32(Slope2), U32(Level2))


    #RETURN_CODE AlazarSetExternalTrigger( HANDLE h, U32 Coupling, U32 Range);
    def AlazarSetExternalTrigger(self, Coupling, Range=0):
        self.callFunc('AlazarSetExternalTrigger', self.handle, U32(Coupling), U32(Range))


    #RETURN_CODE  AlazarSetTriggerDelay( HANDLE h, U32 Delay);
    def AlazarSetTriggerDelay(self, Delay=0):
        self.callFunc('AlazarSetTriggerDelay', self.handle, U32(Delay))
    

    #RETURN_CODE  AlazarSetTriggerTimeOut( HANDLE h, U32 to_ns);
    def AlazarSetTriggerTimeOut(self, time=0.0):
        tick = U32(int(time*1E5))
        self.callFunc('AlazarSetTriggerTimeOut', self.handle, tick)


    #RETURN_CODE AlazarSetRecordSize( HANDLE h, U32 PreSize, U32 PostSize);
    def AlazarSetRecordSize(self, PreSize, PostSize):
        self.nPreSize = int(PreSize)
        self.nPostSize = int(PostSize)
        self.callFunc('AlazarSetRecordSize', self.handle, U32(PreSize), U32(PostSize))


    #RETURN_CODE AlazarSetRecordCount( HANDLE h, U32 Count);
    def AlazarSetRecordCount(self, Count):
        self.nRecord = int(Count)
        self.callFunc('AlazarSetRecordCount', self.handle, U32(Count))


    #RETURN_CODE AlazarStartCapture( HANDLE h);
    def AlazarStartCapture(self):
        self.callFunc('AlazarStartCapture', self.handle)


    #RETURN_CODE AlazarAbortCapture( HANDLE h);
    def AlazarAbortCapture(self):
        self.callFunc('AlazarAbortCapture', self.handle)


    #U32	AlazarBusy( HANDLE h);
    def AlazarBusy(self):
        # get function from DLL
        func = getattr(DLL, 'AlazarBusy')
        func.restype = U32
        # call function, return result
        return bool(func(self.handle))
        

    # U32	AlazarRead(HANDLE h, U32 Channel, void *Buffer, int ElementSize,
    #                 long Record, long TransferOffset, U32 TransferLength);
    def AlazarRead(self, Channel, Buffer, ElementSize, Record, TransferOffset, TransferLength):
        self.callFunc('AlazarRead', self.handle,
                      U32(Channel), byref(Buffer), c_int(ElementSize),
                      c_long(Record), c_long(TransferOffset), U32(TransferLength))


    def readTraces(self, Channel):
        """Read traces, convert to float, average to a single trace"""
        # define sizes
        bitsPerSample = 8
        bytesPerSample = int(np.floor((float(bitsPerSample) + 7.) / 8.0))
        samplesPerRecord = self.nPreSize + self.nPostSize
        # The buffer must be at least 16 samples larger than the transfer size
        samplesPerBuffer = samplesPerRecord + 16
        dataBuffer = (c_uint8*samplesPerBuffer)()
        # define scale factors
        codeZero = 2 ** (float(bitsPerSample) - 1) - 0.5
        codeRange = 2 ** (float(bitsPerSample) - 1) - 0.5
        voltScale = self.dRange[Channel] /codeRange
        # initialize a scaled float vector
        vData = np.zeros(samplesPerRecord, dtype=float)
        for n1 in range(self.nRecord):
            self.AlazarRead(Channel, dataBuffer, bytesPerSample, n1+1,
                            -self.nPreSize, samplesPerRecord)
            # convert and scale to float
            vBuffer = voltScale * ((np.array(dataBuffer[:samplesPerRecord]) - codeZero))
            # add to output vector
            vData += vBuffer
        # normalize
        vData /= self.nRecord
        return vData



if __name__ == '__main__':
    #
#    descriptor = AqDataDescriptor()
#    for s in descriptor._fields_:
#        print s[0], getattr(descriptor, s[0])
    
    # test driver
    Digitizer = AlazarTechDigitizer()

    


