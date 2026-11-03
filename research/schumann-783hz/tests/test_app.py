"""Static checks of the SR783 app (artifact page contract, offline, KB embedding, safety)."""
from __future__ import annotations

import json
import re


def test_artifact_fragment_contract(root):
    page = (root / "app" / "sr783.html").read_text(encoding="utf-8")
    head = page[:8192]
    assert "<title>Trợ lý SR783</title>" in head
    assert '<meta name="claude:viewport-fit-sides" content="cover">' in head
    for tag in ("<!doctype", "<html", "<head>", "<body"):
        assert tag not in page.lower()
    assert "padding-left: max(16px, env(safe-area-inset-left, 0px))" in page
    assert "padding-right: max(16px, env(safe-area-inset-right, 0px))" in page
    assert '@media (prefers-color-scheme: dark) { :root:not([data-theme="light"])' in page
    assert ':root[data-theme="dark"]' in page
    assert len(page.encode()) < 1_000_000


def test_offline_no_external_runtime_dependencies(root):
    page = (root / "app" / "sr783.html").read_text(encoding="utf-8")
    hosts = set(re.findall(r"https?://([a-z0-9.-]+)", page))
    assert hosts <= {"fonts.googleapis.com", "www.w3.org"}, hosts
    assert "eval(" not in page and "new Function" not in page
    assert "alert(" not in page and "confirm(" not in page and "prompt(" not in page


def test_kb_embedded_verbatim(root):
    page = (root / "app" / "sr783.html").read_text(encoding="utf-8")
    kb = (root / "kb" / "kb_vi.json").read_text(encoding="utf-8")
    m = re.search(r'<script type="application/json" id="sr783-kb">(.*?)</script>', page, flags=re.S)
    assert m and m.group(1) == kb
    json.loads(kb)


def test_safety_terms_and_benchmark_coverage(root, kb):
    assert "115" in kb["safety"]["crisis_reply"]
    bench = json.loads((root / "acceptance" / "benchmark_vi.json").read_text(encoding="utf-8"))
    ids = {i["id"] for i in kb["intents"]}
    assert len(bench["questions"]) >= 40
    assert {exp for _, exp in bench["questions"]} <= ids
    assert len(ids) == len(kb["intents"])


def test_no_flashing_constructs(root):
    page = (root / "app" / "src" / "sr783.template.html").read_text(encoding="utf-8")
    # the only CSS animation is the 10 s breathing pacer (0.1 Hz); nothing animates opacity or brightness
    assert re.findall(r"animation:\s*([a-z-]+)\s+([0-9.]+)s", page) == [("breathe", "10")]
    assert "opacity" not in re.sub(r"button:disabled \{ opacity: \.55;", "", page)
    assert "prefers-reduced-motion" in page
