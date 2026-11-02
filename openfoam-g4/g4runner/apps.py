"""Application layer registry: the 21 applications of the report, linked to execution.

One source of truth for three layers:

* application (ud01..ud21) and its support level,
* function chain CN1..CN8 (``cn``: ● main, ○ auxiliary, · unused),
* execution on the G4: profile, physics model for the capacity estimate,
  bottleneck, a verified OpenFOAM 14 tutorial and a ready job template.

``tests/test_doc_parity.py`` checks the published HTML matrix against this
file cell by cell, so the report and the runner cannot drift apart.
Tutorial paths were checked against the OpenFOAM-14 source tree
(commit ee38504, 2026-10-26); "auto" means its Allrun uses only
allow-listed OpenFOAM tools before the solver (see ``allrun.py``).
"""

from __future__ import annotations

from typing import Dict, List, Optional

PROFILES = {
    "cpu_gpu": "CPU + GPU",
    "cpu_ab": "CPU, GPU thử A/B",
    "cpu": "CPU",
    "coupled": "Ghép nhiều chương trình",
    "none": "Không chạy",
}

_RPM = [60, 90, 120, 150, 180, 240]

APPS: List[Dict] = [
    {"id": "ud01", "name": "Khí động học thân xe", "s": "ok", "cn": "●○●●·●○●",
     "physics": "incompressible_rans", "coupled": False, "small": False, "rotating": False,
     "bottleneck": "Băng thông bộ nhớ khi giải áp suất trên lưới chục triệu ô",
     "g4": "snappyHexMesh và bộ giải trên mọi lõi vật lý; áp suất lên GPU nếu thử A/B nhanh hơn ≥ 10 %",
     "tutorial": "incompressibleFluid/motorBikeSteady", "auto": True,
     "template": {"source": {"tutorial": "incompressibleFluid/motorBikeSteady"},
                  "kpi": [{"name": "Cd", "path": "postProcessing/forceCoeffs/0/forceCoeffs.dat", "column": "Cd",
                           "reduce": "mean_last", "n": 100}]}},
    {"id": "ud02", "name": "Làm mát động cơ và điều hoà cabin", "s": "ok", "cn": "●●●○●●○●",
     "physics": "cht_multiregion", "coupled": False, "small": False, "rotating": False,
     "bottleneck": "Nhiều vùng chất lưu–rắn ghép nhiệt, bức xạ",
     "g4": "decomposePar -allRegions trên mọi lõi; GPU chỉ khi thử A/B thắng (đa vùng chưa kiểm chứng với OGL)",
     "tutorial": "multiRegion/CHT/heatedDuct", "auto": True,
     "template": {"source": {"tutorial": "multiRegion/CHT/heatedDuct"}}},
    {"id": "ud03", "name": "Cánh máy bay uốn và rung (FSI)", "s": "cp", "cn": "●○●●●●○●",
     "physics": "compressible", "coupled": True, "small": False, "rotating": False,
     "bottleneck": "Vòng lặp ghép OpenFOAM–CalculiX mỗi bước thời gian",
     "g4": "Chia lõi cho hai chương trình; preCICE chưa được bộ chạy tự động hoá",
     "tutorial": None, "auto": False, "template": None},
    {"id": "ud04", "name": "Tua-bin gió", "s": "ok", "cn": "●●●●·●○●",
     "physics": "incompressible_rans", "coupled": False, "small": False, "rotating": False,
     "bottleneck": "Miền địa hình lớn: băng thông bộ nhớ",
     "g4": "Như ud01; rotor lưới trượt (ghép không trùng lưới) thì bộ chạy tự tắt GPU",
     "tutorial": "incompressibleFluid/turbineSiting", "auto": True,
     "template": {"source": {"tutorial": "incompressibleFluid/turbineSiting"}}},
    {"id": "ud05", "name": "Phát tán khói bụi và chất ô nhiễm", "s": "ok", "cn": "○●●●·●○●",
     "physics": "incompressible_transient", "coupled": False, "small": False, "rotating": False,
     "bottleneck": "Miền khu vực lớn chạy theo thời gian: giải áp suất mỗi bước",
     "g4": "Mọi lõi + GPU cho áp suất khi đủ lớn; chất thụ động (scalarTransport) đi kèm trên CPU",
     "tutorial": "incompressibleFluid/pitzDailyScalarTransport", "auto": True,
     "template": {"source": {"tutorial": "incompressibleFluid/pitzDailyScalarTransport"}}},
    {"id": "ud06", "name": "Vết dầu loang trên biển", "s": "ex", "cn": "○●●○●●○●",
     "physics": "vof", "coupled": False, "small": False, "rotating": False,
     "bottleneck": "Bám mặt phân cách VoF chạy trên CPU; mô hình dầu phải tự viết",
     "g4": "Mọi lõi; GPU cho p_rgh chỉ khi thử A/B thắng",
     "tutorial": "incompressibleVoF/damBreakLaminar", "auto": True,
     "template": {"source": {"tutorial": "incompressibleVoF/damBreakLaminar"}}},
    {"id": "ud07", "name": "Bồn trộn công nghiệp", "s": "ok", "cn": "●●●●·●●●",
     "physics": "incompressible_transient", "coupled": False, "small": False, "rotating": True,
     "bottleneck": "Quét nhiều tốc độ khuấy",
     "g4": "6 biến thể tốc độ chạy cùng lúc, mỗi biến thể một bộ lõi riêng; MRF cho phép GPU, lưới trượt thì không",
     "tutorial": "incompressibleFluid/mixerVessel2DMRF", "auto": True,
     "template": {"source": {"tutorial": "incompressibleFluid/mixerVessel2DMRF"},
                  "variants": [{"name": f"omega{r}rpm", "set": [{"file": "constant/MRFProperties", "entry": "MRF/omega",
                                                                  "value": f"{r} [rpm]"}]} for r in _RPM]}},
    {"id": "ud08", "name": "Dòng chảy đa pha", "s": "ok", "cn": "○●●●·●○●",
     "physics": "multiphase_euler", "coupled": False, "small": False, "rotating": False,
     "bottleneck": "Ghép liên pha, bước thời gian nhỏ theo maxCo",
     "g4": "Mọi lõi; GPU cho áp suất chỉ khi thử A/B thắng",
     "tutorial": "multiphaseEuler/bubbleColumn", "auto": True,
     "template": {"source": {"tutorial": "multiphaseEuler/bubbleColumn"}}},
    {"id": "ud09", "name": "Cháy và phản ứng hoá học", "s": "ok", "cn": "○●●●·●·●",
     "physics": "reacting", "coupled": False, "small": False, "rotating": False,
     "bottleneck": "Tích phân hoá học (ODE) thuần CPU, FP64",
     "g4": "Mọi lõi chạy MPI; GPU không giúp vì áp suất chỉ chiếm khoảng 10 % thời gian",
     "tutorial": "multicomponentFluid/counterFlowFlame2D", "auto": True,
     "template": {"source": {"tutorial": "multicomponentFluid/counterFlowFlame2D"}}},
    {"id": "ud10", "name": "Gió lên toà nhà và cầu (tải tĩnh)", "s": "ok", "cn": "●●●○·●·●",
     "physics": "incompressible_rans", "coupled": False, "small": False, "rotating": False,
     "bottleneck": "Băng thông bộ nhớ khi giải áp suất",
     "g4": "Như ud01",
     "tutorial": "incompressibleFluid/windAroundBuildings", "auto": True,
     "template": {"source": {"tutorial": "incompressibleFluid/windAroundBuildings"}}},
    {"id": "ud11", "name": "Rung lắc, biến dạng nhà cao tầng và cầu treo (FSI)", "s": "cp", "cn": "○○●●●●·●",
     "physics": "incompressible_transient", "coupled": True, "small": False, "rotating": False,
     "bottleneck": "Vòng lặp ghép, bước thời gian nhỏ",
     "g4": "Như ud03",
     "tutorial": None, "auto": False, "template": None},
    {"id": "ud12", "name": "Dòng máu trong mạch cứng", "s": "ok", "cn": "●●●○·●○●",
     "physics": "incompressible_transient", "coupled": False, "small": False, "rotating": False,
     "bottleneck": "Giải áp suất mỗi bước nhân với nhiều chu kỳ tim",
     "g4": "Mọi lõi + GPU cho áp suất; ứng viên GPU tốt nhất vì chạy theo thời gian rất lâu",
     "tutorial": "incompressibleFluid/pitzDailyPulse", "auto": True,
     "template": {"source": {"tutorial": "incompressibleFluid/pitzDailyPulse"}}},
    {"id": "ud13", "name": "Thành mạch mềm và van tim", "s": "cp", "cn": "●●●●●●○●",
     "physics": "incompressible_transient", "coupled": True, "small": False, "rotating": False,
     "bottleneck": "Lưới biến dạng lớn cộng vòng lặp ghép",
     "g4": "Như ud03",
     "tutorial": None, "auto": False, "template": None},
    {"id": "ud14", "name": "Hô hấp và thuốc hít", "s": "ok", "cn": "●●●●·●○●",
     "physics": "incompressible_transient", "coupled": False, "small": False, "rotating": False,
     "bottleneck": "Áp suất (GPU được) cộng theo vết hạt Lagrangian (CPU)",
     "g4": "Mọi lõi + GPU cho áp suất; hạt chạy trên CPU",
     "tutorial": "incompressibleDenseParticleFluid/injectionChannel", "auto": True,
     "template": {"source": {"tutorial": "incompressibleDenseParticleFluid/injectionChannel"}}},
    {"id": "ud15", "name": "Lab-on-a-chip và vi lưu", "s": "ok", "cn": "●○●○○●○●",
     "physics": "incompressible_transient", "coupled": False, "small": True, "rotating": False,
     "bottleneck": "Lưới nhỏ: một ca không lấp đầy các lõi",
     "g4": "Quét nhiều biến thể cùng lúc, mỗi biến thể ≥ 4 lõi; GPU tắt vì lưới nhỏ",
     "tutorial": "incompressibleFluid/cavity", "auto": True,
     "template": {"source": {"tutorial": "incompressibleFluid/cavity"}}},
    {"id": "ud16", "name": "Khí loãng, kích thước nano", "s": "ok", "cn": "●●●●·●○●",
     "physics": "particles_dsmc", "coupled": False, "small": False, "rotating": False,
     "bottleneck": "Số hạt mô phỏng: CPU và RAM",
     "g4": "Mọi lõi chạy MPI; GPU không áp dụng (không có ma trận áp suất)",
     "tutorial": "legacy/lagrangian/dsmcFoam/wedge15Ma5", "auto": True,
     "template": {"source": {"tutorial": "legacy/lagrangian/dsmcFoam/wedge15Ma5"}}},
    {"id": "ud17", "name": "Khuếch tán và phản ứng sinh học", "s": "ex", "cn": "○●●○●●○●",
     "physics": "reacting", "coupled": False, "small": False, "rotating": False,
     "bottleneck": "Động học tự viết bằng C++ chạy trên CPU",
     "g4": "Mọi lõi; màng bán thấm có sẵn ở v14, động học sinh học vẫn phải viết thêm",
     "tutorial": "multicomponentFluid/membrane", "auto": True,
     "template": {"source": {"tutorial": "multicomponentFluid/membrane"}}},
    {"id": "ud18", "name": "Điện động học và plasma", "s": "ex", "cn": "○●●○●○○●",
     "physics": "electrostatic", "coupled": False, "small": True, "rotating": False,
     "bottleneck": "Bộ giải cổ điển (legacy) và mô hình tự viết",
     "g4": "CPU; quét nhiều biến thể nếu cần lấp đầy lõi",
     "tutorial": "legacy/electromagnetics/electrostaticFoam/chargedWire", "auto": True,
     "template": {"source": {"tutorial": "legacy/electromagnetics/electrostaticFoam/chargedWire"}}},
    {"id": "ud19", "name": "Cơ học lượng tử của electron", "s": "out", "cn": "········",
     "physics": None, "coupled": False, "small": False, "rotating": False,
     "bottleneck": "Không áp dụng", "g4": "Không chạy trên OpenFOAM",
     "tutorial": None, "auto": False, "template": None},
    {"id": "ud20", "name": "Kỹ xảo phim và game", "s": "cp", "cn": "○○●●●○●○",
     "physics": "vof", "coupled": False, "small": False, "rotating": False,
     "bottleneck": "Xuất khung hình; trái với chế độ không lưu",
     "g4": "Tính được trong RAM; khung hình chỉ lấy về được nếu bạn tự bật lưu ngoài bộ chạy",
     "tutorial": "incompressibleVoF/damBreakLaminar", "auto": True,
     "template": {"source": {"tutorial": "incompressibleVoF/damBreakLaminar"}}},
    {"id": "ud21", "name": "Tản nhiệt máy tính", "s": "ok", "cn": "●●●○●●○●",
     "physics": "cht_multiregion", "coupled": False, "small": False, "rotating": False,
     "bottleneck": "Nhiều vùng ghép nhiệt cộng quạt MRF",
     "g4": "Như ud02; circuitBoardCooling cần chuẩn bị lưới (Allmesh) trên Mac trước khi đẩy",
     "tutorial": "multiRegion/CHT/heatedDuct", "auto": True,
     "template": {"source": {"tutorial": "multiRegion/CHT/heatedDuct"}}},
]

BY_ID = {a["id"]: a for a in APPS}


def derive_profile(app: Dict) -> str:
    """The rule the report states; ``tests/test_apps.py`` checks every app follows it."""
    if app["s"] == "out" or app["physics"] is None:
        return "none"
    if app["coupled"]:
        return "coupled"
    if app["physics"] in ("particles_dsmc", "reacting", "electrostatic") or app["small"]:
        return "cpu"
    if app["physics"] in ("vof", "multiphase_euler", "cht_multiregion") or app["rotating"]:
        return "cpu_ab"
    return "cpu_gpu"


def profile(app_id: str) -> str:
    return derive_profile(BY_ID[app_id])


def stages_for(app: Dict) -> List[str]:
    """Execution stages TT0..TT8 an application uses: TT0 always, TTk when CNk is ● or ○."""
    if app["s"] == "out":
        return []
    return ["TT0"] + [f"TT{i + 1}" for i, c in enumerate(app["cn"]) if c in "●○"]


def job_from_template(app_id: str, job_id: str, created: str, extra: Optional[Dict] = None) -> Dict:
    app = BY_ID[app_id]
    if not app.get("template"):
        raise ValueError(f"{app_id} has no automatic template ({app['g4']})")
    job = {"schema": 1, "id": job_id, "created": created, "app": app_id, "title": app["name"],
           "np": "auto", "gpu": "auto", "branch": "foundation"}
    job.update(app["template"])
    if extra:
        job.update(extra)
    return job
