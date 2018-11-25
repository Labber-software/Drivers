from BaseDriver import LabberDriver
import numpy as np
import simple_pid



class Driver(LabberDriver):

    def performOpen(self, options={}):
        """Creat the PID controller"""
        self.pid = simple_pid.PID(sample_time=None)


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # just return the value
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # proceed depending on quantity
        if quant.name == 'Output value':
            # start with updating parameters
            self.update_pid_parameters()
            # get input value
            input_value = self.getValue('Input value')
            # run controller and return new output value
            output_value = self.pid(input_value)
            return output_value

        else:
            # for other quantities, just return current value of control
            return quant.getValue()


    def update_pid_parameters(self):
        """Update PID parameters from Labber dialog"""
        # get parameters
        setpoint = self.getValue('Setpoint')
        kp = self.getValue('P')
        ki = self.getValue('I')
        kd = self.getValue('D')
        p_on_input = self.getValue('Proportional on input')
        output_low = self.getValue('Output limit - low')
        output_high = self.getValue('Output limit - high')
        # set to PID object
        self.pid.setpoint = setpoint
        self.pid.tunings = (kp, ki, kd)
        self.pid.proportional_on_measurement = p_on_input
        # output limits
        if np.isinf(output_low):
            output_low = None
        if np.isinf(output_high):
            output_high = None
        self.pid.output_limits = (output_low, output_high)
