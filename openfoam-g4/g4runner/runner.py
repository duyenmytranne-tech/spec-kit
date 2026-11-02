"""Execute a job through the execution stages TT0-TT8, entirely in RAM.

TT0 environment + integrity   TT1 mesh            TT2 conditions + init
TT3 solver                    TT4 parallel + GPU  TT5 coupling + plugins
TT6 measurement (KPI)         TT7 output (console only)
TT8 verification, convergence, self-healing

Each stage TTk carries out function group CNk of the report, which is
what links the application layer (ud01..ud21) to the commands that run.
"""

from __future__ import annotations

import os
import re
import shutil
import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

from . import RETENTION, allrun, heal, manifest, plan, security
from .switch import OglAccelerator, SwitchPlan
from .foam import (
    Stream, branch_of, case_features, count_cells, decompose_body, features_tool, latest_time,
    mpi_command, mpi_flavour, request_stop, say_tail, set_entry, solver_command, write_dict,
)
from .monitor import LogParser, UtilSampler
from .util import fmt_duration, human_bytes, ram_workdir, say

STAGE_NAMES = {
    "TT0": "Môi trường và toàn vẹn", "TT1": "Lưới", "TT2": "Điều kiện và khởi tạo", "TT3": "Bộ giải",
    "TT4": "Song song và GPU", "TT5": "Ghép nối và mở rộng", "TT6": "Đo đạc", "TT7": "Đầu ra",
    "TT8": "Kiểm chứng và hội tụ",
}


class JobError(Exception):
    def __init__(self, status: str, msg: str):
        super().__init__(msg)
        self.status = status


# ----------------------------------------------------------------- helpers
def _copy_case_files(src: str, dst: str) -> None:
    """Copy exactly the files the manifest covers (nothing generated, no macOS metadata)."""
    for rel in manifest.iter_case_files(src):
        s, d = os.path.join(src, rel), os.path.join(dst, rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        if os.path.islink(s):
            os.symlink(os.readlink(s), d)
        else:
            shutil.copy2(s, d)


def _tutorial_resources(case: str, tut_root: str) -> List[str]:
    """Do what a tutorial Allrun does with resource files, without running Allrun."""
    done: List[str] = []
    allrun = os.path.join(case, "Allrun")
    if not os.path.isfile(allrun):
        return done
    with open(allrun, encoding="utf-8", errors="replace") as fh:
        text = fh.read()

    def expand(p: str) -> str:
        return p.replace("$FOAM_TUTORIALS", tut_root).replace("${FOAM_TUTORIALS}", tut_root)

    m = re.search(r"blockMesh\s+-dict\s+(\S+)", text)
    if m and not os.path.isfile(os.path.join(case, "system", "blockMeshDict")):
        src = expand(m.group(1))
        if os.path.realpath(src).startswith(os.path.realpath(tut_root)) and os.path.isfile(src):
            shutil.copy2(src, os.path.join(case, "system", "blockMeshDict"))
            done.append(f"blockMeshDict <- {os.path.relpath(src, tut_root)}")
    for cp in re.finditer(r"^\s*cp\s+(?:-r\s+)?(\$\{?FOAM_TUTORIALS\}?/resources/\S+)\s+(\S+)\s*$", text, re.M):
        src, dst = expand(cp.group(1)), cp.group(2)
        if ".." in dst or dst.startswith("/"):
            continue
        dpath = os.path.join(case, dst)
        if dst.endswith("/"):
            os.makedirs(dpath, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(dpath) or case, exist_ok=True)
        if os.path.isfile(src):
            shutil.copy2(src, dpath)
            done.append(f"{dst} <- {os.path.relpath(src, tut_root)}")
    return done


def _set_many(env: Dict[str, str], case: str, sets: List[Dict]) -> List[str]:
    applied = []
    for s in sets:
        set_entry(env, case, s["file"], s["entry"], str(s["value"]))
        applied.append(f"{s['file']}: {s['entry']} = {s['value']}")
    return applied


def _move_aside(case: str, rel: str, tag: str) -> None:
    src = os.path.join(case, rel)
    if os.path.exists(src):
        dest = os.path.join(case, ".g4", "aside", tag, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(src, dest)


def _processor_dirs(case: str) -> List[str]:
    return sorted(d for d in os.listdir(case) if re.match(r"^processor\d+$", d))


def _read_rows(path: str) -> Tuple[List[str], List[List[str]]]:
    header: List[str] = []
    rows: List[List[str]] = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            s = line.strip()
            if not s:
                continue
            if s.startswith("#"):
                toks = s.lstrip("#").split()
                if toks and toks[0].lower() == "time":
                    header = toks
                continue
            rows.append(re.findall(r"\([^()]*\)|\S+", s))
    return header, rows


def kpi_value(case: str, spec: Dict) -> Dict:
    """Collect a KPI from function-object output (all restart folders, sorted by time)."""
    parts = spec["path"].split("/")
    out = {"name": spec["name"], "value": None, "stable": None, "rows": 0}
    if len(parts) >= 4 and re.match(r"^[-+0-9.eE]+$", parts[2]):
        fo_dir = os.path.join(case, parts[0], parts[1])
        fname = "/".join(parts[3:])
        cands = []
        if os.path.isdir(fo_dir):
            for t in os.listdir(fo_dir):
                p = os.path.join(fo_dir, t, fname)
                if os.path.isfile(p):
                    cands.append(p)
    else:
        p = os.path.join(case, spec["path"])
        cands = [p] if os.path.isfile(p) else []
    if not cands:
        out["error"] = "file not found"
        return out
    by_time: Dict[float, float] = {}
    for p in cands:
        header, rows = _read_rows(p)
        col = spec["column"]
        idx = col if isinstance(col, int) else (header.index(col) if col in header else None)
        if idx is None:
            out["error"] = f"column {col!r} not in header {header}"
            continue
        for r in rows:
            if len(r) <= idx:
                continue
            try:
                t, v = float(r[0]), float(r[idx])
            except ValueError:
                continue
            by_time[t] = v
    vals = [by_time[t] for t in sorted(by_time)]
    out["rows"] = len(vals)
    if not vals:
        return out
    red, n = spec.get("reduce", "last"), max(1, int(spec.get("n", 1)))
    if red == "last":
        out["value"] = vals[-1]
    elif red == "max":
        out["value"] = max(vals)
    elif red == "min":
        out["value"] = min(vals)
    else:
        tail = vals[-n:]
        out["value"] = sum(tail) / len(tail)
    if len(vals) >= 4:
        w = min(n, len(vals) // 2) if red == "mean_last" else min(50, len(vals) // 2)
        a, b = vals[-2 * w:-w], vals[-w:]
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        rel = abs(mb - ma) / max(abs(mb), 1e-30)
        out["drift"] = rel
        out["stable"] = rel < 0.01
    return out


# ----------------------------------------------------------------- the job
class JobRun:
    def __init__(self, job: Dict, repo_dir: Optional[str], hw: Dict, env: Dict[str, str],
                 session_deadline: float, cores: Optional[int] = None, cpu_set: Optional[str] = None,
                 builder=None, arbiter=None, accel=None, gpu_block_reason: Optional[str] = None):
        """``builder``: background OGL build (gpu.OglBuilder); ``arbiter``: who holds the GPU;
        ``accel``: accelerator object (defaults to OGL from ``builder``; tests inject a stand-in);
        ``gpu_block_reason``: set by the watcher while a model task owns the GPU."""
        self.job, self.repo_dir, self.hw, self.env = job, repo_dir, hw, env
        self.branch = branch_of(env)
        self.physical = int(hw["cpu"]["physical"])
        self.cores = int(cores or self.physical)
        if cpu_set is None and int(hw["cpu"].get("threads_per_core", 1)) > 1:
            # one rank per core on its primary thread; siblings stay free for the OGL build or a model
            primaries = [g[0] for g in plan.core_groups()][: self.cores]
            cpu_set = ",".join(str(c) for c in primaries)
        self.cpu_set = cpu_set
        self.builder, self.arbiter = builder, arbiter
        self.accel = accel or (OglAccelerator(builder) if builder is not None else None)
        self.gpu_block_reason = gpu_block_reason
        self.flavour = mpi_flavour(env)
        self.solver_override: Optional[List[str]] = None
        self.region_args: List[str] = []
        self.bind = True
        self.mpi_extra_env: Dict[str, str] = {}
        self.t0 = time.time()
        self.deadline = min(session_deadline, self.t0 + float(job.get("max_hours", 23.0)) * 3600.0)
        # stop early enough to report: 3 minutes, or 10 % of a short window
        self.margin = min(180.0, 0.1 * max(0.0, self.deadline - self.t0))
        self.root = os.path.join(ram_workdir(), "run", job["id"])
        self.report: Dict = {"id": job["id"], "app": job.get("app"), "title": job.get("title"),
                             "retention": RETENTION, "openfoam": env.get("WM_PROJECT_VERSION"),
                             "branch": self.branch, "stages": {}, "variants": [], "heal": [], "notes": []}

    # -- utilities -------------------------------------------------------
    def stage(self, code: str, detail: str, t_start: float, ok: bool = True) -> None:
        dt = time.time() - t_start
        self.report["stages"].setdefault(code, []).append({"detail": detail, "seconds": round(dt, 1), "ok": ok})
        say(f"{code} {STAGE_NAMES[code]} · {detail} · {fmt_duration(dt)}", "ok" if ok else "warn")

    def time_left(self) -> float:
        return self.deadline - time.time()

    def run_tool(self, args: List[str], case: str, parallel: int = 1, env: Optional[Dict[str, str]] = None,
                 parser: Optional[LogParser] = None, should_stop: Optional[Callable[[], bool]] = None,
                 on_stop: Optional[Callable[[], None]] = None) -> Tuple[int, Stream]:
        run_env = dict(env or self.env)
        run_env.update(self.mpi_extra_env)
        cmd = (mpi_command(args, parallel, self.physical, self.flavour, bind=self.bind,
                           cpu_set=self.cpu_set if self.flavour == "openmpi" else None)
               if parallel > 1 else list(args))
        st = Stream(cmd, case, run_env, parser.feed if parser else None)
        rc = st.run(should_stop=should_stop, on_stop=on_stop)
        if rc != 0 and parallel > 1 and parser is not None and parser.mpi_problem and not self.mpi_extra_env.get("_retried"):
            fix = parser.mpi_problem
            say(f"MPI problem '{fix}' detected; retrying with a safer launch", "warn")
            self.mpi_extra_env["_retried"] = "1"
            if fix == "cma":
                self.mpi_extra_env["OMPI_MCA_btl_vader_single_copy_mechanism"] = "none"
            elif fix in ("bind", "slots"):
                self.bind = False
            self.report["notes"].append(f"MPI launch adjusted for '{fix}'")
            parser.reset()
            return self.run_tool(args, case, parallel, env, parser, should_stop, on_stop)
        return rc, st

    def must(self, args: List[str], case: str, parallel: int = 1, what: str = "") -> Stream:
        parser = LogParser()
        rc, st = self.run_tool(args, case, parallel, parser=parser)
        if rc != 0 or parser.fatal:
            say_tail(st)
            raise JobError("failed", f"{what or args[0]} exited with {rc}")
        return st

    # -- TT0 ----------------------------------------------------------------
    def tt0_prepare(self) -> str:
        t = time.time()
        if os.path.exists(self.root):
            # an earlier run of this job id in the same session: keep it (no deletion), start clean
            prev = os.path.join(os.path.dirname(self.root), ".previous", f"{self.job['id']}-{int(t)}")
            os.makedirs(os.path.dirname(prev), exist_ok=True)
            shutil.move(self.root, prev)
            self.report["notes"].append(f"previous run of this job kept at {prev}")
        os.makedirs(self.root, mode=0o700, exist_ok=True)
        base = os.path.join(self.root, "base")
        src = self.job["source"]
        want = self.job.get("branch", "auto")
        if want != "auto" and want != self.branch:
            raise JobError("refused", f"job targets {want} but this runtime has {self.branch} "
                                      f"{self.env.get('WM_PROJECT_VERSION')}")
        if "case" in src:
            if not self.repo_dir:
                raise JobError("refused", "case jobs need the repository checkout")
            case_src = os.path.join(self.repo_dir, src["case"])
            if not os.path.isdir(case_src):
                raise JobError("integrity_failed", f"case folder {src['case']} not in the checkout")
            ok, diffs, actual = manifest.verify(case_src, self.job["manifest"])
            if not ok:
                raise JobError("integrity_failed", "checkout differs from the Mac manifest: " + "; ".join(diffs[:8]))
            _copy_case_files(case_src, base)
            ok2, diffs2, _ = manifest.verify(base, self.job["manifest"])
            if not ok2:
                raise JobError("integrity_failed", "RAM copy differs: " + "; ".join(diffs2[:8]))
            self.report["integrity"] = {"root": actual["root"], "files": actual["count"], "bytes": actual["bytes"],
                                        "identical": True}
        else:
            tut_root = self.env.get("FOAM_TUTORIALS", "")
            tsrc = os.path.join(tut_root, src["tutorial"])
            if not tut_root or not os.path.isdir(tsrc):
                raise JobError("refused", f"tutorial {src['tutorial']} not found in {tut_root or '$FOAM_TUTORIALS'}")
            shutil.copytree(tsrc, base, symlinks=True)
            res = _tutorial_resources(base, tut_root)
            m = manifest.build_manifest(base)
            self.report["integrity"] = {"root": m["root"], "files": m["count"], "bytes": m["bytes"],
                                        "source": f"tutorial {src['tutorial']} of OpenFOAM {self.env.get('WM_PROJECT_VERSION')}",
                                        "resources": res}
        if not os.path.isdir(os.path.join(base, "0")) and os.path.isdir(os.path.join(base, "0.orig")):
            shutil.copytree(os.path.join(base, "0.orig"), os.path.join(base, "0"))
        findings = security.scan_case(base)
        blocks = security.blocking(findings)
        self.report["security"] = findings
        if blocks and not security.allowed_by_operator():
            raise JobError("refused", "case contains code-executing entries: " +
                           "; ".join(f"{b['file']}: {b['why']}" for b in blocks[:5]) +
                           " (operator can allow with G4_ALLOW_CODED=1)")
        applied = _set_many(self.env, base, self.job.get("set", []))
        if applied:
            self.report["set"] = applied
        self.stage("TT0", f"{self.report['integrity']['files']} tệp, SHA-256 {self.report['integrity']['root'][:12]}…, "
                          f"{len(blocks)} chặn", t)
        return base

    # -- TT1 ----------------------------------------------------------------
    def tt1_mesh(self, case: str, ranks: int) -> bool:
        """Mesh the base case. Returns True if the mesh ends up decomposed (parallel snappy)."""
        t = time.time()
        st = self.job.get("stages", {})
        mode = st.get("mesh", "auto")
        if os.path.isfile(os.path.join(case, "constant", "regionProperties")):
            self.region_args = ["-allRegions"]
        has_mesh = count_cells(case) is not None
        decomposed = False
        if mode == "auto" and os.path.isfile(os.path.join(case, "Allrun")):
            decomposed = self.run_allrun_plan(case, ranks)
            mode = "Allrun (lệnh OpenFOAM trong danh sách cho phép)"
        elif mode == "auto":
            if has_mesh:
                mode = "none"
            elif os.path.isfile(os.path.join(case, "system", "snappyHexMeshDict")):
                mode = "blockMesh+snappyHexMesh"
            elif os.path.isfile(os.path.join(case, "system", "blockMeshDict")):
                mode = "blockMesh"
            else:
                raise JobError("failed", "no mesh and no blockMeshDict/snappyHexMeshDict")
        if mode in ("blockMesh", "blockMesh+snappyHexMesh"):
            self.must(["blockMesh"], case, what="blockMesh")
        if mode in ("snappyHexMesh", "blockMesh+snappyHexMesh"):
            feat = features_tool(self.env)
            for dname in ("surfaceFeaturesDict", "surfaceFeatureExtractDict"):
                if feat and os.path.isfile(os.path.join(case, "system", dname)):
                    self.must([feat], case, what=feat)
                    break
            ow = ["-overwrite"] if self.branch == "opencfd" else []
            if ranks > 1:
                try:
                    self.decompose(case, ranks, extra=["-copyZero"])
                    self.must(["snappyHexMesh"] + ow, case, parallel=ranks, what="snappyHexMesh -parallel")
                    decomposed = True
                except JobError:
                    say("parallel snappyHexMesh failed; falling back to serial meshing", "warn")
                    for d in _processor_dirs(case):
                        _move_aside(case, d, "snappy-parallel-failed")
                    self.report["notes"].append("snappyHexMesh: parallel failed, serial fallback used")
            if not decomposed:
                self.must(["snappyHexMesh"] + ow, case, what="snappyHexMesh")
            self.aside_levels(case)
        if count_cells(case) is None:
            raise JobError("failed", "no mesh after the meshing stage")
        cells = count_cells(case) or 0
        renumbered = any(s["tool"] == "renumberMesh" for s in self.report.get("allrun", {}).get("steps", []))
        if st.get("renumber", True) and cells >= 50_000 and not renumbered:
            ow = ["-overwrite"] if self.branch == "opencfd" else []
            self.must(["renumberMesh"] + ow + self.region_args, case, parallel=ranks if decomposed else 1, what="renumberMesh")
        if st.get("checkMesh", True):
            parser = LogParser()
            rc, stream = self.run_tool(["checkMesh"] + self.region_args, case, ranks if decomposed else 1, parser=parser)
            if rc != 0 or (parser.mesh_failed or 0) > 0:
                say_tail(stream)
                raise JobError("mesh_failed", f"checkMesh: {parser.mesh_failed or 'error'} failed checks")
        self.report["cells"] = count_cells(case)
        self.stage("TT1", f"{mode}, {self.report['cells']} ô" + (", lưới chia song song" if decomposed else ""), t)
        return decomposed

    def aside_levels(self, case: str) -> None:
        """snappyHexMesh leaves cellLevel/pointLevel fields in 0/; move them aside (never delete)."""
        roots = [os.path.join(d, "0") for d in _processor_dirs(case)] + ["0"]
        for r0 in roots:
            for lvl in ("cellLevel", "pointLevel"):
                if os.path.isfile(os.path.join(case, r0, lvl)):
                    _move_aside(case, os.path.join(r0, lvl), "mesh-levels")

    def run_allrun_plan(self, case: str, ranks: int) -> bool:
        """Execute the allow-listed OpenFOAM steps of an Allrun up to its solver, with our process count."""
        with open(os.path.join(case, "Allrun"), encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        tut_root = self.env.get("FOAM_TUTORIALS", "")
        steps, ignored = allrun.parse(text, tut_root)
        self.report["allrun"] = {"steps": [x for x in steps if x["kind"] != "unsupported"], "ignored": ignored}
        block = allrun.blockers(steps)
        if block:
            raise JobError("refused", "Allrun has steps before the solver that cannot be automated safely: "
                           + " | ".join(block[:4]) + " — prepare these on the Mac (commit the result) or replace them")
        solver = allrun.first_solver(steps)
        if solver:
            self.solver_override = [solver["tool"]] + solver["args"]
        decomposed = False
        real_case = os.path.realpath(case)
        for step in allrun.pre_solver(steps):
            tool, args, par = step["tool"], list(step["args"]), step["parallel"]
            if step["kind"] == "skip" or tool == "checkMesh":
                continue
            for a in args:
                if a.startswith("/") and not (tut_root and os.path.realpath(a).startswith(os.path.realpath(tut_root) + os.sep)) \
                        and not os.path.realpath(a).startswith(real_case + os.sep):
                    raise JobError("refused", f"Allrun step {tool} reads {a} outside the case and tutorials")
            if tool == "decomposePar":
                if ranks > 1:
                    keep = [a for a in args if a in ("-copyZero", "-allRegions", "-fields", "-noFunctionObjects")]
                    if self.region_args and "-allRegions" not in keep:
                        keep += self.region_args
                    self.decompose(case, ranks, extra=keep)
                    decomposed = True
                continue
            if tool == "surfaceFeatureExtract" and self.branch == "foundation":
                tool = "surfaceFeatures"
            if tool in ("snappyHexMesh", "renumberMesh") and self.branch == "opencfd" and "-overwrite" not in args:
                args.append("-overwrite")
            n = ranks if (par and decomposed) else 1
            self.must([tool] + args, case, parallel=n, what=f"{tool} {' '.join(args)}".strip())
        self.aside_levels(case)
        if ignored:
            self.report["notes"].append(f"Allrun: {len(ignored)} non-OpenFOAM line(s) ignored")
        return decomposed

    # -- TT2 ----------------------------------------------------------------
    def tt2_init(self, case: str, ranks: int, decomposed: bool) -> None:
        t = time.time()
        tools = self.job.get("stages", {}).get("init", [])
        for tool in tools:
            if tool == "setFields" and not os.path.isfile(os.path.join(case, "system", "setFieldsDict")):
                raise JobError("failed", "setFields requested but system/setFieldsDict is missing")
            self.must([tool], case, parallel=ranks if decomposed else 1, what=tool)
        self.stage("TT2", ", ".join(tools) if tools else "điều kiện từ 0/ (không cần khởi tạo thêm)", t)

    # -- TT4 helpers -------------------------------------------------------
    def configure_run(self, case: str) -> None:
        """controlDict settings for an in-RAM run that can be stopped cleanly."""
        cd = "system/controlDict"
        set_entry(self.env, case, cd, "runTimeModifiable", "true")
        set_entry(self.env, case, cd, "writeFormat", "binary")
        kt = int(self.job.get("keep_times", 2))
        if kt > 0:
            set_entry(self.env, case, cd, "purgeWrite", str(kt))
        # see foam.request_stop: let the solver notice controlDict edits within a second
        try:
            set_entry(self.env, case, cd, "OptimisationSwitches/fileModificationSkew", "1")
        except RuntimeError:
            set_entry(self.env, case, cd, "OptimisationSwitches", "{ fileModificationSkew 1; }")

    def decompose(self, case: str, ranks: int, extra: Optional[List[str]] = None) -> None:
        if ranks <= 1:
            return
        extra = extra or []
        for d in _processor_dirs(case):
            _move_aside(case, d, f"old-decomposition-{int(time.time())}")
        method = self.job.get("stages", {}).get("decompose", "auto")
        auto = method == "auto"
        method = "scotch" if auto else method
        write_dict(case, "system/decomposeParDict", decompose_body(ranks, method, self.branch), self.branch)
        try:
            self.must(["decomposePar"] + extra, case, what="decomposePar")
        except JobError:
            if not auto:
                raise
            # self-heal: some builds ship scotch as a stub; hierarchical is always compiled in
            say("scotch decomposition unavailable; retrying with hierarchical", "warn")
            for d in _processor_dirs(case):
                _move_aside(case, d, f"failed-scotch-{int(time.time())}")
            write_dict(case, "system/decomposeParDict", decompose_body(ranks, "hierarchical", self.branch), self.branch)
            self.must(["decomposePar"] + extra, case, what="decomposePar (hierarchical)")
            self.report["notes"].append("decomposition: scotch unavailable, hierarchical used")
        self.report["decomposition"] = "hierarchical" if any("hierarchical used" in n for n in self.report["notes"]) else method

    # -- TT3 + TT8 ----------------------------------------------------------
    def solve(self, case: str, ranks: int, env: Dict[str, str], gpu_on: bool, label: str,
              switch: Optional[SwitchPlan] = None) -> Dict:
        t = time.time()
        feats = case_features(case)
        max_attempts = int(self.job.get("heal", {}).get("max_attempts", 3))
        attempt = 0
        result: Dict = {"variant": label, "ranks": ranks, "gpu": gpu_on}
        sampler = UtilSampler(interval=5.0, gpu=bool(self.hw.get("gpu", {}).get("present")))
        sampler.start()
        last_print = [0.0]
        stopped = {"deadline": False}
        last_print[0] = time.time()

        def progress(_p: LogParser, _line: str) -> None:
            if switch is not None and _line.startswith("Time = "):
                switch.on_line(_p)
            now = time.time()
            if _p.steps and now - last_print[0] > 60:
                last_print[0] = now
                r = ", ".join(f"{k} {v:.2e}" for k, v in list(_p.residual.items())[:3])
                w = _p.wall_per_step()
                say(f"[{label}] t={_p.time} bước {_p.steps} · {r} · Co {_p.courant_max} · "
                    f"{f'{w:.3f}' if w else '?'} s/bước · còn {fmt_duration(self.time_left())}", "info")

        def should_stop() -> bool:
            return self.time_left() < self.margin

        def on_stop() -> None:
            stopped["deadline"] = True
            request_stop(self.env, case, "noWriteNow")

        cd = "system/controlDict"
        while True:
            p = LogParser(hook=progress)
            if switch is not None:
                switch.launched()
            rc, st = self.run_tool(solver_command(env, case, feats, self.solver_override), case, ranks, env=env, parser=p,
                                   should_stop=should_stop, on_stop=on_stop)
            if stopped["deadline"]:
                result["status"] = "stopped_at_deadline"
                break
            target = switch.after_exit() if switch is not None else None
            if target and rc == 0 and switch.reached_end(p):
                switch.note("finished_before_switch", time=p.time)
                switch.phase = "gpu_kept" if gpu_on else "cpu_final"
                target = None
            if target and not p.diverged and latest_time(case):
                if target == "gpu":
                    changes = switch.accel.apply(self.env, case, ranks)
                    env, gpu_on = switch.accel.env(self.env), True
                    say(f"[{label}] t={p.time}: chuyển bước giải áp suất sang {switch.accel.name} ({len(changes)} thay đổi), chạy tiếp", "ok")
                else:
                    switch.accel.revert(self.env, case)
                    env, gpu_on = self.env, False
                    say(f"[{label}] t={p.time}: {switch.accel.name} không nhanh hơn đủ 10 %, quay về CPU", "warn")
                set_entry(self.env, case, cd, "stopAt", "endTime")
                set_entry(self.env, case, cd, "startFrom", "latestTime")
                continue
            if rc == 0 and not p.diverged and (p.ended or p.converged):
                result["status"] = "converged" if p.converged else "completed"
                break
            if gpu_on and not p.diverged:
                say(f"[{label}] GPU run failed (rc={rc}); reverting to CPU solver and resuming", "warn")
                say_tail(st, 15)
                if switch is not None:
                    switch.accel.revert(self.env, case)
                    switch.phase = "cpu_final"
                    switch.note("gpu_failed", rc=rc)
                    switch.release()
                gpu_on, env = False, self.env
                self.report["notes"].append(f"{label}: GPU solver failed at runtime, CPU fallback")
                set_entry(self.env, case, cd, "stopAt", "endTime")
                if latest_time(case):
                    set_entry(self.env, case, cd, "startFrom", "latestTime")
                continue
            if p.diverged and attempt < max_attempts:
                attempt += 1
                say(f"[{label}] phân kỳ ở t={p.first_bad_time}; tự chữa lần {attempt}/{max_attempts}", "warn")
                info = heal.prepare_restart(self.env, case, p.first_bad_time, attempt, feats["steady"])
                info["variant"] = label
                self.report["heal"].append(info)
                continue
            say_tail(st, 25)
            result["status"] = "diverged" if p.diverged else "failed"
            break
        result["util"] = sampler.stop()
        result["log"] = p.summary()
        result["gpu"] = gpu_on
        if switch is not None:
            switch.finish()
            result["switch"] = switch.summary()
        w = p.wall_per_step()
        if w and self.report.get("cells"):
            result["c_cell_us"] = round(w * ranks / float(self.report["cells"]) * 1e6, 4)
        result["healed"] = any(h.get("variant") == label for h in self.report["heal"])
        kpis = [kpi_value(case, k) for k in self.job.get("kpi", [])]
        result["kpi"] = kpis
        self.stage("TT3", f"{label}: {result['status']} sau {p.steps} bước, {ranks} tiến trình"
                          + (", GPU" if result["gpu"] else ""), t, ok=result["status"] in ("converged", "completed"))
        return result

    # -- orchestration -----------------------------------------------------
    def run(self) -> Dict:
        try:
            base = self.tt0_prepare()
            cells_guess = count_cells(base)
            variants = self.job.get("variants") or [{"name": "base", "set": []}]
            conc = plan.concurrency(self.hw, len(variants), cells_guess, case_features(base)["physics"],
                                    int(self.job.get("min_cores_per_job", 4)))
            k = conc["concurrent"]
            per_job = conc["cores_per_job"] if len(variants) > 1 else self.cores
            ranks0 = plan.decide_ranks(self.hw, cells_guess, self.job, cores_available=per_job)
            decomposed = self.tt1_mesh(base, ranks0)
            cells = count_cells(base)
            self.report["cells"] = cells
            ranks = plan.decide_ranks(self.hw, cells, self.job, cores_available=per_job)
            if decomposed and ranks != ranks0:
                ranks = ranks0  # mesh already split for ranks0
            self.tt2_init(base, ranks, decomposed)
            feats = case_features(base)
            self.report["features"] = feats

            t4 = time.time()
            self.configure_run(base)
            if not decomposed:
                self.decompose(base, ranks, extra=list(self.region_args))
            accel = self.accel
            gdec = plan.gpu_decision(self.hw, feats, cells, self.job, bool(accel and accel.ready()))
            if gdec["mode"] != "off" and self.gpu_block_reason:
                gdec = {"mode": "off", "reasons": [self.gpu_block_reason], "estimate": gdec.get("estimate")}
            if gdec["mode"] != "off" and accel is None:
                gdec["mode"] = "off"
                gdec["reasons"].append("no OGL build in this session (--no-gpu-build, or no nvcc)")
            if gdec["mode"] != "off" and self.builder is not None and self.builder.finished() and not self.builder.ready():
                gdec["mode"] = "off"
                gdec["reasons"].append(f"OGL build failed: {self.builder.error}")
            use_switch = gdec["mode"] in ("ab", "on")
            gdec["chosen"] = ("CPU ngay, chuyển áp suất sang GPU khi OGL sẵn sàng và đo thấy nhanh hơn"
                              if use_switch else "CPU")
            self.report["gpu_decision"] = gdec
            self.stage("TT4", f"{ranks} tiến trình × {k} biến thể song song, chia miền "
                              f"{self.report.get('decomposition', 'scotch' if ranks > 1 else 'không cần')}, bộ giải áp suất: "
                              f"{'CPU → GPU trực tuyến' if use_switch else 'CPU (GAMG/PCG)'}", t4)
            if use_switch and self.builder is not None:
                self.stage("TT5", self.builder.status_line(), time.time())
            est_speedup = float((gdec.get("estimate") or {}).get("speedup") or 1.5)

            # variants share the meshed + decomposed base; each gets its own disjoint core set
            sets = plan.cpu_sets(k, per_job) if k > 1 else [None]
            results: List[Dict] = []
            lock = threading.Lock()

            def run_variant(v: Dict, cpu_set: Optional[str]) -> None:
                try:
                    vcase = base if len(variants) == 1 else os.path.join(self.root, f"v-{v['name']}")
                    if vcase != base:
                        shutil.copytree(base, vcase, symlinks=True)
                        _set_many(self.env, vcase, v.get("set", []))
                    sub = JobRun.__new__(JobRun)
                    sub.__dict__.update(self.__dict__)
                    sub.cpu_set = cpu_set if cpu_set is not None else self.cpu_set
                    sub.mpi_extra_env = dict(self.mpi_extra_env)
                    sw = (SwitchPlan(accel, self.env, vcase, ("openfoam", f"{self.job['id']}:{v['name']}"), self.arbiter,
                                     forced=gdec["mode"] == "on", expected_speedup=est_speedup)
                          if use_switch and accel is not None else None)
                    r = sub.solve(vcase, ranks, self.env, False, v["name"], switch=sw)
                except Exception as exc:  # one variant failing must not hide the others
                    say(f"[{v['name']}] failed: {type(exc).__name__}: {exc}", "err")
                    r = {"variant": v["name"], "status": "failed", "error": f"{type(exc).__name__}: {exc}",
                         "ranks": ranks, "gpu": False, "kpi": [], "util": {}, "log": {}}
                with lock:
                    results.append(r)

            queue = list(variants)
            while queue:
                wave, queue = queue[:k], queue[k:]
                threads = [threading.Thread(target=run_variant, args=(v, sets[i] if i < len(sets) else None))
                           for i, v in enumerate(wave)]
                for th in threads:
                    th.start()
                for th in threads:
                    th.join()
            order = {v["name"]: i for i, v in enumerate(variants)}
            self.report["variants"] = sorted(results, key=lambda r: order.get(r["variant"], 0))
            t6 = time.time()
            n_kpi = sum(1 for r in results for q in r.get("kpi", []) if q.get("value") is not None)
            self.stage("TT6", f"{n_kpi} chỉ số KPI đọc từ postProcessing (trong RAM)", t6)
            statuses = {r["status"] for r in results}
            if len(results) != len(variants) or not statuses:
                self.report["status"] = "failed"
            elif statuses == {"converged"}:
                self.report["status"] = "converged"
            elif statuses <= {"converged", "completed"}:
                self.report["status"] = "completed"
            else:
                rank = ["failed", "diverged", "stopped_at_deadline"]
                self.report["status"] = next((x for x in rank if x in statuses), sorted(statuses)[0])
        except JobError as exc:
            self.report["status"] = exc.status
            self.report["error"] = str(exc)
            say(f"{self.job['id']}: {exc.status}: {exc}", "err")
        except Exception as exc:  # report, never leave the watcher dead
            self.report["status"] = "failed"
            self.report["error"] = f"{type(exc).__name__}: {exc}"
            say(f"{self.job['id']}: unexpected {type(exc).__name__}: {exc}", "err")
        self.report["seconds"] = round(time.time() - self.t0, 1)
        t8 = time.time()
        self.stage("TT8", f"trạng thái {self.report.get('status')}, tự chữa {len(self.report['heal'])} lần", t8,
                   ok=self.report.get("status") in ("converged", "completed"))
        print_report(self.report)
        return self.report


def print_report(rep: Dict) -> None:
    """TT7 output: the only place results go is this console summary."""
    say("─" * 72, "info")
    say(f"KẾT QUẢ {rep['id']} · {rep.get('status')} · {fmt_duration(rep.get('seconds', 0))} · "
        f"OpenFOAM {rep.get('openfoam')} · lưu: {rep.get('retention')}", "ok" if rep.get("status") in ("converged", "completed") else "warn")
    integ = rep.get("integrity")
    if integ:
        say(f"Toàn vẹn: {integ['files']} tệp, {human_bytes(integ['bytes'])}, SHA-256 {integ['root']}"
            + (" · trùng khớp tới từng bit" if integ.get("identical") else ""), "info")
    gd = rep.get("gpu_decision")
    if gd:
        say(f"GPU: {gd.get('chosen', gd.get('mode'))} · " + " | ".join(gd.get("reasons", [])), "info")
    for v in rep.get("variants", []):
        u = v.get("util", {})
        say(f"[{v['variant']}] {v.get('status')} · {v.get('ranks')} tiến trình · GPU {v.get('gpu')} · "
            f"CPU bận {u.get('cpu_busy_mean')}% (max {u.get('cpu_busy_max')}%) · GPU {u.get('gpu_util_mean')}% · "
            f"RAM đỉnh {human_bytes(u.get('ram_peak_bytes') or 0)}"
            + (f" · {v['c_cell_us']} µs·lõi/ô/bước" if v.get("c_cell_us") else ""), "info")
        sw = v.get("switch")
        if sw:
            def f(x):
                return "—" if x is None else f"{x:.4g}"
            verdict = {"gpu_kept": "giữ GPU", "cpu_final": "giữ CPU", "cpu": "bộ tăng tốc chưa sẵn sàng khi chạy xong",
                       "measure_cpu": "chạy xong khi đang đo CPU", "gpu_trial": "chạy xong khi đang đo GPU"}.get(sw["phase"], sw["phase"])
            extra = ""
            k = sw.get("measured_build_slowdown")
            if k and k < 0.99:
                extra = f" · khi dựng OGL nền, CPU chạy ở {k:.0%} tốc độ"
            say(f"    chuyển GPU trực tuyến: CPU {f(sw.get('cpu_s_per_step'))} s/bước → {sw['accelerator']} "
                f"{f(sw.get('gpu_s_per_step'))} s/bước: {verdict}{extra}", "info")
        for q in v.get("kpi", []):
            if q.get("value") is None:
                say(f"    {q['name']}: — ({q.get('error', 'no data')})", "warn")
            else:
                stab = "" if q.get("stable") is None else (" ổn định" if q["stable"] else f" đang trôi {q['drift']:.2%}")
                say(f"    {q['name']} = {q['value']:.6g}{stab} ({q['rows']} mẫu)", "info")
    for h in rep.get("heal", []):
        say(f"Tự chữa lần {h['attempt']} ({h.get('variant')}): chạy lại từ {h['restart_from']}; "
            f"{len(h['changes'])} thay đổi số học — cần kiểm chứng lại kết quả", "warn")
    for n in rep.get("notes", []):
        say(f"Ghi chú: {n}", "info")
    if rep.get("error"):
        say(f"Lỗi: {rep['error']}", "err")
    say("─" * 72, "info")
