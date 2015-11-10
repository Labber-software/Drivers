import ctypes
from ctypes import c_int, c_long, c_float, c_double, c_ulong, POINTER, byref

class Error(Exception):
    pass

# open dll
_lib = ctypes.WinDLL('afDigitizerDll_32')

# define data types used by this dll
STRING = ctypes.c_char_p
AFBOOL = c_long

# define variables
afDigitizerInstance_t = c_long

# define dll function objects in python
CreateObject = _lib.afDigitizerDll_CreateObject
CreateObject.restype = c_long
CreateObject.argtypes = [POINTER(afDigitizerInstance_t)]
DestroyObject = _lib.afDigitizerDll_DestroyObject
DestroyObject.restype = c_long
DestroyObject.argtypes = [afDigitizerInstance_t]
BootInstrument = _lib.afDigitizerDll_BootInstrument
BootInstrument.restype = c_long
BootInstrument.argtypes = [afDigitizerInstance_t, STRING, STRING, AFBOOL]
CloseInstrument = _lib.afDigitizerDll_CloseInstrument
CloseInstrument.restype = c_long
CloseInstrument.argtypes = [afDigitizerInstance_t]
ErrorMessage_Get = _lib.afDigitizerDll_ErrorMessage_Get
ErrorMessage_Get.restype = c_long
ErrorMessage_Get.argtypes = [afDigitizerInstance_t, STRING, c_ulong]


def getDllObject(sName, argtypes=[afDigitizerInstance_t], restype=c_long):
    """Create a dll ojbect with input and output types"""    
    obj = getattr(_lib, sName)
    obj.restype = restype
    obj.argypes = argtypes
    return obj


class afDigitizer():
    """Represent a signal generator, redefines the dll function in python"""

    def __init__(self):
        """The init case defines a session ID, used to identify the instrument"""
        # create a session id
        self.session = afDigitizerInstance_t()

    def create_object(self):
        error = CreateObject(self.session)
        self.check_error(error)

    def destroy_object(self):
        error = DestroyObject(self.session)

    def boot_instrument(self, sLoResource, sRfResource, bLoIsPlugin=False):
        cLoResource = STRING(sLoResource)
        cRfResource = STRING(sRfResource)
        error = BootInstrument(self.session, cLoResource,
                               cRfResource, AFBOOL(bLoIsPlugin))
        self.check_error(error)
        return (cLoResource.value, cRfResource.value)

    def close_instrument(self, bCheckError=True):
        error = CloseInstrument(self.session)
        if bCheckError:
            self.check_error(error)

    def rf_centre_frequency_set(self, dFreq):
        obj = getDllObject('afDigitizerDll_RF_CentreFrequency_Set',
                           argtypes=[afDigitizerInstance_t, c_double])
        error = obj(self.session, c_double(dFreq))
        self.check_error(error)

    def rf_centre_frequency_get(self):
        obj = getDllObject('afDigitizerDll_RF_CentreFrequency_Get',
                           argtypes=[afDigitizerInstance_t, POINTER(c_double)])
        dValue = c_double()
        error = obj(self.session, byref(dValue))
        self.check_error(error)
        return dValue.value

    def rf_rf_input_level_set(self, dValue):
        obj = getDllObject('afDigitizerDll_RF_RFInputLevel_Set',
                           argtypes=[afDigitizerInstance_t, c_double])
        error = obj(self.session, c_double(dValue))
        self.check_error(error)

    def rf_rf_input_level_get(self):
        obj = getDllObject('afDigitizerDll_RF_RFInputLevel_Get',
                           argtypes=[afDigitizerInstance_t, POINTER(c_double)])
        dValue = c_double()
        error = obj(self.session, byref(dValue))
        self.check_error(error)
        return dValue.value

#    def modulation_generic_sampling_frequency_set(self, dValue):
#        obj = getDllObject('afDigitizerDll_Modulation_GenericSamplingFrequency_Set',
#                           argtypes=[afDigitizerInstance_t, c_double])
#        error = obj(self.session, c_double(dValue))
#        self.check_error(error)

    def modulation_generic_sampling_frequency_set(self, dValue):
        obj = getDllObject('afDigitizerDll_Modulation_SetGenericSamplingFreqRatio',
                           argtypes=[afDigitizerInstance_t, c_long, c_long])
        error = obj(self.session, c_long(int(dValue)), c_long(1))
        self.check_error(error)

    def modulation_generic_sampling_frequency_get(self):
        obj = getDllObject('afDigitizerDll_Modulation_GenericSamplingFrequency_Get',
                           argtypes=[afDigitizerInstance_t, POINTER(c_double)])
#                           UndecimatedSamplingFrequency
#                           afDigitizerDll_Modulation_DecimatedSamplingFrequency_Get
        dValue = c_double()
        error = obj(self.session, byref(dValue))
        self.check_error(error)
        return dValue.value

    def rf_remove_dc_offset_set(self, bOn=True):
        obj = getDllObject('afDigitizerDll_RF_RemoveDCOffset_Set',
                           argtypes=[afDigitizerInstance_t, AFBOOL])
        error = obj(self.session, AFBOOL(bOn))
        self.check_error(error)

    def rf_remove_dc_offset_get(self):
        obj = getDllObject('afDigitizerDll_RF_RemoveDCOffset_Get',
                           argtypes=[afDigitizerInstance_t, POINTER(AFBOOL)])
        pOn = AFBOOL()
        error = obj(self.session, byref(pOn))
        self.check_error(error)
        return bool(pOn.value)

    def capture_iq_capt_mem(self, nSamples):
        # define buffer type
        nSamples = int(nSamples)
        typeBuffer = c_float*nSamples
        obj = getDllObject('afDigitizerDll_Capture_IQ_CaptMem',
                           argtypes=[afDigitizerInstance_t, c_ulong,
                                     POINTER(typeBuffer),
                                     POINTER(typeBuffer)])
        # pre-allocate memory
        lValueI = typeBuffer()
        lValueQ = typeBuffer()
        error = obj(self.session, c_ulong(nSamples), byref(lValueI), byref(lValueQ))
        self.check_error(error)
        return (list(lValueI), list(lValueQ))

    def trigger_source_set(self, iOption=0):
        """Options for tigger are given in .ini file"""
        obj = getDllObject('afDigitizerDll_Trigger_Source_Set',
                           argtypes=[afDigitizerInstance_t, c_int])
        error = obj(self.session, c_int(iOption))
        self.check_error(error)

    def trigger_source_get(self):
        obj = getDllObject('afDigitizerDll_Trigger_Source_Get',
                           argtypes=[afDigitizerInstance_t, POINTER(c_int)])
        iOption = c_int()
        error = obj(self.session, byref(iOption))
        self.check_error(error)
        return int(iOption.value)


    def modulation_mode_set(self, iOption=0):
        """Modes are [mmUMTS=0, mmGSM=1, mmCDMA20001x=2, mmEmu2319=4, mmGeneric=5]"""
        obj = getDllObject('afDigitizerDll_Modulation_Mode_Set',
                           argtypes=[afDigitizerInstance_t, c_int])
        error = obj(self.session, c_int(iOption))
        self.check_error(error)


    def modulation_mode_get(self):
        """Modes are [mmUMTS=0, mmGSM=1, mmCDMA20001x=2, mmEmu2319=4, mmGeneric=5]"""
        obj = getDllObject('afDigitizerDll_Modulation_Mode_Get',
                           argtypes=[afDigitizerInstance_t, POINTER(c_int)])
        iOption = c_int()
        error = obj(self.session, byref(iOption))
        self.check_error(error)
        return int(iOption.value)


    def error_message_get(self):
        bufferLen = c_ulong(256)
        msgBuffer = STRING(' '*256)
        ErrorMessage_Get(self.session, msgBuffer, bufferLen)
        return msgBuffer.value

    def check_error(self, error=0):
        """If error occurred, get error message and raise error"""
        if error:
            raise Error(self.error_message_get())
        


if __name__ == '__main__':
    # test driver
    Digitizer = afDigitizer()
    Digitizer.create_object()
    Digitizer.boot_instrument('PXI8::15::INSTR', 'PXI8::14::INSTR')
    print Digitizer.modulation_mode_get()
    dFreq = Digitizer.modulation_generic_sampling_frequency_get()
    print 'Current frequency: ' + str(dFreq)
    Digitizer.modulation_generic_sampling_frequency_set(250E6)
    dFreq = Digitizer.modulation_generic_sampling_frequency_get()
    print 'Current frequency: ' + str(dFreq)
    [lI, lQ] = Digitizer.capture_iq_capt_mem(2048)
    print Digitizer.modulation_mode_get()
#    print lI, lQ
    Digitizer.close_instrument()
    Digitizer.destroy_object()

