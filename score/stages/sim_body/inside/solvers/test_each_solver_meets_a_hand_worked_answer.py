"""solvers: the bounded least squares, the least squares over a ball, the low-pass and the central differences each
give the answer worked out by hand (pure numpy and scipy: the score venv runs it).

Breaks (each applied once, seen red, reverted), 2026-10-28:
- least's line search `np.clip(x + size * step, lowest, highest)` made `x + size * step`: a bound is crossed.
- within_balls' projection `np.minimum(1.0, CAP_INSIDE / ...)` made `1.0`: the answer leaves its ball.
- smoothed's `filtfilt(...) if ... else moves` made `moves`: a 15 Hz shake at 30 frames a second goes through.
- stencils' `rate / (after - before)` made `rate`: a line's speed is doubled between its ends.

Each solver is driven once on its hand-worked problem; each row names one measure of those answers, the value worked
out by hand and how close it must come ("close": np.allclose at that atol; "within": the difference's norm of that
order under that bound).

Run: make tests TESTS=score/stages/sim_body/inside/solvers/test_each_solver_meets_a_hand_worked_answer.py
"""
import pathlib
import sys

import numpy as np
import pytest

INSIDE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INSIDE))
import solvers  # noqa: E402

RATE = 30.0  # frames a second
SHAKE = np.array([(-1.0) ** frame for frame in range(60)])  # 15 Hz at 30 frames a second
LINE = 0.1 * np.arange(6)  # rising 0.1 a frame: 3 a second


@pytest.fixture(scope="module")
def answers():
    """Each solver's answer to its hand-worked problem, by the measure the rows name.

    least: |x - (1, -1)|^2 + 0.01 |x|^2 over x >= 0, unbounded above and with x1 at most 0.5.
    within_balls: |y - (2, 0, 0)|^2 with |y| at most CAP_INSIDE (0.95).
    filter_matrix: the low-pass (6 Hz) at 30 frames a second over 60 frames, applied to the shake.
    stencils: the speeds and accelerations over 6 frames, applied to the line.
    """
    system, wanted, costs = np.eye(2), np.array([1.0, -1.0]), np.full(2, 0.1)
    found, furthest = solvers.within_balls(np.eye(3), np.array([2.0, 0.0, 0.0]), np.eye(3), np.zeros(3))
    matrix = solvers.filter_matrix(60, RATE)
    speeds, accelerations = solvers.stencils(6, RATE)
    return {
        "least unbounded above": solvers.least(system, wanted, costs, np.full(2, np.inf)),
        "least with x1 at most 0.5": solvers.least(system, wanted, costs, np.array([0.5, np.inf])),
        "ball answer": found,
        "ball furthest": furthest,
        "low-pass row sums": matrix.sum(axis=1),
        "low-pass shake, middle frames": (matrix @ SHAKE)[10:50],
        "line's speeds": speeds @ LINE,
        "line's accelerations": accelerations @ LINE,
    }


# (measure, hand-worked value, comparison, tolerance, norm order for "within")
ROWS = [
    # x1 = 1 / 1.01 and x2 held at 0 (its bound).
    ("least unbounded above", [1 / 1.01, 0.0], "close", 1e-8, None),
    # x1 capped at 0.5, x2 at its bound.
    ("least with x1 at most 0.5", [0.5, 0.0], "close", 1e-8, None),
    # y = (0.95, 0, 0), within ADMM's tolerance.
    ("ball answer", [solvers.CAP_INSIDE, 0.0, 0.0], "within", 5e-3, 2),
    ("ball furthest", solvers.CAP_INSIDE, "within", 5e-3, np.inf),
    # a constant is kept: each row sums to one.
    ("low-pass row sums", 1.0, "close", 1e-9, None),
    # the 15 Hz shake is taken out of the middle frames.
    ("low-pass shake, middle frames", 0.0, "within", 0.01, np.inf),
    # 3 a second at every frame, its ends included.
    ("line's speeds", 3.0, "close", 1e-8, None),
    ("line's accelerations", 0.0, "close", 1e-9, None),
]


@pytest.mark.parametrize("measure, expected, comparison, tolerance, order", ROWS, ids=[row[0] for row in ROWS])
def test_each_solver_meets_a_hand_worked_answer(answers, measure, expected, comparison, tolerance, order):
    """The measure of a solver's answer meets its hand-worked value within the row's tolerance."""
    found = np.asarray(answers[measure], dtype=float)
    if comparison == "close":
        assert np.allclose(found, expected, atol=tolerance), f"{measure}: {found}, not {expected}"
    else:
        apart = np.linalg.norm(np.ravel(found - np.asarray(expected, dtype=float)), order)
        assert apart < tolerance, f"{measure}: {found}, {apart} from {expected}"
