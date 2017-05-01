import ctypes
from ctypes import *

class Error(Exception):
    pass
class ARBPARAMS(Structure):
    _fields_ = [("IQ file format", c_int),
                ("IQ data format", c_int),
                ("Input sampling rate", c_double),
                ("Output sampling rate", c_double),
                ("Signal bandwidth", c_double),
                ("Oversampling factor",c_double),
                ("Marker Type", c_int),
                ("Scaling Factor", c_double),
                ("Marker filename", c_char_p)]

# open dll
_lib = ctypes.WinDLL('afSigGenDll_32')
#_AeroFlex = ctypes.WinDLL('AeroPackagerRoutines')

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

    def lo_reference_set(self, lLORef):
        """Modes are [lormOCXO=0, lormInternal=1, lormExternalDaisy=2, lormExternalTerminated=3]"""
        obj = getDllObject('afSigGenDll_LO_Reference_Set',
                           argtypes=[afSigGenInstance_t, c_long])
        error = obj(self.session, c_long(lLORef))
        self.check_error(error)
        
    def lo_reference_get(self):
        """Modes are [lormOCXO=0, lormInternal=1, lormExternalDaisy=2, lormExternalTerminated=3]"""
        obj = getDllObject('afSigGenDll_LO_Reference_Get',
                           argtypes=[afSigGenInstance_t, POINTER(c_long)])
        dValue = c_long()
        error = obj(self.session, byref(dValue))
        self.check_error(error)
        return dValue.value

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

    def trigger_source_set(self, iOption=0):
        """See the Signal Generator .ini file for the options for the trigger source"""
        #obj = getDllObject('afSigGenDll_Trigger_Source_Set',
        #                   argtypes=[afSigGenInstance_t, c_long])
        #error = obj(self.session, c_long(iOption))
        #self.check_error(error)

    def trigger_source_get(self):
        """See the Signal Generator .ini file for the options for the trigger source"""
        #obj = getDllObject('afSigGenDll_Trigger_Source_Get',
        #                   argtypes=[afSigGenInstance_t, POINTER(c_long)])
        #iOption = c_long()
       # error = obj(self.session, byref(iOption))
        #self.check_error(error)
        return 1
        #return int(iOption.value)
    
    def negative_edge_set(self, bNegEdge=False):
        #This property sets or returns whether the external ARB trigger 
        #(when enabled) triggers on its negative edge (True) or not (False). 
        obj = getDllObject('afSigGenDll_ARB_ExternalTrigger_NegativeEdge_Set',
                           argtypes=[afSigGenInstance_t, AFBOOL])
        error = obj(self.session, AFBOOL(bNegEdge))
        self.check_error(error)

    def negative_edge_get(self):
        #This property sets or returns whether the external ARB trigger 
        #(when enabled) triggers on its negative edge (True) or not (False). 
        obj = getDllObject('afSigGenDll_ARB_ExternalTrigger_NegativeEdge_Get',
                           argtypes=[afSigGenInstance_t, POINTER(AFBOOL)])
        bNegEdge = AFBOOL()
        error = obj(self.session, byref(bNegEdge))
        self.check_error(error)
        return bool(bNegEdge.value)
        
    def external_trigger_gated_set(self, bGated=False):
        #Sets or queries whether the external ARB trigger 
        #(when enabled) gates the ARB output (True), or is single-shot (False). 
        obj = getDllObject('afSigGenDll_ARB_ExternalTrigger_Gated_Set',
                           argtypes=[afSigGenInstance_t, AFBOOL])
        error = obj(self.session, AFBOOL(bGated))
        self.check_error(error)

    def external_trigger_gated_get(self):
        #This property sets or returns whether the external ARB trigger 
        #(when enabled) triggers on its negative edge (True) or not (False). 
        obj = getDllObject('afSigGenDll_ARB_ExternalTrigger_Gated_Get',
                           argtypes=[afSigGenInstance_t, POINTER(AFBOOL)])
        bGated = AFBOOL()
        error = obj(self.session, byref(bGated))
        self.check_error(error)
        return bool(bGated.value)
        
    def ARB_external_trigger_enable_set(self, bEnable=False):
        #Sets or queries whether the external ARB trigger is enabled (True) or not (False). 
        #If the ARB trigger is to be used, it must first be connected using the afSigGen routing matrix,  
        #otherwise enabling this property will have no effect. 
        obj = getDllObject('afSigGenDll_ARB_ExternalTrigger_Enable_Set',
                           argtypes=[afSigGenInstance_t, AFBOOL])
        error = obj(self.session, AFBOOL(bEnable))
        self.check_error(error)

    def ARB_external_trigger_enable_get(self):
        #This property sets or returns whether the external ARB trigger 
        #(when enabled) triggers on its negative edge (True) or not (False). 
        obj = getDllObject('afSigGenDll_ARB_ExternalTrigger_Enable_Get',
                           argtypes=[afSigGenInstance_t, POINTER(AFBOOL)])
        bEnable = AFBOOL()
        error = obj(self.session, byref(bEnable))
        self.check_error(error)
        return bool(bEnable.value)
    
    def ARB_Fileplaying_get(self):
        #This property provides the file name of the arb file that is 
        #currently playing. If no file is playing, the property returns an empty string.  
        obj = getDllObject('afSigGenDll_ARB_FilePlaying_Get',
                           argtypes=[afSigGenInstance_t, POINTER(c_long), c_long])
        fileNameBuffer = c_long()
        bufferLen = c_long()
        error = obj(self.session, byref(fileNameBuffer))
        self.check_error(error)
        return long(fileNameBuffer.value)
 
    def ARB_Is_Playing_get(self):
        #This property indicates wdRFBandWidthhether an arb file is currently playing (True) or not (False). 
        obj = getDllObject('afSigGenDll_ARB_IsPlaying_Get',
                           argtypes=[afSigGenInstance_t, POINTER(AFBOOL)])
        bIsPlaying = AFBOOL()
        error = obj(self.session, byref(bIsPlaying))
        self.check_error(error)
        return bool(bIsPlaying.value)
        
        
##This function takes an I wave and Q wave and writes them to predefined files
##It writes them as 32bit IEEE floating point
##path = a string containing the path of the folder to be used.  It should be terminated with a backslash

    def WriteIQfloat_set(self,dI,dQ,sPath):
        import os.path
        from array import array
        
        sIpath = sPath + 'I_FILE.dat'
        sQpath = sPath + 'Q_FILE.dat'
        
#        if os.path.isfile(sIpath):
#            sIpath
#        if os.path.isfile(sQpath):
#            del(sQpath)
        
        Iref = open(sIpath, 'wb')
        float_array = array('d', dI)
        float_array.tofile(Iref)
        Iref.close()
        
        Qref = open(sQpath, 'wb')
        float_array = array('d', dQ)
        float_array.tofile(Qref)
        Qref.close()
    
##    //This function writes a marker file with a predefined name which specifies one marker with one on and one off time
##//It assumes that the Oversampling and Decimation are 1, which is typical for our modulation
##//path = is a string containing the path of the folder to be used.  It should be terminated with a backslash
##//length = is the frame length (in number of samples) of the associated IQ files
##//t_on = the on-time (in number of samples) of the marker
##//t_off = the off-time (in number of samples) of the marker
##//path = a string containing the path of the folder to be used.  It should be terminated with a backslash
    def WriteMarkerFile(self,dLen,dtOn,dtOff,sPath):
        sMpath = sPath + 'M_FILE.mkr'
        
#        if os.path.isfile(sMpath):
#            del(sMpath)
        
        Mref = open(sMpath, 'w')
        Mref.write('FrameLength=' + str(dLen) + '\r\n')
        Mref.write('Oversampling=1  \r\nDecimation=1 \r\nMkr1=General \r\nMarker 1 \r\n')
        Mref.write(str(dtOn) + ',' + str(dtOff) + '\r\n')        
        Mref.close()
        
    def WritePackage(self,sPath,sAIQfile,dSampFreq,dRFBandWidth):          
        #Input parameters for Packager        
        iIQfileformat = 13
        iIQdataformat = 27
        dinFs = dSampFreq
        doutFs = dSampFreq
        dBW = dRFBandWidth
        dOS = 1
        imType = 42
        dscale = 100
        sDesc = 'Created in Python'
        AeroFlexDLL = ctypes.WinDLL('af302xCPackager')
        obj = getattr(AeroFlexDLL, 'PackageToAiq')
        obj.argypes = [STRING, STRING, STRING, STRING, ARBPARAMS]
        obj.restypes = c_long
        structParams = ARBPARAMS(c_int(iIQfileformat), c_int(iIQdataformat), c_double(dinFs), c_double(doutFs), c_double(dBW), c_double(dOS), c_int(imType), c_double(dscale), STRING(sPath + 'M_FILE.mkr'))
        error = obj(STRING(sPath + 'I_FILE.dat'),STRING(sPath + 'Q_FILE.dat'),STRING(sPath + sAIQfile), STRING(sDesc), byref(structParams))        
        
        
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
    print ('Current power: ' + str(dPower))
    SigGen.rf_current_level_set(0)
    dPower = SigGen.rf_current_level_get()
    print ('Current power: ' + str(dPower))
    dFreq = SigGen.rf_current_frequency_get()
    print ('Current frequency: ' + str(dFreq))
    SigGen.rf_current_frequency_set(70E6)
    dFreq = SigGen.rf_current_frequency_get()
    print ('Current frequency: ' + str(dFreq))
    SigGen.rf_current_output_enable_set(True)
    print (SigGen.rf_current_output_enable_get())
    import time
    time.sleep(1)
    SigGen.rf_current_output_enable_set(False)
    print (SigGen.rf_current_output_enable_get())
    for n in range(6):
        SigGen.rf_modulation_source_set(n)
        print (SigGen.rf_modulation_source_get())
    for n in range(4):
        SigGen.rf_current_level_mode_set(n)
        print (SigGen.rf_current_level_mode_get())
    SigGen.close_instrument()
    SigGen.destroy_object()

