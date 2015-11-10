import InstrumentDriver
import numpy as np

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements a simple signal generator driver"""
    

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        pass


    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        pass


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # just return the value
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # proceed depending on quantity
        if quant.name == 'Signal':
            # if asking for signal, start with getting values of other controls
            amp = self.getValue('Amplitude')
            freq = self.getValue('Frequency')
            phase = self.getValue('Phase')
            add_noise = self.getValue('Add noise')
            duration = self.getValue('Duration')
            n_points = int(self.getValue('Number of points'))
            # calculate time vector from 0 to 1 with 1000 elements
            time = np.linspace(0.0,duration,n_points)
            signal = amp * np.sin(freq*time*2*np.pi + phase*np.pi/180.0)
            # add noise
            if add_noise:
                noise_amp = self.getValue('Noise amplitude')
                signal += noise_amp * np.random.randn(len(signal))
            # create trace object that contains timing info
            trace = quant.getTraceDict(signal, t0=0.0, dt=time[1]-time[0])
            # finally, return the trace object
            return trace
        else: 
            # for other quantities, just return current value of control
            return quant.getValue()


