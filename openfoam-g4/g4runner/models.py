"""Model lane: when OpenFOAM is not using the GPU, run your own model on it at the same time.

A model job runs a Python script from the repository (for example PyTorch
training of a surrogate, or inference). That is code execution, so:

* it runs only if the Colab operator set ``G4_ALLOW_MODELS=1`` (a job file
  cannot turn it on);
* the script folder must match the SHA-256 manifest signed on the Mac;
* it gets the GPU only through the arbiter (never while an OpenFOAM job has
  switched its pressure solve to the GPU), a few CPU threads the solver does
  not use, a low priority, and an environment without the GitHub token;
* caches (Hugging Face, torch, pip, matplotlib) point into RAM, the working
  directory is in RAM, output goes to the console only.
"""

from __future__ import annotations

import os
import shutil
import sys
import threading
import time
from typing import Dict, List, Optional

from . import RETENTION, manifest
from .foam import Stream, say_tail
from .gpu import limited
from .monitor import UtilSampler
from .util import fmt_duration, ram_workdir, say

_SECRET_VARS = ("G4_GIT_TOKEN", "GH_TOKEN", "GITHUB_TOKEN", "GIT_ASKPASS")


def allowed_by_operator() -> bool:
    return os.environ.get("G4_ALLOW_MODELS", "") == "1"


class ModelTask(threading.Thread):
    def __init__(self, job: Dict, home: str, cpus: Optional[List[int]], arbiter, deadline: float):
        super().__init__(daemon=True, name=f"model-{job['id']}")
        self.job, self.home, self.cpus, self.arbiter, self.deadline = job, home, cpus, arbiter, deadline
        self.owner = ("model", job["id"])
        self.report: Dict = {"id": job["id"], "kind": "model", "title": job.get("title"), "retention": RETENTION,
                             "status": "queued", "notes": []}

    def run(self) -> None:
        t0 = time.time()
        m = self.job["model"]
        try:
            if not allowed_by_operator():
                raise PermissionError("model jobs need G4_ALLOW_MODELS=1 on the Colab side")
            src = os.path.join(self.home, m["dir"])
            ok, diffs, actual = manifest.verify(src, m["manifest"])
            if not ok:
                raise PermissionError("model folder differs from the Mac manifest: " + "; ".join(diffs[:6]))
            work = os.path.join(ram_workdir(), "models", self.job["id"])
            if os.path.exists(work):
                prev = os.path.join(ram_workdir(), "models", ".previous", f"{self.job['id']}-{int(t0)}")
                os.makedirs(os.path.dirname(prev), exist_ok=True)
                shutil.move(work, prev)
            for rel in manifest.iter_case_files(src):
                d = os.path.join(work, rel)
                os.makedirs(os.path.dirname(d), exist_ok=True)
                shutil.copy2(os.path.join(src, rel), d)
            if not self.arbiter.try_acquire(self.owner):
                raise RuntimeError("GPU is held by another task")
            cache = os.path.join(ram_workdir(), "cache")
            env = {k: v for k, v in os.environ.items() if k not in _SECRET_VARS}
            env.update({
                "PYTHONDONTWRITEBYTECODE": "1", "G4_RETENTION": RETENTION,
                "HF_HOME": os.path.join(cache, "hf"), "TORCH_HOME": os.path.join(cache, "torch"),
                "XDG_CACHE_HOME": cache, "PIP_CACHE_DIR": os.path.join(cache, "pip"),
                "MPLCONFIGDIR": os.path.join(cache, "mpl"), "TMPDIR": os.path.join(work, ".tmp"),
            })
            os.makedirs(env["TMPDIR"], exist_ok=True)
            if self.cpus:
                env["OMP_NUM_THREADS"] = env["MKL_NUM_THREADS"] = str(len(self.cpus))
                env["G4_MODEL_CPUS"] = ",".join(str(c) for c in self.cpus)
            cmd = limited([sys.executable, "-B", m["script"]] + list(m.get("args", [])), self.cpus, nice=5)
            self.report["integrity"] = {"root": actual["root"], "files": actual["count"], "identical": True}
            self.report["status"] = "running"
            say(f"[{self.job['id']}] mô hình chạy trên GPU, CPU {env.get('G4_MODEL_CPUS', 'tất cả')}", "ok")
            sampler = UtilSampler(interval=5.0, gpu=True)
            sampler.start()
            jid = self.job["id"]

            def on_line(line: str) -> None:
                say(f"[{jid}] {line}", "info")

            st = Stream(cmd, work, env, on_line, ring=200)
            limit = min(self.deadline, t0 + float(self.job.get("max_hours", 23.0)) * 3600.0)
            rc = st.run(should_stop=lambda: time.time() > limit - 60, on_stop=st.terminate, grace=30)
            self.report["util"] = sampler.stop()
            self.report["exit_code"] = rc
            self.report["status"] = "completed" if rc == 0 else ("stopped_at_deadline" if time.time() > limit - 61 else "failed")
            if rc != 0:
                say_tail(st, 20)
        except Exception as exc:
            self.report["status"] = "refused" if isinstance(exc, PermissionError) else "failed"
            self.report["error"] = f"{type(exc).__name__}: {exc}"
            say(f"[{self.job['id']}] {self.report['status']}: {exc}", "err")
        finally:
            self.arbiter.release(self.owner)
            self.report["seconds"] = round(time.time() - t0, 1)
            u = self.report.get("util", {})
            say(f"[{self.job['id']}] mô hình {self.report['status']} sau {fmt_duration(self.report['seconds'])}"
                + (f" · GPU {u.get('gpu_util_mean')}%" if u.get("gpu_util_mean") is not None else ""),
                "ok" if self.report["status"] == "completed" else "warn")
