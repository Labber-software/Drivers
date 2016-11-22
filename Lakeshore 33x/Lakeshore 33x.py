#!/usr/bin/env python

from VISA_Driver import VISA_Driver

__version__ = "0.0.1"

class Error(Exception):
    pass

class Driver(VISA_Driver):
    """ This class implements the Lakeshore 33x driver"""
        
    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the set value operation"""
        # The default precision of labber is too high...
        self.writeAndLog(quant.set_cmd + str(value))
        return value
        
if __name__ == '__main__':
    pass
