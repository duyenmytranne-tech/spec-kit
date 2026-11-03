"""Generating 7.83 Hz on real hardware and software, analysed at the bit level.

All frequency arithmetic is rational (Fraction); only the 555 timer (ln 2)
and sinusoid quantisation use floating point, and those results are
reported with a stated number of significant digits.
"""
from __future__ import annotations

import math
from fractions import Fraction
from math import gcd

from .bits import dec_str, sci

F_NOMINAL = Fraction(783, 100)  # 7.83 Hz as an exact rational


# --------------------------------------------------------------------------
# Direct digital synthesis (phase accumulator)
# --------------------------------------------------------------------------
def dds(f: Fraction, f_clk: int, nbits: int) -> dict:
    """Tuning word M = round(f * 2^N / f_clk); f_out = M * f_clk / 2^N."""
    word = round(f * (1 << nbits) / f_clk)
    f_out = Fraction(word * f_clk, 1 << nbits)
    err = f_out - f
    return {
        "accumulator_bits": nbits,
        "f_clk_hz": f_clk,
        "tuning_word": word,
        "tuning_word_hex": "0x" + format(word, f"0{(nbits + 3) // 4}X"),
        "f_out_hz": dec_str(f_out, 15),
        "error_hz": sci(err, 4),
        "error_ppm": sci(err / f * 10**6, 4),
        "resolution_hz": sci(Fraction(f_clk, 1 << nbits), 4),
    }


def dds_error_curve(f: Fraction, f_clk: int, widths=range(12, 49, 2)) -> list[dict]:
    rows = []
    for n in widths:
        word = round(f * (1 << n) / f_clk)
        f_out = Fraction(word * f_clk, 1 << n)
        rel = abs(f_out - f) / f
        rows.append({"bits": n, "abs_rel_error": float(rel)})
    return rows


# --------------------------------------------------------------------------
# AVR ATmega328P Timer1 in CTC mode, toggling OC1A
#   f_OC1A = f_clk / (2 * N * (1 + OCR1A))      (datasheet formula)
# --------------------------------------------------------------------------
AVR_PRESCALERS = {1: 0b001, 8: 0b010, 64: 0b011, 256: 0b100, 1024: 0b101}


def avr_timer1_ctc(f: Fraction, f_clk: int = 16_000_000) -> dict:
    rows = []
    for n, cs in AVR_PRESCALERS.items():
        ideal = Fraction(f_clk, 2 * n) / f - 1
        ocr = round(ideal)
        row = {"prescaler": n, "cs_bits": format(cs, "03b"), "ocr_ideal": dec_str(ideal, 4),
               "ocr": ocr, "valid": 0 <= ocr <= 0xFFFF}
        if row["valid"]:
            f_out = Fraction(f_clk, 2 * n * (1 + ocr))
            row.update({"ocr_hex": "0x" + format(ocr, "04X"), "f_out_hz": dec_str(f_out, 9),
                        "error_ppm": dec_str((f_out - f) / f * 10**6, 3)})
            row["_err"] = abs(f_out - f)
        rows.append(row)
    best = min((r for r in rows if r["valid"]), key=lambda r: r["_err"])
    for r in rows:
        r.pop("_err", None)
    tccr1a = 0b0100_0000                         # COM1A1:0 = 01 -> toggle OC1A
    tccr1b = (1 << 3) | AVR_PRESCALERS[best["prescaler"]]  # WGM12=1 (CTC), CS12:10
    return {
        "f_clk_hz": f_clk,
        "rows": rows,
        "best": {k: best[k] for k in ("prescaler", "ocr", "ocr_hex", "f_out_hz", "error_ppm")},
        "registers": {
            "TCCR1A": "0x" + format(tccr1a, "02X"), "TCCR1A_bits": format(tccr1a, "08b"),
            "TCCR1B": "0x" + format(tccr1b, "02X"), "TCCR1B_bits": format(tccr1b, "08b"),
            "OCR1AH": "0x" + format(best["ocr"] >> 8, "02X"),
            "OCR1AL": "0x" + format(best["ocr"] & 0xFF, "02X"),
        },
    }


def clock_tolerance(f_target: float = 7.83) -> list[dict]:
    """How the clock source tolerance moves a timer-derived 7.83 Hz."""
    rows = []
    for name, tol in (("Thạch anh ±20 ppm", 20e-6), ("RC hiệu chuẩn ±1 %", 0.01),
                      ("RC xuất xưởng ±2 %", 0.02), ("RC xuất xưởng ±10 %", 0.10)):
        rows.append({"source": name, "tolerance": tol,
                     "f_min_hz": f"{f_target * (1 - tol):.6f}",
                     "f_max_hz": f"{f_target * (1 + tol):.6f}"})
    return rows


def ne555(r1: float = 11.0e3, r2: float = 86.6e3, c: float = 1.0e-6,
          r_tol: float = 0.01, c_tol: float = 0.05) -> dict:
    """Astable 555: f = 1 / (ln2 * (R1 + 2 R2) * C) (datasheet: 1.44/((RA+2RB)C))."""
    def f(r1_, r2_, c_):
        return 1.0 / (math.log(2) * (r1_ + 2 * r2_) * c_)
    nom = f(r1, r2, c)
    fmax = f(r1 * (1 - r_tol), r2 * (1 - r_tol), c * (1 - c_tol))
    fmin = f(r1 * (1 + r_tol), r2 * (1 + r_tol), c * (1 + c_tol))
    return {"R1_ohm": r1, "R2_ohm": r2, "C_farad": c, "r_tol": r_tol, "c_tol": c_tol,
            "f_nominal_hz": f"{nom:.4f}", "error_percent": f"{(nom / 7.83 - 1) * 100:.3f}",
            "f_min_hz": f"{fmin:.3f}", "f_max_hz": f"{fmax:.3f}",
            "f_datasheet_144_hz": f"{1.44 / ((r1 + 2 * r2) * c):.4f}"}


# --------------------------------------------------------------------------
# Visual stimulation on fixed-refresh displays
# --------------------------------------------------------------------------
def quantize_u8(x: float) -> int:
    """Round-half-up to 0..255 (identical rule in the JavaScript app)."""
    return max(0, min(255, math.floor(255 * x + 0.5)))


def display_frames(f: Fraction = F_NOMINAL, refresh_rates=(60, 75, 90, 120, 144, 165, 240)) -> dict:
    rows = []
    for r in refresh_rates:
        fpc = Fraction(r) / f
        k = round(fpc)
        f_onoff = Fraction(r, k)
        rows.append({"refresh_hz": r, "frames_per_cycle": dec_str(fpc, 4),
                     "onoff_k": k, "onoff_f_hz": dec_str(f_onoff, 4),
                     "onoff_error_percent": dec_str((f_onoff - f) / f * 100, 2)})
    codes = [quantize_u8(0.5 * (1 + math.sin(2 * math.pi * float(f) * i / 60))) for i in range(16)]
    return {"rows": rows, "sampled_sinusoid_60hz_u8": codes,
            "sampled_sinusoid_60hz_hex": " ".join(format(c, "02X") for c in codes),
            "flashes_per_second": dec_str(f, 2), "wcag_231_limit_per_second": 3}


# --------------------------------------------------------------------------
# Digital audio
# --------------------------------------------------------------------------
def lcm(a: int, b: int) -> int:
    return a // gcd(a, b) * b


def loop_samples(freqs: list[Fraction], fs: int) -> int:
    """Smallest buffer length (samples) holding an integer number of cycles of every tone."""
    length = 1
    for fr in freqs:
        # cycles = fr * L / fs integer  <=>  L multiple of fs*den / gcd(num, fs*den)
        num, den = fr.numerator, fr.denominator
        step = fs * den // gcd(num, fs * den)
        length = lcm(length, step)
    return length


def audio_table(f: Fraction = F_NOMINAL, carrier: Fraction = Fraction(200), rates=(44100, 48000, 96000)) -> list[dict]:
    rows = []
    for fs in rates:
        spc = Fraction(fs) / f
        word32 = round(f * (1 << 32) / fs)
        iso = loop_samples([f, carrier], fs)
        bina = loop_samples([carrier, carrier + f], fs)
        rows.append({"fs_hz": fs, "samples_per_cycle": dec_str(spc, 6),
                     "dds32_word": word32, "dds32_word_hex": "0x" + format(word32, "08X"),
                     "loop_isochronic_samples": iso, "loop_isochronic_s": dec_str(Fraction(iso, fs), 4),
                     "loop_binaural_samples": bina, "loop_binaural_s": dec_str(Fraction(bina, fs), 4)})
    return rows


# --------------------------------------------------------------------------
# Harmonic content of a 7.83 Hz pulse train (0/A, duty D)
#   c_n = (2A / (n pi)) |sin(n pi D)| ;  AC power = A^2 D (1 - D)
# --------------------------------------------------------------------------
def pulse_harmonics(duty: float, n_max: int = 12, f0: float = 7.83) -> dict:
    ac_power = duty * (1 - duty)
    rows = []
    for n in range(1, n_max + 1):
        c = 2 / (n * math.pi) * abs(math.sin(n * math.pi * duty))
        rows.append({"n": n, "f_hz": f"{n * f0:.2f}", "amplitude": f"{c:.4f}",
                     "power_fraction": f"{(c * c / 2) / ac_power:.4f}"})
    return {"duty": duty, "rows": rows,
            "fundamental_power_fraction": rows[0]["power_fraction"]}


# --------------------------------------------------------------------------
# Rational phase synchronisation across devices (bit-exact, integer only)
#   phase(t) = frac( f * (t - t0) ),  f = p/q Hz,  t in integer milliseconds
#            = ((p * (t - t0)) mod (1000 q)) / (1000 q)
# --------------------------------------------------------------------------
def phase_units(p: int, q: int, t_ms: int, t0_ms: int = 0) -> tuple[int, int]:
    modulus = 1000 * q
    return (p * (t_ms - t0_ms)) % modulus, modulus


def phase_vector(p: int, q: int, t_ms: int, t0_ms: int = 0) -> dict:
    num, mod = phase_units(p, q, t_ms, t0_ms)
    deg = Fraction(num * 360, mod)
    cycles = Fraction(p * (t_ms - t0_ms), 1000 * q)
    return {"p": p, "q": q, "t_ms": t_ms, "t0_ms": t0_ms, "phase_num": num, "phase_mod": mod,
            "phase_deg": dec_str(deg, 4), "whole_cycles": cycles.numerator // cycles.denominator}


def offset_phase_error(f: Fraction = F_NOMINAL, offsets_ms=(1, 3.55, 10, 20, 50)) -> list[dict]:
    return [{"offset_ms": o, "phase_error_deg": f"{360 * float(f) * o / 1000:.2f}"} for o in offsets_ms]


def max_offset_for(deg: float, f: Fraction = F_NOMINAL) -> str:
    return f"{deg / (360 * float(f)) * 1000:.3f}"
