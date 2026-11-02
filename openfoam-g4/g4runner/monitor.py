"""Read solver output as it streams and measure how hard the machine is working.

Nothing here writes to disk: the parser keeps counters, the sampler keeps
running sums, and both are summarised at the end of a job.
"""

from __future__ import annotations

import math
import re
import shutil
import threading
import time
from typing import Callable, Dict, List, Optional

from .util import run_capture

_TIME = re.compile(r"^Time = ([-+0-9.eE]+)")
_RESID = re.compile(
    r"^\s*(\S+):\s+Solving for (\w+), Initial residual = ([^,]+), Final residual = ([^,]+), No Iterations (\d+)"
)
_COURANT = re.compile(r"^Courant Number mean: (\S+) max: (\S+)")
_EXEC = re.compile(r"^ExecutionTime = ([-+0-9.eE]+) s\s+ClockTime = ([-+0-9.eE]+) s")
_FATAL = re.compile(r"FOAM FATAL (IO )?ERROR")
# Real FPE events only: the start-up banner ("Floating point exception trapping
# enabled") must not count, so match the handler frame or the kernel signal text.
_FPE = re.compile(r"sigFpe::sigHandler|Floating point exception \(core dumped\)|Signal: Floating point exception")
_MPI_SLOTS = re.compile(r"not enough slots", re.I)
_MPI_CMA = re.compile(r"process_vm_readv|single_copy|vader.*(read|write)|CMA", re.I)
_MPI_BIND = re.compile(r"(binding|bind).*(fail|not supported|error)|hwloc", re.I)
_CHECKMESH_FAIL = re.compile(r"Failed (\d+) mesh checks")
_CELLS = re.compile(r"^\s*cells:\s+(\d+)")


def _num(text: str) -> float:
    t = text.strip().lower()
    if t in ("nan", "-nan", "+nan"):
        return math.nan
    if t in ("inf", "-inf", "+inf"):
        return math.inf
    try:
        return float(t)
    except ValueError:
        return math.nan


class LogParser:
    """Incremental parser for OpenFOAM solver output (Foundation and OpenCFD formats)."""

    def __init__(self, clock: Callable[[], float] = time.monotonic,
                 hook: Optional[Callable[[LogParser, str], None]] = None):
        self.clock = clock
        self.hook = hook
        self.time: Optional[float] = None
        self.steps = 0
        self.step_wall: List[float] = []
        self._last_step_at: Optional[float] = None
        self.residual: Dict[str, float] = {}
        self.first_residual: Dict[str, float] = {}
        self.linear_iters: Dict[str, int] = {}
        self.courant_max: Optional[float] = None
        self.exec_time: Optional[float] = None
        self.clock_time: Optional[float] = None
        self.converged = False
        self.ended = False
        self.fatal = False
        self.fpe = False
        self.nan = False
        self.first_bad_time: Optional[float] = None
        self.mpi_problem: Optional[str] = None
        self.mesh_failed: Optional[int] = None
        self.cells: Optional[int] = None

    def reset(self) -> None:
        """Forget everything parsed so far (used before a relaunch); keeps clock and hook."""
        self.__init__(self.clock, self.hook)  # type: ignore[misc]

    def feed(self, line: str) -> None:
        self._feed(line)
        if self.hook:
            self.hook(self, line)

    def _feed(self, line: str) -> None:
        m = _TIME.match(line)
        if m:
            now = self.clock()
            if self._last_step_at is not None:
                self.step_wall.append(now - self._last_step_at)
            self._last_step_at = now
            self.time = _num(m.group(1))
            self.steps += 1
            return
        m = _RESID.match(line)
        if m:
            field, r0 = m.group(2), _num(m.group(3))
            if not math.isfinite(r0) or not math.isfinite(_num(m.group(4))):
                self._bad()
            self.residual[field] = r0
            self.first_residual.setdefault(field, r0)
            self.linear_iters[field] = int(m.group(5))
            return
        m = _COURANT.match(line)
        if m:
            self.courant_max = _num(m.group(2))
            if not math.isfinite(self.courant_max):
                self._bad()
            return
        m = _EXEC.match(line)
        if m:
            self.exec_time, self.clock_time = _num(m.group(1)), _num(m.group(2))
            return
        if "solution converged in" in line:
            self.converged = True
        elif line.strip() == "End":
            self.ended = True
        elif _FATAL.search(line):
            self.fatal = True
        elif _FPE.search(line):
            self.fpe = True
            self._bad()
        m = _CHECKMESH_FAIL.search(line)
        if m:
            self.mesh_failed = int(m.group(1))
        m = _CELLS.match(line)
        if m and self.cells is None:
            self.cells = int(m.group(1))
        if self.mpi_problem is None:
            if _MPI_SLOTS.search(line):
                self.mpi_problem = "slots"
            elif "mpi" in line.lower() or "vader" in line.lower() or "hwloc" in line.lower():
                if _MPI_CMA.search(line):
                    self.mpi_problem = "cma"
                elif _MPI_BIND.search(line):
                    self.mpi_problem = "bind"

    def _bad(self) -> None:
        self.nan = True
        if self.first_bad_time is None:
            self.first_bad_time = self.time

    @property
    def diverged(self) -> bool:
        return self.nan or self.fpe

    def wall_per_step(self, skip: int = 2) -> Optional[float]:
        """Median wall seconds per step, ignoring the first ``skip`` steps (start-up)."""
        data = sorted(self.step_wall[skip:]) if len(self.step_wall) > skip else sorted(self.step_wall)
        if not data:
            return None
        mid = len(data) // 2
        return data[mid] if len(data) % 2 else 0.5 * (data[mid - 1] + data[mid])

    def summary(self) -> Dict:
        return {
            "time": self.time, "steps": self.steps, "residual": dict(self.residual),
            "courant_max": self.courant_max, "converged": self.converged, "ended": self.ended,
            "diverged": self.diverged, "first_bad_time": self.first_bad_time, "fatal": self.fatal,
            "mpi_problem": self.mpi_problem, "wall_per_step": self.wall_per_step(),
            "exec_time": self.exec_time, "clock_time": self.clock_time,
        }


def _cpu_times() -> Optional[List[int]]:
    try:
        with open("/proc/stat", encoding="ascii") as fh:
            parts = fh.readline().split()
        return [int(x) for x in parts[1:]]
    except (OSError, ValueError):
        return None


def _mem_used() -> Optional[int]:
    try:
        vals = {}
        with open("/proc/meminfo", encoding="ascii") as fh:
            for line in fh:
                k, v = line.split(":", 1)
                vals[k] = int(v.split()[0]) * 1024
        return vals["MemTotal"] - vals.get("MemAvailable", vals.get("MemFree", 0))
    except (OSError, ValueError, KeyError):
        return None


class UtilSampler(threading.Thread):
    """Background sampler of CPU busy %, RAM use and GPU utilisation (aggregates only)."""

    def __init__(self, interval: float = 5.0, gpu: bool = True):
        super().__init__(daemon=True)
        self.interval = interval
        self.smi = shutil.which("nvidia-smi") if gpu else None
        self._halt = threading.Event()
        self.n = 0
        self.cpu_sum = 0.0
        self.cpu_max = 0.0
        self.mem_base = _mem_used() or 0
        self.mem_peak = 0
        self.gpu_n = 0
        self.gpu_sum = 0.0
        self.gpu_max = 0.0
        self.gpu_mem_peak = 0.0
        self.gpu_power_sum = 0.0
        self.cpu_whole: Optional[float] = None

    def run(self) -> None:
        prev = self._first = _cpu_times()
        while not self._halt.wait(self.interval):
            cur = _cpu_times()
            if prev and cur:
                d = [c - p for c, p in zip(cur, prev)]
                total = sum(d)
                idle = d[3] + (d[4] if len(d) > 4 else 0)
                if total > 0:
                    busy = 100.0 * (total - idle) / total
                    self.n += 1
                    self.cpu_sum += busy
                    self.cpu_max = max(self.cpu_max, busy)
            prev = cur
            used = _mem_used()
            if used is not None:
                self.mem_peak = max(self.mem_peak, used - self.mem_base)
            if self.smi:
                rc, out, _ = run_capture([self.smi, "--query-gpu=utilization.gpu,memory.used,power.draw",
                                          "--format=csv,noheader,nounits"], timeout=10)
                if rc == 0 and out.strip():
                    try:
                        u, mu, pw = (float(x) for x in out.strip().splitlines()[0].split(","))
                        self.gpu_n += 1
                        self.gpu_sum += u
                        self.gpu_max = max(self.gpu_max, u)
                        self.gpu_mem_peak = max(self.gpu_mem_peak, mu)
                        self.gpu_power_sum += pw
                    except ValueError:
                        pass

    def stop(self) -> Dict:
        self._halt.set()
        self.join(timeout=self.interval + 15)
        # whole-run average from the first to the last reading: exists even for runs shorter than one interval
        first, last = getattr(self, "_first", None), _cpu_times()
        if first and last:
            d = [c - p for c, p in zip(last, first)]
            total = sum(d)
            idle = d[3] + (d[4] if len(d) > 4 else 0)
            self.cpu_whole = round(100.0 * (total - idle) / total, 1) if total > 0 else None
        used = _mem_used()
        if used is not None:
            self.mem_peak = max(self.mem_peak, used - self.mem_base)
        return self.summary()

    def summary(self) -> Dict:
        return {
            "samples": self.n,
            "cpu_busy_mean": round(self.cpu_sum / self.n, 1) if self.n else getattr(self, "cpu_whole", None),
            "cpu_busy_max": round(self.cpu_max, 1) if self.n else None,
            "ram_peak_bytes": self.mem_peak,
            "gpu_util_mean": round(self.gpu_sum / self.gpu_n, 1) if self.gpu_n else None,
            "gpu_util_max": round(self.gpu_max, 1) if self.gpu_n else None,
            "gpu_mem_peak_mib": self.gpu_mem_peak if self.gpu_n else None,
            "gpu_power_mean_w": round(self.gpu_power_sum / self.gpu_n, 1) if self.gpu_n else None,
        }
