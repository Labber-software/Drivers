# qdac.py
# Copyright QDevil ApS, 2018 and 2019
try:
    import serial
except:
    pass
import time

VERSION = "1.22"
class Waveform:
    # Enum-like class defining the built-in waveform types
    sine = 1
    square = 2
    triangle = 3
    staircase = 4
    all = [sine, square, triangle, staircase]

class Generator:
    # Enum-like class defining the waveform generators
    DC = 0
    generator1 = 1
    generator2 = 2
    generator3 = 3
    generator4 = 4
    generator5 = 5
    generator6 = 6
    generator7 = 7
    generator8 = 8
    AWG = 9
    pulsetrain = 10
    functionGenerators = [generator1, generator2, generator3, generator4, generator5, generator6,
           generator7, generator8]
    syncGenerators = functionGenerators + [AWG, pulsetrain]
    all = [DC] + syncGenerators

class qdac():
    # Main QDAC instance class
    noChannel = 0
    debugMode = False

    def __init__(self, port, verbose=False):
        # Constructor
        # port: Serial port for QDAC
        # verbose: Print serial communication during operation. Useful for debugging
        self.port = port
        self.verbose = verbose
        self.channelNumbers = range(1, 49)
        self.syncChannels = range(1, 6)
        self.voltageRange = {ch: 10.0 for ch in self.channelNumbers} # Assumes that QDAC has power-on values
        self.currentRange = {ch: 100e-6 for ch in self.channelNumbers} # Assumes that QDAC has power-on values
        self.triggerRange = range(0, 10)

    def __enter__(self):
        self.sport = serial.Serial(port=self.port, baudrate=460800, bytesize=serial.EIGHTBITS,
                                   parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=0.5)
        return self

    def __exit__(self, type, value, traceback):
        self.sport.close()

    def flush(self):
        # Purges the serial port input buffer
        while True:
            response = self.sport.read(1)
            if not response:
                break

    def getSerialNumber(self):
        # Returns the QDAC unit serial number
        reply = self._checkForError(self._sendReceive(b'sernum'))
        try:
            return reply.decode("utf-8")
        except:
            raise Exception("Error response from QDAC: <%s>" % reply)

    def getNumberOfBoards(self):
        # Returns number of 8-channel boards
        reply = self._checkForError(self._sendReceive(b"boardNum"))
        try:
            self.numBoards = int(reply.split(b":", 1)[1])
            self.channelNumbers = range(1, self.numBoards*8+1)
            self.syncChannels = range(1, self.numBoards)
            return self.numBoards
        except:
            raise Exception("Error response from QDAC: <%s>" % reply)

    def getNumberOfChannels(self):
        # Returns number of channels on the QDAC unit
        return self.getNumberOfBoards()*8

    def setVoltageRange(self, channel, theRange):
        # Set the voltage output range of a QDAC channel
        # range must be 1.0 or 10.0 (unit is V)
        if self.debugMode == False:
            self._validateChannel(channel)
        currentRange = self.getCurrentRange(channel)
        if theRange == 10.0:
            rangeFlag = 0
        elif theRange == 1.0:
            rangeFlag = 1
        else:
            raise Exception("Invalid voltage range %d" % theRange)
        if((currentRange == 100e-6) and (theRange == 1.0)):
            raise Exception("1V range not valid in the 100uA current range")
        reply = self._checkForError(self._sendReceive(b"vol %d %d" % (channel, rangeFlag)))
        rangeFlag = float(reply.split(b": X", 1)[1].split(b",")[0])
        if rangeFlag == 1:
            theRange = 10.0
        elif rangeFlag == 0.1:
            theRange = 1.0
        else:
            raise Exception("Invalid voltage range %d received from QDAC" % rangeFlag)
        self.voltageRange[channel] = theRange
        return theRange


    def getVoltageRange(self, channel):
        # Get the voltage output range of a QDAC channel
        # range is returned as 1.0 or 10.0 (unit is V)
        if self.debugMode == False:
            self._validateChannel(channel)
        reply = self._checkForError(self._sendReceive(b"vol %d" % (channel)))
        rangeFlag = float(reply.split(b": X", 1)[1].split(b",")[0])
        if rangeFlag == 1:
            theRange = 10.0
        elif rangeFlag == 0.1:
            theRange = 1.0
        else:
            raise Exception("Invalid voltage range %d received from QDAC" % rangeFlag)
        self.voltageRange[channel] = theRange
        return theRange

    def setCurrentRange(self, channel, theRange):
        # Set the current sensing range of a QDAC channel
        # range must be 1e-6 or 100e-6 (unit is A)
        if self.debugMode == False:
            self._validateChannel(channel)
        if theRange == 1e-6:
            rangeFlag = 0
        elif theRange == 100e-6:
            rangeFlag = 1
        else:
            raise Exception("Invalid current range %e" % theRange)
        self.currentRange[channel] = theRange
        reply = self._checkForError(self._sendReceive(b"cur %d %d" % (channel, rangeFlag))).decode("utf-8")
        rangeFlag = reply.split(": ", 1)[1].split()[0]
        if rangeFlag == b"Low":
            theRange = 1e-6
        elif rangeFlag == b"High":
            theRange = 100e-6
        return theRange

    def getCurrentRange(self, channel):
        # Get the current sensing range of a QDAC channel
        # range is returned as 1e-6 or 100e-6 (unit is A)
        if self.debugMode == False:
            self._validateChannel(channel)
        reply = self._checkForError(self._sendReceive(b"cur %d" % (channel)))
        rangeFlag = reply.split(b": ", 1)[1].split()[0]
        if rangeFlag == b"Low":
            theRange = 1e-6
        elif rangeFlag == b"High":
            theRange = 100e-6
        else:
            raise Exception("Invalid current range %d received from QDAC" % rangeFlag)
        self.currentRange[channel] = theRange
        return theRange

    def getDCVoltage(self, channel):
        # Gets the DC voltage that is currently set a QDAC channel
        # This only works if setChannelOutput has been set to Generator.DC, which is the power-on setting!!
        if self.debugMode == False:
            self._validateChannel(channel)
        reply = self._checkForError(self._sendReceive(b"set %d" % channel))
        try:
            return float(reply.split(b":", 1)[1].split()[1])
        except:
            raise Exception("Error response from QDAC: <%s>" % reply)

    def setDCVoltage(self, channel, volts):
        # Set the immediate DC voltage of a QDAC channel
        # This only works if setChannelOutput has been set to Generator.DC, which is the power-on setting!!
        if self.debugMode == False:
            self._validateChannel(channel)
            self._validateVoltage(channel, volts)
        reply = str(self._checkForError(self._sendReceive(b"set %d %e" % (channel, volts))).decode("utf-8"))
        try:
            analog =  float(reply.split("Output:")[1].split("(")[0].strip(" "))
            digital = int(reply.split("(")[1].split(")")[0])
            return { "Voltage": analog, "Digital": digital}
        except:
            raise Exception("Error response from QDAC: <%s>" % reply)

    def setRawDAC(self, channel, dacValue):
        # Sets the DAC output of a channel as a raw integer
        # value range from -524288 to 524287
        if dacValue < -524288 or dacValue > 524287:
            raise Exception("Invalid dac value: %d" % dacValue)
        reply = str(self._checkForError(self._sendReceive(b"dac %d %d" % (channel, dacValue))).decode("utf-8"))
        try:
            return int(reply.split("Digital Output:")[1].split("on Channel:")[0].strip(" "))
        except:
            raise Exception("Error response from QDAC: <%s>" % reply)

    def getRawDAC(self, channel):
        # Gets the DAC output of a channel as a raw integer
        # value range from -524288 to 524287
        self._validateChannel(channel)
        reply = self._checkForError(self._sendReceive(b"dac %d" % channel))
        try:
            return int(reply.split(b":")[1].split()[1])
        except:
            raise Exception("Error response from QDAC: <%s>" % reply)

    def setCalibrationChannel(self, channel):
        # Connect a QDAC channel to the Calibration output. Useful for testing the output performance
        # Set channel to 0 to disconnect all channels from the Calibration output
        if self.debugMode == False:
            if channel != qdac.noChannel:
                self._validateChannel(channel)
        reply = self._checkForError(self._sendReceive(b"cal %d" % channel)).decode("utf-8")
        return int(reply.split(':')[1].strip())

    def getCalibrationChannel(self):
        return int(self._sendReceive(b"cal").decode("utf-8").split(':')[1].strip())

    def readTemperature(self, board, position):
        # Read the temperature in Celsius inside the QDAC at different positions
        # Board: 0-5
        # Channel: 0-2
        # board 0 is channel 1-8, board 1 is channel 9-16, etc.
        if self.debugMode == False:
            if board not in [0,1,2,3,4,5] or position not in [0,1,2]:
                raise Exception("readTemperature: Invalid board %d or position %d" % (board, position))
        reply = self._checkForError(self._sendReceive(b"tem %d %d" % (board, position)))
        try:
            return float(reply.split(b":", 1)[1])
        except:
            raise Exception("Error response from QDAC: <%s>" % reply)

    def defineFunctionGenerator(self, generator, waveform, period, dutycycle=50, repetitions=-1, trigger=0):
        # Define a function generator
        # generator: Generator.generator1, ..., Generator.generator8
        # waveform: Waveform.sine, Waveform.square, Waveform.triangle
        # period//step length: Number of samples in waveform period/length of single stap in staircase
        # dutycycle/no. of steps: 0-100, used for square and triangle waveforms to define shap/ number of steps in staircase
        # repetitions: How many times the waveform is repeated. -1 means infinite
        # trigger: trigger source number, if this value exist, generator will not start until triggered
        # Note: The amplitude is always max. range of the channel. Set the amplitude in setChannelOutput
        if generator not in Generator.functionGenerators:
            raise Exception("Invalid generator number (must be 1-8): %d" % generator)
        if waveform not in Waveform.all:
            raise Exception("Invalid waveform: %d" % waveform)
        if period < 1:
            raise Exception("Invalid waveform period: %d" % period)
        if repetitions < -1 or repetitions > 0x7FFFFFFF:
            raise Exception("Invalid number of repetitions: %d" % repetitions)
        if dutycycle < 0 or dutycycle > 100:
            raise Exception("Invalid dutycycle: %f" % dutycycle)
        if trigger < 0 or trigger > 10:
            raise Exception("Invalid trigger number: %d" % trigger)
        str = ''
        returnValue = {}
        if(waveform == Waveform.sine):
            str = self._checkForError(self._sendReceive(b"fun %d %d %f %d %d" % (generator, waveform, period, repetitions, trigger))).decode("utf-8")
            period = float(str.split('Period:')[1].split('Repetitions')[0].replace(',', ''))
            returnValue.update({"Period": period})
            curveType = int(str.split('Curvetype:')[1].split('Period')[0].replace(',', ''))

        if (waveform == Waveform.triangle or waveform == Waveform.square):
            str = self._checkForError(self._sendReceive(
                b"fun %d %d %d %f %d %d" % (generator, waveform, period, dutycycle, repetitions, trigger))).decode("utf-8")
            period = float(str.split('Period:')[1].split('Dutycycle')[0].replace(',', ''))
            dutyCycle = float(str.split('Dutycycle:')[1].split('Repetitions:')[0].replace(',', ''))
            returnValue.update({"Dutycycle": dutyCycle})
            returnValue.update({"Period": period})
            curveType = int(str.split('Curvetype:')[1].split('Period')[0].replace(',', ''))

        if (waveform == Waveform.staircase):
            str = self._checkForError(self._sendReceive(
                b"fun %d %d %d %f %d %d" % (generator, waveform, period, dutycycle, repetitions, trigger))).decode("utf-8")
            stepLength = int(str.split('Step length:')[1].split('No. of steps')[0].replace(',', ''))
            returnValue.update({"Step length": stepLength})
            noOfSteps = int(str.split('No. of steps:')[1].split('Repetitions:')[0].replace(',', ''))
            returnValue.update({"No. of steps": noOfSteps})
            curveType = int(str.split('Curvetype:')[1].split('Step length')[0].replace(',', ''))


        repetitionRate = int(str.split('Repetitions:')[1].split('Trigger')[0].replace(',', ''))
        trigger = int(str.split('Trigger:')[1])

        returnValue.update({"Repetitions": repetitionRate})
        returnValue.update({"Curvetype": curveType})
        returnValue.update({"Trigger": trigger})
        return returnValue

    def getFunctionGenerator(self, generator):
        if not self.debugMode:
            if generator not in Generator.functionGenerators:
                raise Exception("Invalid generator number (must be 1-8): %d" % generator)
        str = self._checkForError(self._sendReceive(b"fun %d" % generator)).decode("utf-8")
        curveType = ''
        if("Period" in str):
            curveType =  int(str.split('Curvetype:')[1].split('Period')[0].replace(',', ''))
        elif("Step length" in str ):
            curveType = int(str.split('Curvetype:')[1].split('Step length')[0].replace(',', ''))

        returnValue = {}
        if (curveType == Waveform.sine):
            period = float(str.split('Period:')[1].split('Repetitions:')[0].replace(',', ''))
            returnValue.update({"Period": period})

        if (curveType == Waveform.triangle or curveType == Waveform.square):
            period = float(str.split('Period:')[1].split('Dutycycle')[0].replace(',', ''))
            dutyCycle = float(str.split('Dutycycle:')[1].split('Repetitions:')[0].replace(',', ''))
            returnValue.update({"Dutycycle": dutyCycle})
            returnValue.update({"Period": period})

        if (curveType == Waveform.staircase):
            stepLength = int(str.split('Step length:')[1].split('No. of steps')[0].replace(',', ''))
            returnValue.update({"Step length": stepLength})
            noOfSteps = int(str.split('No. of steps:')[1].split('Repetitions:')[0].replace(',', ''))
            returnValue.update({"No. of steps": noOfSteps})

        repetitionRate = int(str.split('Repetitions:')[1].split('Trigger')[0].replace(',', ''))
        trigger = int(str.split('Trigger:')[1])

        returnValue.update({"Repetitions": repetitionRate})
        returnValue.update({"Curvetype": curveType})
        returnValue.update({"Trigger": trigger})
        return returnValue

    def definePulsetrain(self, lowDuration, highDuration, lowVolts, highVolts, repetitions=-1, trigger=0):
        # Define a pulse train function generator
        # The generator is always Generator.pulsetrain
        # lowDuration, highDuration, lowVolts, highVolts defines the pulsetrain
        # repetitions: How many times the waveform is repeated. -1 means infinite
        # trigger: trigger source number, if this value exist, generator will not start until triggered
        if trigger < 0 or trigger > 10:
            raise Exception("Invalid trigger number: %d" % trigger)
        if not self.debugMode:
            if lowDuration < 0 or lowDuration > 0x7FFFFFFF:
                raise Exception("Invalid lowDuration: %d" % lowDuration)
            if highDuration < 0 or highDuration > 0x7FFFFFFF:
                raise Exception("Invalid highDuration: %d" % highDuration)
            if lowVolts < -10.0 or lowVolts > 10.0:
                raise Exception("Invalid lowVolts: %f" % lowVolts)
            if highVolts < -10.0 or highVolts > 10.0:
                raise Exception("Invalid highVolts: %f" % highVolts)
            if repetitions < -1 or repetitions > 0xFFFFFFFF:
                raise Exception("Invalid number of repetitions: %d" % repetitions)
        reply = str(self._checkForError(self._sendReceive(b"pul %d %d %e %e %d %d" % (lowDuration, highDuration, lowVolts, highVolts, repetitions, trigger))).decode("utf-8"))
        lowTime = int(reply.split('low time:')[1].split()[0].strip(',').strip('ms'))
        highTime = int(reply.split('high time:')[1].split()[0].strip(',').strip('ms'))
        lowValue = float(reply.split('low value')[1].split()[0].strip(',').strip('V'))
        highValue = float(reply.split('high value:')[1].split()[0].strip(',').strip('V'))
        pulseCount = int(reply.split('high value:')[1].split('times')[0].split(',')[1].strip(' '))
        trigger = int(reply.split('trigger:')[1].split()[0].strip(','))
        return {"LowTime": lowTime, "HighTime": highTime, "LowValue": lowValue, "HighValue": highValue,
                "PulseCount": pulseCount, "Trigger": trigger}

    def getPulsetrain(self):
        reply = str(self._checkForError(self._sendReceive(b"pul")).decode("utf-8"))
        lowTime=  int(reply.split('low time:')[1].split()[0].strip(',').strip('ms'))
        highTime = int(reply.split('high time:')[1].split()[0].strip(',').strip('ms'))
        lowValue = float(reply.split('low value')[1].split()[0].strip(',').strip('V'))
        highValue =  float(reply.split('high value:')[1].split()[0].strip(',').strip('V'))
        pulseCount = int(reply.split('high value:')[1].split('times')[0].split(',')[1].strip(' '))
        trigger = int(reply.split('trigger:')[1].split()[0].strip(','))
        return {"LowTime": lowTime, "HighTime": highTime, "LowValue": lowValue, "HighValue": highValue,
                "PulseCount": pulseCount, "Trigger": trigger}

    def defineAWG(self, samples, repetitions=-1, trigger=0): # Sample rate is 1kS/s
        # Define a pulse train function generator
        # The generator is always Generator.AWG
        # samples: An array of volt, defines the pulsetrain samples at 1000 samples per second. Max 8000 samples allowed
        # repetitions: How many times the waveform is repeated. -1 means infinite
        # trigger: trigger source number, if this value exist, generator will not start until triggered
        if not self.debugMode:
            if len(samples) == 0 or len(samples) > 8000:
                raise Exception("Invalid number of samples in AWG definition")
        for idx in range(0, len(samples), 64):
            cmd = ("awg 0 0 " + " ".join(["%e" % v for v in samples[idx:idx+64]])).encode('ascii')
            self._sendReceive(cmd)
        reply = str(self._checkForError(self._sendReceive(b"run %d %d" % (repetitions, trigger))).decode("utf-8"))
        returnValue = {}
        samples = int(reply.split('Samples:')[1].split(', Repetitions:')[0].strip(' ').strip(','))
        repetitions = int(reply.split('Repetitions:')[1].split('Trigger:')[0].strip(' ').strip(','))
        trigger = int(reply.split('Trigger:')[1].strip(' ').strip('\''))
        returnValue.update({"Samples": samples, "Repetitions": repetitions, "Trigger": trigger})
        return returnValue

    def getAwg(self):
        reply = str(self._sendReceive(b"run"))
        print(reply)
        returnValue = {}
        samples = int(reply.split('Samples:')[1].split(', Repetitions:')[0].strip(' ').strip(','))
        repetitions = int(reply.split('Repetitions:')[1].split('Trigger:')[0].strip(' ').strip(','))
        trigger = int(reply.split('Trigger:')[1].strip(' ').strip('\''))
        returnValue.update({"Samples": samples, "Repetitions": repetitions, "Trigger": trigger})
        return returnValue

    def setChannelOutput(self, channel, generator, amplitude=1.0, offset=0):
        # Defines the output for a channel
        # generator: Generator.DC, Generator.generator1, .., Generator.generator8, Generator.AWG, Generator.pulsetrain
        # amplitude: Scaling of the waveform
        # offset: Voltage offset
        if not self.debugMode:
            self._validateChannel(channel)
        if generator not in Generator.all:
            raise Exception("Invalid generator number (must be 0-10): %d" % generator)
        return self._checkForError(self._sendReceive(b"wav %d %d %e %e" % (channel, generator, amplitude, offset))).decode("utf-8")

    def getChannelOutput(self, channel):
        if not self.debugMode:
            self._validateChannel(channel)
        reply =  str(self._checkForError(self._sendReceive(b"wav %d" %channel)).decode("utf-8"))
        generator = int (reply.split('Generator:')[1].split('Amplitude')[0].replace(',', ''))
        amplitude =  float (reply.split('Amplitude:')[1].split('Offset')[0].replace(',', ''))
        offset =  float(reply.split('Offset:')[1])
        return {"Generator": generator,"Amplitude": amplitude,"Offset": offset}

    def setSyncOutput(self, syncChannel, generator, delay=0, pulseLength=1):
        # Set output on a sync output channel
        # syncChannel: 0-5
        # generator: The generator that the sync channel follows
        # delay: milliseconds delay for the sync
        # pulseLength: Length in milliseconds of the sync pulse
        if syncChannel not in self.syncChannels:
            raise Exception("Invalid sync channel (must be 0-5): %d" % syncChannel)
        if generator not in Generator.all:
            raise Exception("Invalid generator number (must be 0-10): %d" % generator)
        if delay < 0 or delay > 268435455:
            raise Exception("Invalid sync channel delay: %d ms" % delay)
        if pulseLength < 1:
            raise Exception("Invalid sync channel pulse length: %d ms" % pulseLength)
        res =self._checkForError((self._sendReceive(b"syn %d %d %d %d" % (syncChannel, generator, delay, pulseLength))))
        syncCh = int(res.split(b'bound to generator')[0].strip(b'Sync output').strip(b' ').strip(b','))
        generator = int(res.split(b'bound to generator')[1].split(b'delay')[0].strip(b' ').strip(b','))
        delay = int(res.split(b'delay')[1].split(b'duration')[0].strip(b' ').strip(b',').strip(b'ms'))
        duration = int(res.split(b'duration')[1].strip(b' ').strip(b',').strip(b'ms'))
        return {"Channel": syncCh, "Generator": generator, "Delay": delay, "Duration": duration}

    def setSyncOutputOff(self, syncChannel):
        # Turns off output on a sync output channel
        # syncChannel: 0-5
        if syncChannel not in self.syncChannels:
            raise Exception("Invalid sync channel (must be 0-5): %d" % syncChannel)
        res = self._checkForError(self._sendReceive(b"syn %d %d %d %d" % (syncChannel, 0, 0, 0)))
        syncCh = int(res.split(b'bound to generator')[0].strip(b'Sync output').strip(b' ').strip(b','))
        generator = int(res.split(b'bound to generator')[1].split(b'delay')[0].strip(b' ').strip(b','))
        delay = int(res.split(b'delay')[1].split(b'duration')[0].strip(b' ').strip(b',').strip(b'ms'))
        duration = int(res.split(b'duration')[1].strip(b' ').strip(b',').strip(b'ms'))
        return {"Channel": syncCh, "Generator": generator, "Delay": delay, "Duration": duration}
        #return self._checkForError(self._sendReceive(b"syn %d %d %d %d" % (syncChannel, 0, 0, 0))).decode("utf-8")

    def getSyncOutput(self, syncChannel):
        # Get output state on a sync output channel
        # syncChannel: 0-5
        if syncChannel not in self.syncChannels:
            raise Exception("Invalid sync channel (must be 0-5): %d" % syncChannel)
        res = self._checkForError(self._sendReceive(b"syn %d" % syncChannel))
        syncCh = int(res.split(b'bound to generator')[0].strip(b'Sync output').strip(b' ').strip(b','))
        generator = int(res.split(b'bound to generator')[1].split(b'delay')[0].strip(b' ').strip(b','))
        delay = int(res.split(b'delay')[1].split(b'duration')[0].strip(b' ').strip(b',').strip(b'ms'))
        duration = int(res.split(b'duration')[1].strip(b' ').strip(b',').strip(b'ms'))
        return {"Channel": syncCh, "Generator": generator, "Delay": delay, "Duration": duration}

    def getCurrentReading(self, channel):
        # Reads current from a DAC channel. Unit is in Amps
        if self.debugMode == False:
            self._validateChannel(channel)
        reply = self._checkForError(self._sendReceive(b"get %d" % channel))
        try:
            return float(reply.split(b":", 1)[1][:-2])*1e-6
        except:
            raise Exception("Error response from QDAC: <%s>" % reply)

    def getRawCurrentADCreading(self, channel):
        # Reads current from a DAC channel. Unit is in Amps
        if self.debugMode == False:
            self._validateChannel(channel)
        reply = self._checkForError(self._sendReceive(b"adc %d" % channel))
        try:
            return int(reply.split(b":", 1)[1])
        except:
            raise Exception("Error response from QDAC: <%s>" % reply)

    def waitForSync(self, generator, timeout=-1):
        # Software wait for the beginning of a generator signal
        # generator: The generator that the sync waits for
        # timeout: Max number of seconds to wait. -1 = infinite
        beginTime = time.time()
        if generator not in Generator.syncGenerators:
            raise Exception("Invalid generator number (must be 1-10): %d" % generator)
        self._checkForError(self._sendReceive(b"ssy %d" % generator))
        while True:
            response = self._readLine(failOnTimeout=False)
            if response and b"#" in response:
                return True
            if timeout > 0 and time.time() - beginTime > timeout:
                return False
            else:
                time.sleep(0.001)

    def goToBootloader(self):
        # Soft restart system and enter bootlaoder
        return self._checkForError(self._sendReceive(b"bootloader")).decode("utf-8")

    def setVoltageCalibration(self, channel, theRange, samplesPerVolt, offsetSamples):
        # range must be 1.0 or 10.0 (unit is V)
        # Note: Data is not stored in persisted memory. When instrument is rebooted, it is set back to factory values.
        # To store permanently, call storeCalibrationInFlash
        if self.debugMode == False:
            self._validateChannel(channel)
        if theRange == 10.0:
            rangeFlag = 0
        elif theRange == 1.0:
            rangeFlag = 1
        else:
            raise Exception("Invalid voltage range %f" % theRange)
        return self._checkForError(self._sendReceive(b"vcal %d %d %e %e" % (channel, rangeFlag, samplesPerVolt, offsetSamples))).decode("utf-8")

    def getVoltageCalibration(self, channel, theRange):
        # Range must be 1.0 or 10.0 (unit is V)
        if theRange == 10.0:
            rangeFlag = 0
        elif theRange == 1.0:
            rangeFlag = 1
        else:
            raise Exception("Invalid voltage range %f" % theRange)
        reply = self._checkForError(self._sendReceive(b"vcal %d %d" % (channel, rangeFlag))).decode("utf-8")
        return {"Gain" :float(reply.split('mult')[1].split('offset')[0].strip()), "Offset":float(reply.split('offset')[1].strip()) }

    def setCurrentCalibration(self, channel, theRange, microampsPerSample, offsetMicroamps):
        # range must be 1e-6 or 100e-6 (unit is A)
        # Note: Data is not stored in persisted memory. When instrument is rebooted, it is set back to factory values.
        # To store permanently, call storeCalibrationInFlash
        if self.debugMode == False:
            self._validateChannel(channel)
        if theRange == 1e-6:
            rangeFlag = 0
        elif theRange == 100e-6:
            rangeFlag = 1
        else:
            raise Exception("Invalid current range %e" % theRange)
        return self._checkForError(self._sendReceive(b"ical %d %d %e %e" % (channel, rangeFlag, microampsPerSample, offsetMicroamps))).decode("utf-8")

    def getCurrentCalibration(self, channel, theRange):
        # range must be 1e-6 or 100e-6 (unit is A)
        if theRange == 1e-6:
            rangeFlag = 0
        elif theRange == 100e-6:
            rangeFlag = 1
        else:
            raise Exception("Invalid current range: %e" % theRange)
        reply =  self._checkForError(self._sendReceive(b"ical %d %d" % (channel, rangeFlag))).decode("utf-8") # TODO: Proper formatting processing of response
        return {"Gain": float(reply.split('mult')[1].split('offset')[0].strip()), "Offset": float(reply.split('offset')[1].strip())}

    def storeCalibrationInFlash(self):
        # If called after any number of calls to setVoltageCalibration and/or setCurrentCalibration, the new calibration
        # values are stored permanently in flash memory, overwriting the factory values. For channels where the
        # calibration has not been changed, values in the flash memory are also unchanged
        success = False
        for i in range(1):
            reply = self._sendReceive('savecalib5599')
            if b'DATA SAVED' in reply:
                success=True
                break
            else:
                print("Flash storing failed - try #%d: %s" % (i, reply))
                time.sleep(1)
        return success

    def setBaudrate(self, baudrate):
        # Changes the communication speed with the QDAC
        BaudratesAllowed = [600, 1200, 2400, 4800, 9600, 14400, 19200, 38400, 57600, 115200, 230400, 460800, 921600]
        if baudrate in BaudratesAllowed:
            reply = self._checkForError(self._sendReceive(b"brt %d" % baudrate)).decode("utf-8")
            if (reply == 'Changing BAUD rate to: %d' % baudrate):
                self.sport.close()
                self.sport = serial.Serial(port=self.port, baudrate=baudrate, bytesize=serial.EIGHTBITS,
                                           parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=0.5)
            else:
                raise Exception("Failed to change baud rate: %s" % reply)
        else:
            raise Exception("Invalid baud rate: %d" % baudrate)

    def getMinMaxOutputVoltage(self, channel, theRange):
        if self.debugMode == False:
            if(channel!=0):
                self._validateChannel(channel)
        if theRange == 10.0:
            rangeFlag = 0
        elif theRange == 1.0:
            rangeFlag = 1
        else:
            raise Exception("Invalid voltage range: %f" % theRange)
        reply = self._checkForError(self._sendReceive(b"rang %d %d" % (channel, rangeFlag))).decode("utf-8")
        return {"MinVoltage": float(reply.split("MIN:")[1].split("MAX")[0].strip()),
                "MaxVoltage": float(reply.split("MAX:")[1].strip())}

    def restart(self):
        # Reboot the QDAC firmware
        self.goToBootloader()
        time.sleep(2)
        self.sport.close()
        self.sport = serial.Serial(port=self.port, baudrate=115200, bytesize=serial.EIGHTBITS,
                                   parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=0.5)
        self.sport.write(b'\x01\x05\xa5\x50\x04')
        self.sport.close()
        self.sport = serial.Serial(port=self.port, baudrate=460800, bytesize=serial.EIGHTBITS,
                                   parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=0.5)
        time.sleep(0.5)
        self.flush()
    def executeTrigger(self,triggerNumber):
        if not self.debugMode:
            self._validateTrigger(triggerNumber)
        return self._checkForError(self._sendReceive(b"trig %d" % (triggerNumber))).decode("utf-8")

    def linkExternalTrigger(self,triggerNumber, value = 1):
        if not self.debugMode:
            self._validateTrigger(triggerNumber)
        reply = self._checkForError(self._sendReceive(b"trig %d %d" % (triggerNumber,value))).decode("utf-8")
        return int(reply.split("SynB-in connected to trigger:")[1])

    def getExternalTrigger(self):
        reply = self._checkForError(self._sendReceive(b"trig")).decode("utf-8")
        return int(reply.split("SynB-in connected to trigger:")[1])


    def syncPortOut(self,port='A',enabledisable=1):
        if(port=='A'):
            if(enabledisable==1 or enabledisable == 0):
                self._checkForError(self._sendReceive(b"synA %d" % (enabledisable)))
            else:
                raise Exception("Invalid enabledisable value: %d" % enabledisable)
        elif (port=='B'):
            if (enabledisable == 1 or enabledisable == 0):
                self._checkForError(self._sendReceive(b"synB %d" % (enabledisable))).decode("utf-8")
            else:
                raise Exception("Invalid enabledisable value: %d" % enabledisable)


    def getSyncPortOut(self, port='A'):
        if (port == 'A'):
            reply =  self._checkForError(self._sendReceive(b"synA")).decode("utf-8")
            return int(reply.strip("SynA:").strip(" "))
        elif (port == 'B'):
            reply = self._checkForError(self._sendReceive(b"synB")).decode("utf-8")
            return  int(reply.strip("SynB:").strip(" "))
        else:
            raise Exception("Invalid port ")

    def setExternalSampleClock(self, enabledisable):
        if (enabledisable == 1 or enabledisable == 0):
            return self._checkForError(self._sendReceive(b"extclk %d" % (enabledisable))).decode("utf-8")
        else:
            raise Exception("Invalid enabledisable value: %d" % enabledisable)

    def getExternalSampleClock(self):
        reply = self._checkForError(self._sendReceive(b"extclk" )).decode("utf-8")
        return int(reply.strip("ExternalClock:").strip(""))

    def setDebugMode(self, value):
        self.debugMode = value

    def _checkForError(self, message):
        if message[0:5] == b"Error":
            raise Exception("Error response from QDAC: <%s>" % message)
        return message

    def _validateChannel(self, channel):
        if channel not in self.channelNumbers:
            raise Exception("Invalid channel number: %d" % channel)

    def _validateVoltage(self, channel, volts):
        if volts < 0.001-self.voltageRange[channel] or volts > self.voltageRange[channel]-0.001:
            raise Exception("Invalid voltage: %f" % volts)
    def _validateTrigger(self,triggerNumber):
        if triggerNumber not in self.triggerRange:
            raise Exception("Invalid trigger number: %d" % triggerNumber)
    def _sendReceive(self, msg):
        if self.verbose:
            print(msg)
        self.sport.write(msg + b"\n")
        reply = self._readLine()
        return reply

    def _readLine(self, failOnTimeout=True):
        out = b""
        c = b""
        while True:
            c = self.sport.read(1)
            if c:
                if c != b"\n":
                    out += c
                else:
                    break
            else:
                if failOnTimeout and self.verbose:
                    raise Exception("Timeout!")
                break
        if self.verbose and out:
            print(out)
        return out
