#!/usr/bin/env python

import InstrumentDriver
from VISA_Driver import VISA_Driver
import visa
from InstrumentConfig import InstrumentQuantity
import numpy as np
import string
import Tkinter

__version__ = "0.0.1"

class Error(Exception):
    pass

class Driver(VISA_Driver):
    """ This class implements the Oxford Mercury iPS driver"""
  
    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # calling the generic VISA open to make sure we have a connection
        VISA_Driver.performOpen(self, options=options)
        self.detectedOptions = self.getOptions()

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        if quant.name in ('Bx', 'By', 'Bz'):
            value = float(self.askAndLog(quant.get_cmd).strip().rsplit(':',1)[1][:-1])
        elif quant.name in ('BxRate', 'ByRate', 'BzRate'):
            value = float(self.askAndLog(quant.get_cmd).strip().rsplit(':',1)[1][:-3])
        elif quant.name in ('BxSwitchHeater', 'BySwitchHeater', 'BzSwitchHeater'):
            value = (self.askAndLog(quant.get_cmd).strip().rsplit(':',1)[1] == "ON")
        else:
            value = quant.getValue()
        return value

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the set value operation"""
        if quant.name in ('Bx', 'By', 'Bz'):
            resetSwhtr = False
            if quant.name + " switch heater" in self.detectedOptions:
                swhtrFunc = self.instrCfg.getQuantity(quant.name + "SwitchHeater")
                swhtr = self.performGetValue(swhtrFunc)
                if not swhtr:
                    self.performSetValue(swhtrFunc, True)
                    resetSwhtr = True
            dev = quant.set_cmd.split(":", 4)[2]
            self.askAndLog(quant.set_cmd + ":" + str(value))
            self.askAndLog('SET:DEV:' + dev + ':PSU:ACTN:RTOS')
            self.waitForIdle(dev)
            if resetSwhtr:
                self.performSetValue(swhtrFunc, False)
        elif quant.name in ('BxRate', 'ByRate', 'BzRate'):
            self.askAndLog(quant.set_cmd + ":" + str(value))
        elif quant.name in ('BxSwitchHeater', 'BySwitchHeater', 'BzSwitchHeater'):
            vstring = "OFF"
            if value:
                vstring = "ON"
            delay = self.instrCfg.getQuantity('SwitchHeaterDelay').getValue()
            if not delay > 1:
                self.Log("Switch Heater delay unreasonably short. Will not continue as this seems to be an error.")
                return value
            self.askAndLog(quant.set_cmd + ":" + vstring)
            
            tk = Tkinter.Tk()
            label = Tkinter.Label(tk, text="Waiting for switch heater...")
            label.pack(expand=1)
            tk.after(int(delay*1000), lambda: tk.destroy())
            tk.mainloop()
        return value

    def waitForIdle(self, dev):
        idle = (self.askAndLog('READ:DEV:' + dev + ':PSU:ACTN').strip().rsplit(':',1)[1] == "HOLD")
        while not idle and not self.isStopped():
            self.wait(0.1)
            idle = (self.askAndLog('READ:DEV:' + dev + ':PSU:ACTN').strip().rsplit(':',1)[1] == "HOLD")
        if self.isStopped():
            self.askAndLog('SET:DEV:' + dev + ':PSU:ACTN:HOLD')

