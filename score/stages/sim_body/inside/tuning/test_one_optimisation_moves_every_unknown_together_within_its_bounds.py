"""tuning: level 1 is one least_squares over every unknown at once: a toy whose residuals need two landmarks' links
and a global weight moved together is solved jointly to its minimum, within the bounds, a joint link never along its
bone, mirrored pairs sharing unknowns, the pattern reaching only a landmark's own and neighbouring groups, every
evaluation checkpointed and resumed from the best, its Jacobian by ABSOLUTE steps from every unknown at 0 (pure: the
score venv runs it, well under 2 minutes).

Breaks (each applied once, seen red, reverted):
- (2026-10-29) layout's `if axis != LONG_AXIS` dropped: a joint-defining link slides along its bone.
- (2026-10-29) applied's `* paired(name)[1]` dropped: a right landmark's move is not mirrored.
- (2026-10-29) reached's `near.add(PARENT.get(segment, segment))` dropped: a landmark misses its parent group's rows.
- (2026-10-29) resumed's `min(lines, ...)` made `lines[0]`: a resume starts from the first evaluation, not the best.
- (2026-10-29) weight_rewritten's `flags=re.MULTILINE` dropped: no global weight is written back.
- (2026-11-01) relative's `/ largest` dropped: a written trust stays over 1 (level 1's trusts float in scale).
- (2026-11-01) centres_rewritten's `float(value) + float(move)` made `float(move)`: a centre off its body's origin
  (C7_T1 on the torso) lands at its offset, not moved by it.
- (2026-10-29) ended's `middles.get(start, (start,))` made `(start,)`: a hip's centre misses the Hips group it ends.
- (2026-11-01) offsets' `* float(factor[axis])` dropped: the right hip's centre takes the left's move unmirrored.
- (2026-11-01) layout's `paired(centre)[0]` made `centre`: each end its own unknown again, the sides apart.
- (2026-11-01) layout's `axis != LATERAL` made `True`: a middle end's centre moves off the mid-plane.
- (2026-10-29) bounds' "centre" reach dropped: a centre held within a link's 30 mm, not its 40.
- (2026-10-29) prior's `kind in MOVES` made `kind == "link"`: no prior pulls a centre to the model's own.
- (2026-10-29) solved's `jac=differenced` made scipy's `jac="2-point", jac_sparsity=pattern, diff_step=STEP`: at 0
  its relative step is 1.5e-8 (scipy 1.18.1), the measures' rounding reads as flat and nothing moves.
- (2026-10-29) grouped's `if not (used & rows).any()` made `if True`: columns sharing a row stepped together.
- (2026-10-29) signed_steps' flip dropped (always +step): a step passes the upper bound.
- (2026-10-29) nudged's `moved = unknowns.copy()` hoisted out of its loop: each batched set carries the groups
  before it, the one-call Jacobian differs from the serial one (card build step 6a).
- (2026-10-30) solved's `if exact: return exact(unknowns)` dropped: the adjoint's Jacobian is ignored and the
  differences still run (card build step 6b).
- (2026-11-01) case_residuals' `/ SKIN_SCALE` dropped: a region's depth counts in raw mm, not in its unit.
- (2026-11-01) labels given back `("turn", key)` rows for "per group rms deg": the turns, level 1's check, are
  tuned beside the skin (the owner's aim of 2026-11-01: bones inside the skin, turns a check, joints reported).
- (2026-11-01) jacobian's retry of a failed set (`if failed:` made `if False:`): a nudged set the card's level 3 did
  not stop on (None) kills the Jacobian, as l1e's s00014 killed level 1.
- (2026-11-01) jacobian's retry stepping `steps` again (not `-steps`): the failed side is asked twice.
- (2026-11-01) whole's `np.full(size, np.inf) if found is None` dropped: a trial point a body's level 3 did not
  stop on (l1e's tall_heavy, 10:5x) kills level 1 instead of being refused.
- (2026-11-01) evaluated's `if np.all(np.isfinite(found))` dropped: a refused trial is checkpointed at an infinite cost.
- (2026-10-30) _differences.hybrid's `merged[:, chosen] = differenced[:, chosen]` dropped: the hybrid keeps the
  exact Jacobian's chosen (centre) columns in place of their differences.

Run: .venv/bin/python score/stages/sim_body/inside/tuning/test_one_optimisation_moves_every_unknown_together_within_its_bounds.py
"""
import json
import pathlib
import sys
import tempfile

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import tuning  # noqa: E402

TABLE = {"knee_l": {"segment": "LeftLeg", "solver": True, "trust": 0.5, "link": [0, 0, 0]},
         "knee_r": {"segment": "RightLeg", "solver": True, "trust": 0.5, "link": [0, 0, 0]},
         "PSIS_l": {"segment": "Hips", "solver": True, "trust": 1.0, "link": [0, 0, 0]},
         "skip": {"segment": "Head", "solver": False, "trust": 1.0, "link": [0, 0, 0]}}
STARTS = {name: row["link"] for name, row in TABLE.items()}
ENTRIES = tuning.layout(TABLE, held=(), joints={"knee_l", "knee_r"})
GROUPS = {"Hips": (("hipmid", "Spine1"), ("hipmid", "L5_S1"), "pelvis", ()),
          "LeftLeg": (("LeftLeg", "LeftShin"), ("hip_l", "knee_l"), "femur_l", ()),
          "RightLeg": (("RightLeg", "RightShin"), ("hip_r", "knee_r"), "femur_r", ())}
ENDS = tuning.ended(GROUPS, {"hipmid": ("hip_l", "hip_r")})


def test_a_joint_link_moves_only_across_its_bone():
    axes = [axis for pool, kind, axis, _ in ENTRIES if pool == "knee_l" and kind == "link"]
    assert axes == [0, 2]
    assert sum(1 for pool, kind, _, _ in ENTRIES if kind == "trust") == 2  # knee_l/knee_r share, PSIS_l, no skip


def test_a_right_landmark_moves_mirrored():
    unknowns = np.zeros(len(ENTRIES))
    unknowns[[index for index, (pool, kind, axis, _) in enumerate(ENTRIES) if pool == "knee_l" and axis == 2]] = 1
    rows, _ = tuning.applied(unknowns, ENTRIES, STARTS, TABLE, {"marker goal": 1.0, "end weight": 1.0})
    assert np.allclose(rows["knee_l"]["link"], [0, 0, tuning.LINK_UNIT])
    assert np.allclose(rows["knee_r"]["link"], [0, 0, -tuning.LINK_UNIT])


def test_a_landmark_reaches_its_parents_and_childrens_rows():
    near = tuning.reached(["LeftLeg"])
    assert {"LeftLeg", "Hips", "LeftShin"} <= near and "LeftHand" not in near
    pattern = tuning.sparsity(ENTRIES, [("turn", "Hips"), ("turn", "LeftHand"), ("skin", "thigh")], cases=2)
    knee = next(index for index, (pool, kind, _, _) in enumerate(ENTRIES) if pool == "knee_l" and kind == "trust")
    assert list(pattern[:6, knee]) == [1, 0, 1, 1, 0, 1]
    assert pattern[:6, -1].all()  # a global weight reaches every row


def test_a_pair_of_group_ends_is_one_mirrored_unknown_a_middle_one_on_the_mid_plane_within_its_reach():
    assert ENDS == {"hip_l": ["Hips", "LeftLeg"], "hip_r": ["Hips", "RightLeg"]}
    ends = {**ENDS, "L5_S1": ["Hips", "Spine1"]}
    entries = tuning.layout(TABLE, held=(), joints=set(), ends=ends)
    centres = [index for index, (_, kind, _, _) in enumerate(entries) if kind == "centre"]
    assert [entries[index][:3] for index in centres] == [("hip_l", "centre", axis) for axis in range(3)] + [
        ("L5_S1", "centre", axis) for axis in (0, 1)]
    assert entries[centres[0]][3] == ["Hips", "LeftLeg", "RightLeg"]  # the pair reaches both sides' rows
    unknowns = np.zeros(len(entries))
    unknowns[centres[0]], unknowns[centres[2]], unknowns[centres[4]] = 2, 1, 3  # the hips' x and z, L5_S1's y
    unit = tuning.LINK_UNIT
    assert tuning.offsets(unknowns, entries) == {"hip_l": [2 * unit, 0, unit], "hip_r": [2 * unit, 0, -unit],
                                                 "L5_S1": [0, 3 * unit, 0]}
    lower, upper = tuning.bounds(entries)
    assert np.allclose(upper[centres], tuning.END_REACH / tuning.LINK_UNIT) and np.allclose(lower, -upper)
    assert len(tuning.prior(unknowns, entries)) == len(centres) + sum(kind == "link" for _, kind, _, _ in entries)
    assert tuning.LINK_UNIT / tuning.PRIOR in tuning.prior(unknowns, entries)


def test_the_unknowns_are_solved_together_and_resumed_from_the_best():
    target = np.linspace(-1.0, 1.0, len(ENTRIES))
    coupling = np.eye(len(ENTRIES)) + 0.3 * np.ones((len(ENTRIES), len(ENTRIES)))  # every unknown needs the others
    pattern = np.ones((len(ENTRIES), len(ENTRIES)), dtype=np.int8)
    with tempfile.TemporaryDirectory() as folder:
        checkpoint = pathlib.Path(folder) / "checkpoint.jsonl"
        result = tuning.solved(lambda unknowns: coupling @ (unknowns - target), ENTRIES, pattern, checkpoint, 60,
                               start=np.zeros(len(ENTRIES)))
        assert np.allclose(result.x, target, atol=1e-3)
        assert np.allclose(tuning.resumed(checkpoint, len(ENTRIES)), result.x, atol=1e-3)
        lower, upper = tuning.bounds(ENTRIES)
        assert (result.x >= lower).all() and (result.x <= upper).all()


def test_an_exact_jacobian_replaces_the_differences():
    target = np.linspace(-1.0, 1.0, len(ENTRIES))
    coupling = np.eye(len(ENTRIES)) + 0.3 * np.ones((len(ENTRIES), len(ENTRIES)))
    pattern = np.ones((len(ENTRIES), len(ENTRIES)), dtype=np.int8)
    called = []

    def never(sets):
        raise AssertionError("the differences ran beside an exact Jacobian")

    def exact(unknowns):
        called.append(1)
        return coupling

    with tempfile.TemporaryDirectory() as folder:
        result = tuning.solved(lambda unknowns: coupling @ (unknowns - target), ENTRIES, pattern,
                               pathlib.Path(folder) / "checkpoint.jsonl", 60, start=np.zeros(len(ENTRIES)),
                               many=never, exact=exact)
    assert called and np.allclose(result.x, target, atol=1e-6)


def test_the_hybrid_differences_only_its_chosen_columns_and_keeps_the_rest_exact():
    target = np.linspace(-1.0, 1.0, len(ENTRIES))
    coupling = np.eye(len(ENTRIES)) + 0.3 * np.ones((len(ENTRIES), len(ENTRIES)))
    wrong = coupling.copy()
    wrong[:, 1] = 0.0
    pattern = np.ones((len(ENTRIES), len(ENTRIES)), dtype=np.int8)
    stepped = []

    def residuals(unknowns):
        return coupling @ (np.asarray(unknowns) - target)

    def many(sets):
        stepped.extend(sets)
        return [residuals(moved) for moved in sets]

    with tempfile.TemporaryDirectory() as folder:
        result = tuning.solved(residuals, ENTRIES, pattern, pathlib.Path(folder) / "checkpoint.jsonl", 60,
                               start=np.zeros(len(ENTRIES)), many=many, exact=lambda unknowns: wrong,
                               by_differences=[1])
    assert np.allclose(result.jac[:, 1], coupling[:, 1], atol=1e-6)
    assert np.allclose(np.delete(result.jac, 1, axis=1), np.delete(wrong, 1, axis=1))
    assert stepped and np.allclose(result.x, target, atol=1e-6)


def rounded_linear(matrix, target):
    """A toy evaluation whose measures come back rounded to 0.001, as a fit's do: flat below that."""
    return lambda unknowns: np.round(matrix @ (np.asarray(unknowns) - target), 3)


def test_the_differences_step_a_fixed_amount_grouped_on_the_pattern_within_the_bounds():
    pattern = np.array([[1, 0, 1], [0, 1, 1], [0, 0, 1]], dtype=np.int8)
    matrix = np.array([[2.0, 0.0, 0.5], [0.0, -1.0, 0.25], [0.0, 0.0, 3.0]])
    groups = tuning._differences.grouped(pattern)
    assert groups == [[0, 1], [2]]  # 0 and 1 share no row: one evaluation steps both
    unknowns, upper = np.zeros(3), np.array([5.0, 0.2, 5.0])
    steps = tuning._differences.signed_steps(unknowns, tuning.STEP, upper)
    assert list(steps) == [tuning.STEP, -tuning.STEP, tuning.STEP]  # 0.4 would pass the second's bound of 0.2
    residuals = rounded_linear(matrix, np.zeros(3))
    found = tuning._differences.jacobian(tuning._differences.serially(residuals), unknowns, residuals(unknowns),
                                         pattern, groups, steps)
    assert np.allclose(found, matrix, atol=0.01), found


def test_a_set_the_solve_did_not_stop_on_is_differenced_the_other_way_within_the_bounds():
    pattern = np.array([[1, 0, 1], [0, 1, 1], [0, 0, 1]], dtype=np.int8)
    matrix = np.array([[2.0, 0.0, 0.5], [0.0, -1.0, 0.25], [0.0, 0.0, 3.0]])
    groups, unknowns = tuning._differences.grouped(pattern), np.zeros(3)
    steps = tuning._differences.signed_steps(unknowns, tuning.STEP, np.full(3, 5.0))
    asked = []

    def many(sets):  # a set moving column 2 up does not converge (a frame held on its bounds)
        asked.extend(moved.copy() for moved in sets)
        return [None if moved[2] > 0 else matrix @ moved for moved in sets]
    bounds = (np.full(3, -5.0), np.full(3, 5.0))
    found = tuning._differences.jacobian(many, unknowns, np.zeros(3), pattern, groups, steps, bounds)
    assert np.allclose(found, matrix), found
    assert np.allclose(asked[-1], [0, 0, -tuning.STEP])  # asked once more, on the other side
    try:
        tuning._differences.jacobian(many, unknowns, np.zeros(3), pattern, groups, steps,
                                     (np.array([-5.0, -5.0, -0.1]), bounds[1]))
    except RuntimeError as error:
        assert "bound" in str(error)
    else:
        raise AssertionError("the other side past its bound was taken")


def test_a_trial_point_no_body_converged_on_is_refused_and_the_solve_goes_on():
    target = np.linspace(-0.5, 0.5, len(ENTRIES))
    calls = []

    def evaluate(unknowns):  # the first trial after the start: a body's level 3 did not stop (None)
        calls.append(np.asarray(unknowns).copy())
        if len(calls) == 2:
            return None
        moved = np.asarray(unknowns) - target
        return {"tall": {"per group deg": {}, "per joint mm": {}, "per group rms deg": {}, "per joint rms mm": {},
                         "bones outside depth mm": {f"r{index:02d}": float(value * tuning.SKIN_SCALE)
                                                    for index, value in enumerate(moved)}}}
    count = len(ENTRIES)
    places = [index for index, (_, kind, _, _) in enumerate(ENTRIES) if kind in tuning.MOVES]
    exact = np.vstack([np.eye(count) / np.sqrt(count),
                       np.eye(count)[places] * tuning.LINK_UNIT / tuning.PRIOR])  # no differences: every call a trial
    with tempfile.TemporaryDirectory() as folder:
        checkpoint = pathlib.Path(folder) / "checkpoint.jsonl"
        result, _ = tuning.whole(evaluate, lambda unknowns: 0.0, ENTRIES, checkpoint, 60,
                                 start=np.zeros(len(ENTRIES)), every=100, exact=lambda unknowns: exact)
        costs = [json.loads(line)["cost"] for line in checkpoint.read_text().splitlines()]
    assert len(calls) > 2 and np.isfinite(result.cost) and np.all(np.isfinite(costs))
    assert result.cost < 0.5 * costs[0]  # the solve went on past the refused trial


def test_one_call_with_every_nudged_set_gives_the_serial_jacobian_and_solve():
    target = np.linspace(-1.0, 1.0, len(ENTRIES))
    coupling = np.eye(len(ENTRIES)) + 0.3 * np.ones((len(ENTRIES), len(ENTRIES)))
    pattern = np.eye(len(ENTRIES), dtype=np.int8) + np.eye(len(ENTRIES), k=1, dtype=np.int8)
    calls, banded = [], coupling * pattern  # each column moves only its own rows of the pattern

    def residuals(unknowns):
        return banded @ (np.asarray(unknowns) - target)
    groups = tuning._differences.grouped(pattern)
    assert max(len(group) for group in groups) > 1  # some sets move several columns: the batch must not mix them

    def many(sets):
        calls.append(len(sets))
        return [residuals(moved) for moved in sets]
    unknowns = np.full(len(ENTRIES), 0.3)
    steps = tuning._differences.signed_steps(unknowns, tuning.STEP, tuning.bounds(ENTRIES)[1])
    one = tuning._differences.jacobian(many, unknowns, residuals(unknowns), pattern, groups, steps)
    assert calls == [len(groups)], calls  # one call holds every group's set
    assert np.allclose(one, banded, atol=1e-9), np.abs(one - banded).max()
    full, residuals = np.ones((len(ENTRIES), len(ENTRIES)), dtype=np.int8), rounded_linear(coupling, target)
    with tempfile.TemporaryDirectory() as folder:
        batched = tuning.solved(residuals, ENTRIES, full, pathlib.Path(folder) / "a.jsonl", 60,
                                start=np.zeros(len(ENTRIES)), many=tuning._differences.serially(residuals))
        alone = tuning.solved(residuals, ENTRIES, full, pathlib.Path(folder) / "b.jsonl", 60,
                              start=np.zeros(len(ENTRIES)))
    assert np.array_equal(batched.x, alone.x), (batched.x, alone.x)



def test_a_start_at_zero_moves_although_the_measures_are_rounded():
    target = np.linspace(-1.0, 1.0, len(ENTRIES))
    coupling = np.eye(len(ENTRIES)) + 0.3 * np.ones((len(ENTRIES), len(ENTRIES)))
    pattern = np.ones((len(ENTRIES), len(ENTRIES)), dtype=np.int8)
    with tempfile.TemporaryDirectory() as folder:
        result = tuning.solved(rounded_linear(coupling, target), ENTRIES, pattern,
                               pathlib.Path(folder) / "checkpoint.jsonl", 60, start=np.zeros(len(ENTRIES)))
    assert np.allclose(result.x, target, atol=0.01), result.x


def test_a_global_weight_is_written_back_into_its_module():
    source = "MARKER_GOAL = 1.0\nOTHER_GOAL = 1.0\n"
    found = tuning.weight_rewritten(source, "MARKER_GOAL", 2.5)
    assert found == "MARKER_GOAL = 2.5\nOTHER_GOAL = 1.0\n", found


def test_written_trusts_keep_their_ratios_the_largest_one():
    rows = {"a": {"trust": 2.4, "link": [0, 0, 0]}, "b": {"trust": 0.6, "link": [1, 0, 0]}}
    found = tuning.relative(rows)
    assert found == {"a": {"trust": 1.0, "link": [0, 0, 0]}, "b": {"trust": 0.25, "link": [1, 0, 0]}}, found
    assert rows["a"]["trust"] == 2.4  # the rows given are left as they were


def test_a_group_ends_centre_is_moved_by_its_offset_in_both_tables():
    source = ('    "hip_l": ("femur_l", (0, 0, 0)),\n    "C7_T1": ("torso", (-0.03192, 0.39675, 0.00031)),\n'
              '    "L5_S1": ("lumbar5", (0, 0, 0)), "C0_C1": ("head", (-0.00763, 0.00738, 0.00005)),\n')
    found = tuning.centres_rewritten(source, {"hip_l": [0.001, -0.002, 0.0], "C7_T1": [0.002, 0.0, -0.001],
                                              "C0_C1": [0.0, 0.001, 0.0]})
    assert found == ('    "hip_l": ("femur_l", (0.001, -0.002, 0)),\n    "C7_T1": ("torso", (-0.02992, 0.39675, -0.00069)),\n'
                     '    "L5_S1": ("lumbar5", (0, 0, 0)), "C0_C1": ("head", (-0.00763, 0.00838, 5e-05)),\n'), found


def test_the_run_settles_when_the_objective_stops_moving():
    assert tuning.settled([10.0, 5.0, 4.99, 4.985, 4.98])
    assert not tuning.settled([10.0, 5.0, 4.0, 3.0])


def test_only_the_bones_depth_outside_the_skin_is_tuned_never_the_turns_or_joints():
    found = {"bones outside depth mm": {"arm": tuning.SKIN_SCALE, "leg": tuning.SKIN_SCALE},
             "per group deg": {"Hips": [9.0, 20.0]}, "per group rms deg": {"Hips": 4.0},
             "per joint mm": {"knee_l": [7.0, 30.0]}, "per joint rms mm": {"knee_l": 3.0}}
    residuals = tuning.case_residuals(found)
    assert [kind for kind, _ in tuning.labels(found)] == ["skin", "skin"]
    assert np.isclose(residuals @ residuals, 1.0)  # one unit of depth in every region is one unit of the case
    worse = {**found, "per group rms deg": {"Hips": 40.0}, "per joint rms mm": {"knee_l": 30.0}}
    assert np.array_equal(tuning.case_residuals(worse), residuals)


if __name__ == "__main__":
    for test in [value for name, value in sorted(globals().items()) if name.startswith("test_")]:
        test()
    print("ok")
