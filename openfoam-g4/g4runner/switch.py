"""Online CPU → GPU switch inside one running job: no separate trial runs, no wasted work.

1. The solver starts on the CPU at once (OGL may still be building).
2. When the accelerator is ready, the next ``M`` steps measure the CPU rate
   on an unloaded machine (and, from the steps before, the slowdown the
   background build caused).
3. If the rest of the run is long enough to pay for a restart, OpenFOAM is
   asked to write the current time and stop (``stopAt writeNow``); the
   pressure solver is switched to the GPU and the run continues from that
   time (``startFrom latestTime``).
4. After ``M`` more steps the GPU rate is compared with the CPU rate; the
   GPU is kept only if it is at least 10 % faster, otherwise the run
   switches back. Every decision is recorded with the measured numbers.
"""

from __future__ import annotations

import os
import re
import shutil
import time
from typing import Callable, Dict, List, Optional, Tuple

from .foam import get_entry, request_stop, set_entry
from .monitor import LogParser
from . import plan

M_STEPS = 20


def _median(xs: List[float]) -> Optional[float]:
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def _num(v: Optional[str]) -> Optional[float]:
    m = re.match(r"^\s*([-+0-9.eE]+)", v or "")
    try:
        return float(m.group(1)) if m else None
    except ValueError:
        return None


class OglAccelerator:
    """Pressure solve on the GPU through OGL (Ginkgo CG, CUDA executor)."""

    name = "GPU (OGL)"

    def __init__(self, builder):
        self.builder = builder

    def ready(self) -> bool:
        return bool(self.builder and self.builder.ready())

    def env(self, base: Dict[str, str]) -> Dict[str, str]:
        return dict(self.builder.env_ogl) if self.builder and self.builder.env_ogl else dict(base)

    def apply(self, env: Dict[str, str], case: str, ranks: int) -> List[str]:
        fv = "system/fvSolution"
        keep = os.path.join(case, ".g4", "fvSolution.cpu")
        os.makedirs(os.path.dirname(keep), exist_ok=True)
        if not os.path.isfile(keep):
            shutil.copy2(os.path.join(case, fv), keep)
        changes = []
        names = [f for f in ("p", "p_rgh", "pFinal", "p_rghFinal") if get_entry(env, case, fv, f"solvers/{f}") is not None]
        for field in plan.pick_pressure_fields(names):
            if field.endswith("Final") and get_entry(env, case, fv, f"solvers/{field}/solver") is None:
                continue  # inherits from p via $p
            for entry, value in plan.ogl_solver_entries(field, ranks).items():
                set_entry(env, case, fv, entry, value)
                changes.append(f"{entry} = {value}")
        libs = get_entry(env, case, "system/controlDict", "libs")
        new_libs = '("libOGL.so")' if not libs else (libs if "libOGL" in libs else libs.rstrip(")").rstrip() + ' "libOGL.so")')
        set_entry(env, case, "system/controlDict", "libs", new_libs)
        changes.append(f"controlDict libs = {new_libs}")
        return changes

    def revert(self, env: Dict[str, str], case: str) -> None:
        keep = os.path.join(case, ".g4", "fvSolution.cpu")
        if os.path.isfile(keep):
            shutil.copy2(keep, os.path.join(case, "system", "fvSolution"))


class SwitchPlan:
    """State machine driven by the solver output (one instance per running variant)."""

    def __init__(self, accel, env: Dict[str, str], case: str, owner: Tuple[str, str], arbiter=None,
                 forced: bool = False, expected_speedup: float = 1.5, m_steps: int = M_STEPS,
                 clock: Callable[[], float] = time.time):
        self.accel, self.env, self.case, self.owner, self.arbiter = accel, env, case, owner, arbiter
        self.forced = forced
        self.expected = max(1.0, expected_speedup)
        self.m = m_steps
        self.clock = clock
        self.phase = "cpu"
        self.pending: Optional[str] = None
        self.events: List[Dict] = []
        self.cpu_rate: Optional[float] = None
        self.cpu_rate_loaded: Optional[float] = None
        self.gpu_rate: Optional[float] = None
        self.startup_s: Optional[float] = None
        self._mark = 0
        self._launch = clock()
        self._first_step: Optional[float] = None
        self._end = _num(get_entry(env, case, "system/controlDict", "endTime"))
        self._dt = _num(get_entry(env, case, "system/controlDict", "deltaT")) or 1.0

    # called before each solver launch
    def launched(self) -> None:
        self._launch = self.clock()
        self._first_step = None

    def note(self, what: str, **kw) -> None:
        ev = {"t": round(self.clock(), 1), "event": what}
        ev.update(kw)
        self.events.append(ev)

    def _remaining_steps(self, p: LogParser) -> Optional[float]:
        if self._end is None or p.time is None:
            return None
        return max(0.0, (self._end - p.time) / self._dt)

    def _request(self, target: str) -> None:
        self.pending = target
        request_stop(self.env, self.case, "writeNow")

    def reached_end(self, p: LogParser) -> bool:
        return self._end is not None and p.time is not None and p.time >= self._end - 0.5 * self._dt

    def on_line(self, p: LogParser) -> None:
        if p.steps == 1 and self._first_step is None:
            self._first_step = self.clock()
            if self.startup_s is None:
                self.startup_s = self._first_step - self._launch
        if self.pending or self.phase in ("gpu_kept", "cpu_final"):
            return
        if self.phase == "cpu":
            if self.accel.ready():
                self.phase = "measure_cpu"
                self._mark = len(p.step_wall)
                self.cpu_rate_loaded = _median(p.step_wall[-self.m:]) if len(p.step_wall) >= 3 else None
                self.note("accelerator_ready", step=p.steps)
            return
        if self.phase == "measure_cpu":
            if len(p.step_wall) - self._mark < (2 if self.forced else self.m):
                return
            self.cpu_rate = _median(p.step_wall[self._mark:])
            rem = self._remaining_steps(p)
            cost = 2.0 * (self.startup_s or 30.0) + self.m * (self.cpu_rate or 0.0)
            saving = (rem or 0.0) * (self.cpu_rate or 0.0) * (1.0 - 1.0 / self.expected)
            if not self.forced and saving <= 3.0 * cost:
                self.phase = "cpu_final"
                self.note("stay_cpu", reason="remaining work too short to pay for a restart",
                          remaining_steps=rem, saving_s=round(saving, 1), cost_s=round(cost, 1))
                return
            if self.arbiter is not None and not self.arbiter.try_acquire(self.owner):
                self.phase = "cpu_final"
                self.note("stay_cpu", reason="GPU held by another task")
                return
            self.note("switch_to_gpu", cpu_s_per_step=self.cpu_rate, cpu_s_per_step_during_build=self.cpu_rate_loaded,
                      remaining_steps=rem)
            self._request("gpu")
            return
        if self.phase == "gpu_trial":
            if len(p.step_wall) < self.m + 2:
                return
            self.gpu_rate = _median(p.step_wall[2:])
            if self.forced or (self.cpu_rate and self.gpu_rate < 0.9 * self.cpu_rate):
                self.phase = "gpu_kept"
                self.note("keep_gpu", gpu_s_per_step=self.gpu_rate, cpu_s_per_step=self.cpu_rate,
                          speedup=round((self.cpu_rate or 0) / self.gpu_rate, 3) if self.gpu_rate else None)
            else:
                self.note("back_to_cpu", gpu_s_per_step=self.gpu_rate, cpu_s_per_step=self.cpu_rate)
                self._request("cpu")

    def after_exit(self) -> Optional[str]:
        """Called when the solver process ended; returns 'gpu'/'cpu' if a switch must happen now."""
        target, self.pending = self.pending, None
        if target == "gpu":
            self.phase = "gpu_trial"
        elif target == "cpu":
            self.phase = "cpu_final"
            if self.arbiter is not None:
                self.arbiter.release(self.owner)
        return target

    def finish(self) -> None:
        if self.arbiter is not None and self.phase != "gpu_kept":
            self.arbiter.release(self.owner)

    def release(self) -> None:
        if self.arbiter is not None:
            self.arbiter.release(self.owner)

    def summary(self) -> Dict:
        build_slowdown = None
        if self.cpu_rate and self.cpu_rate_loaded:
            build_slowdown = round(self.cpu_rate / self.cpu_rate_loaded, 3)
        return {"accelerator": self.accel.name, "phase": self.phase, "cpu_s_per_step": self.cpu_rate,
                "cpu_s_per_step_during_build": self.cpu_rate_loaded, "measured_build_slowdown": build_slowdown,
                "gpu_s_per_step": self.gpu_rate, "startup_s": self.startup_s, "events": self.events}
