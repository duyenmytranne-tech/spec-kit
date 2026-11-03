#!/usr/bin/env python3
"""Build the report from report/chapters/*.md.

Outputs (in report/):
  BAO-CAO-7.83Hz.md     combined Markdown (rebuild must be bit-identical; checked by tests)
  BAO-CAO-7.83Hz.html   standalone HTML (pandoc; CSS and SVG figures embedded)
  BAO-CAO-7.83Hz.pdf    A4 PDF from the HTML (headless Chromium; Nghị định 30/2020 margins)
  BAO-CAO-7.83Hz.docx   DOCX (pandoc + assets/reference-nd30.docx; PNG figures)
Usage: python tools/build_report.py [--md-only] [--check]
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "report"
CHAPTERS = REPORT / "chapters"
NAME = "BAO-CAO-7.83Hz"
TITLE = "Báo cáo nghiên cứu chuyên sâu tần số 7,83 Hz"
HEADER = ("<!-- Tệp tổng hợp sinh tự động bởi tools/build_report.py từ report/chapters/*.md. "
          "Sửa nội dung ở thư mục chapters/. -->\n\n")
SOURCE_DATE_EPOCH = "1793664000"          # 2026-11-03T00:00:00Z: reproducible DOCX metadata
ANCHOR = re.compile(r'<a id="([A-Za-z0-9-]+)"></a>\n\n(#{1,3} )([^\n]+)')


CROSS_LINK = re.compile(r"\]\(\d\d-[a-z0-9-]+\.md#([A-Za-z0-9-]+)\)")


def combine() -> str:
    """Join chapters; links to another chapter file (`02-...md#c1`) become in-document links (`#c1`)."""
    parts = [p.read_text(encoding="utf-8").strip("\n") for p in sorted(CHAPTERS.glob("*.md"))]
    return CROSS_LINK.sub(r"](#\1)", HEADER + "\n\n".join(parts) + "\n")


def pandoc_source(md: str, png: bool) -> str:
    """Move raw anchors onto headings ({#id}) so internal links work in HTML and DOCX."""
    out = ANCHOR.sub(lambda m: f"{m.group(2)}{m.group(3)} {{#{m.group(1)}}}", md)
    out = out.replace('<a id="top"></a>\n\n', "")
    if png:
        out = re.sub(r"\(figures/([A-Za-z0-9_]+)\.svg\)", r"(figures/png/\1.png)", out)
    return out


def run(cmd: list[str], cwd: Path, env: dict | None = None) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True, env={**os.environ, **(env or {})})


def main() -> int:
    md = combine()
    md_path = REPORT / f"{NAME}.md"
    if "--check" in sys.argv:
        same = md_path.read_text(encoding="utf-8") == md
        print("combined report bit-identical:", same)
        return 0 if same else 1
    md_path.write_text(md, encoding="utf-8")
    print("wrote", md_path.relative_to(ROOT), len(md.encode()), "bytes")
    if "--md-only" in sys.argv:
        return 0
    env = {"SOURCE_DATE_EPOCH": SOURCE_DATE_EPOCH}
    with tempfile.TemporaryDirectory() as tmp:
        src_html = Path(tmp) / "src-html.md"
        src_html.write_text(pandoc_source(md, png=False), encoding="utf-8")
        run(["pandoc", str(src_html), "-f", "markdown-implicit_figures+implicit_figures", "-t", "html5",
             "--standalone", "--embed-resources", "--css", "assets/report.css", "--resource-path", ".",
             "--metadata", f"pagetitle={TITLE}", "--metadata", "lang=vi", "-o", f"{NAME}.html"], REPORT, env)
        html = REPORT / f"{NAME}.html"            # strip trailing blanks (repository CI runs `git diff --check`)
        html.write_text("\n".join(ln.rstrip() for ln in html.read_text(encoding="utf-8").split("\n")), encoding="utf-8")
        print("wrote", f"report/{NAME}.html")
        run(["node", str(ROOT / "tools" / "render.cjs"), "png", str(REPORT / "figures"),
             str(REPORT / "figures" / "png")], ROOT)
        run([sys.executable, str(ROOT / "tools" / "make_reference_docx.py")], ROOT)
        src_docx = Path(tmp) / "src-docx.md"
        src_docx.write_text(pandoc_source(md, png=True), encoding="utf-8")
        run(["pandoc", str(src_docx), "-f", "markdown", "-t", "docx", "--resource-path", ".",
             "--reference-doc", "assets/reference-nd30.docx", "--metadata", "lang=vi-VN",
             "-o", f"{NAME}.docx"], REPORT, env)
        print("wrote", f"report/{NAME}.docx")
    run(["node", str(ROOT / "tools" / "render.cjs"), "pdf", str(REPORT / f"{NAME}.html"),
         str(REPORT / f"{NAME}.pdf")], ROOT)
    print("wrote", f"report/{NAME}.pdf")
    return 0


if __name__ == "__main__":
    sys.exit(main())
