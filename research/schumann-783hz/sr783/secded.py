"""Generic extended Hamming code: SECDED (single-error-correct, double-error-detect).

Layout (identical in the JavaScript app):
  * positions 1..n hold the Hamming code (n = k + r, 2**r >= k + r + 1);
    parity bits sit at the powers of two, data bits fill the other positions
    in increasing order, data bit 0 (LSB) first;
  * position 0 holds the overall parity bit (even parity over positions 0..n);
  * the codeword is an integer whose bit i is position i.

Examples: k=4 -> (8,4); k=16 -> (22,16); k=64 -> (72,64).
"""
from __future__ import annotations


class Secded:
    def __init__(self, k: int):
        if k < 1:
            raise ValueError("k must be >= 1")
        r = 1
        while (1 << r) < k + r + 1:
            r += 1
        self.k, self.r, self.n = k, r, k + r
        self.total_bits = self.n + 1
        self.data_positions = [p for p in range(1, self.n + 1) if p & (p - 1)]
        assert len(self.data_positions) == k
        self.hex_digits = (self.total_bits + 3) // 4

    @property
    def name(self) -> str:
        return f"SECDED({self.total_bits},{self.k})"

    def encode(self, data: int) -> int:
        if not 0 <= data < (1 << self.k):
            raise ValueError("data out of range")
        cw = 0
        syndrome = 0
        for i, pos in enumerate(self.data_positions):
            if (data >> i) & 1:
                cw |= 1 << pos
                syndrome ^= pos
        for j in range(self.r):
            if (syndrome >> j) & 1:
                cw |= 1 << (1 << j)
        if bin(cw).count("1") & 1:
            cw |= 1                                # overall parity -> even
        return cw

    def syndrome(self, cw: int) -> int:
        s = 0
        x = cw >> 1
        pos = 1
        while x:
            if x & 1:
                s ^= pos
            x >>= 1
            pos += 1
        return s

    def decode(self, cw: int) -> dict:
        """Return {'status': ok|corrected|double|uncorrectable, 'data', 'position'}."""
        if cw >> self.total_bits:
            return {"status": "uncorrectable", "data": None, "position": None}
        s = self.syndrome(cw)
        parity = bin(cw).count("1") & 1
        position = None
        if parity == 0 and s == 0:
            status = "ok"
        elif parity == 1 and s <= self.n:
            position = s                           # s == 0 -> the overall parity bit
            cw ^= 1 << s
            status = "corrected"
        elif parity == 0:
            return {"status": "double", "data": None, "position": None}
        else:
            return {"status": "uncorrectable", "data": None, "position": None}
        data = 0
        for i, pos in enumerate(self.data_positions):
            if (cw >> pos) & 1:
                data |= 1 << i
        return {"status": status, "data": data, "position": position}

    def to_hex(self, cw: int) -> str:
        return format(cw, f"0{self.hex_digits}X")

    def from_hex(self, text: str) -> int:
        return int(text, 16)


SECDED_72_64 = Secded(64)
SECDED_22_16 = Secded(16)
SECDED_8_4 = Secded(4)


def protect_bytes(blob: bytes) -> list[str]:
    """Split bytes into 64-bit big-endian words and SECDED(72,64)-encode each."""
    if len(blob) % 8:
        raise ValueError("length must be a multiple of 8 bytes")
    words = [int.from_bytes(blob[i:i + 8], "big") for i in range(0, len(blob), 8)]
    return [SECDED_72_64.to_hex(SECDED_72_64.encode(w)) for w in words]


def recover_bytes(lines: list[str]) -> dict:
    """Decode SECDED(72,64) hex lines; correct single errors, report doubles."""
    out = b""
    report = []
    for i, line in enumerate(lines):
        res = SECDED_72_64.decode(SECDED_72_64.from_hex(line))
        report.append({"word": i, "status": res["status"], "position": res["position"]})
        if res["data"] is None:
            return {"ok": False, "bytes": None, "report": report}
        out += res["data"].to_bytes(8, "big")
    return {"ok": True, "bytes": out, "report": report}
