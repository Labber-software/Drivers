import InstrumentDriver

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements a user input driver"""


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation"""
        # proceed depending on quantity
        if quant.name == 'Set value':
            # get value from user dialog
            newValue = self.getValueFromUserDialog(value, 
                       title='User input - Set value')
            return newValue
        else:
            return quant.getValue()


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # proceed depending on quantity
        if quant.name == 'Get value':
            # get value from user dialog
            newValue = self.getValueFromUserDialog(quant.getValue(), 
                       title='User input - Get value')
            return newValue
        else:
            return quant.getValue()


