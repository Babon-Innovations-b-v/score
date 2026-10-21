"""The picked designs' people (data/people/rows.json, #26): every people row maps to a look of the shared line or a
named new one, the crowd to one far look read off its words, its palettes library surfaces or undecided with why;
the tube's cast names the player and the square's the crowd look; the line's data holds exactly the mapped looks, each baked at its person row's size; a
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
                assert fields["crowd"] in line or fields["crowd"] in found["new"], (place, row)
                assert fields["palettes"] is not None or fields["palettes_from"].startswith("not decided"), (place, row)
                assert all(len(palette) == 3 and set(palette) <= set(surfaces) for palette in fields["palettes"] or [])
            else:
                assert len(fields["looks"]) == fields["count"], (place, row)  # one look a person
                assert all(look in line or look in found["new"] for look in fields["looks"]), (place, row)
    every = [look for entry in found["places"].values() for fields in entry["rows"].values()
             for look in fields.get("looks", [])]
    assert len(every) == len(set(every)), "a look worn by two people"
    crowds = {fields["crowd"] for entry in found["places"].values() for fields in entry["rows"].values()
              if "crowd" in fields}
    assert sorted((set(every) | crowds) - line) == sorted(found["new"]), "a new look not listed, or a listed one unused"


def test_the_tube_casts_the_player_and_the_square_its_crowd():
    tube = people_rows.cast_record("tube")
    player = next(person for person in tube["people"] if person["name"] == "person_right")
    assert (player["character"], player["look"]) == ("player_wide", "player_wide_work"), player
    assert all(person["at"] in people_rows.place_entry("tube")["spots"] for person in tube["people"])
    assert "concept 3059819b" in tube["from"] and "crowd" not in tube
    square = people_rows.cast_record("square")
    assert square["crowd"]["look"] == "kit_m_avg_coat-grey" and square["crowd"]["count"] is None
    assert square["crowd"]["palettes"] == [] and square["crowd"]["palettes_from"] == people_rows.UNDECIDED_PALETTES


def test_the_line_holds_the_mapped_looks_each_baked_at_its_rows_size():
    records = {name: json.loads(path.read_text()) for name, path in people_rows.LINE_FILES.items()}
    props, inventory, surfaces = people_rows.line_rows(people_rows.read(), records["props"], records["inventory"],
                                                       records["surfaces"])
    assert (props, inventory, surfaces) == (records["props"], records["inventory"], records["surfaces"]), \
        "the line's data is not written from rows.json: run python -m score.stages.people_rows"
    assert set(props["objects"]) == {"player_wide-work", "kit_m_avg-coat-grey"}
    assert set(surfaces["bake"]["entries"]) == set(surfaces["bake"]["models"]) == set(props["objects"])
    assert people_rows.size_of("player_wide-work")[1] == "tube/person_right"
    size, origin = people_rows.size_of("kit_m_avg-coat-grey")
    assert people_rows.person_sized(size) and origin == "square/crowd"  # never the street crowd's 8 x 10 m extent


def test_each_line_row_is_drawn_from_the_person_that_maps_it():
    """#26: the shared loop draws each look's close-up from the picked design's person row that maps it (its view the
    kept concept, its box SAM 3's, grounded), so no take row and no work folder stands before the line; the line is
    approved by those picks, as the Pixal3D batch takes a design."""
    import tempfile
    records = {name: json.loads(path.read_text()) for name, path in people_rows.LINE_FILES.items()}
    with tempfile.TemporaryDirectory() as held:
        kept = pathlib.Path(held)
        (kept / "tube.json").write_text(json.dumps({"rows": [{"id": "person_right", "box": [1, 2, 3, 4]}]}))
        props, inventory, _ = people_rows.line_rows(people_rows.read(), records["props"], records["inventory"],
                                                    records["surfaces"], kept)
    rows = {row["id"]: row for row in inventory["rows"]}
    assert rows["player_wide-work"]["view"] == "tube" and rows["player_wide-work"]["box"] == [1, 2, 3, 4]
    assert rows["player_wide-work"]["grounded"] and rows["player_wide-work"]["prop"] == "player_wide-work"
    assert rows["kit_m_avg-coat-grey"]["view"] is None, "the square keeps no inventory here"
    assert inventory["plan"]["views"] == [{"id": "tube", "picture": "{home}/design/concepts/tube.png"}]
    assert inventory["approved"]["by"] == "the creator's pick" and inventory["approved"]["places"] == ["tube"]
    assert "closeup" not in props["objects"]["player_wide-work"]


def test_each_line_rows_close_up_words_say_who_the_look_is():
    """#26: the first people benchmark drew the player, a Chinese man in his thirties by his spec, as someone else:
    the close-up's words were the reading's clothes alone. Every look's words start with its spec's description."""
    from score.stages.props import closeup_row
    inventory = json.loads(people_rows.LINE_FILES["inventory"].read_text())
    rows = {row["id"]: row for row in inventory["rows"]}
    words = {row["id"]: row["words"] for row in closeup_row.inventory_rows(inventory, people_rows.every_look())}
    assert words["player_wide-work"].startswith("a Chinese man in his thirties")
    for look, said in words.items():
        assert said == f"{people_rows.description_of(look)}; {rows[look]['clothes']}"


def test_a_refresh_keeps_the_choices_of_the_same_concept():
    inventory = {"concept_pick": {"sha256": "one"}, "rows": [
        {"id": "pilot", "name": "person", "noun": "person", "count": 2, "size": [0.5, 0.3, 1.8], "route": "people"},
        {"id": "crowd", "name": "crowd of people", "noun": "people", "count": 1, "route": "people"},
        {"id": "chair", "name": "chair", "noun": "chair", "count": 1, "route": "prop"}]}
    fresh = people_rows.refreshed_place("deck", inventory, None, None)
    assert fresh["rows"]["pilot"]["looks"] == ["deck_pilot_1-new", "deck_pilot_2-new"] and "chair" not in fresh["rows"]
    assert fresh["rows"]["crowd"]["crowd"] == "kit_m_avg-coat-grey" and fresh["rows"]["crowd"]["palettes"] is None
    fresh["rows"]["pilot"]["looks"] = ["player_wide-work", "deck_pilot_2-new"]
    assert people_rows.refreshed_place("deck", inventory, None, fresh)["rows"]["pilot"]["looks"][0] == \
        "deck_pilot_1-new", "a pick with no why is no hand-made choice: read again from the design"
    fresh["rows"]["pilot"]["why"] = "the owner's pick"
    assert people_rows.refreshed_place("deck", inventory, None, fresh)["rows"]["pilot"]["looks"][0] == "player_wide-work"
    redrawn = {**inventory, "concept_pick": {"sha256": "two"}}
    assert people_rows.refreshed_place("deck", redrawn, None, fresh)["rows"]["pilot"]["looks"][0] == "deck_pilot_1-new"



def test_a_crowds_look_is_read_off_its_words():
    """No city square's coats on every crowd: the people line's look sharing the most of the row's words, a crowd
    word only between looks that share no other, a new look when none shares a word."""
    line = {"kit_m_avg-coat-grey": {"object": "a person in a plain mid grey coat", "far_only": True},
            "player_wide-work": {"object": "a person in a dark navy one-piece work suit"}}
    def look(name, noun):
        return people_rows.crowd_look("moon", {"id": "crowd", "name": name, "noun": noun}, line)
    assert look("crowd of people", "people") == "kit_m_avg-coat-grey"  # "an ordinary citizen in the crowd"
    assert look("crowd of astronauts", "crowd") == "player_wide-work"  # "an astronaut of a Moon base"
    assert look("flock of penguins", "penguin") == "moon_crowd_1-new"
    assert people_rows.new_looks({"moon": {"rows": {"crowd": {"name": "flock of penguins", "crowd": "moon_crowd_1-new"}}}},
                                 set(line)) == {"moon_crowd_1-new": {"words": "flock of penguins", "from": "moon/crowd"}}


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("people rows checks pass")
