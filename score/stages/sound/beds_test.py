"""A scene's bed from its design alone (beds.py), on toy scenes over the environment's own library briefs, reference
bodies and row kinds: a room in a base on the Moon hears the base's room tone over its hum; a greenhouse's planters,
a garage's rover, a tube's shape, a craft's room and a shelter alone in the open each hear their own tone; outside
on the Moon and on Mars a person hears only the suit; outside on Earth the open air, its crowd where a crowd stands;
a body with no surface pressure or a scene no site holds is undecided and named, never guessed; gaps name what
the design lacks, and the row's `bed` gate fails on it.

Run: .venv/bin/python -m pytest score/stages/sound/beds_test.py
"""
import json
import pathlib
import shutil
import sys
import tempfile

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score import checks  # noqa: E402
from score.stages.sound import beds, gates, needs  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]
SETTING = {"bodies": [{"body": "moon", "reference": "moon"}, {"body": "mars", "reference": "mars"},
                      {"body": "earth", "reference": "earth"}, {"body": "rock", "name": "Rock", "radius_km": 10.0,
                                                                "mass_kg": 1e15}],
           "plots": [], "sites": [{"place": "base", "on": "moon"}, {"place": "crater", "on": "moon"},
                                  {"place": "dunes", "on": "mars"}, {"place": "plaza", "on": "earth"},
                                  {"place": "cave", "on": "rock"}]}
HOLDERS = {"within": {name: {"within": "base"} for name in ("room", "farm", "bay", "link", "cabin")} |
           {"hut": {"within": "dunes"}, "flatlet": {"within": "plaza"}},
           "parts": {"pier": {"of": "plaza"}}, "merged": {}}
PLANS = {"base": {"shell": "kit"}, "room": {}, "farm": {}, "bay": {}, "link": {"shape": "tube"}, "cabin": {"ground_free": "in the ship"},
         "hut": {"shell": "outdoor", "inside": True}, "crater": {"shell": "outdoor"}, "dunes": {"shell": "outdoor"},
         "plaza": {"shell": "kit", "inside": False}, "pier": {"shell": "kit", "inside": False},
         "flatlet": {"shell": "kit", "inside": True}, "cave": {"shell": "outdoor"}, "lost": {}}
ROWS = {"farm": ["planter", "lamp"], "bay": ["rover", "workbench"], "plaza": ["crowd", "the stage's speaker"],
        "pier": ["the launch pad's concrete apron"], "room": ["plant", "chair"]}


@pytest.fixture(scope="module")
def toy():
    """A data folder (the environment's sounds, bodies and row kinds; the toy setting, holders and plans) and a
    design folder holding the toy scenes' inventories."""
    folder = pathlib.Path(tempfile.mkdtemp())
    data, design = folder / "data", folder / "design"
    for name in ("sound/sounds.json", "physics/bodies.json", "checks/row-kinds.json"):
        (data / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / "data" / name, data / name)
    (data / "physics/setting.json").write_text(json.dumps(SETTING))
    (data / "places").mkdir()
    (data / "places/within.json").write_text(json.dumps(HOLDERS))
    (data / "plans").mkdir()
    for place, plan in PLANS.items():
        (data / "plans" / f"{place}.json").write_text(json.dumps(plan))
    (design / "inventory").mkdir(parents=True)
    for place, nouns in ROWS.items():
        rows = [{"id": f"{noun.split()[-1]}_{at}", "noun": noun} for at, noun in enumerate(nouns)]
        (design / "inventory" / f"{place}.json").write_text(json.dumps({"rows": rows}))
    yield data, design
    shutil.rmtree(folder)


def bed(toy, place):
    data, design = toy
    return beds.of_place(place, beds.paths(place, data, design))


def test_rooms_hear_their_own_tone(toy):
    assert bed(toy, "room")["sounds"] == ["habitat", "base_hum"]  # one potted plant makes no greenhouse
    assert bed(toy, "farm")["sounds"] == ["greenhouse", "base_hum"]
    assert bed(toy, "bay")["sounds"] == ["garage", "base_hum"]
    assert bed(toy, "link")["sounds"] == ["link_tube", "base_hum"]
    assert bed(toy, "cabin")["sounds"] == ["ship_inside"]  # a craft's room: no base hum through its hull
    assert bed(toy, "hut")["sounds"] == ["camp_room"]  # a shelter alone in the open on Mars
    assert bed(toy, "flatlet")["sounds"] == ["earth_flat"]  # a room where the air outside is breathed


def test_outside_hears_the_suit_or_the_open_air(toy):
    for place in ("crater", "dunes"):  # the Moon's vacuum and Mars's 0.636 kPa, both under the Armstrong limit
        found = bed(toy, place)
        assert found["facts"]["heard"] == "suit" and found["sounds"] == ["suit_fans", "suit_breathing_calm"], found
    assert bed(toy, "plaza")["sounds"] == ["street_night", "prologue_crowd", "square_pa"]
    assert bed(toy, "pier")["sounds"] == ["launch_pad"]  # a part of the plaza, its site the plaza's
    found = bed(toy, "base")  # a top scene round its rooms stands on its site: outside, though its shell is a kit
    assert found["facts"]["heard"] == "suit" and found["sounds"] == ["suit_fans", "suit_breathing_calm"], found


def test_what_the_design_lacks_is_named_never_guessed(toy):
    cave, lost = bed(toy, "cave"), bed(toy, "lost")
    assert cave["sounds"] == [] and cave["facts"]["missing"] == ["rock has no surface pressure"], cave
    assert lost["sounds"] == [] and lost["facts"]["missing"] == ["no site in the setting holds it"], lost
    data, design = toy
    gaps = {gap["id"]: gap for gap in needs.gaps("cave", data, design)}
    assert "rock has no surface pressure" in gaps["sound:bed:room"]["work"], gaps
    assert "cave" in beds.places(data, design) and "sound:bed:room" not in {
        gap["id"] for gap in needs.gaps("room", data, design)}


def test_the_bed_gate_fails_a_scene_whose_design_leaves_its_bed_undecided(toy):
    data, design = toy
    judged = {place: gates.judge_bed(None, beds.paths(place, data, design), None) for place in ("farm", "cave", "lost")}
    assert judged["farm"].answer == checks.PASS, judged["farm"]
    assert judged["cave"].answer == checks.FAIL and judged["cave"].findings == ("rock has no surface pressure",)
    assert judged["lost"].answer == checks.FAIL and judged["lost"].findings == ("no site in the setting holds it",)


def test_a_bed_still_to_make_is_the_sound_row_s_only_where_the_design_has_one(toy):
    """The plaza (a kept design) and the hut (a plan alone) both hear a bed still to make: the plaza's gap is its sound
    row's to make, the hut has no sound row, so its gap names the work, never a node the table lacks."""
    data, design = toy
    plaza, hut = (next(gap for gap in needs.gaps(place, data, design) if gap["id"] == "sound:bed:room")
                  for place in ("plaza", "hut"))
    assert "still to make" in plaza["sentence"] and "still to make" in hut["sentence"], (plaza, hut)
    assert plaza["node"] == "sound@plaza" and plaza["work"] is None, plaza
    assert hut["node"] is None and hut["work"], hut
    assert needs.sounded("plaza", design) and not needs.sounded("hut", design)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
