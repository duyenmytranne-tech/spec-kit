"""Report figures, generated from results.json only (deterministic SVG)."""
from __future__ import annotations

import math
from xml.sax.saxutils import escape

from .svgplot import AXIS, CRITICAL, FONT, GRID, INK, INK2, MUTED, S1, S2, S3, SURFACE, Plot, n2


def vn(v: float, d: int = 2) -> str:
    """Vietnamese decimal comma."""
    return f"{v:.{d}f}".replace(".", ",")


SUP = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


def sci_vn(text: str, sig: int = 3) -> str:
    """'-7.62939e-8' -> '−7,63·10⁻⁸' (Vietnamese decimal comma, superscript exponent)."""
    mant, exp = f"{float(text):.{sig - 1}e}".split("e")
    mant = mant.replace("-", "−").replace(".", ",")
    e = int(exp)
    return mant if e == 0 else f"{mant}·10{str(e).translate(SUP)}"


def tesla_vn(b: float) -> str:
    from .physics import fmt_tesla
    return fmt_tesla(b).replace(".", ",")


# Figure 1 ------------------------------------------------------------------
def fig_sr_spectrum(res: dict) -> str:
    modes = [float(r["observed_hz"]) for r in res["physics"]["cavity"]["rows"]]
    ideal = [float(r["ideal_hz"]) for r in res["physics"]["cavity"]["rows"]]
    amps = [1.0, 0.75, 0.55, 0.40, 0.30]
    hws = [0.9, 1.1, 1.3, 1.5, 1.7]
    xs = [3 + 0.1 * i for i in range(371)]
    ys = [0.08 + sum(a / (1 + ((x - m) / h) ** 2) for a, m, h in zip(amps, modes, hws)) for x in xs]
    p = Plot(760, 380, "Hình 1. Phổ cộng hưởng Schumann minh họa và tần số khoang lý tưởng",
             "Mode quan sát thấp hơn mô hình khoang không tổn hao vì tầng điện ly dẫn điện hữu hạn")
    p.set_x(3, 40).set_y(0, 1.2)
    p.grid_y([0, 0.3, 0.6, 0.9, 1.2], lambda t: vn(t, 1), "Mật độ phổ tương đối")
    p.axis_x([5, 10, 15, 20, 25, 30, 35, 40], lambda t: str(t), "Tần số (Hz)")
    for i, f in enumerate(ideal[:4]):
        p.vline(f, MUTED, "4 4", f"lý tưởng {vn(f)}", p.t + 12 + 14 * (i % 2))
    p.line(xs, ys, S1, 2, tip="Phổ minh họa: tổng 5 hàm Lorentz")
    for i, m in enumerate(modes):
        peak = 0.08 + sum(a / (1 + ((m - mm) / h) ** 2) for a, mm, h in zip(amps, modes, hws))
        p.dots([m], [peak], S1, 4, [f"Mode {i + 1}: {vn(m)} Hz"])
        p.text(p.X(m), p.Y(peak) - 10, f"n={i + 1}: {vn(m)} Hz", 11, INK, "middle", "700" if i == 0 else "400", halo=True)
    p.legend([("Phổ minh họa (tổng Lorentz)", S1, "line"), ("Tần số khoang lý tưởng", MUTED, "dash")],
             x=p.l + 300, y=56)
    return p.svg("Đường phổ minh họa với năm đỉnh tại 7,83; 14,3; 20,8; 27,3; 33,8 Hz và các đường đứt "
                 "tại tần số khoang lý tưởng 10,59; 18,34; 25,94; 33,49 Hz.")


# Figure 2 ------------------------------------------------------------------
SHORT = {"home50": "Từ trường 50 Hz trong nhà (TB châu Âu)", "icnirp": "Mức tham chiếu ICNIRP ở 7,83 Hz",
         "lsb": "1 LSB từ kế điện thoại (AK09918)"}


def fig_field_ladder(res: dict) -> str:
    rows = res["physics"]["field_ladder"]
    order = ["sr", "gen_1m", "gen_10cm", "home50", "lsb", "earth", "icnirp"]
    lookup = {r["key"]: r for r in rows}
    p = Plot(760, 400, "Hình 2. Thang độ lớn từ trường liên quan tới 7,83 Hz (thang log)",
             "Cộng hưởng tự nhiên nhỏ hơn mức tham chiếu ICNIRP khoảng 6,5·10⁸ lần", left=300, right=30)
    p.set_x(1e-13, 1e-2, log=True).set_y(-0.5, len(order) - 0.5)
    ticks = [1e-12, 1e-9, 1e-6, 1e-3]
    names = {1e-12: "1 pT", 1e-9: "1 nT", 1e-6: "1 µT", 1e-3: "1 mT"}
    for t in ticks:
        x = p.X(t)
        p.raw(f'<line x1="{n2(x)}" y1="{n2(p.t)}" x2="{n2(x)}" y2="{n2(p.h - p.b)}" stroke="{GRID}"/>')
    p.axis_x(ticks, lambda t: names[t], "Mật độ từ thông B (tesla, thang logarit)")
    for i, key in enumerate(order):
        yv = len(order) - 1 - i
        y = p.Y(yv)
        if key == "earth":
            lo, hi = lookup["earth_lo"]["tesla"], lookup["earth_hi"]["tesla"]
            p.raw(f'<line x1="{n2(p.X(lo))}" y1="{n2(y)}" x2="{n2(p.X(hi))}" y2="{n2(y)}" stroke="{S1}" '
                  f'stroke-width="6" stroke-linecap="round"><title>Từ trường tĩnh Trái Đất 25–65 µT</title></line>')
            p.text(p.l - 10, y + 4, "Từ trường tĩnh Trái Đất", 12, INK2, "end")
            p.text(p.X(hi) + 10, y + 4, "25–65 µT", 11, INK)
            continue
        r = lookup[key]
        b = r["tesla"]
        label = r["label"]
        p.dots([b], [yv], CRITICAL if key == "icnirp" else S1, 6 if key == "sr" else 5, [f"{label}: {b:.3g} T"])
        p.text(p.l - 10, y + 4, SHORT.get(key, label), 12, INK2, "end")
        p.text(p.X(b) + 10, y + 4, tesla_vn(b), 11, INK, "start", "700" if key in ("sr", "icnirp") else "400")
    return p.svg("Biểu đồ chấm trên thang log: Schumann 1 pT; máy phát mẫu 62,8 pT ở 1 m và 61,9 nT ở 10 cm; "
                 "50 Hz trong nhà 0,07 µT; 1 LSB từ kế điện thoại 0,15 µT; Trái Đất 25–65 µT; ICNIRP 652 µT.")


# Figure 3 ------------------------------------------------------------------
def fig_ieee754(res: dict) -> str:
    ie = res["bits"]["ieee754"]
    w, h = 760, 330
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
           f'font-family="{FONT}" role="img" aria-label="Bản đồ bit IEEE 754 của 7,83">',
           "<title>Hình 3. Bản đồ bit IEEE 754 của 7,83</title>",
           f'<rect width="{w}" height="{h}" fill="{SURFACE}"/>',
           f'<text x="24" y="24" font-size="15" font-weight="700" fill="{INK}">Hình 3. Bản đồ bit IEEE 754 của số 7,83</text>',
           f'<text x="24" y="42" font-size="12" fill="{INK2}">7,83 không biểu diễn đúng trong nhị phân; '
           f'giá trị lưu là số gần nhất (làm tròn về chẵn)</text>']
    colors = {"s": S2, "e": S1, "m": S3}
    y = 70
    for fmt, cell, size in (("binary16", 26, 12), ("binary32", 22, 11), ("binary64", 10.9, 7.5)):
        d = ie[fmt]
        bits = d["bits"]
        ne = len(d["exponent"])
        out.append(f'<text x="24" y="{y - 6}" font-size="12" font-weight="700" fill="{INK}">{fmt} · {d["hex"]} '
                   f'· giá trị lưu {escape(d["exact_value"][:24])}{"…" if len(d["exact_value"]) > 24 else ""}</text>')
        for i, b in enumerate(bits):
            kind = "s" if i == 0 else ("e" if i <= ne else "m")
            x = 24 + i * cell
            out.append(f'<rect x="{n2(x)}" y="{y}" width="{n2(cell - 2)}" height="22" rx="2" fill="{colors[kind]}" '
                       f'fill-opacity="0.16" stroke="{colors[kind]}" stroke-width="1"><title>{fmt} bit {len(bits) - 1 - i}: {b}</title></rect>')
            out.append(f'<text x="{n2(x + (cell - 2) / 2)}" y="{y + 15}" font-size="{size}" fill="{INK}" '
                       f'text-anchor="middle">{b}</text>')
        y += 74
    lx = 24
    for label, kind in (("dấu (sign)", "s"), ("số mũ có độ lệch (exponent)", "e"), ("phần định trị (fraction)", "m")):
        out.append(f'<rect x="{lx}" y="{y - 16}" width="14" height="12" rx="2" fill="{colors[kind]}" fill-opacity="0.16" '
                   f'stroke="{colors[kind]}"/>')
        out.append(f'<text x="{lx + 20}" y="{y - 6}" font-size="12" fill="{INK2}">{label}</text>')
        lx += 40 + 7 * len(label)
    b32 = ie["binary32"]
    out.append(f'<text x="24" y="{y + 18}" font-size="12" fill="{INK2}">binary32: số mũ {b32["exponent"]}₂ = '
               f'{int(b32["exponent"], 2)} → 2^({int(b32["exponent"], 2)}−127) = 2^{b32["exponent_unbiased"]}; '
               f'sai số {sci_vn(b32["abs_error"])} (≈ {sci_vn(b32["rel_error_ppb"])} ppb)</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


# Figure 4 ------------------------------------------------------------------
def fig_dds_error(res: dict) -> str:
    curves = res["synth"]["dds_curves"]
    p = Plot(760, 380, "Hình 4. Sai số tần số DDS theo độ rộng bộ tích lũy pha",
             "Tần số mục tiêu 7,83 Hz; đường đứt = dung sai thạch anh 20 ppm")
    p.set_x(12, 48).set_y(1e-13, 1, log=True)
    p.grid_y([1e-12, 1e-9, 1e-6, 1e-3, 1], lambda t: {1e-12: "10⁻¹²", 1e-9: "10⁻⁹", 1e-6: "10⁻⁶", 1e-3: "10⁻³", 1: "1"}[t],
             "Sai số tương đối |Δf|/f")
    p.axis_x([12, 16, 20, 24, 28, 32, 36, 40, 44, 48], str, "Số bit của bộ tích lũy pha N")
    yy = p.Y(20e-6)
    p.raw(f'<line x1="{n2(p.l)}" y1="{n2(yy)}" x2="{n2(p.w - p.r)}" y2="{n2(yy)}" stroke="{MUTED}" stroke-dasharray="4 4"/>')
    p.text(p.w - p.r - 4, yy - 6, "20 ppm (thạch anh)", 11, INK2, "end")
    for key, color, label in (("48000", S1, "f_clk = 48 kHz (âm thanh)"), ("16000000", S2, "f_clk = 16 MHz (vi điều khiển)")):
        pts = [(r["bits"], max(r["abs_rel_error"], 1e-13)) for r in curves[key]]
        p.line([a for a, _ in pts], [b for _, b in pts], color, 2)
        p.dots([a for a, _ in pts], [b for _, b in pts], color, 3.5,
               [f"{label}, N={a}: {b:.3g}" for a, b in pts])
    p.legend([("f_clk = 48 kHz (âm thanh)", S1, "line"), ("f_clk = 16 MHz (vi điều khiển)", S2, "line")], y=56)
    first = {k: next(r["bits"] for r in curves[k] if r["abs_rel_error"] < 20e-6) for k in curves}
    return p.svg(f"Hai đường giảm dần theo N; sai số nhỏ hơn 20 ppm từ N = {first['48000']} (48 kHz) "
                 f"và N = {first['16000000']} (16 MHz).")


# Figure 5 ------------------------------------------------------------------
def fig_display(res: dict) -> str:
    codes = res["synth"]["display"]["sampled_sinusoid_60hz_u8"]
    f = 7.83
    p = Plot(760, 360, "Hình 5. Kích thích hình sin lấy mẫu 7,83 Hz trên màn hình 60 Hz",
             "Mỗi khung 16,67 ms nhận một mã độ sáng 8 bit; 7,6628 khung/chu kỳ nên không thể bật/tắt nguyên khung")
    p.set_x(-0.5, 15.5).set_y(0, 255)
    p.grid_y([0, 64, 128, 192, 255], str, "Mã độ sáng (0–255)")
    p.axis_x(list(range(0, 16, 2)), lambda t: f"{t}", "Chỉ số khung i (t = i/60 s)")
    xs = [i / 20 for i in range(0, 15 * 20 + 1)]
    p.line(xs, [255 * 0.5 * (1 + math.sin(2 * math.pi * f * x / 60)) for x in xs], S2, 2,
           tip="Hình sin lý tưởng 7,83 Hz")
    p.stems(list(range(16)), codes, S1, 0, [f"Khung {i}: 0x{c:02X} = {c}" for i, c in enumerate(codes)])
    p.legend([("Mã 8 bit mỗi khung", S1, "dot"), ("Hình sin lý tưởng 7,83 Hz", S2, "line")], y=56, x=p.l + 260)
    return p.svg("Biểu đồ que: 16 mã 8 bit " + " ".join(f"{c:02X}" for c in codes) + " bám theo hình sin 7,83 Hz.")


# Figure 6 ------------------------------------------------------------------
def fig_harmonics(res: dict) -> str:
    h50 = res["synth"]["harmonics"]["0.5"]["rows"]
    h10 = res["synth"]["harmonics"]["0.1"]["rows"]
    p = Plot(760, 360, "Hình 6. Phổ hài của chuỗi xung 7,83 Hz theo hệ số lấp đầy D",
             "Xung hẹp (D = 10 %) chỉ đặt khoảng 21 % công suất xoay chiều ở 7,83 Hz")
    p.set_x(0.4, 12.6).set_y(0, 0.7)
    p.grid_y([0, 0.2, 0.4, 0.6], lambda t: vn(t, 1), "Biên độ hài (đơn vị A)")
    p.axis_x(list(range(1, 13)), lambda t: f"{t}", "Bậc hài n (tần số n × 7,83 Hz)")
    for r50, r10 in zip(h50, h10):
        n = r50["n"]
        p.bar(n - 0.17, 14, float(r50["amplitude"]), S1, tip=f"D=0,5, n={n} ({r50['f_hz']} Hz): {r50['amplitude']}")
        p.bar(n + 0.17, 14, float(r10["amplitude"]), S2, tip=f"D=0,1, n={n} ({r10['f_hz']} Hz): {r10['amplitude']}")
    p.text(p.X(1 - 0.17), p.Y(float(h50[0]["amplitude"])) - 6, vn(float(h50[0]["amplitude"]), 3), 11, INK, "middle")
    p.text(p.X(1 + 0.17) + 6, p.Y(float(h10[0]["amplitude"])) - 6, vn(float(h10[0]["amplitude"]), 3), 11, INK, "start")
    p.legend([("D = 50 % (sóng vuông)", S1, "bar"), ("D = 10 % (xung hẹp)", S2, "bar")], y=56, x=p.l + 300)
    return p.svg("Cột đôi cho n = 1..12: sóng vuông chỉ có hài lẻ, xung hẹp rải năng lượng ra nhiều hài.")


# Figure 7 ------------------------------------------------------------------
METHOD_LABELS = [("argmax", "Đỉnh cực đại"), ("lm", "Khớp Lorentz"), ("lm_robust", "Lorentz bền vững"),
                 ("ridge", "Ridge (ML)"), ("hybrid", "Lai ML + Lorentz")]


def fig_ml(res: dict) -> str:
    m = res["ml"]["metrics"]
    p = Plot(760, 380, "Hình 7. Sai số tuyệt đối trung bình khi ước lượng f₁ (400 phổ kiểm thử)",
             "Phổ mô phỏng có nhiễu nhân 12 % và 35 % mẫu có vạch nhiễu nhân tạo hẹp", bottom=64)
    top = 0.8
    p.set_x(-0.5, 4.5).set_y(0, top)
    p.grid_y([0, 0.2, 0.4, 0.6, 0.8], lambda t: vn(t, 1), "MAE (Hz)")
    yb = p.h - p.b
    p.raw(f'<line x1="{n2(p.l)}" y1="{n2(yb)}" x2="{n2(p.w - p.r)}" y2="{n2(yb)}" stroke="{AXIS}"/>')
    for i, (key, label) in enumerate(METHOD_LABELS):
        c, d = m[key]["clean"]["mae_hz"], m[key]["interference"]["mae_hz"]
        p.bar(i - 0.16, 34, c, S1, tip=f"{label} - không nhiễu vạch: {c} Hz")
        p.bar(i + 0.16, 34, d, S2, tip=f"{label} - có nhiễu vạch: {d} Hz")
        p.text(p.X(i), yb + 18, label, 11, MUTED, "middle")
        if key in ("argmax", "hybrid"):
            p.text(p.X(i + 0.16), p.Y(d) - 6, vn(d, 3), 11, INK, "middle", "700")
            p.text(p.X(i - 0.16), p.Y(c) - 6, vn(c, 3), 11, INK, "middle")
    p.text((p.l + p.w - p.r) / 2, p.h - 14, "Phương pháp ước lượng", 12, INK2, "middle")
    p.legend([("Không nhiễu vạch", S1, "bar"), ("Có nhiễu vạch nhân tạo", S2, "bar")], y=56, x=p.l + 300)
    return p.svg("Cột đôi MAE theo phương pháp; phương pháp lai đạt sai số thấp nhất ở cả hai nhóm.")


# Figure 8 ------------------------------------------------------------------
def _box(out, x, y, w, h, title, lines, color):
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{SURFACE}" stroke="{color}" stroke-width="1.5"/>')
    out.append(f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="2" fill="{color}"/>')
    out.append(f'<text x="{x + 14}" y="{y + 18}" font-size="12.5" font-weight="700" fill="{INK}">{escape(title)}</text>')
    for i, ln in enumerate(lines):
        out.append(f'<text x="{x + 14}" y="{y + 35 + 15 * i}" font-size="11" fill="{INK2}">{escape(ln)}</text>')


def _arrow(out, x1, y1, x2, y2, both=False):
    m = ' marker-start="url(#ah)"' if both else ""
    out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{MUTED}" stroke-width="1.5" '
               f'marker-end="url(#ah)"{m}/>')


def _path_arrow(out, pts):
    d = " ".join(f"{x},{y}" for x, y in pts)
    out.append(f'<polyline points="{d}" fill="none" stroke="{MUTED}" stroke-width="1.5" marker-end="url(#ah)"/>')


def fig_architecture(res: dict) -> str:
    w, h = 760, 520
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
           f'font-family="{FONT}" role="img" aria-label="Kiến trúc hệ thống SR783">',
           "<title>Hình 8. Kiến trúc phần mềm/thiết bị trung gian SR783</title>",
           f'<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
           f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 Z" fill="{MUTED}"/></marker></defs>',
           f'<rect width="{w}" height="{h}" fill="{SURFACE}"/>',
           f'<text x="24" y="24" font-size="15" font-weight="700" fill="{INK}">Hình 8. Kiến trúc SR783: '
           f'trợ lý hội thoại + lõi đồng bộ tần số trên thiết bị đa năng</text>']
    _box(out, 250, 40, 260, 52, "Người dùng", ["điện thoại · máy tính bảng · máy tính · TV"], INK2)
    _box(out, 24, 120, 330, 84, "Trợ lý hội thoại (tiếng Việt)",
         ["Ngoại tuyến: cơ sở tri thức + mức bằng chứng A–D", "Trực tuyến (tùy chọn): Claude gọi công cụ trang",
          "Rào an toàn: không tuyên bố y tế, cảnh báo nhấp nháy"], S1)
    _box(out, 406, 120, 330, 84, "Lõi đồng bộ tần số",
         ["f = p/q Hz (hữu tỉ, mặc định 783/100)", "pha = (p·Δt mod 1000q)/1000q, Δt: ms UTC",
          "đồng hồ âm thanh khóa theo mốc pha 0"], S2)
    _box(out, 24, 240, 230, 84, "Đồng bộ theo Schumann thực đo",
         ["nhập f₁ đo được hoặc CSV trạm", "kiểm tra dải 7,0–9,0 Hz, cờ chất lượng", "đổi sang p/q (q = 1000)"], S3)
    _box(out, 266, 240, 230, 84, "Phòng nhiều thiết bị",
         ["mã phiên SR783 có kiểm tra SHA-256", "ping/pong ước lượng lệch đồng hồ", "hiện diện: thiết bị đang khớp pha"], S3)
    _box(out, 508, 240, 228, 84, "Đầu ra",
         ["âm đẳng thời / hai tai / đơn âm", "vòng pha 30 chu kỳ (không nhấp nháy)", "xuất WAV 16 bit đóng gói ZIP"], S2)
    _box(out, 24, 360, 230, 84, "Kiểm chứng thiết bị 7,83 Hz",
         ["CSV cảm biến → Goertzel + nội suy", "tần số đo, sai số ppm, SNR", "kết luận Đạt/Không đạt"], S1)
    _box(out, 266, 360, 230, 84, "Toàn vẹn và tự sửa lỗi",
         ["cài đặt mã hóa SECDED(72,64)", "sửa 1 bit, phát hiện 2 bit", "nhật ký chuỗi băm SHA-256"], S1)
    _box(out, 508, 360, 228, 84, "Thiết bị trung gian (tùy chọn)",
         ["cuộn cảm ứng + ADC 24 bit", "TCXO hoặc GPS 1 PPS làm chuẩn", "USB-C / BLE tới thiết bị đa năng"], INK2)
    out.append(f'<text x="24" y="482" font-size="11" fill="{INK2}">Mũi tên: luồng dữ liệu. Toàn bộ chạy cục bộ; '
               f'chỉ chức năng trực tuyến tùy chọn gửi câu hỏi tới Claude khi người dùng đồng ý.</text>')
    out.append(f'<text x="24" y="500" font-size="11" fill="{INK2}">Không có chức năng chẩn đoán hay điều trị; '
               f'phát nhịp 7,83 Hz chỉ phục vụ thư giãn, giáo dục và nghiên cứu.</text>')
    _arrow(out, 330, 92, 190, 120, True)
    _arrow(out, 430, 92, 570, 120, True)
    _arrow(out, 354, 162, 406, 162, True)
    _arrow(out, 139, 240, 470, 204)
    _arrow(out, 381, 240, 520, 204, True)
    _arrow(out, 640, 204, 622, 240)
    _arrow(out, 502, 360, 502, 204, True)
    _path_arrow(out, [(736, 402), (748, 402), (748, 162), (736, 162)])
    _path_arrow(out, [(622, 444), (622, 456), (139, 456), (139, 444)])
    out.append("</svg>")
    return "\n".join(out) + "\n"


# Figure 9 ------------------------------------------------------------------
def fig_example_fit(res: dict) -> str:
    ex = res["ml"]["example"]
    grid = [res["ml"]["grid"]["f_lo_hz"] + res["ml"]["grid"]["step_hz"] * i for i in range(res["ml"]["grid"]["bins"])]
    ymax = max(ex["y"]) * 1.1
    p = Plot(760, 380, "Hình 9. Một phổ kiểm thử có vạch nhiễu nhân tạo",
             f"f₁ thật {vn(ex['f1_true'], 3)} Hz; đỉnh cực đại rơi vào vạch nhiễu {vn(ex['argmax'], 2)} Hz; "
             f"phương pháp lai cho {vn(ex['hybrid'], 3)} Hz")
    p.set_x(5, 11).set_y(0, ymax)
    step = 0.5 if ymax < 3 else 1.0
    ticks = [round(step * k, 2) for k in range(int(ymax / step) + 1)]
    p.grid_y(ticks, lambda t: vn(t, 1), "Mật độ phổ (đơn vị tùy ý)")
    p.axis_x([5, 6, 7, 8, 9, 10, 11], str, "Tần số (Hz)")
    p.vline(ex["f1_true"], INK, "5 4", f"f₁ thật {vn(ex['f1_true'], 3)}", p.t + 12, 1.5)
    p.vline(ex["argmax"], MUTED, "2 3", f"đỉnh cực đại {vn(ex['argmax'], 2)}", p.t + 40, 1.5)
    p.dots(grid, ex["y"], S1, 2.5, [f"{vn(f, 2)} Hz: {v}" for f, v in zip(grid, ex["y"])], ring=False)
    p.line(grid, ex["fit"], S2, 2, tip="Khớp Lorentz bền vững khởi tạo bằng ML")
    p.legend([("Phổ quan sát", S1, "dot"), ("Khớp lai ML + Lorentz", S2, "line")], y=56, x=p.l + 330)
    return p.svg("Chấm phổ quan sát có một vạch nhọn; đường khớp bỏ qua vạch và đặt đỉnh gần f₁ thật.")


ALL = {
    "fig1_sr_spectrum.svg": fig_sr_spectrum,
    "fig2_field_ladder.svg": fig_field_ladder,
    "fig3_ieee754_bits.svg": fig_ieee754,
    "fig4_dds_error.svg": fig_dds_error,
    "fig5_display_60hz.svg": fig_display,
    "fig6_pulse_harmonics.svg": fig_harmonics,
    "fig7_ml_results.svg": fig_ml,
    "fig8_architecture.svg": fig_architecture,
    "fig9_example_fit.svg": fig_example_fit,
}
