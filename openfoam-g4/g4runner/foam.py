"""Thin, version-aware layer over the OpenFOAM command-line tools.

Supports the Foundation line (v14: ``foamRun``, ``foamPostProcess``,
``surfaceFeatures``, ``decomposer``) and the OpenCFD line (``vYYMM``:
classic solver names, ``postProcess``, ``surfaceFeatureExtract``,
``method``). Solver output is read from the pipe and handed to a callback;
no log file is ever written.
"""

from __future__ import annotations

import collections
import os
import re
import shutil
import signal
import subprocess
import threading
import time
from typing import Callable, Deque, Dict, List, Optional, Sequence

from .util import run_capture, say

BASHRC_CANDIDATES = [
    "/opt/openfoam14/etc/bashrc",
    "/opt/openfoam13/etc/bashrc",
    "/usr/lib/openfoam/openfoam2606/etc/bashrc",
    "/usr/lib/openfoam/openfoam2512/etc/bashrc",
    "/usr/share/openfoam/etc/bashrc",
]

INCOMPRESSIBLE = {"incompressibleFluid", "simpleFoam", "pimpleFoam", "pisoFoam", "icoFoam", "SRFSimpleFoam"}
FLUID = {"fluid", "buoyantFoam", "buoyantSimpleFoam", "buoyantPimpleFoam", "rhoSimpleFoam", "rhoPimpleFoam", "rhoCentralFoam"}
VOF = {"incompressibleVoF", "compressibleVoF", "incompressibleMultiphaseVoF", "interFoam", "multiphaseInterFoam", "interIsoFoam"}
EULER = {"multiphaseEuler", "multiphaseEulerFoam", "twoPhaseEulerFoam", "reactingTwoPhaseEulerFoam"}
REACTING = {"multicomponentFluid", "reactingFoam", "XiFluid", "XiFoam", "chemFoam"}
MULTIREGION = {"foamMultiRun", "chtMultiRegionFoam", "chtMultiRegionSimpleFoam"}
PARTICLE = {"dsmcFoam", "mdFoam", "mdEquilibrationFoam"}

_NOTE = re.compile(r"nCells:\s*(\d+)")


# ----------------------------------------------------------------- environment
def find_bashrc() -> Optional[str]:
    env = os.environ.get("G4_FOAM_BASHRC")
    for cand in ([env] if env else []) + BASHRC_CANDIDATES:
        if cand and os.path.isfile(cand):
            return cand
    return None


def foam_env(bashrc: Optional[str] = None) -> Optional[Dict[str, str]]:
    """Environment after sourcing an OpenFOAM bashrc, or None if none is installed."""
    bashrc = bashrc or find_bashrc()
    if not bashrc:
        return None
    script = f'source "{bashrc}" >/dev/null 2>&1; env -0'
    proc = subprocess.run(["bash", "-c", script], capture_output=True, check=False)
    env: Dict[str, str] = {}
    for item in proc.stdout.split(b"\0"):
        if b"=" in item:
            k, v = item.split(b"=", 1)
            env[k.decode(errors="replace")] = v.decode(errors="replace")
    if "WM_PROJECT_VERSION" not in env:
        return None
    env.pop("PWD", None)
    env.pop("OLDPWD", None)
    env["FOAM_SIGFPE"] = env.get("FOAM_SIGFPE", "true")  # turn NaN into an immediate, detectable stop
    env["OMPI_ALLOW_RUN_AS_ROOT"] = "1"                 # Colab runs as root
    env["OMPI_ALLOW_RUN_AS_ROOT_CONFIRM"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["G4_BASHRC"] = bashrc
    return env


def branch_of(env: Dict[str, str]) -> str:
    v = env.get("WM_PROJECT_VERSION", "")
    return "opencfd" if v.startswith("v") else "foundation"


def tool(env: Dict[str, str], *names: str) -> Optional[str]:
    """First available executable among ``names`` on the OpenFOAM PATH."""
    for n in names:
        p = shutil.which(n, path=env.get("PATH"))
        if p:
            return n
    return None


def post_tool(env: Dict[str, str]) -> Optional[str]:
    return tool(env, "foamPostProcess", "postProcess")


def features_tool(env: Dict[str, str]) -> Optional[str]:
    # v14 ships surfaceFeatureExtract only as a notice script; prefer surfaceFeatures.
    return tool(env, "surfaceFeatures", "surfaceFeatureExtract")


def mpi_flavour(env: Dict[str, str]) -> str:
    rc, out, err = run_capture(["mpirun", "--version"], env=env, timeout=30)
    text = (out + err).lower()
    if "open mpi" in text or "openrte" in text:
        return "openmpi"
    if "hydra" in text or "mpich" in text:
        return "mpich"
    return "unknown"


# ----------------------------------------------------------------- dictionaries
def header(obj: str, location: str, branch: str, cls: str = "dictionary") -> str:
    version = "    version     2.0;\n" if branch == "opencfd" else ""
    return (
        "FoamFile\n{\n" + version + "    format      ascii;\n"
        f"    class       {cls};\n    location    \"{location}\";\n    object      {obj};\n}}\n\n"
    )


def write_dict(case: str, rel: str, body: str, branch: str, cls: str = "dictionary") -> None:
    path = os.path.join(case, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    loc, obj = os.path.dirname(rel).replace(os.sep, "/"), os.path.basename(rel)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(header(obj, loc, branch, cls) + body)


def decompose_body(n: int, method: str, branch: str) -> str:
    key = "decomposer" if branch == "foundation" else "method"
    body = f"numberOfSubdomains {n};\n\n{key} {method};\n"
    if method in ("hierarchical", "simple"):
        nx, ny, nz = split3(n)
        coeffs = "hierarchicalCoeffs" if branch == "opencfd" else "hierarchical"
        body += f"\n{coeffs}\n{{\n    n ({nx} {ny} {nz});\n    order xyz;\n}}\n"
    return body


def split3(n: int) -> List[int]:
    """Factor n into three near-equal integers (for hierarchical decomposition)."""
    best = [n, 1, 1]
    score = n * 3
    for a in range(1, n + 1):
        if n % a:
            continue
        for b in range(1, n // a + 1):
            if (n // a) % b:
                continue
            c = n // a // b
            s = max(a, b, c) - min(a, b, c)
            if s < score:
                best, score = sorted([a, b, c], reverse=True), s
    return best


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def top_value(path: str, key: str) -> Optional[str]:
    """Value of a top-level ``key value;`` entry (no macro expansion)."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = strip_comments(fh.read())
    except OSError:
        return None
    m = re.search(rf"(?m)^\s*{re.escape(key)}\s+([^;{{}}]+);", text)
    return m.group(1).strip().strip('"') if m else None


def set_entry(env: Dict[str, str], case: str, rel: str, entry: str, value: str) -> None:
    rc, out, err = run_capture(["foamDictionary", "-entry", entry, "-set", str(value), rel], cwd=case, env=env, timeout=120)
    if rc != 0:
        raise RuntimeError(f"foamDictionary -entry {entry} -set {value} {rel}: {(err or out).strip()[-300:]}")


def strip_foam_warnings(text: str) -> str:
    """Remove ``--> FOAM Warning`` blocks (header line plus indented lines) from tool output."""
    out, skipping = [], False
    for line in text.splitlines():
        if line.startswith("--> FOAM Warning"):
            skipping = True
            continue
        if skipping and (line.startswith("    ") or not line.strip()):
            continue
        skipping = False
        out.append(line)
    return "\n".join(out).strip()


def request_stop(env: Dict[str, str], case: str, mode: str = "writeNow") -> None:
    """Ask a running solver to stop (``writeNow`` / ``noWriteNow``) and make sure it notices.

    OpenFOAM re-reads controlDict only when its time stamp moved by more than
    ``fileModificationSkew``; the runner lowers that to 1 s and pushes the
    time stamp forward so the request is seen at the next time step.
    """
    path = os.path.join(case, "system", "controlDict")
    before = os.path.getmtime(path)
    set_entry(env, case, "system/controlDict", "stopAt", mode)
    t = max(time.time(), before + 2.0)
    os.utime(path, (t, t))


def get_entry(env: Dict[str, str], case: str, rel: str, entry: str) -> Optional[str]:
    rc, out, _ = run_capture(["foamDictionary", "-entry", entry, "-value", rel], cwd=case, env=env, timeout=120)
    val = strip_foam_warnings(out) if rc == 0 else ""
    return val or None


# ----------------------------------------------------------------- case facts
def count_cells(case: str) -> Optional[int]:
    """Read ``nCells`` from polyMesh/owner headers (serial or decomposed)."""
    def from_owner(path: str) -> Optional[int]:
        for name in ("owner", "owner.gz"):
            p = os.path.join(path, name)
            if os.path.isfile(p):
                opener = open
                if p.endswith(".gz"):
                    import gzip
                    opener = gzip.open  # type: ignore[assignment]
                with opener(p, "rt", encoding="utf-8", errors="replace") as fh:  # type: ignore[call-arg]
                    head = fh.read(4096)
                m = _NOTE.search(head)
                return int(m.group(1)) if m else None
        return None

    def regions(constant: str) -> List[str]:
        if not os.path.isdir(constant):
            return []
        return sorted(r for r in os.listdir(constant) if os.path.isdir(os.path.join(constant, r, "polyMesh")))

    serial = from_owner(os.path.join(case, "constant", "polyMesh"))
    if serial is not None:
        return serial
    multi = [from_owner(os.path.join(case, "constant", r, "polyMesh")) for r in regions(os.path.join(case, "constant"))]
    if multi and all(n is not None for n in multi):
        return sum(n for n in multi if n is not None)
    procs = sorted(d for d in os.listdir(case) if re.match(r"^processor\d+$", d)) if os.path.isdir(case) else []
    total = 0
    for d in procs:
        pc = os.path.join(case, d, "constant")
        n = from_owner(os.path.join(pc, "polyMesh"))
        if n is None:
            per = [from_owner(os.path.join(pc, r, "polyMesh")) for r in regions(pc)]
            if not per or any(x is None for x in per):
                return None
            n = sum(x for x in per if x is not None)
        total += n
    return total or None


def solver_name(case: str) -> Optional[str]:
    cd = os.path.join(case, "system", "controlDict")
    name = top_value(cd, "solver") or top_value(cd, "application")
    if name:
        return name
    try:
        with open(cd, encoding="utf-8", errors="replace") as fh:
            if re.search(r"(?m)^\s*regionSolvers\b", strip_comments(fh.read())):
                return "foamMultiRun"
    except OSError:
        pass
    return None


def is_steady(case: str) -> bool:
    try:
        with open(os.path.join(case, "system", "fvSchemes"), encoding="utf-8", errors="replace") as fh:
            text = strip_comments(fh.read())
    except OSError:
        return False
    m = re.search(r"ddtSchemes\s*\{([^}]*)\}", text, re.S)
    return bool(m and re.search(r"default\s+steadyState\s*;", m.group(1)))


def case_features(case: str) -> Dict:
    solver = solver_name(case) or "unknown"
    c = os.path.join(case, "constant")
    boundary_txt = ""
    for root, _, files in os.walk(c):
        if os.path.basename(root) == "polyMesh" and "boundary" in files:
            try:
                with open(os.path.join(root, "boundary"), encoding="utf-8", errors="replace") as fh:
                    boundary_txt += fh.read()
            except OSError:
                pass
    ami = bool(re.search(r"\b(cyclicAMI|nonConformal\w*|cyclicACMI)\b", boundary_txt)) or os.path.isfile(
        os.path.join(case, "system", "createNonConformalCouplesDict")
    )
    multi_region = os.path.isfile(os.path.join(c, "regionProperties")) or solver in MULTIREGION
    moving = os.path.isfile(os.path.join(c, "dynamicMeshDict"))
    chem_val = top_value(os.path.join(c, "chemistryProperties"), "chemistry")
    chemistry = chem_val in ("on", "yes", "true")
    particles = any(f.endswith("CloudProperties") or f in ("cloudProperties", "clouds") for f in (os.listdir(c) if os.path.isdir(c) else []))
    sim_type = top_value(os.path.join(c, "momentumTransport"), "simulationType") or top_value(
        os.path.join(c, "turbulenceProperties"), "simulationType"
    )
    steady = is_steady(case)
    buoyant = os.path.isfile(os.path.join(c, "g")) and solver not in INCOMPRESSIBLE

    if solver in PARTICLE:
        physics = "particles_dsmc"
    elif multi_region:
        physics = "cht_multiregion"
    elif solver in EULER:
        physics = "multiphase_euler"
    elif solver in VOF:
        physics = "vof"
    elif solver in REACTING:
        physics = "reacting" if chemistry else "compressible"
    elif solver in FLUID:
        physics = "buoyant" if buoyant else "compressible"
    elif solver in INCOMPRESSIBLE:
        physics = "incompressible_rans" if steady else ("incompressible_les" if sim_type == "LES" else "incompressible_transient")
    else:
        physics = "incompressible_rans" if steady else "incompressible_transient"
    return {
        "solver": solver, "steady": steady, "simulationType": sim_type, "multi_region": multi_region, "ami": ami,
        "moving_mesh": moving, "chemistry": chemistry, "particles": particles, "physics": physics,
        "modular": solver not in PARTICLE and top_value(os.path.join(case, "system", "controlDict"), "solver") is not None,
    }


def time_dirs(path: str) -> List[str]:
    out = []
    if not os.path.isdir(path):
        return out
    for d in os.listdir(path):
        try:
            float(d)
        except ValueError:
            continue
        if os.path.isdir(os.path.join(path, d)):
            out.append(d)
    return sorted(out, key=float)


def latest_time(case: str) -> Optional[str]:
    p0 = os.path.join(case, "processor0")
    times = time_dirs(p0) if os.path.isdir(p0) else time_dirs(case)
    return times[-1] if times else None


# ----------------------------------------------------------------- execution
class Stream:
    """Run one command, feed each output line to ``on_line``; keep only a small ring in RAM."""

    def __init__(self, cmd: Sequence[str], cwd: str, env: Dict[str, str], on_line: Optional[Callable[[str], None]] = None,
                 ring: int = 400):
        self.cmd = list(cmd)
        self.cwd = cwd
        self.env = env
        self.on_line = on_line
        self.tail: Deque[str] = collections.deque(maxlen=ring)
        self.proc: Optional[subprocess.Popen] = None
        self.started = 0.0
        self.ended = 0.0

    def run(self, should_stop: Optional[Callable[[], bool]] = None, on_stop: Optional[Callable[[], None]] = None,
            grace: float = 60.0) -> int:
        """Run to completion. When ``should_stop`` turns true, call ``on_stop`` once (graceful
        request, e.g. ``stopAt noWriteNow``) and terminate the process group after ``grace`` s."""
        self.started = time.time()
        env = dict(self.env, PWD=os.path.abspath(self.cwd))
        self.proc = subprocess.Popen(self.cmd, cwd=self.cwd, env=env, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True, bufsize=1, errors="replace",
                                     start_new_session=True)
        stop_sent = [0.0]

        def watchdog() -> None:
            while self.proc and self.proc.poll() is None:
                if should_stop and should_stop():
                    if not stop_sent[0]:
                        stop_sent[0] = time.time()
                        if on_stop:
                            try:
                                on_stop()
                            except Exception as exc:  # graceful stop is best effort
                                say(f"graceful stop request failed: {exc}", "warn")
                    elif time.time() - stop_sent[0] > grace:
                        self.terminate()
                        return
                time.sleep(1.0)

        wd = threading.Thread(target=watchdog, daemon=True)
        wd.start()
        assert self.proc.stdout is not None
        for line in self.proc.stdout:
            line = line.rstrip("\n")
            self.tail.append(line)
            if self.on_line:
                self.on_line(line)
        rc = self.proc.wait()
        self.ended = time.time()
        return rc

    def terminate(self) -> None:
        if not self.proc or self.proc.poll() is not None:
            return
        for sig, wait in ((signal.SIGINT, 20), (signal.SIGTERM, 20), (signal.SIGKILL, 5)):
            try:
                os.killpg(self.proc.pid, sig)
            except ProcessLookupError:
                return
            t0 = time.time()
            while time.time() - t0 < wait:
                if self.proc.poll() is not None:
                    return
                time.sleep(0.5)


def mpi_command(app: Sequence[str], n: int, physical: int, flavour: str, bind: bool = True,
                cpu_set: Optional[str] = None) -> List[str]:
    """``mpirun`` line pinned to cores; hyper-threads only when ranks exceed physical cores.

    With ``cpu_set`` (concurrent jobs) the ranks are confined to that list of
    logical CPUs; Open MPI rejects ``--map-by`` together with ``--cpu-set``.
    """
    if n <= 1:
        return list(app)
    if flavour == "mpich":
        cmd = ["mpirun", "-np", str(n)] + (["-bind-to", "core"] if bind else [])
    elif cpu_set:
        cmd = ["mpirun", "-np", str(n), "--cpu-set", cpu_set] + (["--bind-to", "core"] if bind else [])
    else:
        cmd = ["mpirun", "-np", str(n)]
        if n > physical:
            cmd += ["--use-hwthread-cpus"] + (["--bind-to", "hwthread", "--map-by", "hwthread"] if bind else [])
        elif bind:
            cmd += ["--bind-to", "core", "--map-by", "core"]
        else:
            cmd += ["--bind-to", "none"]
    return cmd + list(app) + ["-parallel"]


def solver_command(env: Dict[str, str], case: str, feats: Dict, override: Optional[List[str]] = None) -> List[str]:
    if override and tool(env, override[0]):
        return list(override)
    if feats.get("solver") == "foamMultiRun" and tool(env, "foamMultiRun"):
        return ["foamMultiRun"]
    if feats.get("modular") and tool(env, "foamRun"):
        return ["foamRun"]
    name = feats.get("solver") or "unknown"
    if not tool(env, name):
        raise RuntimeError(f"solver '{name}' is not installed in this OpenFOAM ({env.get('WM_PROJECT_VERSION')})")
    return [name]


def say_tail(stream: Stream, n: int = 25) -> None:
    for line in list(stream.tail)[-n:]:
        say("  │ " + line, "debug")
