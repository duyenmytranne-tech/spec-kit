"""Self-healing after divergence: step back to the last good time and soften the numerics.

Each attempt raises the level of a "safe profile" (more under-relaxation,
smaller time step, then first-order convection). Every change is recorded
and printed, because results produced after healing used different
numerics and need re-checking (CN8).

Bad time directories are moved aside inside the RAM work dir, never
deleted.
"""

from __future__ import annotations

import os
import re
import shutil
from typing import Dict, List, Optional

from .foam import get_entry, set_entry, time_dirs
from .util import say


def _float(v: Optional[str]) -> Optional[float]:
    if v is None:
        return None
    m = re.match(r"^\s*([-+0-9.eE]+)", v)
    try:
        return float(m.group(1)) if m else None
    except ValueError:
        return None


def last_good_time(case: str, first_bad: Optional[float]) -> Optional[str]:
    base = os.path.join(case, "processor0") if os.path.isdir(os.path.join(case, "processor0")) else case
    times = [t for t in time_dirs(base) if float(t) > 0]
    if first_bad is not None:
        times = [t for t in times if float(t) < first_bad]
    return times[-1] if times else None


def quarantine_after(case: str, good: Optional[str], attempt: int) -> List[str]:
    """Move time directories newer than ``good`` (all processors) into .g4/quarantine/."""
    moved: List[str] = []
    limit = float(good) if good else 0.0
    roots = [case] + sorted(os.path.join(case, d) for d in os.listdir(case) if re.match(r"^processor\d+$", d))
    for root in roots:
        for t in time_dirs(root):
            if float(t) > limit:
                rel = os.path.relpath(os.path.join(root, t), case)
                dest = os.path.join(case, ".g4", "quarantine", str(attempt), rel)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.move(os.path.join(root, t), dest)
                moved.append(rel)
    return moved


def _try(env: Dict[str, str], case: str, rel: str, entry: str, value: str, log: List[str]) -> bool:
    try:
        set_entry(env, case, rel, entry, value)
        log.append(f"{rel}: {entry} = {value}")
        return True
    except RuntimeError as exc:
        say(f"heal: could not set {entry} in {rel}: {str(exc)[-120:]}", "debug")
        return False


def apply_safe_profile(env: Dict[str, str], case: str, level: int, steady: bool) -> List[str]:
    """Soften the numerics; ``level`` 1..3. Returns the list of changes made."""
    log: List[str] = []
    fs, fv, cd = "system/fvSchemes", "system/fvSolution", "system/controlDict"
    if steady:
        u = {1: "0.7", 2: "0.5", 3: "0.3"}[min(level, 3)]
        p = {1: "0.3", 2: "0.2", 3: "0.1"}[min(level, 3)]
        _try(env, case, fv, "SIMPLE/consistent", "no", log)
        _try(env, case, fv, "relaxationFactors/equations/U", u, log)
        _try(env, case, fv, 'relaxationFactors/equations/".*"', u, log)
        if not _try(env, case, fv, "relaxationFactors/fields/p", p, log):
            _try(env, case, fv, "relaxationFactors/p", p, log)
    else:
        adjustable = (get_entry(env, case, cd, "adjustTimeStep") or "no").strip() in ("yes", "on", "true")
        if adjustable:
            co = _float(get_entry(env, case, cd, "maxCo")) or 1.0
            _try(env, case, cd, "maxCo", f"{co / 2.0:g}", log)
        else:
            dt = _float(get_entry(env, case, cd, "deltaT"))
            if dt:
                _try(env, case, cd, "deltaT", f"{dt / 2.0:g}", log)
        for algo in ("PIMPLE", "PISO"):
            nc = _float(get_entry(env, case, fv, f"{algo}/nCorrectors"))
            if nc is not None:
                _try(env, case, fv, f"{algo}/nCorrectors", str(int(nc) + 1), log)
    if level >= 2:
        conv = "bounded Gauss upwind" if steady else "Gauss upwind"
        for field in ("U", "k", "epsilon", "omega", "nuTilda"):
            _try(env, case, fs, f"divSchemes/div(phi,{field})", conv, log)
        for algo in ("SIMPLE", "PIMPLE", "PISO"):
            if get_entry(env, case, fv, f"{algo}/nNonOrthogonalCorrectors") is not None:
                _try(env, case, fv, f"{algo}/nNonOrthogonalCorrectors", "2", log)
        _try(env, case, fs, "gradSchemes/default", "cellLimited Gauss linear 1", log)
    return log


def prepare_restart(env: Dict[str, str], case: str, first_bad: Optional[float], attempt: int,
                    steady: bool) -> Dict:
    good = last_good_time(case, first_bad)
    moved = quarantine_after(case, good, attempt)
    changes = apply_safe_profile(env, case, attempt, steady)
    cd = "system/controlDict"
    if good:
        set_entry(env, case, cd, "startFrom", "latestTime")
    else:
        set_entry(env, case, cd, "startFrom", "startTime")
    return {"attempt": attempt, "restart_from": good or "startTime", "quarantined": moved, "changes": changes}
