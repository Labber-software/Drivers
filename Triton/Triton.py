#!/usr/bin/env python

import InstrumentDriver
from VISA_Driver import VISA_Driver
import visa
from InstrumentConfig import InstrumentQuantity
import numpy as np
import string
import Tkinter as Tk

__version__ = "0.0.1"

class Error(Exception):
    pass

class Driver(VISA_Driver):
    """ This class implements the Triton 200 driver"""
  
    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # calling the generic VISA open to make sure we have a connection
        VISA_Driver.performOpen(self, options=options)
        # fix issue with termination for read
        visa.vpp43.set_attribute(self.com.vi, visa.VI_ATTR_SUPPRESS_END_EN, visa.VI_FALSE)
        
        #Detect options: (vector) magnet and swicth heater
        detectedOptions = []
        rate = self.askAndLog('READ:SYS:VRM:RFMX').strip().rsplit(':',1)[1][1:-1].translate(None,string.letters+"/").split()
        if float(rate[0]) > 0:
            detectedOptions.append("x magnet")
        if float(rate[1]) > 0:
            detectedOptions.append("y magnet")
        if float(rate[2]) > 0:
            detectedOptions.append("z magnet")
        
        heater = self.askAndLog('READ:SYS:VRM:SWHT').strip().rsplit(':',1)[1][1:-1].split()
        if heater[0] != "NOSW" or heater[1] != "NOSW" or heater[2] != "NOSW":
            detectedOptions.append("switch heater")
            
        self.instrCfg.setInstalledOptions(detectedOptions)
        
        # Make sure that the coordinate system matches the device
        coordFunc = self.instrCfg.getQuantity('CoordSys')
        v = self.performGetValue(coordFunc)
        coordFunc.setValue(v)


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        #on first call clear B-result buffer
        if self.isFirstCall(options):
            self.Bresult = []
        # check type of quantity
        if quant.name in ('T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12', 'T13'):
            # temperatures, get value strings
            sAns = self.askAndLog(quant.get_cmd).strip()
            # convert string to float by taking everything after last colon, ignoring final 'K'
            value = float(sAns.rsplit(':',1)[1][:-1])
        elif quant.name in ('ControlLoop'):
            for i in range(1,14):
                pass
                sAns = self.askAndLog(quant.get_cmd.replace('<c>', str(i))).strip()
                sAns = sAns.rsplit(':',1)[1]
                if sAns != "NOT_FOUND":
                    value = (sAns == "ON")
                    break
        elif quant.name in ('TSet'):
            for i in range(1,14):
                sAns = self.askAndLog(quant.get_cmd.replace('<c>', str(i))).strip()
                sAns = sAns.rsplit(':',1)[1]
                if sAns != "NOT_FOUND":
                    value = float(sAns[:-1])
                    break
        elif quant.name in ('HeaterRange'):
            for i in range(1,14):
                sAns = self.askAndLog(quant.get_cmd.replace('<c>', str(i))).strip()
                sAns = sAns.rsplit(':',1)[1]
                if sAns != "NOT_FOUND":
                    value = quant.getValueFromCmdString(sAns[:-2])
                    break
        elif quant.name in ('PoC'):
            sAns = self.askAndLog(quant.get_cmd).strip()
            value = (sAns.rsplit(':',1)[1] == "ON")
        elif quant.name in ('CoordSys'):
            sAns = self.askAndLog(quant.get_cmd).strip()
            value = quant.getValueFromCmdString(sAns.rsplit(':',1)[1])
        elif quant.name in ('Bx', 'By', 'Bz', 'Br', 'Brho', 'Bphi', 'Btheta'):
            coordFunc = self.instrCfg.getQuantity('CoordSys')
            if not self.Bresult:
                vectValue = self.askAndLog(quant.get_cmd).strip()
                self.Bresult = vectValue.rsplit(':',1)[1][1:-1].translate(None,string.letters).split()
            #Vector results depend on the coordinate system
            value = float('nan')
            if coordFunc.getValue() == 'Cartesian':
                if quant.name == 'Bx':
                    return float(self.Bresult[0])
                elif quant.name == 'By':
                    return float(self.Bresult[1])
                elif quant.name == 'Bz':
                    return float(self.Bresult[2])
            elif coordFunc.getValue() == 'Cylindrical':
                if quant.name == 'Brho':
                    return float(self.Bresult[0])
                elif quant.name == 'Btheta':
                    return float(self.Bresult[1])
                elif quant.name == 'Bz':
                    return float(self.Bresult[2])
            elif coordFunc.getValue() == 'Spherical':
                if quant.name == 'Br':
                    return float(self.Bresult[0])
                elif quant.name == 'Btheta':
                    return float(self.Bresult[1])
                elif quant.name == 'Bphi':
                    return float(self.Bresult[2])
        else:
            # for all other cases, call VISA driver
            cmd = quant.get_cmd
            if (cmd is not None) and (cmd != ''):
                value = self.askAndLog(cmd).strip().rsplit(':',1)[1]
            else:
                value = quant.getValue()
        return value

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the set value operation"""
        #reset the necessity to drive the magnet on first call
        if self.isFirstCall(options):
            self.Bchanged = False
        # check type of quantity
        if quant.name in ('Bx', 'By', 'Bz', 'Br', 'Brho', 'Bphi', 'Btheta'):
            #Remember that B has changed, so we can drive the magnet in the last call
            self.Bchanged = True
            if sweepRate == 0:
                self.setTargetField(quant.name, value, quant.set_cmd)
            else:
                self.setTargetField(quant.name, value, quant.sweep_cmd.replace('<sr>', str(sweepRate*60)))
        elif quant.name in ('ControlLoop'):
            for i in range(1,14):
                sAns = self.askAndLog(quant.get_cmd.replace('<c>', str(i))).strip()
                sAns = sAns.rsplit(':',1)[1]
                if sAns != "NOT_FOUND":
                    vstring = "OFF"
                    if value:
                        vstring = "ON"
                    self.askAndLog(quant.set_cmd.replace('<c>', str(i)).replace('<*>', vstring))
                    break
        elif quant.name in ('TSet'):
            for i in range(1,14):
                sAns = self.askAndLog(quant.get_cmd.replace('<c>', str(i))).strip()
                sAns = sAns.rsplit(':',1)[1]
                if sAns != "NOT_FOUND":
                    self.askAndLog(quant.set_cmd.replace('<c>', str(i)).replace('<*>', quant.getCmdStringFromValue(value)))
                    break
        elif quant.name in ('HeaterRange'):
            for i in range(1,14):
                sAns = self.askAndLog(quant.get_cmd.replace('<c>', str(i))).strip()
                sAns = sAns.rsplit(':',1)[1]
                if sAns != "NOT_FOUND":
                    self.askAndLog(quant.set_cmd.replace('<c>', str(i)).replace('<*>', quant.getCmdStringFromValue(value)))
                    break
        elif quant.name in ('PoC'):
            vstring = "OFF"
            if value:
                vstring = "ON"
            self.askAndLog(quant.set_cmd.replace('<*>', vstring))
        elif quant.name in ('SweepStart', 'SweepStop', 'SweepRate'):
            self.readyToSweep = True
        else:
            cmd = quant.set_cmd
            if (cmd is not None) and (cmd != ''):
                self.askAndLog(cmd.replace('<*>', quant.getCmdStringFromValue(value)))
        
        if self.isFinalCall(options) and self.Bchanged:
            self.askAndLog("SET:SYS:VRM:ACTN:RTOS")
            if sweepRate == 0:
                self.waitForIdle()
        
        return value

    def checkIfSweeping(self, quant, options={}):
        return (self.askAndLog('READ:SYS:VRM:ACTN').strip().rsplit(':',1)[1] != "IDLE")
        
    def waitForIdle(self):
        idle = (self.askAndLog('READ:SYS:VRM:ACTN').strip().rsplit(':',1)[1] == "IDLE")
        while not idle and not self.isStopped():
            self.thread().msleep(100)
            idle = (self.askAndLog('READ:SYS:VRM:ACTN').strip().rsplit(':',1)[1] == "IDLE")
        if self.isStopped():
            self.askAndLog('SET:SYS:VRM:ACTN:HOLD')
            
    def setTargetField(self, axis, value, sCmd):
        #Vector results depend on the coordinate system
        coordFunc = self.instrCfg.getQuantity('CoordSys')
        if self.Bchanged == False:
            self.askAndLog('SET:SYS:VRM:ACTN:HOLD')
            waitForIdle()
            self.performSetValue(coordFunc, coordFunc.getValue())
            self.performGetValue(coordFunc)
        vectValue = self.askAndLog("READ:SYS:VRM:VSET").strip()
        a,b,c = vectValue.rsplit(':',1)[1][1:-1].translate(None,string.letters).split()
        if coordFunc.getValue() == 'Cartesian':
            if axis == 'Bx':
                a = value
            elif axis == 'By':
                b = value
            elif axis == 'Bz':
                c = value
        elif coordFunc.getValue() == 'Cylindrical':
            a = self.instrCfg.getQuantity('Brho').getValue()
            b = self.instrCfg.getQuantity('Btheta').getValue()
            c = self.instrCfg.getQuantity('Bz').getValue()
            if axis == 'Brho':
                a = value
            elif axis == 'Btheta':
                b = value
            elif axis == 'Bz':
                c = value
        elif coordFunc.getValue() == 'Spherical':
            a = self.instrCfg.getQuantity('Br').getValue()
            b = self.instrCfg.getQuantity('Btheta').getValue()
            c = self.instrCfg.getQuantity('Bphi').getValue()
            if axis == 'Br':
                a = value
            elif axis == 'Btheta':
                b = value
            elif axis == 'Bphi':
                c = value
        sMsg = sCmd.replace('<*>', str(a) + " " + str(b) + " " + str(c))
        self.askAndLog(sMsg)

if __name__ == '__main__':
    pass
