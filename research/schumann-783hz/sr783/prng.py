"""SplitMix64 (Steele, Lea & Flood 2014) - integer-only, bit-exact everywhere.

Known answer: seed 0 -> 0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4, ...
"""
from __future__ import annotations

import math

MASK64 = (1 << 64) - 1


class SplitMix64:
    def __init__(self, seed: int):
        self.state = seed & MASK64

    def next_u64(self) -> int:
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK64
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
        return z ^ (z >> 31)

    def uniform(self) -> float:
        """Uniform in [0, 1) with 53 random bits (exact dyadic rational)."""
        return (self.next_u64() >> 11) * (1.0 / (1 << 53))

    def range(self, lo: float, hi: float) -> float:
        return lo + (hi - lo) * self.uniform()

    def normal(self) -> float:
        """Standard normal via Box-Muller (cosine branch only)."""
        u1 = 1.0 - self.uniform()            # (0, 1]
        u2 = self.uniform()
        return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
