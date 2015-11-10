# -*- coding: utf-8 -*-
"""
Created on Fri Jan 16 15:57:31 2015

@author: je25649
"""

import win32com.client as w32


class Error(Exception):
    pass
        
class TimeoutError(Error):
    pass

class MiniCircuitsSwitch():
    
    def __init__(self):
        w32.pythoncom.CoInitialize()
        self.dll = w32.Dispatch('MCL_RF_Switch_Controller.USB_RF_Switch')
        
    def Connect(self,SN = ''):       
        ret = self.dll.Connect(SN)
        if ret == 0:
            raise Error('Failed to connect')
            
    def ConnectByAddress(self,addr):
        ret = self.dll.ConnectByAddress(addr)
        if ret == 0:
            raise Error('Failed to connect')
            
    def Disconnect(self):
        self.dll.Disconnect()
        
    def Get_Available_SN_List(self):        
        ret = self.dll.Get_Available_SN_List()
        if ret[0] == 0:
            return None 
        SNlist = []
        for x in ret[1:]:
            SNlist.append(str(x))
        return SNlist
        
    def Get_Available_Address_List(self):
        ret = self.dll.Get_Available_SN_List()
        if ret[0] == 0:
            return None 
        Addrlist = []
        for x in ret[1:]:
            Addrlist.append(x)
        return Addrlist
        
    def Read_ModelName(self):
        ret = self.dll.Read_ModelName()
        if ret[0] == 0:
            return None
        return str(ret[1])
        
    def Read_SN(self):
        ret = self.dll.Read_SN()
        if ret[0] == 0:
            return None
        return str(ret[1]) #return a string of the SN because you need a string to connect
        
    def Set_Address(self,addr):
        self.dll.SetAddress(addr)
	  
    '''Note the function below requires that external jumpers be connected to the switch unit
    val goes from 0 to 4 and makes switch unit act like DP5T with first pole throws A1/B1/C1/D1/D2 and second pole throws E1/F1/G1/H1/H2'''    
    def Set_DP5T(self,val):
        if val < 0 or val > 4:
            raise Error('Index out of bounds')
        if int(val) == 5:
            writeval == 255
        else:
            writeval = 255^((1<<int(val))+(1<<(int(val)+4)))
        self.Set_SwitchesPort(writeval)

    '''Note the function below assumes the switch is configured with external jumpers to be a DP5T switch'''        
    def Get_DP5T(self):
        ret = self.GetSwitchesStatus()
        for x in range(4):
            throw1 = 1&(ret>>x) #bit x of ABCD bank
            throw2 = 1&(ret>>(x+4)) #bit x of EFGH bank
            if throw1 != throw2: 
                '''if bit x of ABCD bank doesn't match bit x of EFGH bank and we haven't already found a match switch isn't in valid DP5T state'''
                return -1
            elif throw1 == 0: 
                '''if bit x is zero for ABCD and EFGH banks we have a DP5T relay connected to throw x'''
                return x
        return 4 #connected to throw 4
        
    '''Note the function below requires that external jumpers be connected to the switch unit
    val goes from 0 to 8 and makes switch unit act like SP9T '''     
    def Set_SP9T(self,val): 
        if val < 0 or val > 8:
            raise Error('Index out of bounds')
        if int(val)==8:
            writeval = 255
        else:
            writeval = 255^(1<<int(val))
        self.Set_SwitchesPort(writeval)

    '''Note the function below assumes the switch is configured with external jumpers to be a SP9T switch'''        
    def Get_SP9T(self):
        ret = self.GetSwitchesStatus()      
        for x in range(8):
            if ((ret>>x) & 1) == 0: #the first zero bit is the throw index
                return x
        return 8 # connected to throw 8
        
    def Get_Address(self):
        return self.dll.GetAddress()
        
    def GetSwitchesStatus(self):
        ret = self.dll.GetSwitchesStatus()
        if ret[0] == 0:
            raise Error('Failed to get switch status')
        return ret[1] #returns byte with bits encoding switch status, 'A'= LSB, bit=1 --> COM->2
        
    def GetDeviceTemperature(self,channel):
        ret = self.dll.GetDeviceTemperature(channel) #the USB-8SPDT-A18 has 2 thermometers -> channel = 1 or 2
        return ret[0] #device temperature in C
        
    def GetUSBConnectionStatus(self):
        return self.dll.GetUSBConnectionStatus()
        
    def Get_FAN_Indicator(self):
        return self.dll.Get_FAN_Indicator()
        
    def Get_24V_Indicator(self):
        return self.dll.Get_24V_Indicator()
        
    def GetAllSwitchCounters(self):
        ret = self.dll.GetAllSwitchCounters((0,0,0,0,0,0,0,0))        
        if ret[0] == 0:
            raise Error('Failed to get switch counters')
        return ret[1] #returns a tuple of all 8 switch counters
        
    def GetFirmware(self):
        return self.dll.GetFirmware()
        
    def GetHeatAlarm(self):
        return self.dll.GetHeatAlarm()
        
    def Set_Switch(self,addr,val):
        ret = self.dll.Set_Switch(addr,val) #ret[0] = fail, ret[1] = addr, ret[2] = val
        if ret[0] == 0:
            raise Error('Failed to set switch')
    
    def Set_SwitchesPort(self,val):
        ret = self.dll.Set_SwitchesPort(val)
        if ret[0] == 0:
            raise Error('Failed to set switches')
    

if __name__ == '__main__':
    pass

