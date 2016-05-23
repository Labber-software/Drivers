from VISA_Driver import VISA_Driver
import InstrumentDriver
import numpy as np

__version__  = '0.5'

class Driver(VISA_Driver):

    def performOpen(self,options={}):
        VISA_Driver.performOpen(self,options=options)
        #Set the format for the output
        VISA_Driver.writeAndLog(self,'FORM:ELEM:SENS VOLT,CURR,RES')
        #Put source modes to fixed (rather than sweep)
        VISA_Driver.writeAndLog(self,'SOUR:CURR:MODE FIX; :SOUR:VOLT:MODE FIX')

    """
    def performClose(self,bError=False,options={}):
        VISA_Driver.performClose(self,bError,options=options)
    """

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        self.log('performSetValue called: '+quant.name+' value: '+str(value))
        if quant.name == 'Voltage Mode':
            if value == 'Fixed':
                VISA_Driver.writeAndLog(self,'SOUR:VOLT:MODE FIX')
            elif value == 'Ramp':
                #General settings for ramp function
                #Rtime, start:level, end:level are set when actually sweeping
                cmd = []
                cmd.append('SOUR:VOLT:MODE ARB')
                cmd.append('SOUR:ARB:FUNC:SHAP RAMP')
                cmd.append('SOUR:ARB:COUN 1')
                cmd.append('SOUR:ARB:VOLT:RAMP:END:TIME 0')
                cmd.append('SOUR:ARB:VOLT:RAMP:STAR:TIME 0')
                sCmd = cmd.join('; :')
                VISA_Driver.writeAndLog(self,sCmd)
        elif quant.name.endswith('Amplitude'):
            #Voltage Amplitude
            #Current Amplitude
            if quant.name.startswith('Voltage'):
                cmd = 'SOUR:VOLT'
                maxOutpDiff = 0.005 #Never change by more than 5mV
            else:
                cmd = 'SOUR:CURR'
                maxOutpDiff = 0.001 #Never change by more than 1 mA
            initValue = VISA_Driver.askAndLog(self,cmd+'?')
            outpDiff = value-float(initValue)
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
        elif quant.name.endswith(' Ramp'):
            if quant.name.startswith('Voltage'):
                cmd = 'SOUR:VOLT'
                cmd2 = 'SOUR:ARB:VOLT:RAMP'
                maxSweepRate = 0.005 #Never sweep faster than 5mV/sec
            elif quant.name.startswith('Current'):
                cmd = 'SOUR:CURR'
                cmd2 = 'SOUR:ARB:CURR:RAMP'
                maxSweepRate = 0.001 #Never sweep faster than 1mA/sec
            self.log("getting init value for ramp")
            initValue = float(VISA_Driver.askAndLog(self,cmd+'?'))
            outpDiff = value - initValue
            if sweepRate == 0 or sweepRate > maxSweepRate:
                sweepRate = maxSweepRate
            rTime = abs(outpDiff)/sweepRate
            cmd = []
            cmd.append(cmd2+':END:LEV '+str(value))
            cmd.append(cmd2+':RTIM '+str(rTime))
            cmd.append(cmd2+':STAR:LEV '+str(initValue))
            cmd.append('TRIG') #Sends an immediate trigger for both source and measure actions
            sCmd = '; :'.join(cmd)
            VISA_Driver.writeAndLog(self,sCmd)
        elif quant.name.startswith('Measure '):
            #Enable appropriate functions, if something has been updated
            if self.isConfigUpdated():
                #Determine which variables are being measured
                quantDict = {'Measure Current':['CURR',False], \
                             'Measure Voltage':['VOLT',False], \
                             'Measure Resistance':['RES',False]}
                for key,list in quantDict.items():
                    list[1] = self.getValue(key)
                    if list[1]:
                        VISA_Driver.writeAndLog(self,'FUNC:ON '+list[0])
                    else:
                        VISA_Driver.writeAndLog(self,'FUNC:OFF '+list[0])
            return value
        elif quant.name == "Measurement Speed Method":
            #No commands sent to device for this quantity
            return value
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
        else:
            return VISA_Driver.performGetValue(self,quant,options)

    
    def performStopSweep(self,quant,options={}):
        #This command is only necessary if in ramp mode
        if quant.name.startswith('Voltage'):
            mode = self.getValue('Voltage Mode')
        elif quant.name.startswith('Current'):
            mode = self.getValue('Voltage Mode')
        else:
            #if it is some other quant, call default function
            VISA_Driver.performStopSweep(self,quant,options)
        if mode == 'Ramp':
            VISA_Driver.writeAndLog(self,'ABOR')

    """
    def checkIfSweeping(self, quant, options={}):
        VISA_Driver.checkIfSweeping(self,quant,options=options)
    """

if __name__ == '__main__':
    pass
