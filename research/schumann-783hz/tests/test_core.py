"""Bit-level core: IEEE 754, DDS, AVR Timer1, phase, PRNG, WAV, CLI."""
from __future__ import annotations

import struct
import subprocess
import sys
from fractions import Fraction

import pytest

from sr783 import bits, physics, prng, synth, wav

F = Fraction(783, 100)


def test_ieee754_known_patterns():
    rep = bits.representations("7.83")["ieee754"]
    assert rep["binary16"]["hex"] == "0x47D4" and rep["binary16"]["exact_value"] == "7.828125"
    assert rep["binary32"]["hex"] == "0x40FA8F5C"
    assert rep["binary32"]["exact_value"] == "7.8299999237060546875"
    assert rep["binary64"]["hex"] == "0x401F51EB851EB852"
    assert rep["binary64"]["exact_value"] == "7.8300000000000000710542735760100185871124267578125"
    # independent check against the C library through struct
    assert struct.pack(">f", 7.83).hex().upper() == "40FA8F5C"
    assert struct.pack(">d", 7.83).hex().upper() == "401F51EB851EB852"


def test_fixed_point_and_bcd():
    rep = bits.representations("7.83")
    assert rep["fixed_point"]["Q16.16"]["raw"] == 513147
    assert rep["fixed_point"]["Q8.8"]["hex"] == "0x07D4"
    assert rep["bcd"]["nibbles"] == "0111 1000 0011"


@pytest.mark.parametrize("fclk,n,word", [(48000, 32, 700617), (44100, 32, 762576), (96000, 32, 350308),
                                         (16_000_000, 32, 2102), (16_000_000, 48, 137746817)])
def test_dds_tuning_words(fclk, n, word):
    d = synth.dds(F, fclk, n)
    assert d["tuning_word"] == word
    # the reported f_out is the exact rational word*fclk/2^N rounded to 15 decimals
    assert abs(Fraction(d["f_out_hz"]) - Fraction(word * fclk, 1 << n)) <= Fraction(1, 2 * 10**15)


def test_dds_round_half_even_is_optimal():
    for fclk, n in ((48000, 32), (16_000_000, 32)):
        w = synth.dds(F, fclk, n)["tuning_word"]
        err = abs(Fraction(w * fclk, 1 << n) - F)
        assert err <= abs(Fraction((w + 1) * fclk, 1 << n) - F)
        assert err <= abs(Fraction((w - 1) * fclk, 1 << n) - F)


def test_avr_timer1():
    t = synth.avr_timer1_ctc(F)
    assert t["best"] == {"prescaler": 64, "ocr": 15963, "ocr_hex": "0x3E5B", "f_out_hz": "7.830117765", "error_ppm": "15.040"}
    assert t["registers"]["TCCR1A"] == "0x40" and t["registers"]["TCCR1B"] == "0x0B"
    assert Fraction(16_000_000, 2 * 64 * (1 + 15963)) == Fraction(16_000_000, 2 * 256 * (1 + 3990))


def test_phase_vectors_and_offsets():
    assert synth.phase_units(783, 100, 1_793_664_012_345) == (66135, 100000)
    assert synth.phase_vector(783, 100, 1_793_664_000_127, 1_793_664_000_000)["phase_deg"] == "357.9876"
    assert synth.max_offset_for(10) == "3.548"
    # equivalent fractions give identical phase
    a = synth.phase_units(7792, 1000, 1_793_664_012_345)
    b = synth.phase_units(974, 125, 1_793_664_012_345)
    assert Fraction(*a) == Fraction(*b)


def test_display_and_audio_tables():
    d = synth.display_frames()
    assert d["sampled_sinusoid_60hz_hex"] == "80 DD FF D0 6E 17 03 3E A2 F1 F7 B2 4C 07 0F 5E"
    a = {r["fs_hz"]: r for r in synth.audio_table()}
    assert a[48000]["loop_isochronic_samples"] == 4_800_000 and a[44100]["samples_per_cycle"] == "5632.183908"


def test_physics_values():
    cav = physics.cavity_modes()
    assert cav["rows"][0]["ideal_hz"] == "10.59" and cav["wavelength_km"] == "38288"
    assert physics.icnirp_2010()["B_public_uT"] == "652.4"
    mag = physics.magnetometer()
    assert (mag["detect_1lsb_cm"], mag["detect_10lsb_cm"], mag["sr_in_lsb"]) == ("7.42", "3.33", "6.667e-06")


def test_splitmix64_known_answer():
    g = prng.SplitMix64(0)
    assert g.next_u64() == 0xE220A8397B1DCDAF
    assert g.next_u64() == 0x6E789E6AA1B965F4


def test_wav_is_deterministic_and_safe():
    a = wav.wav_bytes(wav.synth("isochronic", 0.2, 48000))
    b = wav.wav_bytes(wav.synth("isochronic", 0.2, 48000))
    assert a == b and a[:4] == b"RIFF" and a[8:12] == b"WAVE"
    assert struct.unpack("<I", a[40:44])[0] == int(0.2 * 48000) * 4
    with pytest.raises(ValueError):
        wav.synth("isochronic", 0.1, 48000, amplitude=0.9)


def test_cli_commands(root):
    out = subprocess.run([sys.executable, "-m", "sr783", "code", "--t0", "1793664000000", "--mode", "I"],
                         cwd=root, capture_output=True, text=True, check=True).stdout.strip()
    assert out == "SR783-1-783-100-1793664000000-I-9336D787"
    out = subprocess.run([sys.executable, "-m", "sr783", "bits", "7.83"], cwd=root, capture_output=True,
                         text=True, check=True).stdout
    assert "0x40FA8F5C" in out and "700617" in out
