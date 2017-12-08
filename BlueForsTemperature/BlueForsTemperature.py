#!/usr/bin/env python

from BaseDriver import LabberDriver
import datetime


class Driver(LabberDriver):
    def performOpen(self, options={}):
        pass

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        if quant.name in ['CH1', 'CH2', 'CH5', 'CH6']:
            try:
                # find latest temperature log file
                logFolderPath = self.getValue('BlueFors Log Folder')
                now = datetime.datetime.now()
                datestr = '%s-%s-%s' %(str(now.year)[-2:],
                    str('{:02d}'.format(now.month)),
                    str('{:02d}'.format(now.day)))
                filePath = '%s/%s/%s T %s.log' % (logFolderPath, datestr,
                                                  quant.name, datestr)
                # read all values from text file
                with open(filePath, 'rb') as f:
                    data = f.readlines()
                    lastline = data[-1].split(b',')
                    value = lastline[2]
            except Exception as e:
                # ignore all errors
                value = 0
                self.log(str(e))
                pass
        else:
            value = LabberDriver.performGetValue(self, quant, options)
        return value


if __name__ == '__main__':
    pass
