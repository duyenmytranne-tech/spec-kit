"""Job specification: what the Mac asks the G4 runtime to do.

A job file is configuration, never a script. Every field is validated
against an allow-list so that a pushed job cannot inject shell commands or
OpenFOAM code (``#codeStream``, ``$macro``, ``;`` sequences) into the run.
"""

from __future__ import annotations

import datetime as _dt
import json
import posixpath
import re
from typing import Any, Dict, List, Optional

SCHEMA = 1

ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,96}$")
NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
SOLVER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
SEGMENT_RE = re.compile(r"^[A-Za-z0-9_.+-]{1,128}$")
#: Function-object output folders may carry arguments, e.g. ``cellMax(T)``.
KPI_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_.+,=()-]{1,128}$")
ENTRY_RE = re.compile(r'^[A-Za-z0-9_.:()|*"\'/+-]{1,200}$')
COLUMN_RE = re.compile(r"^[A-Za-z0-9_()]{1,64}$")
BAD_VALUE_CHARS = set("#$;{}`\n\r\\")
APP_RE = re.compile(r"^ud(0[1-9]|1[0-9]|2[01])$")

ALLOWED_TOP = {
    "schema", "id", "created", "app", "title", "source", "manifest", "branch", "solver", "np", "gpu",
    "stages", "set", "variants", "kpi", "keep_times", "max_hours", "heal", "min_cells_per_rank",
    "min_cores_per_job", "kind",
}
MODEL_TOP = {"schema", "id", "created", "title", "kind", "model", "max_hours"}
ARG_RE = re.compile(r"^[A-Za-z0-9_.,:=+/@%-]{0,200}$")
ALLOWED_STAGES = {"mesh", "renumber", "checkMesh", "init", "decompose"}
MESH_MODES = {"auto", "none", "blockMesh", "snappyHexMesh", "blockMesh+snappyHexMesh"}
INIT_TOOLS = {"potentialFoam", "setFields"}


def _rel_path_ok(p: Any, must_prefix: Optional[str] = None, seg_re: re.Pattern[str] = SEGMENT_RE) -> bool:
    if not isinstance(p, str) or not p or p.startswith("/") or "\\" in p:
        return False
    norm = posixpath.normpath(p)
    if norm != p.rstrip("/") or norm.startswith("..") or "/../" in f"/{norm}/":
        return False
    if any(not seg_re.match(seg) for seg in norm.split("/")):
        return False
    return not must_prefix or norm == must_prefix or norm.startswith(must_prefix + "/")


def _check_sets(sets: Any, where: str, errors: List[str]) -> None:
    if not isinstance(sets, list) or len(sets) > 200:
        errors.append(f"{where}: must be a list of at most 200 edits")
        return
    for i, s in enumerate(sets):
        w = f"{where}[{i}]"
        if not isinstance(s, dict) or set(s) != {"file", "entry", "value"}:
            errors.append(f"{w}: needs exactly file, entry, value")
            continue
        if not _rel_path_ok(s["file"]) or s["file"].split("/")[0] not in {"0", "0.orig", "constant", "system"}:
            errors.append(f"{w}.file: must be a relative path under 0/, constant/ or system/")
        if not isinstance(s["entry"], str) or not ENTRY_RE.match(s["entry"]):
            errors.append(f"{w}.entry: invalid characters")
        v = s["value"]
        if not isinstance(v, (str, int, float)) or isinstance(v, bool):
            errors.append(f"{w}.value: must be a string or number")
        else:
            sv = str(v)
            if len(sv) > 500 or any(c in BAD_VALUE_CHARS for c in sv):
                errors.append(f"{w}.value: forbidden character (# $ ; {{ }} ` \\ or newline) or too long")


def validate_model_job(job: Dict) -> List[str]:
    """A model job runs a signed Python script on the GPU lane (see ``models.py``)."""
    errors: List[str] = []
    unknown = set(job) - MODEL_TOP
    if unknown:
        errors.append(f"unknown keys: {sorted(unknown)}")
    if job.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    if not isinstance(job.get("id"), str) or not ID_RE.match(job["id"]):
        errors.append("id: 1-96 chars of A-Z a-z 0-9 . _ -")
    m = job.get("model")
    if not isinstance(m, dict) or set(m) - {"dir", "script", "args", "manifest"}:
        return errors + ["model: {dir, script, args, manifest}"]
    if not _rel_path_ok(m.get("dir")):
        errors.append("model.dir: clean relative path")
    sc = m.get("script")
    if not isinstance(sc, str) or not _rel_path_ok(sc) or not sc.endswith(".py"):
        errors.append("model.script: relative path to a .py file inside model.dir")
    args = m.get("args", [])
    if not isinstance(args, list) or len(args) > 64 or any(not isinstance(x, str) or not ARG_RE.match(x) for x in args):
        errors.append("model.args: up to 64 strings of A-Z a-z 0-9 _ . , : = + / @ % -")
    man = m.get("manifest")
    if not isinstance(man, dict) or man.get("algo") != "sha256" or not re.match(r"^[0-9a-f]{64}$", str(man.get("root", ""))):
        errors.append("model.manifest: required (run 'foamctl submit-model')")
    mh = job.get("max_hours", 23.0)
    if not isinstance(mh, (int, float)) or isinstance(mh, bool) or not 0.01 <= float(mh) <= 24.0:
        errors.append("max_hours: 0.01..24 (one Colab session)")
    return errors


def validate_job(job: Any) -> List[str]:
    """Return a list of problems; empty means the job is acceptable."""
    errors: List[str] = []
    if not isinstance(job, dict):
        return ["job must be a JSON object"]
    if job.get("kind", "openfoam") == "model":
        return validate_model_job(job)
    if job.get("kind", "openfoam") != "openfoam":
        return ["kind: openfoam | model"]
    unknown = set(job) - ALLOWED_TOP
    if unknown:
        errors.append(f"unknown keys: {sorted(unknown)}")
    if job.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    if not isinstance(job.get("id"), str) or not ID_RE.match(job["id"]):
        errors.append("id: 1-96 chars of A-Z a-z 0-9 . _ -")
    if "app" in job and (not isinstance(job["app"], str) or not APP_RE.match(job["app"])):
        errors.append("app: must be ud01..ud21 (application layer id)")
    if "title" in job and (not isinstance(job["title"], str) or len(job["title"]) > 200):
        errors.append("title: string up to 200 chars")

    src = job.get("source")
    if not isinstance(src, dict) or len(src) != 1 or not (set(src) <= {"case", "tutorial"}):
        errors.append("source: exactly one of {case: path} or {tutorial: path}")
    else:
        key, val = next(iter(src.items()))
        if not _rel_path_ok(val):
            errors.append(f"source.{key}: must be a clean relative path")
        if key == "case":
            man = job.get("manifest")
            if not isinstance(man, dict) or man.get("algo") != "sha256" or not isinstance(man.get("files"), list):
                errors.append("manifest: required for source.case (run 'foamctl submit')")
            elif not re.match(r"^[0-9a-f]{64}$", str(man.get("root", ""))):
                errors.append("manifest.root: must be a sha256 hex digest")

    if job.get("branch", "auto") not in {"auto", "foundation", "opencfd"}:
        errors.append("branch: auto | foundation | opencfd")
    solver = job.get("solver", "auto")
    if solver != "auto" and (not isinstance(solver, str) or not SOLVER_RE.match(solver)):
        errors.append("solver: 'auto' or an identifier like incompressibleFluid / simpleFoam")
    np_ = job.get("np", "auto")
    if np_ != "auto" and (not isinstance(np_, int) or isinstance(np_, bool) or not 1 <= np_ <= 4096):
        errors.append("np: 'auto' or an integer 1..4096")
    if job.get("gpu", "auto") not in {"auto", "off", "on"}:
        errors.append("gpu: auto | off | on")

    stages = job.get("stages", {})
    if not isinstance(stages, dict) or set(stages) - ALLOWED_STAGES:
        errors.append(f"stages: only {sorted(ALLOWED_STAGES)}")
    else:
        if stages.get("mesh", "auto") not in MESH_MODES:
            errors.append(f"stages.mesh: one of {sorted(MESH_MODES)}")
        for b in ("renumber", "checkMesh"):
            if b in stages and not isinstance(stages[b], bool):
                errors.append(f"stages.{b}: true/false")
        init = stages.get("init", [])
        if not isinstance(init, list) or any(t not in INIT_TOOLS for t in init):
            errors.append(f"stages.init: list from {sorted(INIT_TOOLS)}")
        if stages.get("decompose", "auto") not in {"auto", "scotch", "hierarchical", "simple"}:
            errors.append("stages.decompose: auto | scotch | hierarchical | simple")

    _check_sets(job.get("set", []), "set", errors)

    variants = job.get("variants", [])
    if not isinstance(variants, list) or len(variants) > 64:
        errors.append("variants: list of at most 64")
    else:
        names = set()
        for i, v in enumerate(variants):
            if not isinstance(v, dict) or set(v) - {"name", "set"} or "name" not in v:
                errors.append(f"variants[{i}]: needs name and optional set")
                continue
            if not isinstance(v["name"], str) or not NAME_RE.match(v["name"]) or v["name"] in names:
                errors.append(f"variants[{i}].name: unique, A-Z a-z 0-9 _ . -")
            names.add(v.get("name"))
            _check_sets(v.get("set", []), f"variants[{i}].set", errors)

    kpis = job.get("kpi", [])
    if not isinstance(kpis, list) or len(kpis) > 50:
        errors.append("kpi: list of at most 50")
    else:
        for i, k in enumerate(kpis):
            w = f"kpi[{i}]"
            if not isinstance(k, dict) or set(k) - {"name", "path", "column", "reduce", "n"}:
                errors.append(f"{w}: keys name, path, column, reduce, n")
                continue
            if not isinstance(k.get("name"), str) or not NAME_RE.match(k["name"]):
                errors.append(f"{w}.name: invalid")
            if not _rel_path_ok(k.get("path"), must_prefix="postProcessing", seg_re=KPI_SEGMENT_RE):
                errors.append(f"{w}.path: relative path under postProcessing/")
            col = k.get("column")
            if not (isinstance(col, int) and not isinstance(col, bool) and 0 <= col < 1000) and not (
                isinstance(col, str) and COLUMN_RE.match(col)
            ):
                errors.append(f"{w}.column: header name or column index")
            if k.get("reduce", "last") not in {"last", "mean_last", "max", "min"}:
                errors.append(f"{w}.reduce: last | mean_last | max | min")
            n = k.get("n", 1)
            if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= 1_000_000:
                errors.append(f"{w}.n: integer 1..1000000")

    kt = job.get("keep_times", 2)
    if not isinstance(kt, int) or isinstance(kt, bool) or not 0 <= kt <= 1000:
        errors.append("keep_times: integer 0..1000 (0 keeps every written time in RAM)")
    mh = job.get("max_hours", 23.0)
    if not isinstance(mh, (int, float)) or isinstance(mh, bool) or not 0.01 <= float(mh) <= 24.0:
        errors.append("max_hours: 0.01..24 (one Colab session)")
    heal = job.get("heal", {})
    if not isinstance(heal, dict) or set(heal) - {"max_attempts"}:
        errors.append("heal: {max_attempts: 0..5}")
    elif not isinstance(heal.get("max_attempts", 3), int) or not 0 <= heal.get("max_attempts", 3) <= 5:
        errors.append("heal.max_attempts: 0..5")
    mcj = job.get("min_cores_per_job", 4)
    if not isinstance(mcj, int) or isinstance(mcj, bool) or not 1 <= mcj <= 1024:
        errors.append("min_cores_per_job: integer 1..1024")
    mcr = job.get("min_cells_per_rank", 10000)
    if not isinstance(mcr, int) or isinstance(mcr, bool) or not 100 <= mcr <= 10_000_000:
        errors.append("min_cells_per_rank: integer 100..10000000")
    return errors


def load_job(path: str) -> Dict:
    with open(path, encoding="utf-8") as fh:
        job = json.load(fh)
    errs = validate_job(job)
    if errs:
        raise ValueError("invalid job " + path + ":\n  - " + "\n  - ".join(errs))
    return job


def new_job_id(base: str, root: str, now: Optional[_dt.datetime] = None) -> str:
    now = now or _dt.datetime.now(_dt.timezone.utc)
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "-", base).strip("-")[:48] or "job"
    return f"{clean}-{now.strftime('%Y%m%dT%H%MZ')}-{root[:6]}"


def load_active(path: str) -> List[str]:
    """``jobs/active.json`` lists job ids the G4 watcher should run, in order."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return []
    ids = data.get("active", []) if isinstance(data, dict) else []
    return [i for i in ids if isinstance(i, str) and ID_RE.match(i)]
