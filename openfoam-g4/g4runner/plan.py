"""Turn measurements into a plan that keeps every useful part of the G4 busy.

OpenFOAM on its own runs one serial process, never touches the GPU and
binds nothing. The plan fixes that automatically:

* ranks = physical cores (hyper-threads only if a timed trial wins),
* disjoint core sets when several variants share the node,
* GPU linear solver (OGL, Ginkgo) for the pressure equation when the rules
  below allow it and a timed A/B trial on the real case confirms a gain.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional

from . import capacity

MIN_GPU_CELLS = 500_000


def core_groups() -> List[List[int]]:
    """Logical CPU ids grouped by physical core (first id = primary thread)."""
    groups: Dict[str, List[int]] = {}
    base = "/sys/devices/system/cpu"
    try:
        allowed = sorted(os.sched_getaffinity(0))  # type: ignore[attr-defined]
    except AttributeError:
        allowed = list(range(os.cpu_count() or 1))
    for cpu in allowed:
        path = f"{base}/cpu{cpu}/topology/thread_siblings_list"
        try:
            with open(path, encoding="ascii") as fh:
                key = fh.read().strip()
        except OSError:
            key = str(cpu)
        groups.setdefault(key, []).append(cpu)
    return [sorted(v) for _, v in sorted(groups.items(), key=lambda kv: min(kv[1]))]


def cpu_sets(n_jobs: int, cores_per_job: int, groups: Optional[List[List[int]]] = None) -> List[str]:
    """Disjoint ``--cpu-set`` lists (primary threads) so concurrent jobs never share a core."""
    groups = groups if groups is not None else core_groups()
    primaries = [g[0] for g in groups]
    out = []
    for j in range(n_jobs):
        chunk = primaries[j * cores_per_job:(j + 1) * cores_per_job]
        out.append(",".join(str(c) for c in chunk))
    return out


def decide_ranks(hw: Dict, cells: Optional[int], job: Dict, cores_available: Optional[int] = None) -> int:
    physical = int(cores_available or hw["cpu"]["physical"])
    np_ = job.get("np", "auto")
    if isinstance(np_, int):
        return max(1, min(np_, int(hw["cpu"]["logical"])))
    if not cells:
        return physical
    per = int(job.get("min_cells_per_rank", 10000))
    return max(1, min(physical, cells // per))


def gpu_decision(hw: Dict, feats: Dict, cells: Optional[int], job: Dict, ogl_ready: bool,
                 calib: Optional[Dict] = None) -> Dict:
    """Return {'mode': off|ab|on, 'reasons': [...], 'estimate': {...}}."""
    want = job.get("gpu", "auto")
    reasons: List[str] = []
    g = hw.get("gpu", {})
    if want == "off":
        return {"mode": "off", "reasons": ["job asked for gpu: off"]}
    if not g.get("present"):
        return {"mode": "off", "reasons": ["no GPU in this runtime"]}
    if not g.get("healthy", False):
        return {"mode": "off", "reasons": [f"GPU not healthy: {g.get('reason')}"]}
    if feats.get("ami"):
        return {"mode": "off", "reasons": ["sliding mesh (cyclicAMI / non-conformal couples): OGL does not support it"]}
    if feats.get("physics") == "particles_dsmc":
        return {"mode": "off", "reasons": ["particle method (DSMC/MD) has no pressure matrix to offload"]}
    nv = g.get("nvcc_version")
    if not ogl_ready and not nv:
        return {"mode": "off", "reasons": ["no CUDA compiler to build the GPU solver plugin"]}
    est = capacity.estimate({
        "cores_physical": hw["cpu"]["physical"],
        "ram_gb": hw["mem"]["available"] / 1e9,
        "vram_gb": (g["gpus"][0].get("memory.total") or 0) / 1024.0,
        "gpu_bw_gbs": (g.get("bench") or {}).get("d2d_GBs") or capacity.DEFAULTS["gpu_bw_gbs"],
        "cpu_bw_gbs": hw["cpu"].get("triad_GBs") or capacity.DEFAULTS["cpu_bw_gbs"],
        "pcie_gbs": (g.get("bench") or {}).get("h2d_GBs") or capacity.DEFAULTS["pcie_gbs"],
        "cells_m": (cells or 0) / 1e6,
        "physics": feats.get("physics", "incompressible_rans"),
        "iterations": float((calib or {}).get("iterations", 1000)),
        "c_cell_us": (calib or {}).get("c_cell_us", capacity.DEFAULTS["c_cell_us"]),
        "ogl_ready": bool(ogl_ready),
        "ami": False,
    })
    if want == "on":
        return {"mode": "on", "reasons": ["job asked for gpu: on"], "estimate": est}
    if cells is not None and cells < MIN_GPU_CELLS:
        return {"mode": "off", "reasons": [f"{cells} cells < {MIN_GPU_CELLS}: copying the matrix costs more than it saves"],
                "estimate": est}
    if not est["use_gpu"]:
        reasons.append(f"model: speed-up {est['speedup']}x, CPU {est['hours_cpu']} h vs CPU→GPU in parallel {est['hours_par']} h")
        return {"mode": "off", "reasons": reasons, "estimate": est}
    if feats.get("multi_region"):
        reasons.append("multi-region case: OGL untested here, timed trial decides")
    reasons.append(f"model: pressure share {capacity.PHYSICS[feats.get('physics', 'incompressible_rans')]['p_fraction']}, "
                   f"expected speed-up {est['speedup']}x; start on CPU, switch when OGL is ready, keep the faster")
    return {"mode": "ab", "reasons": reasons, "estimate": est}


def ogl_solver_entries(field: str, ranks: int) -> Dict[str, str]:
    """fvSolution edits that move one pressure solve to the GPU (OGL / Ginkgo CG)."""
    base = f"solvers/{field}"
    return {
        f"{base}/solver": "GKOCG",
        f"{base}/preconditioner": "BJ",
        f"{base}/executor": "cuda",
        f"{base}/ranksPerGPU": str(max(1, ranks)),
        f"{base}/updateRHS": "true",
    }


def pick_pressure_fields(names: List[str]) -> List[str]:
    rx = re.compile(r"^(p|p_rgh)(Final)?$")
    return [n for n in names if rx.match(n)]


def concurrency(hw: Dict, n_variants: int, cells: Optional[int], physics: str,
                min_cores_per_job: int = 4) -> Dict[str, int]:
    est = capacity.estimate({
        "cores_physical": hw["cpu"]["physical"], "ram_gb": hw["mem"]["available"] / 1e9,
        "cells_m": (cells or 0) / 1e6, "physics": physics, "variants": n_variants,
        "min_cores_per_job": min_cores_per_job,
    })
    return {"concurrent": int(est["concurrent"]), "cores_per_job": int(est["cores_per_job"])}
