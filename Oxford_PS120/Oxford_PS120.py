#!/usr/bin/env python

from VISA_Driver import VISA_Driver

__version__ = '0.3'

# the Oxford PS does not seem to be able to handle commands any faster
# a delay between commands is needed
delayTime = 0.1

class Driver(VISA_Driver):
    """ This class implements the Oxford PS driver"""
    def performOpen(self,options={}):
        VISA_Driver.performOpen(self,options)
        self.wait(delayTime)
        """
        #Switch to remote & unlocked mode
        #(command already in 'init:' field in INI file)
        VISA_Driver.writeAndLog('$C3')
        """
        self.clearMessages()
        #Switch to extended resolution
        VISA_Driver.writeAndLog(self,'$Q4')
        #Clear clamped status, if applicable
        VISA_Driver.writeAndLog(self,'$A0')
        self.wait(delayTime)

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        self.clearMessages()
        self.log('performSetValue of: '+quant.name+' with value: '+str(value))
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # check quantity
        if quant.name == 'Magnetic Field' or quant.name == 'Current':
            self.log('In Magnetic Field or Current: '+quant.name)
            if quant.name == 'Magnetic Field':
                self.log('In Magnetic Field')
                perCmd = 'R18'
                sourCmd = 'R7'
                targetCmd = '$J'
                sweepRCmd = '$T'
                ###hOffSweepRate can be increased once
                ### it is shown heater status is reliable
                hOffSweepRate = 0.05 #50mT/minute
                maxSweep = 0.05 #50 mT/minute
            elif quant.name ==  'Current':
                self.log('In Current')
                perCmd = 'R16'
                sourCmd = 'R0'
                targetCmd = '$I'
                sweepRCmd = '$S'
                ###hOffSweepRate value can be increased once
                ### it is shown heater status is reliable
                hOffSweepRate = 2.29 #2.29A/minute
                maxSweep = 0.05 #50 mA/minute
            #1) Check field against persistent field
            #   Check heater status
            perVal = float(self.askAndLog(perCmd)[1:])
            self.wait(delayTime)
            sourVal = float(self.askAndLog(sourCmd)[1:])
            self.wait(delayTime)
            hStatus = self.readValueFromOther('Heater status')
            if perVal == value and not(hStatus):
                self.log('perVal == value, so returning')
                #Already at value, do nothing
                return value
            elif sourVal == value and hStatus:
                self.log('perVal == value, so returning')
                #Already at value, do nothing
                return value
            elif sourVal != perVal and not(hStatus):
                """If there is a difference between source and persistent field/current
                    Set source value to persistent value before turning heater on"""
                self.log('sour != perVal and hStatus == False, adjusting source level')
                self.writeAndLog(targetCmd+str(perVal))
                self.wait(delayTime)
                self.writeAndLog(sweepRCmd+str(hOffSweepRate))
                self.wait(delayTime)
                self.writeAndLog('$A1')
                self.wait(delayTime)
            if not hStatus:
                self.log('sour/per levels good, but heater off')
                #If heater is off, turn it on
                hStatus = self.heaterOn()
            if hStatus: 
                self.log('heater is on, setting targets and sweeping')
                #heater is on
                #4) Change set point
                self.writeAndLog(targetCmd+str(value))
                self.wait(delayTime)
                #5) Change sweep rate
                if sweepRate == 0 or sweepRate > maxSweep:
                    sweepRate = maxSweep
                self.writeAndLog(sweepRCmd+str(sweepRate))
                self.wait(delayTime)
                #6) Go to set point
                self.writeAndLog('$A1')
                self.wait(delayTime)
                #7) Wait for sweep
                valueDiff = value - perVal
                sweepTime = 60.0*abs(valueDiff)/(sweepRate)
                self.wait(delayTime)
                self.waitForSweep(quant,options,sweepTime)
                value = self.readValueFromOther(quant.name,options)
                self.heaterOff()
                return value
            else:
                return perVal
        elif quant.name == 'Current or Field':
            self.wait(delayTime)
            if value == 'Magnetic Field':
                self.writeAndLog('$M9')
                self.wait(delayTime)
            elif value == 'Current':
                self.writeAndLog('$M8')
                self.wait(delayTime)
        else:
            # run standard VISA case 
            value = VISA_Driver.performSetValue(self, quant, value, sweepRate, options)
        return value


    def performGetValue(self, quant, options={}):
        self.clearMessages()
        self.log('performGetValue of: '+quant.name)
        """Perform the Get Value instrument operation"""
        # check type of quantity
        # check quantity
        if quant.name == 'Magnetic Field':
            hStatus = self.readValueFromOther('Heater status')
            self.wait(delayTime)
            if hStatus:
                #If heater is on, get source field
                reply = self.askAndLog('R7')
                self.wait(delayTime)
            else:
                #If heater is off, get persistent field
                reply = self.askAndLog('R18')
                self.wait(delayTime)
            return float(reply[1:])
        if quant.name == 'Current':
            hStatus = self.readValueFromOther('Heater status')
            self.wait(delayTime)
            if hStatus:
                #If heater is on, get source current
                reply = self.askAndLog('R0')
                self.wait(delayTime)
            else:
                #If heater is off, get persistent current
                reply = self.askAndLog('R16')
                self.wait(delayTime)
            value = float(reply[1:])
        elif quant.name == 'Heater status':
            reply = self.askAndLog('X')
            self.wait(delayTime)
            if not(reply.startswith('X')):
                self.log('Mismatched response to X: '+reply)
                return 0
            #Reply is of the form XmnAnCnHnMmnPmn
            #So, find index of the 'H' and return the value that is one after it
            index = reply.index('H')+1
            self.log('In performGetValue - Heater status')
            self.log('Reply is: '+reply)
            self.log('Index +1 is: '+str(index))
            self.log('Length of reply is: '+str(len(reply)))
            self.log('Status value is: '+str(reply[index]))
            status = int(reply[index])
            if status == 1:
                self.log('Returning True, Heater is on')
                return True
            else:
                self.log('Returning fALSE, Heater is off')
                return False
        elif quant.name == 'Current or Field':
            reply = self.askAndLog('X')
            self.wait(delayTime)
            if not(reply.startswith('X')):
                self.log('Mismatched response to X: '+reply)
                return 0
            index = reply.index('M')+1
            status = int(reply[index])
            if status == 0 or status == 4:
                return 'Current'
            elif status == 1 or status == 3:
                return 'Magnetic field'
        elif quant.name == 'Source Current':
            reply = self.askAndLog('R0')
            self.wait(delayTime)
            if not(reply.startswith('R')):
                self.log('Mismatched response to R0: '+reply)
                return 0
            # strip first character
            reply = reply[1:]
            # convert to float
            value = float(reply)
        elif quant.name == 'Source Magnetic Field':
            reply = self.askAndLog('R7')
            self.wait(delayTime)
            if not(reply.startswith('R')):
                self.log('Mismatched response to R7: '+reply)
                return 0
            # strip first character
            reply = reply[1:]
            # convert to float
            value = float(reply)
        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performGetValue(self, quant, options)
        return value
        
    def checkIfSweeping(self, quant, options={}):
        self.log('Doing sweep checking of '+quant.name)
        reply = self.askAndLog('X')
        self.wait(delayTime)
        if not(reply.startswith('X')):
            self.log('Mismatched response to X: '+reply)
            return 0
        #Reply is of the form XmnAnCnHnMmnPmn
        #So, find index of the 'M' and return the value that is two after it (the n)
        index = reply.index('M')+2
        status = int(reply[index])
        self.log('status: '+str(status))
        if status == 0:
            return False
        else:
            #For n = 1, 2, 3, output is changing
            #n=1: Sweeping
            #n=2: Sweep limiting
            #n=3: Sweeping and sweep limiting
            return True
        
    def performStopSweep(self, quant, options={}):
        self.log('attempting to stop sweep')
        self.writeAndLog('$A0')
        self.wait(delayTime)
        
    def heaterOn(self):
        """Helper function to turn on heater,
            wait, then check that it is on.
           Returns True if heater is on, False otherwise
           Also returns persistent current"""
        #1) Switch heater on using H1 (H1 also checks persistent current against source current)
        self.writeAndLog('$H1')
        self.wait(delayTime)
        #2) Wait for up to 20 seconds
        #   Heater should generally take 10-15 seconds to open
        self.wait(20)
        return self.readValueFromOther('Heater status')

    def heaterOff(self):
        self.writeAndLog('$H0')
        #9) wait for heater to turn off
        self.wait(20)
        hStatus = self.readValueFromOther('Heater status')
        while hStatus:
            hStatus = self.readValueFromOther('Heater status')
            self.wait(delayTime)

    def waitForSweep(self,quant,options,sweepTime):
        self.log('Wait for sweep called. Sweep time is: '+str(sweepTime))
        #First check that magnet is sweeping
        sweeping = self.checkIfSweeping(quant,options)
        self.log('reported status is: '+str(sweeping))
        if sweeping:
            self.log('In if-statement')
            #wait for expected duration
            self.wait(sweepTime)
            self.log('sweepTime over')
            #Check if it is still sweeping, wait for it to finish
            sweeping = self.checkIfSweeping(quant,options)
            self.log('sweeping status: '+str(sweeping))
            while sweeping:
                self.wait(delayTime)
                sweeping = self.checkIfSweeping(quant,options)
                self.log('While loop sweeping status: '+str(sweeping))
    
    def clearMessages(self):
        #Send version request so message buffer isn't empty
        VISA_Driver.writeAndLog(self,'V')
        #Read message buffer in full, to clear any messages that were not previously cleared
        #(Uncleared messages seem to arise from fact that device seems to be comparatively slow to reply)
        reply = VISA_Driver.read(self,ignore_termination=True)
        self.log("Message buffer read on initialisation: "+reply)
        while not reply.startswith('IPS120'):
            #There was an error or incorrect value, try to clear message buffer again
            reply = VISA_Driver.read(self,ignore_termination=True)
            self.wait(delayTime)
            self.log("Message buffer read again: "+reply)
            
if __name__ == '__main__':
    pass
