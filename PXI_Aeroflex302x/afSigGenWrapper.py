import ctypes
from ctypes import c_int, c_long, c_double, c_ulong, POINTER, byref

class Error(Exception):
    pass

# open dll
_lib = ctypes.WinDLL('afSigGenDll_32')

# define data types used by this dll
STRING = ctypes.c_char_p
AFBOOL = c_long

# define variables
afSigGenInstance_t = c_long

# define dll function objects in python
CreateObject = _lib.afSigGenDll_CreateObject
CreateObject.restype = c_long
CreateObject.argtypes = [POINTER(afSigGenInstance_t)]
DestroyObject = _lib.afSigGenDll_DestroyObject
DestroyObject.restype = c_long
DestroyObject.argtypes = [afSigGenInstance_t]
BootInstrument = _lib.afSigGenDll_BootInstrument
BootInstrument.restype = c_long
BootInstrument.argtypes = [afSigGenInstance_t, STRING, STRING, AFBOOL]
CloseInstrument = _lib.afSigGenDll_CloseInstrument
CloseInstrument.restype = c_long
CloseInstrument.argtypes = [afSigGenInstance_t]
RF_CurrentFrequency_Get = _lib.afSigGenDll_RF_CurrentFrequency_Get
RF_CurrentFrequency_Get.restype = c_long
RF_CurrentFrequency_Get.argtypes = [afSigGenInstance_t, POINTER(c_double)]
RF_CurrentFrequency_Set = _lib.afSigGenDll_RF_CurrentFrequency_Set
RF_CurrentFrequency_Set.restype = c_long
RF_CurrentFrequency_Set.argtypes = [afSigGenInstance_t, c_double]
RF_CurrentLevel_Get = _lib.afSigGenDll_RF_CurrentLevel_Get
RF_CurrentLevel_Get.restype = c_long
RF_CurrentLevel_Get.argtypes = [afSigGenInstance_t, POINTER(c_double)]
RF_CurrentLevel_Set = _lib.afSigGenDll_RF_CurrentLevel_Set
RF_CurrentLevel_Set.restype = c_long
RF_CurrentLevel_Set.argtypes = [afSigGenInstance_t, c_double]
ErrorMessage_Get = _lib.afSigGenDll_ErrorMessage_Get
ErrorMessage_Get.restype = c_long
ErrorMessage_Get.argtypes = [afSigGenInstance_t, STRING, c_ulong]

def getDllObject(sName, argtypes=[afSigGenInstance_t], restype=c_long):
    """Create a dll ojbect with input and output types"""    
    obj = getattr(_lib, sName)
    obj.restype = restype
    obj.argypes = argtypes
    return obj


class afSigGen():
    """Represent a signal generator, redefines the dll function in python"""

    def __init__(self):
        """The init case defines a session ID, used to identify the instrument"""
        # create a session id
        self.session = afSigGenInstance_t()

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

    def rf_current_frequency_set(self, dFreq):
        error = RF_CurrentFrequency_Set(self.session, c_double(dFreq))
        self.check_error(error)

    def rf_current_frequency_get(self):
        pFrequency = c_double()
        error = RF_CurrentFrequency_Get(self.session, byref(pFrequency))
        self.check_error(error)
        return (pFrequency.value)

    def rf_current_level_set(self, dPower):
        error = RF_CurrentLevel_Set(self.session, c_double(dPower))
        self.check_error(error)

    def rf_current_level_get(self):
        pPower = c_double()
        error = RF_CurrentLevel_Get(self.session, byref(pPower))
        self.check_error(error)
        return (pPower.value)

    def rf_current_output_enable_set(self, bOn=True):
        obj = getDllObject('afSigGenDll_RF_CurrentOutputEnable_Set',
                           argtypes=[afSigGenInstance_t, AFBOOL])
        error = obj(self.session, AFBOOL(bOn))
        self.check_error(error)

    def rf_current_output_enable_get(self):
        obj = getDllObject('afSigGenDll_RF_CurrentOutputEnable_Get',
                           argtypes=[afSigGenInstance_t, POINTER(AFBOOL)])
        pOn = AFBOOL()
        error = obj(self.session, byref(pOn))
        self.check_error(error)
        return bool(pOn.value)

    def rf_current_level_mode_set(self, iOption=0):
        """Options for level mode are {Auto, Frozen, Peak, RMS}"""
        obj = getDllObject('afSigGenDll_RF_CurrentLevelMode_Set',
                           argtypes=[afSigGenInstance_t, c_int])
        error = obj(self.session, c_int(iOption))
        self.check_error(error)

    def rf_current_level_mode_get(self):
        obj = getDllObject('afSigGenDll_RF_CurrentLevelMode_Get',
                           argtypes=[afSigGenInstance_t, POINTER(c_int)])
        iOption = c_int()
        error = obj(self.session, byref(iOption))
        self.check_error(error)
        return int(iOption.value)

    def rf_modulation_source_set(self, iOption=0):
        """Options for modulation are {CW, LVDS, ARB, AM, FM, ExtAnalog}"""
        # for some reason, the dll enum has the definition
#        afSigGenDll_msCW	= 3,
#        afSigGenDll_msLVDS	= 0,
#        afSigGenDll_msARB	= 1,
#        afSigGenDll_msAM	= 4,
#        afSigGenDll_msFM	= 5,
#        afSigGenDll_msExtAnalog	= 6
        # use a dict to convert
        dConv = {0:3, 1:0, 2:1, 3:4, 4:5, 5:6}
        iOption = dConv[iOption]
        obj = getDllObject('afSigGenDll_RF_ModulationSource_Set',
                           argtypes=[afSigGenInstance_t, c_int])
        error = obj(self.session, c_int(iOption))
        self.check_error(error)

    def rf_modulation_source_get(self):
        obj = getDllObject('afSigGenDll_RF_ModulationSource_Get',
                           argtypes=[afSigGenInstance_t, POINTER(c_int)])
        iOption = c_int()
        error = obj(self.session, byref(iOption))
        self.check_error(error)
        iOpt = int(iOption.value)
        # for some reason, the dll enum has the definition
#        afSigGenDll_msCW	= 3,
#        afSigGenDll_msLVDS	= 0,
#        afSigGenDll_msARB	= 1,
#        afSigGenDll_msAM	= 4,
#        afSigGenDll_msFM	= 5,
#        afSigGenDll_msExtAnalog	= 6
        # use a dict to convert
        dConv = {0:3, 1:0, 2:1, 3:4, 4:5, 5:6}
        iOut = dConv.values().index(iOpt)
        return int(iOut)

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
    SigGen = afSigGen()
    SigGen.create_object()
    SigGen.boot_instrument('PXI6::14::INSTR', 'PXI6::13::INSTR')
    dPower = SigGen.rf_current_level_get()
    print 'Current power: ' + str(dPower)
    SigGen.rf_current_level_set(0)
    dPower = SigGen.rf_current_level_get()
    print 'Current power: ' + str(dPower)
    dFreq = SigGen.rf_current_frequency_get()
    print 'Current frequency: ' + str(dFreq)
    SigGen.rf_current_frequency_set(70E6)
    dFreq = SigGen.rf_current_frequency_get()
    print 'Current frequency: ' + str(dFreq)
    SigGen.rf_current_output_enable_set(True)
    print SigGen.rf_current_output_enable_get()
    import time
    time.sleep(1)
    SigGen.rf_current_output_enable_set(False)
    print SigGen.rf_current_output_enable_get()
    for n in range(6):
        SigGen.rf_modulation_source_set(n)
        print SigGen.rf_modulation_source_get()
    for n in range(4):
        SigGen.rf_current_level_mode_set(n)
        print SigGen.rf_current_level_mode_get()
    SigGen.close_instrument()
    SigGen.destroy_object()

