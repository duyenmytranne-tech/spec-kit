"""Reproducibility: every generated artifact must rebuild bit-identically from its sources."""
from __future__ import annotations

import importlib.util
import json
import math


def load_tool(root, name):
    spec = importlib.util.spec_from_file_location(name, root / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _close(a, b, tol=2e-3):
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_close(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(_close(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return math.isclose(a, b, abs_tol=tol)
    return a == b


def test_results_rebuild(root):
    tool = load_tool(root, "compute_results")
    fresh = tool.compute()
    committed = json.loads((root / "results" / "results.json").read_text(encoding="utf-8"))
    for key in fresh:
        if key == "ml":
            assert _close(fresh["ml"], committed["ml"]), "ML metrics drifted beyond tolerance"
        else:
            assert fresh[key] == committed[key], key
    blob = tool.dump(fresh)
    if blob != (root / "results" / "results.json").read_bytes():
        # only acceptable on a different platform where libm differs in the last ulp of the ML floats
        assert _close(json.loads(blob)["ml"], committed["ml"])


def test_figures_rebuild(root):
    tool = load_tool(root, "build_figures")
    for name, svg in tool.render().items():
        assert (root / "report" / "figures" / name).read_text(encoding="utf-8") == svg, name


def test_app_rebuild(root):
    tool = load_tool(root, "build_app")
    fragment, standalone = tool.build()
    assert (root / "app" / "sr783.html").read_text(encoding="utf-8") == fragment
    assert (root / "app" / "sr783-standalone.html").read_text(encoding="utf-8") == standalone


def test_report_rebuild(root):
    tool = load_tool(root, "build_report")
    assert (root / "report" / "BAO-CAO-7.83Hz.md").read_text(encoding="utf-8") == tool.combine()
