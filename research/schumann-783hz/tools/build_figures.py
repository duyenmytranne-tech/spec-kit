#!/usr/bin/env python3
"""Render report/figures/*.svg from results/results.json (deterministic)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sr783.figures import ALL  # noqa: E402


def render() -> dict[str, str]:
    res = json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))
    return {name: fn(res) for name, fn in ALL.items()}


def main() -> int:
    out_dir = ROOT / "report" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    check = "--check" in sys.argv
    bad = []
    for name, svg in render().items():
        path = out_dir / name
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != svg:
                bad.append(name)
        else:
            path.write_text(svg, encoding="utf-8")
            print("wrote", path.relative_to(ROOT), len(svg), "bytes")
    if check:
        print("figures bit-identical:", not bad, bad)
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
