# Multi-Qubit Pulse Generator
The mult-qubit pulse generator creates baseband pulses for applying X/Y and Z rotations to systems with superconducting qubits.

The driver uses a library for generating the sequences, which are organized in the following modules and classes:

## sequence.py

Classes for defining gate sequences.  To create a new sequence, subclass the **Sequence** class and implement the gate sequence in the function *generate_sequence*.  The built-in sequences are defined in the file *sequence_builtin.py*

## pulse.py

Classes and code related to creating pulses for driving qubits.

## predistortion.py

Classes and code related to predistorting waveforms to fix pulse imperfections.

## crosstalk.py

Classes and code related to minimizing and compensating for signal crosstalk.

## readout.py

Classes and code for generating waveforms for reading out superconducting qubits.

## docs
Run make html or make latexpdf to create the documentation for the driver.
