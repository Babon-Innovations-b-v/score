"""A step counts only past its noise floor, on a fixed case set (#70). One world: three scoring folders of m.json
files (before, the same point scored twice, after) over a fixed set of tuning and check cases, read by `scored` and
judged by `floor`, `scales`, `changes` and `stepped`. Breaks that turn it red: a case one scoring could not fit is
dropped from the set instead of counted as its failure (the tuning side's 3 cases, failed after ['b'], the check
side's failed after ['c'] and 0 paired); the floor is not the spread of the same point scored twice (the floor
dict); a median change inside the floor is called better or worse ('joint Hips mm' unchanged); a kind's unit is not
its measures' median floor (scales' joint is the Knee floor, not the mean); a missing m.json is dropped instead of read as a
failure, or the share outside is not the reported one (after['b'] is None, 'outside all %' 7.5); a step's report
drops its failures or verdicts (the stepped report's failed lists and verdict dict)."""
import json

import numpy as np
import pytest

from . import changes, floor, scales, scored, stepped

SIDES = {"a": "tuning", "b": "tuning", "d": "tuning", "c": "check"}

# case -> (Hips mm, Knee mm, Leg deg, shin outside %, all outside %); each m.json's second column is a decoy
BEFORE = {"a": (4.0, 6.0, 3.0, 10.0, 7.5), "b": (10.0, 12.0, 3.0, 10.0, 5.0), "c": (9.0, 9.0, 3.0, 10.0, 5.0),
          "d": (8.0, 8.0, 3.0, 10.0, 5.0)}
TWICE = {"a": (4.5, 6.5, 4.0, 10.25, 8.0), "b": (9.9, 11.0, 4.0, 10.25, 5.5), "c": (9.3, 9.5, 4.0, 10.25, 5.5),
         "d": (8.0, 8.5, 4.0, 10.25, 5.5)}
AFTER = {"a": (3.8, 4.0, 5.0, 10.0, 7.5), "d": (7.7, 6.0, 4.0, 10.0, 5.0)}  # b could not fit; c is not named


def written(root, name, rows):
    """A scoring folder: one m.json per fitted case, in the frozen harness's shape."""
    for case, (hips, knee, leg, shin, share) in rows.items():
        (root / name / case).mkdir(parents=True)
        (root / name / case / "m.json").write_text(json.dumps({
            "per joint mm": {"Hips": [hips, 9.0], "Knee": [knee, 8.0]}, "per group deg": {"Leg": [leg, 5.0]},
            "bones outside skin %": {"shin": shin}, "bones outside all %": share}))
    return root / name


def test_a_step_counts_only_past_its_noise_floor_on_a_fixed_case_set(tmp_path):
    before = scored(written(tmp_path, "before", BEFORE), list(SIDES))
    twice = scored(written(tmp_path, "twice", TWICE), list(SIDES))
    after = scored(written(tmp_path, "after", AFTER), ["a", "b", "d"])

    assert after["b"] is None and "c" not in after
    assert before["a"]["outside all %"] == 7.5 and before["a"]["outside shin %"] == 10.0
    assert before["a"]["joints mean mm"] == 5.0 and before["a"]["turn Leg deg"] == 3.0

    noise = floor(before, twice, SIDES)
    assert noise == pytest.approx({
        "joint Hips mm": np.percentile([0.5, 0.1, 0.3, 0.0], 95), "joint Knee mm": np.percentile([0.5, 1.0, 0.5, 0.5], 95), "turn Leg deg": 1.0,
        "outside shin %": 0.25, "outside all %": 0.5, "joints mean mm": np.percentile([0.5, 0.55, 0.4, 0.25], 95),
        "turns mean deg": 1.0})
    assert scales(noise, {"joint": ["joint Hips mm", "joint Knee mm", "turn Leg deg"], "turn": ["turn Leg deg"],
                          "skin": ["outside shin %"]}) == pytest.approx({"joint": np.percentile([0.5, 1.0, 0.5, 0.5], 95), "turn": 1.0, "skin": 0.25})

    paired = changes(before, after, SIDES)
    assert paired["tuning"]["both"] == ["a", "d"] and paired["check"]["both"] == []
    assert np.allclose(paired["tuning"]["paired"]["joint Knee mm"], [-2.0, -2.0])
    assert np.allclose(paired["tuning"]["paired"]["joint Hips mm"], [-0.2, -0.3])

    report = stepped(before, after, SIDES, noise)
    assert report["tuning"]["cases"] == 3 and report["tuning"]["paired"] == 2
    assert report["tuning"]["failed"] == {"before": [], "after": ["b"]}
    assert report["check"]["cases"] == 1 and report["check"]["paired"] == 0
    assert report["check"]["failed"] == {"before": [], "after": ["c"]} and report["check"]["measures"] == {}
    rows = report["tuning"]["measures"]
    assert rows["joint Knee mm"]["median"] == -2.0 and rows["joint Hips mm"]["median"] == pytest.approx(-0.25)
    assert {measure: row["verdict"] for measure, row in rows.items()} == {
        "joint Hips mm": "unchanged", "joint Knee mm": "better", "turn Leg deg": "worse", "outside shin %": "unchanged",
        "outside all %": "unchanged", "joints mean mm": "better", "turns mean deg": "worse"}
