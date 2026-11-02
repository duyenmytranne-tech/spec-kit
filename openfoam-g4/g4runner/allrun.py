"""Read an ``Allrun`` as data: an ordered list of allow-listed OpenFOAM tools.

Tutorials (and many user cases) describe their pre-processing in an Allrun
shell script. Running that script would execute arbitrary shell; instead the
runner parses only ``runApplication`` / ``runParallel`` lines, keeps the
tools on the allow-list below, checks every argument against a strict
pattern, and executes them itself with its own process counts. Anything
else in the script is reported and ignored.
"""

from __future__ import annotations

import re
import shlex
from typing import Dict, List, Tuple

#: utilities that only read dictionaries and write mesh/field data
PRE_TOOLS = {
    "blockMesh", "snappyHexMesh", "surfaceFeatures", "surfaceFeatureExtract", "extrudeMesh", "mirrorMesh",
    "refineMesh", "renumberMesh", "splitMeshRegions", "createPatch", "createZones", "topoSet", "createBaffles",
    "splitBaffles", "createNonConformalCouples", "mergeMeshes", "stitchMesh", "transformPoints", "extrudeToRegionMesh",
    "decomposePar", "setFields", "mapFields", "potentialFoam", "checkMesh", "patchSummary", "changeDictionary",
    "foamDictionary", "dsmcInitialise", "mdInitialise", "applyBoundaryLayer", "subsetMesh", "fluentMeshToFoam",
    "gmshToFoam", "ideasUnvToFoam", "chemkinToFoam", "foamListTimes",
}
#: steps whose output the zero-retention runner does not need
SKIP_TOOLS = {"reconstructPar", "reconstructParMesh", "foamToVTK", "foamToEnsight", "paraFoam", "foamLog",
              "foamPostProcess", "postProcess", "patchSummary", "foamListTimes"}
SOLVERS = {
    "foamRun", "foamMultiRun", "icoFoam", "simpleFoam", "pimpleFoam", "pisoFoam", "interFoam", "buoyantFoam",
    "buoyantSimpleFoam", "buoyantPimpleFoam", "rhoSimpleFoam", "rhoPimpleFoam", "rhoCentralFoam", "reactingFoam",
    "chtMultiRegionFoam", "multiphaseEulerFoam", "dsmcFoam", "mdFoam", "mdEquilibrationFoam", "electrostaticFoam",
    "mhdFoam", "chemFoam", "laplacianFoam", "scalarTransportFoam", "solidDisplacementFoam", "porousSimpleFoam",
    "shallowWaterFoam", "financialFoam", "XiFoam",
}
_ARG = re.compile(r"^[A-Za-z0-9_.,:=+/()-]{1,200}$")
_RUN = re.compile(r"^\s*(runApplication|runParallel)\s+(.*)$")
#: shell lines that never change the case content needed by the solver
_BENIGN = re.compile(
    r"^(cd |\. |source |echo |printf |#|set |export |unset |\}|\{|\(|\)|fi$|then$|else$|done$|do$|;;|esac$|"
    r"case |if |elif |while |for |\[ |shift$|usage|exit|wait$|true$|false$|"
    r"rm -rf constant/polyMesh/sets|find \. .*level.*-exec rm|mkdir |"
    r"cp \$\{?FOAM_TUTORIALS\}?/resources/)"
)


def parse(text: str, tutorials_root: str = "") -> Tuple[List[Dict], List[str]]:
    """Return (steps, ignored_lines). A step is {tool, args, parallel, kind}.

    Ignored lines that are not plainly harmless are kept; :func:`blockers`
    tells which of them come before the solver and so would change the case.
    """
    steps: List[Dict] = []
    ignored: List[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _RUN.match(line)
        if not m:
            if not _BENIGN.match(line):
                ignored.append(line)
                steps.append({"tool": None, "args": [], "parallel": False, "kind": "unsupported", "line": line})
            continue
        parallel = m.group(1) == "runParallel"
        try:
            toks = shlex.split(m.group(2).replace("$FOAM_TUTORIALS", tutorials_root).replace("${FOAM_TUTORIALS}", tutorials_root))
        except ValueError:
            ignored.append(line)
            continue
        # strip RunFunctions options: -s/-suffix X, -a/-append, -o/-overwrite, -np/-n N
        while toks and toks[0].startswith("-"):
            opt = toks.pop(0)
            if opt in ("-s", "-suffix", "-np", "-n") and toks:
                toks.pop(0)
        if not toks:
            ignored.append(line)
            continue
        tool, args = toks[0].split("/")[-1], toks[1:]
        if tool in SOLVERS:
            kind = "solver"
        elif tool in SKIP_TOOLS:
            kind = "skip"
        elif tool in PRE_TOOLS:
            kind = "pre"
        else:
            ignored.append(line)
            steps.append({"tool": None, "args": [], "parallel": parallel, "kind": "unsupported", "line": line})
            continue
        if any(not _ARG.match(a) for a in args):
            ignored.append(line + "   (argument rejected)")
            steps.append({"tool": None, "args": [], "parallel": parallel, "kind": "unsupported", "line": line})
            continue
        steps.append({"tool": tool, "args": args, "parallel": parallel, "kind": kind})
    return steps, ignored


def blockers(steps: List[Dict]) -> List[str]:
    """Unsupported lines before the first solver: skipping them would silently change the case."""
    out = []
    for s in steps:
        if s["kind"] == "solver":
            break
        if s["kind"] == "unsupported":
            out.append(s["line"])
    return out


def pre_solver(steps: List[Dict]) -> List[Dict]:
    """Runnable steps up to (not including) the first solver run."""
    out = []
    for s in steps:
        if s["kind"] == "solver":
            break
        if s["kind"] in ("pre", "skip"):
            out.append(s)
    return out


def first_solver(steps: List[Dict]) -> Dict:
    for s in steps:
        if s["kind"] == "solver":
            return s
    return {}
