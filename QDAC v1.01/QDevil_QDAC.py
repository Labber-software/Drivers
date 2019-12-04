# Labber driver for the QDevil QDAC voltage sources.
# Provided by QDevil 2019

import InstrumentDriver
from VISA_Driver import VISA_Driver
import numpy as np
import os.path
import qdac as qdac

VERSION = "1.01"
REQUIRED_QDACPY_VERSION = "1.22"

Voltageranges = {1:1,10:0}
Currentranges = {1e-6:1, 100e-6:0}
CurrentrangesInv = {1:1e-6, 100:100e-6}
Wavtranslate = {"Waveform":"Curvetype","Period":"Period","Repetitions":"Repetitions", "Dutycycle":"Dutycycle", "Steplength": "Step length", "Steps":"No. of steps","Trigger":"Trigger"}
Pultranslate = {"LowTime": "LowTime", "HighTime": "HighTime", "LowLevel": "LowValue", "HighLevel": "HighValue", "Repetitions":"PulseCount", "Trigger": "Trigger"}
Modetranslate = {"Mode":"Generator", "AmplitudeV":"Amplitude", "AmplitudeX": "Amplitude", "OffsetV": "Offset"}
Syntranslate = {"Source": "Generator", "Length":"Duration", "Delay":"Delay"}
AWGtranslate = {"Repetitions": "Repetitions", "Trigger":"Trigger"}
qdacmodels = ["QDAC 1, 24 Channels", "QDAC 1, 48 Channels"]

DoLogging = False

# Sub class of the qdac facilitating use of VISA driver coming from Labber
class labberqdac(qdac.qdac):
    def __init__(self, visaPort, verbose=False):
        super(labberqdac, self).__init__(visaPort, verbose)
        self.visaPort = visaPort

    def _readLine(self, failOnTimeout=True):
        out = self.visaPort.read(n_bytes=None, ignore_termination=False)
        return out.encode("utf-8")

    def _sendReceive(self, msg):
        self.visaPort.write( msg.decode("utf-8"), bCheckError=False )
        reply = self._readLine()
        return reply

    def _close(self):
        pass

class Driver(VISA_Driver):
    """ Implements a Labber interface to the QDevil QDAC """

# Helper functions
    def _readAWGfromfile(self, quant):
        filename = self.getValue('G9 File')
        if os.path.isfile(filename):
            try:
                signal = np.loadtxt(filename, dtype=float, delimiter='\t', usecols=[0])
            except:
                self.log("***ERROR: Could not read the specified AWG file: ", filename, level = 30)
                signal = np.zeros(1, dtype=float)
            finally:
                return signal
        else:
            self.log("***ERROR: The file does not exist", level = 30)
            return np.zeros(1, dtype=float)

    def _setVoltage(self, quant, command, chanNo, value):
        if DoLogging: self.log("set DC for ch: {}, voltage: {}".format(chanNo, float(value)), level=30)
        self.q.setDCVoltage(channel=chanNo, volts=float(value))
        return value

    def _setVoltageRange(self, quant, command, chanNo, value):
        if DoLogging: self.log("V range", command, " ", chanNo, " ", value, level=30)
        if int(self.getValue(command[0] + " Current-Range".format(chanNo))) == 100 and int(value) == 1:
            value = quant.getValue()
            self.log("***ERROR: Can not change voltage range to 1V when current range is 100 uA", level=30)
        else:
            self.q.setVoltageRange(channel=chanNo, theRange=float(value))
        return value

    def _setCurrentRange(self, quant, command, chanNo, value):
        if DoLogging: self.log("Cur range", command, " ", chanNo, " ", value, level=30)
        if int(self.getValue(command[0] + " Voltage-Range".format(chanNo))) == 1 and int(value) == 100:
            value = 1
            self.log("***ERROR: Can not change current range to 100 uA when voltage range is 1", level=30)
        else:
            currange = CurrentrangesInv[int(value)]
            self.q.setCurrentRange(channel=chanNo, theRange=float(currange))
        return value

    def _Apply(self, quant, command, chanNo, value):
        mode = int(self.getValueIndex("CH{:02d} Mode".format(chanNo)))
        if mode < 9:
            amplitude = self.getValue("CH{:02d} AmplitudeV".format(chanNo))
        else:
            amplitude = self.getValue("CH{:02d} AmplitudeX".format(chanNo))
        offset = self.getValue("CH{:02d} OffsetV".format(chanNo))
        self.q.setChannelOutput(channel=chanNo, generator=mode, amplitude=amplitude, offset=offset)
        return value

    def _setSyncPort(self, quant, command, synNo, value):
        genNo = int(self.getValueIndex("Syn{} Source".format(synNo)))
        length = int(self.getValue("Syn{} Length".format(synNo)))
        delay = int(self.getValue("Syn{} Delay".format(synNo)))
        if DoLogging: self.log("Syn {}, Source: {} pulse length: {}".format(synNo, genNo, length), level=30)
        self.q.setSyncOutput(syncChannel=synNo, generator=genNo, delay=delay, pulseLength=length)
        return value

    def _runWaitPushedGen1_8(self, quant, command, genNo, value):
        waveform = self.getValueIndex("G{} Waveform".format(genNo)) + 1
        period = self.getValue("G{} Period".format(genNo))
        steplength = self.getValue("G{} Steplength".format(genNo))
        nosteps = self.getValue("G{} Steps".format(genNo))
        dutycycle = self.getValue("G{} Dutycycle".format(genNo))
        repetitions = self.getValue("G{} Repetitions".format(genNo))
        trigger = self.getValueIndex("G{} Trigger".format(genNo))
        if waveform < 4:
            self.q.defineFunctionGenerator(genNo, waveform=waveform, period=period, dutycycle=dutycycle,
                                           repetitions=repetitions, trigger=trigger)
        elif waveform == 4:
            self.q.defineFunctionGenerator(genNo, waveform=waveform, period=steplength, dutycycle=nosteps,
                                           repetitions=repetitions, trigger=trigger)
        return value

    def _runWaitPushedPulseTrain(self, quant, command, genNo, value):
        lowtime = self.getValue("G{} LowTime".format(genNo))
        hightime = self.getValue("G{} HighTime".format(genNo))
        lowlevel = self.getValue("G{} LowLevel".format(genNo))
        highlevel = self.getValue("G{} HighLevel".format(genNo))
        repetitions = self.getValue("G{} Repetitions".format(genNo))
        trigger = self.getValueIndex("G{} Trigger".format(genNo))
        self.q.definePulsetrain(lowDuration=lowtime, highDuration=hightime, lowVolts=lowlevel, highVolts=highlevel,
                                repetitions=repetitions, trigger=trigger)
        return value

    def _runWaitPushedAWG(self, quant, command, genNo, value):
        AWGsignal = self.getValueArray("G{} Signal".format(genNo)).tolist()
        repetitions = self.getValue("G{} Repetitions".format(genNo))
        trigger = self.getValueIndex("G{} Trigger".format(genNo))
        if DoLogging: self.log("AWG length: {}, repetitions: {}, trigger: {}".format(len(AWGsignal), repetitions, trigger),
                               level=30)
        if len(AWGsignal) > 1:
            self.q.defineAWG(samples=AWGsignal, repetitions=repetitions, trigger=trigger)
        else:
            self.log("***ERROR: AWG sequence not defined", level=30)
        return value

    def _triggerPushed(self, quant, command, trigNo, value):
        if DoLogging: self.log("Trigger fire: {}".format(trigNo), level=30)
        self.q.executeTrigger(trigNo)
        return value

    def _getModeConfig(self, quant, command, chanNo):
        settings = self.q.getChannelOutput(chanNo)
        if DoLogging:
            for key, val in settings.items(): self.log(key + " " + format(val), level=30)
        if command[1] == "Mode":
            for quantdriver, quantqdac in Modetranslate.items():  # When reading Mode read all parameters as they might have changed, May be obsolete - think about it
                if DoLogging: self.log("We have got " + quantdriver, level=30)  # May be obsolete - think about it
                if quantqdac in settings:
                    if DoLogging: self.log("Found it in settings", level=30)
                    self.setValue(command[0] + " " + quantdriver, settings[quantqdac])
            return settings[Modetranslate[command[1]]]
        else:
            if Modetranslate[command[1]] in settings:
                return settings[Modetranslate[command[1]]]

    def _getSyncConfig(self, quant, command, synNo):
        if DoLogging: self.log("Syn no " + format(synNo), level=30)
        settings = self.q.getSyncOutput(synNo)
        if command[1] in Syntranslate:
            if Syntranslate[command[1]] in settings:
                if DoLogging: self.log(
                    "Translated: " + Syntranslate[command[1]] + " {}".format(settings[Syntranslate[command[1]]]), level=30)
                return int(settings[Syntranslate[command[1]]])

    def _getGenerator1_8Config(self, quant, command, genNo):
        settings = self.q.getFunctionGenerator(genNo)
        if command[1] == "Waveform":
            return settings[Wavtranslate[command[1]]] - 1
        else:
            if Wavtranslate[command[1]] in settings:
                value = settings[Wavtranslate[command[1]]]
                return value

    def _getPulseTrainConfig(self, quant, command, genNo):
        settings = self.q.getPulsetrain()
        if command[1] in Pultranslate:
            if Pultranslate[command[1]] in settings:
                value = settings[Pultranslate[command[1]]]
                return value

    def _getAWGConfig(self, quant, command, genNo):
        if command[1] == "Signal":
            AWGsignal = self._readAWGfromfile(quant)
            if AWGsignal.size > 8000:
                self.log("* ERROR * AWG signal is exceeding 8000 points and has been truncated. ", level=30)
            trace = quant.getTraceDict(AWGsignal[:8000], t0=0.0, dt=0.001)
            return trace
        else:
            settings = self.q.getAwg()
            if command[1] in AWGtranslate and AWGtranslate[command[1]] in settings:
                value = settings[AWGtranslate[command[1]]]
                return value

# The actual VISA driver methods
    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        self.log("Opening QDAC", options, level=30)
        if float(qdac.VERSION) < float(REQUIRED_QDACPY_VERSION):
            raise Exception("This driver requires qdac.py version {} or compatible".format(REQUIRED_QDACPY_VERSION))
        if not hasattr(labberqdac(self), "Virtual"):        # For off line development we have a virtual qdac.py
            VISA_Driver.performOpen(self, options=options)
            self.log("Connected to physical device", level = 30)
        self.q = labberqdac(self)
        # We are not flushing, as we the buffer is expected to be empty. Problem might be if the user turns on the QDAC after Labber is started. to be empty might need a flush here
        N = self.q.getNumberOfChannels()
        self.log("Channels: {}".format(N), level = 30)
        # Set model string to actual model
        if N==24:
            self.setModel(qdacmodels[0])
        if N==48:
            self.setModel(qdacmodels[1])
        return

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        self.q._close()
        if not hasattr(labberqdac(self), "Virtual"):
            VISA_Driver.performClose(self, bError, options=options)
        return

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # just return the value
        if DoLogging: self.log("performSetValue: "+quant.name + " "+format(value), level = 30)
        command = quant.name.split()
        print("Set value ", command)
        try:
            if len(command) > 1:
                if len(command[0])>3:
                    if command[0][0:2]=="CH":
                        chanNo = int(command[0][2:])
                        if command[1] == "Voltage":
                            return self._setVoltage(quant, command, chanNo, value)
                        elif command[1] == "Voltage-Range":
                            return self._setVoltageRange(quant, command, chanNo, value)
                        elif command[1] == "Current-Range":
                            return self._setCurrentRange(quant, command, chanNo, value)
                        elif command[1] == "Apply":
                            return self._Apply(quant, command, chanNo, value)
                    elif command[0][0:3] == "Syn":
                        quant.setValue(value)  # Set whatever value is being set so that we can read it in teh helper function
                        synNo = int(command[0][3:])
                        return self._setSyncPort(quant, command, synNo, value)
                elif len(command[0]) > 1:
                    # Push button handlers
                    if command[0][0] == "G":
                        genNo = int(command[0][1:])
                        if command[1] == "Run-Wait":
                            if genNo in range(1, 9):
                                return self._runWaitPushedGen1_8(quant, command, genNo, value)
                            elif genNo == 10:
                                return self._runWaitPushedPulseTrain(quant, command, genNo, value)
                            elif genNo == 9:
                                return self._runWaitPushedAWG(quant, command, genNo, value)
                    if command[0][0] == "T":
                        trigNo = int(command[0][1:])
                        if command[1] == "Fire":
                            return self._triggerPushed(quant, command, trigNo, value)
        except Exception as exceptmsg:
                self.log("***ERROR(qdac.py): {}".format(exceptmsg), level=30)  # yes, really bad style to catch all exceptions when we whould only catch those from the qdac, but that's the way it is for now
                return quant.getValue()  # return the previous value
        if DoLogging: self.log("Set handler not defined: ", command, level=30)
        return value

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # proceed depending on quantity
        if DoLogging: self.log("performGetValue: "+quant.name , level = 30)
        command = quant.name.split()
        if DoLogging: self.log("Command0:  "+command[0] , level = 30)
        try:
            if len(command[0]) > 3:
                if DoLogging: self.log("command len: {}".format(len(command[0])   ), level=30)
                if command[0][0:2] == "CH":
                    chanNo = int(command[0][2:])
                    if DoLogging: self.log("Chan no : {}".format(chanNo), level=30)
                    if command[1] == "Current":
                        return self.q.getCurrentReading(chanNo)
                    elif command[1] == "Voltage":
                        return self.q.getDCVoltage(chanNo)
                    elif command[1] == "Voltage-Range":
                        return Voltageranges[self.q.getVoltageRange(chanNo)]
                    elif command[1] == "Current-Range":
                        return Currentranges[self.q.getCurrentRange(chanNo)]
                    elif command[1] in Modetranslate:
                        return_value = self._getModeConfig(quant, command, chanNo)
                        if return_value is not None: return return_value
                elif command[0][0:3] == "Syn":
                    synNo = int(command[0][3:])
                    return_value = self._getSyncConfig(quant, command, synNo)
                    if return_value is not None: return return_value
            if len(command[0]) > 1:
                if command[0][0] == "G":
                    genNo = int(command[0][1:])
                    if genNo in range(1, 9):
                        return_value = self._getGenerator1_8Config(quant, command, genNo)
                        if return_value is not None: return return_value
                    if genNo == 9:
                        return_value = self._getAWGConfig(quant, command, genNo)
                        if return_value is not None: return return_value
                    if genNo == 10:
                        return_value = self._getPulseTrainConfig(quant, command, genNo)
                        if return_value is not None: return return_value
        except Exception as exceptmsg:
            self.log("***ERROR(qdac.py): {}".format(exceptmsg), level=30)  # yes, bad style to catch all exceptions when we whoudl only catch those rom the qdac, but that's teh way it is for now
            return quant.getValue()  # return the previous value

        # for other quantities, just return current value of control
        if DoLogging: self.log("Get handler not defined: ", command, level=30)
        return quant.getValue()


