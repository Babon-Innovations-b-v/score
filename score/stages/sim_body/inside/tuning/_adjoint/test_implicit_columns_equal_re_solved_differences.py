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
unknowns' trust (`TapedSites._evaluate` not assigning `self.weights` when `trusted`) turns it red. Assigning the trusts themselves when `ends` is given (`_weighed` returning `tail`) turns it red. Laying a batched body's weights site by site in place of copy by copy (`np.repeat` for `np.tile` in `_evaluate`) turns it red. In `_measures.py`,
skipping `self.centres.zero_()` (joint centres adding onto the last evaluation's) turns the taped measures test red.
Building the bone points without `requires_grad` (`_Skins.points`: no skin depth row reaches the pose) turns it red.
Cutting each seeded row from the first frame's block in place of its own (`_rows` with start 0) turns it red; `case_rows` laying a
skin point's block at frame 0 (`rms_row` ignoring `point_frames`) turns it red.
In `_bodies.py`, a copy's leaders not offset to its own pose (`copied_couplings`
without `copy * len(free)`) turns the copied couplings test red; `RootTurns.pulled` skipping the normalisation's
projection (`along` the raw turn gradient) turns the root chart test red. In `_outer.py`, the trusts' derivative without its LOG_UNIT factor (`site_derivative`) turns the outer map test red. In `_real.py`, `solved_rows`
giving MuJoCo's order (no `newton_order`) turns the real body test red; `frame_couplings` zeroing
the projection's polynomials turns its per-frame model check red; `bound_held` holding nothing (bound-held coordinates left in the pose) turns its refused check red (4.12e-3); `joint_parts`
dropping the centres' scales turns its joints check red; `turn_groups` without the frozen table turns its turns check red; `skin_parts` without the geom's turn turns its skins check red (0.19 m).

The taped test runs `_taped` (Newton eval_fk on a wp.Tape) in Newton's own Python on the card, a four-link chain with
three weighted sites and two link-frame turn rows, once on every coordinate and once with the last a follower of the
second (a polynomial coupling, the pose the three free coordinates), and once with level 2's constants (two free
sites' moves and the third joint's place move after the pose), and once batched (two frames as two copies of the chain
in one model, one launch, level 2's constants shared by both), and once with each site's trust an outer unknown, and once with the last site a group end and the
end weight and markers' goal outer unknowns, and once batched with a group end in each copy (`copies=2`, one frame's
outer unknowns laid on both: its rows equal each copy's own frame's): its gradient, asked twice, equals central differences of its cost to 1e-3 of the largest entry. With no
Newton Python (`SCORE_NEWTON_PYTHON`, else $PROPS_HOME/envs/newton_env) it is skipped; its run is `_check_taped.py`. The taped measures test runs (`_check_measures.py`)
`_measures` on three copies of the chain (frames): two joints (one a MIDDLE of two parts), two turn groups and two skin
regions' bone points against a posed box skin per frame (some outside, some inside), fed through `case_rows`, equal central differences of `case_residuals` to 1 % of the largest entry."""
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


_TABLE = {"knee_l": {"segment": "LeftLeg", "solver": True, "trust": 2.0, "link": [0.1, 0.2, 0.3]},
          "knee_r": {"segment": "RightLeg", "solver": True, "trust": 2.0, "link": [0.1, 0.2, -0.3]},
          "hip": {"segment": "Hips", "solver": False, "trust": 1.0, "link": [0.0, 0.1, 0.0]}}
_STARTS = {name: row["link"] for name, row in _TABLE.items()}
_GLOBALS = {"marker goal": 3.0, "end weight": 0.5}
_TURN = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
_ENDS = [("LeftUpLeg", np.array([0.0, -0.4, 0.0]), _TURN)]
_LANDMARKS = ["knee_l", "knee_r", "hip"]


def test_level_1_unknowns_map_onto_the_taped_outer_unknowns_with_their_derivative():
    from score.stages.sim_body.inside import tuning
    from score.stages.sim_body.inside.tuning._adjoint import _outer
    entries = tuning.layout(_TABLE, set(), {"knee_l"}, {"LeftUpLeg": ["LeftUpLeg"]})
    unknowns = np.linspace(-0.6, 0.9, len(entries))
    mapped = _outer.site_unknowns(unknowns, entries, _LANDMARKS, _ENDS, _STARTS, _TABLE, _GLOBALS)
    rows, weights = tuning.applied(unknowns, entries, _STARTS, _TABLE, _GLOBALS)
    centre = tuning.offsets(unknowns, entries)["LeftUpLeg"]
    assert np.allclose(mapped[:9], np.ravel([rows[name]["link"] for name in _LANDMARKS]))
    assert np.allclose(mapped[9:12], _ENDS[0][1] + _TURN @ centre)
    assert np.allclose(mapped[12:], [rows[name]["trust"] for name in _LANDMARKS]
                       + [weights["end weight"], weights["marker goal"]])
    expected = _adjoint.by_columns(
        lambda point: _outer.site_unknowns(point, entries, _LANDMARKS, _ENDS, _STARTS, _TABLE, _GLOBALS), unknowns, 1e-6)
    derivative = _outer.site_derivative(unknowns, entries, _LANDMARKS, _ENDS, _TABLE, _GLOBALS)
    assert np.allclose(derivative, expected, atol=1e-6)

def _followed(couplings, pose):
    """joint_q from a free pose as `_taped._Couplings.write` lays it (base, free coordinates, followers)."""
    free, followers, leaders, follower_rest, leader_rest, poly, base = couplings
    found = base.copy()
    found[free] = pose
    for follower, leader, rest, lead_rest, terms in zip(followers, leaders, follower_rest, leader_rest, poly):
        found[follower] = rest + np.polyval(terms[::-1], pose[leader] - lead_rest if leader >= 0 else 0.0)
    return found


def test_a_body_copied_per_frame_keeps_the_card_projection_couplings():
    from score.stages.sim_body.inside.tuning._adjoint import _bodies
    poly = np.array([[0.1, 0.5, 0.2, 0.0, 0.0], [0.0, -1.0, 0.0, 0.0, 0.0]])
    rows = np.random.default_rng(3).normal(size=(2, 11))
    rows[:, 9] = 0.4 + np.polyval(poly[0][::-1], rows[:, 7] - 0.2)  # led by a frozen coordinate: stays as solved
    rows[:, 10] = -0.3 + np.polyval(poly[1][::-1], rows[:, 8] - 0.1)
    couplings = _bodies.copied_couplings([9, 10], [7, 8], [0.4, -0.3], [0.2, 0.1], poly, [7], rows)
    pose = _bodies.pose_of(couplings, rows)
    assert len(pose) == 2 * 8
    assert np.allclose(_followed(couplings, pose), rows.reshape(-1))
    moved = pose + 0.05
    expanded = _followed(couplings, moved).reshape(2, 11)
    assert np.allclose(expanded[:, 10], -0.3 + np.polyval(poly[1][::-1], expanded[:, 8] - 0.1))
    with pytest.raises(ValueError):
        _bodies.copied_couplings([9, 10], [7, 9], [0.4, -0.3], [0.2, 0.1], poly, [], rows)


def test_the_root_turn_charted_as_three_tangent_dofs_pulls_back_the_gradient():
    from score.stages.sim_body.inside.tuning._adjoint import _bodies
    rows = np.random.default_rng(5).normal(size=(2, 9))
    rows[:, 3:7] /= np.linalg.norm(rows[:, 3:7], axis=1, keepdims=True)
    chart = _bodies.RootTurns(rows.ravel(), 9)
    point = chart.reduced()
    assert point.size == 2 * 8 and np.allclose(chart.full(point), rows.ravel())
    cost = lambda pose: np.sum(np.sin(pose) * np.arange(1, pose.size + 1))
    moved = point + np.random.default_rng(6).normal(scale=0.1, size=point.size)
    pulled = chart.pulled(moved, np.cos(chart.full(moved)) * np.arange(1, 19))
    differences = [(cost(chart.full(moved + step)) - cost(chart.full(moved - step))) / 2e-6
                   for step in np.eye(point.size) * 1e-6]
    assert np.allclose(pulled, differences, atol=1e-6)


def test_the_taped_gradient_equals_central_differences_of_the_cost():
    python = _newton_python()
    if python is None:
        pytest.skip("no Newton Python (SCORE_NEWTON_PYTHON or $PROPS_HOME/envs/newton_env)")
    ran = subprocess.run([str(python), "-B", str(pathlib.Path(__file__).parent / "_check_taped.py"), str(pathlib.Path(__file__).parent)],
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




def _case_found(joints, turns, skins):
    """`case_residuals`' measures of per-frame joint differences (m), turn degrees and bone points' depths outside (m)."""
    return {"per joint mm": {key: [np.median(1000 * np.linalg.norm(value, axis=1))] for key, value in joints.items()},
            "per group deg": {key: [np.median(value)] for key, value in turns.items()},
            "bones outside depth mm": {key: 1000 * np.sqrt(np.mean(np.square(value))) for key, value in skins.items()}}


def test_the_taped_measures_rows_equal_differences_of_the_case_residuals():
    from score.stages.sim_body.inside.tuning import case_residuals
    python = _newton_python()
    if python is None:
        pytest.skip("no Newton Python (SCORE_NEWTON_PYTHON or $PROPS_HOME/envs/newton_env)")
    ran = subprocess.run([str(python), "-B", str(pathlib.Path(__file__).parent / "_check_measures.py"), str(pathlib.Path(__file__).parent)],
                         capture_output=True, text=True, timeout=110)
    assert ran.returncode == 0, ran.stderr[-2000:]
    found = json.loads(ran.stdout.rsplit("JSON", 1)[1])
    taped = {kind: {key: tuple(np.array(part) for part in value) for key, value in found["taped"][kind].items()}
             for kind in ("joints", "turns", "skins")}
    assert all(np.abs(depths).max() > 1e-3 for depths, *_ in taped["skins"].values()), "no bone point outside the skin"
    assert found["passes"] == 2 * 3 + 2 + 3, found["passes"]  # a frame's most entries per output: joints, turns, skins
    assert all(rows.shape[-1] == 4 for kind in ("joints", "turns") for _, rows in taped[kind].values())  # frame blocks
    values, jacobian = _adjoint.case_rows(taped["joints"], taped["turns"], taped["skins"], frames=3)
    at = {kind: {key: value[0] for key, value in taped[kind].items()} for kind in taped}
    assert np.allclose(values, case_residuals(_case_found(at["joints"], at["turns"], at["skins"])), atol=1e-4)
    scored = [case_residuals(_case_found(*({key: np.array(value) for key, value in nudge[kind].items()}
                                           for kind in ("joints", "turns", "skins"))))
              for nudge in found["nudged"]]
    expected = np.stack([(scored[2 * column] - scored[2 * column + 1]) / (2 * found["step"])
                         for column in range(len(scored) // 2)], axis=1)
    assert np.abs(jacobian - expected).max() < 1e-2 * np.abs(expected).max()


def test_one_real_body_builds_and_its_rows_equal_the_card_solve(tmp_path):
    """`SCORE_ADJOINT_REAL` names a JSON file {seeds, set, reference, cases: {case: job}} (absolute paths): one tuning
    body's set and its card solve's angles. Skipped without it or without Newton's Python (the real store's inputs)."""
    python, named = _newton_python(), os.environ.get("SCORE_ADJOINT_REAL")
    if python is None or not named:
        pytest.skip("no Newton Python or no SCORE_ADJOINT_REAL")
    given = json.loads(pathlib.Path(named).read_text())
    ran = subprocess.run([str(python), "-B", str(pathlib.Path(__file__).parent / "_check_real.py"),
                          str(pathlib.Path(__file__).parent), given["seeds"], given["set"], str(tmp_path), given["reference"],
                          *(f"{case}={job}" for case, job in given["cases"].items())],
                         capture_output=True, text=True, timeout=115)
    assert ran.returncode == 0, ran.stderr[-2000:]
    found = json.loads(ran.stdout.strip().splitlines()[-1])
    assert all(case["most"] < 1e-4 for case in found["cases"].values()), found
    assert found["fk"]["most"] < 1e-4, found
    assert found["taped"]["refused"] == {}, found
    assert found["measures"]["most"] < 1e-4 and found["measures"]["turn most"] < 1e-2, found
    assert found["measures"]["skin most"] < 1e-4, found
