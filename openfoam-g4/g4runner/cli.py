"""Command line: Mac side (submit, manifest, scan, estimate, doctor) and G4 side (colab-up, run, probe).

    python3 -m g4runner submit cases/myCase --gpu auto --kpi Cd:postProcessing/forceCoeffs/0/forceCoeffs.dat:Cd
    python3 -m g4runner colab-up --repo owner/name --branch main --watch
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Dict, List, Optional

from . import RETENTION, __version__, capacity, jobs, manifest, security

G4_HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _say(msg: str, level: str = "info") -> None:
    from .util import say

    say(msg, level)


# ----------------------------------------------------------------- Mac side
def _parse_set(text: str) -> Dict:
    """``file:entry=value``"""
    if ":" not in text or "=" not in text:
        raise argparse.ArgumentTypeError(f"--set expects file:entry=value, got {text!r}")
    file_, rest = text.split(":", 1)
    entry, value = rest.split("=", 1)
    return {"file": file_, "entry": entry, "value": value}


def _parse_kpi(text: str) -> Dict:
    """``name:path:column[:reduce[:n]]``"""
    parts = text.split(":")
    if len(parts) < 3:
        raise argparse.ArgumentTypeError("--kpi expects name:path:column[:reduce[:n]]")
    k: Dict = {"name": parts[0], "path": parts[1], "column": int(parts[2]) if parts[2].isdigit() else parts[2]}
    if len(parts) > 3:
        k["reduce"] = parts[3]
    if len(parts) > 4:
        k["n"] = int(parts[4])
    return k


def _parse_variant(text: str) -> Dict:
    """``name:file:entry=value[,file:entry=value...]``"""
    name, _, rest = text.partition(":")
    sets = [_parse_set(s) for s in rest.split(",") if s] if rest else []
    return {"name": name, "set": sets}


def cmd_manifest(a: argparse.Namespace) -> int:
    m = manifest.build_manifest(a.case)
    if a.json:
        print(json.dumps(m, indent=1))
    else:
        print(f"{m['root']}  {m['count']} files  {m['bytes']} bytes  {a.case}")
    return 0


def cmd_scan(a: argparse.Namespace) -> int:
    f = security.scan_case(a.case)
    for x in f:
        print(f"{x['severity']:5s} {x['file']}: {x['why']}")
    print(f"{len(security.blocking(f))} blocking finding(s)")
    return 1 if security.blocking(f) else 0


def cmd_submit(a: argparse.Namespace) -> int:
    from . import gitio

    home = os.path.abspath(a.home or G4_HOME)
    job: Dict = {"schema": jobs.SCHEMA, "np": a.np if a.np == "auto" else int(a.np), "gpu": a.gpu,
                 "branch": a.target, "keep_times": a.keep_times, "max_hours": a.max_hours}
    if a.template:
        from . import apps

        if a.template not in apps.BY_ID or not apps.BY_ID[a.template].get("template"):
            _say(f"{a.template}: no automatic template; run 'python3 -m g4runner apps'", "err")
            return 2
        tpl = apps.BY_ID[a.template]["template"]
        for k, v in tpl.items():
            job[k] = v
        job["app"] = a.template
        job["title"] = apps.BY_ID[a.template]["name"]
        job["branch"] = "foundation"
        base, root = a.template + "-" + os.path.basename(tpl["source"]["tutorial"]), "0" * 64
    elif a.tutorial:
        job["source"] = {"tutorial": a.tutorial}
        base, root = os.path.basename(a.tutorial.rstrip("/")), "0" * 64
    else:
        case_abs = os.path.abspath(a.case)
        rel = os.path.relpath(case_abs, home).replace(os.sep, "/")
        if rel.startswith(".."):
            _say(f"case must live inside {home}", "err")
            return 2
        findings = security.scan_case(case_abs)
        blocks = security.blocking(findings)
        for b in blocks:
            _say(f"blocked: {b['file']}: {b['why']}", "warn")
        if blocks and not a.allow_blocked:
            _say("the G4 runner will refuse this case; fix it or pass --allow-blocked to submit anyway", "err")
            return 3
        m = manifest.build_manifest(case_abs)
        job["source"] = {"case": rel}
        job["manifest"] = m
        base, root = os.path.basename(rel), m["root"]
    job["id"] = a.id or jobs.new_job_id(base, root)
    job["created"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if a.app:
        job["app"] = a.app
    if a.title:
        job["title"] = a.title
    if a.set:
        job["set"] = a.set
    if a.variant:
        job["variants"] = a.variant
    if a.kpi:
        job["kpi"] = a.kpi
    if a.init:
        job["stages"] = {"init": a.init}
    errs = jobs.validate_job(job)
    if errs:
        for e in errs:
            _say(e, "err")
        return 4
    jdir = os.path.join(home, "jobs")
    os.makedirs(jdir, exist_ok=True)
    jpath = os.path.join(jdir, f"{job['id']}.json")
    with open(jpath, "w", encoding="utf-8") as fh:
        json.dump(job, fh, indent=1, sort_keys=True)
        fh.write("\n")
    apath = os.path.join(jdir, "active.json")
    active = jobs.load_active(apath)
    if job["id"] not in active:
        active.append(job["id"])
    with open(apath, "w", encoding="utf-8") as fh:
        json.dump({"schema": 1, "active": active}, fh, indent=1)
        fh.write("\n")
    src_txt = ("tutorial " + job["source"]["tutorial"]) if "tutorial" in job["source"] else "SHA-256 " + root[:16] + "…"
    _say(f"job {job['id']} written ({src_txt})", "ok")
    if a.no_push:
        return 0
    paths = [jpath, apath] + ([os.path.join(home, job["source"]["case"])] if "case" in job["source"] else [])
    sha = gitio.commit_and_push(home, paths, f"g4: submit {job['id']}")
    _say(f"pushed {sha[:12]}; the G4 watcher picks it up within one polling interval", "ok")
    return 0


def cmd_submit_model(a: argparse.Namespace) -> int:
    from . import gitio

    home = os.path.abspath(a.home or G4_HOME)
    mdir = os.path.abspath(a.dir)
    rel = os.path.relpath(mdir, home).replace(os.sep, "/")
    if rel.startswith("..") or not os.path.isdir(mdir):
        _say(f"model folder must exist inside {home}", "err")
        return 2
    if not os.path.isfile(os.path.join(mdir, a.script)):
        _say(f"{a.script} not found in {rel}", "err")
        return 2
    m = manifest.build_manifest(mdir)
    job = {"schema": jobs.SCHEMA, "kind": "model", "id": a.id or jobs.new_job_id(os.path.basename(rel), m["root"]),
           "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "max_hours": a.max_hours,
           "model": {"dir": rel, "script": a.script, "args": a.args or [], "manifest": m}}
    if a.title:
        job["title"] = a.title
    errs = jobs.validate_job(job)
    if errs:
        for e in errs:
            _say(e, "err")
        return 4
    jdir = os.path.join(home, "jobs")
    os.makedirs(jdir, exist_ok=True)
    jpath = os.path.join(jdir, f"{job['id']}.json")
    with open(jpath, "w", encoding="utf-8") as fh:
        json.dump(job, fh, indent=1, sort_keys=True)
        fh.write("\n")
    apath = os.path.join(jdir, "active.json")
    active = jobs.load_active(apath)
    if job["id"] not in active:
        active.append(job["id"])
    with open(apath, "w", encoding="utf-8") as fh:
        json.dump({"schema": 1, "active": active}, fh, indent=1)
        fh.write("\n")
    _say(f"model job {job['id']} written (SHA-256 {m['root'][:16]}…, {m['count']} files)", "ok")
    if a.no_push:
        return 0
    sha = gitio.commit_and_push(home, [jpath, apath, mdir], f"g4: submit model {job['id']}")
    _say(f"pushed {sha[:12]}; the G4 runs it on the GPU whenever OpenFOAM is not using the GPU", "ok")
    return 0


def cmd_estimate(a: argparse.Namespace) -> int:
    inp = {k: v for k, v in vars(a).items() if k in capacity.DEFAULTS and v is not None}
    out = capacity.estimate(inp)
    out.pop("raw", None)
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


def cmd_apps(a: argparse.Namespace) -> int:
    from . import apps

    if a.json:
        print(json.dumps([dict(x, profile=apps.derive_profile(x), stages=apps.stages_for(x)) for x in apps.APPS],
                         indent=1, ensure_ascii=False))
        return 0
    for x in apps.APPS:
        tut = x["tutorial"] or "—"
        print(f"{x['id']}  {apps.PROFILES[apps.derive_profile(x)]:<24}  {' '.join(apps.stages_for(x)) or '—':<34}  "
              f"{tut:<52}  {x['name']}")
    return 0


def cmd_doctor(a: argparse.Namespace) -> int:
    from . import gitio

    ok = True
    _say(f"g4runner {__version__} · python {sys.version.split()[0]} · retention={RETENTION}")
    if sys.version_info < (3, 9):  # noqa: UP036 - runtime guard for old macOS pythons
        _say("python 3.9 or newer is required", "err")
        ok = False
    root = gitio.repo_root(G4_HOME)
    _say(f"git repo: {root or 'NOT A GIT REPO'} · branch {gitio.current_branch(G4_HOME) if root else '-'}",
         "ok" if root else "err")
    ok = ok and bool(root)
    for d in ("jobs", "cases"):
        p = os.path.join(G4_HOME, d)
        _say(f"{d}/: {'present' if os.path.isdir(p) else 'missing'}", "ok" if os.path.isdir(p) else "warn")
    return 0 if ok else 1


# ----------------------------------------------------------------- G4 side
def _hw(bench: bool) -> Dict:
    from .probe import probe, summary_lines

    hw = probe(bench=bench)
    for line in summary_lines(hw):
        _say(line)
    return hw


def cmd_probe(a: argparse.Namespace) -> int:
    hw = _hw(a.bench)
    if a.json:
        print(json.dumps(hw, indent=1, default=str))
    return 0


def _workdir_in_ram(hw: Dict) -> Dict:
    """Put the work dir on a RAM disk big enough for the run (zero retention)."""
    from .probe import shm_info
    from .util import human_bytes, prepare_workdir

    want = min(16 << 30, hw["mem"]["total"] // 4)
    path, in_ram = prepare_workdir(want, hw["mem"]["total"])
    hw["shm"] = shm_info(path)
    _say(f"thư mục làm việc {path} · {'RAM (tmpfs)' if in_ram else 'ĐĨA tạm của VM'} · trống {human_bytes(hw['shm']['free'])}",
         "ok" if in_ram else "warn")
    return hw


def _capacity_banner(hw: Dict) -> None:
    from .util import human_bytes

    g = hw["gpu"]
    vram = (g["gpus"][0].get("memory.total") or 0) / 1024.0 if g.get("present") else 0.0
    est = capacity.estimate({
        "cores_physical": hw["cpu"]["physical"], "ram_gb": hw["mem"]["available"] / 1e9, "vram_gb": vram,
        "cpu_bw_gbs": hw["cpu"].get("triad_GBs") or capacity.DEFAULTS["cpu_bw_gbs"],
        "gpu_bw_gbs": (g.get("bench") or {}).get("d2d_GBs") or capacity.DEFAULTS["gpu_bw_gbs"],
        "cells_m": 10.0, "physics": "incompressible_rans", "iterations": 2000.0,
    })
    _say(f"Năng lực đo được: {hw['cpu']['physical']} lõi → {hw['cpu']['physical']} tiến trình MPI ghim lõi; "
         f"RAM cho tối đa ~{est['cells_max_m']} triệu ô (RANS không nén); "
         f"RAM-disk {human_bytes(hw['shm']['free'])}; GPU {'có' if g.get('present') else 'không'}")
    _say(f"Ví dụ 10 triệu ô × 2000 vòng: CPU ~{est['hours_cpu']} h; GPU tăng tốc ước tính {est['speedup']}x "
         f"→ {'dùng GPU' if est['use_gpu'] else 'giữ CPU'}; ~{est['cu']} CU")


def _session_deadline(hours: float) -> float:
    return time.time() + hours * 3600.0


def _solver_cpus(groups, physical: int, reserved: List[int]):
    """Cores and --cpu-set for the solver when background work holds ``reserved`` CPUs (no SMT)."""
    keep = [g[0] for g in groups if g[0] not in set(reserved)]
    if not reserved or len(keep) == len(groups) or not keep:
        return physical, None
    return len(keep), ",".join(str(c) for c in keep)


def _start_gpu(env: Dict[str, str], hw: Dict, no_build: bool):
    from . import gpu, plan
    from .foam import branch_of

    arbiter = gpu.GpuArbiter()
    builder = None if no_build else gpu.start_builder(env, hw, plan.core_groups(), branch_of(env))
    return builder, arbiter


def cmd_run(a: argparse.Namespace) -> int:
    from .install import ensure_openfoam
    from .runner import JobRun

    hw = _workdir_in_ram(_hw(a.bench))
    env = ensure_openfoam(a.openfoam)
    job = jobs.load_job(a.job)
    builder, arbiter = _start_gpu(env, hw, a.no_gpu_build)
    from . import plan

    groups = plan.core_groups()
    reserved = builder.cpus if builder is not None and not any(len(g) > 1 for g in groups) else []
    cores, cpu_set = _solver_cpus(groups, int(hw["cpu"]["physical"]), reserved or [])
    rep = JobRun(job, os.path.abspath(a.home or G4_HOME), hw, env, _session_deadline(a.session_hours),
                 cores=cores, cpu_set=cpu_set, builder=builder, arbiter=arbiter).run()
    if a.json:
        print(json.dumps(rep, indent=1, default=str, ensure_ascii=False))
    return 0 if rep.get("status") in ("converged", "completed") else 5


def cmd_colab_up(a: argparse.Namespace) -> int:
    """Watch jobs/active.json and keep the CPU and the GPU busy at the same time.

    Lane 1 (OpenFOAM, one job at a time): every physical core; the pressure solve moves
    to the GPU when the background OGL build is ready and a measurement shows a gain.
    Lane 2 (models): while no OpenFOAM job holds the GPU, a signed model script runs on it,
    on CPU threads the solver does not use.
    """
    import threading

    from . import gitio, gpu, models, plan
    from .install import ensure_openfoam
    from .runner import JobRun
    from .util import ram_workdir

    _say(f"g4runner {__version__} · chế độ lưu: {RETENTION} (không ghi log, không lưu dữ liệu)")
    deadline = _session_deadline(a.session_hours)
    hw = _workdir_in_ram(_hw(not a.no_bench))
    if hw["mem"]["swap_total"]:
        _say("swap đang bật: trang RAM có thể bị đẩy xuống đĩa; tắt swap nếu cần tuyệt đối không ghi đĩa", "warn")
    _capacity_banner(hw)
    env = ensure_openfoam(a.openfoam)
    builder, arbiter = _start_gpu(env, hw, a.no_gpu_build)
    groups = plan.core_groups()
    smt = any(len(g) > 1 for g in groups)
    physical = int(hw["cpu"]["physical"])
    model_cpus = gpu.background_cpus(groups, share=1)[0][: max(1, physical // 8)]
    home = os.path.abspath(a.home or G4_HOME)
    repo_dest = None
    if a.repo:
        repo_dest = os.path.join(ram_workdir(), "repo")
        sha = gitio.clone_readonly(a.repo, a.branch, repo_dest)
        _say(f"repo {a.repo}@{a.branch} {sha[:12]} cloned into RAM", "ok")
        home = os.path.join(repo_dest, a.subdir) if a.subdir else repo_dest
    seen: List[str] = []
    of_queue: List[Dict] = []
    model_queue: List[Dict] = []
    reports: List[Dict] = []
    lock = threading.Lock()
    of_thread: Optional[threading.Thread] = None
    of_cores = [physical]
    model_task: Optional[models.ModelTask] = None
    last_status = 0.0

    def run_of(job: Dict, cores: int, cpu_set: Optional[str], block: Optional[str]) -> None:
        rep = JobRun(job, home, hw, env, deadline, cores=cores, cpu_set=cpu_set, builder=builder,
                     arbiter=arbiter, gpu_block_reason=block).run()
        with lock:
            reports.append(rep)

    while True:
        if repo_dest:
            try:
                gitio.update_readonly(repo_dest, a.branch)
            except RuntimeError as exc:
                _say(f"fetch failed, will retry next round: {exc}", "warn")
        for jid in jobs.load_active(os.path.join(home, "jobs", "active.json")):
            if jid in seen:
                continue
            seen.append(jid)
            try:
                job = jobs.load_job(os.path.join(home, "jobs", f"{jid}.json"))
            except (OSError, ValueError) as exc:
                _say(f"skip {jid}: {exc}", "err")
                continue
            (model_queue if job.get("kind") == "model" else of_queue).append(job)
        time_left = deadline - time.time()

        # lane 2: a model takes the GPU only when nobody holds it
        if model_task is not None and not model_task.is_alive():
            with lock:
                reports.append(model_task.report)
            model_task = None
        of_busy = of_thread is not None and of_thread.is_alive()
        if model_task is None and model_queue and not arbiter.busy() and time_left > 600:
            job = model_queue[0]
            if not models.allowed_by_operator():
                _say(f"{job['id']}: model jobs are off; set G4_ALLOW_MODELS=1 in the notebook to allow them", "warn")
                with lock:
                    reports.append({"id": job["id"], "kind": "model", "status": "refused", "error": "G4_ALLOW_MODELS not set"})
                model_queue.pop(0)
            elif not hw["gpu"].get("present") or not hw["gpu"].get("healthy"):
                _say(f"{job['id']}: no healthy GPU for a model", "warn")
                with lock:
                    reports.append({"id": job["id"], "kind": "model", "status": "refused", "error": "no healthy GPU"})
                model_queue.pop(0)
            elif smt or not of_busy or of_cores[0] < physical:
                model_queue.pop(0)
                model_task = models.ModelTask(job, home, model_cpus, arbiter, deadline)
                model_task.start()

        # lane 1: OpenFOAM, one job at a time on every core it may use
        if not of_busy and of_queue and time_left > 600:
            job = of_queue.pop(0)
            model_active = model_task is not None or bool(model_queue)
            reserved: List[int] = []
            if not smt:
                if model_active:
                    reserved += model_cpus
                if builder is not None and not builder.finished():
                    reserved += builder.cpus or []
            cores, cpu_set = _solver_cpus(groups, physical, reserved)
            of_cores[0] = cores
            block = f"GPU đang chạy mô hình {model_task.job['id']}" if model_task is not None else None
            of_thread = threading.Thread(target=run_of, args=(job, cores, cpu_set, block), daemon=True)
            of_thread.start()
        elif of_queue and time_left <= 600:
            _say("less than 10 minutes of session left; not starting new jobs", "warn")
            of_queue.clear()

        if builder is not None and time.time() - last_status > 300 and not builder.finished():
            _say(builder.status_line())
            last_status = time.time()
        running = (of_thread is not None and of_thread.is_alive()) or model_task is not None
        if not a.watch and not running and not of_queue and not model_queue:
            bad = [r["id"] for r in reports if r.get("status") not in ("converged", "completed")]
            if bad:
                _say(f"{len(bad)} job(s) did not finish cleanly: {', '.join(bad)}", "warn")
            return 5 if bad else 0
        if a.watch and time_left < 600 and not running:
            _say("session deadline reached; watcher stops", "info")
            return 0
        time.sleep(2.0 if running or of_queue or model_queue else a.interval)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="g4runner", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"g4runner {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("manifest", help="SHA-256 manifest of a case")
    s.add_argument("case")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_manifest)

    s = sub.add_parser("scan", help="security scan of a case")
    s.add_argument("case")
    s.set_defaults(fn=cmd_scan)

    s = sub.add_parser("submit", help="Mac: write a job, add it to jobs/active.json, commit and push")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("case", nargs="?")
    g.add_argument("--tutorial", help="run an installed tutorial, e.g. incompressibleFluid/pitzDailySteady")
    g.add_argument("--template", help="ready job of an application, ud01..ud21 (see 'apps')")
    s.add_argument("--home", help=argparse.SUPPRESS)
    s.add_argument("--id")
    s.add_argument("--app", help="application id ud01..ud21 from the report")
    s.add_argument("--title")
    s.add_argument("--np", default="auto")
    s.add_argument("--gpu", default="auto", choices=["auto", "on", "off"])
    s.add_argument("--target", default="auto", choices=["auto", "foundation", "opencfd"])
    s.add_argument("--set", action="append", type=_parse_set, help="file:entry=value (repeatable)")
    s.add_argument("--variant", action="append", type=_parse_variant, help="name:file:entry=value[,..] (repeatable)")
    s.add_argument("--kpi", action="append", type=_parse_kpi, help="name:path:column[:reduce[:n]] (repeatable)")
    s.add_argument("--init", action="append", choices=sorted(jobs.INIT_TOOLS))
    s.add_argument("--keep-times", type=int, default=2, dest="keep_times")
    s.add_argument("--max-hours", type=float, default=23.0, dest="max_hours")
    s.add_argument("--no-push", action="store_true")
    s.add_argument("--allow-blocked", action="store_true")
    s.set_defaults(fn=cmd_submit)

    s = sub.add_parser("submit-model", help="Mac: queue a signed model script for the GPU lane")
    s.add_argument("dir", help="folder with the script, inside the toolkit home, e.g. models/surrogate")
    s.add_argument("--script", default="main.py")
    s.add_argument("--id")
    s.add_argument("--title")
    s.add_argument("--max-hours", type=float, default=23.0, dest="max_hours")
    s.add_argument("--home", help=argparse.SUPPRESS)
    s.add_argument("--no-push", action="store_true")
    s.add_argument("args", nargs="*", help="arguments for the script, after a lone --")
    s.set_defaults(fn=cmd_submit_model)

    s = sub.add_parser("estimate", help="capacity model (same numbers as the report's calculator)")
    for k, v in capacity.DEFAULTS.items():
        if isinstance(v, bool):
            s.add_argument(f"--{k.replace('_', '-')}", dest=k, action="store_true", default=None)
        elif isinstance(v, str):
            s.add_argument(f"--{k.replace('_', '-')}", dest=k, choices=sorted(capacity.PHYSICS), default=None)
        else:
            s.add_argument(f"--{k.replace('_', '-')}", dest=k, type=float, default=None)
    s.set_defaults(fn=cmd_estimate)

    s = sub.add_parser("apps", help="the 21 applications: profile, stages TT0-TT8, OpenFOAM 14 tutorial")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_apps)

    s = sub.add_parser("doctor", help="Mac: check python, git and folders")
    s.set_defaults(fn=cmd_doctor)

    s = sub.add_parser("probe", help="G4: measure CPU, RAM, GPU, ECC (optionally bandwidth)")
    s.add_argument("--bench", action="store_true")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_probe)

    for name, fn, hlp in (("run", cmd_run, "G4: run one job file"), ("colab-up", cmd_colab_up, "G4: install, measure, watch jobs")):
        s = sub.add_parser(name, help=hlp)
        if name == "run":
            s.add_argument("job")
            s.add_argument("--bench", action="store_true")
            s.add_argument("--json", action="store_true")
        else:
            s.add_argument("--repo", help="owner/name to clone into RAM (omit when running inside a checkout)")
            s.add_argument("--branch", default="main")
            s.add_argument("--subdir", default="", help="toolkit folder inside the repo, e.g. openfoam-g4")
            s.add_argument("--watch", action="store_true")
            s.add_argument("--interval", type=float, default=30.0)
            s.add_argument("--no-bench", action="store_true")
        s.add_argument("--home", help=argparse.SUPPRESS)
        s.add_argument("--openfoam", default="14")
        s.add_argument("--session-hours", type=float, default=24.0, dest="session_hours")
        s.add_argument("--no-gpu-build", action="store_true", dest="no_gpu_build")
        s.set_defaults(fn=fn)

    a = p.parse_args(argv)
    try:
        return int(a.fn(a) or 0)
    except BrokenPipeError:  # output piped into head/less that closed early
        try:
            sys.stdout = open(os.devnull, "w")  # noqa: SIM115 - silence the interpreter's final flush
        except OSError:
            pass
        return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
