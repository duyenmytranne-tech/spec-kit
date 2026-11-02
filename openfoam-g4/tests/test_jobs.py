import copy

import pytest

from g4runner import jobs

GOOD = {
    "schema": 1,
    "id": "pitz-20261102T1430Z-abc123",
    "app": "ud01",
    "source": {"case": "cases/pitzDaily"},
    "manifest": {"algo": "sha256", "root": "a" * 64, "files": [], "count": 0, "bytes": 0},
    "np": "auto",
    "gpu": "auto",
    "set": [{"file": "system/controlDict", "entry": "endTime", "value": "500"},
            {"file": "0/U", "entry": "boundaryField/inlet/value", "value": "uniform (10 0 0)"},
            {"file": "system/fvSolution", "entry": 'solvers/"(U|k|omega)"/relTol', "value": 0.1}],
    "variants": [{"name": "U10", "set": []}, {"name": "U20", "set": []}],
    "kpi": [{"name": "Cd", "path": "postProcessing/forceCoeffs/0/forceCoeffs.dat", "column": "Cd",
             "reduce": "mean_last", "n": 100},
            {"name": "Tmax", "path": "postProcessing/cellMax(T)/0/volFieldValue.dat", "column": 1}],
    "keep_times": 2,
    "max_hours": 23,
}


def test_good_job_passes():
    assert jobs.validate_job(GOOD) == []


def test_tutorial_job_needs_no_manifest():
    j = {"schema": 1, "id": "t1", "source": {"tutorial": "incompressibleFluid/pitzDailySteady"}}
    assert jobs.validate_job(j) == []


@pytest.mark.parametrize(
    "mutate, needle",
    [
        (lambda j: j["source"].update(case="../etc"), "source.case"),
        (lambda j: j["source"].update(case="/abs/path"), "source.case"),
        (lambda j: j["set"].append({"file": "Allrun", "entry": "x", "value": "1"}), "set[3].file"),
        (lambda j: j["set"].append({"file": "system/controlDict", "entry": "a b", "value": "1"}), "set[3].entry"),
        (lambda j: j["set"].append({"file": "system/controlDict", "entry": "x", "value": "#codeStream"}), "forbidden"),
        (lambda j: j["set"].append({"file": "system/controlDict", "entry": "x", "value": "$p"}), "forbidden"),
        (lambda j: j["set"].append({"file": "system/controlDict", "entry": "x", "value": "1; libs (x)"}), "forbidden"),
        (lambda j: j["set"].append({"file": "system/controlDict", "entry": "x", "value": "a\nb"}), "forbidden"),
        (lambda j: j.update(np=0), "np"),
        (lambda j: j.update(gpu="maybe"), "gpu"),
        (lambda j: j.update(extra=1), "unknown keys"),
        (lambda j: j.update(schema=2), "schema"),
        (lambda j: j.update(app="ud22"), "app"),
        (lambda j: j["kpi"].append({"name": "x", "path": "constant/x.dat", "column": 1}), "postProcessing"),
        (lambda j: j["variants"].append({"name": "U10"}), "unique"),
        (lambda j: j.update(max_hours=48), "max_hours"),
        (lambda j: j.update(id="bad id"), "id"),
        (lambda j: j.pop("manifest"), "manifest"),
    ],
)
def test_rejections(mutate, needle):
    j = copy.deepcopy(GOOD)
    mutate(j)
    errs = jobs.validate_job(j)
    assert errs and any(needle in e for e in errs), errs


def test_new_job_id_is_clean():
    import datetime as dt

    jid = jobs.new_job_id("my case/π", "abcdef0123", dt.datetime(2026, 11, 2, 14, 30, tzinfo=dt.timezone.utc))
    assert jid == "my-case-20261102T1430Z-abcdef"
    assert jobs.ID_RE.match(jid)


def test_load_active_filters_bad_ids(tmp_path):
    p = tmp_path / "active.json"
    p.write_text('{"schema":1,"active":["ok-1","bad id",3,"ok_2"]}')
    assert jobs.load_active(str(p)) == ["ok-1", "ok_2"]
    assert jobs.load_active(str(tmp_path / "missing.json")) == []
