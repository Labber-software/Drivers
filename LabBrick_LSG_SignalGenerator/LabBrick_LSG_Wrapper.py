import os, ctypes
from ctypes import c_int, c_uint, c_bool, POINTER, byref

class Error(Exception):
    pass

# open dll
sPath = os.path.dirname(os.path.abspath(__file__))
_lib = ctypes.CDLL(os.path.join(sPath, 'DLL', 'vnx_fsynsth'))
#_lib = ctypes.WinDLL('vnx_fsynsth')

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


# VNX_FSYNSTH_API int fnLSG_InitDevice(DEVID deviceID)
# VNX_FSYNSTH_API int fnLSG_CloseDevice(DEVID deviceID)
fnLSG_InitDevice = getDllObject('fnLSG_InitDevice')
fnLSG_CloseDevice = getDllObject('fnLSG_CloseDevice')

# VNX_FSYNSTH_API void fnLSG_SetTestMode(bool testmode)
# VNX_FSYNSTH_API int fnLSG_GetNumDevices()
# VNX_FSYNSTH_API int fnLSG_GetDevInfo(DEVID *ActiveDevices)
# VNX_FSYNSTH_API int fnLSG_GetModelName(DEVID deviceID, char *ModelName)
# VNX_FSYNSTH_API int fnLSG_GetSerialNumber(DEVID deviceID)
fnLSG_SetTestMode = getDllObject('fnLSG_SetTestMode', [c_bool], None)
fnLSG_GetNumDevices = getDllObject('fnLSG_GetNumDevices', [], restype=c_int)
fnLSG_GetDevInfo = getDllObject('fnLSG_GetDevInfo', [POINTER(ACTIVEDEVICES)], restype=c_int)
fnLSG_GetModelName = getDllObject('fnLSG_GetModelName', [DEVID, STRING], restype=c_int)
fnLSG_GetSerialNumber = getDllObject('fnLSG_GetSerialNumber', restype=c_int)

# VNX_FSYNSTH_API LVSTATUS fnLSG_SetFrequency(DEVID deviceID, int frequency);
# VNX_FSYNSTH_API LVSTATUS fnLSG_SetPowerLevel(DEVID deviceID, int powerlevel);
# VNX_FSYNSTH_API LVSTATUS fnLSG_SetRFOn(DEVID deviceID, bool on);
# VNX_FSYNSTH_API LVSTATUS fnLSG_SetUseInternalRef(DEVID deviceID, bool internal);
fnLSG_SetFrequency = getDllObject('fnLSG_SetFrequency', [DEVID, c_int])
fnLSG_SetPowerLevel = getDllObject('fnLSG_SetPowerLevel', [DEVID, c_int])
fnLSG_SetRFOn = getDllObject('fnLSG_SetRFOn', [DEVID, c_bool])
fnLSG_SetUseInternalRef = getDllObject('fnLSG_SetUseInternalRef', [DEVID, c_bool])

# VNX_FSYNSTH_API int fnLSG_GetFrequency(DEVID deviceID);
# VNX_FSYNSTH_API int fnLSG_GetPowerLevel(DEVID deviceID);
# VNX_FSYNSTH_API int fnLSG_GetRF_On(DEVID deviceID);
# VNX_FSYNSTH_API int fnLSG_GetUseInternalRef(DEVID deviceID);
fnLSG_GetFrequency = getDllObject('fnLSG_GetFrequency', restype=c_int)
fnLSG_GetPowerLevel = getDllObject('fnLSG_GetPowerLevel', restype=c_int)
fnLSG_GetRF_On = getDllObject('fnLSG_GetRF_On', restype=c_int)
fnLSG_GetUseInternalRef = getDllObject('fnLSG_GetUseInternalRef', restype=c_int)

#VNX_FSYNSTH_API int fnLSG_GetMaxPwr(DEVID deviceID);
#VNX_FSYNSTH_API int fnLSG_GetMinPwr(DEVID deviceID);
#VNX_FSYNSTH_API int fnLSG_GetMaxFreq(DEVID deviceID);
#VNX_FSYNSTH_API int fnLSG_GetMinFreq(DEVID deviceID);
fnLMS_GetMaxPwr = getDllObject('fnLSG_GetMaxPwr', restype=c_int)
fnLMS_GetMinPwr = getDllObject('fnLSG_GetMinPwr', restype=c_int)
fnLMS_GetMaxFreq = getDllObject('fnLSG_GetMaxFreq', restype=c_int)
fnLMS_GetMinFreq = getDllObject('fnLSG_GetMinFreq', restype=c_int)


class LabBrick_SignalGenerator():
    """Represent a signal generator, redefines the dll function in python"""

    def __init__(self, bTestMode=False):
        """The init case defines a session ID, used to identify the instrument"""
        fnLSG_SetTestMode(c_bool(bTestMode))
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
        status = fnLSG_InitDevice(self.device_id)
        # get limits
        self.maxPower = float(fnLMS_GetMaxPwr(self.device_id))*0.25
        self.minPower = float(fnLMS_GetMinPwr(self.device_id))*0.25
        self.maxFreq = float(fnLMS_GetMaxFreq(self.device_id))*100E3
        self.minFreq = float(fnLMS_GetMinFreq(self.device_id))*100E3
        self.check_error(status)

    def closeDevice(self):
        if self.device_id is not None:
            fnLSG_CloseDevice(self.device_id)

    def getListOfDevices(self):
        lDevice = []
        nDev = int(fnLSG_GetNumDevices())
        if nDev==0:
            return []
        # init list of devices
        devices = ACTIVEDEVICES()
        nDev = fnLSG_GetDevInfo(byref(devices))
        for n1 in range(nDev):
            nameBuffer = STRING(b' '*32)
            fnLSG_GetModelName(devices[n1], nameBuffer)
            serial = int(fnLSG_GetSerialNumber(devices[n1]))
            d = dict()
            d['name'] = str(nameBuffer.value.decode())
            d['serial'] = serial
            d['device_id'] = int(devices[n1])
            lDevice.append(d)
        return lDevice

    def setFrequency(self, dFreq):
        # make sure frequency is in range
        dFreq = max(self.minFreq, min(self.maxFreq, dFreq))
        iFreq = int(dFreq/100E3)
        status = fnLSG_SetFrequency(self.device_id, c_int(iFreq))
        self.check_error(status)
        return dFreq

    def setPowerLevel(self, dPower):
        iPower = int(dPower/0.25)
        status = fnLSG_SetPowerLevel(self.device_id, c_int(iPower))
        self.check_error(status)

    def setRFOn(self, bRFOn):
        status = fnLSG_SetRFOn(self.device_id, c_bool(bRFOn))
        self.check_error(status)

    def setUseInternalRef(self, bInternal):
        status = fnLSG_SetUseInternalRef(self.device_id, c_bool(bInternal))
        self.check_error(status)

    def getFrequency(self):
        reply = fnLSG_GetFrequency(self.device_id)
        return float(reply*100E3)

    def getPowerLevel(self):
        reply = fnLSG_GetPowerLevel(self.device_id)
        return self.maxPower - float(reply*0.25)
#        return float(reply*0.25)

    def getRFOn(self):
        reply = fnLSG_GetRF_On(self.device_id)
        return bool(reply)

    def getUseInternalRef(self):
        reply = fnLSG_GetUseInternalRef(self.device_id)
        return bool(reply)


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
    SG = LabBrick_SignalGenerator(bTestMode=True)
    lDevice = SG.getListOfDevices()
    print (lDevice)
    SG.initDevice(456602)
    SG.setFrequency(0.4E9)
    print ('Frequency', SG.getFrequency()/1E9)
    SG.setPowerLevel(-29)
    print (SG.getPowerLevel())
    SG.setRFOn(True)
    print (SG.getRFOn())
    SG.setUseInternalRef(False)
    print (SG.getUseInternalRef())
    SG.closeDevice()

