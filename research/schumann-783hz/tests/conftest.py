"""Shared fixtures for the SR783 research-package test suite (run: python -m pytest tests)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def results() -> dict:
    return json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def kb() -> dict:
    return json.loads((ROOT / "kb" / "kb_vi.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def report_text() -> str:
    return (ROOT / "report" / "BAO-CAO-7.83Hz.md").read_text(encoding="utf-8")


def vn(text: str) -> str:
    """Python/JSON decimal point -> Vietnamese decimal comma (as written in the report)."""
    return str(text).replace(".", ",")
