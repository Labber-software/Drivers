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
            
    def lo_reference_set(self, lLORef):
        """Modes are [lormOCXO=0, lormInternal=1, lormExternalDaisy=2, lormExternalTerminated=3]"""
        obj = getDllObject('afDigitizerDll_LO_Reference_Set',
                           argtypes=[afDigitizerInstance_t, c_long])
        error = obj(self.session, c_long(lLORef))
        self.check_error(error)
        
    def lo_reference_get(self):
        """Modes are [lormOCXO=0, lormInternal=1, lormExternalDaisy=2, lormExternalTerminated=3]"""
        obj = getDllObject('afDigitizerDll_LO_Reference_Get',
                           argtypes=[afDigitizerInstance_t, POINTER(c_long)])
        dValue = c_long()
        error = obj(self.session, byref(dValue))
        self.check_error(error)
        return dValue.value

    def ref_is_locked(self):
        #Returns whether LO is locked to the external 10 Mhz reference when 
        #Reference is set to ExternalDaisy or ExternalTerminated.
        obj = getDllObject('afDigitizerDll_LO_ReferenceLocked_Get',
                           argtypes=[afDigitizerInstance_t, POINTER(c_long)])
        dValue = c_long()
        error = obj(self.session, byref(dValue))
        self.check_error(error)
        return dValue.value
 
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


    def modulation_generic_sampling_frequency_set(self, dValue):
        obj = getDllObject('afDigitizerDll_Modulation_SetGenericSamplingFreqRatio',
                           argtypes=[afDigitizerInstance_t, c_long, c_long])
        error = obj(self.session, c_long(int(dValue)), c_long(1))
        self.check_error(error)

    def modulation_generic_sampling_frequency_get(self):
        obj = getDllObject('afDigitizerDll_Modulation_GenericSamplingFrequency_Get',
                           argtypes=[afDigitizerInstance_t, POINTER(c_double)])
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
        
    def capture_if_capt_mem(self, nSamples):
        # define buffer type
        nSamples = int(nSamples)
        typeBuffer = c_float*nSamples
        obj = getDllObject('afDigitizerDll_Capture_IF_CaptMem',
                           argtypes=[afDigitizerInstance_t, c_ulong,
                                     POINTER(typeBuffer)])
        # pre-allocate memory
        lValue = typeBuffer()
        error = obj(self.session, c_ulong(nSamples), byref(lValue))
        self.check_error(error)
        return lValue

    def trigger_source_set(self, iOption=0):
        """Options for the trigger source are found in the .ini file for the digitizer
        Sources are
        [PXI_TRIG_0=0, PXI_TRIG_1=1, PXI_TRIG_2=2, PXI_TRIG_3=3, PXI_TRIG_4=4, PXI_TRIG_5=5,
        PXI_TRIG_6=6, PXI_TRIG_7=7, PXI_STAR=8, PXI_LBL_0=9, PXI_LBL_1=10, PXI_LBL_2=11, 
        PXI_LBL_3=12, PXI_LBL_4=13, PXI_LBL_5=14, PXI_LBL_6=15, PXI_LBL_7=16, PXI_LBL_8=17,
        PXI_LBL_9=18, PXI_LBL_10=19, PXI_LBL_11=20, PXI_LBL_12=21, LVDS_MARKER_0=22, LVDS_MARKER_1=23, 
        LVDS_MARKER_2=24, LVDS_MARKER_3=25, LVDS_AUX_0=26, LVDS_AUX_1=27, LVDS_AUX_2=28, LVDS_AUX_3=29,
        LVDS_AUX_4=30, LVDS_SPARE_0=31, SW_TRIG=32, LVDS_MARKER_4=33, INT_TIMER=34, INT_TRIG=35, FRONT_SMB=36]"""
        obj = getDllObject('afDigitizerDll_Trigger_Source_Set',
                           argtypes=[afDigitizerInstance_t, c_long])
        error = obj(self.session, c_long(iOption))
        self.check_error(error)

    def trigger_source_get(self):
        """Options for the trigger source are found in the .ini file for the digitizer
        Sources are
        [PXI_TRIG_0=0, PXI_TRIG_1=1, PXI_TRIG_2=2, PXI_TRIG_3=3, PXI_TRIG_4=4, PXI_TRIG_5=5,
        PXI_TRIG_6=6, PXI_TRIG_7=7, PXI_STAR=8, PXI_LBL_0=9, PXI_LBL_1=10, PXI_LBL_2=11, 
        PXI_LBL_3=12, PXI_LBL_4=13, PXI_LBL_5=14, PXI_LBL_6=15, PXI_LBL_7=16, PXI_LBL_8=17,
        PXI_LBL_9=18, PXI_LBL_10=19, PXI_LBL_11=20, PXI_LBL_12=21, LVDS_MARKER_0=22, LVDS_MARKER_1=23, 
        LVDS_MARKER_2=24, LVDS_MARKER_3=25, LVDS_AUX_0=26, LVDS_AUX_1=27, LVDS_AUX_2=28, LVDS_AUX_3=29,
        LVDS_AUX_4=30, LVDS_SPARE_0=31, SW_TRIG=32, LVDS_MARKER_4=33, INT_TIMER=34, INT_TRIG=35, FRONT_SMB=36]"""
        obj = getDllObject('afDigitizerDll_Trigger_Source_Get',
                           argtypes=[afDigitizerInstance_t, POINTER(c_long)])
        iOption = c_long()
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

    #Added 2014-02-22 by Philip    
    #Detects whether Whether a trigger event has occurred after arming the 
    #AF3070 trigger with the afRfDigitizerDll_Trigger_Arm method. Read-only
    def trigger_detected_get(self):
        obj = getDllObject('afRfDigitizerDll_Trigger_Detected_Get',
                           argtypes=[afDigitizerInstance_t, POINTER(AFBOOL)])
        pOn = AFBOOL()
        error = obj(self.session, byref(pOn))
        self.check_error(error)
        return bool(pOn.value)

    #Added 2014-02-22 by Philip
    #Sets the trigger polarity

    def trigger_polarity_set(self, iOption=0):
        """Modes are [Positive=0, Negative=1]"""
        obj = getDllObject('afDigitizerDll_Trigger_EdgeGatePolarity_Set',
                           argtypes=[afDigitizerInstance_t, c_int])
        error = obj(self.session, c_int(iOption))
        self.check_error(error)
        
    def trigger_polarity_get(self):
        """Modes are [Positive=0, Negative=1]"""
        obj = getDllObject('afDigitizerDll_Trigger_EdgeGatePolarity_Get',
                           argtypes=[afDigitizerInstance_t, POINTER(c_int)])
        dValue = c_int()
        error = obj(self.session, byref(c_int))
        self.check_error(error)
        return dValue.value
 
    def trigger_type_set(self, iOption=0):
        """Modes are [Edge=0, Gate=1]"""
        obj = getDllObject('afDigitizerDll_Trigger_TType_Set',
                           argtypes=[afDigitizerInstance_t, c_int])
        error = obj(self.session, c_int(iOption))
        self.check_error(error)
        
    def trigger_type_get(self):
        """Modes are [Positive=0, Negative=1]"""
        obj = getDllObject('afDigitizerDll_Trigger_TType_Get',
                           argtypes=[afDigitizerInstance_t, POINTER(c_int)])
        dValue = c_int()
        error = obj(self.session, byref(c_int))
        self.check_error(error)
        return dValue.value
 
    def trigger_arm_set(self, inSamples=0):
        obj = getDllObject('afDigitizerDll_Trigger_Arm',
                           argtypes=[afDigitizerInstance_t, c_int])
        error = obj(self.session, c_int(inSamples))
        self.check_error(error)

    def data_capture_complete_get(self):
        obj = getDllObject('afDigitizerDll_Capture_IQ_CaptComplete_Get',
                           argtypes=[afDigitizerInstance_t, POINTER(AFBOOL)])
        dValue = AFBOOL()
        error = obj(self.session, byref(dValue))
        self.check_error(error)
        return bool(dValue.value)
 
    def error_message_get(self):
        bufferLen = c_ulong(256)
        msgBuffer = STRING(' '*256)
        ErrorMessage_Get(self.session, msgBuffer, bufferLen)
        return msgBuffer.value

    def check_error(self, error=0):
        """If error occurred, get error message and raise error"""
        if error:
            raise Error(self.error_message_get())
            
    def rf_level_correction_get(self):
        obj = getDllObject('afDigitizerDll_RF_LevelCorrection_Get',
                           argtypes=[afDigitizerInstance_t, POINTER(c_double)])
        dValue = c_double()
        error = obj(self.session, byref(dValue))
        self.check_error(error)
        return dValue.value      
        
    def trigger_pre_edge_trigger_samples_get(self):
        afDigitizerDll_Trigger_PreEdgeTriggerSamples_Get = getDllObject('afDigitizerDll_Trigger_PreEdgeTriggerSamples_Get', 
                                                                       argtypes = [afDigitizerInstance_t, POINTER(c_ulong)])
        dValue=c_ulong()
        error = afDigitizerDll_Trigger_PreEdgeTriggerSamples_Get(self.session, byref(dValue))
        self.check_error(error)
        return dValue.value
        
    def trigger_pre_edge_trigger_samples_set(self, preEdgeTriggerSamples):
        afDigitizerDll_Trigger_PreEdgeTriggerSamples_Set = getDllObject('afDigitizerDll_Trigger_PreEdgeTriggerSamples_Set', 
                                                              argtypes = [afDigitizerInstance_t, c_ulong])
        error = afDigitizerDll_Trigger_PreEdgeTriggerSamples_Set(self.session, c_ulong(preEdgeTriggerSamples))
        self.check_error(error)    
        
    def trigger_IQ_bandwidth_set(self, dBandWidth, iOption=0):
        afDigitizerDll_Trigger_SetIntIQTriggerDigitalBandwidth = getDllObject('afDigitizerDll_Trigger_SetIntIQTriggerDigitalBandwidth', 
                                                                       argtypes = [afDigitizerInstance_t, c_double, c_int, POINTER(c_double)])
        dValue=c_double()
        error = afDigitizerDll_Trigger_SetIntIQTriggerDigitalBandwidth(self.session, c_double(dBandWidth), c_int(iOption), byref(dValue))
        self.check_error(error)
        return dValue.value
 
    def check_ADCOverload(self):
        afDigitizerDll_Capture_IQ_ADCOverload_Get = getDllObject('afDigitizerDll_Capture_IQ_ADCOverload_Get',
                                                                 argtypes =[afDigitizerInstance_t, POINTER(AFBOOL)])
        bADCOverload = AFBOOL()
        error = afDigitizerDll_Capture_IQ_ADCOverload_Get(self.session, byref(bADCOverload))
        self.check_error(error)
        return bADCOverload.value
        
    def rf_userLOPosition_get(self):
        afDigitizerDll_RF_UserLOPosition_Get = getDllObject('afDigitizerDll_RF_UserLOPosition_Get', argtypes=[afDigitizerInstance_t, POINTER(c_int)])
        iValue = c_int()
        error = afDigitizerDll_RF_UserLOPosition_Get(self.session, byref(iValue))
        self.check_error(error)
        return iValue.value
        
    def rf_userLOPosition_set(self, iLOPosition):
        afDigitizerDll_RF_UserLOPosition_Set = getDllObject('afDigitizerDll_RF_UserLOPosition_Set', argtypes = [afDigitizerInstance_t, c_int])
        error = afDigitizerDll_RF_UserLOPosition_Set(self.session, iLOPosition)
        self.check_error(error)

 

if __name__ == '__main__':
    # test driver
    Digitizer = afDigitizer()
    Digitizer.create_object()
    #Digitizer.boot_instrument('PXI8::15::INSTR', 'PXI8::14::INSTR')
    Digitizer.boot_instrument('PXI7::15::INSTR', 'PXI6::10::INSTR')
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