"""SHA-256 integrity for the whole research package.

* SHA256SUMS            - `sha256sum`-compatible manifest of every file.
* ROOT_HASH.txt         - SHA-256 of the SHA256SUMS bytes (one value seals all).
* ROOT_HASH.secded.txt  - the 256-bit root split into four 64-bit words, each
                          protected by SECDED(72,64): a flipped bit in the
                          stored root is corrected, two flipped bits are detected.
* hash chain            - tamper-evident log: h_i = SHA256(h_{i-1} + "\\n" + canonical(entry_i)).
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .secded import protect_bytes, recover_bytes

MANIFEST = "SHA256SUMS"
ROOT = "ROOT_HASH.txt"
ROOT_SECDED = "ROOT_HASH.secded.txt"
EXCLUDE_FILES = {MANIFEST, ROOT, ROOT_SECDED}
EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", "node_modules", ".venv"}
GENESIS = "0" * 64


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_files(root: Path) -> list[str]:
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS)
        for name in filenames:
            rel = Path(dirpath, name).relative_to(root).as_posix()
            if rel in EXCLUDE_FILES or name.endswith((".pyc", ".pyo")):
                continue
            out.append(rel)
    return sorted(out)


def build_manifest(root: Path) -> str:
    files = iter_files(root)
    bad = [rel for rel in files if rel.startswith("-") or "\n" in rel or "\\" in rel]
    if bad:  # `sha256sum -c` would read "-" as standard input; refuse ambiguous names
        raise ValueError(f"file names not representable in SHA256SUMS: {bad}")
    return "".join(f"{sha256_file(root / rel)}  {rel}\n" for rel in files)


def seal(root: Path) -> dict:
    root = Path(root)
    manifest = build_manifest(root)
    (root / MANIFEST).write_bytes(manifest.encode("utf-8"))
    digest = hashlib.sha256(manifest.encode("utf-8")).digest()
    (root / ROOT).write_text(digest.hex() + "\n", encoding="utf-8")
    lines = protect_bytes(digest)
    body = ("# SHA-256 root of SHA256SUMS, 4 x SECDED(72,64) codewords (hex, word 0 first)\n"
            + "".join(line + "\n" for line in lines))
    (root / ROOT_SECDED).write_text(body, encoding="utf-8")
    return {"files": manifest.count("\n"), "root": digest.hex(), "secded": lines}


def read_secded(root: Path) -> list[str]:
    text = (Path(root) / ROOT_SECDED).read_text(encoding="utf-8")
    return [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]


def verify(root: Path) -> dict:
    root = Path(root)
    stored = (root / MANIFEST).read_text(encoding="utf-8")
    expected = {}
    for line in stored.splitlines():
        digest, rel = line.split("  ", 1)
        expected[rel] = digest
    actual = {rel: sha256_file(root / rel) for rel in iter_files(root)}
    changed = sorted(r for r in expected if r in actual and actual[r] != expected[r])
    missing = sorted(r for r in expected if r not in actual)
    extra = sorted(r for r in actual if r not in expected)
    root_stored = (root / ROOT).read_text(encoding="utf-8").strip()
    root_manifest = hashlib.sha256(stored.encode("utf-8")).hexdigest()
    rec = recover_bytes(read_secded(root))
    secded_root = rec["bytes"].hex() if rec["ok"] else None
    ok = (not changed and not missing and not extra
          and root_stored == root_manifest and secded_root == root_manifest)
    return {"ok": ok, "files": len(expected), "changed": changed, "missing": missing,
            "extra": extra, "root": root_manifest, "root_file_matches": root_stored == root_manifest,
            "secded_root_matches": secded_root == root_manifest, "secded_report": rec["report"]}


def canonical_json(entry: dict) -> str:
    """Strings and integers only - identical bytes in Python and JavaScript."""
    for v in entry.values():
        if not isinstance(v, (str, int)) or isinstance(v, bool):
            raise TypeError("hash-chain entries hold only strings and integers")
    return json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def chain_next(prev_hex: str, entry: dict) -> str:
    return hashlib.sha256((prev_hex + "\n" + canonical_json(entry)).encode("utf-8")).hexdigest()


def chain(entries: list[dict]) -> list[str]:
    out, prev = [], GENESIS
    for e in entries:
        prev = chain_next(prev, e)
        out.append(prev)
    return out
