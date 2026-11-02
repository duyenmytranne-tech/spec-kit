"""SHA-256 manifest of an OpenFOAM case: proves the bytes on Colab are the bytes on the Mac.

The same function runs on both machines, so the comparison is exact to the bit.
Results and machine-generated files (processor*, postProcessing, time
directories other than 0, logs, macOS metadata) are excluded so that a
case directory that has been run locally still hashes like a clean one.
"""

from __future__ import annotations

import hashlib
import os
import re
from typing import Dict, List, Tuple

ALGO = "sha256"

_EXCLUDED_DIRS = {"postProcessing", "VTK", "dynamicCode", ".g4", "__pycache__", ".git", ".svn"}
_PROCESSOR_DIR = re.compile(r"^processors?\d*(_\d+)?$")
_EXCLUDED_FILE = re.compile(r"^(\.DS_Store|\._.*|log\..*|.*\.foam|.*\.OpenFOAM|.*\.pyc|.*~|\..*\.swp|Thumbs\.db)$")
_NUMBER = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")


def _is_result_time_dir(name: str) -> bool:
    """Numeric top-level directories except ``0`` hold solver output."""
    if not _NUMBER.match(name):
        return False
    try:
        return float(name) != 0.0
    except ValueError:
        return False


def iter_case_files(case_dir: str) -> List[str]:
    """Return sorted POSIX-style relative paths of the files that define the case."""
    out: List[str] = []
    case_dir = os.path.abspath(case_dir)
    for dirpath, dirnames, filenames in os.walk(case_dir, followlinks=False):
        rel_dir = os.path.relpath(dirpath, case_dir)
        top = rel_dir == "."
        keep = []
        for d in sorted(dirnames):
            if d in _EXCLUDED_DIRS or _PROCESSOR_DIR.match(d):
                continue
            if top and _is_result_time_dir(d):
                continue
            keep.append(d)
        dirnames[:] = keep
        for f in sorted(filenames):
            if _EXCLUDED_FILE.match(f):
                continue
            rel = f if top else os.path.join(rel_dir, f)
            out.append(rel.replace(os.sep, "/"))
    out.sort()
    return out


def file_digest(path: str) -> Tuple[int, str]:
    """Size and SHA-256 of a file's raw bytes (symlinks hashed by their target text)."""
    h = hashlib.sha256()
    if os.path.islink(path):
        target = os.readlink(path).encode("utf-8")
        h.update(b"symlink:" + target)
        return len(target), h.hexdigest()
    size = 0
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            size += len(chunk)
            h.update(chunk)
    return size, h.hexdigest()


def root_hash(files: List[List]) -> str:
    """Hash of the sorted ``sha size path`` lines: one value for the whole case."""
    h = hashlib.sha256()
    for path, size, sha in sorted(files, key=lambda r: r[0]):
        h.update(f"{sha} {size} {path}\n".encode())
    return h.hexdigest()


def build_manifest(case_dir: str) -> Dict:
    files: List[List] = []
    total = 0
    for rel in iter_case_files(case_dir):
        size, sha = file_digest(os.path.join(case_dir, rel))
        files.append([rel, size, sha])
        total += size
    return {"algo": ALGO, "count": len(files), "bytes": total, "root": root_hash(files), "files": files}


def compare(expected: Dict, actual: Dict) -> List[str]:
    """Human-readable differences; an empty list means identical to the bit."""
    if expected.get("algo") != ALGO:
        return [f"unsupported manifest algorithm {expected.get('algo')!r}"]
    exp = {p: (s, h) for p, s, h in expected.get("files", [])}
    act = {p: (s, h) for p, s, h in actual.get("files", [])}
    diffs: List[str] = []
    for p in sorted(set(exp) - set(act)):
        diffs.append(f"missing: {p}")
    for p in sorted(set(act) - set(exp)):
        diffs.append(f"unexpected: {p}")
    for p in sorted(set(exp) & set(act)):
        if exp[p] != act[p]:
            diffs.append(f"changed: {p} (size {exp[p][0]}→{act[p][0]})")
    if not diffs and expected.get("root") != actual.get("root"):
        diffs.append("root hash differs")
    return diffs


def verify(case_dir: str, expected: Dict) -> Tuple[bool, List[str], Dict]:
    actual = build_manifest(case_dir)
    diffs = compare(expected, actual)
    return (not diffs), diffs, actual
