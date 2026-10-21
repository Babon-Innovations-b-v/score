"""The picked designs' people (data/people/rows.json, #26): every people row maps to a look of the shared line or a
named new one, the crowd to one far look in palettes of library surfaces; the tube's cast names the player and the
square's the crowd look; the line's data holds exactly the mapped looks, each baked at its person row's size; a
refresh keeps the hand-made choices of a row read from the same concept."""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from score.stages import people_rows  # noqa: E402


def test_every_people_row_maps_to_a_look():
    found = people_rows.read()
    line = people_rows.line_looks()
    sys.path.append(str(REPO / "tools/props/library"))
    import library
    surfaces = library.resolved(people_rows.LINE)
    for place, entry in found["places"].items():
        for row, fields in entry["rows"].items():
            if "crowd" in fields:
                assert fields["crowd"] in line, (place, row)
                assert all(len(palette) == 3 and set(palette) <= set(surfaces) for palette in fields["palettes"])
            else:
                assert len(fields["looks"]) == fields["count"], (place, row)  # one look a person
                assert all(look in line or look in found["new"] for look in fields["looks"]), (place, row)
    every = [look for entry in found["places"].values() for fields in entry["rows"].values()
             for look in fields.get("looks", [])]
    assert len(every) == len(set(every)), "a look worn by two people"
    assert sorted(set(every) - line) == sorted(found["new"]), "a new look not listed, or a listed one unused"


def test_the_tube_casts_the_player_and_the_square_its_crowd():
    tube = people_rows.cast_record("tube")
    player = next(person for person in tube["people"] if person["name"] == "person_right")
    assert (player["character"], player["look"]) == ("player_wide", "player_wide_work"), player
    assert all(person["at"] in people_rows.place_entry("tube")["spots"] for person in tube["people"])
    assert "concept 3059819b" in tube["from"] and "crowd" not in tube
    square = people_rows.cast_record("square")
    assert square["crowd"]["look"] == "kit_m_avg_coat-grey" and square["crowd"]["count"] is None
    assert all(len(colour) == 3 and all(0 <= value <= 255 for value in colour)
               for palette in square["crowd"]["palettes"] for colour in palette)


def test_the_line_holds_the_mapped_looks_each_baked_at_its_rows_size():
    records = {name: json.loads(path.read_text()) for name, path in people_rows.LINE_FILES.items()}
    props, inventory, surfaces = people_rows.line_rows(people_rows.read(), records["props"], records["inventory"],
                                                       records["surfaces"])
    assert (props, inventory, surfaces) == (records["props"], records["inventory"], records["surfaces"]), \
        "the line's data is not written from rows.json: run python -m score.stages.people_rows"
    assert set(props["objects"]) == {"player_wide-work", people_rows.CROWD_LOOK}
    assert set(surfaces["bake"]["entries"]) == set(surfaces["bake"]["models"]) == set(props["objects"])
    assert people_rows.size_of("player_wide-work")[1] == "tube/person_right"
    size, origin = people_rows.size_of(people_rows.CROWD_LOOK)
    assert people_rows.person_sized(size) and origin == "square/crowd"  # never the street crowd's 8 x 10 m extent


def test_a_refresh_keeps_the_choices_of_the_same_concept():
    inventory = {"concept_pick": {"sha256": "one"}, "rows": [
        {"id": "pilot", "name": "person", "noun": "person", "count": 2, "size": [0.5, 0.3, 1.8], "route": "people"},
        {"id": "crowd", "name": "crowd of people", "noun": "people", "count": 1, "route": "people"},
        {"id": "chair", "name": "chair", "noun": "chair", "count": 1, "route": "prop"}]}
    fresh = people_rows.refreshed_place("deck", inventory, None, None)
    assert fresh["rows"]["pilot"]["looks"] == ["deck_pilot_1-new", "deck_pilot_2-new"] and "chair" not in fresh["rows"]
    assert fresh["rows"]["crowd"]["crowd"] == people_rows.CROWD_LOOK
    fresh["rows"]["pilot"]["looks"] = ["player_wide-work", "deck_pilot_2-new"]
    assert people_rows.refreshed_place("deck", inventory, None, fresh)["rows"]["pilot"]["looks"][0] == "player_wide-work"
    redrawn = {**inventory, "concept_pick": {"sha256": "two"}}
    assert people_rows.refreshed_place("deck", redrawn, None, fresh)["rows"]["pilot"]["looks"][0] == "deck_pilot_1-new"


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("people rows checks pass")
