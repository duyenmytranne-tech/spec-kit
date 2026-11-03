"""SR783 command line - the "software intermediary device" for computers.

  python -m sr783 bits 7.83
  python -m sr783 phase --p 783 --q 100 [--t0 0] [--t now|<ms>]
  python -m sr783 code --p 783 --q 100 --t0 1793664000000 --mode I
  python -m sr783 tone --mode isochronic --seconds 60 --out phien.wav [--freq 7.83] [--carrier 200]
  python -m sr783 seal | verify
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from . import bits, integrity, synth, wav

ROOT = Path(__file__).resolve().parents[1]


def cmd_bits(a) -> int:
    rep = bits.representations(a.value)
    f = Fraction(Decimal(a.value))
    out = {"value": a.value, "rational": rep["rational"],
           "binary32": rep["ieee754"]["binary32"]["hex"], "binary32_exact": rep["ieee754"]["binary32"]["exact_value"],
           "binary64": rep["ieee754"]["binary64"]["hex"], "binary64_exact": rep["ieee754"]["binary64"]["exact_value"],
           "dds_48k_32bit": synth.dds(f, 48000, 32), "avr_timer1": synth.avr_timer1_ctc(f)["best"]}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


def cmd_phase(a) -> int:
    t = int(time.time() * 1000) if a.t == "now" else int(a.t)
    print(json.dumps(synth.phase_vector(a.p, a.q, t, a.t0), ensure_ascii=False))
    return 0


def cmd_code(a) -> int:
    body = f"SR783-1-{a.p}-{a.q}-{a.t0}-{a.mode}"
    print(body + "-" + hashlib.sha256(body.encode()).hexdigest()[:8].upper())
    return 0


def cmd_tone(a) -> int:
    beat = Fraction(Decimal(a.freq))
    pcm = wav.synth(a.mode, a.seconds, a.fs, beat, Fraction(Decimal(a.carrier)), a.amplitude)
    blob = wav.wav_bytes(pcm, a.fs)
    Path(a.out).write_bytes(blob)
    print(f"wrote {a.out}: {len(blob)} bytes, {a.mode}, beat {beat.numerator}/{beat.denominator} Hz, "
          f"sha256 {hashlib.sha256(blob).hexdigest()}")
    return 0


def cmd_seal(a) -> int:
    res = integrity.seal(ROOT)
    print(f"sealed {res['files']} files; root {res['root']}")
    return 0


def cmd_verify(a) -> int:
    res = integrity.verify(ROOT)
    print(json.dumps({k: v for k, v in res.items() if k != "secded_report"}, ensure_ascii=False, indent=1))
    return 0 if res["ok"] else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="sr783", description="SR783 bit-exact 7.83 Hz toolkit")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("bits"); p.add_argument("value", nargs="?", default="7.83"); p.set_defaults(fn=cmd_bits)
    p = sub.add_parser("phase"); p.add_argument("--p", type=int, default=783); p.add_argument("--q", type=int, default=100)
    p.add_argument("--t0", type=int, default=0); p.add_argument("--t", default="now"); p.set_defaults(fn=cmd_phase)
    p = sub.add_parser("code"); p.add_argument("--p", type=int, default=783); p.add_argument("--q", type=int, default=100)
    p.add_argument("--t0", type=int, required=True); p.add_argument("--mode", choices="IBM", default="I"); p.set_defaults(fn=cmd_code)
    p = sub.add_parser("tone"); p.add_argument("--mode", choices=wav.MODES, default="isochronic")
    p.add_argument("--seconds", type=float, default=60.0); p.add_argument("--fs", type=int, default=48000)
    p.add_argument("--freq", default="7.83"); p.add_argument("--carrier", default="200")
    p.add_argument("--amplitude", type=float, default=0.3); p.add_argument("--out", required=True); p.set_defaults(fn=cmd_tone)
    sub.add_parser("seal").set_defaults(fn=cmd_seal)
    sub.add_parser("verify").set_defaults(fn=cmd_verify)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
