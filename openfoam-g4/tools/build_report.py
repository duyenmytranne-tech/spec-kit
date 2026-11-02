#!/usr/bin/env python3
"""Build the upgraded report (v2) from the original (v1) without deleting anything.

    python3 -I tools/build_report.py            # writes docs/OpenFOAM_chi_tiet.html
    python3 -I tools/build_report.py --artifact OUT.html   # page body only (for the Artifact publisher)

Every application row, card execution block and the capacity calculator come
from ``g4runner.apps`` and ``g4runner.capacity``; ``tests/test_doc_parity.py``
re-reads the output and checks it against those modules cell by cell.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys

HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HOME)

from g4runner import apps, capacity  # noqa: E402

#: shown in the acceptance table; tests/test_doc_parity.py asserts it equals the number of collected tests
NTESTS = 89

SRC = os.path.join(HOME, "docs", "source", "OpenFOAM_chi_tiet_v1.html")
OUT = os.path.join(HOME, "docs", "OpenFOAM_chi_tiet.html")
E = html.escape

CN_TITLES = {1: "Hình học và lưới", 2: "Điều kiện, vật liệu, khởi tạo", 3: "Vật lý và bộ giải",
             4: "Phương pháp số và song song", 5: "Ghép nối và mở rộng", 6: "Đo đạc và hậu xử lý",
             7: "Dữ liệu ra và tự động hoá", 8: "Kiểm chứng và hội tụ"}
TT_TITLES = {0: "Môi trường và toàn vẹn", 1: "Lưới", 2: "Điều kiện và khởi tạo", 3: "Bộ giải",
             4: "Song song và đại số tuyến tính", 5: "Ghép nối và mở rộng", 6: "Đo đạc",
             7: "Đầu ra và tự động hoá", 8: "Kiểm chứng và hội tụ"}
PF_CLASS = {"cpu_gpu": "pg", "cpu_ab": "pa", "cpu": "pc", "coupled": "pk", "none": "pn"}

# v14 names checked in the OpenFOAM-14 source tree (commit ee38504, 2026-10-26); per application card
V14_NOTES = {
    "ud01": "v14 dùng <code>surfaceFeatures</code> (đọc <code>surfaceFeaturesDict</code>); <code>surfaceFeatureExtract</code> ở v14 chỉ còn là script báo đã thay thế.",
    "ud02": "Biên <code>externalWallHeatFluxTemperature</code> ở v14 đổi tên thành <code>externalTemperature</code> (tên cũ vẫn được nhận).",
    "ud04": "v14 không còn <code>cyclicAMI</code>: vùng quay dùng ghép không trùng lưới (<code>nonConformalCyclic</code>, tạo bằng <code>createNonConformalCouples</code>). Biên gió là <code>atmosphericBoundaryLayerVelocity</code> (tên <code>atmBoundaryLayer…</code> không còn ở v14).",
    "ud05": "Họ biên khí quyển ở v14: <code>atmosphericBoundaryLayerVelocity</code>, <code>…TurbulentKineticEnergy</code>, <code>…TurbulentEpsilon</code>.",
    "ud07": "v14 thay <code>cyclicAMI</code> bằng ghép không trùng lưới; tutorial <code>mixerVesselAMI2D</code> ở v14 là <code>mixerVessel2D</code> (lưới trượt) và <code>mixerVessel2DMRF</code> (MRF).",
    "ud09": "v14 không có function object <code>fieldMinMax</code>: dùng <code>volFieldValue</code> với <code>operation max</code>, gói sẵn là <code>#includeFunc cellMax(T)</code>.",
    "ud10": "Họ biên khí quyển ở v14 là <code>atmosphericBoundaryLayer…</code>.",
    "ud15": "v14 thay <code>sample</code> bằng function object <code>sets</code> (gói sẵn <code>graphUniform</code>, <code>graphCell</code>).",
    "ud16": "<code>dsmcFoam</code> nằm trong nhóm legacy của v14; trường trung bình lấy bằng function object <code>dsmcFields</code> (không còn <code>dsmcFieldsCalc</code>).",
    "ud17": "v14 có sẵn biên màng bán thấm <code>semiPermeableBaffleMassFraction</code> (tutorial <code>multicomponentFluid/membrane</code>) cho thông lượng loài qua màng; động học sinh học vẫn phải viết thêm.",
    "ud18": "<code>electrostaticFoam</code> và <code>mhdFoam</code> nằm trong nhóm legacy của v14 (tutorial <code>chargedWire</code>, <code>hartmann</code>).",
    "ud21": "v14: <code>fieldMinMax</code> → <code>#includeFunc cellMax(T)</code>; vùng xốp là fvModel <code>porosityForce</code> (tên <code>explicitPorositySource</code> vẫn được nhận).",
}

V14_TABLE = [
    ("CN1", "surfaceFeatureExtract", "Đã thay bằng surfaceFeatures", "bin/surfaceFeatureExtract (script báo thay thế)", "đổi"),
    ("CN1", "topoSet", "Còn, xếp vào deprecated; có thêm createZones", "applications/utilities/deprecated/topoSet", "cũ"),
    ("CN1", "blockMesh, snappyHexMesh, extrudeMesh, mirrorMesh, refineMesh, splitMeshRegions, createPatch, renumberMesh, fluentMeshToFoam, gmshToFoam, ideasUnvToFoam", "Có", "applications/utilities/mesh/…", "có"),
    ("CN1", "snappyHexMesh, renumberMesh: -overwrite", "Ghi đè là mặc định (-noOverwrite để giữ)", "src/OpenFOAM/include/addNoOverwriteOption.H", "đổi"),
    ("CN2", "cyclicAMI", "Không còn; dùng ghép không trùng lưới nonConformalCyclic + createNonConformalCouples", "src/meshTools/nonConformal", "đổi"),
    ("CN2", "atmBoundaryLayerInletVelocity / K / Epsilon", "Không còn; atmosphericBoundaryLayerVelocity / TurbulentKineticEnergy / TurbulentEpsilon", "src/atmosphericModels/derivedFvPatchFields", "đổi"),
    ("CN2", "externalWallHeatFluxTemperature", "Đổi tên thành externalTemperature, tên cũ vẫn nhận", "…/externalTemperature/externalTemperatureFvPatchScalarField.C", "đổi"),
    ("CN2", "changeDictionary", "Còn, xếp vào deprecated (dùng foamDictionary)", "applications/utilities/deprecated/changeDictionary", "cũ"),
    ("CN2", "setFields, mapFields, potentialFoam, foamDictionary, fixedValue, inletOutlet, totalPressure, flowRateInletVelocity, nutkWallFunction, fan, codedFixedValue, codedMixed", "Có", "src/finiteVolume, applications/…", "có"),
    ("CN3", "Module incompressibleFluid, fluid, multicomponentFluid, multiphaseEuler, incompressibleVoF, solidDisplacement, incompressibleDriftFlux, incompressibleDenseParticleFluid, XiFluid, movingMesh, functions", "Có", "applications/modules/", "có"),
    ("CN3", "MRF, actuationDisk, rotorDisk, kEpsilon, kOmegaSST", "Có", "src/finiteVolume/cfdTools/general/MRF, src/fvModels", "có"),
    ("CN3", "vùng xốp (explicitPorositySource)", "fvModel porosityForce, tên cũ vẫn nhận", "src/fvModels/general/porosityForce", "đổi"),
    ("CN3", "dsmcFoam, mdFoam, electrostaticFoam, mhdFoam, icoFoam", "Có, trong nhóm legacy", "applications/legacy/", "cũ"),
    ("CN3", "chemFoam", "Có (không thấy tutorial cùng tên)", "applications/solvers/chemFoam", "có"),
    ("CN4", "decomposeParDict: method", "Từ khoá mới là decomposer (method vẫn nhận); distributor cho phân phối lại", "src/parallel/decompose/decompositionMethods", "đổi"),
    ("CN4", "decomposePar, reconstructPar, redistributePar, scotch, hierarchical, PCG, GAMG, smoothSolver", "Có", "src/OpenFOAM/matrices, src/parallel", "có"),
    ("CN5", "foamMultiRun, codedFixedValue, libs", "Có", "applications/solvers/foamMultiRun", "có"),
    ("CN6", "fieldMinMax", "Không còn; volFieldValue operation max (#includeFunc cellMax)", "etc/caseDicts/functions/volFieldValue/cellMax", "đổi"),
    ("CN6", "sample", "Không còn; function object sets (#includeFunc graphUniform…)", "src/sampling/sampledSet/sampledSets", "đổi"),
    ("CN6", "forces, forceCoeffs, probes, surfaces, fieldAverage, yPlus, wallShearStress, surfaceFieldValue, volFieldValue, foamPostProcess", "Có", "src/functionObjects, src/sampling", "có"),
    ("CN6", "dsmcFieldsCalc", "Function object dsmcFields", "src/lagrangian/functionObjects/dsmcFields", "đổi"),
    ("CN7", "foamToVTK, foamToEnsight, foamListTimes, foamCleanTutorials, foamDictionary", "Có", "applications/utilities, bin/", "có"),
    ("CN8", "solverInfo (tên của nhánh OpenCFD)", "v14 dùng function object residuals", "src/functionObjects/utilities/residuals", "đổi"),
    ("CN8", "checkMesh, foamLog, yPlus", "Có", "applications/utilities, bin/foamLog", "có"),
    ("An ninh", "systemCall, #codeStream, coded…", "Có: chạy lệnh shell hoặc biên dịch C++ từ tệp case — bộ chạy chặn mặc định", "src/functionObjects/utilities/systemCall, src/OpenFOAM/db/dictionary/functionEntries/codeStream", "chặn"),
]


def tt_chip(k: int, aux: bool = False) -> str:
    cls = "tt aux" if aux else "tt"
    return f'<a class="{cls}" href="#tt{k}" title="TT{k} · {TT_TITLES[k]}">TT{k}</a>'


def cn_chip(k: int) -> str:
    return f'<a class="cn" href="#cn{k}" title="CN{k} · {CN_TITLES[k]}">CN{k}</a>'


def pf_badge(p: str) -> str:
    return f'<span class="pf {PF_CLASS[p]}">{E(apps.PROFILES[p])}</span>'


def stage_chips(app: dict) -> str:
    if app["s"] == "out":
        return '<span class="sr">không chạy</span><span aria-hidden="true">—</span>'
    chips = [tt_chip(0)]
    for i, c in enumerate(app["cn"]):
        if c == "●":
            chips.append(tt_chip(i + 1))
        elif c == "○":
            chips.append(tt_chip(i + 1, aux=True))
    return "".join(chips)


def must_replace(text: str, old: str, new: str, count: int = 1) -> str:
    n = text.count(old)
    if n != count:
        raise SystemExit(f"anchor found {n} times (expected {count}): {old[:90]!r}")
    return text.replace(old, new)


# ----------------------------------------------------------------- blocks
CSS = """
/* v2 · sửa lỗi có từ bản trước: nhãn .sr (position:absolute) trong bảng cuộn phải lấy khung cuộn làm khối chứa,
   nếu không chúng thoát khỏi overflow và kéo rộng cả trang trên điện thoại */
.scroll{position:relative}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
/* v2 · tầng thực thi: chip TT (xanh) đi cặp với chip CN (đỏ) cùng chỉ số; hồ sơ G4 là nhãn viền */
.tt{display:inline-block;font:600 11px/1 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;padding:4px 5px;border:1px solid var(--cp);color:var(--cp);background:var(--cp-soft);border-radius:3px;text-decoration:none;white-space:nowrap;vertical-align:1px;margin:1px 2px 1px 0}
.tt.aux{background:transparent;border-style:dashed}
a.tt:hover{filter:brightness(.95);text-decoration:underline}
.steps b .tt{margin-left:4px}
.pf{display:inline-block;font-size:12.5px;font-weight:600;line-height:1;padding:4px 7px;border-radius:999px;white-space:nowrap;border:1.5px solid currentColor;background:transparent}
.pf.pg{color:var(--acc)}.pf.pa{color:var(--ex)}.pf.pc{color:var(--ink)}.pf.pk{color:var(--cp)}.pf.pn{color:var(--out)}
.mx td.tts{white-space:normal;min-width:150px}
.mx td.bn{white-space:normal;min-width:190px;font-size:13.5px;color:var(--mute);font-weight:400}
.mx td.pfc{white-space:nowrap}
.flt-label{font-size:13px;color:var(--mute);align-self:center;margin-right:4px}
.vf{display:inline-block;font-size:11.5px;font-weight:700;letter-spacing:.04em;padding:2px 6px;border-radius:3px;vertical-align:1px;white-space:nowrap}
.vf.do{background:var(--ok-soft);color:var(--ok)}.vf.n3{background:var(--ex-soft);color:var(--ex)}.vf.uc{background:var(--cp-soft);color:var(--cp)}.vf.gt{background:var(--out-soft);color:var(--out)}
table.ttab{min-width:1060px;font-size:14px}
table.ttab td{white-space:normal}
table.ttab td:first-child{min-width:150px}
table.ttab td:nth-child(4){min-width:230px}
table.v14 td:first-child{white-space:nowrap}
table.v14 td:nth-child(2){min-width:220px}
table.spec td:first-child{white-space:normal;min-width:170px}
table.spec td:nth-child(2){white-space:nowrap;font-variant-numeric:tabular-nums}
.flow{display:grid;grid-template-columns:1fr auto 1fr auto 1.4fr auto 1fr;gap:10px;align-items:stretch;margin:16px 0}
.flow .arr{align-self:center;color:var(--mute);font-size:22px;text-align:center}
.flow .card small{display:block;color:var(--mute);font-size:13px;margin-bottom:4px;letter-spacing:.06em;text-transform:uppercase}
.flow .card{border-top-color:var(--cp)}
@media (max-width:860px){.flow{grid-template-columns:1fr}.flow .arr{transform:rotate(90deg)}}
.calc{background:var(--panel);border:1px solid var(--line);padding:16px 18px;margin:16px 0}
.calc form{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(190px,100%),1fr));gap:10px 14px;margin:0}
.calc label{display:flex;flex-direction:column;gap:4px;font-size:13px;color:var(--mute);font-weight:600;min-width:0}
.calc input,.calc select{font:inherit;font-size:15px;color:var(--ink);background:var(--bg);border:1px solid var(--line);padding:6px 8px;border-radius:3px;min-width:0;width:100%}
.calc input:focus-visible,.calc select:focus-visible{outline:2px solid var(--acc);outline-offset:1px}
.calc .chk{flex-direction:row;align-items:center;gap:8px;color:var(--ink)}
.calc .chk input{width:auto}
.calc .presets{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 14px}
.calc output{display:block}
.calc table{min-width:0}
.calc td:nth-child(2){font-variant-numeric:tabular-nums;font-weight:700;white-space:normal;overflow-wrap:anywhere;min-width:7em}
.calc td:first-child{white-space:normal;font-weight:400}
.yes{color:var(--ok);font-weight:700}.no{color:var(--acc);font-weight:700}
.new-box{border:1px solid var(--line);border-left:3px solid var(--cp);background:var(--panel);padding:12px 18px;margin:18px 0 0;max-width:none}
.new-box h3{font-size:15px;margin:0 0 6px}
.new-box ul{margin:4px 0;max-width:none}
pre.cfg{border-left-color:var(--cp)}
"""


def build_tt_section() -> str:
    rows = [
        (0, "nền cho mọi nhóm, gắn với " + cn_chip(7) + " " + cn_chip(8),
         "Mac M4 → GitHub → Colab G4",
         "<code>./foamctl submit</code>, <code>git push</code> / <code>git fetch --depth 1</code>, <code>nvidia-smi -q -d ECC</code>, <code>apt install openfoam14</code>",
         "Đo lõi, RAM, RAM-disk, GPU và bộ đếm ECC; cài OpenFOAM 14 mỗi phiên; so SHA-256 từng tệp với manifest ký trên Mac; quét lệnh chạy được trong case",
         "SHA-256 trùng từng bit; 0 phát hiện mức chặn; GPU không có lỗi ECC không sửa được",
         "Git và apt thử lại sau 2, 4, 8, 16 s; GPU có lỗi ECC thì chỉ chạy CPU",
         "Mạng, RAM-disk"),
        (1, cn_chip(1), "Colab G4 · mọi lõi CPU",
         "v14: <code>surfaceFeatures</code>, <code>blockMesh</code>, <code>decomposePar -copyZero</code>, <code>snappyHexMesh</code> chạy <code>-parallel</code>, <code>createZones</code>, <code>createBaffles</code>, <code>splitMeshRegions</code>, <code>renumberMesh</code>. OpenCFD: thêm <code>-overwrite</code>, <code>surfaceFeatureExtract</code>",
         "Đọc <code>Allrun</code> như dữ liệu, chỉ nhận lệnh OpenFOAM trong danh sách cho phép; chạy snappyHexMesh trên mọi lõi; đánh số lại ô để tận dụng bộ đệm",
         "<code>checkMesh</code> không báo “Failed n mesh checks”",
         "snappyHexMesh song song lỗi → chạy tuần tự; thiếu scotch → hierarchical; Allrun có bước không tự động hoá được trước bước giải → từ chối rõ ràng",
         "Mọi lõi, RAM"),
        (2, cn_chip(2), "Colab G4 · CPU",
         "<code>foamDictionary -entry … -set …</code> (từ trường <code>set</code> của job), <code>setFields</code>, <code>potentialFoam</code>",
         "Áp các thay đổi đã kiểm ký tự; khởi tạo song song khi lưới đã chia",
         "Giá trị không chứa <code># $ ; { } ` \\</code> hay xuống dòng; có <code>setFieldsDict</code> khi gọi setFields",
         "Từ chối kèm lý do, không đoán",
         "Một lõi hoặc mọi lõi"),
        (3, cn_chip(3), "Colab G4 · CPU, GPU qua TT4",
         "<code>foamRun</code> (solver đọc từ <code>controlDict</code>), <code>foamMultiRun</code>, hoặc tên cổ điển (<code>simpleFoam</code>, <code>dsmcFoam</code>…) với <code>-parallel</code>",
         "Đọc luồng ra từng dòng, không có tệp log; in tiến độ mỗi phút; đếm bước, đo giây mỗi bước, đo % CPU và GPU",
         "<code>End</code> hoặc “solution converged”, không NaN",
         "Xem TT8",
         "Mọi lõi, GPU nếu bật"),
        (4, cn_chip(4), "Colab G4 · CPU + GPU",
         "<code>decomposeParDict</code> (<code>decomposer scotch</code> ở v14, <code>method scotch</code> ở OpenCFD); <code>mpirun -np N --bind-to core --map-by core</code>; <code>--cpu-set</code> cho biến thể đồng thời; OGL <code>GKOCG</code> + <code>executor cuda</code> trong <code>fvSolution</code>",
         "N = số lõi vật lý (giữ ≥ 10 000 ô mỗi tiến trình), ghim vào luồng chính của mỗi lõi; biến thể chạy đồng thời, ≥ 4 lõi mỗi biến thể. CPU chạy ngay; khi OGL dựng xong thì đo 20 bước, ghi mốc, chuyển áp suất sang GPU, đo 20 bước, giữ cách nhanh hơn",
         "GPU phải nhanh hơn ≥ 10 % (đo trên chính lần chạy) mới được giữ",
         "GPU lỗi hoặc chậm → khôi phục <code>fvSolution</code> CPU và chạy tiếp từ mốc mới nhất; lỗi gắn lõi MPI → chạy lại với cách gắn an toàn",
         "Mọi lõi, GPU, PCIe"),
        (5, cn_chip(5), "Colab G4 · luồng anh em của siêu phân luồng, GPU",
         "<code>libs (\"libOGL.so\")</code>; CMake dựng OGL + Ginkgo cho đúng <code>sm_</code> đọc từ <code>nvidia-smi</code>; <code>foamMultiRun</code> đa vùng; làn mô hình chạy script Python đã ký trên GPU; preCICE (chưa tự động)",
         "Dựng OGL nền ngay khi phiên mở, sáu khâu, độ ưu tiên thấp nhất, trong RAM, song song với solver; GPU rảnh thì giao cho làn mô hình",
         "Chạy thử 3 bước trên GPU qua; mô hình khớp manifest và được người vận hành bật",
         "Nhánh dev dựng lỗi → thử thẻ phát hành mới nhất; vẫn lỗi → cả phiên chạy CPU, in lý do",
         "Luồng anh em, GPU"),
        (6, cn_chip(6), "Colab G4 · RAM",
         "Function object trong <code>controlDict</code>: <code>forceCoeffs</code>, <code>probes</code>, <code>wallShearStress</code>; v14 dùng <code>#includeFunc cellMax(T)</code> thay <code>fieldMinMax</code>",
         "Đọc tệp <code>.dat</code> trong <code>postProcessing/</code>, gộp các thư mục chạy tiếp, tính last, mean, max, min và độ trôi",
         "KPI có giá trị; độ trôi giữa hai nửa cửa sổ cuối dưới 1 %",
         "Báo thiếu tệp hoặc thiếu cột, không bịa số",
         "CPU nhẹ"),
        (7, cn_chip(7), "Colab → màn hình",
         "Không <code>foamToVTK</code>, không <code>reconstructPar</code>: không lưu gì. Bảng kết quả in ra ô notebook",
         "Theo dõi <code>jobs/active.json</code> mỗi 30 s và chạy lần lượt các job mới",
         "Đầu ra notebook không được lưu (tuỳ chọn của Colab)",
         "Fetch lỗi → thử lại ở vòng sau",
         "—"),
        (8, cn_chip(8), "Colab G4",
         "<code>checkMesh</code> (cổng của TT1), phần dư, số Courant, NaN, <code>stopAt noWriteNow</code>",
         "Phát hiện phân kỳ; quay về mốc tốt gần nhất; giảm bước thời gian hoặc hệ số nới lỏng, rồi chuyển upwind; dừng sạch trước hạn phiên; đo % khai thác CPU, GPU, RAM; hạ <code>fileModificationSkew</code> xuống 1 s để lệnh dừng có hiệu lực ngay bước sau",
         "Hội tụ hoặc chạy hết; KPI ổn định",
         "Tối đa 3 lần (đặt được 0–5); mốc hỏng dời vào <code>.g4/quarantine</code>, không xoá; kết quả sau khi tự chữa được đánh dấu cần kiểm chứng lại",
         "—"),
    ]
    body = []
    for k, cn, where, cmd, auto, gate, heal, res in rows:
        body.append(f'<tr id="tt{k}"><td>{tt_chip(k)} {TT_TITLES[k]}</td><td>{cn}</td><td>{where}</td><td>{cmd}</td>'
                    f'<td>{auto}</td><td>{gate}</td><td>{heal}</td><td>{res}</td></tr>')
    return f"""
<h2 id="thuc-thi">Tầng thực thi: chín khâu TT0–TT8 chạy trên G4</h2>
<p class="sub">Khâu <span class="tt">TTk</span> thực hiện đúng nhóm chức năng <span class="cn">CNk</span> cùng chỉ số, trên một máy cụ thể, có lệnh, cổng kiểm tra và cách tự sửa lỗi. TT0 là nền chung: môi trường và toàn vẹn. Bộ chạy <code>g4runner</code> trong thư mục <code>openfoam-g4/</code> làm mọi việc ở cột “Bộ chạy tự động làm gì”, không cần chỉnh tay.</p>
<div class="scroll"><table class="ttab"><thead><tr><th>Khâu</th><th>Chức năng</th><th>Chạy ở đâu</th><th>Lệnh OpenFOAM và tệp</th><th>Bộ chạy tự động làm gì</th><th>Cổng kiểm tra</th><th>Tự sửa lỗi</th><th>Tài nguyên G4</th></tr></thead><tbody>
{''.join(body)}
</tbody></table></div>
<div class="note"><b>Chế độ không lưu là mặc định duy nhất.</b> Mọi dữ liệu tính nằm trong RAM (<code>/dev/shm</code> hoặc một tmpfs riêng), log của solver được đọc thẳng từ luồng ra và chỉ giữ 400 dòng cuối trong RAM để báo lỗi, notebook không mount Drive và không đẩy gì lên GitHub. Khi runtime kết thúc, mọi thứ biến mất. Nằm ngoài tầm của bộ chạy: nhật ký vận hành của chính Google và GitHub, lịch sử git bạn đã đẩy, và Colab Secrets nếu bạn dùng.</div>
"""


def matrix_extra_cells(app: dict) -> str:
    p = apps.derive_profile(app)
    return (f'<td class="tts">{stage_chips(app)}</td><td class="pfc">{pf_badge(p)}</td>'
            f'<td class="bn">{E(app["bottleneck"])}</td>')


def card_exec_row(app: dict) -> str:
    p = apps.derive_profile(app)
    parts = [f'<p>{pf_badge(p)} {stage_chips(app)}</p>',
             f'<p><b>Nút cổ chai:</b> {E(app["bottleneck"])}. <b>Bộ chạy:</b> {E(app["g4"])}.</p>']
    if app["tutorial"]:
        auto = "Allrun chỉ gồm lệnh trong danh sách cho phép, chạy tự động" if app["auto"] else "cần chuẩn bị thêm"
        parts.append(f'<p><b>Tutorial OpenFOAM 14 đã đối chiếu:</b> <code>{E(app["tutorial"])}</code> ({auto}).</p>')
    if app.get("template"):
        parts.append(f'<p><b>Chạy mẫu từ Mac:</b> <code>./foamctl submit --template {app["id"]}</code></p>')
    if app["id"] in V14_NOTES:
        parts.append(f'<p><b>Tên ở v14:</b> {V14_NOTES[app["id"]]}</p>')
    return f'<div class="ex"><dt>Thực thi trên G4</dt><dd>{"".join(parts)}</dd></div>'


def presets_js() -> str:
    pre = {
        "ud01": {"cells_m": 20, "physics": "incompressible_rans", "iterations": 20000, "variants": 1, "ami": False},
        "ud07": {"cells_m": 2, "physics": "incompressible_transient", "iterations": 5000, "variants": 6, "ami": False},
        "ud09": {"cells_m": 3, "physics": "reacting", "iterations": 20000, "variants": 1, "ami": False},
        "ud12": {"cells_m": 5, "physics": "incompressible_transient", "iterations": 50000, "variants": 1, "ami": False},
        "ud15": {"cells_m": 0.2, "physics": "incompressible_transient", "iterations": 20000, "variants": 12, "ami": False},
        "max": {"cells_m": 100, "physics": "incompressible_rans", "iterations": 3000, "variants": 1, "ami": False},
    }
    return json.dumps(pre)


CAPACITY_JS = r"""
/* Port of g4runner/capacity.py estimate(): only + - * / floor ceil min max, so it returns the
   same IEEE-754 doubles as Python for the same inputs (tests/test_doc_parity.py checks this). */
function g4Round(x, scale) { return Math.floor(x * scale + 0.5) / scale; }
function g4Estimate(inp) {
  var D = __DEFAULTS__, P = __PHYSICS__, p = {}, k;
  for (k in D) p[k] = D[k];
  for (k in inp) if (inp[k] !== null && inp[k] !== undefined) p[k] = inp[k];
  var phys = P[p.physics];
  var cores = Math.max(1, Math.trunc(p.cores_physical));
  var cells = p.cells_m * 1000000.0;
  var variants = Math.max(1, Math.trunc(p.variants));
  var ram_need_gb = p.cells_m * phys.kb_per_cell;
  var ram_budget = p.ram_gb * p.ram_headroom;
  var mcj = Math.max(1, Math.trunc(p.min_cores_per_job));
  var by_cores = cores >= mcj ? Math.floor(cores / mcj) : 1.0;
  var by_ram = ram_need_gb > 0 ? Math.floor(ram_budget / ram_need_gb) : variants;
  var concurrent = Math.max(1.0, Math.min(variants, Math.max(1.0, by_cores), Math.max(1.0, by_ram)));
  var cores_per_job = Math.floor(cores / concurrent);
  var ranks = Math.min(cores_per_job, Math.max(1.0, Math.floor(cells / p.min_cells_per_rank)));
  var cells_per_rank = cells / ranks;
  var t_iter_cpu = cells * p.c_cell_us * 0.000001 / ranks;
  var gpu_allowed = !!phys.gpu_ok && !p.ami && p.vram_gb > 0.0;
  var vram_need_gb = cells * p.gpu_bytes_per_cell / 1000000000.0;
  var vram_fit = vram_need_gb <= p.vram_gb * p.vram_headroom;
  var s_p = (p.gpu_bw_gbs * p.gpu_eff) / (p.cpu_bw_gbs * p.cpu_eff);
  s_p = Math.min(s_p, 20.0);
  var t_transfer = cells * p.transfer_bytes_per_cell * phys.p_solves / (p.pcie_gbs * 1000000000.0);
  var overhead = t_iter_cpu > 0 ? t_transfer / t_iter_cpu : 0.0;
  var f = phys.p_fraction;
  var speedup = (gpu_allowed && vram_fit && f > 0) ? 1.0 / ((1.0 - f) + f / s_p + overhead) : 1.0;
  var iters = p.iterations;
  var hours_cpu = iters * t_iter_cpu / 3600.0;
  var t_b = p.ogl_ready ? 0.0 : p.ogl_build_h;
  var k = p.build_slowdown;
  var hours_gpu = hours_cpu / speedup + t_b;
  var hours_par;
  if (t_b <= 0.0) hours_par = hours_cpu / speedup + p.switch_h;
  else if (hours_cpu / k <= t_b) hours_par = hours_cpu / k;
  else hours_par = t_b + (hours_cpu - k * t_b) / speedup + p.switch_h;
  if (!p.ogl_overlap) hours_par = hours_gpu;
  var eligible = gpu_allowed && vram_fit && speedup >= 1.1;
  var use_gpu = eligible && hours_par < hours_cpu;
  var hours_job = use_gpu ? hours_par : hours_cpu;
  var waves = Math.ceil(variants / concurrent);
  var hours_total = hours_job * waves;
  var cu = hours_total * p.cu_per_hour;
  var fits_session = hours_total <= p.session_hours - 0.5;
  return {
    physics: p.physics, ram_need_gb: g4Round(ram_need_gb, 1000.0), ram_fit: ram_need_gb <= ram_budget,
    cells_max_m: g4Round(ram_budget / phys.kb_per_cell, 10.0), concurrent: concurrent, cores_per_job: cores_per_job,
    ranks: ranks, cells_per_rank: g4Round(cells_per_rank, 1.0), t_iter_cpu_s: g4Round(t_iter_cpu, 10000.0),
    gpu_allowed: gpu_allowed, vram_need_gb: g4Round(vram_need_gb, 1000.0), vram_fit: vram_fit,
    s_pressure: g4Round(s_p, 100.0), overhead: g4Round(overhead, 10000.0), speedup: g4Round(speedup, 1000.0),
    use_gpu: use_gpu, hours_cpu: g4Round(hours_cpu, 1000.0), hours_gpu: g4Round(hours_gpu, 1000.0),
    hours_par: g4Round(hours_par, 1000.0),
    hours_total: g4Round(hours_total, 1000.0), cu: g4Round(cu, 100.0), usd: g4Round(cu * p.usd_per_cu, 100.0),
    fits_session: fits_session,
    raw: {t_iter_cpu: t_iter_cpu, speedup: speedup, hours_par: hours_par, hours_total: hours_total, cu: cu}
  };
}
"""


def capacity_js() -> str:
    d = dict(capacity.DEFAULTS)
    return CAPACITY_JS.replace("__DEFAULTS__", json.dumps(d)).replace("__PHYSICS__", json.dumps(capacity.PHYSICS))


def physics_options() -> str:
    names = {
        "incompressible_rans": "Không nén, dừng (RANS)", "incompressible_transient": "Không nén, theo thời gian",
        "incompressible_les": "Không nén, LES", "buoyant": "Có lực nổi", "compressible": "Nén được",
        "vof": "Hai pha VoF", "multiphase_euler": "Đa pha Euler–Euler", "reacting": "Cháy, phản ứng",
        "cht_multiregion": "Nhiều vùng chất lưu–rắn (CHT)", "particles_dsmc": "Hạt DSMC / MD",
        "electrostatic": "Điện tĩnh (legacy)",
    }
    return "".join(f'<option value="{k}">{E(names[k])} · {capacity.PHYSICS[k]["kb_per_cell"]} kB/ô</option>'
                   for k in capacity.PHYSICS)


def three_way_table() -> str:
    cases = [("10 triệu ô RANS × 2 000 vòng, job đầu phiên", {}),
             ("Cùng ca, từ job thứ hai (OGL đã sẵn)", {"ogl_ready": True}),
             ("20 triệu ô RANS × 20 000 vòng", {"cells_m": 20.0, "iterations": 20000.0}),
             ("Dòng máu 5 triệu ô × 50 000 bước", {"cells_m": 5.0, "physics": "incompressible_transient", "iterations": 50000.0}),
             ("Cháy 3 triệu ô × 20 000 bước", {"cells_m": 3.0, "physics": "reacting", "iterations": 20000.0})]
    rows = []
    for label, inp in cases:
        e = capacity.estimate(inp)
        best = "C · song song" if e["use_gpu"] else "A · chỉ CPU"
        rows.append(f"<tr><td style=\"white-space:normal\">{E(label)}</td><td>{e['hours_cpu']}</td><td>{e['hours_gpu']}</td>"
                    f"<td>{e['hours_par']}</td><td>{best}</td></tr>")
    return ('<div class="scroll"><table><thead><tr><th>Ca</th><th>(A) chỉ CPU, giờ</th><th>(B) dựng xong mới GPU, giờ</th>'
            '<th>(C) CPU ngay + dựng nền + chuyển GPU, giờ</th><th>Bộ chạy chọn</th></tr></thead><tbody>'
            + "".join(rows) + '</tbody></table></div><p class="sub">Song song (C) luôn tốt hơn dựng trước (B) ở job đầu phiên vì '
            'CPU không đứng chờ; từ job thứ hai OGL đã sẵn nên C còn lại thêm một lần khởi động lại để đo. Với job đầu ngắn, '
            'chỉ CPU vẫn nhanh hơn một chút và bộ chạy chọn đúng như vậy; GPU khi đó rảnh cho làn mô hình.</p>')


def parallel_block() -> str:
    stages = [
        ("Kiểm tra", "GPU khoẻ (ECC), <code>nvcc --list-gpu-arch</code> có <code>compute_&lt;cc&gt;</code> đọc từ <code>nvidia-smi</code> (RTX PRO 6000 Blackwell báo 12.0), cmake ≥ 3.18, git, make", "Thiếu gì thì dừng, cả phiên chạy CPU, in lý do"),
        ("Tải mã", "<code>git clone --depth 1 --branch dev</code> OGL vào RAM, ghi lại commit", "Lỗi thì thử thẻ phát hành mới nhất (<code>git ls-remote --tags</code>)"),
        ("Cấu hình", "CMake bật CUDA, OpenMP, <code>OGL_CUDA_ARCHITECTURES</code> đúng kiến trúc, tắt test, nhãn 64 bit nếu OpenFOAM dùng", "Như trên"),
        ("Biên dịch", "<code>cmake --build -j N</code> trên luồng anh em (hoặc lõi dành riêng), <code>nice 19</code>", "Như trên"),
        ("Cài đặt", "Vào thư mục RAM; thêm vào <code>LD_LIBRARY_PATH</code> của solver", "Không thấy <code>libOGL.so</code> → GPU tắt"),
        ("Chạy thử", "Cavity 16³ với <code>GKOCG</code>, <code>executor cuda</code>, 3 bước", "Không qua → GPU tắt"),
    ]
    rows = "".join(f"<tr><td>{i + 1} · {E(n)}</td><td style=\"white-space:normal\">{w}</td><td style=\"white-space:normal\">{f}</td></tr>"
                   for i, (n, w, f) in enumerate(stages))
    return f"""
<h3 id="song-song-cpu-gpu" style="margin-top:26px">CPU và GPU song song, OGL dựng tự động</h3>
<p>Dựng OGL là việc nặng về biên dịch, còn solver bị giới hạn bởi băng thông bộ nhớ, nên hai việc chạy song song được. Bộ chạy ghim mỗi tiến trình MPI vào luồng chính của một lõi; việc dựng chạy trên luồng anh em của siêu phân luồng với độ ưu tiên thấp nhất (máy không có siêu phân luồng thì trên vài lõi dành riêng). Solver bắt đầu ngay, không chờ.</p>
<div class="scroll"><table><thead><tr><th>Khâu dựng</th><th>Làm gì</th><th>Khi lỗi</th></tr></thead><tbody>{rows}</tbody></table></div>
<ol class="steps">
<li><b>Bắt đầu trên CPU</b>Mọi lõi vật lý làm việc ngay từ giây đầu; trong lúc dựng, tốc độ CPU giảm còn khoảng k (giả định {capacity.DEFAULTS['build_slowdown']:g}, bộ chạy đo thật).</li>
<li><b>OGL sẵn sàng → đo CPU</b>20 bước tiếp theo đo tốc độ CPU khi máy đã rảnh.</li>
<li><b>Ghi mốc và chuyển</b>Nếu phần việc còn lại đủ dài để bù hai lần khởi động lại, bộ chạy nhận GPU từ trọng tài, đặt <code>stopAt writeNow</code>, đổi bộ giải áp suất sang <code>GKOCG</code> (<code>executor cuda</code>), chạy tiếp từ <code>latestTime</code>.</li>
<li><b>Đo GPU và quyết định</b>Sau 20 bước: nhanh hơn ≥ 10 % thì giữ; không thì ghi mốc và quay về CPU, trả GPU cho làn mô hình. Không có lần chạy thử riêng nào, mọi bước đều là bước thật của bài toán.</li>
</ol>
<h3 id="lan-mo-hinh" style="margin-top:26px">Làn mô hình: GPU rảnh thì chạy mô hình của bạn</h3>
<p>Khi OpenFOAM không giữ GPU (hồ sơ “CPU”, job đầu ngắn, hoặc đo thấy GPU không lợi), GPU 96 GB vẫn chạy được việc khác cùng lúc: huấn luyện mô hình thay thế (surrogate) từ các biến thể vừa tính, hay suy luận một mô hình. Job loại <code>model</code> chạy một script Python trong repo:</p>
<ul>
<li>Chỉ chạy khi người vận hành bật Secret <code>G4_ALLOW_MODELS</code> = <code>1</code>; tệp job không tự bật được. Thư mục script phải khớp manifest SHA-256 ký trên Mac.</li>
<li>Trọng tài GPU: mô hình chỉ nhận GPU khi không job OpenFOAM nào đang giải áp suất trên GPU, và ngược lại.</li>
<li>CPU: vài luồng anh em (máy không siêu phân luồng: một lõi dành riêng, solver dùng các lõi còn lại); <code>nice 5</code>; <code>OMP_NUM_THREADS</code> giới hạn đúng số luồng được giao.</li>
<li>Không lưu: bộ đệm Hugging Face, torch, pip, matplotlib và thư mục làm việc nằm trong RAM; môi trường không có token GitHub; đầu ra chỉ in ra ô notebook.</li>
</ul>
"""


def build_g4_section() -> str:
    D = capacity.DEFAULTS
    ref = capacity.estimate({})
    tr = capacity.estimate({"cells_m": 5.0, "physics": "incompressible_transient", "iterations": 50000.0})
    mx = capacity.estimate({"cells_m": 100.0, "iterations": 3000.0})
    rows_max = "".join(
        f'<tr><td>{E(name)}</td><td>{capacity.PHYSICS[k]["kb_per_cell"]} kB</td><td>{capacity.estimate({"physics": k})["cells_max_m"]} triệu</td>'
        f'<td>{capacity.PHYSICS[k]["p_fraction"]:.2f}</td><td>{capacity.estimate({"physics": k})["speedup"]}×</td></tr>'
        for k, name in [("incompressible_rans", "Không nén, dừng (RANS)"), ("incompressible_transient", "Không nén, theo thời gian"),
                        ("incompressible_les", "LES"), ("buoyant", "Có lực nổi"), ("compressible", "Nén được"),
                        ("vof", "Hai pha VoF"), ("multiphase_euler", "Đa pha Euler–Euler"), ("reacting", "Cháy, phản ứng"),
                        ("cht_multiregion", "CHT nhiều vùng"), ("particles_dsmc", "DSMC / MD"), ("electrostatic", "Điện tĩnh")])
    return f"""
<p class="part">Phần III · Tầng thực thi trên Colab G4</p>
<h2 id="g4">Năng lực của G4 và cách khai thác hết cho OpenFOAM</h2>
<p class="sub">Colab gọi runtime này là <b>G4</b>: một GPU NVIDIA RTX PRO 6000 Blackwell Server Edition trên máy ảo G4 của Google Cloud. Nhãn bên cạnh mỗi con số cho biết độ tin cậy: <span class="vf do">ĐO</span> đo được ngay trong phiên bởi bộ chạy, <span class="vf n3">NGUỒN</span> lấy từ nhà sản xuất hoặc trang chính thức, <span class="vf uc">ƯỚC TÍNH</span> suy ra bằng công thức, <span class="vf gt">GIẢ ĐỊNH</span> chưa có nguồn xác nhận, bộ chạy thay bằng số đo.</p>
<div class="scroll"><table class="spec"><thead><tr><th>Thành phần</th><th>Giá trị</th><th>Độ tin cậy</th><th>Ý nghĩa với OpenFOAM</th></tr></thead><tbody>
<tr><td>GPU</td><td>1 × RTX PRO 6000 Blackwell Server</td><td><span class="vf n3">NGUỒN</span></td><td>Colab công bố hỗ trợ G4; nvidia-smi hiện tên RTX PRO 6000</td></tr>
<tr><td>Bộ nhớ GPU</td><td>96 GB GDDR7, ECC, bus 512 bit</td><td><span class="vf n3">NGUỒN</span></td><td>Đủ cho hệ áp suất khoảng 216 triệu ô (400 B/ô), lớn hơn giới hạn RAM máy</td></tr>
<tr><td>Băng thông bộ nhớ GPU</td><td>1 597 GB/s (≈ 1,6 TB/s)</td><td><span class="vf n3">NGUỒN</span> <span class="vf do">ĐO</span></td><td>Con số quyết định tốc độ giải áp suất (bài toán thưa, bị giới hạn bởi băng thông)</td></tr>
<tr><td>FP32 / FP64</td><td>≈ 120 TFLOPS / ≈ 1,9 TFLOPS</td><td><span class="vf n3">NGUỒN</span> <span class="vf uc">ƯỚC TÍNH</span> <span class="vf do">ĐO</span></td><td>FP64 suy từ tỉ lệ 1:64 của chip GB202; bộ chạy đo bằng phép nhân ma trận float64. Gradient liên hợp chỉ cần khoảng 0,13 FLOP mỗi byte, tức chừng 0,2 TFLOPS ở 1,6 TB/s, nên FP64 không phải giới hạn</td></tr>
<tr><td>BF16 / Tensor core</td><td>960 TFLOPS (Colab, có thưa 2:4)</td><td><span class="vf n3">NGUỒN</span></td><td>OpenFOAM tính FP64, không dùng được; chỉ hữu ích cho mô hình học máy thay thế (surrogate)</td></tr>
<tr><td>CPU</td><td>48 vCPU AMD EPYC Turin, 2,7 / 3,5 / 4,1 GHz</td><td><span class="vf n3">NGUỒN</span> (máy g4-standard-48)</td><td>Giả định 24 lõi vật lý × 2 luồng; bộ chạy đọc <code>/proc/cpuinfo</code> để biết thật</td></tr>
<tr><td>CPU FP64 đỉnh</td><td>≈ 2,7 TFLOPS</td><td><span class="vf uc">ƯỚC TÍNH</span></td><td>24 lõi × 3,5 GHz × 32 FLOP/chu kỳ (AVX-512, hai FMA 512 bit của Zen 5)</td></tr>
<tr><td>Băng thông RAM của máy ảo</td><td>{D['cpu_bw_gbs']:g} GB/s</td><td><span class="vf gt">GIẢ ĐỊNH</span> <span class="vf do">ĐO</span></td><td>1/8 của máy chủ hai socket 12 kênh DDR5; bộ chạy đo thật bằng phép triad trên mọi lõi</td></tr>
<tr><td>RAM</td><td>180 GB (thấy 176 GB trong một phiên)</td><td><span class="vf n3">NGUỒN</span> <span class="vf do">ĐO</span></td><td>Giới hạn số ô lớn nhất: {ref['cells_max_m']} triệu ô RANS với 15 % dự phòng</td></tr>
<tr><td>PCIe</td><td>5.0 x16, ≈ {D['pcie_gbs']:g} GB/s thực tế</td><td><span class="vf gt">GIẢ ĐỊNH</span> <span class="vf do">ĐO</span></td><td>Chi phí chép ma trận áp suất sang GPU mỗi lần giải</td></tr>
<tr><td>Ổ đĩa</td><td>≈ 189 GB trống (một báo cáo)</td><td><span class="vf gt">GIẢ ĐỊNH</span></td><td>Chế độ không lưu không dùng ổ đĩa cho dữ liệu</td></tr>
<tr><td>Hệ điều hành Colab</td><td>Ubuntu 22.04.5, Python 3.12</td><td><span class="vf n3">NGUỒN</span></td><td>Khớp gói <code>openfoam14</code> cho Ubuntu 22.04 (jammy)</td></tr>
<tr><td>Chi phí</td><td>≈ {D['cu_per_hour']:g} CU/giờ ≈ {D['cu_per_hour'] * D['usd_per_cu']:.2f} USD/giờ</td><td><span class="vf gt">GIẢ ĐỊNH</span> (ảnh chụp của bên thứ ba)</td><td>Pro+ 500 CU/tháng ≈ {500 / D['cu_per_hour']:.0f} giờ G4 (một số nguồn ghi 600 CU ≈ {600 / D['cu_per_hour']:.0f} giờ); Colab hiện tốc độ tiêu thụ thật trong bảng tài nguyên</td></tr>
<tr><td>Thời lượng phiên</td><td>Tới 24 giờ chạy nền (Pro+)</td><td><span class="vf n3">NGUỒN</span> (bên thứ ba)</td><td>Bộ chạy dừng sạch trước hạn bằng <code>stopAt noWriteNow</code></td></tr>
</tbody></table></div>

<h3 style="margin-top:26px">Vì sao OpenFOAM mặc định không khai thác hết G4</h3>
<ul>
<li><b>Một lõi.</b> Không có <code>decomposePar</code> và <code>mpirun</code>, solver chạy một tiến trình: 1 trên 24 lõi vật lý làm việc.</li>
<li><b>Không GPU.</b> Bộ giải tuyến tính của OpenFOAM chỉ chạy trên CPU. Muốn đưa áp suất lên GPU phải nạp thêm thư viện như OGL (Ginkgo), PETSc4FOAM hoặc AmgX.</li>
<li><b>Không ghim lõi.</b> Tiến trình MPI trôi giữa các lõi và luồng siêu phân luồng, mất bộ đệm.</li>
<li><b>Chạy lần lượt.</b> Quét tham số mặc định chạy từng ca một, ca nhỏ không lấp đầy máy.</li>
<li><b>Ghi đĩa.</b> Kết quả ghi theo <code>writeInterval</code> ra đĩa, vừa chậm vừa trái với yêu cầu không lưu.</li>
</ul>

<h3 style="margin-top:26px">Kế hoạch khai thác 100 %, tự động</h3>
<div class="scroll"><table><thead><tr><th>Tài nguyên</th><th>Bộ chạy làm gì</th><th>Bằng chứng in ra cuối job</th></tr></thead><tbody>
<tr><td>Lõi CPU</td><td style="white-space:normal">Chia miền scotch với N = số lõi vật lý; <code>--bind-to core --map-by core</code>; siêu phân luồng chỉ khi được yêu cầu</td><td style="white-space:normal">% CPU bận đo từ <code>/proc/stat</code>. Thử thật trên máy 4 lõi: <b>99,6 %</b> suốt 6 502 bước</td></tr>
<tr><td>Nhiều ca nhỏ</td><td style="white-space:normal">Chạy đồng thời trên các bộ lõi tách biệt (<code>--cpu-set</code>), ≥ 4 lõi mỗi ca, giới hạn theo RAM</td><td style="white-space:normal">Thử thật: hai biến thể bị giam đúng trong lõi {{0,1}} và {{2,3}} (kiểm bằng <code>taskset</code>)</td></tr>
<tr><td>GPU</td><td style="white-space:normal">OGL dựng nền ngay khi phiên mở; solver chạy CPU ngay và chuyển áp suất sang GPU giữa chừng khi đo thấy nhanh hơn ≥ 10 %</td><td style="white-space:normal">Giây mỗi bước của CPU và GPU đo trên chính lần chạy, % GPU, công suất</td></tr>
<tr><td>GPU lúc OpenFOAM không cần</td><td style="white-space:normal">Làn mô hình: script Python đã ký của bạn chạy trên GPU cùng lúc, trọng tài GPU không cho hai bên giẫm nhau</td><td style="white-space:normal">Thử thật: mô hình bị giam trong CPU 3 trong lúc một job OpenFOAM chạy xong</td></tr>
<tr><td>Luồng siêu phân luồng</td><td style="white-space:normal">MPI ghim vào luồng chính của mỗi lõi; luồng anh em dành cho việc dựng OGL và cho mô hình</td><td style="white-space:normal">Tốc độ CPU khi đang dựng so với sau khi dựng, đo trên lần chạy</td></tr>
<tr><td>Bộ nhớ ECC</td><td style="white-space:normal">Đọc bộ đếm mã Hamming SECDED của GPU: lỗi 1 bit được phần cứng tự sửa, lỗi 2 bit chỉ phát hiện được → tắt GPU</td><td style="white-space:normal">Số lỗi đã sửa và không sửa được</td></tr>
<tr><td>RAM</td><td style="white-space:normal">Thư mục làm việc là tmpfs, ghi nhị phân, <code>purgeWrite</code> giữ vài mốc</td><td style="white-space:normal">Đỉnh RAM của lần chạy</td></tr>
<tr><td>Tensor core, RT core, NVENC</td><td style="white-space:normal">Không phục vụ được bộ giải FP64 của OpenFOAM; Tensor core dùng được qua làn mô hình (BF16)</td><td style="white-space:normal">Báo thẳng, không tính vào phần của OpenFOAM</td></tr>
</tbody></table></div>

<h3 style="margin-top:26px">Tính tổng năng lực: công thức</h3>
<ol class="steps">
<li><b>Số tiến trình</b><code>ranks = min(lõi cho mỗi ca, ⌊số ô / 10 000⌋)</code>. Với 24 lõi và 10 triệu ô: 24 tiến trình, {ref['cells_per_rank']:,.0f} ô mỗi tiến trình.</li>
<li><b>Giới hạn lưới theo RAM</b><code>số ô tối đa = 0,85 × RAM / (kB mỗi ô)</code>. Với 176 GB và 1,2 kB/ô: {ref['cells_max_m']} triệu ô.</li>
<li><b>Thời gian mỗi vòng trên CPU</b><code>t = số ô × c / ranks</code>, với <code>c</code> là chi phí mỗi ô mỗi vòng (µs·lõi). Mặc định {D['c_cell_us']:g} µs là giả định; bộ chạy đo <code>c</code> thật cho từng case (máy thử 4 lõi đo được 2,76–4,80 µs).</li>
<li><b>Tăng tốc của riêng bước áp suất</b><code>s = (băng thông GPU × 0,6) / (băng thông RAM × 0,6) = {ref['s_pressure']}</code>, chặn trên ở 20.</li>
<li><b>Tăng tốc toàn bài (định luật Amdahl)</b><code>S = 1 / ((1 − f) + f / s + o)</code>, với <code>f</code> là phần thời gian giải áp suất và <code>o</code> là chi phí chép qua PCIe. RANS 10 triệu ô: f = 0,45, o = {ref['overhead']}, S = <b>{ref['speedup']}×</b>; theo thời gian: S = <b>{tr['speedup']}×</b>. Các nghiên cứu công bố đo được 2× đến 9× cho riêng bước áp suất.</li>
<li><b>Chạy CPU và GPU song song thay vì chờ dựng OGL</b>Chế độ không lưu buộc dựng lại OGL mỗi phiên (giả định T<sub>b</sub> = {D['ogl_build_h']:g} giờ). Ba cách: (A) chỉ CPU: <code>T<sub>c</sub></code>; (B) dựng xong mới chạy GPU: <code>T<sub>b</sub> + T<sub>c</sub>/S</code>; (C) song song: CPU chạy ngay ở tốc độ k = {D['build_slowdown']:g} trong lúc dựng, rồi chuyển GPU: <code>T<sub>b</sub> + (T<sub>c</sub> − k·T<sub>b</sub>)/S + {D['switch_h']:g}</code> (job xong trước khi dựng xong thì chỉ là <code>T<sub>c</sub>/k</code>). Bộ chạy luôn làm C và giữ GPU chỉ khi đo thấy lợi. Bảng dưới cho các con số.</li>
<li><b>Chi phí</b><code>CU = giờ × {D['cu_per_hour']:g}</code>. Ví dụ dòng máu 5 triệu ô × 50 000 bước: {tr['hours_total']} giờ, {tr['cu']} CU ≈ {tr['usd']} USD. Lưới lớn nhất vừa RAM (100 triệu ô × 3 000 vòng): {mx['hours_total']} giờ, vừa một phiên 24 giờ.</li>
</ol>
<div class="scroll"><table><thead><tr><th>Loại vật lý</th><th>RAM mỗi ô</th><th>Lưới tối đa (176 GB)</th><th>Phần áp suất f</th><th>Tăng tốc GPU, 10 triệu ô</th></tr></thead><tbody>
{rows_max}
</tbody></table></div>
<p class="sub">Hai cột cuối là ước tính của mô hình, không phải số đo. DSMC và điện tĩnh không có bước áp suất để đưa lên GPU.</p>
{three_way_table()}

{parallel_block()}
<h3 id="may-tinh" style="margin-top:26px">Máy tính năng lực G4</h3>
<div class="calc">
<div class="presets" role="group" aria-label="Ví dụ theo ứng dụng"><button class="flt" type="button" data-preset="ud01">ud01 khí động 20 triệu ô</button><button class="flt" type="button" data-preset="ud07">ud07 6 tốc độ khuấy</button><button class="flt" type="button" data-preset="ud09">ud09 cháy</button><button class="flt" type="button" data-preset="ud12">ud12 dòng máu</button><button class="flt" type="button" data-preset="ud15">ud15 12 biến thể vi lưu</button><button class="flt" type="button" data-preset="max">Lưới lớn nhất</button></div>
<form id="g4calc" autocomplete="off">
<label>Số ô (triệu)<input id="c-cells" type="number" min="0.001" step="any" value="{D['cells_m']:g}"></label>
<label>Loại vật lý<select id="c-physics">{physics_options()}</select></label>
<label>Số vòng lặp / bước<input id="c-iter" type="number" min="1" step="1" value="{D['iterations']:g}"></label>
<label>Số biến thể<input id="c-var" type="number" min="1" step="1" value="1"></label>
<label>Lõi vật lý<input id="c-cores" type="number" min="1" step="1" value="{D['cores_physical']}"></label>
<label>RAM trống (GB)<input id="c-ram" type="number" min="1" step="any" value="{D['ram_gb']:g}"></label>
<label>VRAM (GB)<input id="c-vram" type="number" min="0" step="any" value="{D['vram_gb']:g}"></label>
<label>Băng thông RAM (GB/s)<input id="c-cbw" type="number" min="1" step="any" value="{D['cpu_bw_gbs']:g}"></label>
<label>Băng thông GPU (GB/s)<input id="c-gbw" type="number" min="1" step="any" value="{D['gpu_bw_gbs']:g}"></label>
<label>PCIe (GB/s)<input id="c-pcie" type="number" min="1" step="any" value="{D['pcie_gbs']:g}"></label>
<label>Chi phí mỗi ô (µs·lõi)<input id="c-ccell" type="number" min="0.01" step="any" value="{D['c_cell_us']:g}"></label>
<label>Dựng OGL (giờ)<input id="c-ogl" type="number" min="0" step="any" value="{D['ogl_build_h']:g}"></label>
<label>CU mỗi giờ<input id="c-cu" type="number" min="0" step="any" value="{D['cu_per_hour']:g}"></label>
<label>Giới hạn phiên (giờ)<input id="c-sess" type="number" min="1" step="any" value="{D['session_hours']:g}"></label>
<label class="chk"><input id="c-ami" type="checkbox"> Có lưới trượt (AMI / ghép không trùng lưới)</label>
<label class="chk"><input id="c-ready" type="checkbox"> OGL đã dựng xong trong phiên (từ job thứ hai)</label>
</form>
<output id="c-out" for="g4calc" aria-live="polite"></output>
</div>
<p class="sub">Máy tính dùng đúng công thức của <code>g4runner/capacity.py</code>; cùng đầu vào thì cho cùng con số tới từng bit (có kiểm thử so sánh). Trên Colab, bộ chạy điền số đo thật vào các ô băng thông, lõi, RAM và chi phí mỗi ô.</p>
"""


def build_auto_section() -> str:
    job_example = json.dumps(apps.job_from_template("ud01", "ud01-motorBikeSteady-20261102T1430Z-000000",
                                                    "2026-11-02T14:30:00Z"), ensure_ascii=False, indent=1)
    return f"""
<h2 id="tu-dong">Tự động hoá: Mac Mini M4 đẩy code, Colab G4 chạy</h2>
<p class="sub">Toàn bộ mã nằm trong thư mục <code>openfoam-g4/</code>: gói Python <code>g4runner</code> (chỉ thư viện chuẩn, chạy được với python3 có sẵn trên macOS), lệnh <code>foamctl</code> cho Mac, notebook <code>colab/OpenFOAM_G4.ipynb</code> và bộ kiểm thử.</p>
<div class="flow">
<div class="card"><small>Mac Mini M4</small><h3>Sửa và ký</h3><p>Sửa case, <code>./foamctl submit</code> kiểm bảo mật, tính SHA-256 từng tệp, ghi job, commit, push.</p><p>{tt_chip(0)}</p></div>
<div class="arr" aria-hidden="true">→</div>
<div class="card"><small>GitHub</small><h3>Chỉ chứa code</h3><p>Case, <code>jobs/&lt;id&gt;.json</code>, <code>jobs/active.json</code>. Không có kết quả. Token của Colab chỉ đọc.</p></div>
<div class="arr" aria-hidden="true">→</div>
<div class="card"><small>Colab G4 · RAM</small><h3>Chạy hết công suất</h3><p>Kiểm từng bit, dựng lưới, chia miền, giải ngay trên CPU trong khi OGL dựng nền, chuyển áp suất sang GPU khi lợi, tự chữa, đọc KPI. GPU rảnh thì chạy mô hình của bạn.</p><p>{tt_chip(0)}{tt_chip(1)}{tt_chip(2)}{tt_chip(4)}{tt_chip(5)}{tt_chip(3)}{tt_chip(8)}{tt_chip(6)}</p></div>
<div class="arr" aria-hidden="true">→</div>
<div class="card"><small>Màn hình</small><h3>Kết quả</h3><p>Bảng KPI, hội tụ, tự chữa, % CPU/GPU in ra ô notebook. Không lưu.</p><p>{tt_chip(7)}</p></div>
</div>

<h3 style="margin-top:22px">Làm một lần</h3>
<ol class="steps">
<li><b>Mac Mini M4: công cụ</b>Cài Command Line Tools của Apple (có <code>git</code>, <code>python3</code> ≥ 3.9), lấy repo về và kiểm tra.
<pre>xcode-select --install
git clone https://github.com/&lt;owner&gt;/&lt;repo&gt;.git
cd &lt;repo&gt;/openfoam-g4
./foamctl doctor</pre>Tuỳ chọn: máy ảo Ubuntu ARM64 trên M4 cài được <code>openfoam14</code> bằng apt (gói ARM64 có cho Ubuntu 22.04, 24.04, 26.04) để thử <code>blockMesh</code>, <code>checkMesh</code> tại chỗ.</li>
<li><b>GitHub: repo và token</b>Tạo repo riêng tư, chép thư mục <code>openfoam-g4/</code> vào. Tạo fine-grained token chỉ cho repo đó, quyền <b>Contents: Read-only</b>.</li>
<li><b>Colab: notebook</b><i>File → Open notebook → GitHub</i>, mở <code>openfoam-g4/colab/OpenFOAM_G4.ipynb</code>. <i>Runtime → Change runtime type</i> → <b>G4</b>. <i>Edit → Notebook settings</i> → tick <b>Omit code cell output when saving this notebook</b>. Thêm Secrets <code>GH_REPO</code> = <code>owner/repo</code> và <code>GH_TOKEN</code>.</li>
<li><b>Colab: chạy</b><i>Runtime → Run all</i>. Ô cuối đo phần cứng, cài OpenFOAM 14 (mỗi phiên, vì không lưu bộ đệm), rồi xem <code>jobs/active.json</code> mỗi 30 giây. Pro+ cho chạy nền tới 24 giờ khi đóng trình duyệt. Colab bản thường không tự mở notebook khi có push: phiên phải đang chạy.</li>
</ol>

<h3 style="margin-top:22px">Hằng ngày trên Mac</h3>
<pre class="cfg"><span class="c"># gửi case của bạn, đo hệ số cản trung bình 100 vòng cuối</span>
./foamctl submit cases/myCar --app ud01 --gpu auto \\
  --kpi Cd:postProcessing/forceCoeffs/0/forceCoeffs.dat:Cd:mean_last:100

<span class="c"># chạy ứng dụng mẫu: bồn trộn, 6 tốc độ khuấy chạy cùng lúc trên 6 bộ lõi</span>
./foamctl submit --template ud07

<span class="c"># xem 21 ứng dụng, hồ sơ G4, khâu TT và tutorial v14</span>
./foamctl apps

<span class="c"># ước tính trước khi chạy (cùng công thức với máy tính ở trên)</span>
./foamctl estimate --cells-m 20 --iterations 20000

<span class="c"># làn mô hình: script Python đã ký chạy trên GPU khi OpenFOAM không dùng GPU</span>
<span class="c"># (cần Secret G4_ALLOW_MODELS = 1 trong notebook)</span>
./foamctl submit-model models/surrogate --script train.py -- --epochs 20</pre>
<p>Job là cấu hình JSON, không phải script. Ví dụ job sinh từ mẫu <code>ud01</code>:</p>
<pre class="cfg">{E(job_example)}</pre>

<h3 style="margin-top:22px">An toàn và bảo mật</h3>
<ul>
<li>Mọi trường của job được kiểm theo danh sách cho phép; giá trị không được chứa <code># $ ; {{ }} ` \\</code> hay xuống dòng, đường dẫn không được ra ngoài case.</li>
<li><code>Allrun</code> không bao giờ chạy như shell. Bộ chạy chỉ đọc dòng <code>runApplication</code>/<code>runParallel</code> có công cụ OpenFOAM trong danh sách cho phép; nếu trước bước giải có dòng không tự động hoá được, job bị từ chối thay vì bỏ qua âm thầm.</li>
<li>Case chứa <code>systemCall</code>, <code>#codeStream</code>, <code>#calc</code>, <code>coded…</code>, <code>libs</code> theo đường dẫn, <code>#include</code> ra ngoài case, symlink ra ngoài, hay tệp <code>.so</code> đều bị chặn; chỉ người vận hành Colab mở được bằng <code>G4_ALLOW_CODED=1</code>, tệp job không mở được.</li>
<li>Token chỉ nằm trong biến môi trường của phiên; git lấy nó qua script askpass không chứa bí mật; <code>credential.helper</code> bị tắt.</li>
</ul>

<h3 style="margin-top:22px">Nghiệm thu: đã chạy thật những gì</h3>
<div class="scroll"><table><thead><tr><th>Kiểm tra</th><th>Kết quả</th><th>Môi trường</th></tr></thead><tbody>
<tr><td>Bộ kiểm thử tự động</td><td style="white-space:normal">__NTESTS__ / __NTESTS__ đạt (đơn vị, đầu–cuối, chuỗi Git, kế hoạch Allrun, chuyển GPU trực tuyến, làn mô hình, khớp tài liệu)</td><td style="white-space:normal">Python 3.12, OpenFOAM v1912 (gói Ubuntu 24.04), Open MPI 4.1.6, 4 lõi</td></tr>
<tr><td>Chạy song song</td><td style="white-space:normal">Cavity 3D 13 824 ô, 4 tiến trình, 60 bước, xong; chi phí đo được 4,80 µs·lõi/ô/bước</td><td>OpenFOAM thật</td></tr>
<tr><td>Lật 1 bit sau khi ký</td><td style="white-space:normal">Bị từ chối: <code>changed: system/fvSolution (size 660→660)</code></td><td>OpenFOAM thật</td></tr>
<tr><td>Case có <code>systemCall</code></td><td>Bị từ chối trước khi chạy bất cứ gì</td><td>OpenFOAM thật</td></tr>
<tr><td>Ép phân kỳ (Courant ≈ 20)</td><td style="white-space:normal">Tự chữa 2 lần: <code>deltaT</code> 0,1 → 0,05 → 0,025, quay về mốc t = 0,25, thêm upwind; chạy xong tới t = 3, Courant cực đại 1,15</td><td>OpenFOAM thật</td></tr>
<tr><td>Hết hạn phiên</td><td style="white-space:normal">Dừng sạch sau 65 s (cửa sổ 72 s), 6 502 bước, CPU bận 99,6 %</td><td>OpenFOAM thật</td></tr>
<tr><td>Hai biến thể đồng thời</td><td style="white-space:normal">Mỗi biến thể 2 tiến trình trong bộ lõi riêng {{0,1}} và {{2,3}}, cả hai xong</td><td>OpenFOAM thật</td></tr>
<tr><td>Chuyển trực tuyến giữa chừng</td><td style="white-space:normal">Bộ tăng tốc thay thế (GAMG → PCG) sẵn sàng sau 2 s; tại t = 0,35 solver ghi mốc, dừng, đổi bộ giải, chạy tiếp 746 bước tới hết; đo CPU 0,0081 s/bước, sau khi đổi 0,0074 s/bước</td><td>OpenFOAM thật</td></tr>
<tr><td>Làn mô hình cùng lúc với OpenFOAM</td><td style="white-space:normal">Mô hình bị giam trong CPU 3, không thấy token GitHub, bộ đệm trong RAM; job OpenFOAM chạy xong trong lúc mô hình còn chạy</td><td>OpenFOAM thật</td></tr>
<tr><td>Chuỗi Mac → Git → G4</td><td style="white-space:normal">submit đẩy lên kho Git trần, bộ theo dõi clone vào RAM, khớp SHA-256, chạy job, mã thoát 0</td><td>Kho Git cục bộ thay GitHub</td></tr>
<tr><td>Lỗi thật tìm ra khi chạy</td><td style="white-space:normal">7 lỗi đã sửa: dòng khởi động “Floating point exception trapping” bị coi là phân kỳ; cảnh báo PWD của OpenFOAM làm hỏng giá trị đọc về; <code>--cpu-set</code> xung đột <code>--map-by</code>; thư mục biến thể cũ còn sót; lỗi trong luồng biến thể bị nuốt; lệnh dừng bị bỏ qua vì <code>fileModificationSkew</code> 10 s; khởi động lại thừa khi job đã tới <code>endTime</code></td><td>OpenFOAM thật</td></tr>
<tr><td>Chưa kiểm thử được</td><td style="white-space:normal">Dựng và chạy OGL thật trên GPU, cài <code>openfoam14</code> bằng apt, đo băng thông GPU, chạy trên Colab thật: môi trường phát triển không có GPU và chặn dựng mã nguồn tải từ ngoài. Các phần này có đường lùi tự động về CPU và in lý do</td><td>—</td></tr>
</tbody></table></div>
"""


def build_v14_section() -> str:
    rows = []
    for grp, name, status, where, tag in V14_TABLE:
        cls = {"có": "do", "đổi": "n3", "cũ": "gt", "chặn": "uc"}[tag]
        label = {"có": "CÓ", "đổi": "ĐỔI", "cũ": "CŨ", "chặn": "CHẶN"}[tag]
        chip = cn_chip(int(grp[2])) if grp.startswith("CN") else E(grp)
        rows.append(f"<tr><td>{chip}</td><td>{E(name)}</td><td><span class=\"vf {cls}\">{label}</span> {E(status)}</td>"
                    f"<td><code>{E(where)}</code></td></tr>")
    return f"""
<h2 id="doi-chieu">Đối chiếu tên với mã nguồn OpenFOAM 14</h2>
<p class="sub">Mỗi tên lệnh, điều kiện biên và function object trong bảng chức năng được tìm trong mã nguồn OpenFOAM-14 (commit <code>ee38504</code>, ngày 26/10/2026) bằng cách đọc, không biên dịch. Tên của nhánh OpenCFD (v2606) chưa được đối chiếu mã nguồn ở bản này.</p>
<div class="scroll"><table class="v14"><thead><tr><th>Nhóm</th><th>Tên trong báo cáo</th><th>Ở OpenFOAM 14</th><th>Chỗ tìm thấy</th></tr></thead><tbody>
{''.join(rows)}
</tbody></table></div>
<p>Kế hoạch Allrun của bộ chạy được thử trên toàn bộ tutorial của v14: trong <b>195</b> tutorial có <code>Allrun</code>, <b>180</b> có bước giải; <b>125</b> chỉ gồm lệnh trong danh sách cho phép trước bước giải nên chạy tự động được; <b>55</b> bị từ chối rõ ràng vì gọi script phụ (<code>./Allmesh</code>, <code>foamMergeCase</code>) hoặc đối số không kiểm được trước bước giải. Đây là phân tích tĩnh, chưa chạy từng tutorial.</p>
"""


# ----------------------------------------------------------------- transform
def transform(src: str) -> str:
    t = src

    # nav: keep every original link, add the new sections; highlight what is new in this version
    old_nav = re.search(r'<nav aria-label="Mục lục">.*?</nav>', t).group(0)
    nav = old_nav.replace(' class="new"', "")
    nav = nav.replace('<a href="#vong-doi">Quy trình</a>', '<a class="new" href="#thuc-thi">Tầng thực thi</a><a href="#vong-doi">Quy trình</a>')
    nav = nav.replace('<a href="#hoc">Lộ trình học</a>', '<a class="new" href="#g4">Năng lực G4</a><a class="new" href="#song-song-cpu-gpu">CPU + GPU song song</a>'
                      '<a class="new" href="#may-tinh">Máy tính</a><a class="new" href="#tu-dong">Tự động hoá</a><a class="new" href="#doi-chieu">Đối chiếu v14</a><a href="#hoc">Lộ trình học</a>')
    nav = nav.replace('<a href="#ma-tran">Ma trận ứng dụng</a>', '<a class="new" href="#ma-tran">Ma trận ứng dụng</a>')
    t = must_replace(t, old_nav, nav)

    # lead + facts + what is new
    t = must_replace(t, "chỉ rõ ứng dụng nào dùng chức năng nào, và chỗ nào OpenFOAM chưa đủ.</p>",
                     "chỉ rõ ứng dụng nào dùng chức năng nào, và chỗ nào OpenFOAM chưa đủ.</p>\n"
                     '<p class="lead">Bản này thêm <b>tầng thực thi</b>: chín khâu <span class="tt">TT0</span>–<span class="tt">TT8</span> chạy tự động trên Colab G4, khâu TTk làm đúng nhóm chức năng CNk. Mac Mini M4 chỉ việc đẩy code; bộ chạy tự dùng hết lõi CPU ngay lập tức, dựng OGL ở nền rồi chuyển phần giải áp suất lên GPU giữa chừng khi đo thấy lợi, giao GPU rảnh cho mô hình của bạn, tự sửa lỗi và không lưu log hay dữ liệu.</p>')
    t = must_replace(t, "<div><dt>Nhóm chức năng</dt><dd>8 (CN1 đến CN8)</dd></div>\n</dl>",
                     "<div><dt>Nhóm chức năng</dt><dd>8 (CN1 đến CN8)</dd></div>\n"
                     "<div><dt>Tầng thực thi</dt><dd>9 khâu (TT0 đến TT8)</dd></div>\n"
                     "<div><dt>Máy chạy</dt><dd>Colab G4 · RTX PRO 6000</dd></div>\n</dl>")
    t = must_replace(t, "hãy đối chiếu với bản bạn cài.</p>\n</header>",
                     "hãy đối chiếu với bản bạn cài.</p>\n"
                     '<div class="new-box"><h3>Có gì mới trong bản này</h3><ul>'
                     '<li>Ma trận ứng dụng thành <a href="#ma-tran">ma trận ba tầng</a>: mỗi hàng có thêm khâu thực thi, hồ sơ chạy trên G4 và nút cổ chai; lọc được theo hồ sơ.</li>'
                     '<li><a href="#thuc-thi">Bảng tầng thực thi</a> TT0–TT8 nối CN với lệnh, máy, cổng kiểm tra và cách tự sửa lỗi.</li>'
                     '<li>Mỗi <a href="#chi-tiet">thẻ ứng dụng</a> có mục “Thực thi trên G4” với tutorial OpenFOAM 14 đã đối chiếu và lệnh chạy mẫu.</li>'
                     '<li><a href="#g4">Năng lực G4</a>, <a href="#song-song-cpu-gpu">CPU và GPU chạy song song, OGL dựng tự động</a>, <a href="#lan-mo-hinh">làn mô hình</a>, <a href="#may-tinh">máy tính năng lực</a>, <a href="#tu-dong">hướng dẫn tự động hoá Mac M4 → Colab G4</a> và <a href="#doi-chieu">đối chiếu tên với mã nguồn v14</a>.</li>'
                     '</ul><p class="sub" style="margin:6px 0 0">Không mục nào của bản trước bị bỏ; nội dung mới chỉ được thêm vào.</p></div>\n</header>')

    t = must_replace(t, "<style>\n/* Bố cục:", "<style>\n/* Bố cục:")  # sanity: original style block present
    t = must_replace(t, "\n</style>\n\n<div class=\"wrap\">", CSS + "</style>\n\n<div class=\"wrap\">")

    # three layers -> execution layer
    t = must_replace(t, '<h2 id="tang">Ba tầng: mục tiêu, chức năng, tệp</h2>',
                     '<h2 id="tang">Ba tầng: mục tiêu, chức năng, tệp và thực thi</h2>')
    t = must_replace(t, "<h3>Tệp và lệnh</h3><p><code>0/</code>, <code>constant/</code>, <code>system/</code> và các chương trình gọi từ dòng lệnh. Đây là nơi bạn thật sự gõ.</p></div>",
                     "<h3>Tệp và lệnh, khâu thực thi</h3><p><code>0/</code>, <code>constant/</code>, <code>system/</code> và các chương trình gọi từ dòng lệnh. Đây là nơi bạn thật sự gõ.</p>"
                     f"<p>Trên G4, chín khâu {tt_chip(0)}…{tt_chip(8)} chạy các lệnh đó tự động: TTk làm nhóm CNk, trong RAM, không lưu gì.</p></div>")
    t = must_replace(t, "để thấy một nhóm chức năng gánh bao nhiêu ứng dụng.</p>",
                     "để thấy một nhóm chức năng gánh bao nhiêu ứng dụng.</p>\n"
                     '<p>Hướng thứ ba, từ chức năng sang thực thi: mỗi nhóm <span class="cn">CNk</span> có đúng một khâu <span class="tt">TTk</span> cùng chỉ số (cột cuối bảng dưới), và <a href="#thuc-thi">bảng tầng thực thi</a> cho biết khâu đó chạy lệnh gì, trên máy nào, qua cổng kiểm tra nào.</p>')

    # function catalog: one execution stage per group
    t = must_replace(t, "<th>Quyết định điều gì</th><th>Chủ đạo ở</th></tr></thead>",
                     "<th>Quyết định điều gì</th><th>Chủ đạo ở</th><th>Khâu thực thi</th></tr></thead>")
    t, n = re.subn(r'(<tr id="cn(\d)">.*?<td>\d+ / 21</td>)</tr>', lambda m: m.group(1) + f"<td>{tt_chip(int(m.group(2)))}</td></tr>", t, flags=re.S)
    if n != 8:
        raise SystemExit(f"catalog rows patched: {n}")

    # execution-layer table right after the catalog
    i8 = t.index('<tr id="cn8">')
    end = t.index("</tbody></table></div>", i8) + len("</tbody></table></div>")
    t = t[:end] + "\n" + build_tt_section() + t[end:]

    # lifecycle steps: pair every CN chip with its TT chip
    s0 = t.index('<ol class="steps">')
    s1 = t.index("</ol>", s0)
    steps = re.sub(r'(<a class="cn" href="#cn(\d)" title="[^"]*">CN\d</a>)', lambda m: m.group(1) + tt_chip(int(m.group(2))), t[s0:s1])
    t = t[:s0] + steps + t[s1:]

    # matrix: header, colgroup width, rows, filters, reading note
    t = must_replace(t, '<th scope="col">Mức hỗ trợ</th></tr></thead>',
                     '<th scope="col">Khâu thực thi</th><th scope="col">Hồ sơ G4</th><th scope="col">Nút cổ chai</th><th scope="col">Mức hỗ trợ</th></tr></thead>')
    t = t.replace('<th colspan="10" scope="colgroup">', '<th colspan="13" scope="colgroup">')
    for a in apps.APPS:
        pat = re.compile(r'(<tr data-s="' + a["s"] + r'")(><td><a class="go" href="#' + a["id"] + r'">.*?)(<td><span class="b [a-z]+">[^<]+</span></td></tr>)', re.S)
        m = pat.search(t)
        if not m:
            raise SystemExit(f"matrix row {a['id']} not found")
        t = t[:m.start()] + m.group(1) + f' data-p="{apps.derive_profile(a)}"' + m.group(2) + matrix_extra_cells(a) + m.group(3) + t[m.end():]
    prof_counts = {p: sum(1 for a in apps.APPS if apps.derive_profile(a) == p) for p in apps.PROFILES}
    pbtn = "".join(f'<button class="flt" type="button" data-g="{p}" aria-pressed="false">{E(apps.PROFILES[p])} <i>{prof_counts[p]}</i></button>'
                   for p in apps.PROFILES)
    t = must_replace(t, '<button class="flt" type="button" data-f="out" aria-pressed="false">Ngoài phạm vi <i>1</i></button></div>',
                     '<button class="flt" type="button" data-f="out" aria-pressed="false">Ngoài phạm vi <i>1</i></button></div>\n'
                     '<div class="flts" role="group" aria-label="Lọc theo hồ sơ chạy trên G4"><span class="flt-label">Hồ sơ G4:</span>'
                     f'<button class="flt" type="button" data-g="all" aria-pressed="true">Tất cả <i>21</i></button>{pbtn}</div>')
    t = must_replace(t, '<h2 id="ma-tran">Ma trận: ứng dụng nào cần chức năng nào</h2>',
                     '<h2 id="ma-tran">Ma trận: ứng dụng nào cần chức năng nào, chạy bằng khâu nào trên G4</h2>')
    t = must_replace(t, "Bấm tên ứng dụng để nhảy tới thẻ.</p>",
                     "Bấm tên ứng dụng để nhảy tới thẻ.</p>\n"
                     '<p class="sub">Ba cột mới nối sang tầng thực thi. <b>Khâu thực thi</b> suy thẳng từ các chấm: TT0 luôn có, rồi <span class="tt">TTk</span> nền đặc cho mỗi CNk chủ đạo và viền đứt cho CNk phụ trợ. <b>Hồ sơ G4</b> theo một quy tắc: ngoài phạm vi thì không chạy; có ghép chương trình khác lúc chạy (preCICE) thì ghép nhiều chương trình; phương pháp hạt, hoá học, điện tĩnh hoặc lưới nhỏ thì CPU; VoF, Euler–Euler, nhiều vùng hoặc vùng quay thì CPU và thử GPU bằng A/B; còn lại (áp suất chiếm phần lớn thời gian) thì CPU + GPU. Bộ chạy áp cùng quy tắc lên chính case khi chạy.</p>')
    t = must_replace(t, "Hàng nào có CN5 chủ đạo thì đó là chỗ OpenFOAM một mình chưa đủ.</p>",
                     "Hàng nào có CN5 chủ đạo thì đó là chỗ OpenFOAM một mình chưa đủ.</p>\n"
                     f'<p class="sub">Cách đọc hồ sơ: {prof_counts["cpu_gpu"]} ứng dụng có thể đưa áp suất lên GPU, {prof_counts["cpu_ab"]} cần thử A/B, {prof_counts["cpu"]} chạy thuần CPU, {prof_counts["coupled"]} cần ghép chương trình khác và {prof_counts["none"]} nằm ngoài OpenFOAM. Ở mọi hồ sơ, bộ chạy đều dùng hết lõi CPU; chỉ phần GPU là khác nhau.</p>')

    # cards: profile attribute + execution block before the boundary row
    for a in apps.APPS:
        head = f'<article class="app" id="{a["id"]}" data-s="{a["s"]}">'
        t = must_replace(t, head, f'<article class="app" id="{a["id"]}" data-s="{a["s"]}" data-p="{apps.derive_profile(a)}">')
        start = t.index(f'id="{a["id"]}"')
        stop = t.index("</article>", start)
        seg = t[start:stop]
        k = seg.rfind("<div><dt>Ranh giới</dt>")
        if k < 0:
            raise SystemExit(f"no boundary row in {a['id']}")
        seg = seg[:k] + card_exec_row(a) + seg[k:]
        t = t[:start] + seg + t[stop:]

    # worked example: execution column
    t = must_replace(t, "<thead><tr><th>Bước</th><th>Chức năng</th><th>Lệnh hoặc tệp</th><th>Tiêu chí xong</th></tr></thead>",
                     "<thead><tr><th>Bước</th><th>Chức năng</th><th>Lệnh hoặc tệp</th><th>Tiêu chí xong</th><th>Thực thi trên G4</th></tr></thead>")
    ex = [
        ("Mục tiêu và đại lượng đo", f"{tt_chip(6)}{tt_chip(8)} trường <code>kpi</code> của job; độ trôi &lt; 1 %"),
        ("Lưới", f"{tt_chip(1)} v14: <code>surfaceFeatures</code>; snappyHexMesh trên 24 tiến trình"),
        ("Điều kiện", f"{tt_chip(2)} trường <code>set</code> của job, ví dụ tốc độ vào"),
        ("Vật lý và bộ giải", f"{tt_chip(3)}{tt_chip(4)} <code>foamRun</code>; áp suất lên GPU nếu thử A/B thắng"),
        ("Chạy song song", f"{tt_chip(4)} 24 tiến trình ghim lõi, tự động"),
        ("Đo", f"{tt_chip(6)} KPI <code>Cd</code> mean_last 100"),
        ("Kiểm chứng", f"{tt_chip(8)} hai job: lưới gốc và lưới mịn, so Cd"),
        ("Bàn giao", f"{tt_chip(7)} <code>./foamctl submit</code>; kết quả hiện trên màn hình, không lưu"),
    ]
    for label, cell in ex:
        pat = re.compile(r"(<tr><td>" + re.escape(label) + r"</td>.*?)</tr>", re.S)
        m = pat.search(t, t.index('<h2 id="vi-du">'))
        if not m:
            raise SystemExit(f"worked example row {label}")
        t = t[:m.start()] + m.group(1) + f"<td style=\"white-space:normal\">{cell}</td></tr>" + t[m.end():]

    # boundaries: add, do not remove
    t = must_replace(t, "OpenFOAM cho dữ liệu vật lý tính sẵn chứ không dựng cảnh.</li>\n</ul>",
                     "OpenFOAM cho dữ liệu vật lý tính sẵn chứ không dựng cảnh.</li>\n"
                     "<li><b>GPU chỉ gánh phần giải áp suất.</b> Lắp ráp ma trận, mô hình rối, hoá học và hạt vẫn chạy trên CPU, nên tăng tốc toàn bài bị chặn bởi định luật Amdahl; bộ chạy đo bằng thử A/B trước khi giữ GPU.</li>\n"
                     "<li><b>Không lưu nghĩa là không có gì để xem lại.</b> Muốn giữ trường kết quả hay khung hình (ví dụ cho kỹ xảo), bạn phải tự bật lưu ngoài bộ chạy; bộ chạy cố ý không có tuỳ chọn đó.</li>\n</ul>")

    # new part III before the learning path
    t = must_replace(t, '<h2 id="hoc">Lộ trình học thực tế, theo ứng dụng</h2>',
                     build_g4_section() + build_auto_section() + build_v14_section() + '\n<h2 id="hoc">Lộ trình học thực tế, theo ứng dụng</h2>')

    # footer: append the sources of this version
    t = must_replace(t, "hãy xác nhận bằng <code>find $FOAM_TUTORIALS</code>.\n</footer>",
                     "hãy xác nhận bằng <code>find $FOAM_TUTORIALS</code>.\n"
                     '<p style="margin:10px 0 0">Nguồn của tầng thực thi (tra tháng 11/2026): '
                     '<a href="https://www.linkedin.com/posts/google-colab_we-just-added-support-for-nvidia-g4-rtx-activity-7435739505883619328-G5sp">Colab thêm GPU G4</a> · '
                     '<a href="https://cloud.google.com/blog/products/compute/g4-vms-powered-by-nvidia-rtx-6000-blackwell-gpus-are-ga">máy ảo G4 GA</a> · '
                     '<a href="https://gcloud-compute.com/g4-standard-48.html">g4-standard-48</a> · '
                     '<a href="https://flopper.io/gpu/nvidia-rtx-pro-6000-blackwell-server-edition">RTX PRO 6000 Server (thông số)</a> · '
                     '<a href="https://www.nvidia.com/content/dam/en-zz/Solutions/products/workstations/professional-desktop-gpus/rtx-pro-6000-max-q/workstation-datasheet-blackwell-rtx-pro-6000-max-q-nvidia-us-5349650-web.pdf">datasheet NVIDIA (CUDA 12.8)</a> · '
                     '<a href="https://research.google.com/colaboratory/runtime-version-faq.html">phiên bản runtime Colab</a> · '
                     '<a href="https://cloud.google.com/colab/docs/manage-access-notebook">tuỳ chọn không lưu đầu ra</a> · '
                     '<a href="https://fastero.com/blog/google-colab-pro">giá Colab (bên thứ ba)</a> · '
                     '<a href="https://openfoam.org/news/v14-patch/">OpenFOAM 14: gói Ubuntu và ARM64</a> · '
                     '<a href="https://www.openfoam.com/download">OpenFOAM v2606</a> · '
                     '<a href="https://github.com/OpenFOAM/OpenFOAM-14">mã nguồn OpenFOAM-14</a> · '
                     '<a href="https://github.com/hpsim/OGL">OGL (Ginkgo)</a> · '
                     '<a href="https://develop.openfoam.com/modules/external-solver">PETSc4FOAM</a> · '
                     '<a href="https://arxiv.org/abs/2512.22215">SPUMA</a> · '
                     '<a href="https://www.mdpi.com/2226-4310/10/9/792">GPU cho áp suất ≈ 2×</a> · '
                     '<a href="https://www.nafems.org/publications/resource_center/nwc21-262-c/">AmgX tới 9×</a> · '
                     '<a href="https://www.hivenet.com/post/openfoam-gpu-state-of-play">tình hình GPU cho OpenFOAM (bài của nhà cung cấp)</a>.</p>\n'
                     "</footer>")

    # script: two filters (support level and G4 profile) + calculator
    s0 = t.index("<script>\n(function(){")
    s1 = t.index("</script>", s0) + len("</script>")
    t = t[:s0] + SCRIPT.replace("/*__CAPACITY__*/", capacity_js()).replace("__PRESETS__", presets_js()) + t[s1:]
    t = t.replace("__NTESTS__", str(NTESTS))
    return t


SCRIPT = r"""<script>
/*__CAPACITY__*/
(function(){
  var fS = 'all', fP = 'all';
  var bs = document.querySelectorAll('.flt[data-f]'), bp = document.querySelectorAll('.flt[data-g]');
  function apply(){
    document.querySelectorAll('[data-s]').forEach(function(el){
      var okS = fS === 'all' || el.getAttribute('data-s') === fS;
      var okP = fP === 'all' || el.getAttribute('data-p') === fP;
      el.hidden = !(okS && okP);
    });
    document.querySelectorAll('tr.gr').forEach(function(g){
      var n = g.nextElementSibling, any = false;
      while (n && !n.classList.contains('gr')) { if (!n.hidden) any = true; n = n.nextElementSibling; }
      g.hidden = !any;
    });
    document.querySelectorAll('.dom').forEach(function(d){ d.hidden = !d.querySelector('.app:not([hidden])'); });
    bs.forEach(function(b){ b.setAttribute('aria-pressed', String(b.getAttribute('data-f') === fS)); });
    bp.forEach(function(b){ b.setAttribute('aria-pressed', String(b.getAttribute('data-g') === fP)); });
  }
  bs.forEach(function(b){ b.addEventListener('click', function(){ fS = b.getAttribute('data-f'); apply(); }); });
  bp.forEach(function(b){ b.addEventListener('click', function(){ fP = b.getAttribute('data-g'); apply(); }); });
  document.querySelectorAll('a[href^="#ud"]').forEach(function(a){
    a.addEventListener('click', function(){
      var t = document.getElementById(a.getAttribute('href').slice(1));
      if (t && (t.hidden || (t.closest && t.closest('[hidden]')))) { fS = 'all'; fP = 'all'; apply(); }
    });
  });

  var form = document.getElementById('g4calc'), out = document.getElementById('c-out');
  if (!form || !out) return;
  var PRESETS = __PRESETS__;
  function num(id){ var v = parseFloat(document.getElementById(id).value); return isFinite(v) ? v : null; }
  function yn(b){ return b ? '<span class="yes">có</span>' : '<span class="no">không</span>'; }
  function fmt(x, d){ return Number(x).toLocaleString('vi-VN', {maximumFractionDigits: d}); }
  function run(){
    var inp = {cells_m: num('c-cells'), physics: document.getElementById('c-physics').value, iterations: num('c-iter'),
      variants: num('c-var'), cores_physical: num('c-cores'), ram_gb: num('c-ram'), vram_gb: num('c-vram'),
      cpu_bw_gbs: num('c-cbw'), gpu_bw_gbs: num('c-gbw'), pcie_gbs: num('c-pcie'), c_cell_us: num('c-ccell'),
      ogl_build_h: num('c-ogl'), cu_per_hour: num('c-cu'), session_hours: num('c-sess'), ami: document.getElementById('c-ami').checked,
      ogl_ready: document.getElementById('c-ready').checked};
    var e = g4Estimate(inp);
    var rows = [
      ['Ca chạy đồng thời × lõi mỗi ca', fmt(e.concurrent, 0) + ' × ' + fmt(e.cores_per_job, 0)],
      ['Tiến trình MPI mỗi ca', fmt(e.ranks, 0) + ' (' + fmt(e.cells_per_rank, 0) + ' ô/tiến trình)'],
      ['RAM cần mỗi ca', fmt(e.ram_need_gb, 1) + ' GB · vừa: ' + yn(e.ram_fit)],
      ['Lưới lớn nhất vừa RAM', fmt(e.cells_max_m, 1) + ' triệu ô'],
      ['Thời gian mỗi vòng trên CPU', fmt(e.t_iter_cpu_s, 4) + ' s'],
      ['Tăng tốc riêng bước áp suất', fmt(e.s_pressure, 2) + '×'],
      ['Tăng tốc toàn bài nếu bật GPU', fmt(e.speedup, 3) + '× (chi phí chép ' + fmt(e.overhead * 100, 2) + ' %)'],
      ['GPU được phép / vừa VRAM', yn(e.gpu_allowed) + ' / ' + yn(e.vram_fit) + ' (' + fmt(e.vram_need_gb, 1) + ' GB)'],
      ['(A) chỉ CPU', fmt(e.hours_cpu, 3) + ' giờ'],
      ['(B) dựng OGL xong mới chạy GPU', fmt(e.hours_gpu, 3) + ' giờ'],
      ['(C) CPU ngay + dựng nền + chuyển GPU', fmt(e.hours_par, 3) + ' giờ'],
      ['Bộ chạy chọn', e.use_gpu ? '<span class="yes">C: CPU và GPU song song</span>' : '<span class="no">A: chỉ CPU</span>'],
      ['Tổng thời gian', fmt(e.hours_total, 3) + ' giờ · vừa một phiên: ' + yn(e.fits_session)],
      ['Chi phí', fmt(e.cu, 2) + ' CU ≈ ' + fmt(e.usd, 2) + ' USD']
    ];
    out.innerHTML = '<div class="scroll"><table><tbody>' + rows.map(function(r){ return '<tr><td>' + r[0] + '</td><td>' + r[1] + '</td></tr>'; }).join('') + '</tbody></table></div>';
  }
  form.addEventListener('input', run);
  form.addEventListener('change', run);
  form.addEventListener('submit', function(ev){ ev.preventDefault(); });
  document.querySelectorAll('[data-preset]').forEach(function(b){
    b.addEventListener('click', function(){
      var p = PRESETS[b.getAttribute('data-preset')];
      document.getElementById('c-cells').value = p.cells_m;
      document.getElementById('c-physics').value = p.physics;
      document.getElementById('c-iter').value = p.iterations;
      document.getElementById('c-var').value = p.variants;
      document.getElementById('c-ami').checked = p.ami;
      document.getElementById('c-ready').checked = false;
      run();
    });
  });
  run();
})();
</script>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", help="also write the page body without the document skeleton here")
    a = ap.parse_args()
    with open(SRC, encoding="utf-8") as fh:
        src = fh.read()
    out = transform(src)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(out)
    print(f"wrote {OUT} ({len(out.encode('utf-8'))} bytes)")
    if a.artifact:
        body = out[out.index("<body>") + len("<body>"):out.rindex("</body>")].lstrip("\n")
        with open(a.artifact, "w", encoding="utf-8") as fh:
            fh.write(body)
        print(f"wrote {a.artifact} ({len(body.encode('utf-8'))} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
