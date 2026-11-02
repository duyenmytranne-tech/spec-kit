"""Use the CPU and the GPU at the same time.

* :class:`GpuArbiter` decides who holds the GPU: an OpenFOAM job that switched
  its pressure solve to OGL, or a model task. Never both.
* :class:`OglBuilder` builds the OGL plugin (Ginkgo, CUDA) in the background
  as soon as the session starts, in six stages, on CPU threads the solver
  does not use (hyper-thread siblings, or a few reserved cores), at the
  lowest priority. Solvers start on the CPU immediately; when the plugin is
  ready they switch their pressure solve to the GPU (see ``runner.py``).

Zero retention: source, build tree and the installed library live in RAM
and are rebuilt in every session.
"""

from __future__ import annotations

import os
import re
import shutil
import threading
import time
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .util import fmt_duration, ram_workdir, run_capture, say

OGL_REPO = "https://github.com/hpsim/OGL.git"
STAGES = ["kiểm tra", "tải mã", "cấu hình", "biên dịch", "cài đặt", "chạy thử"]


class GpuArbiter:
    """One holder at a time: ("openfoam", job_id) or ("model", job_id)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.holder: Optional[Tuple[str, str]] = None

    def try_acquire(self, owner: Tuple[str, str]) -> bool:
        with self._lock:
            if self.holder is None or self.holder == owner:
                self.holder = owner
                return True
            return False

    def release(self, owner: Tuple[str, str]) -> None:
        with self._lock:
            if self.holder == owner:
                self.holder = None

    def busy(self) -> bool:
        with self._lock:
            return self.holder is not None


def smt_layout(groups: List[List[int]]) -> Tuple[List[int], List[int]]:
    """(primary threads, sibling threads) from core groups."""
    primaries = [g[0] for g in groups]
    siblings = [c for g in groups for c in g[1:]]
    return primaries, siblings


def background_cpus(groups: List[List[int]], share: int) -> Tuple[List[int], List[int]]:
    """CPUs for background work and CPUs left for the solver.

    With hyper-threading the background gets every sibling thread and the
    solver keeps one primary thread per core (no core lost). Without it the
    background gets the last ``share`` cores.
    """
    primaries, siblings = smt_layout(groups)
    if siblings:
        return siblings, primaries
    share = max(1, min(share, len(primaries) - 1)) if len(primaries) > 1 else 0
    if share == 0:
        return primaries, primaries
    return primaries[-share:], primaries[:-share]


def limited(cmd: Sequence[str], cpus: Optional[List[int]], nice: int = 19) -> List[str]:
    """Wrap a command so it runs only on ``cpus`` at low priority (thread-safe: no preexec_fn)."""
    out: List[str] = []
    if cpus and shutil.which("taskset"):
        out += ["taskset", "-c", ",".join(str(c) for c in cpus)]
    if shutil.which("nice"):
        out += ["nice", "-n", str(nice)]
    return out + list(cmd)


def cuda_arch(hw: Dict) -> Optional[str]:
    g = hw.get("gpu", {})
    if not g.get("present") or not g.get("gpus"):
        return None
    m = re.match(r"^(\d+)\.(\d+)$", str(g["gpus"][0].get("compute_cap") or ""))
    return f"{m.group(1)}{m.group(2)}" if m else None


def _version_tuple(text: str) -> Tuple[int, ...]:
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text or "")
    return tuple(int(x) for x in m.groups() if x is not None) if m else ()


class OglBuilder(threading.Thread):
    """Six-stage background build of OGL; ``ready()`` flips when the smoke test passes."""

    def __init__(self, env: Dict[str, str], hw: Dict, cpus: Optional[List[int]], branch: str,
                 smoke: Optional[Callable[[Dict[str, str]], Tuple[bool, str]]] = None, timeout_h: float = 2.0):
        super().__init__(daemon=True, name="ogl-builder")
        self.env, self.hw, self.cpus, self.branch = env, hw, cpus, branch
        self.smoke = smoke
        self.timeout = timeout_h * 3600.0
        self.root = os.path.join(ram_workdir(), "ogl")
        self.stage = 0
        self.state = "idle"
        self.error: Optional[str] = None
        self.commit: Optional[str] = None
        self.t0 = 0.0
        self.t_ready: Optional[float] = None
        self.env_ogl: Optional[Dict[str, str]] = None
        self._ready = threading.Event()
        self._done = threading.Event()

    # ---- state -----------------------------------------------------------
    def ready(self) -> bool:
        return self._ready.is_set()

    def finished(self) -> bool:
        return self._done.is_set()

    def wait(self, timeout: Optional[float] = None) -> bool:
        self._done.wait(timeout)
        return self.ready()

    def status_line(self) -> str:
        if self.state == "ready":
            return f"OGL sẵn sàng sau {fmt_duration((self.t_ready or time.time()) - self.t0)} (commit {self.commit or '?'})"
        if self.state == "failed":
            return f"OGL không dựng được ({self.error}); GPU solver tắt trong phiên này"
        if self.state == "idle":
            return "OGL chưa bắt đầu dựng"
        return f"OGL đang dựng: khâu {self.stage + 1}/6 {STAGES[self.stage]} · {fmt_duration(time.time() - self.t0)}"

    def _fail(self, msg: str) -> None:
        self.state, self.error = "failed", msg
        say(self.status_line(), "warn")
        self._done.set()

    def _run(self, cmd: Sequence[str], env: Dict[str, str], cwd: Optional[str] = None, timeout: float = 3600) -> Tuple[int, str]:
        rc, out, err = run_capture(limited(cmd, self.cpus), cwd=cwd, env=env, timeout=timeout)
        return rc, (err or out).strip()[-400:]

    # ---- the six stages -------------------------------------------------
    def run(self) -> None:  # noqa: C901 - linear sequence of stages
        self.t0 = time.time()
        self.state = "building"
        try:
            self._build()
        except Exception as exc:  # never kill the session because of the plugin
            self._fail(f"{type(exc).__name__}: {exc}")

    def _build(self) -> None:
        # 1 preflight
        self.stage = 0
        arch = cuda_arch(self.hw)
        g = self.hw.get("gpu", {})
        nvcc = g.get("nvcc")
        if not g.get("present") or not g.get("healthy"):
            return self._fail("no healthy GPU")
        if not arch or not nvcc:
            return self._fail("missing compute capability or nvcc")
        for exe in ("git", "cmake", "make"):
            if not shutil.which(exe):
                return self._fail(f"{exe} not installed")
        rc, out, _ = run_capture([nvcc, "--list-gpu-arch"], timeout=60)
        if rc == 0 and f"compute_{arch}" not in out:
            return self._fail(f"nvcc {g.get('nvcc_version')} cannot target sm_{arch}")
        rc, out, _ = run_capture(["cmake", "--version"], timeout=60)
        if _version_tuple(out) < (3, 18):
            return self._fail(f"cmake {out.split()[2] if out else '?'} < 3.18")
        src, build, prefix = (os.path.join(self.root, d) for d in ("src", "build", "install"))
        os.makedirs(self.root, exist_ok=True)
        benv = dict(self.env, PATH=os.path.dirname(nvcc) + os.pathsep + self.env.get("PATH", ""), CUDACXX=nvcc)
        jobs = str(max(1, len(self.cpus or []) or (os.cpu_count() or 2)))

        def attempt(ref: str) -> Optional[str]:
            # 2 fetch
            self.stage = 1
            target = src + "-" + re.sub(r"[^A-Za-z0-9_.-]", "_", ref)
            if not os.path.isdir(os.path.join(target, ".git")):
                rc, msg = self._run(["git", "clone", "--quiet", "--depth", "1", "--branch", ref, OGL_REPO, target], benv, timeout=900)
                if rc != 0:
                    return f"clone {ref}: {msg}"
            rc, out, _ = run_capture(["git", "rev-parse", "--short", "HEAD"], cwd=target, timeout=60)
            self.commit = f"{ref}@{out.strip()}" if rc == 0 else ref
            # 3 configure
            self.stage = 2
            bdir = build + "-" + os.path.basename(target)
            conf = ["cmake", "-S", target, "-B", bdir, "-DCMAKE_BUILD_TYPE=Release", f"-DCMAKE_INSTALL_PREFIX={prefix}",
                    "-DOGL_BUILD_CUDA=ON", "-DGINKGO_BUILD_CUDA=ON", "-DGINKGO_BUILD_OMP=ON",
                    f"-DOGL_CUDA_ARCHITECTURES={arch}", f"-DCMAKE_CUDA_ARCHITECTURES={arch}",
                    "-DGINKGO_BUILD_TESTS=OFF", "-DGINKGO_BUILD_EXAMPLES=OFF", "-DGINKGO_BUILD_BENCHMARKS=OFF"]
            if self.env.get("WM_LABEL_SIZE") == "64":
                conf.append("-DOGL_DP_LABELS=ON")
            rc, msg = self._run(conf, benv, timeout=1800)
            if rc != 0:
                return f"configure: {msg}"
            # 4 compile
            self.stage = 3
            rc, msg = self._run(["cmake", "--build", bdir, "-j", jobs], benv, timeout=self.timeout)
            if rc != 0:
                return f"build: {msg}"
            # 5 install
            self.stage = 4
            rc, msg = self._run(["cmake", "--install", bdir], benv, timeout=900)
            if rc != 0:
                return f"install: {msg}"
            return None

        err = attempt("dev")
        if err:
            say(f"OGL dev branch failed ({err[:160]}); trying the latest release tag", "warn")
            tag = latest_tag()
            if not tag:
                return self._fail(err)
            err2 = attempt(tag)
            if err2:
                return self._fail(err2)
        lib_dirs = [d for d in (os.path.join(prefix, "lib"), os.path.join(prefix, "lib64")) if os.path.isdir(d)]
        user_lib = self.env.get("FOAM_USER_LIBBIN", "")
        if user_lib and os.path.isdir(user_lib):
            lib_dirs.append(user_lib)
        if not any(f.startswith("libOGL") for d in lib_dirs for f in os.listdir(d)):
            return self._fail("installed, but libOGL.so not found")
        env_ogl = dict(self.env)
        env_ogl["LD_LIBRARY_PATH"] = os.pathsep.join(lib_dirs + [self.env.get("LD_LIBRARY_PATH", "")]).strip(os.pathsep)
        # 6 smoke test on a tiny case with the GPU executor
        self.stage = 5
        if self.smoke:
            ok, why = self.smoke(env_ogl)
            if not ok:
                return self._fail(f"smoke test: {why}")
        self.env_ogl = env_ogl
        self.state = "ready"
        self.t_ready = time.time()
        self._ready.set()
        self._done.set()
        say(self.status_line(), "ok")


def latest_tag() -> Optional[str]:
    rc, out, _ = run_capture(["git", "ls-remote", "--tags", "--refs", OGL_REPO], timeout=120)
    if rc != 0:
        return None
    tags = [line.split("refs/tags/")[-1] for line in out.splitlines() if "refs/tags/" in line]
    tags = [t for t in tags if _version_tuple(t)]
    return max(tags, key=_version_tuple) if tags else None


def ogl_smoke(branch: str) -> Callable[[Dict[str, str]], Tuple[bool, str]]:
    """Tiny cavity solved for 3 steps with the pressure on the GPU."""

    def run(env_ogl: Dict[str, str]) -> Tuple[bool, str]:
        from . import casegen, plan
        from .foam import set_entry, solver_command, case_features

        case = os.path.join(ram_workdir(), "ogl", f"smoke-{int(time.time())}")
        casegen.cavity3d(case, n=16, steps=3, branch=branch, functions=False)
        rc, _, err = run_capture(["blockMesh"], cwd=case, env=env_ogl, timeout=300)
        if rc != 0:
            return False, f"blockMesh: {err.strip()[-160:]}"
        for entry, value in plan.ogl_solver_entries("p", 1).items():
            set_entry(env_ogl, case, "system/fvSolution", entry, value)
        set_entry(env_ogl, case, "system/controlDict", "libs", '("libOGL.so")')
        rc, out, err = run_capture(solver_command(env_ogl, case, case_features(case)), cwd=case, env=env_ogl, timeout=600)
        text = out + err
        if rc != 0 or "End" not in text:
            return False, (text.strip()[-200:] or f"rc={rc}")
        return True, "ok"

    return run


def start_builder(env: Dict[str, str], hw: Dict, groups: List[List[int]], branch: str) -> Optional[OglBuilder]:
    """Start the background build if the GPU can use it; returns the running builder or None."""
    g = hw.get("gpu", {})
    if not g.get("present") or not g.get("healthy") or not g.get("nvcc"):
        return None
    cpus, _ = background_cpus(groups, share=max(1, len(groups) // 4))
    b = OglBuilder(env, hw, cpus, branch, smoke=ogl_smoke(branch))
    b.start()
    say(f"OGL bắt đầu dựng nền trên {len(cpus)} luồng CPU {'(luồng siêu phân luồng)' if any(len(x) > 1 for x in groups) else '(lõi dành riêng)'}; "
        "solver không phải chờ", "info")
    return b
