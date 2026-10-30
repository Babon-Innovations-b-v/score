"""The implicit Jacobian equals central differences of re-solved inner fits on a toy two-level problem (frames' poses
and shared constants, residuals nonzero at the optimum so Gauss-Newton differs from the full Hessian), and an
unconverged inner fit is refused, and level 1's outer rows (a per-frame distance's median and a root mean square)
equal differences of the measures they stand for.

Breaks (each applied once, seen red, reverted), in `tuning/_adjoint/__init__.py`: `rms_row` dropping its 1 / count
turns the outer rows test red; `case_rows` weighing joints 1.0 in place of
JOINT_SHARE turns the case rows test red; dropping the mixed term
(`moved` set to zeros) turns the columns test red; `schur_solve` skipping the couplings' reduction (`reduced = corner`)
turns the Schur and columns tests red; removing the `Unconverged` check turns the refusal test red; `stacked_jacobian` skipping `refused`
(no check before use) turns the stacked refusal test red; dropping the prior's block turns the stacked test red;
in `_taped.py`, dropping `tape.zero()` (a second gradient adds onto the first's) turns the taped gradient test red; skipping
the turn rows' launch turns it red; dropping the followers' launch (couplings) turns it red; reading level 2's
inside-joint gradient as zeros (`_Constants.gradient`) turns it red; reading only the first frame's copy of a constant
in a batched body (`_Constants.gradient` taking `[0]` in place of `.sum(axis=0)`) turns it red. Ignoring the outer
unknowns' trust (`TapedSites._evaluate` not assigning `self.weights` when `trusted`) turns it red. Assigning the trusts themselves when `ends` is given (`_weighed` returning `tail`) turns it red. In `_measures.py`,
skipping `self.centres.zero_()` (joint centres adding onto the last evaluation's) turns the taped measures test red.

The taped test runs `_taped` (Newton eval_fk on a wp.Tape) in Newton's own Python on the card, a four-link chain with
three weighted sites and two link-frame turn rows, once on every coordinate and once with the last a follower of the
second (a polynomial coupling, the pose the three free coordinates), and once with level 2's constants (two free
sites' moves and the third joint's place move after the pose), and once batched (two frames as two copies of the chain
in one model, one launch, level 2's constants shared by both), and once with each site's trust an outer unknown, and once with the last site a group end and the
end weight and markers' goal outer unknowns: its gradient, asked twice, equals central differences of its cost to 1e-3 of the largest entry. With no
Newton Python (`SCORE_NEWTON_PYTHON`, else $PROPS_HOME/envs/newton_env) it is skipped. The taped measures test runs
`_measures` on three copies of the chain (frames): two joints (one a MIDDLE of two parts) and two turn groups, fed
through `case_rows`, equal central differences of `case_residuals` to 1 % of the largest entry."""
import json
import os
import pathlib
import subprocess

import numpy as np
import pytest
import scipy.optimize

from score.stages.sim_body.inside.tuning import _adjoint

FRAMES, POSE, CONSTANTS, SPREAD = 4, 2, 2, 0.3
TIMES = np.linspace(0.0, 1.0, FRAMES)


def _parts(inner, outer):
    poses = inner[: FRAMES * POSE].reshape(FRAMES, POSE)
    constants = inner[FRAMES * POSE:]
    first, second = poses[:, 0], poses[:, 1]
    sine = np.sin(first) + constants[0] - outer[0] * (1 + TIMES)
    product = first * second + constants[1] - outer[1]
    return poses, constants, first, second, sine, product


def _gradient(inner, outer):
    poses, constants, first, second, sine, product = _parts(inner, outer)
    along_first = sine * np.cos(first) + product * second + (first - 0.5)
    along_second = product * first + (second - outer[2])
    by_constants = [sine.sum() + SPREAD * constants[0], product.sum() + SPREAD * constants[1]]
    return np.concatenate([np.stack([along_first, along_second], axis=1).ravel(), by_constants])


def _cost(inner, outer):
    poses, constants, first, second, sine, product = _parts(inner, outer)
    return 0.5 * (np.sum(sine ** 2) + np.sum(product ** 2) + np.sum((second - outer[2]) ** 2)
                  + np.sum((first - 0.5) ** 2) + SPREAD * np.sum(constants ** 2))


def _residuals(inner, outer):
    poses, constants, first, second, _, _ = _parts(inner, outer)
    return np.concatenate([first + second - outer[2], first * constants[0], [constants[1] * outer[1]]])


def _solved(outer):
    found = scipy.optimize.minimize(_cost, np.full(FRAMES * POSE + CONSTANTS, 0.2), args=(outer,), jac=_gradient,
                                    method="BFGS", options={"gtol": 1e-13, "maxiter": 10000})
    return found.x


OUTER = np.array([0.4, 0.9, -0.3])


def test_implicit_columns_equal_re_solved_differences():
    inner = _solved(OUTER)
    implicit = _adjoint.implicit_jacobian(_residuals, _gradient, inner, OUTER, FRAMES, POSE, (1e-5, 1e-5), 1e-8)
    re_solved = _adjoint.by_columns(lambda point: _residuals(_solved(point), point), OUTER, 1e-4)
    assert np.allclose(implicit, re_solved, rtol=1e-4, atol=1e-6)


def test_schur_solve_equals_the_dense_solve():
    inner = _solved(OUTER)
    blocks, couplings, corner = _adjoint.arrow_hessian(_gradient, inner, OUTER, FRAMES, POSE, 1e-5)
    dense = _adjoint.by_columns(lambda point: _gradient(point, OUTER), inner, 1e-5)
    right = np.random.default_rng(0).normal(size=(len(inner), 3))
    assert np.allclose(_adjoint.schur_solve(blocks, couplings, corner, right), np.linalg.solve(dense, right),
                       rtol=1e-5, atol=1e-7)


def test_an_unconverged_inner_fit_is_refused():
    with pytest.raises(_adjoint.Unconverged):
        _adjoint.implicit_jacobian(_residuals, _gradient, np.full(FRAMES * POSE + CONSTANTS, 0.2), OUTER, FRAMES,
                                   POSE, (1e-5, 1e-5), 1e-8)


def _body(name, inner):
    return _adjoint.Body(name, _residuals, _gradient, inner, FRAMES, POSE)


def _prior(outer):
    return outer ** 2


def test_stacked_jacobian_is_each_body_then_the_prior():
    inner = _solved(OUTER)
    stacked = _adjoint.stacked_jacobian([_body("one", inner), _body("two", inner)], OUTER, _prior, (1e-5, 1e-5), 1e-8)
    one = _adjoint.implicit_jacobian(_residuals, _gradient, inner, OUTER, FRAMES, POSE, (1e-5, 1e-5), 1e-8)
    assert np.allclose(stacked, np.concatenate([one, one, np.diag(2 * OUTER)]), atol=1e-8)


def test_the_stacked_jacobian_names_every_unconverged_body():
    stopped = np.full(FRAMES * POSE + CONSTANTS, 0.2)
    with pytest.raises(_adjoint.Unconverged, match="two .*three"):
        _adjoint.stacked_jacobian([_body("one", _solved(OUTER)), _body("two", stopped), _body("three", stopped)],
                                  OUTER, _prior, (1e-5, 1e-5), 1e-8)


_TAPED_CHECK = """
import sys, numpy as np, warp as wp, newton
sys.path.insert(0, sys.argv[1])
import _taped
builder = newton.ModelBuilder()
parent = -1
for index in range(4):
    body = builder.add_link(mass=1.0)
    place = wp.transform(wp.vec3(0.0, 0.0, 0.3 if index else 0.0), wp.quat_identity())
    axis = (1.0, 0.0, 0.0) if index % 2 == 0 else (0.0, 1.0, 0.0)
    builder.add_joint_revolute(parent, body, parent_xform=place, axis=axis)
    parent = body
builder.add_articulation(list(range(4)))
model = builder.finalize(device="cuda:0", requires_grad=True)
turns = ([2, 3], [1.5, 0.7], [[0.1, 0.2, 0.0, 0.9747], [0.0, -0.3, 0.1, 0.9487]],
         [[0.0, 0.0, 0.0, 1.0], [0.05, 0.0, 0.0, 0.99875]])
sites = _taped.TapedSites(model, [1, 3, 3], [1.0, 2.0, 0.5], [[0.1, 0.2, 0.5], [0.3, -0.2, 1.0], [0.0, 0.1, 0.8]],
                          turns)
pose = np.array([0.2, 0.4, -0.3, 0.6])
outer = np.array([0.05, 0.0, 0.1, 0.02, 0.03, 0.1, -0.04, 0.0, 0.05])
sites.gradient(pose, outer)
taped = sites.gradient(pose, outer)
def cost(moved):
    found = sites.residuals(moved, outer)
    return 0.5 * float(found @ found)
step = 1e-3
differences = np.array([(cost(pose + step * np.eye(4)[axis]) - cost(pose - step * np.eye(4)[axis])) / (2 * step)
                        for axis in range(4)])
assert np.abs(sites.residuals(pose, outer)[9:]).min() > 1e-3, "turn rows missing from the cost"
coupled = _taped.TapedSites(model, [1, 3, 3], [1.0, 2.0, 0.5],
                            [[0.1, 0.2, 0.5], [0.3, -0.2, 1.0], [0.0, 0.1, 0.8]], turns,
                            ([0, 1, 2], [3], [1], [0.1], [0.05], [[0.0, 0.8, -0.6, 0.3, 0.0]], [0.0, 0.0, 0.0, 0.1]))
free = np.array([0.2, 0.4, -0.3])
coupled.gradient(free, outer)
coupled_taped = coupled.gradient(free, outer)
def coupled_cost(moved):
    found = coupled.residuals(moved, outer)
    return 0.5 * float(found @ found)
coupled_differences = np.array([(coupled_cost(free + step * np.eye(3)[axis])
                                 - coupled_cost(free - step * np.eye(3)[axis])) / (2 * step) for axis in range(3)])
lead = free[1] - 0.05
expanded = np.append(free, 0.1 + 0.8 * lead - 0.6 * lead ** 2 + 0.3 * lead ** 3)
assert np.abs(coupled.residuals(free, outer) - sites.residuals(expanded, outer)).max() < 1e-5, "follower not coupled"
constant = _taped.TapedSites(model, [1, 3, 3], [1.0, 2.0, 0.5],
                             [[0.1, 0.2, 0.5], [0.3, -0.2, 1.0], [0.0, 0.1, 0.8]], turns, None, ([0, 2], [2]))
moved_inner = np.concatenate([pose, [0.02, -0.01, 0.03, 0.0, 0.04, -0.02, 0.01, 0.02, -0.03]])
constant.gradient(moved_inner, outer)
constant_taped = constant.gradient(moved_inner, outer)
def constant_cost(moved):
    found = constant.residuals(moved, outer)
    return 0.5 * float(found @ found)
width = len(moved_inner)
constant_differences = np.array([(constant_cost(moved_inner + step * np.eye(width)[axis])
                                  - constant_cost(moved_inner - step * np.eye(width)[axis])) / (2 * step)
                                 for axis in range(width)])
assert np.abs(constant_differences[-3:]).max() > 1e-3, "inside joint's move not in the cost"
gaps = [np.abs(taped - differences).max() / np.abs(differences).max(),
        np.abs(coupled_taped - coupled_differences).max() / np.abs(coupled_differences).max(),
        np.abs(constant_taped - constant_differences).max() / np.abs(constant_differences).max()]
batch_builder = newton.ModelBuilder()
for copy in range(2):
    parent = -1
    for index in range(4):
        body = batch_builder.add_link(mass=1.0)
        place = wp.transform(wp.vec3(0.0, 0.0, 0.3 if index else 0.0), wp.quat_identity())
        axis = (1.0, 0.0, 0.0) if index % 2 == 0 else (0.0, 1.0, 0.0)
        batch_builder.add_joint_revolute(parent, body, parent_xform=place, axis=axis)
        parent = body
    batch_builder.add_articulation(list(range(4 * copy, 4 * copy + 4)))
batch_model = batch_builder.finalize(device="cuda:0", requires_grad=True)
batch_targets = [[0.1, 0.2, 0.5], [0.3, -0.2, 1.0], [0.0, 0.1, 0.8], [0.2, 0.1, 0.4], [0.1, -0.1, 0.9], [-0.1, 0.2, 0.7]]
batched = _taped.TapedSites(batch_model, [1, 3, 3, 5, 7, 7], [1.0, 2.0, 0.5, 1.0, 2.0, 0.5], batch_targets, None, None,
                            ([[0, 2], [3, 5]], [[2], [6]]))
second_pose = np.array([-0.1, 0.3, 0.2, -0.4])
batch_inner = np.concatenate([pose, second_pose, moved_inner[4:]])
batch_outer = np.concatenate([outer, outer])
batched.gradient(batch_inner, batch_outer)
batch_taped = batched.gradient(batch_inner, batch_outer)
def batch_cost(moved):
    found = batched.residuals(moved, batch_outer)
    return 0.5 * float(found @ found)
batch_width = len(batch_inner)
batch_differences = np.array([(batch_cost(batch_inner + step * np.eye(batch_width)[axis])
                               - batch_cost(batch_inner - step * np.eye(batch_width)[axis])) / (2 * step)
                              for axis in range(batch_width)])
assert np.abs(batch_differences[8:11]).max() > 1e-3, "a free site's move not in the batched cost"
gaps.append(np.abs(batch_taped - batch_differences).max() / np.abs(batch_differences).max())
trusted = _taped.TapedSites(model, [1, 3, 3], [9.0, 9.0, 9.0],
                            [[0.1, 0.2, 0.5], [0.3, -0.2, 1.0], [0.0, 0.1, 0.8]], turns, trusted=True)
trust = np.array([1.0, 2.0, 0.5])
assert np.abs(trusted.residuals(pose, np.concatenate([outer, trust])) - sites.residuals(pose, outer)).max() < 1e-6, \
    "trust not read from the outer unknowns"
doubled = trusted.residuals(pose, np.concatenate([outer, 2 * trust]))
assert np.abs(doubled[:9] - 2 * sites.residuals(pose, outer)[:9]).max() < 1e-5, "trust not scaling its site's rows"
trusted_outer = np.concatenate([outer, trust])
trusted.gradient(pose, trusted_outer)
trusted_taped = trusted.gradient(pose, trusted_outer)
def trusted_cost(moved):
    found = trusted.residuals(moved, trusted_outer)
    return 0.5 * float(found @ found)
trusted_differences = np.array([(trusted_cost(pose + step * np.eye(4)[axis])
                                 - trusted_cost(pose - step * np.eye(4)[axis])) / (2 * step) for axis in range(4)])
gaps.append(np.abs(trusted_taped - trusted_differences).max() / np.abs(trusted_differences).max())
ended = _taped.TapedSites(model, [1, 3, 3], [9.0, 9.0, 9.0],
                          [[0.1, 0.2, 0.5], [0.3, -0.2, 1.0], [0.0, 0.1, 0.8]], turns, trusted=True, ends=1)
landmarks, end_weight, goal = np.array([1.0, 2.0]), 0.5, 3.0
all_trusts = np.array([1.0, 2.0, 0.5 * 1.5])
by_hand = np.sqrt(goal * all_trusts / all_trusts.sum())
ended_rows = ended.residuals(pose, np.concatenate([outer, landmarks, [end_weight, goal]]))
assert np.abs(ended_rows - trusted.residuals(pose, np.concatenate([outer, by_hand]))).max() < 1e-5, \
    "end weight and marker goal not read from the outer unknowns"
goal_doubled = ended.residuals(pose, np.concatenate([outer, landmarks, [end_weight, 2 * goal]]))
assert np.abs(goal_doubled[:9] - np.sqrt(2) * ended_rows[:9]).max() < 1e-5, "marker goal not scaling every site"
print("GAP", max(gaps))
"""


def _newton_python():
    """Newton's own Python: `SCORE_NEWTON_PYTHON`, else $PROPS_HOME/envs/newton_env's; None when neither exists."""
    named = os.environ.get("SCORE_NEWTON_PYTHON")
    if named:
        return pathlib.Path(named)
    found = pathlib.Path(os.environ.get("PROPS_HOME", "/nonexistent")) / "envs/newton_env/bin/python"
    return found if found.exists() else None


def _differences(unknowns):
    times = np.linspace(0.0, 1.0, 5)[:, None]
    return np.concatenate([np.sin(unknowns[0] + 3 * times), unknowns[1] * times + 0.2, np.cos(unknowns[2] * (1 + times))],
                          axis=1)


def _outer_values(unknowns):
    lengths, _ = _adjoint.distance_rows(_differences(unknowns), np.zeros((5, 3, 3)))
    return np.array([np.median(lengths), np.sqrt(np.mean(np.square(lengths)))])


def test_the_outer_rows_equal_differences_of_the_median_and_the_root_mean_square():
    unknowns = np.array([0.3, 0.7, 1.1])
    rows = _adjoint.by_columns(lambda point: _differences(point).ravel(), unknowns, 1e-6).reshape(5, 3, 3)
    lengths, length_rows = _adjoint.distance_rows(_differences(unknowns), rows)
    median, median_row = _adjoint.median_row(lengths, length_rows)
    root, root_row = _adjoint.rms_row(lengths, length_rows)
    expected = _adjoint.by_columns(_outer_values, unknowns, 1e-6)
    assert np.allclose([median, root], _outer_values(unknowns))
    assert np.allclose(np.stack([median_row, root_row]), expected, atol=1e-6)
    assert np.allclose(_adjoint.median_row(lengths[:4], length_rows[:4])[0], np.median(lengths[:4]))

def test_the_taped_gradient_equals_central_differences_of_the_cost():
    python = _newton_python()
    if python is None:
        pytest.skip("no Newton Python (SCORE_NEWTON_PYTHON or $PROPS_HOME/envs/newton_env)")
    ran = subprocess.run([str(python), "-B", "-c", _TAPED_CHECK, str(pathlib.Path(__file__).parent)],
                         capture_output=True, text=True, timeout=110)
    assert ran.returncode == 0, ran.stderr[-2000:]
    gap = float(ran.stdout.rsplit("GAP", 1)[1])
    assert gap < 1e-3


def _measured(unknowns):
    """A toy case's taped per-frame measures as functions of a 3-unknown inner pose (metres and degrees)."""
    lean = _differences(unknowns)
    return {"joints": {"LeftLeg": 0.01 * lean, "Hips": 0.02 * lean[::-1] + 0.005},
            "turns": {"Hips": 4 + 3 * lean[:, 0] * lean[:, 1], "LeftLeg": 6 + 2 * lean[:, 2]},
            "skins": {"pelvis": 0.002 * lean[:, 1], "thigh": 0.001 * (lean[:, 0] + 2)}}


def _found(unknowns):
    measured = _measured(unknowns)
    return {"per joint mm": {key: [np.median(1000 * np.linalg.norm(value, axis=1))]
                             for key, value in measured["joints"].items()},
            "per group deg": {key: [np.median(value)] for key, value in measured["turns"].items()},
            "bones outside depth mm": {key: 1000 * np.sqrt(np.mean(np.square(value)))
                                       for key, value in measured["skins"].items()}}


def test_the_taped_case_rows_equal_differences_of_the_case_residuals():
    from score.stages.sim_body.inside.tuning import case_residuals
    unknowns = np.array([0.3, 0.7, 1.1])
    measured = _measured(unknowns)
    rows = {kind: {key: _adjoint.by_columns(lambda point, kind=kind, key=key: np.ravel(_measured(point)[kind][key]),
                                            unknowns, 1e-6).reshape(*np.shape(value), 3)
                   for key, value in measured[kind].items()} for kind in measured}
    values, jacobian = _adjoint.case_rows(*({key: (value, rows[kind][key]) for key, value in measured[kind].items()}
                                            for kind in ("joints", "turns", "skins")))
    assert np.allclose(values, case_residuals(_found(unknowns)))
    expected = _adjoint.by_columns(lambda point: case_residuals(_found(point)), unknowns, 1e-6)
    assert np.allclose(jacobian, expected, atol=1e-6)


_MEASURES_CHECK = """
import sys, json, numpy as np, warp as wp, newton
sys.path.insert(0, sys.argv[1])
import _taped, _measures
builder = newton.ModelBuilder()
for copy in range(3):
    parent = -1
    for index in range(4):
        body = builder.add_link(mass=1.0)
        place = wp.transform(wp.vec3(0.0, 0.0, 0.3 if index else 0.0), wp.quat_identity())
        builder.add_joint_revolute(parent, body, parent_xform=place, axis=(1.0, 0.0, 0.0) if index % 2 == 0 else (0.0, 1.0, 0.0))
        parent = body
    builder.add_articulation(list(range(4 * copy, 4 * copy + 4)))
model = builder.finalize(device="cuda:0", requires_grad=True)
sites = _taped.TapedSites(model, [1], [1.0], [[0.0, 0.0, 0.5]])
to_own = [[1, 0, 0], [0, 0, 1], [0, -1, 0]]
joints = {"LeftLeg": ([[(4 * frame + 3, (0.0, 0.05, 0.1), 1.0)] for frame in range(3)], [[0.1, 0.8, -0.1], [0.0, 0.9, 0.0], [0.2, 0.7, 0.1]]),
          "Hips": ([[(4 * frame + 1, (0.02, 0.0, 0.0), 0.5), (4 * frame + 2, (0.0, 0.03, 0.0), 0.5)] for frame in range(3)],
                   [[0.05, 0.4, 0.0], [0.0, 0.45, 0.02], [0.03, 0.5, -0.02]])}
turns = {"LeftLeg": ([3, 7, 11], [0.05, 0.0, 0.0, 0.99875], [[0.1, 0.2, 0.0, 0.9747], [0.0, -0.3, 0.1, 0.9487], [0.2, 0.1, 0.1, 0.9695]]),
         "Hips": ([1, 5, 9], [0.0, 0.0, 0.0, 1.0], [[0.0, 0.1, 0.3, 0.9487], [0.1, 0.0, -0.2, 0.9747], [0.3, 0.0, 0.0, 0.9539]])}
measures = _measures.TapedMeasures(sites, joints, to_own, turns)
pose = np.array([0.2, 0.4, -0.3, 0.6, 0.1, -0.5, 0.3, 0.2, -0.2, 0.3, 0.5, -0.4])
outer = np.zeros(3)
def plain(found):
    return {kind: {key: [value[0].tolist(), value[1].tolist()] for key, value in part.items()} for kind, part in zip(("joints", "turns"), found)}
step, nudged = 1e-3, []
for column in range(len(pose)):
    for sign in (1, -1):
        moved = pose.copy(); moved[column] += sign * step
        nudged.append({kind: {key: value[0] for key, value in part.items()} for kind, part in plain(measures.measured(moved, outer)).items()})
print("JSON" + json.dumps({"taped": plain(measures.measured(pose, outer)), "nudged": nudged, "step": step}))
"""


def _case_found(joints, turns):
    """`case_residuals`' measures of per-frame joint differences (m) and turn degrees, with no skin regions."""
    return {"per joint mm": {key: [np.median(1000 * np.linalg.norm(value, axis=1))] for key, value in joints.items()},
            "per group deg": {key: [np.median(value)] for key, value in turns.items()}, "bones outside depth mm": {}}


def test_the_taped_measures_rows_equal_differences_of_the_case_residuals():
    from score.stages.sim_body.inside.tuning import case_residuals
    python = _newton_python()
    if python is None:
        pytest.skip("no Newton Python (SCORE_NEWTON_PYTHON or $PROPS_HOME/envs/newton_env)")
    ran = subprocess.run([str(python), "-B", "-c", _MEASURES_CHECK, str(pathlib.Path(__file__).parent)],
                         capture_output=True, text=True, timeout=110)
    assert ran.returncode == 0, ran.stderr[-2000:]
    found = json.loads(ran.stdout.rsplit("JSON", 1)[1])
    taped = {kind: {key: tuple(np.array(part) for part in value) for key, value in found["taped"][kind].items()}
             for kind in ("joints", "turns")}
    values, jacobian = _adjoint.case_rows(taped["joints"], taped["turns"], {})
    at = {kind: {key: value[0] for key, value in taped[kind].items()} for kind in taped}
    assert np.allclose(values, case_residuals(_case_found(at["joints"], at["turns"])), atol=1e-4)
    scored = [case_residuals(_case_found({key: np.array(value) for key, value in nudge["joints"].items()},
                                         {key: np.array(value) for key, value in nudge["turns"].items()}))
              for nudge in found["nudged"]]
    expected = np.stack([(scored[2 * column] - scored[2 * column + 1]) / (2 * found["step"])
                         for column in range(len(scored) // 2)], axis=1)
    assert np.abs(jacobian - expected).max() < 1e-2 * np.abs(expected).max()
