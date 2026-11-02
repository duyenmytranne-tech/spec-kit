from g4runner import plan
from g4runner.foam import decompose_body, split3

HW_GPU = {
    "cpu": {"physical": 24, "logical": 48, "threads_per_core": 2, "triad_GBs": 150.0},
    "mem": {"available": 170e9, "total": 180e9, "swap_total": 0},
    "gpu": {"present": True, "healthy": True, "nvcc_version": "12.8", "nvcc": "/usr/local/cuda/bin/nvcc",
            "gpus": [{"memory.total": 97887.0, "compute_cap": "12.0"}], "bench": {"d2d_GBs": 1450.0, "h2d_GBs": 52.0}},
}
FEATS = {"physics": "incompressible_rans", "ami": False, "multi_region": False}


def test_gpu_rules_in_order():
    big = 20_000_000
    long_run = {"iterations": 20000, "c_cell_us": 2.0}
    assert plan.gpu_decision(HW_GPU, FEATS, big, {"gpu": "off"}, True)["mode"] == "off"
    nogpu = dict(HW_GPU, gpu={"present": False})
    assert plan.gpu_decision(nogpu, FEATS, big, {}, True)["mode"] == "off"
    sick = dict(HW_GPU, gpu=dict(HW_GPU["gpu"], healthy=False, reason="uncorrectable ECC"))
    assert "not healthy" in plan.gpu_decision(sick, FEATS, big, {}, True)["reasons"][0]
    assert plan.gpu_decision(HW_GPU, dict(FEATS, ami=True), big, {}, True)["mode"] == "off"
    assert plan.gpu_decision(HW_GPU, dict(FEATS, physics="particles_dsmc"), big, {}, True)["mode"] == "off"
    assert plan.gpu_decision(HW_GPU, FEATS, 100_000, {}, True, long_run)["mode"] == "off"
    assert plan.gpu_decision(HW_GPU, FEATS, big, {}, True, long_run)["mode"] == "ab"
    assert plan.gpu_decision(HW_GPU, FEATS, big, {"gpu": "on"}, False)["mode"] == "on"


def test_cpu_sets_use_primary_threads_and_never_overlap():
    groups = [[0, 24], [1, 25], [2, 26], [3, 27]]
    assert plan.cpu_sets(2, 2, groups) == ["0,1", "2,3"]


def test_decide_ranks():
    assert plan.decide_ranks(HW_GPU, None, {}) == 24
    assert plan.decide_ranks(HW_GPU, 50_000, {}) == 5
    assert plan.decide_ranks(HW_GPU, 10**8, {"np": 64}) == 48  # capped at logical CPUs


def test_ogl_entries_and_pressure_fields():
    e = plan.ogl_solver_entries("p", 24)
    assert e["solvers/p/solver"] == "GKOCG" and e["solvers/p/executor"] == "cuda" and e["solvers/p/ranksPerGPU"] == "24"
    assert plan.pick_pressure_fields(["p", "U", "p_rgh", "pFinal", "p_rghFinal", "pcorr"]) == ["p", "p_rgh", "pFinal", "p_rghFinal"]


def test_decomposition_dictionary_per_branch():
    assert "decomposer scotch;" in decompose_body(24, "scotch", "foundation")
    assert "method scotch;" in decompose_body(24, "scotch", "opencfd")
    assert split3(24) == [4, 3, 2] and split3(7) == [7, 1, 1]
    assert "n (4 3 2);" in decompose_body(24, "hierarchical", "opencfd")
