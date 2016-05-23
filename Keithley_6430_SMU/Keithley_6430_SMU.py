from VISA_Driver import VISA_Driver
import InstrumentDriver
import numpy as np

__version__  = '0.5'

class Driver(VISA_Driver):

    def performOpen(self,options={}):
        VISA_Driver.performOpen(self,options)
        #Set the format for the output
        VISA_Driver.writeAndLog(self,'FORM:ELEM VOLT,CURR,RES')
        #Put source modes to fixed (rather than sweep)
        VISA_Driver.writeAndLog(self,'SOUR:CURR:MODE FIX; :SOUR:VOLT:MODE FIX')

    """
    def performClose(self,bError=False,options={}):
        VISA_Driver.performClose(self,bError,options=options)
    """

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        self.log('performSetValue called: '+quant.name+' value: '+str(value))
        if quant.name == 'Source on_off':
            if value == 'On':
                VISA_Driver.writeAndLog(self,'OUTP:STAT 1')
                return 'On'
            else:
                #Sweep source to zero before turning off, to avoid sudden jumps
                func = self.getValue('Source function')
                if func == 'Voltage':
                    self.sendValueToOther('Voltage Amplitude',0)
                    while self.sendValueToOther('Voltage Amplitude',0) != 0:
                        self.wait(0.1)
                elif func == 'Current':
                    self.sendValueToOther('Current Amplitude',0)
                    while self.sendValueToOther('Voltage Amplitude',0) != 0:
                        self.wait(0.1)
                VISA_Driver.writeAndLog(self,'OUTP:STAT 0')
                return 'Off'
        elif quant.name.endswith('Amplitude'):
            #Voltage Amplitude
            #Current Amplitude
            if quant.name.startswith('Voltage'):
                cmd = 'SOUR:VOLT'
                maxOutpDiff = 0.0005 #5mV/s
                #Program sets source every 0.1 seconds, so sweepRate = outpDiff/0.1 = 10*outpDiff
                #Note minimum output change is 5uV.
            else:
                cmd = 'SOUR:CURR'
                maxOutpDiff = 0.0001
            initValue = float(VISA_Driver.askAndLog(self,cmd+'?'))
            outpDiff = value-initValue
            if outpDiff == 0:
                #Don't send if already at right value
                return value
            elif outpDiff > maxOutpDiff:
                #If program is trying to move to a value too far away instantly,
                #  then override by changing value
                    value = initValue+maxOutpDiff
            elif outpDiff < -maxOutpDiff:
                    value = initValue-maxOutpDiff
            #Enter the (modified or unmodified) value
            VISA_Driver.writeAndLog(self,cmd+' '+str(value))
            return value
        elif quant.name.startswith('Measure '):
            #Determine which variables are being measured
            quantDict = {'Measure Current':['CURR',False], \
                         'Measure Voltage':['VOLT',False], \
                         'Measure Resistance':['RES',False]}
            for key,list in quantDict.items():
                list[1] = self.getValue(key)
            
            #If only one, turn off concurrency
            if sum(list[1] for list in quantDict.values()) == 1:
                VISA_Driver.writeAndLog(self,'FUNC:CONC 0')
            else:
                VISA_Driver.writeAndLog(self,'FUNC:CONC 1')
            
            #Enable appropriate functions
            for key,list in quantDict.items():
                if list[1]:
                    VISA_Driver.writeAndLog(self,'FUNC:ON '+'"'+list[0]+'"')
                else:
                    VISA_Driver.writeAndLog(self,'FUNC:OFF '+'"'+list[0]+'"')
            return value
        elif quant.name.endswith('Range Mode'):
            #convert auto/manual to auto on, auto off
            comboDict = {'Manual':'0','Automatic':'1'}
            value = comboDict[value]
            #Check source mode
            func = self.getValue('Source function')
            if quant.name.startswith('Voltage'):
                if func == 'Voltage':
                    #If quant matches source mode, set source range
                    VISA_Driver.writeAndLog(self,'SOUR:VOLT:RANG:AUTO '+value)
                else:
                    #Otherwise, set measurement range
                    VISA_Driver.writeAndLog(self,'SENS:VOLT:RANG:AUTO '+value)
            elif quant.name.startswith('Current'):
                if func == 'Current':
                    VISA_Driver.writeAndLog(self,'SOUR:CURR:RANG:AUTO '+value)
                else:
                    VISA_Driver.writeAndLog(self,'SENS:CURR:RANG:AUTO '+value)
            elif quant.name.startswith('Resistance'):
                #If using manual resistance mode, do nothing
                if self.getValue('Resistance Measurement Mode') == 'Automatic':   
                    VISA_Driver.writeAndLog(self,'SENS:RES:RANG:AUTO '+value)
            return int(value)
        elif quant.name == 'Voltage Manual Range' or quant.name == 'Current Manual Range' :
            #Check source mode
            func = self.getValue('Source function')
            if quant.name.startswith('Voltage'):
                if func == 'Voltage':
                    #If quant matches source mode, set source range
                    VISA_Driver.writeAndLog(self,'SOUR:VOLT:RANG '+str(value))
                else:
                    #Otherwise, set compliance rainge and measurement range
                    VISA_Driver.writeAndLog(self,'SENS:VOLT:PROT '+str(value*1.1))
                    VISA_Driver.writeAndLog(self,'SENS:VOLT:RANG '+str(value))
            elif quant.name.startswith('Current'):
                if func == 'Current':
                    VISA_Driver.writeAndLog(self,'SOUR:CURR:RANG '+str(value))
                else:
                    VISA_Driver.writeAndLog(self,'SENS:CURR:PROT '+str(value*1.05))
                    VISA_Driver.writeAndLog(self,'SENS:CURR:RANG '+str(value))
            return value
        elif quant.name == 'Averaging Time':
            self.log('Averaging called')
            NPLC = self.getValue('NPLC')
            self.log('NPLC: '+str(NPLC))
            repeat = self.getValue('Repeat Filter')
            self.log('repeat: '+str(repeat))
            medRank = self.getValue('Median Filter')
            self.log('medRank: '+str(medRank))
            avCount = self.getValue('Moving Filter')
            self.log('avCount: '+str(avCount))
            timeBase = 1.0/50.0
            avTime = NPLC*timeBase*repeat*(2*medRank+1)*avCount
            self.setValue('Averaging Time',str(avTime))
            return avTime
        else:
            return VISA_Driver.performSetValue(self,quant,value,options=options,sweepRate=sweepRate)

    def performGetValue(self, quant, options={}):
        self.log('performGetValue called: '+quant.name)
        if quant.name.startswith('Measure '):
            #Determine which variables are being measured
            quantDict = {'Measure Current':'CURR', \
                         'Measure Voltage':'VOLT', \
                         'Measure Resistance':'RES'}
            reply = VISA_Driver.askAndLog(self,'FUNC?')
            if quantDict[quant.name] in reply:
                return True
            else:
                return False
        elif quant.name.endswith('variable'):
            #Have set up format so the read or fetch command always returns values in the following order 
            quantDict = {'Voltage variable':0, \
                         'Current variable':1, \
                         'Resistance variable':2}
            #If this is first measurement call, perform read operation and return appropriate values
            if self.isFirstCall(options):
                reply = VISA_Driver.askAndLog(self,'READ?')
            #otherwise perform fetch operation and return appropriate values
            else:
                reply = VISA_Driver.askAndLog(self,'FETCH?')
            value = reply.split(',')
            return value[quantDict[quant.name]]
        elif quant.name.endswith('Range Mode'):
            #For converting reply to combo choice
            comboDict = {0:'Manual',1:'Automatic'}
            #Check source mode
            func = self.getValue('Source function')
            if quant.name.startswith('Voltage'):
                if func == 'Voltage':
                    #If quant matches source mode, get source range
                    reply = VISA_Driver.askAndLog(self,'SOUR:VOLT:RANG:AUTO?')
                else:
                    #Otherwise, get measurement range
                    reply = VISA_Driver.askAndLog(self,'SENS:VOLT:RANG:AUTO?')
            elif quant.name.startswith('Current'):
                if func == 'Current':
                    reply = VISA_Driver.askAndLog(self,'SOUR:CURR:RANG:AUTO?')
                else:
                    reply = VISA_Driver.askAndLog(self,'SENS:CURR:RANG:AUTO?')
            elif quant.name.startswith('Resistance'):
                if self.getValue('Resistance Measurement Mode') == 'Automatic':
                    reply = VISA_Driver.askAndLog(self,'SENS:RES:RANG:AUTO?')
                else:
                    reply = 0
            return comboDict[int(reply)]
        elif quant.name == 'Voltage Manual Range' or quant.name == 'Current Manual Range' :
            #Check source mode
            func = self.getValue('Source function')
            if quant.name.startswith('Voltage'):
                if func == 'Voltage':
                    #If quant matches source mode, get source range
                    reply = VISA_Driver.askAndLog(self,'SOUR:VOLT:RANG?')
                else:
                    #Otherwise, get measurement range
                    reply = VISA_Driver.askAndLog(self,'SENS:VOLT:RANG?')
            elif quant.name.startswith('Current'):
                if func == 'Current':
                    reply = VISA_Driver.askAndLog(self,'SOUR:CURR:RANG?')
                else:
                    reply = VISA_Driver.askAndLog(self,'SENS:CURR:RANG?')
            return reply
        elif quant.name == 'Averaging Time':
            self.log('Averaging called')
            NPLC = self.getValue('NPLC')
            self.log('NPLC: '+str(NPLC))
            repeat = self.getValue('Repeat Filter')
            self.log('repeat: '+str(repeat))
            medRank = self.getValue('Median Filter')
            self.log('medRank: '+str(medRank))
            avCount = self.getValue('Moving Filter')
            self.log('avCount: '+str(avCount))
            timeBase = 1.0/50.0
            avTime = NPLC*timeBase*repeat*(2*medRank+1)*avCount
            return avTime
        else:
            return VISA_Driver.performGetValue(self,quant,options)

    """
    def performStopSweep(self,quant,options={}):
        VISA_Driver.writeAndLog(self,'ABOR')

    def checkIfSweeping(self, quant, options={}):
		VISA_Driver.checkIfSweeping(self,quant,options=options)
    """

if __name__ == '__main__':
    pass
