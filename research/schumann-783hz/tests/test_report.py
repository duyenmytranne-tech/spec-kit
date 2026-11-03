"""Report integrity: citations, anchors, figures, and every quoted number vs results.json."""
from __future__ import annotations

import json
import re

from conftest import vn


def chapters(root):
    return {p.name: p.read_text(encoding="utf-8") for p in sorted((root / "report" / "chapters").glob("*.md"))}


def test_reference_list_is_complete_and_cited(root):
    ch = chapters(root)
    refs_text = ch["08-tai-lieu-tham-khao.md"]
    numbers = [int(n) for n in re.findall(r"^\\\[(\d+)\\\] ", refs_text, flags=re.M)]
    assert numbers == list(range(1, len(numbers) + 1)) and len(numbers) == 53
    body = "\n".join(t for name, t in ch.items() if name != "08-tai-lieu-tham-khao.md")
    cited = {int(n) for n in re.findall(r"\[(\d{1,2})\]", body)}
    assert cited <= set(numbers), sorted(cited - set(numbers))
    assert set(numbers) <= cited, f"never cited: {sorted(set(numbers) - cited)}"


def test_every_reference_has_verification_status(root):
    refs_text = chapters(root)["08-tai-lieu-tham-khao.md"]
    lines = re.findall(r"^\\\[\d+\\\] .*$", refs_text, flags=re.M)
    assert len(lines) == 53
    for line in lines:
        assert re.search(r"\[V[123]", line), line


def test_internal_links_and_figures(root, report_text):
    anchors = set(re.findall(r'<a id="([A-Za-z0-9-]+)"></a>', report_text))
    links = set(re.findall(r"\]\(#([A-Za-z0-9-]+)\)", report_text))
    assert links and links <= anchors, sorted(links - anchors)
    figs = re.findall(r"\]\((figures/[^)]+)\)", report_text)
    assert len(figs) == 9
    for f in figs:
        assert (root / "report" / f).exists(), f


def test_no_placeholders(report_text):
    for bad in ("TODO", "TBD", "[NEEDS CLARIFICATION", "lorem ipsum", "XX "):
        assert bad not in report_text


def test_quoted_numbers_match_results(results, report_text, kb):
    r = results
    b = r["bits"]["ieee754"]
    s, ph, ml = r["synth"], r["physics"], r["ml"]["metrics"]
    dds48 = next(d for d in s["dds"] if d["f_clk_hz"] == 48000 and d["accumulator_bits"] == 32)
    facts = [
        b["binary16"]["hex"], b["binary32"]["hex"], b["binary64"]["hex"],
        vn(b["binary32"]["exact_value"]), vn(b["binary64"]["exact_value"]), b["binary32"]["fraction"],
        str(dds48["tuning_word"]), dds48["tuning_word_hex"], vn(dds48["f_out_hz"]),
        str(s["timer1"]["best"]["ocr"]), s["timer1"]["best"]["ocr_hex"], vn(s["timer1"]["best"]["f_out_hz"]),
        "+" + vn(s["timer1"]["best"]["error_ppm"]) + " ppm", s["timer1"]["registers"]["TCCR1B"],
        s["display"]["sampled_sinusoid_60hz_hex"], vn(s["audio"][0]["samples_per_cycle"]),
        vn(s["max_offset_10deg_ms"]) + " ms", s["sync_code_example"]["code"],
        vn(ph["icnirp"]["B_public_uT"]) + " µT", ph["icnirp"]["B_occupational_uT"] + " µT",
        vn(ph["icnirp"]["E_cns_public_mV_per_m"]) + " mV/m",
        vn(ph["cavity"]["rows"][0]["ideal_hz"]), vn(ph["cavity"]["rows"][0]["ratio"]),
        vn(ph["cavity"]["wavelength_over_circumference"]), vn(ph["cavity"]["c_over_2pi_a_hz"]),
        "38 288 km", "40 030 km", str(ph["cavity"]["fft_bin_10min"]["bin_index"]),
        vn(ph["magnetometer"]["detect_1lsb_cm"]) + " cm", vn(ph["magnetometer"]["detect_10lsb_cm"]) + " cm",
        vn(ph["magnetometer"]["bits_to_resolve_1pT_full_scale"]), "6,667·10⁻⁶",
        "61,9 nT", "62,8 pT", vn(ph["adc"][2]["ideal_snr_db"]),
        vn(f'{ml["hybrid"]["all"]["mae_hz"]:.4f}'), vn(f'{ml["argmax"]["all"]["mae_hz"]:.4f}'),
        vn(f'{ml["argmax"]["interference"]["mae_hz"]:.4f}'), vn(f'{ml["lm"]["interference"]["rmse_hz"]:.4f}'),
        vn(f'{ml["argmax"]["interference"]["fail_rate_gt_0_2hz"] * 100:.2f}') + " %",
        vn(f'{float(s["harmonics"]["0.5"]["fundamental_power_fraction"]) * 100:.2f}') + " %",
        vn(f'{float(s["harmonics"]["0.1"]["fundamental_power_fraction"]) * 100:.2f}') + " %",
        r["secded"]["binary64_secded_72_64"]["codeword_hex"], r["secded"]["ocr1a_secded_22_16"]["codeword_hex"],
        r["integrity"]["chain_hashes"][0], r["integrity"]["chain_hashes"][1],
        vn(s["phase_vectors"][1]["phase_deg"]) + "°", str(s["phase_vectors"][1]["phase_num"]),
        f'{len(kb["intents"])} chủ đề', "44/44",
    ]
    missing = [f for f in facts if f not in report_text]
    assert not missing, missing


def test_kb_answers_match_results(results, kb):
    text = json.dumps(kb, ensure_ascii=False)
    for fact in ("652,4 µT", "6,667·10⁻⁶ LSB", "0,0299 Hz", "0,3283 Hz", "700617", "15963", "3,548 ms",
                 "7,42 cm", "3,33 cm", "0x40FA8F5C", "0x401F51EB851EB852", "61,9 nT", "62,8 pT", "10,59 Hz"):
        assert fact in text, fact
    for it in kb["intents"]:
        assert it["grade"] in "ABCD" and all(1 <= n <= 53 for n in it["refs"]), it["id"]
