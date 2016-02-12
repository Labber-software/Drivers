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
        # zero-span mode moved from bool to combo box with start-stop, center-span
        version = '1.1'
        # assume old value quantity was referring to a voltage
        if 'Zero-span mode' in dValue:
            bZeroSpan = dValue.pop('Zero-span mode')
            if bZeroSpan:
                dValue['Range type'] = 'Zero-span mode'
            else:
                dValue['Range type'] = 'Center - Span'
    # return new version and data
    return (version, dValue, dOption, dQuantReplace)
