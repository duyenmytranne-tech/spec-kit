"""Generate a lid-driven 3D cavity of N^3 cells: the calibration case for the G4.

Used to measure the real cost per cell and step (``c_cell_us``) on the
session's hardware, and as the end-to-end test case. Dictionary syntax
follows each line's own tutorials: Foundation v14 ``incompressibleFluid``
(named units) and the OpenCFD classic ``icoFoam`` layout.
"""

from __future__ import annotations

import os

from .foam import write_dict


def _block_mesh(n: int) -> str:
    return f"""scale 0.1;

vertices
(
    (0 0 0) (1 0 0) (1 1 0) (0 1 0)
    (0 0 1) (1 0 1) (1 1 1) (0 1 1)
);

blocks
(
    hex (0 1 2 3 4 5 6 7) ({n} {n} {n}) simpleGrading (1 1 1)
);

boundary
(
    movingWall
    {{
        type wall;
        faces ((3 7 6 2));
    }}
    fixedWalls
    {{
        type wall;
        faces ((0 4 7 3) (2 6 5 1) (1 5 4 0) (0 3 2 1) (4 5 6 7));
    }}
);
"""


_FUNCTIONS = """
functions
{
    lidForce
    {
        type            forces;
        libs            ("libforces.so");
        writeControl    timeStep;
        writeInterval   1;
        patches         (movingWall);
        rho             rhoInf;
        rhoInf          1;
        CofR            (0 0 0);
        log             false;
    }
}
"""


def cavity3d(case: str, n: int, steps: int, branch: str, functions: bool = True) -> str:
    """Write the case; returns the solver/application name it uses.

    ``functions=False`` leaves out the force function object (needed on the
    Ubuntu 24.04 rebuild of OpenFOAM v1912, whose function-object digest is broken).
    """
    os.makedirs(case, exist_ok=True)
    dx = 0.1 / n
    dt = 0.5 * dx  # Courant ~0.5 at the lid speed of 1 m/s
    end = dt * steps
    write_dict(case, "system/blockMeshDict", _block_mesh(n), branch)
    if branch == "foundation":
        app_line, vel, kin, solver = "solver          incompressibleFluid;\n", "[velocity]", "[kinematicPressure]", "incompressibleFluid"
        write_dict(case, "constant/physicalProperties", "viscosityModel  constant;\n\nnu              1e-05 [m^2/s];\n", branch)
        write_dict(case, "constant/momentumTransport", "simulationType  laminar;\n", branch)
        algo = "PIMPLE"
    else:
        app_line, vel, kin, solver = "application     icoFoam;\n", "[0 1 -1 0 0 0 0]", "[0 2 -2 0 0 0 0]", "icoFoam"
        write_dict(case, "constant/transportProperties", "nu              [0 2 -1 0 0 0 0] 1e-05;\n", branch)
        algo = "PISO"
    write_dict(case, "system/controlDict", app_line + f"""
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         {end:.9g};
deltaT          {dt:.9g};
writeControl    timeStep;
writeInterval   {max(1, steps)};
purgeWrite      0;
writeFormat     binary;
writePrecision  8;
writeCompression off;
timeFormat      general;
timePrecision   8;
runTimeModifiable true;
""" + (_FUNCTIONS if functions else ""), branch)
    write_dict(case, "system/fvSchemes", """ddtSchemes { default Euler; }
gradSchemes { default Gauss linear; }
divSchemes { default none; div(phi,U) Gauss linear; }
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
""", branch)
    write_dict(case, "system/fvSolution", f"""solvers
{{
    p
    {{
        solver          GAMG;
        smoother        GaussSeidel;
        tolerance       1e-06;
        relTol          0.05;
    }}
    pFinal
    {{
        $p;
        relTol          0;
    }}
    "(U|UFinal)"
    {{
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-05;
        relTol          0;
    }}
}}

{algo}
{{
    nOuterCorrectors 1;
    nCorrectors     2;
    nNonOrthogonalCorrectors 0;
    pRefCell        0;
    pRefValue       0;
}}
""", branch)
    write_dict(case, "0/U", f"""dimensions      {vel};

internalField   uniform (0 0 0);

boundaryField
{{
    movingWall {{ type fixedValue; value uniform (1 0 0); }}
    fixedWalls {{ type noSlip; }}
}}
""", branch, cls="volVectorField")
    write_dict(case, "0/p", f"""dimensions      {kin};

internalField   uniform 0;

boundaryField
{{
    movingWall {{ type zeroGradient; }}
    fixedWalls {{ type zeroGradient; }}
}}
""", branch, cls="volScalarField")
    return solver
