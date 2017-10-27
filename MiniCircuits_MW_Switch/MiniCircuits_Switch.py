#!/usr/bin/env python

import http.client # pip install http
import InstrumentDriver
from InstrumentConfig import InstrumentQuantity

__version__ = "0.0.1"

class Error(Exception):
    pass

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements the MiniCircuits USB Switch Matrix driver"""


    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        #try:
            # open connection
        ip_address = self.getAddress()
        port = 80
        self.hc = http.client.HTTPConnection(ip_address, 80, timeout = 2)
        self.hc.request("POST", "/MN?")
        res = self.hc.getresponse()
        MNstr = str(res.read())[5:-1]
        self.setModel(MNstr)
        MNstr2 = self.getModel()
        self.log(MNstr, level = 30)
        self.log(MNstr2, level = 30)

        #except Exception as e:
            # re-cast afdigitizer errors as a generic communication error
            #msg = str(e)
            #raise InstrumentDriver.CommunicationError(msg)

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # check if digitizer object exists
        try:
            # close and remove object
            self.hc.close()
        except:
            # never return error here
            pass


    def performSetValue(self, quant, value, sweepRate = 0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # start with setting current quant value
        quant.setValue(value)
        try:
            self.hc.request("POST", "/MN?")
            res = self.hc.getresponse()
            MNstr = str(res.read())[5:-1]
        except:
            ip_address = self.getAddress()
            port = 80
            self.hc = http.client.HTTPConnection(ip_address, 80, timeout = 2)
            self.hc.request("POST", "/MN?")
            res = self.hc.getresponse()
            MNstr = str(res.read())[5:-1]
        # get values from relevant quants
        if quant.name == 'SP4T Switch A':
            self.hc.request("POST", "/SP4TA:STATE:{}".format(int(value)))
            res = self.hc.getresponse()
            value = int(res.read())
        elif quant.name == 'SP4T Switch B':
            self.hc.request("POST", "/SP4TB:STATE:{}".format(int(value)))
            res = self.hc.getresponse()
            value = int(res.read())
        elif quant.name == 'SP6T Switch A':
            self.hc.request("POST", "/SP6TA:STATE:{}".format(int(value)))
            res = self.hc.getresponse()
            value = int(res.read())
        elif quant.name == 'SP6T Switch B':
            self.hc.request("POST", "/SP6TB:STATE:{}".format(int(value)))
            res = self.hc.getresponse()
            value = int(res.read())
        elif quant.name == 'SPDT Switch A':
            self.hc.request("POST", "/SETA={}".format(int(value)))
            res = self.hc.getresponse()
            value = int(res.read())
        elif quant.name == 'SPDT Switch B':
            self.hc.request("POST", "/SETB={}".format(int(value)))
            res = self.hc.getresponse()
            value = int(res.read())
        elif quant.name == 'SPDT Switch C':
            self.hc.request("POST", "/SETC={}".format(int(value)))
            res = self.hc.getresponse()
            value = int(res.read())
        elif quant.name == 'SPDT Switch D':
            self.hc.request("POST", "/SETD={}".format(int(value)))
            res = self.hc.getresponse()
            value = int(res.read())
        elif quant.name == 'Number of switches':
            pass
        else:
             # do nothing for these quantities, the value will be stored in local quant
             pass
        # finish set value with get value, to make sure we catch any coercing
        return self.performGetValue(quant)


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        try:
            self.hc.request("POST", "/MN?")
            res = self.hc.getresponse()
            MNstr = str(res.read())[5:-1]
        except:
            ip_address = self.getAddress()
            port = 80
            self.hc = http.client.HTTPConnection(ip_address, 80, timeout = 2)
            self.hc.request("POST", "/MN?")
            res = self.hc.getresponse()
            MNstr = str(res.read())[5:-1]
        if quant.name[0:4] == 'SP4T':
            if quant.name[5:] == 'Switch A':
                self.hc.request("POST", "/SP4TA:STATE?")
                res = self.hc.getresponse()
                value = int(res.read())
            elif quant.name[5:] == 'Switch B':
                self.hc.request("POST", "/SP4TB:STATE?")
                res = self.hc.getresponse()
                value = int(res.read())
        elif quant.name[0:4] == 'SP6T':
            if quant.name[5:] == 'Switch A':
                self.hc.request("POST", "/SP6TA:STATE?")
                res = self.hc.getresponse()
                value = int(res.read())
            elif quant.name[5:] == 'Switch B':
                self.hc.request("POST", "/SP6TB:STATE?")
                res = self.hc.getresponse()
                value = int(res.read())
        elif quant.name[0:4] == 'SPDT':
            self.hc.request("POST", "/SWPORT?")
            res = self.hc.getresponse()
            intstring = int(res.read())
            binarystring = '{0:b}'.format(intstring)
            binarystring = binarystring.rjust(8, '0')
            self.log(binarystring, level = 30)
            if quant.name[5:] == 'Switch A':
                value = int(binarystring[-1])
            elif quant.name[5:] == 'Switch B':
                value = int(binarystring[-2])
            elif quant.name[5:] == 'Switch C':
                value = int(binarystring[-3])
            elif quant.name[5:] == 'Switch D':
                value = int(binarystring[-4])
        else:
            value = quant.getValue()
        return value


if __name__ == '__main__':
    pass
