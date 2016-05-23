# -*- coding: utf-8 -*-
"""
Created on Sun Jan 24 12:21:00 2016

@author: Roger
"""

from VISA_Driver import VISA_Driver
import InstrumentDriver
import numpy as np

__version__ = '0.4'


class Driver(VISA_Driver):
    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        couplingModes = ['Coupling CFRQAB','Coupling CFRQAC','Coupling RFLVAB','Coupling RFLVAC']
        self.log('Quant.name is: '+quant.name+' Set value')
        if quant.name[-1] == ')':
            #Add source selection string to beginning of every
            #source specific command (ensure setting affects right source)
            source = quant.name[-2]
            sourceCmd = 'SOURCE '+source+'; :'
        if quant.name == 'Combiner Mode':
            VISA_Driver.writeAndLog(self,'CMODE '+value)
            return value
        elif quant.name == couplingModes[0]:
            """
            This function sets all coupling modes at once, so it should
            only be called once per set_config action.

            Note: COUPLING:MODE CFRQAB (for example) makes CFRQAB the only mode
            I.e. modes can't be added one by one
            """
            modeCmds = []
            for cMode in couplingModes:
                if self.getValue(cMode) == True:
                    self.log('Adding: '+cMode)
                    modeCmds.append(cMode.split(' ')[1])
            if len(modeCmds) == 0:
                cmdStr = 'COUPLING:MODE DISABLED'
            else:
                cmdStr = 'COUPLING:MODE '+','.join(modeCmds)
            VISA_Driver.writeAndLog(self,cmdStr)
        elif quant.name in couplingModes:
            pass
        elif quant.name.startswith('Coupling'):
            cmd = quant.name.split(' ')
            """
            cmd[0] = 'Coupling'
            cmd[1] = one of the coupling modes
            cmd[2] = MODE, HARM, SUBHARM, OFFSET
            """
            if cmd[2] == 'MODE':
                comboDict = {'Harmonic':'HARM','Sub-harmonic':'SUBHARM'}
                VISA_Driver.writeAndLog(self,'COUPLING:'+cmd[1]+':'+cmd[2]+' '+comboDict[value])
            else:
                VISA_Driver.writeAndLog(self,'COUPLING:'+cmd[1]+':'+cmd[2]+' '+str(value))
        elif quant.name.startswith('Carrier Frequency'):
            initValue = self.readValueFromOther(quant.name,options)
            initValue = float(initValue)
            if value == initValue:
                return initValue
            elif sweepRate != 0:
                """
                Sweeping is done by continuously setting frequency
                Minimum time between steps is 50msec
                """
                valueDiff = value - initValue
                time = abs(valueDiff)/sweepRate
                increment = 0.05*sweepRate
                #Sweep to point
                cmd = 'SWEEP:'+sourceCmd
                cmd += 'SWEEP:TRIG STARTSTOP; '
                cmd += 'SWEEP:CFRQ:START '+str(initValue)+'; '
                cmd +='STOP '+str(value)+'; '
                cmd += 'TIME 0.05S; '
                cmd += 'INC '+str(increment)+'; '
                cmd += ':SWEEP:GO'
                VISA_Driver.writeAndLog(self,cmd)
            else:
                VISA_Driver.writeAndLog(self,sourceCmd+'CFRQ:VALUE '+str(value)+'HZ')
        elif quant.name.startswith('Carrier Phase offset'):
            VISA_Driver.writeAndLog(self,sourceCmd+'CFRQ:PHASE '+str(value)+'DEG')
        elif quant.name.startswith('RF Output On'):
            if value:
                VISA_Driver.writeAndLog(self,sourceCmd+'RFLV:ON')
            else:
                VISA_Driver.writeAndLog(self,sourceCmd+'RFLV:OFF')
        elif quant.name.startswith('RF Level'):
            VISA_Driver.writeAndLog(self,sourceCmd+'RFLV:VALUE '+str(value)+'DBM')
        elif quant.name.startswith('RF Type'):
            VISA_Driver.writeAndLog(self,sourceCmd+'RFLV:TYPE '+str(value))
        elif quant.name.startswith('Modulation Control'):
            if value:
                VISA_Driver.writeAndLog(self,sourceCmd+'MOD:ON')
            else:
                VISA_Driver.writeAndLog(self,sourceCmd+'MOD:OFF')
        elif quant.name.startswith('Modulation mode'):
            modeList = []
            pulse = self.getValue('Pulse Modulation ('+source+')')
            if 'AM' in value:
                modeList.append('AM')
            if 'FM' in value:
                modeList.append('FM')
            if 'PM' in value:
                modeList.append('PM')
            if 'FSK2L' in value:
                modeList.append('FSK2L')
            if 'FSK4L' in value:
                modeList.append('FSK4L')
            if pulse:
                modeList.append('PULSE')
            VISA_Driver.writeAndLog(self,'MODE '+','.join(modeList))
        elif quant.name.startswith('Frequency Modulation Type'):
            if value:
                VISA_Driver.writeAndLog(self,sourceCmd+'FM:OFF; :FM1:ON; :FM2:ON')
            else:
                VISA_Driver.writeAndLog(self,sourceCmd+'FM:ON; :FM1:OFF; :FM2:OFF')
        elif quant.name.startswith('Phase Modulation Type'):
            if value:
                VISA_Driver.writeAndLog(self,sourceCmd+'PM:OFF; :PM1:ON; :PM2:ON')
            else:
                VISA_Driver.writeAndLog(self,sourceCmd+'PM:ON; :PM1:OFF; :PM2:OFF')
        elif quant.name.startswith('Pulse Modulation'):
            if value:
                VISA_Driver.writeAndLog(self,'PULSE:ON')
            else:
                VISA_Driver.writeAndLog(self,'PULSE:OFF')
        elif quant.name[:2] in ['FM','PM','AM']:
            cmd = quant.name.split(' ')
            """
            cmd[0] = FM1, FM2, PM1, PM2, AM1, or AM2
            cmd[1] = Deviation, Source, Modulation, Waveform, Phase, (Depth for AM), Status
            """
            if cmd[1] == 'Status':
                if value:
                    VISA_Driver.writeAndLog(self,sourceCmd+cmd[0]+':ON')
                else:
                    VISA_Driver.writeAndLog(self,sourceCmd+cmd[0]+':OFF')
            elif cmd[1] == 'Deviation':
                VISA_Driver.writeAndLog(self,sourceCmd+cmd[0]+':DEVN '+str(value))
            elif cmd[1] == 'Source':
                comboDict = {'Internal':'INT','External AC':'EXTAC','External ALC':'EXTALC','External DC':'EXTDC'}
                VISA_Driver.writeAndLog(self,sourceCmd+cmd[0]+':'+comboDict[value])
            elif cmd[1] == 'Modulation':
                VISA_Driver.writeAndLog(self,sourceCmd+cmd[0]+':MODF:VALUE '+str(value)+'HZ')
            elif cmd[1] == 'Waveform':
                VISA_Driver.writeAndLog(self,sourceCmd+cmd[0]+':MODF:'+str(value))
            elif cmd[1] == 'Phase':
                VISA_Driver.writeAndLog(self,sourceCmd+cmd[0]+':MODF:PHASE '+str(value)+'DEG')
            elif cmd[1] == 'Depth':
                VISA_Driver.writeAndLog(self,sourceCmd+cmd[0]+':DEPTH '+str(value)+'PCT')
            else:
                self.log('Unknown command received: '+cmd[1])
        elif quant.name.startswith('DC FM'):
            VISA_Driver.writeAndLog(self,sourceCmd+'DCFMNL')
        elif quant.name.endswith('Connected'):
            return value
        else:
            self.log('No quant name triggered')
            return VISA_Driver.performSetValue(self,quant,value,options,sweepRate)
        return value
    def performGetValue(self, quant, options ={}):
        couplingModes = ['Coupling CFRQAB','Coupling CFRQAC','Coupling RFLVAB','Coupling RFLVAC']
        self.log('Quant.name is: '+quant.name+' Get value')
        if quant.name[-1] == ')':
            #quant is source specific
            source = quant.name[-2]
            #Use sourceCmd before every source specific command
            sourceCmd = 'SOURCE '+source+'; :'
        if quant.name == 'Combiner mode':
            reply = VISA_Driver.askAndLog(self,'CMODE?')
            #return syntax is ':CMODE <*>'
            reply = reply.split(' ')[1]
            combos = ['A','B','C','AB','BC','AC','ABC','OFF']
            for comboValue in combos:
                #Need set so we get AB == BA, etc
                if set(reply) == set(comboValue):
                    return comboValue
            self.log('Coupling mode not found: '+reply)
        elif quant.name == 'Impedance':
            reply = VISA_Driver.askAndLog(self,'IMPEDANCE?')
            if reply.split(' ')[1] == 'Z50R':
                return '50 Ohms'
            else:
                return '75 Ohms'
        elif quant.name in couplingModes:
            mode = quant.name.split(' ')[1]
            reply = VISA_Driver.askAndLog(self,'COUPLING?')
            #Reply syntax: COUPLING:MODE CFRQAB,RFLVAC,...
            #get rid of 'COUPLING:MODE'
            reply = reply.split(' ')[1]
            #puts 2nd part into list of enabled modes
            reply = reply.split(',')
            if mode in reply:
                return True
            else:
                return False
        elif quant.name.startswith('Coupling'):
            cmd = quant.name.split(' ')
            """
            cmd[0] = 'coupling'
            cmd[1] = one of the coupling modes
            cmd[2] = MODE, HARM, SUBHARM, or OFFSET
            """
            cmdStr = 'COUPLING: '+cmd[1]+'?'
            reply = VISA_Driver.askAndLog(self,cmdStr)
            #Reply syntax: :COUPLING:CFRQAC:MODE SUBHARM;HARM 2;SUBHARM 6;OFFSET 2 
            replist = reply.split(';')
            if cmd[2] == 'MODE':
                #Split MODE and SUBHARM in reply[0], return SUBHARM
                return replist[0].split(' ')[1]
            elif cmd[2] == 'HARM':
                #split HARM and value in reply[1]
                return replist[1].split(' ')[1]
            elif cmd[2] == 'SUBHARM':
                #split SUBHARM and value in reply[2]
                return replist[2].split(' ')[1]
            elif cmd[2] == 'OFFSET':
                #Split offset and value in reply[3]
                return replist[3].split(' ')[1]
            else:
                self.log('Received invalid response: '+reply)
        elif quant.name.startswith('Carrier Frequency'):
            reply = VISA_Driver.askAndLog(self,sourceCmd+'CFRQ?')
            #reply syntax: :CFRQ:VALUE 1000000000.0;INC 25000.0
            reply = reply.split(';')[0]
            reply = reply.split(' ')[1]
            self.log('Carrier frequency: '+reply)
            return float(reply)
        elif quant.name.startswith('RF'):
            cmd = quant.name.split(' ')
            #cmd[1] = Output, Level, or Type
            #Reply syntax: :RFLV:UNITS DBM;TYPE PD;VALUE −103.5;INC 2.0;ON
            reply = VISA_Driver.askAndLog(self,sourceCmd+'RFLV?')
            reply = reply.split(';')
            if cmd[1] == 'Output':
                if reply[3] == 'ON':
                    return True
                else:
                    return False
            elif cmd[1] == 'Level':
                return reply[2].split(' ')[1]
            elif cmd[1] == 'Type':
                return reply[1].split(' ')[1]
            else:
                self.log('Quant not recognised: '+quant.name)
        elif quant.name.startswith('Modulation Control'):
            reply = VISA_Driver.askAndLog(self,sourceCmd+'MOD?')
            if reply.split(':')[-1] == 'ON':
                return True
            else:
                return False
        elif quant.name.startswith('Modulation mode'):
            reply = VISA_Driver.askAndLog(self,sourceCmd+'MODE?')
            #Reply syntax: :MODE AM,FM,PULSE
            #Remove ':MODE' component of reply
            reply = reply.split(' ')[1]
            #Separate activated modes into list
            reply = reply.split(',')
            if 'AM' in reply:
                if 'FM' in reply:
                    return 'AM & FM'
                elif 'PM' in reply:
                    return 'AM & PM'
                else:
                    return 'AM'
            elif 'FM' in reply:
                return 'FM'
            elif 'PM' in reply:
                return 'PM'
            elif 'FSK2L' in reply:
                return 'FSK2L'
            elif 'FSK4L' in reply:
                return 'FSK4L'
            else:
                self.log('No modulation mode active')
        elif quant.name[:2] in ['FM','PM','AM']:
            cmd = quant.name.split(' ')
            """
            cmd[0] = FM, FM1, FM2, PM, PM1, PM2, AM, AM1, or AM2
            cmd[1] = Status, Deviation, Source, Modulation, Waveform, Phase, (Depth for AM)
            """
            if cmd[1] == 'Status':
                reply = VISA_Driver.askAndLog(self,sourceCmd+cmd[0]+'?')
                #Reply syntax: :FM1:DEVN 1000.0;INT;OFF;INC 1000.0
                reply = reply.split(';')
                if reply[2] == 'OFF':
                    return False
                else:
                    return True
            elif cmd[1] == 'Deviation':
                reply = VISA_Driver.askAndLog(self,sourceCmd+cmd[0]+'?')
                #Reply syntax: :FM1:DEVN 25000.0;INT;ON;INC 1000.0
                reply = reply.split(';')
                return reply[0].split(' ')[1]
            elif cmd[1] == 'Source':
                reply = VISA_Driver.askAndLog(self,sourceCmd+cmd[0]+'?')
                #Reply syntax: :FM1:DEVN 25000.0;INT;ON;INC 1000.0
                reply = reply.split(';')
                comboDict = {'INT':'Internal','EXTAC':'External AC','EXTALC':'External ALC','EXTDC':'External DC'}
                return comboDict[reply[1]]
            elif cmd[1] == 'Modulation':
                reply = VISA_Driver.askAndLog(self,sourceCmd+cmd[0]+':MODF?')
                #Reply syntax: :FM1:MODF:VALUE 5750.00;SIN;INC 1000.00
                reply = reply.split(';')[0]
                return reply.split(' ')[1]
            elif cmd[1] == 'Waveform':
                reply = VISA_Driver.askAndLog(self,sourceCmd+cmd[0]+':MODF?')
                #Reply syntax: :FM1:MODF:VALUE 5750.00;SIN;INC 1000.00
                return reply.split(';')[1]
            elif cmd[1] == 'Phase':
                return 0 #No way to get this setting
            elif cmd[1] == 'Depth':
                reply = VISA_Driver.askAndLog(self,sourceCmd+cmd[0]+'?')
                #Reply syntax: :FM1:DEVN 25000.0;INT;ON;INC 1000.0
                reply = reply.split(';')
                return reply[0].split(' ')[1]
            else:
                self.log('Quant command not recognised: '+quant.name)
        elif quant.name.startswith('Pulse Modulation'):
            reply = VISA_Driver.askAndLog(self,sourceCmd+'PULSE?')
            #Reply syntax: :PULSE:ON/OFF
            #Remove ':MODE' component of reply
            if reply.endswith('ON'):
                return True
            else:
                return False
        else:
            self.log('quant.name not tringgered: '+quant.name)
            return VISA_Driver.performGetValue(self,quant,options)
    def performStopSweep(self,quant,options={}):
        VISA_Driver.writeAndLog(self,'SWEEP:HALT')
    def checkIfSweeping(self, quant, options={}): #Can't see any simple way to check
        self.log('Check sweep for: '+quant.name)
        carrierStatus = self.getValue('Source '+quant.name[-2]+' Connected')
        if carrierStatus:
            value1 = self.readValueFromOther(quant.name,options)
            self.wait(0.2)
            value2 = self.readValueFromOther(quant.name,options)
            if value2-value1 == 0:
                self.log('Check sweep returned False/no sweep')
                return False
            else:
                self.log('Check sweep returning True/sweeping')
                return True
        else:
            self.log('checkIfSweeping determined source '+quant.name[-2]+' not Connected')
            return False

if __name__ == '__main__':
    pass