#!/usr/bin/env python

from VISA_Driver import VISA_Driver
import InstrumentDriver
import numpy as np

__version__  = '1.1'


class Driver(VISA_Driver):
    """ The Yoko driver re-implements the VISA driver with some more options"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
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
        if quant.name == 'Function':
            # if set function, first read old function (voltage or current)
            sAll = self.askAndLog('H1 OD')
            # check for errors and raise exception if necesary
            self.queryErrors()
            # check result, should be voltage or current, convert to option string
            if sAll[3] == 'V':
                sOldValue = '1'
            elif sAll[3] == 'A':
                sOldValue = '5'
            else:
                raise InstrumentDriver.InstrumentConfig.OptionError(sAll[3], ['V', 'A'])
            # convert given value to command string
            sValue = quant.getCmdStringFromValue(value)
            # if old and new command strings are different, set new, otherwise do nothing
            if sOldValue != sValue:
                newFunc = VISA_Driver.performSetValue(self, quant, value, sweepRate,
                                                      options=options)
                # set value to zero, since we changed function
                if sValue == '1':
                    self.sendValueToOther('Voltage', 0.0)
                elif sValue == '5':
                    self.sendValueToOther('Current', 0.0)
                # also get new range by re-reading the func value
                newFunc = self.readValueFromOther('Function')
                return newFunc
            else:
                return value
        # check if set value and in sweep mode
        elif quant.name in ('Voltage', 'Current'):
            # check limits
            (dStep, dMax) = self.getMaxValueAndSmallestStep()
            if abs(value) > dMax:
                # new value out of range, return error
                raise Exception('New value (%.6g) is out of range (max = %.6g)' % (value, dMax))
            # calculate actual value based on smallest step size
            value = dStep * np.round(value/dStep)
            # check if sweep mode, if not call generic driver
            if sweepRate == 0.0:
                return VISA_Driver.performSetValue(self, quant, value, 0.0, options=options)
            # sweep mode, do it here
            sCmd = 'M1 PI<st> SW<st> PRS S<*> PRE RU2'
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
            # replace with sweep time string
            sCmd = sCmd.replace('<st>', sSweepTime)
            # check if value is to be included in the middle of the command
            sValue = quant.getCmdStringFromValue(value)
            sMsg = sCmd.replace('<*>', sValue)
            # start sweep
            self.writeAndLog(sMsg)
            # return target value
            return value
        else:
            # for all other quantities, call the generic VISA driver
            return VISA_Driver.performSetValue(self, quant, value, sweepRate,
                                               options=options)


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # do special case get value for some quantities
        if quant.name in ('Function', 'Range (V)', 'Range (I)'):
            # common method for these quants
            s1 = self.askAndLog('OS')
            # this command returns five lines of info, get them all
            s2 = self.read()
            s3 = self.read()
            s4 = self.read()
            s5 = self.read()
            # check for errors and raise exception if necesary
            self.queryErrors()
            # first four characters in line 2 contains the info 'FnRm', with
            # F: n=1: voltage, n=5: current
            # R: m=2-6: voltage range, m=4-6: current range
            sFunc = s2[1]
            sRange = s2[3]
            if quant.name == 'Function':
                # func quantity, get value
                valueFunc = quant.getValueFromCmdString(sFunc)
                # function changed, keep track of new internal range quantities
                if valueFunc == 'Voltage':
                    quantRange = self.getQuantity('Range (V)')
                elif valueFunc == 'Current':
                    quantRange = self.getQuantity('Range (I)')
                valueRange = quantRange.getValueFromCmdString(sRange)
                quantRange.setValue(valueRange)
                # return func value
                return valueFunc
            else:
                # range quantity
                return quant.getValueFromCmdString(sRange)
        # check for output
        elif quant.name == 'Output':
            # get bit info, output is bit 4 (=16)
            status = self.askAndLog('OC')
            # check for errors and raise exception if necesary
            self.queryErrors()
            # perform bitwise and to get output on/off
            return (int(status[5:]) & 16) > 0
        else:
            # run the generic visa driver case
            return VISA_Driver.performGetValue(self, quant, options=options)


    def checkIfSweeping(self, quant, options={}):
        """Check if instrument is sweeping the given quantity"""
        # check for a bit combination in the response from the OC command
        status = self.askAndLog('OC')
        return ((int(status[5:]) & 3) > 0)


    def getMaxValueAndSmallestStep(self):
        """Return the resolution, which depends on function (voltage or current)
        and range settings"""
        # get function type
        func = self.getValue('Function')
        if func == 'Voltage':
            # get range, voltage
            dRange = {'30 V': 1E-3, '10 V': 1E-4, '1 V': 1E-5, '100 mV': 1E-6,
                      '10 mV': 1E-7}
            dMax = {'30 V': 30.0, '10 V': 12.0, '1 V': 1.2, '100 mV': 0.12,
                    '10 mV': 0.012}
            sRange = self.getValue('Range (V)')
            return (dRange[sRange], dMax[sRange])
        elif func == 'Current':
            # get range, current
            dRange = {'100 mA': 1E-6, '10 mA': 1E-7, '1 mA': 1E-8}
            dMax = {'100 mA': .12, '10 mA': 0.012, '1 mA': 0.0012}
            sRange = self.getValue('Range (I)')
            return (dRange[sRange], dMax[sRange])


if __name__ == '__main__':
    pass
