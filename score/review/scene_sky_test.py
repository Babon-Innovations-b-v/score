"""Each scene's kept sky inputs (score/review/scene_sky.py): a top scene keeps its own site and scene time from the
environment's plan, a room within it its top scene's, a scene with no time keeps none, and one that loses its time
has its kept sky taken out; the kept inputs give the sky overhead.py works out at that site (a house under its sun at
its equinox noon, 90 degrees less its latitude up)."""
import json

import pytest

from score.review import environment_plan, overhead, scene_sky
from score.review.environment_plan_test import kept_setting
from score.review.setting_test import HOUSE
from score.store import Store

NOON = "2024-03-20T12:00:00Z"


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(scene_sky, "KEPT", tmp_path / "sky")
    return Store.in_folder(tmp_path / "store")


def timed(store, when):
    """The house's environment plan with its scene time set to `when` (None: none), kept as his edit."""
    kept_setting(store, HOUSE)
    plan = environment_plan.derived(store)
    plan["maps"][0]["sites"][0]["time"] = when
    return environment_plan.edited(store, plan, "joey")["plan"]


def test_a_room_keeps_the_site_and_time_of_the_top_scene_it_stands_in(store):
    plan = timed(store, NOON)
    found = scene_sky.sky_of(plan, "kitchen", "house")
    assert found["top"] == "house" and found["time"] == NOON
    assert found["site"] == {"on": "meadow", "x": 0.0, "y": 0.0, "height_m": 0.0}
    sun = overhead.seen(found["setting"], found["site"], found["time"])["lights"][0]
    assert sun["altitude"] == pytest.approx(90.0 - 52.0, abs=0.01) and sun["azimuth"] == pytest.approx(180.0, abs=0.01)
    assert scene_sky.sky_of(plan, "barn", "barn") is None  # no site on the plan


def test_keep_writes_a_timed_scene_and_takes_it_out_once_its_time_is_gone(store):
    timed(store, NOON)
    assert scene_sky.keep(store, ["house"]) == (["house"], ["house"])
    kept = json.loads((scene_sky.KEPT / "house.json").read_text())
    assert kept["place"] == kept["top"] == "house" and kept["setting"]["lights"][0]["name"] == "Sun"
    assert scene_sky.keep(store, ["house"]) == (["house"], [])  # unchanged: written once
    timed(store, None)  # a new version of the physics: the timed plan is out of date, the derived one has no time
    assert scene_sky.keep(store, ["house"]) == ([], ["house"])
    assert not (scene_sky.KEPT / "house.json").exists()
