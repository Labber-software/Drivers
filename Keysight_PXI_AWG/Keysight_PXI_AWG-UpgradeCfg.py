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
        # re-label AWG -> Ch, change in trig mode
        version = '1.1'

        # rename AWG -> Ch
        before_after = [
            ['AWG1 - Waveform', 'Ch1 - Waveform'],
            ['AWG1 - Trig mode', 'Ch1 - Trig mode'],
            ['AWG1 - Trig', 'Ch1 - Trig'],
            ['AWG1 - Cycles', 'Ch1 - Cycles'],
            ['AWG2 - Waveform', 'Ch2 - Waveform'],
            ['AWG2 - Trig mode', 'Ch2 - Trig mode'],
            ['AWG2 - Trig', 'Ch2 - Trig'],
            ['AWG2 - Cycles', 'Ch2 - Cycles'],
            ['AWG3 - Waveform', 'Ch3 - Waveform'],
            ['AWG3 - Trig mode', 'Ch3 - Trig mode'],
            ['AWG3 - Trig', 'Ch3 - Trig'],
            ['AWG3 - Cycles', 'Ch3 - Cycles'],
            ['AWG4 - Waveform', 'Ch4 - Waveform'],
            ['AWG4 - Trig mode', 'Ch4 - Trig mode'],
            ['AWG4 - Trig', 'Ch4 - Trig'],
            ['AWG4 - Cycles', 'Ch4 - Cycles'],
        ]

        for before, after in before_after:
            dQuantReplace[before] = after
            if before in dValue:
                dValue[after] = dValue.pop(before)

        # replace trig mode labels
        rule = {
            'Auto': 'Continuous',
            'Software': 'Software',
            'Software (per cycle)': 'Software',
            'External': 'External',
            'External (per cycle)': 'External',
        }

        # apply rule for all trig modes
        for n in range(4):
            label = 'Ch%d - Trig mode' % (n + 1)
            if label in dValue:
                dValue[label] = rule[dValue[label]]

    elif version == '1.1':
        # convert version 1.1 -> 1.2
        version = '1.2'

        # replace trig mode labels
        rule = {
            'Continuous': 'Continuous',
            'Software': 'Software / HVI',
            'External': 'External',
        }

        # apply rule for all trig modes
        for n in range(4):
            label = 'Ch%d - Trig mode' % (n + 1)
            if label in dValue:
                dValue[label] = rule[dValue[label]]
    # return new version and data
    return (version, dValue, dOption, dQuantReplace)
