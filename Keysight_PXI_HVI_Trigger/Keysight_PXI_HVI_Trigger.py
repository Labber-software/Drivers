#!/usr/bin/env python
import sys
import os
import numpy as np
from BaseDriver import LabberDriver, Error
sys.path.append('C:\\Program Files (x86)\\Keysight\\SD1\\Libraries\\Python')
import keysightSD1


class Driver(LabberDriver):
    """Keysigh PXI HVI trigger"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # timeout
        self.timeout_ms = int(1000 * self.dComCfg['Timeout'])
        # get PXI chassis
        self.chassis = int(self.comCfg.address)
        # auto-scan chassis address
        n_unit = keysightSD1.SD_Module.moduleCount()
        all_chassis = [
            keysightSD1.SD_Module.getChassisByIndex(n) for n in range(n_unit)]
        # check if user-given chassis is available
        if n_unit > 0 and self.chassis not in all_chassis:
            # if all units are in the same chassis, override given PXI chassis
            if np.all(np.array(all_chassis) == all_chassis[0]):
                self.chassis = all_chassis[0]

        # number of slots in chassis
        self.n_slot = 18
        # supported AWGs and Digitizers
        self.AWGS = ['M3201', 'M3202', 'M3300', 'M3302']
        self.DIGS = ['M3100', 'M3102']
        # keep track of current PXI configuration
        # 0: None, 1: AWG, 2: Digitizer
        self.units = [0] * self.n_slot
        self.old_trig_period = -1.0
        self.old_dig_delay = -1.0

        # Create HVI object
        self.HVI = keysightSD1.SD_HVI()


    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # do not check for error if close was called with an error
        try:
            # close instrument
            self.HVI.stop()
            self.HVI.close()
        except Exception:
            # never return error here
            pass


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # continue depending on quantity
        if quant.name == 'Auto-detect':
            # auto-detect units
            if value:
                self.auto_detect()
        elif quant.name == 'Scan':
            # when scanning, just run auto-detect
            self.auto_detect()
        else:
            # just set the quantity value, config will be set at final call
            quant.setValue(value)

        # only update configuration at final call
        if self.isFinalCall(options):
            self.configure_hvi()

        return value


    def configure_hvi(self):
        """Configure and start/stop HVI depending on UI settings"""
        # get units
        units = self.get_pxi_config_from_ui()
        n_awg = len([x for x in units if x == 1])
        n_dig = len([x for x in units if x == 2])

        # if no units in use, just stop
        if (n_awg + n_dig) == 0:
            self.HVI.stop()
            return

        # check if unit configuration changed, if so reload HVI
        if units != self.units:
            # stop current HVI, may not even be running
            self.HVI.stop()
            self.HVI.close()
            self.units = units

            # we need at least one AWG
            if n_awg == 0:
                raise Error('This driver requires at least one AWG.')
            # currently only support 2 digitizers
            if n_dig > 2:
                raise Error('This driver only supports up to two digitizers.')

            # get HVI name and open
            hvi_name = 'InternalTrigger_%d_%d.HVI' % (n_awg, n_dig)
            dir_path = os.path.dirname(os.path.realpath(__file__))
            self.HVI.open(os.path.join(dir_path, 'HVI_Delay', hvi_name))

            # assign units, run twice to ignore errors before all units are set
            for m in range(2):
                awg_number = 0
                dig_number = 0
                for n, unit in enumerate(units):
                    # if unit in use, assign to module
                    if unit == 0:
                        continue
                    elif unit == 1:
                        # AWG
                        module_name = 'Module %d' % awg_number
                        awg_number += 1
                    elif unit == 2:
                        # digitizer
                        module_name = 'DAQ %d' % dig_number
                        dig_number += 1
                    r = self.HVI.assignHardwareWithUserNameAndSlot(
                        module_name, self.chassis, n + 1)
                    # only check for errors after second run
                    if m > 0:
                        self.check_keysight_error(r)
            # clear old trig period to force update
            self.old_trig_period = 0.0

        # only update trig period if necessary, takes time to re-compile
        if (self.getValue('Trig period') != self.old_trig_period or
                self.getValue('Digitizer delay') != self.old_dig_delay):
            self.old_trig_period = self.getValue('Trig period')
            self.old_dig_delay = self.getValue('Digitizer delay')
            # update trig period, include 460 ns delay in HVI
            wait = round(self.getValue('Trig period') / 10E-9) - 46
            digi_wait = round(self.getValue('Digitizer delay') / 10E-9)
            # special case if only one module: add 240 ns extra delay
            if (n_awg + n_dig) == 1:
                wait += 24
            # r = self.HVI.writeIntegerConstantWithIndex(0, 'Wait time', wait)
            r = self.HVI.writeIntegerConstantWithUserName(
                'Module 0', 'Wait time', wait)
            self.check_keysight_error(r)
            self.log('Number of modules', self.HVI.getNumberOfModules())
            for n in range(n_dig):
                r = self.HVI.writeIntegerConstantWithUserName(
                    'DAQ %d' % n, 'Digi wait', digi_wait)
                self.check_keysight_error(r)

            # need to recompile after setting wait time, not sure why
            self.check_keysight_error(self.HVI.compile())
            # try to load twice, sometimes hangs on first try
            n_try = 2
            while True:
                try:
                    self.check_keysight_error(self.HVI.load())
                    break
                except Exception:
                    n_try -= 1
                    if n_try <= 0:
                        raise

        # start or stop the HVI, depending on output state
        if self.getValue('Output'):
            self.check_keysight_error(self.HVI.start())

        else:
            self.HVI.stop()


    def check_keysight_error(self, code):
        """Check and raise error"""
        if code >= 0:
            return
        # get error message
        raise Error(keysightSD1.SD_Error.getErrorMessage(code))


    def auto_detect(self):
        """Auto-detect units"""
        # start by clearing old config
        for n in range(self.n_slot):
            self.setValue('Slot %d' % (n + 1), 0)

        # loop through all units, make sure chassis match
        n_unit = keysightSD1.SD_Module.moduleCount()
        for n in range(n_unit):
            chassis = keysightSD1.SD_Module.getChassisByIndex(n)
            slot = keysightSD1.SD_Module.getSlotByIndex(n)
            # if chassis match, check unit type
            if chassis == self.chassis:
                model = keysightSD1.SD_Module.getProductNameByIndex(n)
                if model[:5] in self.AWGS:
                    self.setValue('Slot %d' % slot, 'AWG')
                elif model[:5] in self.DIGS:
                    self.setValue('Slot %d' % slot, 'Digitizer')


    def get_pxi_config_from_ui(self):
        """Get PXI config from user interface"""
        units = []
        for n in range(self.n_slot):
            units.append(self.getValueIndex('Slot %d' % (n + 1)))
        return units




if __name__ == '__main__':
    pass
