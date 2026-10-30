"""A step counts only past its noise floor, on a fixed case set (#70). Red when: a case one scoring could not fit is
dropped from the set instead of counted as its failure (test_failed_case_counted); the floor is not the spread of the
same point scored twice (test_floor_is_twice_scored_spread); a median change inside the floor is called better or
worse (test_inside_floor_unchanged); a kind's unit is not its measures' median floor (test_scales_from_noise)."""
import numpy as np

from . import changes, floor, scales, verdict

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
