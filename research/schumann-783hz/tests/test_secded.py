"""Hamming SECDED: exhaustive and randomised fault injection."""
from __future__ import annotations

import itertools

import pytest

from sr783 import prng, secded


def test_parameters():
    assert (secded.SECDED_8_4.total_bits, secded.SECDED_22_16.total_bits, secded.SECDED_72_64.total_bits) == (8, 22, 72)


def test_secded_8_4_exhaustive():
    c = secded.SECDED_8_4
    for data in range(16):
        cw = c.encode(data)
        assert c.decode(cw) == {"status": "ok", "data": data, "position": None}
        for i in range(8):
            assert c.decode(cw ^ (1 << i)) == {"status": "corrected", "data": data, "position": i}
        for i, j in itertools.combinations(range(8), 2):
            assert c.decode(cw ^ (1 << i) ^ (1 << j))["status"] == "double"


@pytest.mark.parametrize("code", [secded.SECDED_22_16, secded.SECDED_72_64])
def test_secded_random_words(code):
    g = prng.SplitMix64(72)
    for _ in range(40):
        data = g.next_u64() & ((1 << code.k) - 1)
        cw = code.encode(data)
        assert code.decode(cw)["status"] == "ok"
        for i in range(code.total_bits):
            r = code.decode(cw ^ (1 << i))
            assert r["status"] == "corrected" and r["data"] == data and r["position"] == i
        for _ in range(60):
            i = g.next_u64() % code.total_bits
            j = (i + 1 + g.next_u64() % (code.total_bits - 1)) % code.total_bits
            assert code.decode(cw ^ (1 << i) ^ (1 << j))["status"] == "double"


def test_protect_and_recover_root_hash():
    blob = bytes(range(32))
    lines = secded.protect_bytes(blob)
    assert len(lines) == 4 and all(len(x) == 18 for x in lines)
    assert secded.recover_bytes(lines)["bytes"] == blob
    for w in range(4):
        for b in range(72):
            damaged = list(lines)
            damaged[w] = format(int(damaged[w], 16) ^ (1 << b), "018X")
            rec = secded.recover_bytes(damaged)
            assert rec["ok"] and rec["bytes"] == blob
    damaged = list(lines)
    damaged[2] = format(int(damaged[2], 16) ^ 0b101, "018X")
    assert not secded.recover_bytes(damaged)["ok"]


def test_results_fault_injection_summary(results):
    fi = results["secded"]["fault_injection"]
    assert fi["72_64"] == {"codeword_bits": 72, "single_flips": 72, "single_corrected": True,
                           "double_flips": 2556, "double_detected": True}
    assert results["secded"]["binary64_secded_72_64"]["codeword_hex"] == "0x410FA8F5C247AE0A32"
