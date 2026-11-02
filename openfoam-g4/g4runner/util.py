"""Small shared helpers: console output, retries, subprocess, RAM work dir."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from typing import Callable, Dict, List, Optional, Sequence, Tuple, TypeVar

T = TypeVar("T")

_QUIET = os.environ.get("G4_QUIET", "") == "1"

#: Backoff schedule (seconds) for network operations: 2, 4, 8, 16.
BACKOFF = (2, 4, 8, 16)


def say(msg: str, level: str = "info") -> None:
    """Print one line to the console. Nothing is written to any file."""
    if _QUIET and level == "debug":
        return
    tag = {"info": "·", "ok": "✓", "warn": "!", "err": "✗", "debug": " "}.get(level, "·")
    stream = sys.stderr if level == "err" else sys.stdout
    print(f"[g4 {tag}] {msg}", file=stream, flush=True)


def retry(
    fn: Callable[[], T],
    delays: Sequence[float] = BACKOFF,
    retry_on: Tuple[type, ...] = (Exception,),
    sleep: Callable[[float], None] = time.sleep,
    what: str = "operation",
) -> T:
    """Call ``fn``; on failure wait 2, 4, 8, 16 s and try again (5 tries total)."""
    last: Optional[BaseException] = None
    for attempt in range(len(delays) + 1):
        try:
            return fn()
        except retry_on as exc:  # noqa: PERF203 - retry loop by design
            last = exc
            if attempt == len(delays):
                break
            wait = delays[attempt]
            say(f"{what} failed ({exc}); retry {attempt + 1}/{len(delays)} in {wait:g}s", "warn")
            sleep(wait)
    assert last is not None
    raise last


def run_capture(
    cmd: Sequence[str],
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: Optional[float] = None,
    input_text: Optional[str] = None,
) -> Tuple[int, str, str]:
    """Run a command without a shell and return (returncode, stdout, stderr)."""
    if env is not None and cwd is not None:
        env = dict(env, PWD=os.path.abspath(cwd))  # OpenFOAM warns on stdout when PWD != cwd
    try:
        proc = subprocess.run(
            list(cmd),
            cwd=cwd,
            env=env,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout if isinstance(exc.stdout, str) else ""
        return 124, out, f"timeout after {timeout}s"
    return proc.returncode, proc.stdout, proc.stderr


def ram_workdir(name: str = "g4") -> str:
    """Return a private working directory in RAM.

    Order: ``$G4_WORKDIR`` (set by :func:`prepare_workdir`), then ``/dev/shm``
    (a tmpfs on Linux, so nothing reaches a disk), then the OS temp dir
    (macOS; the Mac side never runs solvers, so this only matters for tests).
    """
    override = os.environ.get("G4_WORKDIR")
    if override:
        base = override
    elif os.path.isdir("/dev/shm") and os.access("/dev/shm", os.W_OK):
        base = "/dev/shm"
    else:
        base = tempfile.gettempdir()
    path = base if override else os.path.join(base, name)
    os.makedirs(path, mode=0o700, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def prepare_workdir(min_free: int, ram_total: int) -> Tuple[str, bool]:
    """Make sure the work dir is in RAM and large enough; returns (path, in_ram).

    If ``/dev/shm`` is smaller than ``min_free`` (containers often cap it),
    mount a private tmpfs sized to 60 % of RAM at ``/mnt/g4ram``. If that is
    not permitted either, fall back to the OS temp dir and say so plainly.
    """
    import shutil

    if os.environ.get("G4_WORKDIR"):
        p = ram_workdir()
        return p, is_ram_path(p)
    shm = "/dev/shm"
    if os.path.isdir(shm) and os.access(shm, os.W_OK) and shutil.disk_usage(shm).free >= min_free:
        p = ram_workdir()
        return p, is_ram_path(p)
    mnt = "/mnt/g4ram"
    size_mib = max(1024, int(ram_total * 0.6 / (1 << 20)))
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        os.makedirs(mnt, mode=0o700, exist_ok=True)
        if not is_ram_path(mnt):
            rc, _, err = run_capture(["mount", "-t", "tmpfs", "-o", f"size={size_mib}m,mode=700", "tmpfs", mnt], timeout=30)
            if rc != 0:
                say(f"could not mount a tmpfs ({err.strip()[:120]})", "warn")
        if is_ram_path(mnt):
            os.environ["G4_WORKDIR"] = mnt
            return mnt, True
    p = os.path.join(tempfile.gettempdir(), "g4")
    os.makedirs(p, mode=0o700, exist_ok=True)
    os.environ["G4_WORKDIR"] = p
    say(f"no RAM disk of {min_free >> 30} GiB available: working on the VM disk at {p} (deleted with the runtime)", "warn")
    return p, False


def is_ram_path(path: str) -> bool:
    """True when ``path`` lives on a tmpfs/ramfs mount (checked via /proc/mounts)."""
    try:
        real = os.path.realpath(path)
        best, fstype = "", ""
        with open("/proc/mounts", encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) < 3:
                    continue
                mnt, typ = parts[1], parts[2]
                if (real == mnt or real.startswith(mnt.rstrip("/") + "/")) and len(mnt) > len(best):
                    best, fstype = mnt, typ
        return fstype in ("tmpfs", "ramfs")
    except OSError:
        return False


def human_bytes(n: float) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    i = 0
    while abs(n) >= 1024 and i < len(units) - 1:
        n /= 1024.0
        i += 1
    return f"{n:.1f} {units[i]}"


def fmt_duration(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    h, rem = divmod(int(round(seconds)), 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}h{m:02d}m{s:02d}s" if h else f"{m:d}m{s:02d}s"


def which_all(names: List[str], path: Optional[str] = None) -> Dict[str, Optional[str]]:
    import shutil

    return {n: shutil.which(n, path=path) for n in names}
