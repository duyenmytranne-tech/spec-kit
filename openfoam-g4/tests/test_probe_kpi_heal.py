import os

from g4runner import heal
from g4runner.probe import parse_ecc
from g4runner.runner import kpi_value

ECC_NEW = """
==============NVSMI LOG==============
    ECC Mode
        Current                           : Enabled
        Pending                           : Enabled
    ECC Errors
        Volatile
            SRAM Correctable              : 3
            SRAM Uncorrectable            : 0
            DRAM Correctable              : 2
            DRAM Uncorrectable            : 1
        Aggregate
            SRAM Correctable              : 10
            SRAM Uncorrectable            : 0
            DRAM Correctable              : 4
            DRAM Uncorrectable            : 1
"""
ECC_OLD = """
    Ecc Mode
        Current                     : Enabled
    ECC Errors
        Volatile
            Single Bit
                Device Memory       : 5
                Total               : 5
            Double Bit
                Device Memory       : 0
                Total               : 0
"""


def test_parse_ecc_counts_secded_corrections():
    n = parse_ecc(ECC_NEW)
    assert n["mode"] == "Enabled"
    assert (n["volatile_corrected"], n["volatile_uncorrected"]) == (5, 1)
    assert (n["aggregate_corrected"], n["aggregate_uncorrected"]) == (14, 1)
    o = parse_ecc(ECC_OLD)
    assert o["volatile_corrected"] == 5 and o["volatile_uncorrected"] == 0  # the Total line, not per-memory lines


FC_HEADER = "# Force coefficients\n# Time          Cm              Cd              Cl              Cl(f)           Cl(r)\n"


def _dat(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(FC_HEADER)
        for r in rows:
            fh.write("\t".join(str(x) for x in r) + "\n")


def test_kpi_merges_restart_folders_and_reduces(tmp_path):
    case = str(tmp_path)
    _dat(f"{case}/postProcessing/forceCoeffs/0/forceCoeffs.dat", [(t, 0.0, 0.30 + 0.001 * t, 0.1, 0, 0) for t in range(1, 101)])
    _dat(f"{case}/postProcessing/forceCoeffs/100/forceCoeffs.dat", [(t, 0.0, 0.40, 0.1, 0, 0) for t in range(100, 201)])
    last = kpi_value(case, {"name": "Cd", "path": "postProcessing/forceCoeffs/0/forceCoeffs.dat", "column": "Cd"})
    assert last["value"] == 0.40 and last["rows"] == 200
    mean = kpi_value(case, {"name": "Cd", "path": "postProcessing/forceCoeffs/0/forceCoeffs.dat", "column": 2,
                            "reduce": "mean_last", "n": 50})
    assert abs(mean["value"] - 0.40) < 1e-12 and mean["stable"] is True
    mx = kpi_value(case, {"name": "Cd", "path": "postProcessing/forceCoeffs/0/forceCoeffs.dat", "column": "Cd", "reduce": "max"})
    assert mx["value"] == 0.40
    missing = kpi_value(case, {"name": "x", "path": "postProcessing/none/0/a.dat", "column": 1})
    assert missing["value"] is None and missing["error"] == "file not found"


def test_quarantine_moves_and_never_deletes(tmp_path):
    case = tmp_path / "case"
    for proc in ("processor0", "processor1"):
        for t in ("0", "0.1", "0.2", "0.3"):
            d = case / proc / t
            d.mkdir(parents=True)
            (d / "U").write_text(f"{proc} {t}")
    good = heal.last_good_time(str(case), first_bad=0.25)
    assert good == "0.2"
    moved = heal.quarantine_after(str(case), good, attempt=1)
    assert sorted(moved) == ["processor0/0.3", "processor1/0.3"]
    kept = case / ".g4" / "quarantine" / "1" / "processor0" / "0.3" / "U"
    assert kept.read_text() == "processor0 0.3"
    assert sorted(os.listdir(case / "processor0")) == ["0", "0.1", "0.2"]
