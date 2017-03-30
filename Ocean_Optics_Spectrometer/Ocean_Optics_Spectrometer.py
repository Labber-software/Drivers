#!/usr/bin/env python

import InstrumentDriver
import seabreeze.spectrometers as sb

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements the Ocean Optics Spectrometer"""
    
    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # init object
        self.spec = None
        try:
            # open connection
            devices = sb.list_devices()
            # check if devices available
            if len(devices) == 0:
                # no devices found
                raise Exception('No spectrometer found')
            elif len(devices) == 1:
                # one device, use
                self.spec = sb.Spectrometer(devices[0])
            else:
                # many devices, look for serial
                self.spec = sb.Spectrometer.from_serial_number(self.comCfg.address)
        except Exception as e:
            # re-cast errors as a generic communication error
            raise InstrumentDriver.CommunicationError(str(e))


    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # check if digitizer object exists
        try:
            if self.spec is None:
                # do nothing, object doesn't exist (probably was never opened)
                return
        except:
            # never return error here, do nothing, object doesn't exist
            return
        try:
            # close and remove object
            self.spec.close()
            del self.spec
        except:
            # never return error here
            pass


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # check quantity
        if quant.name == 'Integration time':
            # conversion from s -> us
            self.spec.integration_time_micros(int(value*1E6))
        elif quant.name == 'Temperature':
            # temperature set point
            self.spec.tec_set_temperature_C(value)
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check type of quantity
        if quant.name == 'Temperature':
            # temperature
            value = self.spec.tec_get_temperature_C()
        elif quant.name == 'Intensity':
            # get intensity
            vY = self.spec.intensities(correct_dark_counts=False, correct_nonlinearity=False)
            # assume equally-spaced waveform values
            vX = self.spec.wavelengths()
            value = quant.getTraceDict(vY, dt=1E-6*((vX[-1]-vX[0])/float(len(vX)-1)),
                    t0=1E-6*vX[0])
            # # don't return x-data
            # value = quant.getTraceDict(vY)
        # elif quant.name == 'Wavelength':
        #     # get wavelength 
        #     vX = self.spec.wavelengths()
        #     value = quant.getTraceDict(1E-6*np.array(vX))
        return value
        

if __name__ == '__main__':
    pass
