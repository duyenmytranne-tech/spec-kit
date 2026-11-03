#!/usr/bin/env python3
"""Build the SR783 app from app/src/sr783.template.html + kb/kb_vi.json.

Outputs
  app/sr783.html             artifact-ready page body (no doctype/html/head/body tags)
  app/sr783-standalone.html  the same page wrapped as a complete offline HTML document
Usage: python tools/build_app.py [--check]
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "app" / "src" / "sr783.template.html"
KB = ROOT / "kb" / "kb_vi.json"
OUT_FRAGMENT = ROOT / "app" / "sr783.html"
OUT_STANDALONE = ROOT / "app" / "sr783-standalone.html"
PLACEHOLDER = "__KB_JSON__"

WRAP_HEAD = ('<!doctype html>\n<html lang="vi">\n<head>\n<meta charset="utf-8">\n'
             '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
             '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);'
             'padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}img{max-width:100%}'
             '[hidden]{display:none!important}</style>\n</head>\n<body>\n')
WRAP_TAIL = "\n</body>\n</html>\n"


def build() -> tuple[str, str]:
    template = TEMPLATE.read_text(encoding="utf-8")
    kb = KB.read_text(encoding="utf-8")
    if template.count(PLACEHOLDER) != 1:
        raise SystemExit("template must contain the KB placeholder exactly once")
    if "</script" in kb.lower():
        raise SystemExit("knowledge base must not contain </script")
    fragment = template.replace(PLACEHOLDER, kb)
    return fragment, WRAP_HEAD + fragment + WRAP_TAIL


def main() -> int:
    fragment, standalone = build()
    if "--check" in sys.argv:
        ok = (OUT_FRAGMENT.read_text(encoding="utf-8") == fragment
              and OUT_STANDALONE.read_text(encoding="utf-8") == standalone)
        print("app bit-identical:", ok)
        return 0 if ok else 1
    OUT_FRAGMENT.write_text(fragment, encoding="utf-8")
    OUT_STANDALONE.write_text(standalone, encoding="utf-8")
    print("wrote", OUT_FRAGMENT.relative_to(ROOT), len(fragment.encode()), "bytes;",
          OUT_STANDALONE.relative_to(ROOT), len(standalone.encode()), "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
