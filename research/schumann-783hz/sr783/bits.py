"""Exact bit-level representations of a decimal value such as 7.83.

Every conversion is done with rational arithmetic (fractions.Fraction) and
round-half-to-even, i.e. exactly as IEEE 754-2019 specifies for
roundTiesToEven, and is then cross-checked against the platform's own
`struct` packing. Nothing here depends on floating-point behaviour.
"""
from __future__ import annotations

import struct
from decimal import Decimal, localcontext
from fractions import Fraction

# name: (struct code, total bits, exponent bits, fraction bits)
IEEE_FORMATS = {
    "binary16": ("e", 16, 5, 10),
    "binary32": ("f", 32, 8, 23),
    "binary64": ("d", 64, 11, 52),
}


def frac_to_decimal(q: Fraction, digits: int = 80) -> Decimal:
    """Exact (or `digits`-significant) decimal value of a fraction."""
    with localcontext() as ctx:
        ctx.prec = digits
        return Decimal(q.numerator) / Decimal(q.denominator)


def dec_str(q: Fraction, places: int) -> str:
    """Fixed-point decimal string with `places` digits after the point."""
    with localcontext() as ctx:
        ctx.prec = 120
        d = Decimal(q.numerator) / Decimal(q.denominator)
        return format(d.quantize(Decimal(1).scaleb(-places)), "f")


def sci(q: Fraction | float, sig: int = 6) -> str:
    """Scientific notation with `sig` significant digits (stable text)."""
    if isinstance(q, Fraction):
        d = frac_to_decimal(q, 60)
    else:
        d = Decimal(repr(q))
    if d == 0:
        return "0"
    return format(d, f".{sig - 1}e")


def exact_ieee(value: Fraction, fmt: str) -> dict:
    """Round a positive rational to an IEEE 754 binary format exactly."""
    if value <= 0:
        raise ValueError("only positive normal values are needed here")
    code, nbits, ebits, mbits = IEEE_FORMATS[fmt]
    bias = (1 << (ebits - 1)) - 1
    e = value.numerator.bit_length() - value.denominator.bit_length()
    while Fraction(2) ** e > value:
        e -= 1
    while Fraction(2) ** (e + 1) <= value:
        e += 1
    m = round(value / Fraction(2) ** e * (1 << mbits))  # round-half-even
    if m == 1 << (mbits + 1):
        m >>= 1
        e += 1
    exp_field = e + bias
    if not 0 < exp_field < (1 << ebits) - 1:
        raise ValueError("value outside the normal range of " + fmt)
    frac_field = m - (1 << mbits)
    word = (exp_field << mbits) | frac_field
    represented = Fraction(m, 1 << mbits) * Fraction(2) ** e
    # Cross-check with the platform implementation (struct, C double -> fmt).
    platform = struct.unpack(">Q" if nbits == 64 else (">I" if nbits == 32 else ">H"),
                             struct.pack(">" + code, float(represented)))[0]
    if platform != word:
        raise AssertionError(f"exact {fmt} {word:#x} != platform {platform:#x}")
    err = represented - value
    bits = format(word, f"0{nbits}b")
    return {
        "format": fmt,
        "hex": "0x" + format(word, f"0{nbits // 4}X"),
        "bits": bits,
        "sign": bits[0],
        "exponent": bits[1:1 + ebits],
        "fraction": bits[1 + ebits:],
        "exponent_unbiased": e,
        "exact_value": format(frac_to_decimal(represented), "f").rstrip("0"),
        "abs_error": sci(err, 6),
        "rel_error_ppb": sci(err / value * 10**9, 6),
    }


def fixed_point(value: Fraction, frac_bits: int, total_bits: int) -> dict:
    """Unsigned Qm.n fixed point (round-half-even)."""
    raw = round(value * (1 << frac_bits))
    if raw >= 1 << total_bits:
        raise ValueError("overflow")
    represented = Fraction(raw, 1 << frac_bits)
    return {
        "q_format": f"Q{total_bits - frac_bits}.{frac_bits}",
        "raw": raw,
        "hex": "0x" + format(raw, f"0{total_bits // 4}X"),
        "exact_value": format(frac_to_decimal(represented), "f").rstrip("0"),
        "abs_error": sci(represented - value, 6),
    }


def bcd(text: str) -> dict:
    """Packed BCD of the digits of a decimal string ("7.83" -> 0111 1000 0011)."""
    digits = [c for c in text if c.isdigit()]
    groups = [format(int(c), "04b") for c in digits]
    return {"digits": "".join(digits), "nibbles": " ".join(groups),
            "hex": "0x" + "".join(format(int(c), "X") for c in digits)}


def representations(value_text: str = "7.83") -> dict:
    q = Fraction(Decimal(value_text))
    return {
        "value": value_text,
        "rational": f"{q.numerator}/{q.denominator}",
        "ieee754": {fmt: exact_ieee(q, fmt) for fmt in IEEE_FORMATS},
        "fixed_point": {
            "Q8.8": fixed_point(q, 8, 16),
            "Q16.16": fixed_point(q, 16, 32),
        },
        "bcd": bcd(value_text),
    }
