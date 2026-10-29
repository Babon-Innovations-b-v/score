"""The level-2 check's problem: fit's own toy (a free pelvis, two legs, a coupled ankle, the knee a joint inside its
group; `../../test_the_solver_...py`'s `toy_fitting`), five of its frames, five markers free, the unknowns moved off
the start so the root's rotation vector and the moves are not zero; and the 2-point central differences of its
residuals, the reference the exact Jacobian is held to. Newton's Python (mujoco, scipy)."""
import importlib.util
import pathlib

import numpy as np

FIT = pathlib.Path(__file__).resolve().parents[2]
FREE_MARKS = 5
SPREAD = 0.05  # the unknowns' move off the start (metres, radians)
STEP = 1e-6


def toy_test():
    """fit's own test module (its toy, its targets)."""
    path = next(FIT.glob("test_*.py"))
    spec = importlib.util.spec_from_file_location("fit_toy_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def problem_and_point(folder):
    """The toy's constants problem and a point off its start."""
    from fit._constants import Problem
    toy = toy_test()
    fitting = toy.toy_fitting(folder)
    turns, points, _ = toy.posed_targets(fitting, toy.truth_of(fitting), toy.POSES[:-1])
    path = []
    for place, hip_l, knee_l, hip_r in toy.POSES[:-1]:
        qpos = fitting.model.qpos0.copy()
        qpos[:3] = place
        qpos[7:11] = hip_l, knee_l, hip_r, 0.5 * hip_r
        path.append(qpos)
    problem = Problem(fitting, np.array(path), turns, points, fitting.neutral(), list(range(FREE_MARKS)))
    start = problem.start()
    return problem, start + np.random.default_rng(1).normal(0.0, SPREAD, start.size)


def differences(problem, unknowns):
    """The residuals' central differences, column by column (dense)."""
    columns = []
    for column in range(unknowns.size):
        up, down = unknowns.copy(), unknowns.copy()
        up[column] += STEP
        down[column] -= STEP
        columns.append((problem.residuals(up) - problem.residuals(down)) / (2 * STEP))
    return np.array(columns).T


def staged_both(folder):
    """The toy's constants and angles by `_constants.staged` twice from the same start, the path's places and hinges
    moved SPREAD off the poses so the solve has a way to go: scipy's 2-point differences (the reference) and the exact
    Jacobian (`jacobian`, host kinematics)."""
    from fit._card import _level2
    from fit._constants import staged
    problem, _ = problem_and_point(folder)
    path = problem.path.copy()
    unturned = [index for index in range(path.shape[1]) if index not in range(3, 7)]
    path[:, unturned] += np.random.default_rng(2).normal(0.0, SPREAD, (len(path), len(unturned)))
    given = (problem.fitting, path, problem.turns, problem.points, problem.given, problem.free)
    return staged(*given), staged(*given, jacobian=_level2.jacobian)
