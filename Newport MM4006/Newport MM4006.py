#!/usr/bin/env python

import InstrumentDriver
from VISA_Driver import VISA_Driver
import visa
from InstrumentConfig import InstrumentQuantity
import numpy as np

__version__ = "0.0.1"

class Error(Exception):
    pass

class Driver(VISA_Driver):
    """ This class implements the Newport MM4006 driver"""
  
    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # calling the generic VISA open to make sure we have a connection
        VISA_Driver.performOpen(self, options=options)
        
        degChannels = []
        self.unitFactors = [0. for i in range(8)]
        for i in range(1,9):
            #Check if channel can be used (left and right limit tripped indicates failure or missing device)
            if int(self.askAndLog(str(i)+"MS").strip()[3].encode("hex"), 16) & 0x18 == 0x18:
                continue
            #Check the units
            unit = self.askAndLog(str(i)+"SN?").strip()[3:]
            self.unitFactors[i] = 1.
            if unit == "Dg.":
                degChannels.append("ch"+str(i)+"deg")
            elif unit == "mm":
                degChannels.append("ch"+str(i)+"mm")
                self.unitFactors[i] = .001;
            else:
                degChannels.append("ch"+str(i)+"unknown")
            #Set maximum velocity
            vmax = self.askAndLog(str(i)+"VU?")[3:]
            self.writeAndLog(str(i)+"VA"+vmax)
        self.instrCfg.setInstalledOptions(degChannels)

        #Todo:
        #Set max speed
        #Check channel limits

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check type of quantity
        if quant.name[3:] in ('Position', 'Rotation', 'Value'):
            sAns = self.askAndLog(quant.get_cmd).strip()
            # Remove the query string from the response
            value = self.unitFactors[int(quant.name[2])]*float(sAns[len(quant.get_cmd):])
        elif quant.name[3:] in ('Name'):
            sAns = self.askAndLog(quant.get_cmd).strip()
            # Remove the query string from the response (-1 as the query contains a question mark)
            value = sAns[len(quant.get_cmd)-1:]
        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performGetValue(self, quant, options)
        return value
        
    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the set value operation"""
        # check type of quantity
        if quant.name[3:] in ('Position', 'Rotation', 'Value'):
            self.writeAndLog(quant.set_cmd.replace('<*>', "{:.4f}".format(value/self.unitFactors[int(quant.name[2])])))
            channel = quant.name[2]
            moving = (int(self.askAndLog(channel+"MS").strip()[3].encode("hex"), 16) & 0x01 != 0)
            while moving and not self.isStopped():
                self.wait(0.2)
                moving = (int(self.askAndLog(channel+"MS").strip()[3].encode("hex"), 16) & 0x01 != 0)
            if self.isStopped():
                self.askAndLog(quant.stop_cmd)
            value = self.performGetValue(quant, options)
        return value
        
if __name__ == '__main__':
    pass
