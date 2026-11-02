"""Install OpenFOAM 14 inside a Colab session (the OGL plugin is built by ``gpu.OglBuilder``).

Zero retention: downloaded packages and apt/dpkg logs stay in RAM
(``/dev/shm``); only the installed software itself lands in the ephemeral
VM's system directories, which vanish with the runtime.
"""

from __future__ import annotations

import os
import re
import shutil
import urllib.request
from typing import Dict

from .foam import find_bashrc, foam_env
from .util import ram_workdir, retry, run_capture, say

FOUNDATION_KEY_URL = "https://dl.openfoam.org/gpg.key"
FOUNDATION_REPO = "http://dl.openfoam.org/ubuntu"


def _codename() -> str:
    try:
        with open("/etc/os-release", encoding="utf-8") as fh:
            m = re.search(r"^VERSION_CODENAME=(\w+)", fh.read(), re.M)
            return m.group(1) if m else "jammy"
    except OSError:
        return "jammy"


def _apt(args, ram: str) -> None:
    """apt-get with package cache and logs redirected into RAM."""
    os.makedirs(os.path.join(ram, "apt", "archives", "partial"), exist_ok=True)
    os.makedirs(os.path.join(ram, "apt", "log"), exist_ok=True)
    cmd = ["apt-get", "-y", "-qq",
           "-o", f"Dir::Cache::Archives={ram}/apt/archives",
           "-o", f"Dir::Log={ram}/apt/log",
           "-o", "DPkg::Options::=--log=/dev/null"] + list(args)
    env = dict(os.environ, DEBIAN_FRONTEND="noninteractive")

    def once() -> None:
        rc, out, err = run_capture(cmd, env=env, timeout=3600)
        if rc != 0:
            raise RuntimeError((err or out).strip()[-400:])

    retry(once, what="apt-get " + " ".join(args[:2]))


def ensure_openfoam(version: str = "14") -> Dict[str, str]:
    """Return an OpenFOAM environment, installing the Foundation pack via apt if needed."""
    env = foam_env()
    if env:
        return env
    if os.geteuid() != 0 or not shutil.which("apt-get"):
        raise RuntimeError("OpenFOAM is not installed and this is not a root apt system (expected on Colab)")
    ram = ram_workdir()
    say(f"installing OpenFOAM {version} (Foundation) for Ubuntu {_codename()} ...")

    def get_key() -> bytes:
        with urllib.request.urlopen(FOUNDATION_KEY_URL, timeout=60) as resp:  # noqa: S310 - fixed https URL
            return resp.read()

    key = retry(get_key, what="download OpenFOAM signing key")
    with open("/etc/apt/trusted.gpg.d/openfoam.asc", "wb") as fh:
        fh.write(key)
    with open("/etc/apt/sources.list.d/openfoam.list", "w", encoding="utf-8") as fh:
        fh.write(f"deb {FOUNDATION_REPO} {_codename()} main\n")
    _apt(["update"], ram)
    _apt(["install", f"openfoam{version}"], ram)
    env = foam_env(find_bashrc())
    if not env:
        raise RuntimeError(f"openfoam{version} installed but no bashrc found")
    say(f"OpenFOAM {env.get('WM_PROJECT_VERSION')} ready ({env.get('G4_BASHRC')})", "ok")
    return env
