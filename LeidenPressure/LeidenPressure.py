#!/usr/bin/env python

from BaseDriver import LabberDriver

dIndx = {'P4': 0,
         'P5': 1,
         'Dump, 3He': 2,
         'Dump, 4He': 3,
         'Flow': 4,
         'Still pressure': 5,
         'OVC pressure': 6,
         'IVC pressure': 7}

class Driver(LabberDriver):

    def performOpen(self, options={}):
        self.lValues = [0.0] * len(dIndx)
        self.lUpdated = [False] * len(dIndx)


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        if quant.name in dIndx:
            # check if value already measured
            indx = dIndx[quant.name]
            if not self.lUpdated[indx]:
                try:
                    # read all values from text file
                    sFile = self.getValue('Data file')
                    with open(sFile, 'rb') as f:
                        data = f.read()
                        self.log(str(data))
                        for n, val in enumerate(data.split(b',')):
                            self.lValues[n] = float(val.strip())
                            self.lUpdated[n] = True
                except Exception as e:
                    # ignore all errors
                    self.log(str(e))
                    pass
            value = self.lValues[indx]
            # set value to None, to mark as used
            self.lUpdated[indx] = False
        else:
            value = LabberDriver.performGetValue(self, quant, options)
        return value



if __name__ == '__main__':
    pass
