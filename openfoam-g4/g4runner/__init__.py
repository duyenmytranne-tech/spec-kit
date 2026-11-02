"""g4runner: run OpenFOAM jobs pushed from a Mac on a Google Colab G4 runtime.

Design rules (enforced in code, not only in docs):

* Zero retention: the runner writes no log files and stores no results.
  Work happens in RAM (``/dev/shm``), solver output is parsed from the pipe,
  and the only output is what is printed to the notebook cell.
* Bit-identical inputs: every case is checked against a SHA-256 manifest
  computed on the Mac before anything runs.
* Full use of the hardware is planned automatically from measured values
  (cores, RAM, GPU, ECC state), never from hard-coded guesses.

Standard library only, compatible with Python 3.9 (macOS system python)
through 3.13.
"""

__version__ = "1.0.0"

#: The only retention mode implemented. Kept as a constant so tests and the
#: report can assert it.
RETENTION = "none"
