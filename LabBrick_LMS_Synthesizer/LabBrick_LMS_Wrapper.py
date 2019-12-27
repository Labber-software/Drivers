import os, ctypes
from ctypes import c_int, c_uint, c_bool, c_float, POINTER, byref

class Error(Exception):
    pass

# open dll
sPath = os.path.dirname(os.path.abspath(__file__))
_lib = ctypes.CDLL(os.path.join(sPath, 'DLL', 'vnx_fmsynth'))

# define data types used by this dll
DEVID = c_uint
LVSTATUS = c_uint
STRING = ctypes.c_char_p
ACTIVEDEVICES = DEVID*64


def getDllObject(sName, argtypes=[DEVID,], restype=LVSTATUS):
    """Create a dll ojbect with input and output types"""    
    obj = getattr(_lib, sName)
    obj.restype = restype
    obj.argypes = argtypes
    return obj


#VNX_FSYNSTH_API int fnLMS_InitDevice(DEVID deviceID);
#VNX_FSYNSTH_API int fnLMS_CloseDevice(DEVID deviceID);
fnLMS_InitDevice = getDllObject('fnLMS_InitDevice')
fnLMS_CloseDevice = getDllObject('fnLMS_CloseDevice')

#VNX_FSYNSTH_API void fnLMS_SetTestMode(bool testmode);
#VNX_FSYNSTH_API int fnLMS_GetNumDevices();
#VNX_FSYNSTH_API int fnLMS_GetDevInfo(DEVID *ActiveDevices);
#VNX_FSYNSTH_API int fnLMS_GetModelName(DEVID deviceID, char *ModelName);
#VNX_FSYNSTH_API int fnLMS_GetSerialNumber(DEVID deviceID);
fnLMS_SetTestMode = getDllObject('fnLMS_SetTestMode', [c_bool], None)
fnLMS_GetNumDevices = getDllObject('fnLMS_GetNumDevices', [], restype=c_int)
fnLMS_GetDevInfo = getDllObject('fnLMS_GetDevInfo', [POINTER(ACTIVEDEVICES)], restype=c_int)
fnLMS_GetModelName = getDllObject('fnLMS_GetModelName', [DEVID, STRING], restype=c_int)
fnLMS_GetSerialNumber = getDllObject('fnLMS_GetSerialNumber', restype=c_int)

#VNX_FSYNSTH_API LVSTATUS fnLMS_SetFrequency(DEVID deviceID, int frequency);
#VNX_FSYNSTH_API LVSTATUS fnLMS_SetPowerLevel(DEVID deviceID, int powerlevel);
#VNX_FSYNSTH_API LVSTATUS fnLMS_SetRFOn(DEVID deviceID, bool on);
#VNX_FSYNSTH_API LVSTATUS fnLMS_SetUseInternalRef(DEVID deviceID, bool internal);
#VNX_FSYNSTH_API LVSTATUS fnLMS_SetUseExternalPulseMod(DEVID deviceID, bool external);
#VNX_FSYNSTH_API LVSTATUS fnLMS_SetFastPulsedOutput(DEVID deviceID, float pulseontime, float pulsereptime, bool on);
fnLMS_SetFrequency = getDllObject('fnLMS_SetFrequency', [DEVID, c_int])
fnLMS_SetPowerLevel = getDllObject('fnLMS_SetPowerLevel', [DEVID, c_int])
fnLMS_SetRFOn = getDllObject('fnLMS_SetRFOn', [DEVID, c_bool])
fnLMS_SetUseInternalRef = getDllObject('fnLMS_SetUseInternalRef', [DEVID, c_bool])
fnLMS_SetUseExternalPulseMod = getDllObject('fnLMS_SetUseExternalPulseMod', [DEVID, c_bool])
fnLMS_SetFastPulsedOutput = getDllObject('fnLMS_SetFastPulsedOutput', [DEVID, c_float, c_float, c_bool])


# VNX_FSYNSTH_API int fnLMS_GetFrequency(DEVID deviceID);
# VNX_FSYNSTH_API int fnLMS_GetPowerLevel(DEVID deviceID);
# VNX_FSYNSTH_API int fnLMS_GetRF_On(DEVID deviceID);
# VNX_FSYNSTH_API int fnLMS_GetUseInternalRef(DEVID deviceID);
fnLMS_GetFrequency = getDllObject('fnLMS_GetFrequency', restype=c_int)
fnLMS_GetPowerLevel = getDllObject('fnLMS_GetPowerLevel', restype=c_int)
fnLMS_GetRF_On = getDllObject('fnLMS_GetRF_On', restype=c_int)
fnLMS_GetUseInternalRef = getDllObject('fnLMS_GetUseInternalRef', restype=c_int)

#VNX_FSYNSTH_API float fnLMS_GetPulseOnTime(DEVID deviceID);
#VNX_FSYNSTH_API float fnLMS_GetPulseOffTime(DEVID deviceID);
#VNX_FSYNSTH_API int fnLMS_GetPulseMode(DEVID deviceID);
#VNX_FSYNSTH_API int fnLMS_GetUseInternalPulseMod(DEVID deviceID);
fnLMS_GetPulseOnTime = getDllObject('fnLMS_GetPulseOnTime', restype=c_float)
fnLMS_GetPulseOffTime = getDllObject('fnLMS_GetPulseOffTime', restype=c_float)
fnLMS_GetPulseMode = getDllObject('fnLMS_GetPulseMode', restype=c_int)
fnLMS_GetUseInternalPulseMod = getDllObject('fnLMS_GetUseInternalPulseMod', restype=c_int)

#VNX_FSYNSTH_API int fnLMS_GetMaxPwr(DEVID deviceID);
#VNX_FSYNSTH_API int fnLMS_GetMinPwr(DEVID deviceID);
#VNX_FSYNSTH_API int fnLMS_GetMaxFreq(DEVID deviceID);
#VNX_FSYNSTH_API int fnLMS_GetMinFreq(DEVID deviceID);
fnLMS_GetMaxPwr = getDllObject('fnLMS_GetMaxPwr', restype=c_int)
fnLMS_GetMinPwr = getDllObject('fnLMS_GetMinPwr', restype=c_int)
fnLMS_GetMaxFreq = getDllObject('fnLMS_GetMaxFreq', restype=c_int)
fnLMS_GetMinFreq = getDllObject('fnLMS_GetMinFreq', restype=c_int)


class LabBrick_Synthesizer():
    """Represent a signal generator, redefines the dll function in python"""

    def __init__(self, bTestMode=False):
        """The init case defines a session ID, used to identify the instrument"""
        fnLMS_SetTestMode(c_bool(bTestMode))
        self.device_id = None

    def initDevice(self, serial):
        # get list of devices
        try:
            iSerial = int(serial)
        except:
            iSerial = 0
        lDev = self.getListOfDevices()
        lSerial = [d['serial'] for d in lDev]
        if iSerial not in lSerial:
            # raise error if device not found
            sErr = (
                ('Device with serial number "%d" cannot be found.' % iSerial) +
                '\n\nDevices detected:\n')
            for dDev in lDev:
                sErr += ('Name: %s, Serial: %d\n' % (dDev['name'], dDev['serial']))
            raise Error(sErr)
        indx = lSerial.index(iSerial)
        self.device_id = DEVID(lDev[indx]['device_id'])
        status = fnLMS_InitDevice(self.device_id)
        self.maxPower = float(fnLMS_GetMaxPwr(self.device_id))*0.25
        self.minPower = float(fnLMS_GetMinPwr(self.device_id))*0.25
        self.maxFreq = float(fnLMS_GetMaxFreq(self.device_id))*10.
        self.minFreq = float(fnLMS_GetMinFreq(self.device_id))*10.
        self.check_error(status)

    def closeDevice(self):
        if self.device_id is not None:
            fnLMS_CloseDevice(self.device_id)

    def getListOfDevices(self):
        lDevice = []
        nDev = int(fnLMS_GetNumDevices())
        if nDev==0:
            return []
        # init list of devices
        devices = ACTIVEDEVICES()
        nDev = fnLMS_GetDevInfo(byref(devices))
        for n1 in range(nDev):
            nameBuffer = STRING(b' '*32)
            fnLMS_GetModelName(devices[n1], nameBuffer)
            serial = int(fnLMS_GetSerialNumber(devices[n1]))
            d = dict()
            d['name'] = str(nameBuffer.value.decode())
            d['serial'] = serial
            d['device_id'] = int(devices[n1])
            lDevice.append(d)
        return lDevice

    def setFrequency(self, dFreq):
        # make sure frequency is in range
        dFreq = max(self.minFreq, min(self.maxFreq, dFreq))
        iFreq = int(dFreq/10.)
        status = fnLMS_SetFrequency(self.device_id, c_int(iFreq))
        self.check_error(status)
        return dFreq

    def setPowerLevel(self, dPower):
        iPower = int(dPower/0.25)
        status = fnLMS_SetPowerLevel(self.device_id, c_int(iPower))
        self.check_error(status)

    def setRFOn(self, bRFOn):
        status = fnLMS_SetRFOn(self.device_id, c_bool(bRFOn))
        self.check_error(status)

    def setUseInternalRef(self, bInternal):
        status = fnLMS_SetUseInternalRef(self.device_id, c_bool(bInternal))
        self.check_error(status)

    def getFrequency(self):
        reply = fnLMS_GetFrequency(self.device_id)
        return float(reply*10.)

    def getPowerLevel(self):
        reply = fnLMS_GetPowerLevel(self.device_id)
        return self.maxPower - float(reply*0.25)
#        return float(reply*0.25)

    def getRFOn(self):
        reply = fnLMS_GetRF_On(self.device_id)
        return bool(reply)

    def getUseInternalRef(self):
        reply = fnLMS_GetUseInternalRef(self.device_id)
        return bool(reply)

    def setInternalPulseMod(self, dOntime, dReptime, bOn=False):
        status = fnLMS_SetFastPulsedOutput(self.device_id, c_float(dOntime), c_float(dReptime), c_bool(bOn))
        self.check_error(status)

    def setExternalPulseMod(self, bOn=False):
        status = fnLMS_SetUseExternalPulseMod(self.device_id, c_bool(bOn))
        self.check_error(status)

    def getInternalPulseMod(self):
        reply = fnLMS_GetPulseMode(self.device_id)
        return bool(reply)

    def getPulseOnTime(self):
        reply = fnLMS_GetPulseOnTime(self.device_id)
        return float(reply)

    def getPulseOffTime(self):
        reply = fnLMS_GetPulseOffTime(self.device_id)
        return float(reply)

    def getPulsePeriod(self):
        return self.getPulseOnTime() + self.getPulseOffTime()

    def getExternalPulseMod(self):
        reply = fnLMS_GetUseInternalPulseMod(self.device_id)
        return not bool(reply)

    def check_error(self, status=0):
        """If error occurred, get error message and raise error"""
        # error codes
        BAD_PARAMETER = 0x80010000		
        BAD_HID_IO    = 0x80020000		
        DEVICE_NOT_READY = 0x80030000		
        dError = {BAD_PARAMETER: 'Out of range input - frequency outside min/max etc.',
                  BAD_HID_IO: 'A failure occurred internally during I/O to the device',
                  DEVICE_NOT_READY: "Device isn't open or no handle"}
        if status:
            
            if status in dError:
                sErr = dError[status]
            else:
                sErr = 'Unknown error'
            raise Error(sErr)
        


if __name__ == '__main__':
    # test driver
    SG = LabBrick_Synthesizer(bTestMode=True)
    lDevice = SG.getListOfDevices()
    print (lDevice)
    SG.initDevice(100103)
    SG.setFrequency(61.4E9)
    print ('Frequency', SG.getFrequency())
    SG.setPowerLevel(6)
    print ('Power', SG.getPowerLevel())
    SG.setRFOn(True)
    print (SG.getRFOn())
    SG.setUseInternalRef(False)
    print (SG.getUseInternalRef())
    print ('Get pulse mod:')
    SG.setExternalPulseMod(True)
    SG.setInternalPulseMod(2E-3, 10E-3, True)
    print (SG.getExternalPulseMod())
    print (SG.getInternalPulseMod())
    print (SG.getPulseOnTime())
    print (SG.getPulseOffTime())
    print (SG.getPulsePeriod())
    SG.closeDevice()

