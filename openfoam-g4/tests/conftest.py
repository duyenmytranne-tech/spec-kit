import os
import shutil
import sys

import pytest

HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HOME)
sys.dont_write_bytecode = True


@pytest.fixture()
def ramdir(tmp_path, monkeypatch):
    """Isolated work dir; on Linux pytest's tmp_path is used so tests never touch /dev/shm state."""
    wd = tmp_path / "g4work"
    wd.mkdir()
    monkeypatch.setenv("G4_WORKDIR", str(wd))
    return wd


def foam_available():
    from g4runner.foam import foam_env

    return foam_env() is not None and shutil.which("mpirun") is not None


needs_foam = pytest.mark.skipif(not foam_available(), reason="OpenFOAM + MPI not installed")
