#Zurich Instruments UHF

This driver encapsulates most features of the Zurich Instruments UHF lock-in amplifier. However, communication is done through ziPython and the LabOne server, which you will have to obtain both from Zurich Instruments. While the LabOne server needs to be running during measurement, the ziPython libs need to be copied to the driver path. Just install ziPython (you do not need an actual local Python installation) and copy the zhinst folder from *C:\PythonX\Lib\site-packages\* to the driver folder (next to *Zurich Instruments UHF.py*).

##Trace Step
The trace step function allows to record a timed trace during which other parameters are changed. The other parameter can be set to two values at given delays.

To enable this function *TimeStep* has to be set to on. The second channel is selected from *TimeStepChannel*. If a trace is started, the trace will run over the duration *TraceLength*, but after *TimeStepDelayA* the value of *TimeStepChannel* will be set to *TimeStepSetpointA*. After an additional delay of *TimeStepDelayB* it will be set to *TimeStepSetpointB* (which can be used to reset the value before the next trace).