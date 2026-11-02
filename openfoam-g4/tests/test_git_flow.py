"""Mac -> Git -> G4 chain with a local bare repository standing in for GitHub."""

import json
import os
import subprocess

import pytest
from conftest import needs_foam

from g4runner import casegen, cli, gitio, jobs, util


def _git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture()
def mac_repo(tmp_path):
    bare = tmp_path / "remote.git"
    _git("init", "--bare", "-q", "-b", "main", str(bare))
    mac = tmp_path / "mac"
    _git("clone", "-q", str(bare), str(mac))
    _git("config", "user.email", "test@example.invalid", cwd=mac)
    _git("config", "user.name", "Mac M4", cwd=mac)
    (mac / "README").write_text("toolkit home\n")
    _git("add", "README", cwd=mac)
    _git("commit", "-q", "-m", "init", cwd=mac)
    _git("push", "-q", "-u", "origin", "main", cwd=mac)
    return bare, mac


def test_retry_backoff_schedule():
    calls, waits = [], []

    def flaky():
        calls.append(1)
        if len(calls) < 5:
            raise RuntimeError("network down")
        return "ok"

    assert util.retry(flaky, sleep=waits.append, what="push") == "ok"
    assert waits == [2, 4, 8, 16] and len(calls) == 5
    with pytest.raises(RuntimeError):
        util.retry(lambda: (_ for _ in ()).throw(RuntimeError("always")), sleep=lambda s: None)


def test_submit_pushes_job_and_g4_reads_it(mac_repo, tmp_path, ramdir):
    bare, mac = mac_repo
    case = mac / "cases" / "cav"
    casegen.cavity3d(str(case), n=8, steps=5, branch="foundation")
    rc = cli.main(["submit", str(case), "--home", str(mac), "--app", "ud15", "--title", "cavity smoke test",
                   "--kpi", "Fx:postProcessing/lidForce/0/force.dat:1"])
    assert rc == 0
    active = json.loads((mac / "jobs" / "active.json").read_text())["active"]
    assert len(active) == 1
    # the G4 side: read-only shallow clone into RAM, same bytes as the Mac
    dest = str(ramdir / "repo")
    sha = gitio.clone_readonly(f"file://{bare}", "main", dest)
    assert len(sha) == 40
    job = jobs.load_job(os.path.join(dest, "jobs", f"{active[0]}.json"))
    from g4runner import manifest
    ok, diffs, _ = manifest.verify(os.path.join(dest, job["source"]["case"]), job["manifest"])
    assert ok, diffs
    # a second submit is seen by update_readonly
    rc = cli.main(["submit", "--tutorial", "incompressibleFluid/cavity", "--home", str(mac)])
    assert rc == 0
    sha2 = gitio.update_readonly(dest, "main")
    assert sha2 != sha
    assert len(jobs.load_active(os.path.join(dest, "jobs", "active.json"))) == 2


def test_submit_refuses_blocked_case(mac_repo):
    _, mac = mac_repo
    case = mac / "cases" / "bad"
    casegen.cavity3d(str(case), n=4, steps=2, branch="foundation", functions=False)
    with open(case / "system" / "controlDict", "a") as fh:
        fh.write("\nx #codeStream { code #{ #}; };\n")
    assert cli.main(["submit", str(case), "--home", str(mac), "--no-push"]) == 3


@needs_foam
def test_colab_up_runs_active_job_from_remote(mac_repo, ramdir):
    from g4runner.foam import branch_of, foam_env

    bare, mac = mac_repo
    case = mac / "cases" / "run"
    casegen.cavity3d(str(case), n=12, steps=10, branch=branch_of(foam_env()), functions=False)
    assert cli.main(["submit", str(case), "--home", str(mac), "--np", "2"]) == 0
    rc = cli.main(["colab-up", "--repo", f"file://{bare}", "--branch", "main", "--no-bench", "--no-gpu-build",
                   "--session-hours", "1"])
    assert rc == 0
