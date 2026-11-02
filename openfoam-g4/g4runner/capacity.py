"""Capacity model of a G4 runtime for OpenFOAM: pure functions, no I/O.

The HTML report carries a JavaScript port of ``estimate`` (function
``g4Estimate``). Both use only +, -, *, /, floor, ceil, min and max, which
IEEE-754 defines exactly, so for the same inputs they return the same
doubles bit for bit; ``tests/test_capacity_parity.py`` checks this.

Defaults are labelled assumptions; the runner replaces ``c_cell_us`` and
``cpu_bw_gbs`` with values it measures in the session.
"""

from __future__ import annotations

import math
from typing import Any, Dict

#: kB of RAM per cell and the share of solver time spent in the pressure
#: solve (the part a GPU linear solver can take over). Rules of thumb.
PHYSICS: Dict[str, Dict[str, Any]] = {
    "incompressible_rans": {"kb_per_cell": 1.2, "p_fraction": 0.45, "p_solves": 1.0, "gpu_ok": True},
    "incompressible_transient": {"kb_per_cell": 1.2, "p_fraction": 0.60, "p_solves": 2.0, "gpu_ok": True},
    "incompressible_les": {"kb_per_cell": 1.4, "p_fraction": 0.60, "p_solves": 2.0, "gpu_ok": True},
    "buoyant": {"kb_per_cell": 1.6, "p_fraction": 0.45, "p_solves": 1.0, "gpu_ok": True},
    "compressible": {"kb_per_cell": 1.8, "p_fraction": 0.35, "p_solves": 2.0, "gpu_ok": True},
    "vof": {"kb_per_cell": 1.6, "p_fraction": 0.40, "p_solves": 3.0, "gpu_ok": True},
    "multiphase_euler": {"kb_per_cell": 3.5, "p_fraction": 0.25, "p_solves": 2.0, "gpu_ok": True},
    "reacting": {"kb_per_cell": 2.5, "p_fraction": 0.10, "p_solves": 2.0, "gpu_ok": True},
    "cht_multiregion": {"kb_per_cell": 1.8, "p_fraction": 0.30, "p_solves": 1.0, "gpu_ok": True},
    "particles_dsmc": {"kb_per_cell": 2.0, "p_fraction": 0.0, "p_solves": 0.0, "gpu_ok": False},
    "electrostatic": {"kb_per_cell": 0.6, "p_fraction": 0.0, "p_solves": 0.0, "gpu_ok": False},
}

DEFAULTS: Dict[str, Any] = {
    "cores_physical": 24,      # g4-standard-48: 48 vCPU = 24 cores x 2 threads (preflight measures)
    "ram_gb": 176.0,           # seen in a Colab G4 session; preflight measures MemAvailable
    "vram_gb": 96.0,           # RTX PRO 6000 Blackwell Server Edition
    "gpu_bw_gbs": 1597.0,      # GDDR7 512-bit, published figure
    "cpu_bw_gbs": 144.0,       # assumption: 1/8 of a 2-socket Turin host; preflight measures triad
    "pcie_gbs": 50.0,          # PCIe 5.0 x16 achievable host->device (assumption; measured)
    "cells_m": 10.0,
    "physics": "incompressible_rans",
    "iterations": 2000.0,
    "c_cell_us": 2.0,          # microseconds x core per cell per iteration (calibrated in session)
    "cpu_eff": 0.6,            # share of CPU bandwidth a sparse solve achieves
    "gpu_eff": 0.6,            # share of GPU bandwidth a sparse solve achieves
    "min_cells_per_rank": 10000.0,
    "ram_headroom": 0.85,
    "vram_headroom": 0.9,
    "gpu_bytes_per_cell": 400.0,
    "transfer_bytes_per_cell": 72.0,
    "ami": False,              # sliding mesh (cyclicAMI / non-conformal couples) => no GPU solver
    "ogl_build_h": 0.4,        # zero-retention: GPU plugin rebuilt every session (assumption; runner times it)
    "ogl_overlap": True,       # CPU starts at once, OGL builds in the background, switch to GPU when ready
    "ogl_ready": False,        # OGL already built earlier in this session
    "build_slowdown": 0.85,    # CPU speed while the build shares the cores (assumption; runner measures)
    "switch_h": 0.02,          # write the latest time and restart on the GPU solver
    "cu_per_hour": 8.71,       # third-party snapshot; Colab shows the live rate
    "usd_per_cu": 0.0999,      # $9.99 per 100 compute units
    "session_hours": 24.0,     # Colab Pro+ background execution limit
    "variants": 1.0,
    "min_cores_per_job": 4.0,  # concurrent variants never get fewer cores than this
}


def _round(x: float, scale: float) -> float:
    """Round half up at 1/scale, written so JavaScript gives the same bits."""
    return math.floor(x * scale + 0.5) / scale


def estimate(inp: Dict[str, Any]) -> Dict[str, Any]:
    p = dict(DEFAULTS)
    p.update({k: v for k, v in inp.items() if v is not None})
    phys = PHYSICS[p["physics"]]
    cores = float(max(1, int(p["cores_physical"])))
    cells = float(p["cells_m"]) * 1000000.0
    variants = float(max(1, int(p["variants"])))

    # concurrency: several variants share the node, each gets >= 4 cores, RAM permitting
    ram_need_gb = float(p["cells_m"]) * phys["kb_per_cell"]
    ram_budget = float(p["ram_gb"]) * float(p["ram_headroom"])
    mcj = float(max(1, int(p["min_cores_per_job"])))
    by_cores = math.floor(cores / mcj) if cores >= mcj else 1.0
    by_ram = math.floor(ram_budget / ram_need_gb) if ram_need_gb > 0 else variants
    concurrent = max(1.0, min(variants, max(1.0, by_cores), max(1.0, by_ram)))
    cores_per_job = math.floor(cores / concurrent)

    ranks = min(cores_per_job, max(1.0, math.floor(cells / float(p["min_cells_per_rank"]))))
    cells_per_rank = cells / ranks
    t_iter_cpu = cells * float(p["c_cell_us"]) * 0.000001 / ranks

    gpu_allowed = bool(phys["gpu_ok"]) and not bool(p["ami"]) and float(p["vram_gb"]) > 0.0
    vram_need_gb = cells * float(p["gpu_bytes_per_cell"]) / 1000000000.0
    vram_fit = vram_need_gb <= float(p["vram_gb"]) * float(p["vram_headroom"])
    s_p = (float(p["gpu_bw_gbs"]) * float(p["gpu_eff"])) / (float(p["cpu_bw_gbs"]) * float(p["cpu_eff"]))
    s_p = min(s_p, 20.0)
    t_transfer = cells * float(p["transfer_bytes_per_cell"]) * phys["p_solves"] / (float(p["pcie_gbs"]) * 1000000000.0)
    overhead = t_transfer / t_iter_cpu if t_iter_cpu > 0 else 0.0
    f = phys["p_fraction"]
    speedup = 1.0 / ((1.0 - f) + f / s_p + overhead) if gpu_allowed and vram_fit and f > 0 else 1.0

    iters = float(p["iterations"])
    hours_cpu = iters * t_iter_cpu / 3600.0
    t_b = 0.0 if bool(p["ogl_ready"]) else float(p["ogl_build_h"])
    k = float(p["build_slowdown"])
    # B: build first, then run on the GPU from the start
    hours_gpu = hours_cpu / speedup + t_b
    # C: run on the CPU at once, build in the background, switch the pressure solve to the GPU when ready
    if t_b <= 0.0:
        hours_par = hours_cpu / speedup + float(p["switch_h"])
    elif hours_cpu / k <= t_b:
        hours_par = hours_cpu / k
    else:
        hours_par = t_b + (hours_cpu - k * t_b) / speedup + float(p["switch_h"])
    if not bool(p["ogl_overlap"]):
        hours_par = hours_gpu
    eligible = gpu_allowed and vram_fit and speedup >= 1.1
    use_gpu = eligible and hours_par < hours_cpu
    hours_job = hours_par if use_gpu else hours_cpu
    waves = math.ceil(variants / concurrent)
    hours_total = hours_job * waves
    cu = hours_total * float(p["cu_per_hour"])
    usable_session = float(p["session_hours"]) - 0.5
    fits_session = hours_total <= usable_session

    return {
        "physics": p["physics"],
        "ram_need_gb": _round(ram_need_gb, 1000.0),
        "ram_fit": ram_need_gb <= ram_budget,
        "cells_max_m": _round(ram_budget / phys["kb_per_cell"], 10.0),
        "concurrent": concurrent,
        "cores_per_job": cores_per_job,
        "ranks": ranks,
        "cells_per_rank": _round(cells_per_rank, 1.0),
        "t_iter_cpu_s": _round(t_iter_cpu, 10000.0),
        "gpu_allowed": gpu_allowed,
        "vram_need_gb": _round(vram_need_gb, 1000.0),
        "vram_fit": vram_fit,
        "s_pressure": _round(s_p, 100.0),
        "overhead": _round(overhead, 10000.0),
        "speedup": _round(speedup, 1000.0),
        "use_gpu": use_gpu,
        "hours_cpu": _round(hours_cpu, 1000.0),
        "hours_gpu": _round(hours_gpu, 1000.0),
        "hours_par": _round(hours_par, 1000.0),
        "hours_total": _round(hours_total, 1000.0),
        "cu": _round(cu, 100.0),
        "usd": _round(cu * float(p["usd_per_cu"]), 100.0),
        "fits_session": fits_session,
        "raw": {"t_iter_cpu": t_iter_cpu, "speedup": speedup, "hours_par": hours_par, "hours_total": hours_total, "cu": cu},
    }
