#!/usr/bin/env python

import InstrumentDriver
from VISA_Driver import VISA_Driver
from InstrumentConfig import InstrumentQuantity
import numpy as np
import struct

__version__ = "0.0.1"

class Error(Exception):
    pass

class Driver(VISA_Driver):
    """ This class implements the LeCroy scope driver"""

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # update visa commands for triggers
        if quant.name == 'Trig slope':
            sTrig = self.getCmdStringFromValue('Trig source')
            quant.set_cmd = '%s:TRSL' % sTrig
        elif quant.name == 'Trig level':
            sTrig = self.getCmdStringFromValue('Trig source')
            quant.set_cmd = '%s:TRLV' % sTrig
        # run standard VISA case with updated commands
        value = VISA_Driver.performSetValue(self, quant, value, sweepRate, options)
        return value
        

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check type of quantity
        if quant.name in ('Ch1 - Data', 'Ch2 - Data', 'Ch3 - Data', 'Ch4 - Data'):
            # traces, get channel
            channel = int(quant.name[2])
            # check if channel is on
            if self.getValue('Ch%d - Enabled' % channel):
                # get waveform descriptor data
#                sDesc = self.askAndLog('C%d:WF? DESC;' % channel)
                self.write('C%d:WF? DESC;' % channel, bCheckError=False)
                sDesc = self.read(ignore_termination=True)
                # start by finding byte count, skip 9 bytes after
                indx = sDesc.find('#9')
                sDesc = sDesc[indx+2+9:]
                # strip out relevant info
                iFirst = struct.unpack('>i', sDesc[124:128])[0]
                iLast = struct.unpack('>i', sDesc[128:132])[0]
                Voffs = struct.unpack('>f', sDesc[160:164])[0]
                Vgain = struct.unpack('>f', sDesc[156:160])[0]
                dt = struct.unpack('>f', sDesc[176:180])[0]
                nPts = struct.unpack('>i', sDesc[116:120])[0]
    #            print (iFirst, iLast, Voffs, Vgain, dt, nPts)
                #
                # do a second call to get data, convert to numpy array
                self.write('C%d:WF? DAT1;' % channel, bCheckError=False)
                sData = self.read(ignore_termination=True)
                head = 16
                vData = np.fromstring(sData[(head + iFirst*2):(head + (iLast+1)*2)], 
                                      dtype='>h', count=nPts)
                value = InstrumentQuantity.getTraceDict(vData*Vgain + Voffs, dt=dt)
            else:
                # not enabled, return empty array
                value = InstrumentQuantity.getTraceDict([])
        elif quant.name == 'Trig source':
            # trig source, treat seperately
            sAns = self.askAndLog('TRSE?').strip()
            i1 = sAns.find(',SR,') + 4
            i2 = sAns.find(',HT')
            # convert response to a number
            value = quant.getValueFromCmdString(sAns[i1:i2])
        elif quant.name == 'Trig level':
            # trig options, get local trig source value
            sTrig = self.getCmdStringFromValue('Trig source')
            sAns = self.askAndLog('%s:TRLV?' % sTrig).strip()
            i1 = sAns.find('V')
            value = float(sAns[:i1])
        elif quant.name == 'Trig slope':
            # trig options, get local trig source value
            sTrig = self.getCmdStringFromValue('Trig source')
            # update visa commands
            quant.set_cmd = '%s:TRSL' % sTrig
            # run standard VISA case with updated commands
            value = VISA_Driver.performGetValue(self, quant, options)
        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performGetValue(self, quant, options)
        return value

if __name__ == '__main__':
    pass


