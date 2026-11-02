"""The published report and the code must agree cell by cell, and the upgrade must not delete anything."""

import html
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

from g4runner import apps, capacity

HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(HOME, "docs", "OpenFOAM_chi_tiet.html")
SRC = os.path.join(HOME, "docs", "source", "OpenFOAM_chi_tiet_v1.html")
sys.path.insert(0, os.path.join(HOME, "tools"))
import build_report  # noqa: E402


@pytest.fixture(scope="module")
def doc():
    with open(DOC, encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def v1():
    with open(SRC, encoding="utf-8") as fh:
        return fh.read()


def test_committed_report_is_rebuilt_from_code(doc, v1):
    assert build_report.transform(v1) == doc, "run: python3 -I tools/build_report.py"


def test_original_is_preserved_bit_for_bit(v1):
    import hashlib

    assert hashlib.sha256(v1.encode("utf-8")).hexdigest() == "51338aa4bc59b498f7cabe38357824e0f27c2d4883a0d042e0e14951beb5473a"


def _rows(doc):
    mx = doc[doc.index('<table class="mx">'):]
    mx = mx[:mx.index("</table>")]
    out = {}
    for m in re.finditer(r'<tr data-s="(\w+)" data-p="(\w+)"><td><a class="go" href="#(ud\d+)">[^<]+</a></td>(.*?)</tr>', mx, re.S):
        s, p, uid, cells = m.groups()
        cn = re.findall(r'<td class="m">(.*?)</td>', cells, re.S)
        pat = "".join("●" if 'class="dot"' in c else ("○" if "dot aux" in c else "·") for c in cn)
        tts = re.search(r'<td class="tts">(.*?)</td>', cells, re.S).group(1)
        stages = [(x, "aux" in cls) for cls, x in re.findall(r'<a class="(tt(?: aux)?)" href="#tt\d"[^>]*>(TT\d)</a>', tts)]
        prof = re.search(r'<td class="pfc"><span class="pf (\w+)">([^<]+)</span>', cells).groups()
        bn = html.unescape(re.search(r'<td class="bn">(.*?)</td>', cells, re.S).group(1))
        out[uid] = {"s": s, "p": p, "cn": pat, "stages": stages, "pf_label": html.unescape(prof[1]), "bn": bn}
    return out


def test_matrix_matches_registry_cell_by_cell(doc):
    rows = _rows(doc)
    assert list(rows) == [a["id"] for a in apps.APPS]
    for a in apps.APPS:
        r = rows[a["id"]]
        prof = apps.derive_profile(a)
        assert (r["s"], r["p"], r["cn"]) == (a["s"], prof, a["cn"]), a["id"]
        assert r["pf_label"] == apps.PROFILES[prof]
        assert r["bn"] == a["bottleneck"]
        expected = [] if a["s"] == "out" else [("TT0", False)] + [
            (f"TT{i + 1}", c == "○") for i, c in enumerate(a["cn"]) if c != "·"]
        assert r["stages"] == expected, a["id"]


def test_counts_and_filters_stay_consistent(doc):
    claimed = [int(x) for x in re.findall(r"<td>(\d+) / 21</td>", doc)]
    assert claimed == [12, 15, 20, 12, 9, 18, 2, 19]
    assert re.findall(r'data-f="(\w+)" aria-pressed="\w+">[^<]+<i>(\d+)</i>', doc) == [
        ("all", "21"), ("ok", "13"), ("cp", "4"), ("ex", "3"), ("out", "1")]
    prof = dict(re.findall(r'data-g="(\w+)" aria-pressed="\w+">[^<]+<i>(\d+)</i>', doc))
    assert prof.pop("all") == "21"
    assert {k: int(v) for k, v in prof.items()} == {p: sum(apps.derive_profile(a) == p for a in apps.APPS) for p in apps.PROFILES}


def test_cards_carry_the_execution_block(doc):
    for a in apps.APPS:
        m = re.search(r'<article class="app" id="' + a["id"] + r'" data-s="(\w+)" data-p="(\w+)">(.*?)</article>', doc, re.S)
        assert m, a["id"]
        body = m.group(3)
        assert m.group(2) == apps.derive_profile(a)
        assert "<dt>Thực thi trên G4</dt>" in body and body.index("Thực thi trên G4") < body.index("<dt>Ranh giới</dt>")
        if a["tutorial"]:
            assert f"<code>{a['tutorial']}</code>" in body
        if a["template"]:
            assert f"./foamctl submit --template {a['id']}" in body


def test_every_internal_link_resolves(doc):
    ids = re.findall(r'\bid="([^"]+)"', doc)
    assert len(ids) == len(set(ids)), "duplicate ids"
    targets = set(re.findall(r'href="#([^"]+)"', doc))
    missing = sorted(t for t in targets if t not in set(ids))
    assert missing == []
    assert {"thuc-thi", "g4", "song-song-cpu-gpu", "lan-mo-hinh", "may-tinh", "tu-dong", "doi-chieu"} <= set(ids)
    assert {f"tt{k}" for k in range(9)} <= set(ids) and {f"cn{k}" for k in range(1, 9)} <= set(ids)


def _visible_text(page):
    page = re.sub(r"<script\b.*?</script>", " ", page, flags=re.S)
    page = re.sub(r"<style\b.*?</style>", " ", page, flags=re.S)
    chunks = [html.unescape(c) for c in re.split(r"<[^>]+>", page)]
    return [re.sub(r"\s+", " ", c).strip() for c in chunks if c.strip()]


def test_nothing_from_the_original_was_removed(doc, v1):
    new_text = " ␞ ".join(_visible_text(doc))
    lost = [c for c in _visible_text(v1) if c not in new_text]
    assert lost == []


def _js_engine(doc):
    start = doc.index("/* Port of g4runner/capacity.py")
    end = doc.index("(function(){", start)
    return doc[start:end]


CASES = [{}]
for phys in capacity.PHYSICS:
    for cells in (0.05, 3.0, 20.0, 100.0):
        CASES.append({"physics": phys, "cells_m": cells, "iterations": 20000.0})
CASES += [
    {"ami": True, "cells_m": 20.0}, {"ogl_ready": True}, {"ogl_overlap": False}, {"variants": 6, "cells_m": 2.0},
    {"variants": 12, "cells_m": 0.2, "physics": "incompressible_transient"}, {"cells_m": 0.5, "iterations": 100.0},
    {"cores_physical": 4, "ram_gb": 15.0, "c_cell_us": 4.8037, "cpu_bw_gbs": 20.0, "vram_gb": 0.0},
    {"cells_m": 60.0, "variants": 6}, {"cu_per_hour": 10.5, "usd_per_cu": 0.1, "session_hours": 12.0, "iterations": 1e6},
    {"build_slowdown": 0.7, "ogl_build_h": 0.9, "cells_m": 8.0, "iterations": 9000.0},
]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_estimate_matches_python_bit_for_bit(doc, tmp_path):
    js = tmp_path / "engine.js"
    js.write_text(_js_engine(doc) + "\nconst cases = JSON.parse(require('fs').readFileSync(0, 'utf8'));\n"
                  "process.stdout.write(JSON.stringify(cases.map(g4Estimate)));\n")
    out = subprocess.run(["node", str(js)], input=json.dumps(CASES), capture_output=True, text=True, check=True).stdout
    got = json.loads(out, parse_float=str, parse_int=str)
    for inp, j in zip(CASES, got):
        py = capacity.estimate(inp)
        for key, pv in py.items():
            jv = j[key]
            if key == "raw":
                for rk, rv in pv.items():
                    assert float(jv[rk]) == rv and float(jv[rk]).hex() == float(rv).hex(), (inp, rk, jv[rk], rv)
            elif isinstance(pv, bool):
                assert jv is pv, (inp, key)
            elif isinstance(pv, str):
                assert jv == pv
            else:
                assert float(jv) == float(pv), (inp, key, jv, pv)
    assert len(got) == len(CASES) >= 45


def test_acceptance_table_states_the_real_test_count():
    out = subprocess.run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "--collect-only", "-q", os.path.join(HOME, "tests")],
                         capture_output=True, text=True, cwd=HOME, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    m = re.search(r"(\d+) tests? collected", out.stdout)
    assert m, out.stdout[-400:]
    assert int(m.group(1)) == build_report.NTESTS, f"set NTESTS = {m.group(1)} in tools/build_report.py and rebuild"
