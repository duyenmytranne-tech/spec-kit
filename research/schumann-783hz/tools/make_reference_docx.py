#!/usr/bin/env python3
"""Create report/assets/reference-nd30.docx: a pandoc reference document whose page setup and
styles follow Nghị định 30/2020/NĐ-CP (A4; margins top/bottom 20 mm, left 30 mm, right 15 mm;
Times New Roman 13 pt; line spacing between single and 1.5; paragraph spacing >= 6 pt; page number
centred in the top margin and hidden on the first page).  Requires pandoc and python-docx.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "report" / "assets" / "reference-nd30.docx"
FONT = "Times New Roman"


def set_font(style, size_pt: float, bold: bool | None = None, italic: bool | None = None) -> None:
    style.font.name = FONT
    style.font.size = Pt(size_pt)
    if bold is not None:
        style.font.bold = bold
    if italic is not None:
        style.font.italic = italic
    rpr = style.element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        fonts.attrib.pop(qn(attr), None)          # theme fonts would override the explicit face
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(attr), FONT)
    color = rpr.find(qn("w:color"))
    if color is not None:
        color.set(qn("w:val"), "000000")


def page_field(paragraph) -> None:
    run = paragraph.add_run()
    for tag, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if tag:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), tag)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = text
        run._r.append(el)
    run.font.name = FONT
    run.font.size = Pt(13)


def main() -> int:
    base = subprocess.run(["pandoc", "--print-default-data-file", "reference.docx"],
                          check=True, capture_output=True).stdout
    tmp = OUT.with_suffix(".tmp.docx")
    tmp.write_bytes(base)
    doc = Document(str(tmp))
    for section in doc.sections:
        section.page_width, section.page_height = Mm(210), Mm(297)
        section.top_margin, section.bottom_margin = Mm(20), Mm(20)
        section.left_margin, section.right_margin = Mm(30), Mm(15)
        section.header_distance = Mm(10)
        section.different_first_page_header_footer = True
        hp = section.header.paragraphs[0] if section.header.paragraphs else section.header.add_paragraph()
        hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        page_field(hp)
    styles = {st.name: st for st in doc.styles}
    for name in ("Normal", "Body Text", "First Paragraph", "Compact"):
        if name in styles:
            st = styles[name]
            set_font(st, 13)
            pf = st.paragraph_format
            pf.space_after = Pt(6)
            pf.line_spacing = 1.2
            if name in ("Body Text", "First Paragraph"):
                pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for name, size in (("Title", 16), ("Heading 1", 14), ("Heading 2", 13), ("Heading 3", 13)):
        if name in styles:
            set_font(styles[name], size, bold=True, italic=(name == "Heading 3"))
            styles[name].paragraph_format.space_before = Pt(12)
            styles[name].paragraph_format.space_after = Pt(6)
    for name in ("Image Caption", "Table Caption", "Caption"):
        if name in styles:
            set_font(styles[name], 12, italic=True)
    if "Table" in styles:                           # grid borders (0.5 pt) on every table
        tbl = styles["Table"].element
        tblpr = tbl.find(qn("w:tblPr"))
        if tblpr is None:
            tblpr = OxmlElement("w:tblPr")
            tbl.append(tblpr)
        old = tblpr.find(qn("w:tblBorders"))
        if old is not None:
            tblpr.remove(old)
        borders = OxmlElement("w:tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            e = OxmlElement(f"w:{edge}")
            e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:space"), "0"); e.set(qn("w:color"), "808080")
            borders.append(e)
        tblpr.append(borders)
    for name in ("Source Code", "Verbatim Char"):
        if name in styles:
            styles[name].font.size = Pt(10.5)
    doc.save(str(OUT))
    tmp.unlink()
    print("wrote", OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
