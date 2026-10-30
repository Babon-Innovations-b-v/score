"""A step counts only past its noise floor, on a fixed case set (#70). Red when: a case one scoring could not fit is
dropped from the set instead of counted as its failure (test_failed_case_counted); the floor is not the spread of the
same point scored twice (test_floor_is_twice_scored_spread); a median change inside the floor is called better or
worse (test_inside_floor_unchanged); a kind's unit is not its measures' median floor (test_scales_from_noise); a
missing m.json is dropped instead of read as a failure, or the share outside is not the reported one
(test_scored_reads_failures); a step's report drops its failures or verdicts (test_stepped_report)."""
import json
import pathlib
import tempfile

import numpy as np

from . import changes, floor, scales, scored, stepped, verdict

SIDES = {"a": "tuning", "b": "tuning", "c": "check"}


def test_failed_case_counted():
    before = {"a": {"joint": 10.0}, "b": {"joint": 12.0}, "c": {"joint": 9.0}}
    after = {"a": {"joint": 9.0}, "b": None}
    report = changes(before, after, SIDES)
    assert report["tuning"]["cases"] == 2 and report["tuning"]["failed"]["after"] == ["b"]
    assert report["check"]["failed"]["after"] == ["c"] and report["check"]["both"] == []
    assert np.allclose(report["tuning"]["paired"]["joint"], [-1.0])


def test_floor_is_twice_scored_spread():
    first = {case: {"joint": 10.0} for case in SIDES}
    second = {"a": {"joint": 10.5}, "b": {"joint": 9.9}, "c": {"joint": 10.0}}
    assert np.isclose(floor(first, second, SIDES)["joint"], np.percentile([0.5, 0.1, 0.0], 95))


def test_inside_floor_unchanged():
    paired = {"joint": np.array([-0.2, -0.3, -0.1]), "turn": np.array([-2.0, -1.5, -3.0]), "skin": np.array([1.0, 2.0])}
    noise = {"joint": 0.5, "turn": 1.0, "skin": 0.5}
    assert verdict(paired, noise) == {"joint": "unchanged", "turn": "better", "skin": "worse"}


def test_scales_from_noise():
    noise = {"Leg": 2.0, "Arm": 4.0, "Shin": 3.0, "Hips": 1.0}
    assert scales(noise, {"joint": ["Leg", "Arm", "Shin"], "turn": ["Hips"]}) == {"joint": 3.0, "turn": 1.0}


FOUND = {"per joint mm": {"Hips": [4.0, 9.0], "Knee": [6.0, 8.0]}, "per group deg": {"Leg": [3.0, 5.0]},
         "bones outside skin %": {"shin": 10.0}, "bones outside all %": 7.5}


def test_scored_reads_failures():
    with tempfile.TemporaryDirectory() as folder:
        (pathlib.Path(folder) / "a").mkdir()
        (pathlib.Path(folder) / "a" / "m.json").write_text(json.dumps(FOUND))
        found = scored(pathlib.Path(folder), ["a", "b"])
    assert found["b"] is None and found["a"]["outside all %"] == 7.5
    assert found["a"]["joints mean mm"] == 5.0 and found["a"]["turn Leg deg"] == 3.0


def test_stepped_report():
    before = {"a": {"joint": 10.0}, "b": {"joint": 12.0}, "c": {"joint": 9.0}}
    after = {"a": {"joint": 8.0}, "b": {"joint": 10.0}, "c": None}
    report = stepped(before, after, SIDES, {"joint": 1.0})
    assert report["tuning"]["measures"]["joint"]["verdict"] == "better"
    assert report["tuning"]["measures"]["joint"]["median"] == -2.0
    assert report["check"]["failed"]["after"] == ["c"] and report["check"]["paired"] == 0
