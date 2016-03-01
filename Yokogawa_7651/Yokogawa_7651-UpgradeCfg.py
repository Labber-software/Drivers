#!/usr/bin/env python

def upgradeDriverCfg(version, dValue={}, dOption=[]):
    """Upgrade the config given by the dict dValue and dict dOption to the
    latest version."""
    # the dQuantUpdate dict contains rules for replacing missing quantities
    dQuantReplace = {}
    # update quantities depending on version
    if version == '1.0':
        # convert version 1.0 -> 1.1
        # changes:
        # seperate voltage/current quantities instead of generic value
        version = '1.1'
        # assume old value quantity was referring to a voltage
        if 'Value' in dValue:
            dValue['Voltage'] = dValue.pop('Value')
        # replace 'Value' with 'Voltage'
        dQuantReplace['Value'] = 'Voltage'
    # return new version and data
    return (version, dValue, dOption, dQuantReplace)
