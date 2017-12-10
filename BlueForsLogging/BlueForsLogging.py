#!/usr/bin/env python

from BaseDriver import LabberDriver
import datetime

dIndx = {'P1': 0,
         'P2': 1,
         'P3': 2,
         'P4': 3,
         'P5': 4,
         'P6': 5,
         }


class Driver(LabberDriver):
    def performOpen(self, options={}):
        # List of current pressure values
        self.lValues = [0.0] * len(dIndx)
        # List to check if currently stored values have been read
        self.lUpdated = [False] * len(dIndx)

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        if quant.name in dIndx:
            indx = dIndx[quant.name]
            # check if value already measured
            if not self.lUpdated[indx]:
                try:
                    # find latest pressure log file
                    logFolderPath = self.getValue('BlueFors Log Folder')
                    now = datetime.datetime.now()
                    datestr = '%s-%s-%s' % (str(now.year)[-2:],
                                            str('{:02d}'.format(now.month)),
                                            str('{:02d}'.format(now.day)))
                    filePath = '%s/%s/maxigauge %s.log' % (logFolderPath,
                                                           datestr, datestr)
                    # read all values from text file
                    with open(filePath, 'rb') as f:
                        data = f.readlines()
                        lastline = data[-1].split(b',')
                        self.lValues = [float(lastline[5]),
                                        float(lastline[11]),
                                        float(lastline[17]),
                                        float(lastline[23]),
                                        float(lastline[29]),
                                        float(lastline[35])]
                        self.lUpdated = [True for i in self.lUpdated]
                except Exception as e:
                    # ignore all errors and keep old pressures
                    self.log(str(e))
                    pass
            # convert reading from bar to mbar
            value = self.lValues[indx]/1000.
            # to mark as used, set value to False
            self.lUpdated[indx] = False
        elif quant.name in ['CH1', 'CH2', 'CH5', 'CH6']:
            try:
                # find latest temperature log file
                logFolderPath = self.getValue('BlueFors Log Folder')
                now = datetime.datetime.now()
                datestr = '%s-%s-%s' % (str(now.year)[-2:],
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
