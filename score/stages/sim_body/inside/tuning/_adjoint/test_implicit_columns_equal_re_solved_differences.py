"""The implicit Jacobian equals central differences of re-solved inner fits on a toy two-level problem (frames' poses
and shared constants, residuals nonzero at the optimum so Gauss-Newton differs from the full Hessian), and an
unconverged inner fit is refused.

Breaks (each applied once, seen red, reverted), in `tuning/_adjoint/__init__.py`: dropping the mixed term
(`moved` set to zeros) turns the columns test red; `schur_solve` skipping the couplings' reduction (`reduced = corner`)
turns the Schur and columns tests red; removing the `Unconverged` check turns the refusal test red; `stacked_jacobian` skipping `refused`
(no check before use) turns the stacked refusal test red; dropping the prior's block turns the stacked test red;
in `_taped.py`, dropping `tape.zero()` (a second gradient adds onto the first's) turns the taped gradient test red; skipping
the turn rows' launch turns it red; dropping the followers' launch (couplings) turns it red; reading level 2's
inside-joint gradient as zeros (`_Constants.gradient`) turns it red; reading only the first frame's copy of a constant
in a batched body (`_Constants.gradient` taking `[0]` in place of `.sum(axis=0)`) turns it red. Ignoring the outer
unknowns' trust (`TapedSites._evaluate` not assigning `self.weights` when `trusted`) turns it red. Assigning the trusts themselves when `ends` is given (`_weighed` returning `tail`) turns it red.

The taped test runs `_taped` (Newton eval_fk on a wp.Tape) in Newton's own Python on the card, a four-link chain with
three weighted sites and two link-frame turn rows, once on every coordinate and once with the last a follower of the
second (a polynomial coupling, the pose the three free coordinates), and once with level 2's constants (two free
sites' moves and the third joint's place move after the pose), and once batched (two frames as two copies of the chain
in one model, one launch, level 2's constants shared by both), and once with each site's trust an outer unknown, and once with the last site a group end and the
end weight and markers' goal outer unknowns: its gradient, asked twice, equals central differences of its cost to 1e-3 of the largest entry. With no
Newton Python (`SCORE_NEWTON_PYTHON`, else $PROPS_HOME/envs/newton_env) it is skipped."""
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


def test_the_taped_gradient_equals_central_differences_of_the_cost():
    python = _newton_python()
    if python is None:
        pytest.skip("no Newton Python (SCORE_NEWTON_PYTHON or $PROPS_HOME/envs/newton_env)")
    ran = subprocess.run([str(python), "-B", "-c", _TAPED_CHECK, str(pathlib.Path(__file__).parent)],
                         capture_output=True, text=True, timeout=110)
    assert ran.returncode == 0, ran.stderr[-2000:]
    gap = float(ran.stdout.rsplit("GAP", 1)[1])
    assert gap < 1e-3
