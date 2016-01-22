#!/usr/bin/env python

import InstrumentDriver
from VISA_Driver import VISA_Driver
import visa
from InstrumentConfig import InstrumentQuantity
import numpy as np
import string

__version__ = "0.0.1"

class Error(Exception):
    pass

class Driver(VISA_Driver):
    """ This class implements the Triton 200 driver"""
  
    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # calling the generic VISA open to make sure we have a connection
        VISA_Driver.performOpen(self, options=options)
        # Check if there really is an IPS120 at the other end of the wire
        if not "IPS120" in self.askAndLog("V"):
            raise InstrumentDriver.CommunicationError("Could not get an identification as IPS120.")
        self.writeAndLog("Q4")

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        if quant.name in ('B', 'SweepRate'):
            value = float(self.askAndLog(quant.get_cmd).strip()[1:])
            return value
        else:
            return quant.getValue()

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the set value operation"""
        if quant.name in ('B', 'SweepRate'):
            self.askAndLog("C3")
            if quant.name in ('B'):
                self.askAndLog(quant.set_cmd.replace('<*>', "{:.5f}".format(value)))
                self.askAndLog("A1")
                self.waitForTarget(value)
            elif quant.name in ('SweepRate'):
                self.askAndLog(quant.set_cmd.replace('<*>', "{:.4f}".format(value)))
            self.askAndLog("C2")
        return value

    def waitForTarget(self, target):
        current = float(self.askAndLog('R7').strip()[1:])
        precision = self.getValue("Precision")
        while abs(target-current) > precision and not self.isStopped():
            self.thread().msleep(100)
            current = float(self.askAndLog('R7').strip()[1:])
        self.askAndLog('A0')

