#!/usr/bin/env python
from BaseDriver import LabberDriver
from sequence_builtin import Rabi, CPMG, PulseTrain 

import importlib


class Driver(LabberDriver):
    """ This class implements a multi-qubit pulse generator"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # init variables
        self.sequence = None
        self.values = {}


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. 

        """
        # only do something here if changing the sequence type
        if quant.name == 'Sequence' and value != 'Custom':
            # create new sequence if needed
            if (value != quant.getValue()) or (self.sequence is None):
                # create a new sequence object
                if value == 'Rabi':
                    self.sequence = Rabi()
                elif value == 'CP/CPMG':
                    self.sequence = CPMG()
                elif value == 'Pulse train':
                    self.sequence = PulseTrain()

        elif quant.name =='Custom python file':
            # for custom python files
            mod = importlib.import_module(value)
            # the custom sequence class has to be named 'CustomSequence'
            self.sequence = mod.CustomSequence()
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation

        """
        # check type of quantity
        if quant.isVector():
            # traces, check if waveform needs to be re-calculated
            if self.isConfigUpdated():
                # update sequence object with current driver configuation
                config = self.instrCfg.getValuesDict()
                self.sequence.set_parameters(config)
                # calcluate waveforms
                self.values = self.sequence.calculate_waveforms(config)
            # get correct data from waveforms stored in memory
            value = self.getWaveformFromMemory(quant)
        else:
            # for all other cases, do nothing
            value = quant.getValue()
        return value


    def getWaveformFromMemory(self, quant):
        """Return data from already calculated waveforms"""
        # check which data to return
        if quant.name[-1] in ('1','2','3','4','5','6','7','8','9'):
            # get name and number of qubit waveform asked for
            name = quant.name[:-1]
            n = int(quant.name[-1]) - 1
            # get correct vector
            if name == 'Trace - I':
                if self.getValue('Swap IQ'):
                    value = self.values['wave_xy'][n].imag
                else:
                    value = self.values['wave_xy'][n].real
            elif name == 'Trace - Q':
                if self.getValue('Swap IQ'):
                    value = self.values['wave_xy'][n].real
                else:
                    value = self.values['wave_xy'][n].imag
            elif name == 'Trace - Z':
                value = self.values['wave_z'][n]
            elif name == 'Trace - G':
                value = self.values['wave_gate'][n]

        elif quant.name == 'Trace - Readout trig':
            value = self.values['readout_trig']

        elif quant.name == 'Trace - Readout IQ':
            value = self.values['readout_iq']

        # return data as dict with sampling information
        dt = 1 / self.sequence.sample_rate
        value = quant.getTraceDict(value, dt=dt)
        return value





if __name__ == '__main__':
    pass
