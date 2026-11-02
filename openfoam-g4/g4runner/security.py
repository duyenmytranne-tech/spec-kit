"""Static scan of a case for constructs that execute code outside the solver.

OpenFOAM dictionaries can run code: ``#codeStream``/``#calc`` compile C++ at
read time, ``coded*`` boundary conditions and function objects compile C++,
``systemCall`` runs shell commands, and ``libs`` can load a shared library
from a path inside the case. A case pushed to GitHub is data; on the G4
runtime it must not become a way to run arbitrary programs. Findings of
severity ``block`` stop the job unless the Colab side (not the job file)
sets ``G4_ALLOW_CODED=1``.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List

from .manifest import iter_case_files

_RULES = [
    ("block", re.compile(r"#\s*(codeStream|calc|calcEntry)\b"), "inline C++ compiled while reading dictionaries"),
    ("block", re.compile(r"#\{"), "verbatim C++ block (#{ ... #})"),
    ("block", re.compile(r"\btype\s+coded\w*\s*;"), "coded boundary condition / function object (compiles C++)"),
    ("block", re.compile(r"\btype\s+systemCall\s*;"), "systemCall function object (runs shell commands)"),
    ("block", re.compile(r"#\s*include\s+\"(/|\.\./)"), "#include of a file outside the case"),
]
_LIBS = re.compile(r"\blibs\s*\(([^)]*)\)", re.S)
_LIB_NAME = re.compile(r"\"([^\"]+)\"")


def _is_text(path: str) -> bool:
    try:
        with open(path, "rb") as fh:
            head = fh.read(8192)
    except OSError:
        return False
    return b"\x00" not in head


def scan_case(case_dir: str) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    real_case = os.path.realpath(case_dir)
    for rel in iter_case_files(case_dir):
        path = os.path.join(case_dir, rel)
        if os.path.islink(path):
            target = os.path.realpath(path)
            if not (target == real_case or target.startswith(real_case + os.sep)):
                findings.append({"severity": "block", "file": rel, "why": "symlink points outside the case"})
            continue
        if not _is_text(path):
            sev = "block" if rel.endswith((".so", ".dylib", ".dll")) or os.access(path, os.X_OK) else "note"
            findings.append({"severity": sev, "file": rel, "why": "binary file in case"})
            continue
        if os.access(path, os.X_OK):
            findings.append({"severity": "note", "file": rel, "why": "executable script (the runner never executes case scripts)"})
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        stripped = re.sub(r"//[^\n]*", "", text)
        stripped = re.sub(r"/\*.*?\*/", "", stripped, flags=re.S)
        for sev, rx, why in _RULES:
            m = rx.search(stripped)
            if m:
                findings.append({"severity": sev, "file": rel, "why": f"{why}: '{m.group(0).strip()}'"})
        for block in _LIBS.finditer(stripped):
            for lib in _LIB_NAME.findall(block.group(1)):
                if "/" in lib or "$" in lib or lib.startswith("."):
                    findings.append({"severity": "block", "file": rel, "why": f"libs loads a library by path: {lib}"})
                else:
                    findings.append({"severity": "note", "file": rel, "why": f"libs loads {lib}"})
    return findings


def blocking(findings: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [f for f in findings if f["severity"] == "block"]


def allowed_by_operator() -> bool:
    """Only the Colab operator can allow coded constructs, via the environment."""
    return os.environ.get("G4_ALLOW_CODED", "") == "1"
