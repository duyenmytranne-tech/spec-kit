import collections
import datetime as dt

from g4runner import apps, capacity, jobs


def test_registry_shape_and_counts():
    assert [a["id"] for a in apps.APPS] == [f"ud{i:02d}" for i in range(1, 22)]
    assert collections.Counter(a["s"] for a in apps.APPS) == {"ok": 13, "cp": 4, "ex": 3, "out": 1}
    # the report's "Chủ đạo ở" column: solid dots per function group
    solid = [sum(a["cn"][i] == "●" for a in apps.APPS) for i in range(8)]
    assert solid == [12, 15, 20, 12, 9, 18, 2, 19]
    assert all(len(a["cn"]) == 8 and set(a["cn"]) <= set("●○·") for a in apps.APPS)


def test_profiles_follow_the_stated_rule():
    prof = collections.Counter(apps.derive_profile(a) for a in apps.APPS)
    assert prof == {"cpu_gpu": 6, "cpu_ab": 6, "cpu": 5, "coupled": 3, "none": 1}
    # coupled exactly where runtime coupling (preCICE) is part of the chain
    assert {a["id"] for a in apps.APPS if apps.derive_profile(a) == "coupled"} == {"ud03", "ud11", "ud13"}
    for a in apps.APPS:
        if apps.derive_profile(a) == "coupled":
            assert a["cn"][4] == "●", "coupling apps must use CN5"
        if a["physics"]:
            assert a["physics"] in capacity.PHYSICS


def test_stages_mirror_function_chain():
    for a in apps.APPS:
        st = apps.stages_for(a)
        if a["s"] == "out":
            assert st == []
            continue
        assert st[0] == "TT0"
        assert st[1:] == [f"TT{i + 1}" for i, c in enumerate(a["cn"]) if c != "·"]


def test_every_template_is_a_valid_job():
    now = dt.datetime(2026, 11, 2, tzinfo=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    n = 0
    for a in apps.APPS:
        if not a["template"]:
            assert apps.derive_profile(a) in ("coupled", "none")
            continue
        job = apps.job_from_template(a["id"], f"{a['id']}-test", now)
        assert jobs.validate_job(job) == [], (a["id"], jobs.validate_job(job))
        assert job["source"]["tutorial"] == a["tutorial"]
        n += 1
    assert n == 17


def test_gpu_ready_apps_are_estimated_as_gpu_capable():
    for a in apps.APPS:
        if apps.derive_profile(a) == "cpu_gpu":
            e = capacity.estimate({"physics": a["physics"], "cells_m": 20.0, "iterations": 20000, "ogl_build_h": 0.0})
            assert e["gpu_allowed"] and e["use_gpu"], a["id"]
        if apps.derive_profile(a) == "cpu" and a["physics"] in ("particles_dsmc", "electrostatic"):
            assert capacity.estimate({"physics": a["physics"]})["gpu_allowed"] is False
