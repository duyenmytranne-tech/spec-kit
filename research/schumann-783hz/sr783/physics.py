"""Physical scale of 7.83 Hz: cavity modes, fields, limits, sensors, channels.

Constants
---------
c        299 792 458 m/s (exact, SI)
a        6 371 008.8 m   (IUGG mean Earth radius R1)
mu0      4*pi*1e-7 N/A^2 (differs from the CODATA value by < 1e-9 relative)
"""
from __future__ import annotations

import math

C = 299_792_458.0
A_EARTH = 6_371_008.8
MU0 = 4 * math.pi * 1e-7

OBSERVED_MODES_HZ = [7.83, 14.3, 20.8, 27.3, 33.8]   # commonly quoted mean values


def cavity_modes() -> dict:
    base = C / (2 * math.pi * A_EARTH)
    rows = []
    for n, obs in enumerate(OBSERVED_MODES_HZ, start=1):
        ideal = base * math.sqrt(n * (n + 1))
        rows.append({"n": n, "ideal_hz": f"{ideal:.2f}", "observed_hz": f"{obs:.2f}",
                     "ratio": f"{obs / ideal:.3f}"})
    lam = C / 7.83
    circ = 2 * math.pi * A_EARTH
    return {"c_over_2pi_a_hz": f"{base:.4f}", "rows": rows,
            "wavelength_km": f"{lam / 1000:.0f}", "circumference_km": f"{circ / 1000:.0f}",
            "wavelength_over_circumference": f"{lam / circ:.4f}",
            "fft_bin_10min": {"T_s": 600, "df_hz": f"{1 / 600:.6f}", "bin_index": round(7.83 * 600)}}


def icnirp_2010(f: float = 7.83) -> dict:
    """ICNIRP (2010) values for 1 Hz <= f < 8 Hz (reference levels) and 1-10 Hz (CNS)."""
    b_pub = 4e-2 / f**2        # T, general public reference level, 1-8 Hz
    b_occ = 2e-1 / f**2        # T, occupational reference level, 1-8 Hz
    e_cns = 0.1 / f            # V/m, basic restriction CNS tissue (public), 1-10 Hz
    # continuity checks at the band edges (8 Hz and 25 Hz)
    edge8 = (4e-2 / 64, 5e-3 / 8)
    edge25 = (5e-3 / 25, 2e-4)
    return {"f_hz": f, "B_public_uT": f"{b_pub * 1e6:.1f}", "B_occupational_uT": f"{b_occ * 1e6:.0f}",
            "E_cns_public_mV_per_m": f"{e_cns * 1e3:.1f}",
            "continuity_8hz_uT": [f"{v * 1e6:.1f}" for v in edge8],
            "continuity_25hz_uT": [f"{v * 1e6:.1f}" for v in edge25]}


def coil_axis_field(z_m: float, turns: int = 100, current_a: float = 0.010, radius_m: float = 0.01) -> float:
    """On-axis flux density of a flat circular coil (Biot-Savart)."""
    return MU0 * turns * current_a * radius_m**2 / (2 * (radius_m**2 + z_m**2) ** 1.5)


def fmt_tesla(b: float) -> str:
    for unit, scale in (("mT", 1e-3), ("µT", 1e-6), ("nT", 1e-9), ("pT", 1e-12), ("fT", 1e-15)):
        if b >= scale:
            return f"{b / scale:.3g} {unit}"
    return f"{b:.3g} T"


def generator_table() -> dict:
    rows = []
    for z_cm in (0, 1, 2, 3, 5, 10, 30, 100):
        b = coil_axis_field(z_cm / 100)
        rows.append({"z_cm": z_cm, "B_T": f"{b:.4e}", "B_text": fmt_tesla(b),
                     "x_schumann_1pT": f"{b / 1e-12:.3g}", "ak09918_lsb": f"{b / 0.15e-6:.3g}"})
    return {"model": {"turns": 100, "current_mA": 10, "radius_cm": 1.0}, "rows": rows}


def detect_distance_cm(lsb_count: float, lsb_t: float = 0.15e-6) -> str:
    """Distance at which the model coil gives `lsb_count` magnetometer LSB (bisection)."""
    target = lsb_count * lsb_t
    lo, hi = 0.0, 2.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if coil_axis_field(mid) > target:
            lo = mid
        else:
            hi = mid
    return f"{lo * 100:.2f}"


def field_ladder() -> list[dict]:
    """Magnitudes compared on one logarithmic axis (tesla)."""
    return [
        {"key": "sr", "label": "Cộng hưởng Schumann (mode 1)", "tesla": 1e-12},
        {"key": "gen_1m", "label": "Máy phát mẫu ở 1 m", "tesla": coil_axis_field(1.0)},
        {"key": "gen_10cm", "label": "Máy phát mẫu ở 10 cm", "tesla": coil_axis_field(0.10)},
        {"key": "home50", "label": "Từ trường 50 Hz trung bình trong nhà (châu Âu)", "tesla": 0.07e-6},
        {"key": "lsb", "label": "1 LSB từ kế điện thoại (AK09918)", "tesla": 0.15e-6},
        {"key": "earth_lo", "label": "Từ trường tĩnh Trái Đất (xích đạo)", "tesla": 25e-6},
        {"key": "earth_hi", "label": "Từ trường tĩnh Trái Đất (cực)", "tesla": 65e-6},
        {"key": "icnirp", "label": "Mức tham chiếu ICNIRP công chúng ở 7,83 Hz", "tesla": 4e-2 / 7.83**2},
    ]


def magnetometer() -> dict:
    lsb = 0.15e-6
    full_scale = 4912e-6
    return {"lsb_uT": 0.15, "bits": 16, "sr_in_lsb": f"{1e-12 / lsb:.3e}",
            "bits_to_resolve_1pT_full_scale": f"{math.log2(full_scale / 1e-12):.2f}",
            "detect_1lsb_cm": detect_distance_cm(1), "detect_10lsb_cm": detect_distance_cm(10),
            "nyquist_note_hz": 50}


def adc_dynamic_range() -> list[dict]:
    return [{"bits": n, "ideal_snr_db": f"{6.02 * n + 1.76:.2f}"} for n in (12, 16, 24, 32)]


def shannon(bandwidth_hz: float, snr_db: float) -> float:
    return bandwidth_hz * math.log2(1 + 10 ** (snr_db / 10))


def shannon_table() -> list[dict]:
    rows = []
    for label, b in (("Băng thông mode 1 (f/Q, Q≈5)", 7.83 / 5), ("Dải FSK 72-80 Hz", 8.0)):
        for snr in (10, 0, -10, -20):
            rows.append({"case": label, "B_hz": f"{b:.3f}", "snr_db": snr,
                         "capacity_bps": f"{shannon(b, snr):.4g}"})
    return rows


def diurnal_vn() -> list[dict]:
    """Classic SR intensity peaks (UT) converted to Viet Nam time (UTC+7)."""
    rows = []
    for ut, region in ((8, "châu Á - Hải đảo Đông Nam Á"), (14, "châu Phi"), (20, "châu Mỹ")):
        vn = (ut + 7) % 24
        rows.append({"ut_h": ut, "vn_h": vn, "region": region, "next_day": ut + 7 >= 24})
    return rows
