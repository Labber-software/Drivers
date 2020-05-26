#!/usr/bin/env python

def upgradeDriverCfg(version, dValue={}, dOption=[]):
    """Upgrade the config given by the dict dValue and dict dOption to the
    latest version."""
    # the dQuantUpdate dict contains rules for replacing missing quantities
    dQuantReplace = {}
    # update quantities depending on version
    if version == '1.1':
        # convert version 1.1 -> 1.2
        # changes:
        # number of qubits naming conventions, "One" -> "1", "Two" -> "2", etc
        version = '1.2'

        translate = {
            'One': '1',
            'Two': '2',
            'Three': '3',
            'Four': '4',
            'Five': '5',
            'Six': '6',
            'Seven': '7',
            'Eight': '8',
            'Nine': '9'
        }

        # dict with items to update, with default values
        update = {
            'Number of qubits': '2',
            'Qubit for tomography': '1',
            'Qubit 1 # tomography': '1',
            'Qubit 2 # tomography': '2',
            'CT-matrix element #1': 'None',
            'CT-matrix element #2': 'None',
            'CT-matrix element #3': 'None',
            'CT-matrix element #4': 'None',
            'CT-matrix element #5': 'None',
        }

        # update items
        for key, def_value in update.items():
            if key in dValue:
                dValue[key] = translate.get(dValue[key], def_value)

    # return new version and data
    return (version, dValue, dOption, dQuantReplace)
