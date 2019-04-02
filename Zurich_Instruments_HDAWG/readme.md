# Zurich Instruments HDAWG

This driver encapsulates most features of the Zurich Instruments 8-channel HDAWG. However, communication is done through ziPython and the LabOne server, which you will have to obtain both from Zurich Instruments. While the LabOne server needs to be running during measurement, the ziPython libs need to be copied to the driver path. Just install ziPython (you do not need an actual local Python installation) and copy the zhinst folder from *C:\PythonX\Lib\site-packages\* to the driver folder (next to *Zurich_Instruments_HDAWG.py*).

