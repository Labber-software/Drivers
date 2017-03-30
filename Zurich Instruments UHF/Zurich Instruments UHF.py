import InstrumentDriver
import numpy as np
import os, sys, inspect, re, math

#Some stuff to import ziPython from a relative path independent from system wide installations
cmd_folder = os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0]))
if cmd_folder not in sys.path:
    sys.path.insert(0, cmd_folder)

import zhinst.utils as zi

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class wraps the ziPython API"""
    

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        
        try:
            self.ziConnection = zi.autoConnect(8004, 4)
        except:
            raise InstrumentDriver.CommunicationError("Could not connect to Zurich Instruments Data Server. Is it running?")
            return

        if self.comCfg.address == "":
            self.device = zi.autoDetect(self.ziConnection)
            self.log("Autodetected Zurich Instruments device \"" + self.device + "\". Use the address field to set a specific device.")
        else:
            self.device = self.comCfg.address
        
        try:
            devtype = self.ziConnection.getByte(str('/%s/features/devtype' % self.device))
        except:
            raise InstrumentDriver.CommunicationError("Device " + self.device + " not found.")
            return
            
        if re.match('UHF', devtype):
            self.log("Zurich Instruments device \"" + self.device + "\" has been accepted by the driver.")
        else:
            self.log("Zurich Instruments device \"" + self.device + "\" has been rejected by the driver.", 50)
            raise InstrumentDriver.CommunicationError("Device " + self.device + " is not an UHF lock-in")
            return
        
        #Check Options
        devoptions = self.ziConnection.getByte(str('/%s/features/options' % self.device))
        detectedOptions = []
        if re.search('MOD', devoptions):
            detectedOptions.append("MOD")
        self.instrCfg.setInstalledOptions(detectedOptions)

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        pass


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        #Simple booleans
        if quant.name in ['SigOut1On', 'SigOut2On'] + \
                        ['SigIn1AC', 'SigIn2AC'] + \
                        ['Mod1On', 'Mod2On'] + \
                        ['Out'+str(x+1)+'SigOut' + str(y+1) + 'On' for x in range(8) for y in range(2)] + \
                        ['Demod'+str(x+1)+'On' for x in range(8)]:
            self.ziConnection.setInt(str(quant.get_cmd % self.device), 1 if value else 0)
        #Simple floating points
        elif quant.name in ['SigIn1Range', 'SigIn2Range'] + \
                        ['Oscillator'+str(x+1)+'Frequency' for x in range(8)] + \
                        ['Out'+str(x+1)+'SigOut' + str(y+1) + 'Amp' for x in range(8) for y in range(2)] + \
                        ['SigOut1Offset', 'SigOut2Offset'] + \
                        ['Demod'+str(x+1)+'RefPhase' for x in range(8)] + \
                        ['Demod'+str(x+1)+'TC' for x in range(8)] + \
                        ['Demod'+str(x+1)+'SampleRate' for x in range(8)] + \
                        ['Mod1Phase', 'Mod2Phase'] + \
                        ['Mod1SB1Phase', 'Mod2SB1Phase'] + \
                        ['Mod1SB2Phase', 'Mod2SB2Phase'] + \
                        ['Mod1TC', 'Mod2TC'] + \
                        ['Mod1SB1TC', 'Mod2SB1TC'] + \
                        ['Mod1SB2TC', 'Mod2SB2TC'] + \
                        ['Mod1OutAmp', 'Mod2OutAmp'] + \
                        ['Mod1SB1OutAmp', 'Mod2SB1OutAmp'] + \
                        ['Mod1SB2OutAmp', 'Mod2SB2OutAmp']:
            self.ziConnection.setDouble(str(quant.get_cmd % self.device), float(value))
        #Combos (Oscillator-selector for demodulators and Modulator mode)
        elif quant.name in ['Demod'+str(x+1)+'Osc' for x in range(8)] + \
                            ['Mod1Mode', 'Mod2Mode'] + \
                            ['Mod1SB1Mode', 'Mod2SB1Mode'] + \
                            ['Mod1SB2Mode', 'Mod2SB2Mode'] + \
                            ['Mod1Osc', 'Mod2Osc'] + \
                            ['Mod1SB1Osc', 'Mod2SB1Osc'] + \
                            ['Mod1SB2Osc', 'Mod2SB2Osc']:
            # convert input to integer
            intValue = int(quant.getCmdStringFromValue(value))
            self.ziConnection.setInt(str(quant.get_cmd % self.device), intValue)
        return value


    def performGetValue(self, quant, options={}):
        if self.isFirstCall(options):
            self.resultBuffer = {}
            self.traceBuffer = {}
        """Perform the Get Value instrument operation"""
        # proceed depending on quantity
        #Simple booleans
        if quant.name in ['SigOut1On', 'SigOut2On'] + \
                        ['SigIn1AC', 'SigIn2AC'] + \
                        ['Mod1On', 'Mod2On'] + \
                        ['Out'+str(x+1)+'SigOut' + str(y+1) + 'On' for x in range(8) for y in range(2)] + \
                        ['Demod'+str(x+1)+'On' for x in range(8)]:
            return (self.ziConnection.getInt(str(quant.get_cmd % self.device)) > 0)
        #Simple floating points
        elif quant.name in ['SigIn1Range', 'SigIn2Range'] + \
                        ['Oscillator'+str(x+1)+'Frequency' for x in range(8)] + \
                        ['Out'+str(x+1)+'SigOut' + str(y+1) + 'Amp' for x in range(8) for y in range(2)] + \
                        ['SigOut1Offset', 'SigOut2Offset'] + \
                        ['Demod'+str(x+1)+'RefPhase' for x in range(8)] + \
                        ['Demod'+str(x+1)+'TC' for x in range(8)] + \
                        ['Demod'+str(x+1)+'SampleRate' for x in range(8)] + \
                        ['Mod1Phase', 'Mod2Phase'] + \
                        ['Mod1SB1Phase', 'Mod2SB1Phase'] + \
                        ['Mod1SB2Phase', 'Mod2SB2Phase'] + \
                        ['Mod1TC', 'Mod2TC'] + \
                        ['Mod1SB1TC', 'Mod2SB1TC'] + \
                        ['Mod1SB2TC', 'Mod2SB2TC'] + \
                        ['Mod1OutAmp', 'Mod2OutAmp'] + \
                        ['Mod1SB1OutAmp', 'Mod2SB1OutAmp'] + \
                        ['Mod1SB2OutAmp', 'Mod2SB2OutAmp']:
            return self.ziConnection.getDouble(str(quant.get_cmd % self.device))
        #Read-out channels of demodulator
        elif quant.name in ['Demod'+str(x+1)+'R' for x in range(8)] + \
                        ['Demod'+str(x+1)+'phi' for x in range(8)] + \
                        ['Demod'+str(x+1)+'X' for x in range(8)] + \
                        ['Demod'+str(x+1)+'Y' for x in range(8)]:
            if quant.get_cmd in self.resultBuffer.keys():
                data = self.resultBuffer[quant.get_cmd]
            else:
                data = self.ziConnection.getSample(str(quant.get_cmd % self.device))
                self.resultBuffer[quant.get_cmd] = data
            channel = quant.name[6:]
            if channel == "X":
                return data["x"][0]
            elif channel == "Y":
                return data["y"][0]
            elif channel == "R":
                return math.sqrt(data["x"][0]**2 + data["y"][0]**2)
            elif channel == "phi":
                return math.degrees(math.atan2(data["y"][0], data["x"][0]))
            return float('nan')
        #Trace channels of demodulator
        elif quant.name in ['TraceDemod'+str(x+1)+'R' for x in range(8)] + \
                        ['TraceDemod'+str(x+1)+'phi' for x in range(8)] + \
                        ['TraceDemod'+str(x+1)+'X' for x in range(8)] + \
                        ['TraceDemod'+str(x+1)+'Y' for x in range(8)]:
            if (quant.get_cmd % self.device) in self.traceBuffer.keys():
                data = self.traceBuffer[quant.get_cmd % self.device]
            else:
                self.ziConnection.sync()
                self.ziConnection.flush()
                rec = self.ziConnection.record(2*self.getValue("TraceLength"), 500)
                rec.set('trigger/0/type', 0)
                rec.set('trigger/0/duration', self.getValue("TraceLength"))
                # Subscribe to all active modulators
                for i in range(8):
                    if self.getValue('Demod'+str(i+1)+"On"):
                        path = "/%s/demods/%d/sample" % (self.device, i)
                        rec.subscribe(path)
                rec.execute()
                rec.trigger()
                if not self.getValue("TraceStep"):
                    self.wait(self.getValue("TraceLength"))
                else:
                    self.wait(self.getValue("TraceStepDelayA"))
                    self.log("Setpoint A: " + str(self.getValue("TraceStepSetpointA")))
                    self.ziConnection.setDouble(str(self.instrCfg.getQuantity('TraceStepChannel').getCmdStringFromValue(self.getValue("TraceStepChannel")) % self.device), self.getValue("TraceStepSetpointA"))
                    self.wait(self.getValue("TraceStepDelayB"))
                    self.log("Setpoint B: " + str(self.getValue("TraceStepSetpointB")))
                    self.ziConnection.setDouble(str(self.instrCfg.getQuantity('TraceStepChannel').getCmdStringFromValue(self.getValue("TraceStepChannel")) % self.device), self.getValue("TraceStepSetpointB"))
                while not rec.finished():
                    self.wait(0.05)
                self.traceBuffer = rec.read(True)
                self.clockbase = float(self.ziConnection.getInt(str('/%s/clockbase' % self.device)))
                data = self.traceBuffer[quant.get_cmd % self.device][0]
                self.log(data)
                rec.finish()
                rec.clear()
            data = self.traceBuffer[quant.get_cmd % self.device][0]
            self.log(data)
            dt = (data['timestamp'][-1] - data['timestamp'][0])/self.clockbase/(len(data['timestamp'])-1)
            channel = quant.name[11:]
            nPoints = self.getValue("TraceLength")*self.getValue("Demod"+quant.name[10]+"SampleRate")
            if channel == "X":
                signal = quant.getTraceDict(data["x"][:nPoints], t0=0.0, dt=dt)
                return signal
            elif channel == "Y":
                signal = quant.getTraceDict(data["y"][:nPoints], t0=0.0, dt=dt)
                return signal
            elif channel == "R":
                signal = quant.getTraceDict(np.sqrt(np.array(data["x"][:nPoints])**2 + np.array(data["y"][:nPoints])**2), t0=0.0, dt=dt)
                return signal
            elif channel == "phi":
                signal = quant.getTraceDict(np.degrees(np.arctan2(np.array(data["y"][:nPoints]), np.array(data["x"][:nPoints]))), t0=0.0, dt=dt)
                return signal
            return quant.getTraceDict([])
        #Combos (Oscillator-selector for demodulators and Modulator mode)
        elif quant.name in ['Demod'+str(x+1)+'Osc' for x in range(8)] + \
                            ['Mod1Mode', 'Mod2Mode'] + \
                            ['Mod1SB1Mode', 'Mod2SB1Mode'] + \
                            ['Mod1SB2Mode', 'Mod2SB2Mode'] + \
                            ['Mod1Osc', 'Mod2Osc'] + \
                            ['Mod1SB1Osc', 'Mod2SB1Osc'] + \
                            ['Mod1SB2Osc', 'Mod2SB2Osc']:
            return quant.getValueFromCmdString(self.ziConnection.getInt(str(quant.get_cmd % self.device)))
        # for other quantities, just return current value of control
        return quant.getValue()


