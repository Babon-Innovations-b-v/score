"""The implicit Jacobian equals central differences of re-solved inner fits on a toy two-level problem (frames' poses
and shared constants, residuals nonzero at the optimum so Gauss-Newton differs from the full Hessian), and an
unconverged inner fit is refused, and level 1's outer rows (a per-frame distance's median and a root mean square)
equal differences of the measures they stand for.

Breaks (each applied once, seen red, reverted), in `tuning/_adjoint/__init__.py`: `rms_row` dropping its 1 / count
turns the outer rows test red; `case_rows` weighing joints 1.0 in place of
JOINT_SHARE turns the case rows test red; dropping the mixed term
(`moved` set to zeros) turns the columns test red; `schur_solve` skipping the couplings' reduction (`reduced = corner`)
turns the Schur and columns tests red; removing the `Unconverged` check turns the refusal test red; `rowed_jacobian` dropping the given R_z term (`by_outer` alone) turns the given rows test red; `chained_jacobian` dropping level 2's term (R_c dc/dtheta) turns the level 2 chain test red; `chained_rows` dropping it the same way turns the given level 3 rows test red; `stacked_jacobian` skipping `refused`
(no check before use) turns the stacked refusal test red; dropping the prior's block turns the stacked test red;
in `_taped.py`, dropping `tape.zero()` (a second gradient adds onto the first's) turns the taped gradient test red; skipping
the turn rows' launch turns it red; dropping the followers' launch (couplings) turns it red; reading level 2's
inside-joint gradient as zeros (`_Constants.gradient`) turns it red; reading only the first frame's copy of a constant
in a batched body (`_Constants.gradient` taking `[0]` in place of `.sum(axis=0)`) turns it red. Ignoring the outer
unknowns' trust (`TapedSites._evaluate` not assigning `self.weights` when `trusted`) turns it red. Assigning the trusts themselves when `ends` is given (`_weighed` returning `tail`) turns it red. Laying a batched body's weights site by site in place of copy by copy (`np.repeat` for `np.tile` in `_evaluate`) turns it red. In `_measures.py`,
skipping `self.centres.zero_()` (joint centres adding onto the last evaluation's) turns the taped measures test red.
Building the bone points without `requires_grad` (`_Skins.points`: no skin depth row reaches the pose) turns it red.
Cutting each seeded row from the first frame's block in place of its own (`_rows` with start 0) turns it red; `case_rows` laying a
skin point's block at frame 0 (`rms_row` ignoring `point_frames`) turns it red. `_real.level2_solved` returning its start path in place of the solved angles (what `constants_on` drops) turns the real level 2 test red. `fit/_constants.staged` without its `polished` step turns the real constant motion test red (its free gradient over 1e-9). `_real.level2_constants` laying every copy's free marks on the first copy's sites (the copy shift times 0) turns the real constants test red. `_bodies.level3_body`'s gradient without `pinned.gradient` (held rows not springs) turns it red; its `placed` ignoring theta turns it red too (theta gap 1). `TapedMeasures._constant_blocks` reading every frame's rows off the first copy's inside joints turns the taped measures test red (R_c 148 against 101). `_check_chained.py` with R_c dropped (`by_constants` zeroed) turns the real chained rows test red (1.01).
In `_bodies.py`, a copy's leaders not offset to its own pose (`copied_couplings`
without `copy * len(free)`) turns the copied couplings test red; `RootTurns.pulled` skipping the normalisation's
projection (`along` the raw turn gradient) turns the root chart test red; `RootTurns.pulled_rows` cutting each copy's fourth turn coordinate in place of pulling the row
through the chart turns it red; `Pinned.rows` keeping a held column turns the pinned test red; `Pinned.gradient` giving a held entry zero in place of its spring (a
singular frame block) turns the pinned test red. In `_level2.py`, `level2_body`'s gradient left in the Problem's order (no `to_body`) turns the constants-first level 2 test red; `pinned_mask` holding no bound-held entry turns it red; `level2_body` rebuilding the Problem on every gradient call (no `problem_of` cache) turns it red. In `_outer.py`, the trusts' derivative without its LOG_UNIT factor (`site_derivative`) turns the outer map test red. In `_real.py`, `solved_rows`
giving MuJoCo's order (no `newton_order`) turns the real body test red; `frame_couplings` zeroing
the projection's polynomials turns its per-frame model check red; `bound_held` holding nothing (bound-held coordinates left in the pose) turns its refused check red (4.12e-3); `joint_parts`
dropping the centres' scales turns its joints check red; `turn_groups` without the frozen table turns its turns check red; `skin_parts` without the geom's turn turns its skins check red (0.19 m). The case rows' derivative left over the full pose (no `RootTurns.pulled_rows`) turns its pulled check red.

The taped test runs `_taped` (Newton eval_fk on a wp.Tape) in Newton's own Python on the card, a four-link chain with
three weighted sites and two link-frame turn rows, once on every coordinate and once with the last a follower of the
second (a polynomial coupling, the pose the three free coordinates), and once with level 2's constants (two free
sites' moves and the third joint's place move after the pose), and once batched (two frames as two copies of the chain
in one model, one launch, level 2's constants shared by both), and once with each site's trust an outer unknown, and once with the last site a group end and the
end weight and markers' goal outer unknowns, and once batched with a group end in each copy (`copies=2`, one frame's
outer unknowns laid on both: its rows equal each copy's own frame's): its gradient, asked twice, equals central differences of its cost to 1e-3 of the largest entry. With no
Newton Python (`SCORE_NEWTON_PYTHON`, else $PROPS_HOME/envs/newton_env) it is skipped; its run is `_check_taped.py`. The taped measures test runs (`_check_measures.py`)
`_measures` on three copies of the chain (frames): two joints (one a MIDDLE of two parts), two turn groups and two skin
regions' bone points against a posed box skin per frame (some outside, some inside), fed through `case_rows`, equal central differences of `case_residuals` to 1 % of the largest entry; so do its rows over level 2's moves (R_c: a free mark's columns zero, an inside joint's)."""
import json

import numpy as np
import pytest

from score.stages.sim_body.inside.tuning import _adjoint
from score.stages.sim_body.inside.tuning._adjoint import _runs as runs, _toys as toys
from score.stages.sim_body.inside.tuning._adjoint._toys import CONSTANTS, FRAMES, OUTER, POSE


def test_implicit_columns_equal_re_solved_differences():
    inner = toys.solved(OUTER)
    implicit = _adjoint.implicit_jacobian(toys.residuals, toys.gradient, inner, OUTER, FRAMES, POSE, (1e-5, 1e-5), 1e-8)
    re_solved = _adjoint.by_columns(lambda point: toys.residuals(toys.solved(point), point), OUTER, 1e-4)
    assert np.allclose(implicit, re_solved, rtol=1e-4, atol=1e-6)


def test_given_rows_give_the_implicit_columns_without_residual_calls():
    inner = toys.solved(OUTER)
    rowed = _adjoint.rowed_jacobian(toys.toy_rows(inner, OUTER), toys.gradient, inner, OUTER, FRAMES, POSE, (1e-5, 1e-5), 1e-8)
    re_solved = _adjoint.by_columns(lambda point: toys.residuals(toys.solved(point), point), OUTER, 1e-4)
    assert np.allclose(rowed, re_solved, rtol=1e-4, atol=1e-6)


def test_schur_solve_equals_the_dense_solve():
    inner = toys.solved(OUTER)
    blocks, couplings, corner = _adjoint.arrow_hessian(toys.gradient, inner, OUTER, FRAMES, POSE, 1e-5)
    dense = _adjoint.by_columns(lambda point: toys.gradient(point, OUTER), inner, 1e-5)
    right = np.random.default_rng(0).normal(size=(len(inner), 3))
    assert np.allclose(_adjoint.schur_solve(blocks, couplings, corner, right), np.linalg.solve(dense, right),
                       rtol=1e-5, atol=1e-7)


def test_an_unconverged_inner_fit_is_refused():
    with pytest.raises(_adjoint.Unconverged):
        _adjoint.implicit_jacobian(toys.residuals, toys.gradient, np.full(FRAMES * POSE + CONSTANTS, 0.2), OUTER, FRAMES,
                                   POSE, (1e-5, 1e-5), 1e-8)


def test_stacked_jacobian_is_each_body_then_the_prior():
    inner = toys.solved(OUTER)
    stacked = _adjoint.stacked_jacobian([toys.body("one", inner), toys.body("two", inner)], OUTER, toys.prior, (1e-5, 1e-5), 1e-8)
    one = _adjoint.implicit_jacobian(toys.residuals, toys.gradient, inner, OUTER, FRAMES, POSE, (1e-5, 1e-5), 1e-8)
    assert np.allclose(stacked, np.concatenate([one, one, np.diag(2 * OUTER)]), atol=1e-8)


def test_the_stacked_jacobian_names_every_unconverged_body():
    stopped = np.full(FRAMES * POSE + CONSTANTS, 0.2)
    with pytest.raises(_adjoint.Unconverged, match="two .*three"):
        _adjoint.stacked_jacobian([toys.body("one", toys.solved(OUTER)), toys.body("two", stopped), toys.body("three", stopped)],
                                  OUTER, toys.prior, (1e-5, 1e-5), 1e-8)


def test_the_outer_rows_equal_differences_of_the_median_and_the_root_mean_square():
    unknowns = np.array([0.3, 0.7, 1.1])
    rows = _adjoint.by_columns(lambda point: toys.differences(point).ravel(), unknowns, 1e-6).reshape(5, 3, 3)
    lengths, length_rows = _adjoint.distance_rows(toys.differences(unknowns), rows)
    median, median_row = _adjoint.median_row(lengths, length_rows)
    root, root_row = _adjoint.rms_row(lengths, length_rows)
    expected = _adjoint.by_columns(toys.outer_values, unknowns, 1e-6)
    assert np.allclose([median, root], toys.outer_values(unknowns))
    assert np.allclose(np.stack([median_row, root_row]), expected, atol=1e-6)
    assert np.allclose(_adjoint.median_row(lengths[:4], length_rows[:4])[0], np.median(lengths[:4]))


def test_level_1_unknowns_map_onto_the_taped_outer_unknowns_with_their_derivative():
    from score.stages.sim_body.inside import tuning
    from score.stages.sim_body.inside.tuning._adjoint import _outer
    entries = tuning.layout(toys.TABLE, set(), {"knee_l"}, {"LeftUpLeg": ["LeftUpLeg"]})
    unknowns = np.linspace(-0.6, 0.9, len(entries))
    assert np.allclose(_outer.site_unknowns(unknowns, entries, toys.LANDMARKS, toys.ENDS, toys.STARTS, toys.TABLE,
                                            toys.GLOBALS), toys.site_outer(unknowns, entries))
    derivative = _outer.site_derivative(unknowns, entries, toys.LANDMARKS, toys.ENDS, toys.TABLE, toys.GLOBALS)
    assert np.allclose(derivative, toys.site_outer_differences(unknowns, entries), atol=1e-6)


def test_a_body_copied_per_frame_keeps_the_card_projection_couplings():
    from score.stages.sim_body.inside.tuning._adjoint import _bodies
    poly = np.array([[0.1, 0.5, 0.2, 0.0, 0.0], [0.0, -1.0, 0.0, 0.0, 0.0]])
    rows = np.random.default_rng(3).normal(size=(2, 11))
    rows[:, 9] = 0.4 + np.polyval(poly[0][::-1], rows[:, 7] - 0.2)  # led by a frozen coordinate: stays as solved
    rows[:, 10] = -0.3 + np.polyval(poly[1][::-1], rows[:, 8] - 0.1)
    couplings = _bodies.copied_couplings([9, 10], [7, 8], [0.4, -0.3], [0.2, 0.1], poly, [7], rows)
    pose = _bodies.pose_of(couplings, rows)
    assert len(pose) == 2 * 8
    assert np.allclose(toys.followed(couplings, pose), rows.reshape(-1))
    moved = pose + 0.05
    expanded = toys.followed(couplings, moved).reshape(2, 11)
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
    assert np.allclose(pulled, _adjoint.by_columns(lambda at: np.atleast_1d(cost(chart.full(at))), moved, 1e-6)[0], atol=1e-6)
    mix = np.random.default_rng(7).normal(size=(3, 18))
    pulled_rows = chart.pulled_rows(moved, mix * np.cos(chart.full(moved)))
    row_differences = _adjoint.by_columns(lambda at: mix @ np.sin(chart.full(at)), moved, 1e-6)
    assert pulled_rows.shape == (3, 16) and np.allclose(pulled_rows, row_differences, atol=1e-6)


def test_the_taped_gradient_equals_central_differences_of_the_cost():
    gap = float(runs.newton_ran("_check_taped.py").rsplit("GAP", 1)[1])
    assert gap < 1e-3


def test_the_taped_case_rows_equal_differences_of_the_case_residuals():
    from score.stages.sim_body.inside.tuning import case_residuals
    unknowns = np.array([0.3, 0.7, 1.1])
    measured = toys.measured(unknowns)
    rows = {kind: {key: _adjoint.by_columns(lambda point, kind=kind, key=key: np.ravel(toys.measured(point)[kind][key]),
                                            unknowns, 1e-6).reshape(*np.shape(value), 3)
                   for key, value in measured[kind].items()} for kind in measured}
    values, jacobian = _adjoint.case_rows(*({key: (value, rows[kind][key]) for key, value in measured[kind].items()}
                                            for kind in ("joints", "turns", "skins")))
    assert np.allclose(values, case_residuals(toys.found(unknowns)))
    expected = _adjoint.by_columns(lambda point: case_residuals(toys.found(point)), unknowns, 1e-6)
    assert np.allclose(jacobian, expected, atol=1e-6)


def test_the_taped_measures_rows_equal_differences_of_the_case_residuals():
    from score.stages.sim_body.inside.tuning import case_residuals
    found = json.loads(runs.newton_ran("_check_measures.py").rsplit("JSON", 1)[1])
    taped = dict(zip(("joints", "turns", "skins"), toys.taped_parts(found, "taped")))
    assert all(np.abs(depths).max() > 1e-3 for depths, *_ in taped["skins"].values()), "no bone point outside the skin"
    assert found["passes"] == 2 * 3 + 2 + 3, found["passes"]  # a frame's most entries per output: joints, turns, skins
    assert all(rows.shape[-1] == 4 for kind in ("joints", "turns") for _, rows in taped[kind].values())  # frame blocks
    values, jacobian = _adjoint.case_rows(taped["joints"], taped["turns"], taped["skins"], frames=3)
    at = {kind: {key: value[0] for key, value in taped[kind].items()} for kind in taped}
    assert np.allclose(values, case_residuals(toys.case_found(at["joints"], at["turns"], at["skins"])), atol=1e-4)
    expected = toys.nudged_differences(found["nudged"], found["step"])
    assert np.abs(jacobian - expected).max() < 1e-2 * np.abs(expected).max()
    constant_jacobian = _adjoint.case_rows(*toys.taped_parts(found, "constant_taped"))[1]  # R_c: a free mark, a joint
    expected = toys.nudged_differences(found["constant_nudged"], found["step"])
    assert np.all(constant_jacobian[:, :3] == 0) and np.abs(constant_jacobian - expected).max() < 1e-2 * np.abs(expected).max()


def test_one_real_body_builds_and_its_rows_equal_the_card_solve(tmp_path):
    """`runs.real_inputs`: one tuning body's set and its card solve's angles (the real store's inputs)."""
    given, cases = runs.real_inputs()
    found = runs.last_json(runs.newton_ran("_check_real.py", given["seeds"], given["set"], tmp_path, given["reference"],
                                           *cases, timeout=115))
    assert all(case["most"] < 1e-4 for case in found["cases"].values()), found
    assert found["fk"]["most"] < 1e-4, found
    assert found["taped"]["refused"] == {} and found["taped"]["frames"] == found["rows"], found
    assert found["measures"]["most"] < 1e-4 and found["measures"]["turn most"] < 1e-2, found
    assert found["measures"]["skin most"] < 1e-4, found
    pulled = found["pulled"]
    assert pulled["charted"] == [pulled["full"][0], found["taped"]["inner"]] and pulled["finite"], found
    assert pulled["held columns most"] == 0.0, found


def test_a_pinned_held_entry_keeps_the_frame_blocks_and_equals_the_pose_with_it_dropped():
    from score.stages.sim_body.inside.tuning._adjoint import _bodies
    inner = toys.solved(OUTER)
    held = np.zeros(inner.size, dtype=bool)
    held[[1, 4]] = True
    pinned = _bodies.Pinned(inner, held)
    gradient = lambda point, outer: pinned.gradient(point, toys.gradient(pinned.whole(point), outer))
    residuals = lambda point, outer: toys.residuals(pinned.whole(point), outer)
    kept = _adjoint.implicit_jacobian(residuals, gradient, inner, OUTER, FRAMES, POSE, (1e-5, 1e-5), 1e-8)
    assert np.allclose(kept, toys.held_dropped_jacobian(inner, held), rtol=1e-6, atol=1e-9)
    rows = np.ones((2, inner.size))
    assert not pinned.rows(rows)[:, held].any() and (pinned.rows(rows)[:, ~held] == 1.0).all()


def test_level_2_constants_outer_to_level_3_chain_to_re_solved_differences():
    level2, level3, untold = toys.chain_bodies()
    chained = _adjoint.chained_jacobian(level2, level3, OUTER, (1e-5, 1e-5), 1e-8)
    re_solved = _adjoint.by_columns(lambda point: toys.chain_re_solved(point, untold), OUTER, 1e-4)
    assert np.abs(re_solved).max() > 0.1
    assert np.abs(chained - re_solved).max() < 1e-4 * np.abs(re_solved).max()


def test_given_level_3_rows_chain_to_re_solved_differences():
    level2, level3, untold = toys.chain_bodies()
    joined = np.concatenate([OUTER, level2.inner[FRAMES * POSE:]])
    rows = toys.seen_rows(level3.inner, joined)
    chained = _adjoint.chained_rows(level2, level3, rows, OUTER, (1e-5, 1e-5), 1e-8)
    re_solved = _adjoint.by_columns(lambda point: toys.chain_re_solved(point, untold), OUTER, 1e-4)
    assert np.abs(chained - re_solved).max() < 1e-4 * np.abs(re_solved).max()


def test_level_2_body_off_a_constants_first_problem_moves_its_constants_as_re_solved():
    from score.stages.sim_body.inside.tuning._adjoint import _level2
    outer = np.array([0.4, -0.3])
    solved, kept = toys.constants_first_solved(outer)
    assert abs(solved[3] - toys.ConstantsFirst.LOW) < 1e-9
    built = []
    body = _level2.level2_body(lambda point: built.append(1) or toys.ConstantsFirst(point),
                               lambda problem, unknowns: problem.jacobian(unknowns), solved, kept, outer)
    assert np.array_equal(_level2.to_problem(body.inner, 2), solved)
    moved = _adjoint.constant_motion(body, outer, (1e-5, 1e-5), 1e-8)
    assert len(built) == 1 + 2 * outer.size
    re_solved = _adjoint.by_columns(lambda point: toys.constants_first_solved(point)[0][:2], outer, 1e-4)
    assert np.abs(re_solved).max() > 0.1
    assert np.abs(moved - re_solved).max() < 1e-4 * np.abs(re_solved).max()


LEVEL2_STATIONARY = 1e-2  # level 2's pinned gradient at its solve over the one at its start (heavy_kimodo, 2026-10-30: 1.6e-3)
MOTION_SHARE = 0.02  # a slot's implicit dc/dtheta off its settled re-solves, over the column's largest entry
CONSTANTS_SHARE = 1e-2  # the taped constants' gradient off central differences of the cost, over its largest entry


def test_level_2_on_one_real_body_is_stationary_at_its_solve(tmp_path):
    """`SCORE_ADJOINT_REAL` as above: level 2 solved on its sampled frames (`_real.level2_solved`, the angles kept),
    `_level2.level2_body` on `_real.problem_at` at the solve, its pinned gradient far under the one at the start."""
    given, cases = runs.real_inputs()
    found = runs.last_json(runs.newton_ran("_check_level2.py", given["set"], tmp_path, *cases, timeout=115))
    assert found["solved most"] < LEVEL2_STATIONARY * found["start most"], found


def test_level_2_constant_motion_on_one_real_body_equals_settled_re_solves(tmp_path):
    """`SCORE_ADJOINT_REAL` as above: `constant_motion` on level 2 at its float64-settled solve against differences of
    level 2 re-solved at marker goal +-0.1, told, unpinned slots off their bounds (heavy_kimodo, 2026-10-30: 99 s)."""
    given, cases = runs.real_inputs()
    found = runs.last_json(runs.newton_ran("_check_motion.py", given["set"], tmp_path, "0.1", *cases, timeout=300))
    assert found["off"] > 0 and found["free gradient"] < 1e-9, found
    assert found["most difference"] < MOTION_SHARE * found["top"], found


def test_level_2_constants_on_the_real_tape_equal_differences_of_its_cost(tmp_path):
    """`SCORE_ADJOINT_REAL` as above: `_real.taped_sites(constants=_real.level2_constants(...))` at the solved rows,
    moves 0: its constants' gradient on its largest entries equals central differences of the cost, its pose part the
    constant-free gradient; level 3's g_q,c (`_bodies.level3_body`, `mixed` over the moves) equals the constants'
    gradient differenced over the pose (H's symmetry), its held rows zero, and its g_q,theta over a free mark's own
    site offset that mark's g_q,c column."""
    given, cases = runs.real_inputs()
    found = runs.last_json(runs.newton_ran("_check_constants.py", given["seeds"], given["set"], tmp_path, *cases))
    assert found["pose most"] < 1e-6 * max(found["pose largest"], 1.0), found
    assert found["gap over largest"]["0.0001"] < CONSTANTS_SHARE, found
    assert found["cross symmetry"] < CONSTANTS_SHARE and found["cross held most"] == 0.0, found
    assert found["theta marks"] > 0 and found["theta gap"] < CONSTANTS_SHARE, found


def test_level_2_constants_rows_on_the_real_body_equal_differences_of_its_case_rows(tmp_path):
    """`SCORE_ADJOINT_REAL` as above: R_c (`TapedMeasures.constant_measured` through `case_rows`) on its largest
    columns equals `case_rows` of the per-frame measures' central differences over level 2's moves, the medians'
    frames fixed (a move of every frame swaps the median's frame; that gap is reported, not judged). Red when a skin
    point's rows are read off its skin frame's index in place of its link's copy (2026-10-30: 1.57 of the largest)."""
    given, cases = runs.real_inputs()
    found = runs.last_json(runs.newton_ran("_check_rows.py", given["seeds"], given["set"], tmp_path, *cases))
    assert found["finite"] and found["masked gap over largest"] < CONSTANTS_SHARE, found


def test_chained_rows_on_the_real_body_equal_both_levels_re_solved(tmp_path):
    """`SCORE_ADJOINT_REAL` as above: `chained_rows` on one link column against `case_rows` of both levels re-solved at
    +-0.1, the medians' frames fixed (heavy_kimodo ASIS_l, 2026-10-30: 0.48 % of the largest, 366 s)."""
    given, cases = runs.real_inputs()
    found = runs.last_json(runs.newton_ran("_check_chained.py", given["seeds"], given["set"], tmp_path, "0.1", *cases, timeout=600))
    assert found["gap over largest"] < MOTION_SHARE, found
