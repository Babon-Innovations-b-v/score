"""The picked designs' people (data/people/rows.json, #26): every people row maps to looks of the shared line, the
crowd to one far look read off its words, its palettes library surfaces or undecided with why; one look (one body)
for the people the rows say are and wear the same, written from its largest standing row alone (its spec and take); a crowd stands on the plan items its row makes; the tube's
cast names the player and the square's the crowd look; the line's data holds exactly the mapped looks, each baked at
its person row's size; a refresh keeps the hand-made choices of a row read from the same concept."""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
# Run as a script, this folder is sys.path[0], and its `library` package would shadow tools/props/library's
# `library` that palette_library imports bare (it appends that folder, so this one would win).
HERE = pathlib.Path(__file__).resolve().parent
sys.path[:] = [entry for entry in sys.path if pathlib.Path(entry or ".").resolve() != HERE]
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
                assert len(fields["looks"]) == fields["count"], (place, row)  # a look for each person
                assert all(look in line for look in fields["looks"]), (place, row)  # every person can be made
    # one body a look (owner, 2026-10-22): the camp's, the garage's and the airlock's astronauts are one look
    assert people_rows.mapping_rows(found)["astronaut-made"]
    assert {fields["looks"][0] for place in ("camp", "garage", "airlock") for fields in
            found["places"][place]["rows"].values()} == {"astronaut-made"}
    assert all(look.endswith(f"-{people_rows.OUTFIT}") for look in line), "a row asks for the drawn face"


def test_people_rows_are_grouped_into_looks_by_what_they_are_and_wear():
    """One body a look (owner, 2026-10-22): a row's words before where it stands or what it holds, its pose and
    colour words left out (its clip and its dress vary it); a named person or the player is a look of its own."""
    def look(name, crowd=False, row="row"):
        return people_rows.look_of("deck", {"id": row, "name": name, "noun": "person"}, crowd)
    assert look("seated astronaut") == look("astronaut standing") == look("astronauts") == "astronaut-made"
    assert look("person sitting at a table") == look("people on walkway") == look("person holding an umbrella") \
        == look("person") == "person-made"
    assert look("worker in blue jumpsuit") == look("worker in grey jumpsuit") == "worker_jumpsuit-made"
    assert look("person in uniform") == "person_uniform-made" != look("person in spacesuit")
    assert look("crowd of people", crowd=True) == "crowd-made" and look("crowd of aliens", crowd=True) == "alien-made"
    assert look("the player in a work suit", row="hero") == look("Nev at the console", row="hero") == "deck_hero-made"


def test_a_person_row_s_look_is_written_from_the_row_alone():
    """#26: a design's person is made from its row, never a hand-written character file: who by the row's words, the
    build by its metres, face, hair and clothes as the concept draws them; a spec the maker takes."""
    sys.path.insert(0, str(REPO / "tools/characters/maker"))
    import spec as specs
    found = {"places": {"deck": {"concept": "abcdef0123", "rows": {
        "pilot": {"name": "pilot in a red suit", "noun": "person", "count": 2, "size": [0.3, 0.4, 1.7],
                  "where": "standing at the console", "share": 0.2, "looks": ["pilot_suit-made"] * 2},
        "guest": {"name": "seated guest", "noun": "person", "count": 1, "size": [0.7, 0.9, 1.3],
                  "where": "sitting on a sofa", "looks": ["guest-made"]},
        "copilot": {"name": "seated pilot in a suit", "noun": "person", "count": 1, "size": [0.7, 0.9, 1.3],
                    "where": "sitting at the console", "share": 0.5, "looks": ["pilot_suit-made"]},
        "crowd": {"name": "crowd of people", "noun": "crowd", "count": 1, "size": [8.0, 9.0, 1.8],
                  "crowd": "crowd-made", "palettes": None}}}}}
    surfaces = json.loads(people_rows.LINE_FILES["surfaces"].read_text())
    made = people_rows.designed_specs(found, surfaces)
    assert set(made) == {"pilot_suit-made", "guest-made", "crowd-made"}
    pilot = made["pilot_suit-made"]  # drawn from its largest standing person, never the bigger seated one
    assert pilot["name"] == "pilot_suit" and pilot["outfits"] == ["made"] and "abcdef01" in pilot["approved"]
    assert pilot["description"] == "pilot in a red suit, a slim build, as drawn in the deck concept", pilot
    assert people_rows.size_of("pilot_suit-made", found) == ([0.3, 0.4, 1.7], "deck/pilot")
    assert "a broad build" in made["guest-made"]["description"]  # seated: its narrower side, 0.7 m
    assert made["crowd-made"]["description"].startswith("one person of the crowd of people, an average build")
    assert all(not specs.problems_of(spec) for spec in made.values()), [specs.problems_of(s) for s in made.values()]
    assert people_rows.member_size("crowd-made", found) == ([0.55, 0.55, 1.8], "deck/crowd")
    props, inventory, lined = people_rows.with_designed(made, {"objects": {}}, {"rows": []}, surfaces)
    take = lined["bake"]["models"]["pilot_suit-made"]
    assert take == "pilot_suit-made-s1" and props["objects"]["pilot_suit-made"]["take"] == take
    assert lined["takes"][take]["spec"] == "data/people/specs/pilot_suit.json"
    assert lined["takes"][take]["outfit"] == "made" and {row["id"] for row in inventory["rows"]} == set(made)
    assert all(entry["spec"].startswith("data/people/specs/") for entry in surfaces["takes"].values()), \
        "every look on the line is written from a design's row (the hand-made makes were retired, 2026-10-21)"


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
    counted = {**entry["rows"]["crowd"], "count": 30}
    assert people_rows.crowd_record("crowd", counted, entry)["count"] == 30
    import library
    try:  # a palette of surfaces the (empty) library does not hold names them, never a KeyError
        people_rows.crowd_record("crowd", {**counted, "palettes": [["skin_light", "wool_grey", "leather_black"]]},
                                 entry)
    except library.LibraryEmpty as empty:
        assert "skin_light" in str(empty) and library.EMPTY in str(empty), empty
    else:
        raise AssertionError("a crowd palette was coloured from surfaces no library holds")


def test_the_tube_casts_its_people_and_the_square_its_crowd():
    tube = people_rows.cast_record("tube")
    person = next(person for person in tube["people"] if person["name"] == "person_right")
    assert (person["character"], person["look"]) == ("person_uniform", "person_uniform_made"), person
    assert {person["look"] for person in tube["people"]} == {"person_uniform_made"}  # its three people, one look
    assert all(person["at"] in people_rows.place_entry("tube")["spots"] for person in tube["people"])
    assert "concept 3059819b" in tube["from"] and "crowd" not in tube
    square = people_rows.cast_record("square")
    assert square["crowd"]["look"] == "crowd_made" and square["crowd"]["count"] is None
    assert square["crowd"]["palettes"] == [] and square["crowd"]["palettes_from"] == people_rows.UNDECIDED_PALETTES


def test_the_line_holds_the_mapped_looks_each_baked_at_its_rows_size():
    records = {name: json.loads(path.read_text()) for name, path in people_rows.LINE_FILES.items()}
    props, inventory, surfaces = people_rows.line_rows(people_rows.read(), records["props"], records["inventory"],
                                                       records["surfaces"])
    assert (props, inventory, surfaces) == (records["props"], records["inventory"], records["surfaces"]), \
        "the line's data is not written from rows.json: run python -m score.stages.people_rows"
    assert set(props["objects"]) == people_rows.every_look()  # every look the designs map, each on the line
    assert set(surfaces["bake"]["entries"]) == set(surfaces["bake"]["models"]) == set(props["objects"])
    assert people_rows.size_of("person_uniform-made")[1] == "tube/person_right"  # the larger of the tube's two rows
    size, origin = people_rows.size_of("crowd-made")
    assert people_rows.person_sized(size) and origin == "stairwell/crowd"  # one member, never the crowd's extent
    found = {"places": {"stairwell": people_rows.place_entry("stairwell")}}  # five people standing apart on 10 x 30 m
    size, origin = people_rows.size_of("person-made", found)
    assert people_rows.person_sized(size) and origin == "stairwell/walkway_crowd", (size, origin)


def test_each_line_row_is_drawn_from_the_person_that_maps_it():
    """#26: the shared loop draws each look's close-up from the picked design's person row that maps it (its view the
    kept concept, its box SAM 3's, grounded), so no take row and no work folder stands before the line; the line is
    approved by those picks, as the Pixal3D batch takes a design."""
    import tempfile
    records = {name: json.loads(path.read_text()) for name, path in people_rows.LINE_FILES.items()}
    with tempfile.TemporaryDirectory() as held:
        kept = pathlib.Path(held)
        (kept / "tube.json").write_text(json.dumps({"rows": [{"id": "person_right", "box": [1, 2, 3, 4]}]}))
        boxes = [[number, 0, number + 1, 2 + number % 3] for number in range(5)]
        (kept / "garage.json").write_text(json.dumps({"rows": [{"id": "astronaut", "box": boxes[0],
                                                                 "boxes": boxes}]}))
        props, inventory, _ = people_rows.line_rows(people_rows.read(), records["props"], records["inventory"],
                                                    records["surfaces"], kept)
    rows = {row["id"]: row for row in inventory["rows"]}
    right = rows["person_uniform-made"]
    assert right["view"] == "tube" and right["box"] == [1, 2, 3, 4]
    assert right["grounded"] and right["prop"] == "person_uniform-made"
    assert rows["crowd-made"]["view"] is None, "the stairwell keeps no inventory here"
    assert inventory["plan"]["views"] == [{"id": place, "picture": f"{{home}}/design/concepts/{place}.png"}
                                          for place in ("garage", "tube")]
    assert inventory["approved"]["by"] == "the creator's pick"
    assert inventory["approved"]["places"] == ["garage", "tube"]
    assert "closeup" not in props["objects"]["person_uniform-made"]
    # a look drawn from the tallest of its row's SAM 3 instances: its largest person
    assert rows["astronaut-made"]["view"] == "garage" and rows["astronaut-made"]["box"] == boxes[2]


def test_each_line_rows_close_up_words_say_who_the_look_is():
    """#26: the first people benchmark drew its player, a Chinese man in his thirties by his spec, as someone else:
    the close-up's words were the reading's clothes alone. Every look's words start with its spec's description."""
    from score.stages.props import closeup_row
    inventory = json.loads(people_rows.LINE_FILES["inventory"].read_text())
    rows = {row["id"]: row for row in inventory["rows"]}
    words = {row["id"]: row["words"] for row in closeup_row.inventory_rows(inventory, people_rows.every_look())}
    assert words["person_uniform-made"].startswith("person in uniform, an average build")
    for look, said in words.items():
        assert said == f"{people_rows.description_of(look)}; {rows[look]['clothes']}"


def test_a_refresh_keeps_the_choices_of_the_same_concept():
    inventory = {"concept_pick": {"sha256": "one"}, "rows": [
        {"id": "pilot", "name": "person", "noun": "person", "count": 2, "size": [0.5, 0.3, 1.8], "route": "people"},
        {"id": "crowd", "name": "crowd of people", "noun": "people", "count": 1, "route": "people"},
        {"id": "chair", "name": "chair", "noun": "chair", "count": 1, "route": "prop"}]}
    fresh = people_rows.refreshed_place("deck", inventory, None, None)
    assert fresh["rows"]["pilot"]["looks"] == ["person-made", "person-made"] and "chair" not in fresh["rows"]
    assert fresh["rows"]["crowd"]["crowd"] == "crowd-made" and fresh["rows"]["crowd"]["palettes"] is None, \
        "a crowd takes no look drawn from another scene's row"
    fresh["rows"]["pilot"]["looks"] = ["deck_pilot-made", "person-made"]
    assert people_rows.refreshed_place("deck", inventory, None, fresh)["rows"]["pilot"]["looks"][0] == \
        "person-made", "a pick with no why is no hand-made choice: read again from the design"
    fresh["rows"]["pilot"]["why"] = "the owner's pick: the player"
    assert people_rows.refreshed_place("deck", inventory, None, fresh)["rows"]["pilot"]["looks"][0] == \
        "deck_pilot-made"
    redrawn = {**inventory, "concept_pick": {"sha256": "two"}}
    assert people_rows.refreshed_place("deck", redrawn, None, fresh)["rows"]["pilot"]["looks"][0] == "person-made"


def test_a_crowds_look_is_read_off_its_words():
    """No city square's coats on every crowd: the people line's look sharing the most of the row's words, a crowd
    word only between looks that share no other, a new look when none shares a word."""
    import tempfile
    with tempfile.TemporaryDirectory() as held:
        citizen, astronaut = pathlib.Path(held) / "citizen.json", pathlib.Path(held) / "astronaut.json"
        citizen.write_text(json.dumps({"description": "a man in his thirties, an ordinary citizen in the crowd"}))
        astronaut.write_text(json.dumps({"description": "a man in his thirties, an astronaut of a Moon base"}))
        line = {"citizen-coat": {"object": "a person in a plain mid grey coat", "far_only": True,
                                 "spec": str(citizen)},
                "astronaut-work": {"object": "a person in a dark navy one-piece work suit", "spec": str(astronaut)}}

        def look(name, noun):
            return people_rows.crowd_look("moon", {"id": "crowd", "name": name, "noun": noun}, line)
        assert look("crowd of people", "people") == "citizen-coat"  # "an ordinary citizen in the crowd"
        assert look("crowd of astronauts", "crowd") == "astronaut-work"  # "an astronaut of a Moon base"
        assert look("flock of penguins", "penguin") == "flock_penguin-made"  # its own words' (designed_specs)
        # who the row names decides, never its crowd word alone: a city crowd's look is no one else's crowd
        assert look("crowd of aliens", "crowd") == "alien-made"
        assert look("crowd of martian colonists", "crowd") == "martian_colonist-made"
        assert look("crowd of shoppers in grey coats", "crowd") == "citizen-coat"
        # a look drawn from another scene's crowd row is that row's own, however its words match
        drawn = pathlib.Path(held) / "crowd.json"
        drawn.write_text(json.dumps({"description": "one person of the crowd of people, as drawn in the square concept"}))
        square = {"square_crowd-drawn": {"object": "one person of the crowd of people", "far_only": True,
                                         "spec": str(people_rows.SPECS / "square_crowd.json")},
                  "people-made": {"object": "one person of the crowd of people", "far_only": True,
                                  "spec": str(drawn)}}
        row = {"id": "crowd", "name": "crowd of people", "noun": "crowd"}
        assert people_rows.crowd_look("moon", row, square) == "crowd-made"
        assert people_rows.crowd_look("moon", row, {**line, **square}) == "citizen-coat"


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
    labels = people_clothes.labels()
    # the people's fabrics as their surface library gives them (every old surface retired on 2026-10-21: stand-ins)
    blue = np.array([38, 64, 150], dtype=np.uint8)

    def lab(srgb):
        return [float(value) for value in labels.lab(np.array(srgb, dtype=float)[None] / 255)[0]]
    fabrics = {"jacket_blue": lab(blue), "suit_light_blue": lab([150, 180, 220]), "suit_grey": lab([128, 128, 128])}
    assert people_clothes.fabrics() == {}  # the repository's library holds none
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
    assert people_rows.dressed_looks("deck", found) == {("worker_jumpsuit-made", "jacket_blue"),
                                                        ("person-made", None)}
    assert people_rows.every_dressed(found) == {("worker_jumpsuit-made", "jacket_blue")}
    assert {person["name"]: person["surface"] for person in people_rows.cast_record("deck", found)["people"]} == {
        "worker": "jacket_blue", "pilot": None}


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("people rows checks pass")
