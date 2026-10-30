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


LEVEL2_CARD_MOST = 1e-5  # the same from the card's float32 kinematics (_level2_card)
LEVEL2_SOLVE_MM = 1e-3  # level 2 with jac=exact against 2-point differences on the exact toy: constants (the
LEVEL2_SOLVE_DEG = 1e-4  # plan's 0.05 mm / 0.01 deg is the real bodies'; a frozen Jacobian is 0.027 mm off here)
LEVEL2_MOST = 1e-6  # a column's largest miss over its largest entry (measured 1.8e-10; the plan allows 1e-2 against 2-point)


def the_level2_jacobian_equals_its_differences():
    import tempfile
    import numpy as np
    from fit._card import _level2, _level2_card
    with tempfile.TemporaryDirectory() as folder:
        problem, unknowns = problem_and_point(folder)
        card = _level2_card.CardKinematics(problem.fitting, len(problem.path))  # made at the start constants
        moved = differences(problem, unknowns)
        outside = ~problem.sparsity().toarray().astype(bool)
        found = {"card": (_level2.jacobian(problem, unknowns, card).toarray(), LEVEL2_CARD_MOST),
                 "host": (_level2.jacobian(problem, unknowns).toarray(), LEVEL2_MOST)}
    problems = []
    for source, (exact, most) in found.items():
        worst = max(np.abs(exact[:, column] - moved[:, column]).max() / max(np.abs(moved[:, column]).max(), 1e-12)
                    for column in range(unknowns.size))
        problems += ([f"{source} Jacobian off its differences by {worst:.2e} of a column"] if worst > most else []) + (
            [f"{source} Jacobian outside the sparse pattern"] if np.abs(exact[outside]).max() > 0 else [])
    return problems


def the_level2_solve_with_the_exact_jacobian_equals_differences():
    import tempfile
    import numpy as np
    with tempfile.TemporaryDirectory() as folder:
        (moved, moved_angles, _), (exact, exact_angles, _) = staged_both(folder)
    off_mm, off_angles = 1000 * np.abs(exact - moved).max(), np.abs(exact_angles - moved_angles).max()
    return ([f"level 2 with the exact Jacobian off differences' constants by {off_mm:.4f} mm"]
            if off_mm > LEVEL2_SOLVE_MM else []) + (
        [f"level 2 with the exact Jacobian off differences' angles by {off_angles:.2e}"]
        if off_angles > np.radians(LEVEL2_SOLVE_DEG) else [])


ACROSS_SETS = 3  # level 2 across sets: the toy's frames under this many sets' constants, one card model
ACROSS_SPREAD = 0.02  # each set's constants moved this far off the toy's (metres)


def the_frames_per_world_equal_each_set_alone():
    """Every frame of every set laid on one card model (each world its set's body_pos and site_pos) equals the same
    frames on a card model of that set alone, bit for bit."""
    import tempfile
    from fit._card import _level2_card
    with tempfile.TemporaryDirectory() as folder:
        problem, _ = problem_and_point(folder)
        model, frames = problem.fitting.model, len(problem.path)
        moved = np.random.default_rng(3)
        sets = [(model.body_pos + moved.normal(0.0, ACROSS_SPREAD, model.body_pos.shape) * (index > 0),
                 model.site_pos + moved.normal(0.0, ACROSS_SPREAD, model.site_pos.shape) * (index > 0))
                for index in range(ACROSS_SETS)]
        together = _level2_card.CardKinematics(problem.fitting, ACROSS_SETS * frames).frames(
            np.tile(problem.path, (ACROSS_SETS, 1)), np.repeat([body for body, _ in sets], frames, axis=0),
            np.repeat([site for _, site in sets], frames, axis=0))
        alone = _level2_card.CardKinematics(problem.fitting, frames)
        problems = []
        for index, (body, site) in enumerate(sets):
            for frame, own in enumerate(alone.frames(problem.path, body[None], site[None])):
                mine = together[index * frames + frame]
                worst = max(np.abs(getattr(mine, name) - getattr(own, name)).max()
                            for name in ("site_turns", "body_turns", "places", "spins"))
                problems += [f"set {index} frame {frame} off its set alone by {worst:.2e}"] if worst > 0 else []
        return problems


def the_batched_inverses_equal_each_row():
    """`_level2.left_jacobian_inverses`, one array pass over every frame and group, equals `left_jacobian_inverse`
    row by row to the float64 floor (2e-15), a near-zero rotation (its small-angle branch) among the rows."""
    from fit._card import _level2
    rotations = np.vstack([np.random.default_rng(5).normal(0.0, 1.0, (40, 3)), [[1e-9, 0.0, -2e-9], [0.0, 0.0, 0.0]]])
    batched = _level2.left_jacobian_inverses(rotations)
    worst = max(np.abs(batched[index] - _level2.left_jacobian_inverse(rotation)).max()
                for index, rotation in enumerate(rotations))
    return [f"batched inverse left Jacobians off each row's by {worst:.2e}"] if worst > 2e-15 else []
