#!/usr/bin/env python

from VISA_Driver import VISA_Driver

__version__ = "0.0.1"


class Driver(VISA_Driver):
    """ The SRS DG645 driver re-implements the VISA driver with some more options"""

    dChCmd = {'AB - Start': 2, 'AB - Stop': 3, 'CD - Start': 4, 'CD - Stop': 5,
              'EF - Start': 6, 'EF - Stop': 7, 'GH - Start': 8, 'GH - Stop': 9}

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # perform special setValue for delay commands
        name = str(quant.name)
        if name.endswith(('Start time', 'Start reference',
                          'Stop time', 'Stop reference')):
            # get pulse channel in use
            lName =  name.split(' ')
            key = '%s - %s' % (lName[0], lName[2])
            sChannel = '%d' % self.dChCmd[key]
            # get buddy quantity
            if lName[3] == 'time':
                sTime = quant.getCmdStringFromValue(value)
                sRef = self.getCmdStringFromValue('%s - %s reference' % 
                                                  (lName[0], lName[2]))
            else:
                sTime = self.getCmdStringFromValue('%s - %s time' %
                                                   (lName[0], lName[2]))
                sRef = quant.getCmdStringFromValue(value)
            sCmd = 'DLAY %s,%s,%s' % (sChannel, sRef, sTime)
            self.writeAndLog(sCmd)
            return value
        else:
            # for all other quantities, call the generic VISA driver
            return VISA_Driver.performSetValue(self, quant, value, sweepRate,
                                               options=options)


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # perform special getValue for delay commands
        name = str(quant.name)
        if name.endswith(('Start time', 'Start reference',
                          'Stop time', 'Stop reference')):
            # get pulse channel in use
            lName =  name.split(' ')
            key = '%s - %s' % (lName[0], lName[2])
            sChannel = '%d' % self.dChCmd[key]
            sCmd = 'DLAY?%s' % sChannel
            sAns = self.askAndLog(sCmd).strip()
            lAns = sAns.split(',')
            # return time or reference
            if lName[3] == 'time':
                return float(lAns[1])
            else:
                return quant.getValueFromCmdString(lAns[0])
        else:
            # run the generic visa driver case
            return VISA_Driver.performGetValue(self, quant, options=options)



if __name__ == '__main__':
    pass
