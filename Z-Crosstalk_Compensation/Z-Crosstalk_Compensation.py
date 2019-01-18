#!/usr/bin/env python

import InstrumentDriver
import numpy as np


class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements Z-Crosstalk Compensation"""


    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # init variables


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # do nothing, just return value

        if (quant.name == 'Do Conversion'):
            self.doConversion()
        elif ('Flux Bias' in quant.name):
            self.doConversion()

        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check type of quantity
        if quant.isVector():
            pass
        else:
            if 'Flux Bias' in quant.name:

                self.doConversion()
            # for all other cases, do nothing
            value = quant.getValue()
        return value

    def doConversion(self):
        n = int(self.getValue('Number of Z-Control Lines'))
        #self.log("Number of Z-Control Lines: %d "%(n))

        M = np.zeros((n,n))
        for i in range(n):
            for j in range(n):
                M[i,j] = self.getValue('M' + str(i+1) + str(j+1))
        self.log("M: " +str(M))

        M_inv = np.linalg.inv(M)

        self.log("M_inv: " +str(M_inv))

        vecPhi = np.zeros((n))
        for i in range(n):
            vecPhi[i] = self.getValue('Flux Bias ' + str(i+1))

        vecV = np.matmul(M_inv, vecPhi)
        self.log("vec_V: " + str(vecV))
        for i in range(n):
            self.setValue('Control Knob '+str(i+1), vecV[i])

            for j in range(n):
                self.setValue('Minv'+str(i+1)+str(j+1), M_inv[i,j])

if __name__ == '__main__':
    pass
