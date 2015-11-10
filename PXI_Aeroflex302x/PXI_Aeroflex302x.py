#!/usr/bin/env python

import InstrumentDriver
from InstrumentConfig import InstrumentQuantity
import afSigGenWrapper

__version__ = "0.0.1"


class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements a signal generator in the PXI rack"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # check communication
        try:
            # open connection
            self.sigGen = afSigGenWrapper.afSigGen()
            self.sigGen.create_object()
            # get address strings
            sVisaSigGen = self.dComCfg['address']
            sVisaLO = self.getValue('Local oscillator VISA')
            self.sigGen.boot_instrument(sVisaLO, sVisaSigGen)

        except afSigGenWrapper.Error as e:
            # re-cast afSigGen errors as a generic communication error
            msg = str(e)
            raise InstrumentDriver.CommunicationError(msg)


    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # check if SigGen object exists
        if not hasattr(self, 'sigGen'):
            # do nothing, object doesn't exist (probably was never opened)
            return
        try:
            # do not check for error if close was called with an error
            self.sigGen.close_instrument(bCheckError=not bError)
        except afSigGenWrapper.Error as e:
            # do not raise errors if error already exists
            if not bError:
                # re-cast errors as a generic communication error
                msg = str(e)
                raise InstrumentDriver.CommunicationError(msg)
        finally:
            try:
                # destroy dll object
                self.sigGen.destroy_object()
                del self.sigGen
            except:
                # never return error here
                pass

        
    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        try:
            # proceed depending on command
            if quant.name == 'Frequency':
                self.sigGen.rf_current_frequency_set(value)
            elif quant.name == 'Power':
                self.sigGen.rf_current_level_set(value)
            elif quant.name == 'Output':
                self.sigGen.rf_current_output_enable_set(bool(value))
            elif quant.name == 'Modulation':
                # combo, get index
                if isinstance(value, (str, unicode)):
                    valueIndex = quant.combo_defs.index(value)
                else:
                    valueIndex = int(value)
                self.sigGen.rf_modulation_source_set(valueIndex)
#                self.sigGen.rf_modulation_source_set(quant.getValueIndex(value))
            elif quant.name == 'Levelling mode':
                # combo, get index
                if isinstance(value, (str, unicode)):
                    valueIndex = quant.combo_defs.index(value)
                else:
                    valueIndex = int(value)
                self.sigGen.rf_current_level_mode_set(valueIndex)
#                self.sigGen.rf_current_level_mode_set(quant.getValueIndex(value))
            return value
        except afSigGenWrapper.Error as e:
            # re-cast errors as a generic communication error
            msg = str(e)
            raise InstrumentDriver.CommunicationError(msg)


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        try:
            # proceed depending on command
            if quant.name == 'Frequency':
                value = self.sigGen.rf_current_frequency_get()
            elif quant.name == 'Power':
                value = self.sigGen.rf_current_level_get()
            elif quant.name == 'Output':
                value = self.sigGen.rf_current_output_enable_get()
            elif quant.name == 'Modulation':
                value = self.sigGen.rf_modulation_source_get()
                value = quant.getValueString(value)
            elif quant.name == 'Levelling mode':
                value = self.sigGen.rf_current_level_mode_get()
                value = quant.getValueString(value)
            # return value
            return value
        except afSigGenWrapper.Error as e:
            # re-cast errors as a generic communication error
            msg = str(e)
            raise InstrumentDriver.CommunicationError(msg)
            
   
if __name__ == '__main__':
	pass

