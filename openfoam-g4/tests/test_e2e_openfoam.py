"""End-to-end runs with a real OpenFOAM + MPI (skipped when not installed).

These were the scenarios checked by hand while building the runner: a clean
parallel run, divergence healing, a deadline stop, concurrent variants on
disjoint cores, a refused case and a one-bit integrity failure.
"""

import os
import time

from conftest import needs_foam

from g4runner import casegen, manifest
from g4runner.foam import branch_of, foam_env
from g4runner.probe import probe
from g4runner.runner import JobRun


def _job(home, name, n, steps, functions=False, **extra):
    env = foam_env()
    case = os.path.join(home, "cases", name)
    casegen.cavity3d(case, n=n, steps=steps, branch=branch_of(env), functions=functions)
    job = {"schema": 1, "id": f"t-{name}", "source": {"case": f"cases/{name}"},
           "manifest": manifest.build_manifest(case), "np": "auto", "min_cells_per_rank": 1000, "max_hours": 1}
    job.update(extra)
    return job, case


def _run(job, home, window_h=1.0):
    env = foam_env()
    hw = probe(bench=False)
    return JobRun(job, str(home), hw, env, time.time() + window_h * 3600).run()


@needs_foam
def test_clean_parallel_run(tmp_path, ramdir):
    job, _ = _job(tmp_path, "clean", 20, 30)
    rep = _run(job, tmp_path)
    assert rep["status"] == "completed"
    assert rep["integrity"]["identical"] is True
    v = rep["variants"][0]
    physical = probe()["cpu"]["physical"]
    assert v["ranks"] == min(physical, 8000 // 1000)
    assert v["log"]["steps"] == 30 and v["log"]["ended"]
    assert rep["retention"] == "none"


@needs_foam
def test_divergence_is_healed(tmp_path, ramdir):
    dt = 0.5 * 0.1 / 20
    job, _ = _job(tmp_path, "div", 20, 400, heal={"max_attempts": 5}, set=[
        {"file": "system/controlDict", "entry": "deltaT", "value": f"{dt * 40:.9g}"},
        {"file": "system/controlDict", "entry": "endTime", "value": f"{dt * 40 * 30:.9g}"},
        {"file": "system/controlDict", "entry": "writeInterval", "value": "5"}])
    rep = _run(job, tmp_path)
    assert rep["status"] == "completed"
    assert len(rep["heal"]) >= 1
    assert any("deltaT" in c for c in rep["heal"][0]["changes"])
    assert rep["variants"][0]["healed"] is True


@needs_foam
def test_deadline_stops_cleanly(tmp_path, ramdir):
    job, _ = _job(tmp_path, "long", 16, 10_000_000, max_hours=0.01)
    rep = _run(job, tmp_path)
    assert rep["status"] == "stopped_at_deadline"
    assert rep["variants"][0]["log"]["steps"] > 10
    assert rep["seconds"] < 0.01 * 3600 + 30


@needs_foam
def test_concurrent_variants_on_disjoint_cores(tmp_path, ramdir):
    if (os.cpu_count() or 1) < 4:
        return
    job, _ = _job(tmp_path, "var", 16, 20, min_cores_per_job=2, variants=[
        {"name": "a", "set": []},
        {"name": "b", "set": [{"file": "system/controlDict", "entry": "deltaT", "value": "0.0015"}]}])
    rep = _run(job, tmp_path)
    assert rep["status"] == "completed"
    assert [v["variant"] for v in rep["variants"]] == ["a", "b"]
    assert all(v["ranks"] == 2 for v in rep["variants"])
    assert rep["variants"][0]["log"]["time"] != rep["variants"][1]["log"]["time"]


@needs_foam
def test_refusal_and_one_bit_integrity(tmp_path, ramdir):
    job, case = _job(tmp_path, "sec", 8, 5)
    with open(os.path.join(case, "system", "controlDict"), "a") as fh:
        fh.write("\nfunctions { s { type systemCall; executeCalls (\"true\"); } }\n")
    job["manifest"] = manifest.build_manifest(case)
    assert _run(job, tmp_path)["status"] == "refused"
    job2, case2 = _job(tmp_path, "bit", 8, 5)
    p = os.path.join(case2, "system", "fvSchemes")
    with open(p, "rb") as fh:
        data = bytearray(fh.read())
    data[50] ^= 0x04
    with open(p, "wb") as fh:
        fh.write(bytes(data))
    rep = _run(job2, tmp_path)
    assert rep["status"] == "integrity_failed" and "fvSchemes" in rep["error"]
