# -*- coding: utf-8 -*-
"""
Created on Thu Jan 15 17:43:56 2015

@author: je25649
"""

from ctypes import CDLL,c_char,c_uint
import os

class Error(Exception):
    pass
        
class TimeoutError(Error):
    pass


DEVID = c_uint
LVSTATUS = c_uint
STATUS_OK = 0
BAD_PARAMETER = 0x80010000		#out of range input -- frequency outside min/max etc.
BAD_HID_IO =   0x80020000
DEVICE_NOT_READY = 0x80030000		# device isn't open, no handle, etc.
FEATURE_NOT_SUPPORTED = 0x80040000
MAXDEVICES = 64
MAX_MODELNAME = 32
PROFILE_MAX = 100

'''These are the bit masks used in getFeatures()'''
DEFAULT_FEATURES	= 0x00000000	
HAS_BIDIR_RAMPS	= 0x00000001
HAS_PROFILES	= 0x00000002

'''This explains the return value of getDeviceStatus()'''
INVALID_DEVID =		0x80000000		# MSB is set if the device ID is invalid
DEV_CONNECTED =		0x00000001		# LSB is set if a device is connected
DEV_OPENED	=		0x00000002		# set if the device is opened
SWP_ACTIVE	=		0x00000004		# set if the device is sweeping
SWP_UP	=		0x00000008		# set if the device is sweeping up in frequency
SWP_REPEAT	=		0x00000010		# set if the device is in continuous sweep mode
SWP_BIDIRECTIONAL =	0x00000020		# set if the device is in bidirectional sweep mode
PROFILE_ACTIVE =		0x00000040		# set if a profile is playing


class VaunixAttenuator():

    def __init__(self):
        """The init case defines a device ID, used to identify the instrument"""
        # create a device id
        self.DeviceID = DEVID()
        base_path = os.path.dirname(os.path.abspath(__file__))
        dll_path = os.path.join(base_path, 'VNX_atten.dll')
        self.VxDLL = CDLL(dll_path)


    def callfuncstatus(self, sFunc, *args, **kargs):
        """General function caller which checks for errors in DLL return value"""
        # get function from DLL
        func = getattr(self.VxDLL, sFunc)
        func.restype = LVSTATUS
        # call function, raise error if needed
        status = func(*args)
        if 'bIgnoreError' in kargs:
            bIgnoreError = kargs['bIgnoreError']
        else:
            bIgnoreError = False
        if status >= INVALID_DEVID and not bIgnoreError:
            if status == INVALID_DEVID:
                raise Error('Invalid Device ID')
            elif status == BAD_PARAMETER:
                raise Error('Parameter Out of Range')
            elif status == BAD_HID_IO:
                raise Error('Communication Failure')
            elif status == DEVICE_NOT_READY:
                raise Error('Device Not Ready')
            elif status == FEATURE_NOT_SUPPORTED:
                raise Error('Feature Not Supported')           
            
    def callfuncret(self, sFunc, *args, **kargs):
        """General function caller which returns the value from the DLL function"""
        # get function from DLL
        func = getattr(self.VxDLL, sFunc)    
        # call function and return value
        return func(*args)
        
    def setTestMode(self,TestMode):
        self.VxDLL['fnLDA_SetTestMode'](TestMode)
        
    def getNumDevices(self):
        return self.callfuncret('fnLDA_GetNumDevices')
        
    def getDevInfo(self):
        deviceList = (DEVID * MAXDEVICES)()
        self.callfuncret('fnLDA_GetDevInfo', deviceList)
        return deviceList
        
    def getModelName(self,devID):
        if devID==None:
            devID=self.DeviceID        
        modelName = (c_char * MAX_MODELNAME)()
        self.callfuncret('fnLDA_GetModelName',devID,modelName)
        return modelName.value
        
    def getSerialNumber(self,devID):
        if devID==None:
            devID=self.DeviceID
        return self.callfuncret('fnLDA_GetSerialNumber',devID)
        
    def getDeviceStatus(self,devID):
        if devID==None:
            devID=self.DeviceID
        return self.callfuncret('fnLDA_GetDeviceStatus',devID)
        
    def initDevice(self,devID):
        self.DeviceID = devID        
        self.callfuncstatus('fnLDA_InitDevice',self.DeviceID)
        self.MaxAtten = self.__getMaxAttenuation(self.DeviceID)
        self.MinAtten = self.__getMinAttenuation(self.DeviceID)
        self.MinAttenStep = self.__getMinAttenStep(self.DeviceID)
        self.Features = self.getFeatures(self.DeviceID)
        
    def closeDevice(self,devID):
        if devID==None:
            devID=self.DeviceID
        return self.callfuncret('fnLDA_CloseDevice',devID)
        
    def setAttenuation(self,devID,atten): #atten in dB
        if devID==None:
            devID=self.DeviceID
        attenint = int(self.MinAttenStep*round(atten*4/self.MinAttenStep)) # function wants atten in units of 0.25 dB w/ MinAttenStep resolution       
        if attenint < self.MinAtten:
            attenint = self.MinAtten
        elif attenint > self.MaxAtten:
            attenint = self.MaxAtten        
        self.callfuncstatus('fnLDA_SetAttenuation',devID,attenint) 
        
    def setRampStart(self,devID,startatten): #atten in dB
        if devID==None:
            devID=self.DeviceID
        startattenint = int(self.MinAttenStep*round(startatten*4/self.MinAttenStep))
        if startattenint < self.MinAtten:
            startattenint = self.MinAtten
        elif startattenint > self.MaxAtten:
            startattenint = self.MaxAtten
        self.callfuncstatus('fnLDA_SetRampStart',devID,startattenint)
        
    def setRampEnd(self,devID,endatten): #atten in dB
        if devID==None:
            devID=self.DeviceID
        endattenint = int(self.MinAttenStep*round(endatten*4/self.MinAttenStep))
        if endattenint < self.MinAtten:
            endattenint = self.MinAtten
        elif endattenint > self.MaxAtten:
            endattenint = self.MaxAtten
        self.callfuncstatus('fnLDA_SetRampEnd',devID,endattenint)
        
    def setAttenuationStep(self,devID,step): #step in dB
        if devID==None:
            devID=self.DeviceID
        stepint = int(self.MinAttenStep*round(step*4/self.MinAttenStep))
        self.callfuncstatus('fnLDA_SetAttenuationStep',devID,stepint)
        
    def setAttenuationStepTwo(self,devID,step2): #second phase of ramp step in dB
        if devID==None:
            devID=self.DeviceID
        if not self.Features & HAS_BIDIR_RAMPS:
            raise Error('Feature Not Supported')
        step2int = int(self.MinAttenStep*round(step2*4/self.MinAttenStep))
        self.callfuncstatus('fnLDA_SetAttenuationStep',devID,step2int)
        
    def setDwellTime(self,devID,dwelltime): #time in ms
        if devID==None:
            devID=self.DeviceID
        if int(dwelltime) < 1:
            dwelltime = 1
        self.callfuncstatus('fnLDA_SetDwellTime',devID,int(dwelltime))
        
    def setDwellTimeTwo(self,devID,dwelltime2): #second phase of ramp dwell time in ms
        if not self.Features & HAS_BIDIR_RAMPS:
            raise Error('Feature Not Supported')
        if devID==None:
            devID=self.DeviceID
        if int(dwelltime2) < 1:
            dwelltime2 = 1
        self.callfuncstatus('fnLDA_SetDwellTimeTwo',devID,int(dwelltime2))
        
    def setHoldTime(self,devID,holdtime): #hold time between first and second phases of bidirectional sweep in ms
        if devID==None:
            devID=self.DeviceID        
        if not self.Features & HAS_BIDIR_RAMPS:
            raise Error('Feature Not Supported')        
        self.callfuncstatus('fnLDA_SetHoldTime',devID,int(holdtime))
        
    def setIdleTime(self,devID,idletime): #idle time between repeated sweeps in ms
        if devID==None:
            devID=self.DeviceID
        self.callfuncstatus('fnLDA_SetIdleTime',devID,int(idletime))
        
    def setRFOn(self,devID,on): #toggles between maximum atten (true) and set atten (false)
        if devID==None:
            devID=self.DeviceID
        self.callfuncstatus('fnLDA_SetRFOn',devID,on)
        
    def setRampDirection(self,devID,up):
        if devID==None:
            devID=self.DeviceID
        self.callfuncstatus('fnLDA_SetRampDirection',devID,up)
        
    def setRampMode(self,devID,mode): #true = repeated, false = once
        if devID==None:
            devID=self.DeviceID
        self.callfuncstatus('fnLDA_SetRampMode',devID,mode)
        
    def setRampBidirectional(self,devID,bidir): #true = triangle, false = sawtooth
        if not self.Features & HAS_BIDIR_RAMPS:
            raise Error('Feature Not Supported')   
        if devID==None:
            devID=self.DeviceID
        self.callfuncstatus('fnLDA_SetRampBidirectional',devID,bidir)
        
    def startRamp(self,devID,go):
        if devID==None:
            devID=self.DeviceID
        self.callfuncstatus('fnLDA_StartRamp',devID,go)
        
    def setProfileElement(self,devID,index,atten): #can build custom atten sweep profile one element at a time
        if not self.Features & HAS_PROFILES:
            raise Error('Feature Not Supported') 
        if devID==None:
            devID=self.DeviceID
        self.callfuncstatus('fnLDA_SetProfileElement',devID,index,atten)
        
    def setProfileCount(self,devID,profilecount):
        if not self.Features & HAS_PROFILES:
            raise Error('Feature Not Supported')  
        if devID==None:
            devID=self.DeviceID
        if profilecount < 1:
            profilecount = 1
        if profilecount > PROFILE_MAX:
            profilecount = PROFILE_MAX
        self.callfuncstatus('fnLDA_SetProfileCount',devID,profilecount)
        
    def setProfileIdleTime(self,devID,idletime):
        if not self.Features & HAS_PROFILES:
            raise Error('Feature Not Supported') 
        if devID==None:
            devID=self.DeviceID
        self.callfuncstatus('fnLDA_SetProfileIdleTime',devID,idletime)
        
    def setProfileDwellTime(self,devID,dwelltime):
        if not self.Features & HAS_PROFILES:
            raise Error('Feature Not Supported')   
        if devID==None:
            devID=self.DeviceID
        if dwelltime < 1:
            dwelltime = 1
        self.callfuncstatus('fnLDA_SetProfileDwellTime',devID,dwelltime)
        
    def getProfileElement(self,devID,index):
        if not self.Features & HAS_PROFILES:
            raise Error('Feature Not Supported')   
        if devID==None:
            devID=self.DeviceID
        return 0.25*self.callfuncret('fnLDA_GetProfileElement',devID,index)
        
    def getProfileCount(self,devID):
        if not self.Features & HAS_PROFILES:
            raise Error('Feature Not Supported')
        if devID==None:
            devID=self.DeviceID
        return self.callfuncret('fnLDA_GetProfileCount',devID)
        
    def getProfileIdleTime(self,devID):
        if not self.Features & HAS_PROFILES:
            raise Error('Feature Not Supported') 
        if devID==None:
            devID=self.DeviceID
        return self.callfuncret('fnLDA_GetProfileIdleTime',devID)
        
    def getProfileDwellTime(self,devID):
        if not self.Features & HAS_PROFILES:
            raise Error('Feature Not Supported')  
        if devID==None:
            devID=self.DeviceID
        return self.callfuncret('fnLDA_GetProfileDwellTime',devID)
        
    def startProfile(self,devID,mode): #0 = stop, 1 = once, 2 = repeat
        if devID==None:
            devID=self.DeviceID
        self.callfuncstatus('fnLDA_StartProfile',devID,mode)
        
    def getProfileIndex(self,devID): #current index in profile sweep
        return self.callfuncret('fnLDA_GetProfileIndex',devID)
        
    def saveSettings(self,devID):
        if devID==None:
            devID=self.DeviceID
        self.callfuncstatus('fnLDA_SaveSettings',devID)
        
    def getAttenuation(self,devID):
        if devID==None:
            devID=self.DeviceID
        return 0.25*self.callfuncret('fnLDA_GetAttenuation',devID) #returns atten in dB
        
    def getAttenuationStep(self,devID):
        if devID==None:
            devID=self.DeviceID
        return 0.25*self.callfuncret('fnLDA_GetAttenuationStep',devID) #returns atten step in dB
        
    def getAttenuationStepTwo(self,devID):
        if devID==None:
            devID=self.DeviceID
        return 0.25*self.callfuncret('fnLDA_GetAttenuationStepTwo',devID) #returns atten step 2 in dB
        
    def getRampStart(self,devID):
        if devID==None:
            devID=self.DeviceID
        return 0.25*self.callfuncret('fnLDA_GetRampStart',devID) #returns atten in dB
        
    def getRampEnd(self,devID):
        if devID==None:
            devID=self.DeviceID
        return 0.25*self.callfuncret('fnLDA_GetRampEnd',devID) #returns atten in dB
        
    def getDwellTime(self,devID):
        if devID==None:
            devID=self.DeviceID
        return self.callfuncret('fnLDA_GetDwellTime',devID) #time in ms
        
    def getDwellTimeTwo(self,devID):
        if devID==None:
            devID=self.DeviceID
        return self.callfuncret('fnLDA_GetDwellTimeTwo',devID) #time in ms
        
    def getIdleTime(self,devID):
        if devID==None:
            devID=self.DeviceID
        return self.callfuncret('fnLDA_GetIdleTime',devID) #time in ms
        
    def getRFOn(self,devID):
        if devID==None:
            devID=self.DeviceID
        return self.callfuncret('fnLDA_GetRF_On',devID)
        
    def __getMaxAttenuation(self,devID):
        if devID==None:
            devID=self.DeviceID
        return self.callfuncret('fnLDA_GetMaxAttenuation',devID) #encoded atten
        
    def __getMinAttenuation(self,devID):
        if devID==None:
            devID=self.DeviceID
        return self.callfuncret('fnLDA_GetMinAttenuation',devID) #encoded atten       
        
    def __getMinAttenStep(self,devID):
        if devID==None:
            devID=self.DeviceID
        return self.callfuncret('fnLDA_GetMinAttenStep',devID) #encoded min atten step
        
    def getMaxAttenuation(self,devID):
        return 0.25*self.__getMaxAttenuation(devID) #atten in dB
        
    def getMinAttenuation(self,devID):
        return 0.25*self.__getMinAttenuation(devID) #atten in dB
        
    def getMinAttenStep(self,devID):
        return 0.25*self.__getMinAttenStep(devID) #atten step in dB
        
    def getFeatures(self,devID):
        if devID==None:
            devID=self.DeviceID
        return self.callfuncret('fnLDA_GetFeatures',devID)
        
    def getDLLVersion(self):
        return self.callfuncret('fnLDA_GetDLLVersion')
        

if __name__ == '__main__':
    pass
