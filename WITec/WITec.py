import InstrumentDriver
import platform
import comtypes as com
import os, sys, inspect, re, math

#Some stuff to import win32gui and win32con from a relative path independent from system wide installations
cmd_folder = os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0]))
if cmd_folder not in sys.path:
    sys.path.insert(0, cmd_folder)

import win32gui
import win32con
import WIPfile

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class wraps the ziPython API"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        com.CoInitialize()
        try:
            self.bucsLib = com.client.GetModule("BasicUniversalCOMServer.tlb")
        except:
            raise InstrumentDriver.CommunicationError("Could not connect to WITec Control. Make sure that it is running and that remote access has been granted.")
        self.rememberWITecWindows()
        return

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        com.CoUninitialize()
        return


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        
        #Some quants are driver settings, that do not require any communication
        cmd = quant.get_cmd
        if cmd is None or cmd == "":
            if quant.name in "CloseWindowsOnTrigger":
                self.rememberWITecWindows()
            return value
    
        #We reconnect on each call as the connection might have been closed for manual control
        self.connectToCOM()
        manip = self.getManipulator(quant)
        #While LabControl does not distinguish double and int, WITec does. So if writing fails, we have to convert to int
        try:
            manip.setValue(value)
        except:
            if quant.datatype == quant.DOUBLE:
                manip.setValue(int(value))
        return manip.getValue()


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        
        #Some quants are driver settings, that do not require any communication
        cmd = quant.get_cmd
        if cmd is None or cmd == "":
            return quant.getValue()
            
        #We reconnect on each call as the connection might have been closed for manual control
        self.connectToCOM()
        if quant.name[:7] == "Trigger":
            if self.instrCfg.getQuantity('CloseWindowsOnTrigger').getValue():
                self.closeWITecWindows()
            lastIndex = self.triggerMeasurement(quant)
            if quant.name[:14] == "TriggerAndRead":
                indexManip = self.getNumericManipulator("UserParameters|AutoSaveProject|FileNumber")
                indexManip.setValue(1)
                dirManip = self.getStringManipulator("UserParameters|AutoSaveProject|StartDirectory")
                dirManip.setValue("C:\\")
                subDirManip = self.getStringManipulator("UserParameters|AutoSaveProject|ExtraDirectory")
                subDirManip.setValue("Labber-Temp")
                subDirManip = self.getStringManipulator("UserParameters|AutoSaveProject|FileName")
                subDirManip.setValue("temp")
                nextFileManip = self.getStringManipulator("UserParameters|AutoSaveProject|NextFileName")
                filename = nextFileManip.getValue()
                triggerManip = self.getTriggerManipulator("UserParameters|AutoSaveProject|StoreProject")
                triggerManip.OperateTrigger()
                data = WIPfile.loadWIP(filename)
                return quant.getTraceDict(data[0], data[1], data[2])
            else:
                return lastIndex
        else:
            manip = self.getManipulator(quant)
            return manip.getValue()

    def connectToCOM(self):
        try:
            del self.IBUCSCore
        except:
            pass
        self.IBUCSCore = com.client.CreateObject(self.bucsLib.CBUCSCore, None, platform.node(), self.bucsLib.IBUCSCore)
        IBUCSAccess = self.IBUCSCore.QueryInterface(self.bucsLib.IBUCSAccess)
        if not IBUCSAccess.RequestWriteAccess(True):
            raise InstrumentDriver.CommunicationError("Could not get write access for WITec Control. Make sure that remote write access has been granted.")
        return

    def getGenericManipulator(self, address):
        return self.IBUCSCore.GetSubSystemDefaultInterface(address)
        
    def getStringManipulator(self, address):
        return self.getGenericManipulator(address).QueryInterface(self.bucsLib.IBUCSString)
    
    def getNumericManipulator(self, address):
        gManip = self.getGenericManipulator(address)
        try:
            return gManip.QueryInterface(self.bucsLib.IBUCSInt)
        except:
            try:
                return gManip.QueryInterface(self.bucsLib.IBUCSFloat)
            except:
                return None
    
    def getBooleanManipulator(self, address):
        return self.getGenericManipulator(address).QueryInterface(self.bucsLib.IBUCSBool)
    
    def getTriggerManipulator(self, address):
        return self.getGenericManipulator(address).QueryInterface(self.bucsLib.IBUCSTrigger)
    
    def getStatusManipulator(self, address):
        return self.getGenericManipulator(address).QueryInterface(self.bucsLib.IBUCSStatusContainer)
    
    def getManipulator(self, quant):
        if quant.datatype == quant.STRING:
            return self.getStringManipulator(quant.get_cmd)
        elif quant.datatype == quant.DOUBLE:
            return self.getNumericManipulator(quant.get_cmd)
        elif quant.datatype == quant.BOOLEAN:
            return self.getBooleanManipulator(quant.get_cmd)
        return None

    def triggerMeasurement(self, quant):
        #Handle the file naming within the project
        nameManip = self.getStringManipulator(quant.get_cmd.rsplit('|',1)[0] + "|Naming|DataName")
        indexManip = self.getNumericManipulator(quant.get_cmd.rsplit('|',1)[0] + "|Naming|DataNumber")
        
        #For some quantities we want to do automatic renaming:
        name = None
        if quant.name == "TriggerImageScan":
            name = self.instrCfg.getQuantity('ImageName').getValue()
        elif quant.name == "TriggerLineScan":
            name = self.instrCfg.getQuantity('LineName').getValue()
        elif quant.name == "TriggerSingleSpectrum":
            name = self.instrCfg.getQuantity('SpectrumName').getValue()
        if name is not None:
            v0 = self.instrCfg.getQuantity('AutoNameValue0').getValue()
            v1 = self.instrCfg.getQuantity('AutoNameValue1').getValue()
            v2 = self.instrCfg.getQuantity('AutoNameValue2').getValue()
            v3 = self.instrCfg.getQuantity('AutoNameValue3').getValue()
            nameManip.setValue(name.format(v0, v1, v2, v3))
        
        #ok, let's go
        triggerManip = self.getTriggerManipulator(quant.get_cmd)
        activeManip = self.getStatusManipulator("Status|Software|Sequencers|IsASequencerActive")
        triggerManip.OperateTrigger()
        activeManip.update()
        statInt, statBool = activeManip.GetSingleValueAsInt()
        while statInt > 0 and statBool == True:
            self.wait(0.5)
            activeManip.update()
            statInt, statBool = activeManip.GetSingleValueAsInt()
        return indexManip.getValue()
        
    def rememberWITecWindows(self):
        self.WITecWindows = []
        def cb(hwnd, hwnds):
            if win32gui.IsWindowVisible(hwnd):
                parent = win32gui.GetWindowText(win32gui.GetWindow(hwnd, win32con.GW_OWNER))
                self.log("Parent " + parent )
                if "Control FOUR" in parent:
                    title = win32gui.GetWindowText(hwnd)
                    self.log("Remembering " + title )
                    self.WITecWindows.append(title)
            return True
        win32gui.EnumWindows(cb, 0)
        
    def closeWITecWindows(self):
        self.log("close Windows")
        def cb(hwnd, hwnds):
            if win32gui.IsWindowVisible(hwnd):
                parent = win32gui.GetWindowText(win32gui.GetWindow(hwnd, win32con.GW_OWNER))
                if "Control FOUR" in parent:
                    title = win32gui.GetWindowText(hwnd)
                    if (not title in self.WITecWindows) and (not "WITec Control" in title):
                        self.log("Closing " + title )
                        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    else:
                        self.log("Ignoring " + title )
            return True
        win32gui.EnumWindows(cb, 0)
