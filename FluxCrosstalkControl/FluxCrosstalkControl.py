import InstrumentDriver
import numpy as np

# Allow logging to Labber's instrument log
import logging
log=logging.getLogger('LabberDriver')

from FluxCrosstalkControl_helpers import FluxControl

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements a simple signal generator driver"""
    
    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        
        self.n = int(self.getValue('Number of Qubits'))
        self.fluxControl = FluxControl(numQubits=self.n)


    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        del self.fluxControl


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # just return the value

        if quant.name == 'Number of Qubits':
            for i in range(self.n): self.setValue('row {}'.format(i+1), '')
            self.n = int(value)
            self.fluxControl = FluxControl(numQubits=self.n)
            self.log('changed number of qubits, need to reload data!')
            #self.setValue('Crosstalk Matrix Path', '...')
            #self.setValue('Flux Offsets Path', '...')
            return value

        if quant.name == 'Matrix Element Value':
            if self.getValue('Change CT matrix element'):
                matrix = 1 / self.fluxControl.sensitivity
                i = int(self.getValue('index qubit')) - 1
                j = int(self.getValue('index source')) - 1
                if i in range(self.n) and j in range(self.n): 
                    element = value #self.getValue('Matrix Element Value')
                    matrix[i,j] = element
                    self.fluxControl.load_matrix(matrix)
                    self.log('loaded crosstalk matrix: {}'.format(matrix))
                    self.write_matrix(matrix)
            self.setValue(quant.name, value)
            #self.doConversion()

        if quant.name == 'Change CT matrix element':
            if value:
                matrix = 1 / self.fluxControl.sensitivity
                i = int(self.getValue('index qubit')) - 1
                j = int(self.getValue('index source')) - 1
                if i in range(self.n) and j in range(self.n): 
                    element = self.getValue('Matrix Element Value')
                    matrix[i,j] = element
                    self.fluxControl.load_matrix(matrix)
                    self.log('loaded crosstalk matrix: {}'.format(matrix))
                    self.write_matrix(matrix)
            if not value:
                path = self.getValue('Crosstalk Matrix Path')
                if path == '...':
                    pass
                else:
                    matrix = np.load(path)
                    self.fluxControl.load_matrix(matrix)
                    self.log('loaded crosstalk matrix: {}'.format(matrix))
                    self.write_matrix(matrix)
            self.setValue(quant.name, value)
            #self.doConversion() 

        if quant.name=='Crosstalk Matrix Path':
            try:
                matrix = np.load(value)
            except Exception as m:
                log.error('Error loading xtalk matrix from npy file. {:s}'.format(m))
                raise FileNotFoundError

            self.fluxControl.load_matrix(matrix)
            self.log('loaded crosstalk matrix: {}'.format(matrix))
            self.write_matrix(matrix)
            #self.doConversion()

        ''' Flux Offset i (Phi0) '''
        if quant.name.split(' ')[0]=='Flux' and quant.name.split(' ')[1]=='Offset':
            self.setValue(quant.name, value)
            self.fluxControl.set_flux_offset(int(quant.name.split(' ')[-1])-1, value)

            #self.doConversion()

        ''' Flux i '''
        if quant.name.split(' ')[0]=='Flux' and quant.name.split(' ')[1]!='Offset':
            self.setValue(quant.name, value)
        
        self.doConversion()
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # proceed depending on quantity

        return quant.getValue()


    def doConversion(self):

        #get voltages and fluxes
        fluxes = []
        for i in range(self.n):
            fluxes.append(self.getValue('Flux {}'.format(i+1)))
        fluxes = np.array(fluxes)
        voltages = self.fluxControl.get_voltages(fluxes)

        #set controls based on the voltages
        for i in range(self.n):
            #self.log('\t *** for Control {} use row {}'.format(i+1, i+1))
            self.setValue('Control {}'.format(i+1), voltages[i])


    def write_matrix(self, matrix):
        for i in range(self.n):
            line = '\t|'
            for m in matrix[i]:
                line = line + '{:.2e} | '.format(m)
            self.setValue('row {}'.format(i+1), line)