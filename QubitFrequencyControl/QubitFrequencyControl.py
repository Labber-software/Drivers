import InstrumentDriver
import numpy as np

from QubitFrequencyControl_helpers import *

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements a simple signal generator driver"""
    

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        self.fControl = FrequencyControl()
        self.numQubits = int(self.getValue('Number of Qubits'))
        self.getTraces()

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        del self.fControl


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # just return the value
        if quant.name == 'Load Traces':
            self.getTraces()
      
        if 'Frequency' in quant.name:
            for i in range(self.numQubits):
                if quant.name == 'Frequency {}'.format(i+1):
                    self.fControl.set_target_frequencies([value], qubits=[i])
            self.updateFluxes()

        if 'Offset' in quant.name:
            for i in range(self.numQubits):
                if quant.name == 'Offset {}'.format(i+1):
                    qb = self.fControl.qubits[i] 
                    qb.set_offset(value)
                    self.setValue(quant.name, value)
            self.updateFluxes()

        if quant.name == 'Number of Qubits':
            self.numQubits = int(value)
            if self.fControl.numQubits > self.numQubits:
                for i in range(self.fControl.numQubits, self.numQubits, -1):
                    self.fControl.remove_qubit(i-1)
            else:
                self.getTraces()
      
        if quant.name == 'set all':
            for i in range(self.numQubits):
                self.setValue('Frequency {}'.format(i+1), self.getValue('Frequency all'))
                self.fControl.set_target_frequencies([self.getValue('Frequency all')], qubits=[i])

            self.updateFluxes()

        if quant.name == 'all to max':
            for i in range(self.numQubits):
                self.setValue('Frequency {}'.format(i+1), self.fControl.qubits[i].f_max)
                self.fControl.set_target_frequencies([self.fControl.qubits[i].f_max], qubits=[i])
            self.updateFluxes()

        if quant.name == 'all to min':
            for i in range(self.numQubits):
                self.setValue('Frequency {}'.format(i+1), self.fControl.qubits[i].f_min)
                self.fControl.set_target_frequencies([self.fControl.qubits[i].f_min], qubits=[i])
            self.updateFluxes()

        if 'negFlux' in quant.name:
            self.setValue(quant.name, value)
            if value:
                self.fControl.qubits[int(quant.name[-1])-1].positive_flux = False
                self.log('qubit {} positive_flux = {}'.format(int(quant.name[-1]), self.fControl.qubits[int(quant.name[-1])-1].positive_flux))
            else:
                self.fControl.qubits[int(quant.name[-1])-1].positive_flux = True
                self.log('qubit {} positive_flux = {}'.format(int(quant.name[-1]), self.fControl.qubits[int(quant.name[-1])-1].positive_flux))
            self.updateFluxes()

        if 'go to' in quant.name:
            qubit = int(quant.name[-1])-1
            if str(value) == 'OFF': # OFF
                f_target = self.getValue('Frequency {}'.format(qubit+1))
            if str(value) == 'MAX': # MAX
                f_target = self.fControl.qubits[qubit].f_max
            if str(value) == 'MIN': # MIN
                f_target = self.fControl.qubits[qubit].f_min

            self.setValue('Frequency {}'.format(qubit+1), f_target)
            self.fControl.set_target_frequencies([f_target], qubits=[qubit])
            self.updateFluxes()


        if quant.name == 'update':
            self.getTraces()

        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # proceed depending on quantity
        for i in range(self.numQubits):
            if quant.name == 'Trace - {}'.format(i+1):
                trace = self.fControl.qubits[i].trace
                flux = self.fControl.qubits[i].flux
                trace = quant.getTraceDict(trace, x=flux)
                return trace
        return quant.getValue()


    def getTraces(self):
        self.fControl.__init__()
        for i in range(self.numQubits):
            if self.getValue('use fit {}'.format(i+1)):
                params = [self.getValue('f_max {}'.format(i+1)), self.getValue('asymmetry {}'.format(i+1))]
                self.log('added qubit {} with params: {}'.format(i, params))
                self.fControl.add_qubit_fit(params)
            else:
                path = self.getValue('path trace {}'.format(i+1))
                self.log('qubit {} path: {}'.format(i, path))
                if path == '...':
                    return
                self.fControl.add_qubit(path)
            trace = self.fControl.qubits[i].trace
            self.setValue('Trace - {}'.format(i+1), trace)
            target_frequencies = self.fControl.target_frequencies
            self.setValue('Frequency {}'.format(i+1), target_frequencies[i])
        self.updateFluxes()

    
    def updateFluxes(self):
        fluxes = self.fControl.get_fluxes()
        self.log('updating fluxes to {}'.format(fluxes))
        for i in range(self.numQubits):
            self.setValue('Flux {}'.format(i+1), fluxes[i])
