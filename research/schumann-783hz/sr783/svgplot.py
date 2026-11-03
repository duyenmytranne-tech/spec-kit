"""Tiny deterministic SVG plotting (no dependencies, byte-stable output).

Design rules follow the dataviz method: thin marks, 2 px lines, rounded
data ends on bars, recessive grid, text in ink colours (never series
colours), legend for >= 2 series plus direct labels, <title> on every mark
for hover read-out, explicit surface so the figure reads on any background.
"""
from __future__ import annotations

import math
from xml.sax.saxutils import escape

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"
CRITICAL = "#d03b3b"
FONT = "Liberation Sans, Arial, Helvetica, DejaVu Sans, sans-serif"


def n2(v: float) -> str:
    s = f"{v:.2f}"
    return "0.00" if s == "-0.00" else s


class Plot:
    def __init__(self, width=760, height=380, title="", subtitle="", left=72, right=24, top=64, bottom=58):
        self.w, self.h = width, height
        self.l, self.r, self.t, self.b = left, right, top, bottom
        self.title, self.subtitle = title, subtitle
        self.items: list[str] = []
        self.overlay: list[str] = []
        self.xlog = self.ylog = False
        self.x0, self.x1, self.y0, self.y1 = 0.0, 1.0, 0.0, 1.0

    # scales ------------------------------------------------------------
    def set_x(self, lo, hi, log=False):
        self.x0, self.x1, self.xlog = lo, hi, log
        return self

    def set_y(self, lo, hi, log=False):
        self.y0, self.y1, self.ylog = lo, hi, log
        return self

    def X(self, v):
        if self.xlog:
            v, lo, hi = math.log10(v), math.log10(self.x0), math.log10(self.x1)
        else:
            lo, hi = self.x0, self.x1
        return self.l + (v - lo) / (hi - lo) * (self.w - self.l - self.r)

    def Y(self, v):
        if self.ylog:
            v, lo, hi = math.log10(v), math.log10(self.y0), math.log10(self.y1)
        else:
            lo, hi = self.y0, self.y1
        return self.h - self.b - (v - lo) / (hi - lo) * (self.h - self.t - self.b)

    # primitives ----------------------------------------------------------
    def text(self, x, y, s, size=12, color=INK2, anchor="start", weight="400", layer=None, halo=False):
        h = f' stroke="{SURFACE}" stroke-width="3" paint-order="stroke"' if halo else ""
        (layer if layer is not None else self.overlay).append(
            f'<text x="{n2(x)}" y="{n2(y)}" font-size="{size}" fill="{color}" text-anchor="{anchor}" '
            f'font-weight="{weight}"{h}>{escape(s)}</text>')

    def _title(self, tip):
        return f"<title>{escape(tip)}</title>" if tip else ""

    def grid_y(self, ticks, fmt=str, label=""):
        for t in ticks:
            y = self.Y(t)
            self.items.append(f'<line x1="{n2(self.l)}" y1="{n2(y)}" x2="{n2(self.w - self.r)}" y2="{n2(y)}" '
                              f'stroke="{GRID}" stroke-width="1"/>')
            self.text(self.l - 8, y + 4, fmt(t), 11, MUTED, "end")
        if label:
            cy = (self.t + self.h - self.b) / 2
            self.overlay.append(f'<text x="16" y="{n2(cy)}" font-size="12" fill="{INK2}" text-anchor="middle" '
                                f'transform="rotate(-90 16 {n2(cy)})">{escape(label)}</text>')

    def axis_x(self, ticks, fmt=str, label=""):
        yb = self.h - self.b
        self.items.append(f'<line x1="{n2(self.l)}" y1="{n2(yb)}" x2="{n2(self.w - self.r)}" y2="{n2(yb)}" '
                          f'stroke="{AXIS}" stroke-width="1"/>')
        for t in ticks:
            x = self.X(t)
            self.items.append(f'<line x1="{n2(x)}" y1="{n2(yb)}" x2="{n2(x)}" y2="{n2(yb + 4)}" stroke="{AXIS}"/>')
            self.text(x, yb + 18, fmt(t), 11, MUTED, "middle")
        if label:
            self.text((self.l + self.w - self.r) / 2, self.h - 12, label, 12, INK2, "middle")

    def line(self, xs, ys, color, width=2, dash=None, tip=None):
        pts = " ".join(f"{n2(self.X(x))},{n2(self.Y(y))}" for x, y in zip(xs, ys))
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.items.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{width}" '
                          f'stroke-linejoin="round" stroke-linecap="round"{d}>{self._title(tip)}</polyline>')

    def dots(self, xs, ys, color, r=4, tips=None, ring=True):
        for i, (x, y) in enumerate(zip(xs, ys)):
            tip = tips[i] if tips else None
            ring_s = f' stroke="{SURFACE}" stroke-width="2"' if ring else ""
            self.items.append(f'<circle cx="{n2(self.X(x))}" cy="{n2(self.Y(y))}" r="{r}" fill="{color}"{ring_s}>'
                              f'{self._title(tip)}</circle>')

    def stems(self, xs, ys, color, base, tips=None):
        for i, (x, y) in enumerate(zip(xs, ys)):
            tip = tips[i] if tips else None
            self.items.append(f'<line x1="{n2(self.X(x))}" y1="{n2(self.Y(base))}" x2="{n2(self.X(x))}" '
                              f'y2="{n2(self.Y(y))}" stroke="{color}" stroke-width="2"/>')
            self.items.append(f'<circle cx="{n2(self.X(x))}" cy="{n2(self.Y(y))}" r="4" fill="{color}" '
                              f'stroke="{SURFACE}" stroke-width="2">{self._title(tip)}</circle>')

    def bar(self, xc, width_px, y, color, base=0.0, tip=None, radius=4):
        """Vertical bar with a rounded data end anchored to the baseline."""
        x = self.X(xc) - width_px / 2
        yt, yb = self.Y(y), self.Y(base)
        hgt = max(0.0, yb - yt)
        r = min(radius, width_px / 2, hgt)
        path = (f"M{n2(x)},{n2(yb)} V{n2(yt + r)} Q{n2(x)},{n2(yt)} {n2(x + r)},{n2(yt)} "
                f"H{n2(x + width_px - r)} Q{n2(x + width_px)},{n2(yt)} {n2(x + width_px)},{n2(yt + r)} "
                f"V{n2(yb)} Z")
        self.items.append(f'<path d="{path}" fill="{color}">{self._title(tip)}</path>')

    def vline(self, x, color=MUTED, dash="4 4", label=None, label_y=None, width=1.5):
        xx = self.X(x)
        self.items.append(f'<line x1="{n2(xx)}" y1="{n2(self.t)}" x2="{n2(xx)}" y2="{n2(self.h - self.b)}" '
                          f'stroke="{color}" stroke-width="{width}" stroke-dasharray="{dash}"/>')
        if label:
            self.text(xx + 4, label_y if label_y is not None else self.t + 12, label, 11, INK2, halo=True)

    def legend(self, entries, x=None, y=None):
        """entries: (label, color, kind) with kind in line|dot|bar|dash."""
        x = self.l if x is None else x
        y = self.t - 16 if y is None else y
        cx = x
        for label, color, kind in entries:
            if kind == "line":
                self.overlay.append(f'<line x1="{n2(cx)}" y1="{n2(y - 4)}" x2="{n2(cx + 18)}" y2="{n2(y - 4)}" '
                                    f'stroke="{color}" stroke-width="2"/>')
            elif kind == "dash":
                self.overlay.append(f'<line x1="{n2(cx)}" y1="{n2(y - 4)}" x2="{n2(cx + 18)}" y2="{n2(y - 4)}" '
                                    f'stroke="{color}" stroke-width="1.5" stroke-dasharray="4 3"/>')
            elif kind == "dot":
                self.overlay.append(f'<circle cx="{n2(cx + 9)}" cy="{n2(y - 4)}" r="4" fill="{color}"/>')
            else:
                self.overlay.append(f'<rect x="{n2(cx + 2)}" y="{n2(y - 10)}" width="14" height="12" rx="2" '
                                    f'fill="{color}"/>')
            self.text(cx + 24, y, label, 12, INK2)
            cx += 34 + 6.6 * len(label)

    def raw(self, s: str):
        self.items.append(s)

    def svg(self, desc: str = "") -> str:
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" '
                f'height="{self.h}" font-family="{FONT}" role="img" aria-label="{escape(self.title)}">')
        parts = [head, f"<title>{escape(self.title)}</title>"]
        if desc:
            parts.append(f"<desc>{escape(desc)}</desc>")
        parts.append(f'<rect x="0" y="0" width="{self.w}" height="{self.h}" fill="{SURFACE}"/>')
        parts.append(f'<text x="{self.l}" y="22" font-size="15" font-weight="700" fill="{INK}">{escape(self.title)}</text>')
        if self.subtitle:
            parts.append(f'<text x="{self.l}" y="40" font-size="12" fill="{INK2}">{escape(self.subtitle)}</text>')
        parts.extend(self.items)
        parts.extend(self.overlay)
        parts.append("</svg>")
        return "\n".join(parts) + "\n"
