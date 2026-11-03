"""SHA-256 vectors, hash chain, and the package seal (manifest + root + SECDED root)."""
from __future__ import annotations

import hashlib
import shutil
import subprocess

import pytest

from sr783 import integrity


def test_nist_vectors(results):
    assert hashlib.sha256(b"abc").hexdigest() == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert hashlib.sha256(b"").hexdigest() == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert results["integrity"]["sha256_abc"].startswith("ba7816bf")


def test_hash_chain(results):
    entries = results["integrity"]["chain_entries"]
    assert integrity.chain(entries) == results["integrity"]["chain_hashes"]
    tampered = [dict(entries[0], mode="B")] + entries[1:]
    assert integrity.chain(tampered)[-1] != results["integrity"]["chain_hashes"][-1]


def test_seal_verify_and_tamper(tmp_path, root):
    pkg = tmp_path / "pkg"
    shutil.copytree(root / "sr783", pkg / "sr783", ignore=shutil.ignore_patterns("__pycache__"))
    (pkg / "data.txt").write_text("7,83 Hz\n", encoding="utf-8")
    res = integrity.seal(pkg)
    assert res["files"] >= 2
    assert integrity.verify(pkg)["ok"]
    # one flipped bit in the stored SECDED root is corrected
    lines = integrity.read_secded(pkg)
    lines[1] = format(int(lines[1], 16) ^ (1 << 17), "018X")
    (pkg / integrity.ROOT_SECDED).write_text("#\n" + "\n".join(lines) + "\n", encoding="utf-8")
    v = integrity.verify(pkg)
    assert v["ok"] and any(r["status"] == "corrected" for r in v["secded_report"])
    # a changed payload byte is detected
    (pkg / "data.txt").write_text("7,84 Hz\n", encoding="utf-8")
    v = integrity.verify(pkg)
    assert not v["ok"] and v["changed"] == ["data.txt"]


def test_committed_seal_if_present(root):
    if not (root / integrity.MANIFEST).exists():
        return
    v = integrity.verify(root)
    assert v["ok"], {k: v[k] for k in ("changed", "missing", "extra")}


def test_manifest_compatible_with_sha256sum(root):
    """The seal must also verify with the operating system's own tool (independent implementation)."""
    if not (root / integrity.MANIFEST).exists() or shutil.which("sha256sum") is None:
        pytest.skip("no seal or no sha256sum")
    names = [ln.split("  ", 1)[1] for ln in (root / integrity.MANIFEST).read_text(encoding="utf-8").splitlines()]
    assert not [n for n in names if n.startswith("-")]
    subprocess.run(["sha256sum", "-c", "--quiet", integrity.MANIFEST], cwd=root, check=True)
