"""Measure the machine instead of assuming it: CPU topology, RAM, tmpfs, GPU, ECC, bandwidth.

Everything returned here is a measurement taken in the current session. The
planner (``plan.py``) and the capacity model (``capacity.py``) only consume
these numbers, so the same code adapts if Colab hands out a different shape.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import textwrap
from typing import Any, Dict, List, Optional

from .util import ram_workdir, run_capture, say

_TRIAD_C = r"""
#include <stdio.h>
#include <stdlib.h>
#include <omp.h>
int main(int argc, char **argv) {
    size_t n = argc > 1 ? strtoull(argv[1], 0, 10) : 40000000ULL;
    int reps = argc > 2 ? atoi(argv[2]) : 10;
    double *a = malloc(n * sizeof(double)), *b = malloc(n * sizeof(double)), *c = malloc(n * sizeof(double));
    if (!a || !b || !c) return 2;
    #pragma omp parallel for schedule(static)
    for (size_t i = 0; i < n; i++) { a[i] = 1.0; b[i] = 2.0; c[i] = 0.5; }
    double best = 1e30;
    for (int r = 0; r < reps; r++) {
        double t = omp_get_wtime();
        #pragma omp parallel for schedule(static)
        for (size_t i = 0; i < n; i++) a[i] = b[i] + 3.0 * c[i];
        t = omp_get_wtime() - t;
        if (t < best) best = t;
    }
    double s = 0; for (size_t i = 0; i < n; i += n / 16 + 1) s += a[i];
    printf("TRIAD_GBS %.3f\nCHECK %.3f\nTHREADS %d\n", 24.0 * (double)n / best / 1e9, s, omp_get_max_threads());
    free(a); free(b); free(c);
    return 0;
}
"""

_GPU_BENCH_PY = textwrap.dedent(
    """
    import json, time, torch
    d = torch.device("cuda")
    r = {"torch": torch.__version__, "cuda": torch.version.cuda}
    n = 1 << 28
    x = torch.empty(n, dtype=torch.float32, device=d); y = torch.empty_like(x)
    for _ in range(3): y.copy_(x)
    torch.cuda.synchronize(); t = time.perf_counter(); reps = 20
    for _ in range(reps): y.copy_(x)
    torch.cuda.synchronize(); r["d2d_GBs"] = 2 * n * 4 * reps / (time.perf_counter() - t) / 1e9
    h = torch.empty(n, dtype=torch.float32, pin_memory=True)
    x.copy_(h); torch.cuda.synchronize(); t = time.perf_counter()
    for _ in range(5): x.copy_(h, non_blocking=True)
    torch.cuda.synchronize(); r["h2d_GBs"] = n * 4 * 5 / (time.perf_counter() - t) / 1e9
    del x, y, h
    m = 8192
    A = torch.randn(m, m, dtype=torch.float64, device=d); B = torch.randn(m, m, dtype=torch.float64, device=d)
    A @ B; torch.cuda.synchronize(); t = time.perf_counter(); reps = 3
    for _ in range(reps): C = A @ B
    torch.cuda.synchronize(); r["fp64_TFLOPS"] = 2 * m ** 3 * reps / (time.perf_counter() - t) / 1e12
    torch.backends.cuda.matmul.allow_tf32 = False
    A = A.float(); B = B.float(); A @ B; torch.cuda.synchronize(); t = time.perf_counter(); reps = 10
    for _ in range(reps): C = A @ B
    torch.cuda.synchronize(); r["fp32_TFLOPS"] = 2 * m ** 3 * reps / (time.perf_counter() - t) / 1e12
    print("G4BENCH " + json.dumps(r))
    """
)


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def cpu_info() -> Dict[str, Any]:
    try:
        logical = len(os.sched_getaffinity(0))  # type: ignore[attr-defined]
    except AttributeError:
        logical = os.cpu_count() or 1
    cores = set()
    model, flags, mhz = "", "", 0.0
    phys = core = None
    for line in _read("/proc/cpuinfo").splitlines():
        if ":" not in line:
            continue
        k, v = (s.strip() for s in line.split(":", 1))
        if k == "physical id":
            phys = v
        elif k == "core id":
            core = v
        elif k == "model name" and not model:
            model = v
        elif k == "flags" and not flags:
            flags = v
        elif k == "cpu MHz":
            try:
                mhz = max(mhz, float(v))
            except ValueError:
                pass
        if phys is not None and core is not None:
            cores.add((phys, core))
            phys = core = None
    physical = len(cores) or logical
    numa = len([d for d in os.listdir("/sys/devices/system/node") if re.match(r"node\d+$", d)]) if os.path.isdir(
        "/sys/devices/system/node"
    ) else 1
    fl = set(flags.split())
    return {
        "model": model or "unknown",
        "logical": logical,
        "physical": min(physical, logical),
        "threads_per_core": max(1, round(logical / max(1, min(physical, logical)))),
        "numa_nodes": max(1, numa),
        "avx512": "avx512f" in fl,
        "avx2": "avx2" in fl,
        "mhz_seen": round(mhz, 1),
    }


def mem_info() -> Dict[str, Any]:
    vals: Dict[str, int] = {}
    for line in _read("/proc/meminfo").splitlines():
        m = re.match(r"^(\w+):\s+(\d+)\s*kB", line)
        if m:
            vals[m.group(1)] = int(m.group(2)) * 1024
    return {
        "total": vals.get("MemTotal", 0),
        "available": vals.get("MemAvailable", vals.get("MemFree", 0)),
        "swap_total": vals.get("SwapTotal", 0),
    }


def shm_info(path: Optional[str] = None) -> Dict[str, Any]:
    path = path or ram_workdir()
    du = shutil.disk_usage(path)
    from .util import is_ram_path

    return {"path": path, "total": du.total, "free": du.free, "in_ram": is_ram_path(path)}


def parse_ecc(text: str) -> Dict[str, Any]:
    """Parse ``nvidia-smi -q -d ECC``: the counters of the GPU memory's Hamming SECDED code.

    Newer drivers print ``SRAM/DRAM Correctable/Uncorrectable : n``; older ones
    group ``Single Bit`` / ``Double Bit`` blocks whose ``Total`` line is the count.
    """
    out = {"mode": None, "volatile_corrected": 0, "volatile_uncorrected": 0,
           "aggregate_corrected": 0, "aggregate_uncorrected": 0}
    scope = bitscope = None
    in_mode = False
    for raw in text.splitlines():
        line = raw.strip()
        low = line.lower()
        if low.startswith("ecc mode"):
            in_mode = True
            continue
        if in_mode and low.startswith("current") and ":" in line:
            out["mode"] = line.split(":", 1)[1].strip()
            in_mode = False
            continue
        if low.startswith("volatile"):
            scope, bitscope = "volatile", None
            continue
        if low.startswith("aggregate"):
            scope, bitscope = "aggregate", None
            continue
        if low in ("single bit", "double bit"):
            bitscope = "corrected" if low.startswith("single") else "uncorrected"
            continue
        if scope and ":" in line:
            key, val = (x.strip() for x in line.split(":", 1))
            if not val.isdigit():
                continue
            k = key.lower()
            if bitscope:
                if k == "total":
                    out[f"{scope}_{bitscope}"] += int(val)
            elif "uncorrectable" in k:
                out[f"{scope}_uncorrected"] += int(val)
            elif "correctable" in k:
                out[f"{scope}_corrected"] += int(val)
    return out


def gpu_info() -> Dict[str, Any]:
    smi = shutil.which("nvidia-smi")
    if not smi:
        return {"present": False, "reason": "nvidia-smi not found"}
    fields = ["index", "name", "memory.total", "memory.used", "driver_version", "compute_cap",
              "power.limit", "clocks.max.sm", "pcie.link.gen.max", "pcie.link.width.max"]
    rc, out, err = run_capture([smi, f"--query-gpu={','.join(fields)}", "--format=csv,noheader,nounits"], timeout=30)
    if rc != 0:
        rc, out, err = run_capture([smi, "--query-gpu=index,name,memory.total,memory.used,driver_version",
                                    "--format=csv,noheader,nounits"], timeout=30)
        fields = fields[:5]
    if rc != 0 or not out.strip():
        return {"present": False, "reason": (err or out).strip()[:200]}
    gpus: List[Dict[str, Any]] = []
    for line in out.strip().splitlines():
        vals = [v.strip() for v in line.split(",")]
        g = dict(zip(fields, vals))
        for k in ("memory.total", "memory.used", "power.limit", "clocks.max.sm"):
            try:
                g[k] = float(g[k])
            except (KeyError, ValueError):
                g[k] = None
        gpus.append(g)
    _, ecc_txt, _ = run_capture([smi, "-q", "-d", "ECC"], timeout=30)
    ecc = parse_ecc(ecc_txt)
    _, rr_txt, _ = run_capture([smi, "-q", "-d", "ROW_REMAPPER"], timeout=30)
    remap_fail = bool(re.search(r"Remapping Failure Occurred\s*:\s*Yes", rr_txt))
    remap_pending = bool(re.search(r"Pending\s*:\s*Yes", rr_txt))
    healthy = ecc["volatile_uncorrected"] == 0 and not remap_fail and not remap_pending
    nvcc = shutil.which("nvcc") or ("/usr/local/cuda/bin/nvcc" if os.path.exists("/usr/local/cuda/bin/nvcc") else None)
    nvcc_ver = None
    if nvcc:
        _, o, _ = run_capture([nvcc, "--version"], timeout=30)
        m = re.search(r"release (\d+\.\d+)", o)
        nvcc_ver = m.group(1) if m else None
    reason = None if healthy else "uncorrectable ECC errors or pending/failed row remap"
    return {"present": True, "gpus": gpus, "count": len(gpus), "ecc": ecc, "row_remap_failure": remap_fail,
            "row_remap_pending": remap_pending, "healthy": healthy, "reason": reason, "nvcc": nvcc, "nvcc_version": nvcc_ver}


def bench_cpu_bandwidth(threads: int, mem_available: int) -> Optional[float]:
    """STREAM-style triad (24 bytes per element), compiled and run inside RAM."""
    gcc = shutil.which("gcc") or shutil.which("cc")
    if not gcc:
        return None
    work = os.path.join(ram_workdir(), "bench")
    os.makedirs(work, mode=0o700, exist_ok=True)
    src, exe = os.path.join(work, "triad.c"), os.path.join(work, "triad")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(_TRIAD_C)
    rc, _, err = run_capture([gcc, "-O3", "-march=native", "-fopenmp", "-o", exe, src], timeout=120)
    if rc != 0:
        rc, _, err = run_capture([gcc, "-O3", "-fopenmp", "-o", exe, src], timeout=120)
    if rc != 0:
        say(f"triad compile failed: {err.strip()[:120]}", "warn")
        return None
    n = int(max(4_000_000, min(80_000_000, mem_available * 0.04 / 24)))
    env = dict(os.environ, OMP_NUM_THREADS=str(threads), OMP_PROC_BIND="spread", OMP_PLACES="cores")
    rc, out, _ = run_capture([exe, str(n), "10"], env=env, timeout=600)
    m = re.search(r"TRIAD_GBS\s+([\d.]+)", out)
    return float(m.group(1)) if rc == 0 and m else None


def bench_gpu(timeout: float = 600) -> Optional[Dict[str, Any]]:
    """Bandwidth and FP64/FP32 throughput with PyTorch (preinstalled on Colab)."""
    py = shutil.which("python3")
    if not py:
        return None
    rc, out, err = run_capture([py, "-c", "import torch,sys;sys.exit(0 if torch.cuda.is_available() else 3)"], timeout=120)
    if rc != 0:
        return None
    rc, out, err = run_capture([py, "-c", _GPU_BENCH_PY], timeout=timeout)
    m = re.search(r"G4BENCH (\{.*\})", out)
    if rc != 0 or not m:
        say(f"GPU benchmark failed: {(err or out).strip()[-200:]}", "warn")
        return None
    return json.loads(m.group(1))


def probe(bench: bool = False) -> Dict[str, Any]:
    cpu, mem, gpu = cpu_info(), mem_info(), gpu_info()
    hw: Dict[str, Any] = {"cpu": cpu, "mem": mem, "shm": shm_info(), "gpu": gpu}
    if bench:
        say(f"measuring memory bandwidth on {cpu['physical']} cores ...")
        hw["cpu"]["triad_GBs"] = bench_cpu_bandwidth(cpu["physical"], mem["available"])
        if gpu.get("present") and gpu.get("healthy"):
            say("measuring GPU bandwidth and FP64/FP32 throughput ...")
            hw["gpu"]["bench"] = bench_gpu()
    return hw


def summary_lines(hw: Dict[str, Any]) -> List[str]:
    from .util import human_bytes

    c, m, s, g = hw["cpu"], hw["mem"], hw["shm"], hw["gpu"]
    lines = [
        f"CPU  {c['model']} · {c['physical']} lõi vật lý / {c['logical']} luồng · NUMA {c['numa_nodes']}"
        + (" · AVX-512" if c.get("avx512") else ""),
        f"RAM  {human_bytes(m['total'])} tổng · {human_bytes(m['available'])} trống · swap {human_bytes(m['swap_total'])}",
        f"RAM-disk {s['path']} · {human_bytes(s['free'])} trống · tmpfs={s['in_ram']}",
    ]
    if c.get("triad_GBs"):
        lines.append(f"Băng thông RAM đo được (triad) {c['triad_GBs']:.0f} GB/s")
    if g.get("present"):
        for gg in g["gpus"]:
            lines.append(
                f"GPU{gg.get('index')} {gg.get('name')} · {gg.get('memory.total')} MiB · CC {gg.get('compute_cap', '?')}"
                f" · driver {gg.get('driver_version')}"
            )
        e = g["ecc"]
        lines.append(
            f"ECC (Hamming SECDED) mode={e['mode']} · đã sửa {e['volatile_corrected']} · không sửa được "
            f"{e['volatile_uncorrected']} · {'khoẻ' if g['healthy'] else 'KHÔNG khoẻ'}"
        )
        if g.get("bench"):
            b = g["bench"]
            lines.append(
                f"GPU đo được: {b.get('d2d_GBs', 0):.0f} GB/s nội bộ · {b.get('h2d_GBs', 0):.1f} GB/s PCIe · "
                f"FP64 {b.get('fp64_TFLOPS', 0):.2f} TFLOPS · FP32 {b.get('fp32_TFLOPS', 0):.1f} TFLOPS"
            )
    else:
        lines.append(f"GPU  không có ({g.get('reason')})")
    return lines
