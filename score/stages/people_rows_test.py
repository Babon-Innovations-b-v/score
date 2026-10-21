"""The picked designs' people (data/people/rows.json, #26): every people row maps to looks of the shared line, the
crowd to one far look read off its words, its palettes library surfaces or undecided with why; a look a row reads
anew is written from the row alone (its spec and take); a crowd stands on the plan items its row makes; the tube's
cast names the player and the square's the crowd look; the line's data holds exactly the mapped looks, each baked at
its person row's size; a refresh keeps the hand-made choices of a row read from the same concept."""
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
                assert fields["palettes"] is not None or fields["palettes_from"].startswith("not decided"), (place, row)
                assert all(len(palette) == 3 and set(palette) <= set(surfaces) for palette in fields["palettes"] or [])
            else:
                assert len(fields["looks"]) == fields["count"], (place, row)  # one look a person
                assert all(look in line for look in fields["looks"]), (place, row)  # every person can be made
    every = [look for entry in found["places"].values() for fields in entry["rows"].values()
             for look in fields.get("looks", [])]
    assert len(every) == len(set(every)), "a look worn by two people"


def test_a_person_row_s_look_is_written_from_the_row_alone():
    """#26: a design's person is made from its row, never a hand-written character file: who by the row's words, the
    build by its metres, face, hair and clothes as the concept draws them; a spec the maker takes."""
    sys.path.insert(0, str(REPO / "tools/characters/maker"))
    import spec as specs
    found = {"places": {"deck": {"concept": "abcdef0123", "rows": {
        "pilot": {"name": "pilot in a red suit", "noun": "person", "count": 2, "size": [0.3, 0.4, 1.7],
                  "where": "standing at the console", "looks": ["deck_pilot_1-drawn", "deck_pilot_2-drawn"]},
        "guest": {"name": "seated guest", "noun": "person", "count": 1, "size": [0.7, 0.9, 1.3],
                  "where": "sitting on a sofa", "looks": ["deck_guest_1-drawn"]},
        "crowd": {"name": "crowd of people", "noun": "crowd", "count": 1, "size": [8.0, 9.0, 1.8],
                  "crowd": "deck_crowd-drawn", "palettes": None}}}}}
    surfaces = json.loads(people_rows.LINE_FILES["surfaces"].read_text())
    made = people_rows.designed_specs(found, surfaces)
    assert set(made) == {"deck_pilot_1-drawn", "deck_pilot_2-drawn", "deck_guest_1-drawn", "deck_crowd-drawn"}
    pilot = made["deck_pilot_1-drawn"]
    assert pilot["name"] == "deck_pilot_1" and pilot["outfits"] == ["drawn"] and "abcdef01" in pilot["approved"]
    assert pilot["description"] == "pilot in a red suit, a slim build, as drawn in the deck concept", pilot
    assert "a broad build" in made["deck_guest_1-drawn"]["description"]  # seated: its narrower side, 0.7 m
    assert made["deck_crowd-drawn"]["description"].startswith("one person of the crowd of people, an average build")
    assert all(not specs.problems_of(spec) for spec in made.values()), [specs.problems_of(s) for s in made.values()]
    assert people_rows.member_size("deck_crowd-drawn", found) == ([0.55, 0.55, 1.8], "deck/crowd")
    props, inventory, lined = people_rows.with_designed(made, {"objects": {}}, {"rows": []}, surfaces)
    take = lined["bake"]["models"]["deck_pilot_1-drawn"]
    assert take == "deck_pilot_1-drawn-s1" and props["objects"]["deck_pilot_1-drawn"]["take"] == take
    assert lined["takes"][take]["spec"] == "data/people/specs/deck_pilot_1.json"
    assert lined["takes"][take]["outfit"] == "drawn" and {row["id"] for row in inventory["rows"]} == set(made)
    hand = {look for look, entry in surfaces["bake"]["models"].items() if "characters/makes" in
            surfaces["takes"][entry]["spec"]}
    assert not hand & set(people_rows.designed_specs(people_rows.read(), surfaces)), "a hand spec written over"


def test_a_crowd_s_ground_is_the_plan_items_its_row_makes():
    plan = {"w": 20.0, "d": 10.0, "items": [["CROWD 1", 2.0, 1.0, 6.0, 4.0, None, "item"],
                                            ["BENCH 1", 0.0, 0.0, 1.0, 1.0, "N", "item"]],
            "rows": {"CROWD 1": ["crowd"], "BENCH 1": ["bench"]}}
    assert people_rows.crowd_ground(plan, "crowd") == [[-8.0, -4.0, 6.0, 4.0]]  # unframed: the plan's middle at 0
    assert people_rows.crowd_ground(plan, "pilot") == [] and people_rows.crowd_ground(None, "crowd") == []
    inventory = {"concept_pick": {"sha256": "0badcafe"}, "rows": [
        {"id": "crowd", "name": "crowd of people", "noun": "people", "count": 1, "route": "people"}]}
    entry = people_rows.refreshed_place("deck", inventory, plan, None)
    crowd = people_rows.crowd_record("crowd", entry["rows"]["crowd"], entry)
    assert crowd["spread"] == [-8.0, -4.0, 6.0, 4.0] and crowd["grounds"] == [[-8.0, -4.0, 6.0, 4.0]]
    assert crowd["count"] is None and crowd["seed"] == 0x0badcafe and crowd["facing_to"] == entry["middle"]
    assert crowd["palettes"] == [] and crowd["palettes_from"] == people_rows.UNDECIDED_PALETTES
    counted = {**entry["rows"]["crowd"], "count": 30, "palettes": [["skin_light", "wool_grey", "leather_black"]]}
    assert people_rows.crowd_record("crowd", counted, entry)["count"] == 30


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
    assert set(props["objects"]) == people_rows.every_look()  # every look the designs map, each on the line
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
        boxes = [[number, 0, number + 1, 2] for number in range(7)]
        (kept / "campgrounds.json").write_text(json.dumps({"rows": [{"id": "astronaut", "box": boxes[0],
                                                                      "boxes": boxes}]}))
        props, inventory, _ = people_rows.line_rows(people_rows.read(), records["props"], records["inventory"],
                                                    records["surfaces"], kept)
    rows = {row["id"]: row for row in inventory["rows"]}
    assert rows["player_wide-work"]["view"] == "tube" and rows["player_wide-work"]["box"] == [1, 2, 3, 4]
    assert rows["player_wide-work"]["grounded"] and rows["player_wide-work"]["prop"] == "player_wide-work"
    assert rows["kit_m_avg-coat-grey"]["view"] is None, "the square keeps no inventory here"
    assert inventory["plan"]["views"] == [{"id": place, "picture": f"{{home}}/design/concepts/{place}.png"}
                                          for place in ("campgrounds", "tube")]
    assert inventory["approved"]["by"] == "the creator's pick"
    assert inventory["approved"]["places"] == ["campgrounds", "tube"]
    assert "closeup" not in props["objects"]["player_wide-work"]
    # each of a row's people drawn from its own SAM 3 instance, never seven close-ups of the first one
    assert [rows[f"campgrounds_astronaut_{number}-drawn"]["box"] for number in range(1, 8)] == boxes


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
    assert fresh["rows"]["pilot"]["looks"] == ["deck_pilot_1-drawn", "deck_pilot_2-drawn"] and "chair" not in fresh["rows"]
    assert fresh["rows"]["crowd"]["crowd"] == "kit_m_avg-coat-grey" and fresh["rows"]["crowd"]["palettes"] is None
    fresh["rows"]["pilot"]["looks"] = ["player_wide-work", "deck_pilot_2-drawn"]
    assert people_rows.refreshed_place("deck", inventory, None, fresh)["rows"]["pilot"]["looks"][0] == \
        "deck_pilot_1-drawn", "a pick with no why is no hand-made choice: read again from the design"
    fresh["rows"]["pilot"]["why"] = "the owner's pick"
    assert people_rows.refreshed_place("deck", inventory, None, fresh)["rows"]["pilot"]["looks"][0] == "player_wide-work"
    redrawn = {**inventory, "concept_pick": {"sha256": "two"}}
    assert people_rows.refreshed_place("deck", redrawn, None, fresh)["rows"]["pilot"]["looks"][0] == "deck_pilot_1-drawn"


def test_a_crowds_look_is_read_off_its_words():
    """No city square's coats on every crowd: the people line's look sharing the most of the row's words, a crowd
    word only between looks that share no other, a new look when none shares a word."""
    line = {"kit_m_avg-coat-grey": {"object": "a person in a plain mid grey coat", "far_only": True,
                                    "spec": "data/characters/makes/kit_m_avg_prop.json"},
            "player_wide-work": {"object": "a person in a dark navy one-piece work suit",
                                 "spec": "data/characters/makes/player_wide_prop.json"}}
    def look(name, noun):
        return people_rows.crowd_look("moon", {"id": "crowd", "name": name, "noun": noun}, line)
    assert look("crowd of people", "people") == "kit_m_avg-coat-grey"  # "an ordinary citizen in the crowd"
    assert look("crowd of astronauts", "crowd") == "player_wide-work"  # "an astronaut of a Moon base"
    assert look("flock of penguins", "penguin") == "moon_crowd-drawn"  # drawn from its row (designed_specs)
    # who the row names decides, never its crowd word alone: a city crowd's look is no one else's crowd
    assert look("crowd of aliens", "crowd") == look("crowd of martian colonists", "crowd") == "moon_crowd-drawn"
    assert look("crowd of shoppers in grey coats", "crowd") == "kit_m_avg-coat-grey"


def a_concept(fabric_lab_colour, box):
    """A 100 x 100 concept, dark, the box's torso painted the given sRGB (0..255)."""
    import numpy as np
    picture = np.full((100, 100, 3), 20, dtype=np.uint8)
    left, top, right, bottom = box
    picture[top:bottom, left:right] = fabric_lab_colour
    return picture


def test_a_row_wears_the_fabric_its_words_name_nearest_its_torso():
    """The concept decides the clothes, per row: of the people fabrics its name names, the nearest its measured torso
    within people_clothes.WITHIN; a row naming none, or one whose torso is far from every named fabric, wears its
    look's own paint; and the cast and the dress rows follow the row (no hand-kept list of places)."""
    import numpy as np
    from score.stages import people_clothes
    fabrics = people_clothes.fabrics()
    labels = people_clothes.labels()
    import library
    blue = np.round(labels.srgb(np.array(library.resolved("people")["jacket_blue"]["colour"])) * 255).astype(np.uint8)
    box = [20, 10, 60, 90]
    inventory = {"concept_pick": {"sha256": "one"}, "rows": [
        {"id": "worker", "name": "worker in blue jumpsuit", "where": "near the light", "noun": "worker", "count": 1,
         "size": [0.5, 0.3, 1.8], "route": "people", "boxes": [box]},
        {"id": "pilot", "name": "person", "where": "left", "noun": "person", "count": 1, "size": [0.5, 0.3, 1.8],
         "route": "people", "box": box}]}
    entry = people_rows.refreshed_place("deck", inventory, None, None, a_concept(blue, box), fabrics)
    worker, pilot = entry["rows"]["worker"]["dress"], entry["rows"]["pilot"]["dress"]
    assert worker["surface"] == "jacket_blue" and worker["de"] < 1 and worker["figures"] == 1, worker
    assert "suit_light_blue" in worker["named"] and not any("light" in name and "blue" not in name
                                                            for name in worker["named"]), worker
    assert pilot["surface"] is None and pilot["named"] == [], pilot
    orange = a_concept([230, 90, 20], box)
    far = people_rows.refreshed_place("deck", inventory, None, None, orange, fabrics)["rows"]["worker"]["dress"]
    assert far["surface"] is None and far["de"] > people_clothes.WITHIN, far
    unseen = people_rows.refreshed_place("deck", inventory, None, None, None, fabrics)["rows"]["worker"]["dress"]
    assert unseen["surface"] is None and unseen["torso_lab"] is None, unseen
    found = {"places": {"deck": {**entry, "concept": "one"}}}
    assert people_rows.dressed_looks("deck", found) == {("deck_worker_1-drawn", "jacket_blue"),
                                                        ("deck_pilot_1-drawn", None)}
    assert people_rows.every_dressed(found) == {("deck_worker_1-drawn", "jacket_blue")}
    assert {person["name"]: person["surface"] for person in people_rows.cast_record("deck", found)["people"]} == {
        "worker": "jacket_blue", "pilot": None}


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("people rows checks pass")
