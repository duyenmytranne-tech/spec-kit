import math

from g4runner.monitor import LogParser

V14_LOG = """
trapFpe: Floating point exception trapping enabled (FOAM_SIGFPE).
sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).
Starting time loop

Time = 1

smoothSolver:  Solving for Ux, Initial residual = 1, Final residual = 0.0538, No Iterations 1
smoothSolver:  Solving for Uy, Initial residual = 1, Final residual = 0.0309, No Iterations 2
GAMG:  Solving for p, Initial residual = 1, Final residual = 0.068, No Iterations 17
ExecutionTime = 0.05 s  ClockTime = 0 s

Time = 2

smoothSolver:  Solving for Ux, Initial residual = 0.43, Final residual = 0.02, No Iterations 1
GAMG:  Solving for p, Initial residual = 0.2, Final residual = 0.01, No Iterations 9
Courant Number mean: 0.12 max: 0.85
ExecutionTime = 0.09 s  ClockTime = 0 s

SIMPLE solution converged in 2 iterations

End
"""


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        self.t += 0.5
        return self.t


def test_parses_v14_output():
    p = LogParser(clock=FakeClock())
    for line in V14_LOG.splitlines():
        p.feed(line)
    assert p.steps == 2 and p.time == 2.0
    assert p.residual == {"Ux": 0.43, "Uy": 1.0, "p": 0.2}
    assert p.first_residual["p"] == 1.0 and p.linear_iters["p"] == 9
    assert p.courant_max == 0.85 and p.exec_time == 0.09
    assert p.converged and p.ended
    assert not p.diverged, "the start-up FPE banner must not count as divergence"
    assert p.wall_per_step(skip=0) == 0.5


def test_nan_marks_divergence_with_time():
    p = LogParser()
    for line in ["Time = 0.3", "GAMG:  Solving for p, Initial residual = nan, Final residual = nan, No Iterations 1000"]:
        p.feed(line)
    assert p.diverged and p.first_bad_time == 0.3
    assert math.isnan(p.residual["p"])


def test_real_fpe_stack_frame_marks_divergence():
    p = LogParser()
    p.feed("Time = 0.4")
    p.feed("#1  Foam::sigFpe::sigHandler(int) at ??:?")
    assert p.diverged and p.first_bad_time == 0.4


def test_mpi_problems_are_classified():
    p = LogParser()
    p.feed("There are not enough slots available in the system to satisfy the 48 slots")
    assert p.mpi_problem == "slots"
    q = LogParser()
    q.feed("Read -1, expected 4096, errno = 1 ... vader single_copy mechanism failed in MPI")
    assert q.mpi_problem == "cma"


def test_checkmesh_failures_and_cells():
    p = LogParser()
    for line in ["    cells:            13824", "Failed 2 mesh checks."]:
        p.feed(line)
    assert p.cells == 13824 and p.mesh_failed == 2


def test_hook_is_called_and_reset_keeps_it():
    seen = []
    p = LogParser(hook=lambda parser, line: seen.append((parser.steps, line)))
    p.feed("Time = 1")
    p.reset()
    p.feed("Time = 2")
    assert seen == [(1, "Time = 1"), (1, "Time = 2")]
