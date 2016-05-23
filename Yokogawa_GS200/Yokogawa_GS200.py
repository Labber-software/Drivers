from VISA_Driver import VISA_Driver
import InstrumentDriver
import numpy as np

__version__  = '0.5'


class Driver(VISA_Driver):
    def performSetValue(self, quant, value, sweepRate=0.001, options={}):
        if quant.name == 'Output':
            if value:
                VISA_Driver.writeAndLog(self,'OUTP:STAT ON')
                return True
            else:
                #Sweep source to zero before turning off, to avoid sudden jumps
                func = self.getValue('Function')
                if func == 'Voltage':
                    self.sendValueToOther('Source Voltage Level',0)
                    while self.checkIfSweeping('Source Voltage Level',options):
                        self.wait(0.05)
                elif func == 'Current':
                    self.sendValueToOther('Source Current Level',0)
                    while self.checkIfSweeping('Source Current Level',options):
                        self.wait(0.05)
                VISA_Driver.writeAndLog(self,'OUTP:STAT OFF')
                return False
        elif quant.name == 'Function':
            if value == 'Voltage':
                VISA_Driver.writeAndLog(self,'SOUR:FUNC VOLT')
                return 'Voltage'
            elif value == 'Current':
                VISA_Driver.writeAndLog(self,'SOUR:FUNC CURR')
                return 'Current'
        elif quant.name == 'Source Current Range' or quant.name == 'Source Voltage Range':
            VISA_Driver.writeAndLog(self,'SOUR:RANG '+str(value))
            return value
        elif quant.name == 'Source Voltage Level' or quant.name == 'Source Current Level':
            self.log(quant.name+' value passed: '+str(value))
            self.log('Sweep rate: '+str(sweepRate))
            #Check current source level
            initValue = float(self.askAndLog('SOUR:LEV?'))
            if value == initValue:
                #if no change, do nothing
                return float(value)
            else:
                #It seems sometimes sweepRate is not passed to this function (e.g. when setting config)
                # Ensure that this never causes a jump in source levels
                if quant.name == 'Source Voltage Level':
                    maxSweepRate = 0.03 #30mV/sec or 1.8V/min
                else:
                    maxSweepRate = 0.03 #30mA/sec or 1.8A/min
                if sweepRate == 0 or sweepRate > maxSweepRate:
                    sweepRate = maxSweepRate
                difference = abs(value - initValue)
                duration = difference/abs(sweepRate)
                #Note minimum duration is 0.1s
                duration = max(duration,0.1)
                cmd1 = 'PROG:REP 0; '               #Program doesn't repeat
                cmd2 = 'SLOP '+str(duration)+'; '   #Source takes this long to move between values
                cmd3 = 'INT '+str(duration)+'; '    #This much time between program steps
                cmd4 = 'EDIT:STAR; '                #Add points to program
                cmd5 = ':SOUR:LEV '+str(value)+'; ' #Add target point
                cmd6 = ':PROG:EDIT:END; '           #Stop adding points to program
                cmd7 = ':PROG:RUN'                  #Run program
                sCmd = cmd1+cmd2+cmd3+cmd4+cmd5+cmd6+cmd7
                VISA_Driver.writeAndLog(self,sCmd)  #Combine all the above into one string, then send it
                return float(value)
        else:
            self.log('No other quant names triggered: '+quant.name)
            return VISA_Driver.performSetValue(self,quant,value,options,sweepRate)
    def performGetValue(self, quant, options={}):
        if quant.name == 'Output':
            value = VISA_Driver.askAndLog(self,'OUTP:STAT?')
            #Value will be 0 (false/off) or 1 (true/on)
            return int(value)
        elif quant.name == 'Function':
            value = VISA_Driver.askAndLog(self,'SOUR:FUNC?')
            if value == 'VOLT':
                return 'Voltage'
            elif value == 'CURR':
                return 'Current'
            return value
        elif quant.name == 'Source Current Range' or quant.name == 'Source Voltage Range':
            return VISA_Driver.askAndLog(self,'SOUR:RANG?')
        elif quant.name == 'Source Voltage Level' or quant.name == 'Source Current Level':
            returnVal = VISA_Driver.askAndLog(self,'SOUR:LEV?')
            return float(returnVal)
        else:
            self.log('Get quantity not listed elsewhere: '+quant.name)
            return VISA_Driver.performGetValue(self,quant,options)
    def performStopSweep(self,quant,options={}):
        VISA_Driver.writeAndLog(self,'PROG:PAUS')
    def checkIfSweeping(self, quant, options={}):
        #Can't create quant instances from here, can only pass name of quant
        #Whereas system
        if type(quant) == str:
            name = quant
        else:
            name = quant.name
        if name == 'Source Voltage Level' or name == 'Source Current Level':
            #If sweeping, can't go into program edit mode
            #Can't see any other way of checking if program is running
            VISA_Driver.writeAndLog(self,'*CLS') #Clear any existing errors
            VISA_Driver.writeAndLog(self,'PROG:EDIT:STAR') #force an error if program running
            err = VISA_Driver.askAndLog(self,'SYST:ERR?') #Check if there's a 'program running' error
            #Separate error code and error message
            #error code = 0 -> no errors
            errCode = int(err.split(',')[0])
            if errCode == -284:
                #There is a 'program running' error, so program must be sweeping
                return True
            elif errCode == 103:
                #There is a 'program being edited error' for some reason. Stop editing
                self.log("Program didn't stop properly")
                VISA_Driver.writeAndLog(self,'PROG:EDIT:END')
                return False
            else:
                VISA_Driver.writeAndLog(self,'PROG:EDIT:END')
                return False
        else:
            #Not checking one of the quants that can sweep
            return False
if __name__ == '__main__':
    pass
