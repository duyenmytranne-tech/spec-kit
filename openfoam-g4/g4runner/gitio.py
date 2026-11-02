"""Git transport: the Mac pushes code and jobs; the G4 runtime only reads.

The access token lives in an environment variable for the life of the
process. A small askpass script (which contains no secret) hands it to git,
and ``credential.helper`` is disabled, so nothing about it reaches a disk.
"""

from __future__ import annotations

import os
import stat
from typing import Dict, List, Optional

from .util import ram_workdir, retry, run_capture, say

_ASKPASS = """#!/bin/sh
case "$1" in
  *[Uu]sername*) printf '%s\\n' "${G4_GIT_USER:-x-access-token}" ;;
  *) printf '%s\\n' "$G4_GIT_TOKEN" ;;
esac
"""


def git_env(token_var: str = "G4_GIT_TOKEN") -> Dict[str, str]:
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    if env.get(token_var):
        helper = os.path.join(ram_workdir(), "askpass.sh")
        with open(helper, "w", encoding="utf-8") as fh:
            fh.write(_ASKPASS)
        os.chmod(helper, stat.S_IRWXU)
        env["GIT_ASKPASS"] = helper
    return env


def _git(args: List[str], cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None, timeout: float = 600) -> str:
    rc, out, err = run_capture(["git", "-c", "credential.helper="] + args, cwd=cwd, env=env, timeout=timeout)
    if rc != 0:
        raise RuntimeError(f"git {' '.join(args[:2])}: {(err or out).strip()[-300:]}")
    return out.strip()


def clone_readonly(repo: str, branch: str, dest: str) -> str:
    """Shallow clone into RAM. ``repo`` is ``owner/name`` or a full URL."""
    url = repo if "://" in repo or repo.startswith("/") or repo.startswith("file:") else f"https://github.com/{repo}.git"
    env = git_env()
    if os.path.isdir(os.path.join(dest, ".git")):
        return update_readonly(dest, branch)
    retry(lambda: _git(["clone", "--depth", "1", "--single-branch", "--branch", branch, url, dest], env=env),
          what="git clone")
    return _git(["rev-parse", "HEAD"], cwd=dest)


def update_readonly(dest: str, branch: str) -> str:
    """Fetch the branch tip and check it out detached; returns the commit."""
    env = git_env()
    retry(lambda: _git(["fetch", "--depth", "1", "origin", branch], cwd=dest, env=env), what="git fetch")
    sha = _git(["rev-parse", "FETCH_HEAD"], cwd=dest)
    _git(["checkout", "--quiet", "--detach", sha], cwd=dest, env=env)
    return sha


def repo_root(path: str) -> Optional[str]:
    rc, out, _ = run_capture(["git", "rev-parse", "--show-toplevel"], cwd=path, timeout=30)
    return out.strip() if rc == 0 else None


def current_branch(path: str) -> Optional[str]:
    rc, out, _ = run_capture(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=path, timeout=30)
    return out.strip() if rc == 0 else None


def commit_and_push(cwd: str, paths: List[str], message: str, branch: Optional[str] = None,
                    sleep=None) -> str:
    """Mac side: stage only ``paths``, commit, push with 2/4/8/16 s backoff."""
    _git(["add", "--"] + paths, cwd=cwd)
    rc, out, err = run_capture(["git", "diff", "--cached", "--quiet"], cwd=cwd, timeout=60)
    if rc != 0:
        _git(["commit", "--quiet", "-m", message], cwd=cwd)
    else:
        say("nothing new to commit; pushing the current commit", "info")
    branch = branch or current_branch(cwd) or "main"
    kwargs = {"sleep": sleep} if sleep else {}

    def push() -> str:
        return _git(["push", "-u", "origin", branch], cwd=cwd, env=git_env(), timeout=900)

    retry(push, what="git push", **kwargs)
    return _git(["rev-parse", "HEAD"], cwd=cwd)
