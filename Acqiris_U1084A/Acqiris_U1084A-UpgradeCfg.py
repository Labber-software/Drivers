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
        # demodulation not on by default
        version = '1.1'
        # if converting from old driver, turn on demodulation
        dValue['Enable demodulation'] = True
    # return new version and data
    return (version, dValue, dOption, dQuantReplace)
