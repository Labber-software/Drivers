from VISA_Driver import VISA_Driver
import numpy as np

class Driver(VISA_Driver):
    """ The Yoko driver re-implements the VISA driver with some more options"""


    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # keep track of sweep state
        self.is_sweeping = False
        # start by calling the generic VISA open to make sure we have a connection
        VISA_Driver.performOpen(self, options=options)
        # always get function and range: they are essential for correct resolution and sweeping
        self.readValueFromOther('Function')


    def initSetConfig(self):
        """This function is run before setting values in Set Config.
        Check if new range is smaller than old, if so first go to new value to
        avoid zeroing when setting the range with high value"""
        # get functions and range, first from internal settings (from SetCfg)
        newFunction = self.getValue('Function')
        dRangeNew, dMaxNew = self.getMaxValueAndSmallestStep()
        # get actual settings on instrument by first calling readFromOther
        oldFunction = self.readValueFromOther('Function')
        # also read the range settings
        if oldFunction == 'Voltage':
            self.readValueFromOther('Range (V)')
        elif oldFunction == 'Current':
            self.readValueFromOther('Range (I)')
        dRangeOld, dMaxOld = self.getMaxValueAndSmallestStep()
        # check if instrument in different mode ot new range is bigger, if so return
        if (newFunction != oldFunction) or (dMaxNew > dMaxOld):
            return
        # set new value, either voltage or current
        if newFunction == 'Voltage':
            quant = self.getQuantity('Voltage')
        elif newFunction == 'Current':
            quant = self.getQuantity('Current')
        # get new value and sweep rate from internal quantity 
        value = quant.getValue()
        rate = quant.getSweepRate()
        # set value here, before changing the range
        self.sendValueToOther(quant.name, value, sweepRate=rate)


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # check if set value and in sweep mode
        if quant.name in ('Voltage', 'Current'):
            # check limits
            (dStep, dMax) = self.getMaxValueAndSmallestStep()
            if abs(value) > dMax:
                # new value out of range, return error
                raise Exception('New value (%.6g) is out of range (max = %.6g)' % (value, dMax))
            # calculate actual value based on smallest step size
            value = dStep * np.round(value/dStep)
            # check if sweep mode or output off, if not call generic driver
            if sweepRate == 0.0 or (not self.getValue('Output')):
                return VISA_Driver.performSetValue(self, quant, value, 0.0, options=options)
            # sweep mode, do it here
            # get old value to find sweep time and step size
            currValue = self.performGetValue(quant)
            if value == currValue:
                # already at the final value, return
                return value
            # if sweep range is less than two minimal steps, don't sweep
            if abs(value-currValue) < 2.5*dStep:
                return VISA_Driver.performSetValue(self, quant, value, 0.0, options=options)
            dSweepTime = abs(value-currValue)/sweepRate
            # don't allow sweep times that are shorter than 0.1 s
            dSweepTime = max(dSweepTime, 0.1)
            sSweepTime = '%.1f' % dSweepTime
            sCmd = '*CLS;:PROG:REP 0;' + \
                   'SLOP %s;' % sSweepTime + \
                   'INT %s;'  % sSweepTime + \
                   'EDIT:STAR;' + \
                   ':SOUR:LEV %.6E;' % value + \
                   ':PROG:EDIT:END;' + \
                   ':PROG:RUN'
            self.is_sweeping = True
            VISA_Driver.writeAndLog(self, sCmd)  
            # return target value
            return value
        else:
            # for all other quantities, call the generic VISA driver
            return VISA_Driver.performSetValue(self, quant, value, sweepRate,
                                               options=options)


    def checkIfSweeping(self, quant, options={}):
        """Check if instrument is sweeping the given quantity"""
        # check for bit 7 EOP (End of program) im the extended event register
        status = self.askAndLog(':STAT:EVEN?')
        # mark as done if bit is set
        if (int(status) & 128) > 0:
            self.is_sweeping = False
        return self.is_sweeping


    def getMaxValueAndSmallestStep(self):
        """Return the resolution, which depends on function (voltage or current)
        and range settings"""
        # get function type
        func = self.getValue('Function')
        if func == 'Voltage':
            # get range, voltage
            dRange = {'30 V': 1E-3, '10 V': 1E-4, '1 V': 1E-5, '100 mV': 1E-6,
                      '10 mV': 1E-7}
            dMax = {'30 V': 32.0, '10 V': 12.0, '1 V': 1.2, '100 mV': 0.12,
                    '10 mV': 0.012}
            sRange = self.getValue('Range (V)')
            return (dRange[sRange], dMax[sRange])
        elif func == 'Current':
            # get range, current
            dRange = {'200 mA': 2E-6, '100 mA': 1E-6, '10 mA': 1E-7, '1 mA': 1E-8}
            dMax = {'200 mA': .2, '100 mA': .12, '10 mA': 0.012, '1 mA': 0.0012}
            sRange = self.getValue('Range (I)')
            return (dRange[sRange], dMax[sRange])


