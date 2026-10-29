"""tuning: level 1 is one least_squares over every unknown at once: a toy whose residuals need two landmarks' links
and a global weight moved together is solved jointly to its minimum, within the bounds, a joint link never along its
bone, mirrored pairs sharing unknowns, the pattern reaching only a landmark's own and neighbouring groups, every
evaluation checkpointed and resumed from the best (pure: the score venv runs it, well under 2 minutes).

Breaks (each applied once, seen red, reverted):
- (2026-10-29) layout's `if axis != LONG_AXIS` dropped: a joint-defining link slides along its bone.
- (2026-10-29) applied's `* paired(name)[1]` dropped: a right landmark's move is not mirrored.
- (2026-10-29) reached's `near.add(PARENT.get(segment, segment))` dropped: a landmark misses its parent group's rows.
- (2026-10-29) resumed's `min(lines, ...)` made `lines[0]`: a resume starts from the first evaluation, not the best.
- (2026-10-29) weight_rewritten's `flags=re.MULTILINE` dropped: no global weight is written back.
- (2026-10-29) ended's `middles.get(start, (start,))` made `(start,)`: a hip's centre misses the Hips group it ends.
- (2026-10-29) offsets keyed by `paired(centre)[0]`: the right hip's centre takes the left's move (bodies are not
  symmetric: each end its own).
- (2026-10-29) bounds' "centre" reach dropped: a centre held within a link's 30 mm, not its 40.
- (2026-10-29) prior's `kind in MOVES` made `kind == "link"`: no prior pulls a centre to the model's own.

Run: .venv/bin/python score/stages/sim_body/inside/tuning/test_one_optimisation_moves_every_unknown_together_within_its_bounds.py
"""
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


def test_every_group_end_is_its_own_unknown_within_its_reach_pulled_to_the_models_centre():
    assert ENDS == {"hip_l": ["Hips", "LeftLeg"], "hip_r": ["Hips", "RightLeg"]}
    entries = tuning.layout(TABLE, held=(), joints=set(), ends=ENDS)
    centres = [index for index, (_, kind, _, _) in enumerate(entries) if kind == "centre"]
    assert [entries[index][:3] for index in centres] == [(centre, "centre", axis) for centre in ENDS for axis in range(3)]
    unknowns = np.zeros(len(entries))
    unknowns[centres[2]] = 1  # the left hip's z
    assert tuning.offsets(unknowns, entries) == {"hip_l": [0, 0, tuning.LINK_UNIT], "hip_r": [0, 0, 0]}
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


def test_a_global_weight_is_written_back_into_its_module():
    source = "MARKER_GOAL = 1.0\nOTHER_GOAL = 1.0\n"
    found = tuning.weight_rewritten(source, "MARKER_GOAL", 2.5)
    assert found == "MARKER_GOAL = 2.5\nOTHER_GOAL = 1.0\n", found


def test_the_run_settles_when_the_objective_stops_moving():
    assert tuning.settled([10.0, 5.0, 4.99, 4.985, 4.98])
    assert not tuning.settled([10.0, 5.0, 4.0, 3.0])


if __name__ == "__main__":
    for test in [value for name, value in sorted(globals().items()) if name.startswith("test_")]:
        test()
    print("ok")
