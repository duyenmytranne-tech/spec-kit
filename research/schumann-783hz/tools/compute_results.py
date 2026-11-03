#!/usr/bin/env python3
"""Regenerate results/results.json - every number quoted in the report.

Usage:  python tools/compute_results.py [--check]
  --check  recompute and compare with the committed file instead of writing.
The output has no timestamps and is serialised with sorted keys, so the
bytes are identical on every run of the same Python on the same platform.
"""
from __future__ import annotations

import hashlib
import json
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sr783 import __version__, bits, integrity, physics, prng, secded, srml, synth  # noqa: E402

OUT = ROOT / "results" / "results.json"


def secded_examples() -> dict:
    ex = {}
    c84 = secded.SECDED_8_4
    ex["bcd_783_secded_8_4"] = [{"digit": d, "data_bits": format(int(d), "04b"),
                                 "codeword_bits": format(c84.encode(int(d)), "08b")} for d in "783"]
    c22 = secded.SECDED_22_16
    ocr = 15963
    ex["ocr1a_secded_22_16"] = {"data_hex": f"0x{ocr:04X}", "codeword_hex": "0x" + c22.to_hex(c22.encode(ocr))}
    c72 = secded.SECDED_72_64
    word = int(bits.representations("7.83")["ieee754"]["binary64"]["hex"], 16)
    ex["binary64_secded_72_64"] = {"data_hex": f"0x{word:016X}", "codeword_hex": "0x" + c72.to_hex(c72.encode(word))}
    # exhaustive fault injection on the three example codewords
    summary = {}
    for name, code, data in (("8_4", c84, 7), ("22_16", c22, ocr), ("72_64", c72, word)):
        cw = code.encode(data)
        single_ok = all(code.decode(cw ^ (1 << i)) == {"status": "corrected", "data": data, "position": i}
                        for i in range(code.total_bits))
        doubles = [(i, j) for i in range(code.total_bits) for j in range(i + 1, code.total_bits)]
        double_ok = all(code.decode(cw ^ (1 << i) ^ (1 << j))["status"] == "double" for i, j in doubles)
        summary[name] = {"codeword_bits": code.total_bits, "single_flips": code.total_bits,
                         "single_corrected": single_ok, "double_flips": len(doubles), "double_detected": double_ok}
    ex["fault_injection"] = summary
    return ex


def settings_record() -> dict:
    """Contract example for the app's SECDED-protected settings (2 x 64-bit words)."""
    p, q, carrier_centi, volume, mode, minutes, flags = 783, 100, 20000, 30, 1, 20, 0
    w0 = (p << 32) | q
    w1 = (carrier_centi << 40) | (volume << 32) | (mode << 28) | (minutes << 20) | (flags << 12)
    c = secded.SECDED_72_64
    cws = [c.to_hex(c.encode(w0)), c.to_hex(c.encode(w1))]
    tag = hashlib.sha256("".join(cws).encode()).hexdigest()[:16]
    return {"fields": {"p": p, "q": q, "carrier_centi_hz": carrier_centi, "volume_pct": volume, "mode": mode,
                       "session_min": minutes, "flags": flags},
            "word0_hex": f"{w0:016X}", "word1_hex": f"{w1:016X}", "codewords": cws, "tag": tag}


def sync_code(p: int, q: int, t0: int, mode: str) -> dict:
    body = f"SR783-1-{p}-{q}-{t0}-{mode}"
    check = hashlib.sha256(body.encode()).hexdigest()[:8].upper()
    return {"body": body, "check": check, "code": f"{body}-{check}"}


def compute() -> dict:
    f = synth.F_NOMINAL
    dds_cases = [(48000, 32), (44100, 32), (96000, 32), (48000, 24), (16_000_000, 32), (16_000_000, 48), (1_000_000, 24)]
    t_ref = 1_793_664_000_000            # 2026-11-03T00:00:00Z in ms
    rng = prng.SplitMix64(0)
    chain_entries = [{"event": "start", "p": 783, "q": 100, "t_ms": t_ref, "mode": "I"},
                     {"event": "stop", "p": 783, "q": 100, "t_ms": t_ref + 600_000, "mode": "I"}]
    return {
        "meta": {"package": "sr783", "version": __version__, "generator": "tools/compute_results.py",
                 "value": "7.83 Hz = 783/100 Hz", "note": "deterministic: no timestamps, sorted keys"},
        "bits": bits.representations("7.83"),
        "synth": {
            "dds": [synth.dds(f, fc, n) for fc, n in dds_cases],
            "dds_curves": {str(fc): synth.dds_error_curve(f, fc) for fc in (48000, 16_000_000)},
            "timer1": synth.avr_timer1_ctc(f),
            "clock_tolerance": synth.clock_tolerance(),
            "ne555": synth.ne555(),
            "display": synth.display_frames(),
            "audio": synth.audio_table(),
            "harmonics": {"0.5": synth.pulse_harmonics(0.5), "0.1": synth.pulse_harmonics(0.1)},
            "phase_vectors": [synth.phase_vector(783, 100, t_ref), synth.phase_vector(783, 100, t_ref + 12_345),
                              synth.phase_vector(783, 100, t_ref + 127, t_ref),
                              synth.phase_vector(7792, 1000, t_ref + 12_345)],
            "offset_phase_error": synth.offset_phase_error(),
            "max_offset_10deg_ms": synth.max_offset_for(10),
            "sync_code_example": sync_code(783, 100, t_ref, "I"),
        },
        "physics": {
            "cavity": physics.cavity_modes(),
            "icnirp": physics.icnirp_2010(),
            "generator": physics.generator_table(),
            "magnetometer": physics.magnetometer(),
            "field_ladder": physics.field_ladder(),
            "adc": physics.adc_dynamic_range(),
            "shannon": physics.shannon_table(),
            "diurnal_vn": physics.diurnal_vn(),
        },
        "secded": secded_examples(),
        "settings_record": settings_record(),
        "prng": {"splitmix64_seed0": [f"0x{rng.next_u64():016X}" for _ in range(4)]},
        "integrity": {
            "sha256_abc": hashlib.sha256(b"abc").hexdigest(),
            "sha256_empty": hashlib.sha256(b"").hexdigest(),
            "chain_entries": chain_entries,
            "chain_hashes": integrity.chain(chain_entries),
        },
        "ml": srml.run(),
    }


def dump(data: dict) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode("utf-8")


def main() -> int:
    blob = dump(compute())
    if "--check" in sys.argv:
        same = OUT.read_bytes() == blob
        print("results.json bit-identical:", same)
        return 0 if same else 1
    OUT.write_bytes(blob)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(blob)} bytes, sha256 {hashlib.sha256(blob).hexdigest()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
