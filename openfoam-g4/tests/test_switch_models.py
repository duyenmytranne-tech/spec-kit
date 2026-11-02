"""CPU+GPU in parallel: online switch state machine, the switch on a real OpenFOAM run, and the model lane.

The development machine has no GPU, so the end-to-end switch uses a stand-in
accelerator that swaps GAMG for PCG: it exercises exactly the same path
(measure, ``stopAt writeNow``, edit fvSolution, ``startFrom latestTime``,
measure, keep or revert) as the OGL accelerator.
"""

import os
import shutil
import time

from conftest import needs_foam

from g4runner import casegen, gpu, manifest, models, switch
from g4runner.monitor import LogParser


class FakeAccel:
    name = "PCG (stand-in)"

    def __init__(self, ready_after=0.0):
        self.t_ready = time.time() + ready_after
        self.applied = 0
        self.reverted = 0

    def ready(self):
        return time.time() >= self.t_ready

    def env(self, base):
        return dict(base)

    def apply(self, env, case, ranks):
        from g4runner.foam import set_entry

        keep = os.path.join(case, ".g4", "fvSolution.cpu")
        os.makedirs(os.path.dirname(keep), exist_ok=True)
        if not os.path.isfile(keep):
            shutil.copy2(os.path.join(case, "system", "fvSolution"), keep)
        set_entry(env, case, "system/fvSolution", "solvers/p/solver", "PCG")
        set_entry(env, case, "system/fvSolution", "solvers/p/preconditioner", "DIC")
        self.applied += 1
        return ["solvers/p/solver = PCG"]

    def revert(self, env, case):
        shutil.copy2(os.path.join(case, ".g4", "fvSolution.cpu"), os.path.join(case, "system", "fvSolution"))
        self.reverted += 1


def _plan(monkeypatch, accel, arbiter=None, forced=False, end=1000.0, m=4, expected=2.0):
    edits = []
    monkeypatch.setattr(switch, "get_entry", lambda env, case, rel, entry: {"endTime": str(end), "deltaT": "1"}.get(entry))
    monkeypatch.setattr(switch, "set_entry", lambda env, case, rel, entry, value: edits.append((entry, value)))
    monkeypatch.setattr(switch, "request_stop", lambda env, case, mode: edits.append(("stopAt", mode)))
    sp = switch.SwitchPlan(accel, {}, "/case", ("openfoam", "j:base"), arbiter, forced=forced, expected_speedup=expected, m_steps=m)
    sp.startup_s = 0.5
    return sp, edits


def _feed(sp, p, n, dt):
    for _ in range(n):
        p.steps += 1
        p.time = float(p.steps)
        p.step_wall.append(dt)
        sp.on_line(p)


def test_switch_keeps_gpu_when_faster(monkeypatch):
    arb = gpu.GpuArbiter()
    accel = FakeAccel(ready_after=1e9)  # still building
    sp, edits = _plan(monkeypatch, accel, arb)
    p = LogParser()
    _feed(sp, p, 6, 1.2)            # 6 CPU steps while the build shares the cores
    accel.t_ready = 0.0             # build finished
    _feed(sp, p, 5, 1.0)            # first step notices "ready", then m=4 unloaded CPU steps
    assert sp.pending == "gpu" and ("stopAt", "writeNow") in edits and arb.holder == ("openfoam", "j:base")
    assert sp.after_exit() == "gpu" and sp.phase == "gpu_trial"
    q = LogParser()
    _feed(sp, q, 6, 0.5)            # GPU twice as fast
    assert sp.phase == "gpu_kept" and sp.gpu_rate == 0.5 and sp.cpu_rate == 1.0
    sp.finish()
    assert arb.holder == ("openfoam", "j:base")   # still on the GPU until the job ends
    s = sp.summary()
    assert [e["event"] for e in s["events"]] == ["accelerator_ready", "switch_to_gpu", "keep_gpu"]
    assert s["cpu_s_per_step_during_build"] == 1.2 and s["measured_build_slowdown"] == round(1.0 / 1.2, 3)


def test_switch_reverts_when_not_10_percent_faster(monkeypatch):
    arb = gpu.GpuArbiter()
    sp, edits = _plan(monkeypatch, FakeAccel(), arb)
    p = LogParser()
    _feed(sp, p, 6, 1.0)
    sp.after_exit()
    q = LogParser()
    _feed(sp, q, 6, 0.95)           # only 5 % faster
    assert sp.pending == "cpu"
    assert sp.after_exit() == "cpu" and sp.phase == "cpu_final" and arb.holder is None


def test_switch_skipped_when_rest_is_short_or_gpu_busy(monkeypatch):
    sp, _ = _plan(monkeypatch, FakeAccel(), end=12.0)
    p = LogParser()
    _feed(sp, p, 8, 1.0)
    assert sp.phase == "cpu_final" and sp.pending is None
    assert sp.events[-1]["event"] == "stay_cpu" and "too short" in sp.events[-1]["reason"]
    arb = gpu.GpuArbiter()
    assert arb.try_acquire(("model", "m1"))
    sp2, _ = _plan(monkeypatch, FakeAccel(), arb)
    q = LogParser()
    _feed(sp2, q, 8, 1.0)
    assert sp2.phase == "cpu_final" and "another task" in sp2.events[-1]["reason"]


def test_background_cpu_split():
    smt = [[0, 24], [1, 25], [2, 26], [3, 27]]
    bg, solver = gpu.background_cpus(smt, share=1)
    assert bg == [24, 25, 26, 27] and solver == [0, 1, 2, 3]
    flat = [[0], [1], [2], [3]]
    bg, solver = gpu.background_cpus(flat, share=1)
    assert bg == [3] and solver == [0, 1, 2]
    assert gpu.limited(["make"], [3], 19)[-1] == "make"


def test_builder_fails_cleanly_without_gpu(ramdir):
    b = gpu.OglBuilder({}, {"gpu": {"present": False}}, None, "foundation")
    b.start()
    assert b.wait(30) is False and b.state == "failed" and "GPU" in b.error
    assert "không dựng được" in b.status_line()


@needs_foam
def test_online_switch_on_a_real_run(tmp_path, ramdir):
    """Same path as OGL: measure CPU, writeNow, swap solver, continue from latestTime, measure, decide."""
    from g4runner.foam import branch_of, foam_env
    from g4runner.probe import probe
    from g4runner.runner import JobRun

    env = foam_env()
    case = tmp_path / "cases" / "sw"
    casegen.cavity3d(str(case), n=22, steps=900, branch=branch_of(env), functions=False)
    casegen_dt = 0.5 * 0.1 / 22
    hw = probe()
    hw["gpu"] = {"present": True, "healthy": True, "nvcc": "/bin/true", "nvcc_version": "12.8",
                 "gpus": [{"memory.total": 98304.0, "compute_cap": "12.0"}]}
    job = {"schema": 1, "id": "t-switch", "source": {"case": "cases/sw"}, "manifest": manifest.build_manifest(str(case)),
           "min_cells_per_rank": 1000, "max_hours": 1, "gpu": "on",
           "set": [{"file": "system/controlDict", "entry": "writeInterval", "value": "50"}]}
    accel = FakeAccel(ready_after=2.0)
    arb = gpu.GpuArbiter()
    rep = JobRun(job, str(tmp_path), hw, env, time.time() + 3600, accel=accel, arbiter=arb).run()
    assert rep["status"] == "completed", rep.get("error")
    v = rep["variants"][0]
    sw = v["switch"]
    assert accel.applied == 1 and sw["phase"] == "gpu_kept"     # forced mode keeps the accelerator
    assert [e["event"] for e in sw["events"]][:2] == ["accelerator_ready", "switch_to_gpu"]
    assert abs(v["log"]["time"] - casegen_dt * 900) < 1e-5 * casegen_dt * 900   # reached endTime after the restart
    assert v["gpu"] is True
    with open(os.path.join(os.environ["G4_WORKDIR"], "run", "t-switch", "base", "system", "fvSolution")) as fh:
        assert "PCG" in fh.read()


def _model_dir(home, body):
    d = home / "models" / "probe"
    d.mkdir(parents=True)
    (d / "main.py").write_text(body)
    return d


MODEL_BODY = """import os, sys
print("AFFINITY", sorted(os.sched_getaffinity(0)))
print("TOKEN", "G4_GIT_TOKEN" in os.environ)
print("HF_HOME", os.environ.get("HF_HOME"))
print("ARGS", sys.argv[1:])
"""


def _model_job(d, home):
    return {"schema": 1, "kind": "model", "id": "m-probe", "max_hours": 1,
            "model": {"dir": os.path.relpath(d, home), "script": "main.py", "args": ["--epochs", "2"],
                      "manifest": manifest.build_manifest(str(d))}}


def test_model_lane_runs_isolated(tmp_path, ramdir, monkeypatch, capsys):
    from g4runner import jobs

    d = _model_dir(tmp_path, MODEL_BODY)
    job = _model_job(d, tmp_path)
    assert jobs.validate_job(job) == []
    monkeypatch.setenv("G4_ALLOW_MODELS", "1")
    monkeypatch.setenv("G4_GIT_TOKEN", "secret-value")
    cpus = [sorted(os.sched_getaffinity(0))[-1]]
    arb = gpu.GpuArbiter()
    t = models.ModelTask(job, str(tmp_path), cpus, arb, time.time() + 600)
    t.start()
    t.join(60)
    out = capsys.readouterr().out
    assert t.report["status"] == "completed", t.report
    assert f"AFFINITY {cpus}" in out
    assert "TOKEN False" in out and "secret-value" not in out
    assert f"HF_HOME {os.path.join(str(ramdir), 'cache', 'hf')}" in out
    assert "ARGS ['--epochs', '2']" in out
    assert arb.holder is None


def test_model_lane_refusals(tmp_path, ramdir, monkeypatch):
    d = _model_dir(tmp_path, MODEL_BODY)
    job = _model_job(d, tmp_path)
    monkeypatch.delenv("G4_ALLOW_MODELS", raising=False)
    t = models.ModelTask(job, str(tmp_path), None, gpu.GpuArbiter(), time.time() + 600)
    t.run()
    assert t.report["status"] == "refused" and "G4_ALLOW_MODELS" in t.report["error"]
    monkeypatch.setenv("G4_ALLOW_MODELS", "1")
    (d / "main.py").write_text(MODEL_BODY + "print('changed after signing')\n")
    t = models.ModelTask(job, str(tmp_path), None, gpu.GpuArbiter(), time.time() + 600)
    t.run()
    assert t.report["status"] == "refused" and "differs" in t.report["error"]


@needs_foam
def test_watcher_runs_model_and_openfoam_together(tmp_path, ramdir, monkeypatch):
    """colab-up with one model job and one OpenFOAM job: both run at the same time, on separate CPUs."""
    import subprocess

    from g4runner import cli
    from g4runner.foam import branch_of, foam_env
    from g4runner.probe import probe

    home = tmp_path / "home"
    (home / "jobs").mkdir(parents=True)
    d = home / "models" / "slow"
    d.mkdir(parents=True)
    (d / "main.py").write_text("import os, time\nprint('MODEL_CPUS', sorted(os.sched_getaffinity(0)))\ntime.sleep(4)\nprint('MODEL_DONE')\n")
    case = home / "cases" / "c"
    casegen.cavity3d(str(case), n=12, steps=40, branch=branch_of(foam_env()), functions=False)
    subprocess.run(["git", "init", "-q", str(home)], check=True)
    assert cli.main(["submit-model", str(d), "--home", str(home), "--no-push", "--id", "m-slow"]) == 0
    assert cli.main(["submit", str(case), "--home", str(home), "--no-push", "--id", "of-c"]) == 0
    hw = probe()
    hw["gpu"] = {"present": True, "healthy": True, "nvcc": None, "gpus": [{"memory.total": 98304.0, "compute_cap": "12.0"}],
                 "ecc": {}, "count": 1}
    monkeypatch.setattr(cli, "_hw", lambda bench: hw)
    monkeypatch.setenv("G4_ALLOW_MODELS", "1")
    rc = cli.main(["colab-up", "--home", str(home), "--no-bench", "--no-gpu-build", "--session-hours", "1"])
    assert rc == 0
