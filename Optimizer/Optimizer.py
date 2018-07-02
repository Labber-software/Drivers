#!/usr/bin/env python
import InstrumentDriver
import numpy as np
import copy

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements a Nelder-Mead optimization driver"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        self.x = []
        self.cost = 0
        self.step = 'None'
        self.i = -1


    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        pass


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""

        if quant.name == 'Cost':
            self.cost += value
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        if quant.name.startswith('Parameter'):
            n = int(quant.name.split('#')[1]) - 1
            if int(self.getValue('Iteration')) != self.i:
                self.nelder_mead()
                self.cost = 0
            value = self.x[n]

        elif quant.name == 'Cost':
            value = self.cost
        else:
            # just return the quantity value
            value = quant.getValue()
        return value

    def cost_function(self):
        if self.getValue('Maximize'):
            return -self.cost
        else:
            return self.cost


    def nelder_mead(self):
        '''
        Reference: https://en.wikipedia.org/wiki/Nelder%E2%80%93Mead_method
        '''
        self.i = int(self.getValue('Iteration'))
        gamma = 2.
        rho = 0.5
        sigma = 0.5

        if self.i == 0:
            self.n_parameters = int(self.getValue('Number of parameters'))
            # init
            self.x_start = []
            self.x_step = []
            for i in range(self.n_parameters):
                self.x_start.append(self.getValue('Start value parameter #{}'.format(i+1)))
                self.x_step.append(self.getValue('Step size parameter #{}'.format(i+1)))
            self.x_start = np.array(self.x_start)
            self.x = self.x_start

        elif self.i == 1:
            self.prev_best = self.cost_function()
            self.res = [[self.x_start, self.prev_best]]

            x = copy.copy(self.x_start)
            self.k = 0
            x[self.k] = x[self.k] + self.x_step[self.k]
            self.log('start ', x)
            self.x = x

        elif self.i in (np.arange(self.n_parameters) + 1):
            self.score = self.cost_function()
            self.res.append([self.x, self.score])
            self.k += 1
            x = copy.copy(self.x_start)
            x[self.k] = x[self.k] + self.x_step[self.k]
            self.log('start ', x)
            self.x = x

        elif self.i == self.n_parameters + 1:
            self.score = self.cost_function()
            self.res.append([self.x, self.score])
            self.start()

        else:
            if self.step == 'reflection':
                self.rscore = self.cost_function()
                if self.res[0][1] <= self.rscore < self.res[-2][1]:
                    del self.res[-1]
                    self.res.append([self.xr, self.rscore])
                    self.start()

                elif self.rscore < self.res[0][1]:
                        self.xe = self.x0 + gamma*(self.xr - self.x0)
                        self.x = self.xe
                        self.step = 'expansion'

                else:
                    self.xc = self.x0 + rho*(self.res[-1][0] - self.x0)
                    self.x = self.xc
                    self.step = 'contraction'

            elif self.step == 'expansion':
                    self.escore = self.cost_function()
                    if self.escore < self.rscore:
                        del self.res[-1]
                        self.res.append([self.xe, self.escore])
                        self.start()
                    else:
                        del self.res[-1]
                        self.res.append([self.xr, self.rscore])
                        self.start()

            elif self.step == 'contraction':
                self.cscore = self.cost_function()
                if self.cscore < self.res[-1][1]:
                    del self.res[-1]
                    self.res.append([self.xc, self.cscore])
                    self.start()

                else:
                    self.x1 = self.res[0][0]
                    self.step = 'reduction'
                    self.nres = []
                    self.j = 0
                    self.redx = self.x1 + sigma*(self.res[self.j][0] - self.x1)
                    self.x = self.redx

            elif self.step == 'reduction':
                    self.score = self.cost_function()
                    self.nres.append([self.redx, self.score])
                    self.j += 1
                    if self.j < len(self.res):
                        self.redx = self.x1 + sigma*(self.res[self.j][0] - self.x1)
                        self.x = self.redx
                    else:
                        self.res = self.nres
                        self.start()
            else:
                raise ValueError('Should never happen')

    def start(self):
        alpha = 1
        # order
        self.res.sort(key=lambda x: x[1])

        # centroid
        self.x0 = [0.] * self.n_parameters
        for tup in self.res[:-1]:
            for i, c in enumerate(tup[0]):
                self.x0[i] += c / (len(self.res)-1)

        self.xr = self.x0 + alpha*(self.x0 - self.res[-1][0])

        self.x = self.xr
        self.step = 'reflection'

if __name__ == '__main__':
    pass
