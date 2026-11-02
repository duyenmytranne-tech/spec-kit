import math

from g4runner import capacity


def test_reference_case_numbers():
    e = capacity.estimate({})  # 10 M cells, incompressible RANS, 2000 iterations on the default G4 shape
    assert e["ranks"] == 24 and e["cores_per_job"] == 24 and e["concurrent"] == 1
    assert e["ram_need_gb"] == 12.0 and e["ram_fit"]
    assert e["cells_max_m"] == 124.7          # 176 GB x 0.85 / 1.2 kB
    assert e["t_iter_cpu_s"] == 0.8333        # 1e7 x 2 us / 24
    s_p = (1597.0 * 0.6) / (144.0 * 0.6)
    overhead = (1e7 * 72.0 * 1.0 / 50e9) / (1e7 * 2e-6 / 24)
    speedup = 1.0 / ((1 - 0.45) + 0.45 / s_p + overhead)
    assert e["s_pressure"] == math.floor(s_p * 100 + 0.5) / 100
    assert abs(e["raw"]["speedup"] - speedup) < 1e-15
    assert e["use_gpu"] is False, "0.4 h plugin build every session outweighs the gain for 0.46 h of work"


def test_gpu_pays_off_for_long_runs_or_prebuilt_plugin():
    assert capacity.estimate({"iterations": 20000})["use_gpu"] is True
    assert capacity.estimate({"ogl_build_h": 0.0})["use_gpu"] is True


def test_parallel_build_and_switch_hides_most_of_the_build():
    e = capacity.estimate({})                        # 10 M cells x 2000, first job of the session
    T_c, S = e["raw"]["t_iter_cpu"] * 2000 / 3600, e["raw"]["speedup"]
    expect = 0.4 + (T_c - 0.85 * 0.4) / S + 0.02     # build 0.4 h at 85 % CPU speed, then GPU
    assert abs(e["raw"]["hours_par"] - expect) < 1e-12
    assert (e["hours_cpu"], e["hours_gpu"], e["hours_par"]) == (0.463, 0.681, 0.495)
    assert e["use_gpu"] is False                      # first short job: CPU still 7 % ahead
    second = capacity.estimate({"ogl_ready": True})  # every later job of the session
    assert second["hours_par"] == 0.301 and second["use_gpu"] is True
    big = capacity.estimate({"cells_m": 20.0, "iterations": 20000.0})
    assert big["hours_par"] < big["hours_gpu"] < big["hours_cpu"]
    short = capacity.estimate({"cells_m": 0.5, "iterations": 100.0})
    assert short["hours_par"] == round(short["raw"]["t_iter_cpu"] * 100 / 3600 / 0.85, 3)  # ends during the build
    seq = capacity.estimate({"ogl_overlap": False})
    assert seq["hours_par"] == seq["hours_gpu"]


def test_sliding_mesh_and_particles_never_use_gpu():
    for inp in ({"ami": True}, {"physics": "particles_dsmc"}):
        e = capacity.estimate(dict(inp, iterations=1e6, ogl_build_h=0.0))
        assert e["use_gpu"] is False and e["speedup"] == 1.0


def test_small_mesh_limits_ranks():
    e = capacity.estimate({"cells_m": 0.05})
    assert e["ranks"] == 5 and e["cells_per_rank"] == 10000.0


def test_variants_pack_the_node_and_ram_caps_them():
    e = capacity.estimate({"variants": 6, "cells_m": 1.0})
    assert e["concurrent"] == 6 and e["cores_per_job"] == 4 and e["ranks"] == 4
    big = capacity.estimate({"variants": 6, "cells_m": 60.0})
    assert big["concurrent"] == 2  # 2 x 72 GB fit in 150 GB, 3 would not


def test_session_fit_flag():
    assert capacity.estimate({"iterations": 1e6})["fits_session"] is False
