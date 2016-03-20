#!/usr/bin/env python

from VISA_Driver import VISA_Driver
from InstrumentConfig import InstrumentQuantity
import numpy as np

__version__ = "0.0.1"

class Error(Exception):
    pass

class Driver(VISA_Driver):
    """ This class implements the LeCroy scope driver"""

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check type of quantity
        if quant.name in ('Ch1 - Data', 'Ch2 - Data', 'Ch3 - Data', 'Ch4 - Data'):
            # traces, get channel
            channel = int(quant.name[2])
            # check if channel is on
            if self.getValue('Ch%d - Enabled' % channel):
                # select channel and set # of bytes to send
                if self.getModel()=='TDS 3000':
                    self.write(':DATA:SOU CH%d;:WFMP:BYT_N 2;' % channel, bCheckError=False)
                else:
                    self.write(':DATA:SOU CH%d;:WFMO:BYT_N 2;' % channel, bCheckError=False)
                # query range and offset
                if self.getModel()=='TDS 3000':
                    sRange = self.ask(':WFMP:XZE?;:WFMP:XIN?;:WFMP:YMU?;:WFMP:YOF?;:WFMP:YZE?;', bCheckError=False)
                else:
                    sRange = self.ask(':WFMO:XZE?;:WFMO:XIN?;:WFMO:YMU?;:WFMO:YOF?;:WFMO:YZE?;', bCheckError=False)
                lRange = sRange.split(';')
                (t0, dt, gain, ioffset, offset) = [float(s) for s in lRange]
                # get data as i16, convert to numpy array
                self.write('CURV?', bCheckError=False)
                sData = self.read(ignore_termination=True)
                # strip header to find # of points
                i0 = sData.find('#')
                nDig = int(sData[i0+1])
                nByte = int(sData[i0+2:i0+2+nDig])
                nData = nByte/2
                # get data to numpy array
                vData = np.frombuffer(sData[(i0+2+nDig):(i0+2+nDig+nByte)], 
                                      dtype='>h', count=nData)
                value = InstrumentQuantity.getTraceDict( \
                        gain*(vData - ioffset) + offset, dt=dt)
            else:
                # not enabled, return empty array
                value = InstrumentQuantity.getTraceDict([])
        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performGetValue(self, quant, options)
        return value

if __name__ == '__main__':
    pass


