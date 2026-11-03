"""Bit-exact 16-bit PCM WAV synthesis of 7.83 Hz rhythm sessions.

Phase is computed per sample with integer arithmetic,
    phase_n = (num * n) mod (den * fs) / (den * fs)   for f = num/den Hz,
so a session never drifts, any sample can be computed independently, and
two devices that start from the same epoch produce the same waveform.
Samples are quantised with round-half-up (floor(x * 32767 + 0.5)).
"""
from __future__ import annotations

import math
import struct
from fractions import Fraction

MODES = ("isochronic", "binaural", "monaural")


def _phase(f: Fraction, n: int, fs: int) -> float:
    mod = f.denominator * fs
    return ((f.numerator * n) % mod) / mod


def _q16(x: float) -> int:
    return max(-32768, min(32767, math.floor(x * 32767 + 0.5)))


def synth(mode: str = "isochronic", seconds: float = 10.0, fs: int = 48000,
          beat: Fraction = Fraction(783, 100), carrier: Fraction = Fraction(200),
          amplitude: float = 0.3, fade_s: float = 3.0) -> bytes:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    if not 0 < amplitude <= 0.5:
        raise ValueError("amplitude is capped at 0.5 (-6 dBFS) for hearing safety")
    total = int(round(seconds * fs))
    fade = max(1, int(round(fade_s * fs)))
    upper = carrier + beat
    out = bytearray()
    tau = 2 * math.pi
    for n in range(total):
        g = amplitude * min(1.0, n / fade, (total - 1 - n) / fade)
        if mode == "isochronic":
            env = 0.5 - 0.5 * math.cos(tau * _phase(beat, n, fs))       # raised cosine, 0..1
            v = g * env * math.sin(tau * _phase(carrier, n, fs))
            left = right = v
        elif mode == "binaural":
            left = g * math.sin(tau * _phase(carrier, n, fs))
            right = g * math.sin(tau * _phase(upper, n, fs))
        else:
            v = 0.5 * g * (math.sin(tau * _phase(carrier, n, fs)) + math.sin(tau * _phase(upper, n, fs)))
            left = right = v
        out += struct.pack("<hh", _q16(left), _q16(right))
    return bytes(out)


def wav_bytes(pcm: bytes, fs: int = 48000, channels: int = 2, bits: int = 16) -> bytes:
    block = channels * bits // 8
    header = b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, channels, fs, fs * block, block, bits)
    header += b"data" + struct.pack("<I", len(pcm))
    return header + pcm
