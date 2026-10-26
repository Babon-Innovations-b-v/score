"""A scene inventory row's kind comes from its own reading words alone (row_kinds.py): its reading noun first, matched
whole, its name's last word only for a row read with no noun, else the kind its name says holds it; a scene's
emitting, moving and loose rows are picked out by what their kind does; a row's objects are found on a stage by name,
outside the layers' own scopes, and a prim no row's object has is a stranger. On rules written here and on the house
rules (data/checks/row-kinds.json, where the expected kinds are read off the file's own nouns by hand).

Breaks that turn it red (each applied once and seen red, then reverted):
- `kind_of`: the noun ignored (`words(row.get("noun")) or` dropped)  -> the noun test ("door panel" read as a door).
- `kind_of`: `wanted in rule["nouns"]` read as any noun inside the words  -> the noun test ("floor plate").
- `held_kind`: `said[-2] in rule["nouns"]` dropped  -> the lamp test ("fence post" read as a lamp).
- `objects_of`: the NOT_OBJECTS prune dropped  -> the objects test (/toy/Effects/door_3 found).
- `of_row`: `(_\\d+)?` read as `.*`  -> the objects test (door_frame_1 found) and the strangers test.
"""
from pxr import Usd, UsdGeom

from score.stages import row_kinds

RULES = {"door": {"nouns": ["door", "hatch"], "does": ["moves"]},
         "kettle": {"nouns": ["kettle"], "does": ["emits", "loose"]},
         "loose": {"nouns": ["chair", "cylinder"], "does": ["loose"]}}


def test_the_noun_decides_before_the_name():
    # a "door panel" is a panel (its noun), not a door; a row read with no noun falls back on its name's last word
    assert row_kinds.kind_of({"id": "door_panel", "name": "door panel", "noun": "panel"}, RULES) is None
    assert row_kinds.kind_of({"id": "airlock_door", "name": "airlock door", "noun": "door"}, RULES) == "door"
    assert row_kinds.kind_of({"id": "gas_cylinder", "name": "gas cylinder"}, RULES) == "loose"
    assert row_kinds.kind_of({"id": "round_hatch"}, RULES) == "door"
    # a noun of two words is matched whole: a "floor plate" is no plate, though "plate" is a loose noun
    assert row_kinds.kind_of({"id": "floor_plate", "name": "floor plate", "noun": "floor plate"},
                             {"loose": {"nouns": ["plate"], "does": ["loose"]}}) is None


def test_a_lamp_read_as_what_holds_it_is_still_a_lamp():
    # a "floodlight tower" read as a tower is the lamp kind's (held_by); a "light switch" and a "fence post" are none
    rules = {"lamp": {"nouns": ["light", "floodlight"], "does": ["glows"], "held_by": ["tower", "frame", "post"]}}
    assert row_kinds.kind_of({"id": "floodlight_tower", "name": "floodlight tower", "noun": "tower"}, rules) == "lamp"
    assert row_kinds.kind_of({"id": "grow_light_frame", "noun": "frame"}, rules) == "lamp"
    assert row_kinds.kind_of({"id": "light_switch", "name": "light switch", "noun": "switch"}, rules) is None
    assert row_kinds.kind_of({"id": "fence_post", "name": "fence post", "noun": "post"}, rules) is None


def test_a_scenes_rows_are_picked_by_what_their_kind_does_and_a_kind_can_do_more_than_one_thing():
    inventory = {"rows": [{"id": "kettle", "noun": "kettle"}, {"id": "stool", "noun": "chair"},
                          {"id": "front_door", "noun": "door"}, {"id": "wall", "noun": "wall"}]}
    assert [row["id"] for row in row_kinds.rows_that(inventory, "loose", RULES)] == ["kettle", "stool"]
    assert [row["id"] for row in row_kinds.rows_that(inventory, "emits", RULES)] == ["kettle"]
    assert [(row["id"], row["row_kind"]) for row in row_kinds.rows_that(inventory, "moves", RULES)] == [
        ("front_door", "door")]


def test_the_house_rules_read_real_words():
    rules = row_kinds.table()
    expected = {("stove", "stove"): "cooker", ("table lamp", "lamp"): "lamp", ("tracked rover", "rover"): "vehicle",
                ("ceiling light", "light"): "lamp", ("dining chair", "chair"): "loose", ("tv", "tv"): "screen",
                ("laptop", "laptop"): "computer", ("planter bed", "planter"): "plant", ("hatch", "hatch"): "door",
                ("door mat", "mat"): None, ("outer wall", "wall"): None}
    for (name, noun), kind in expected.items():
        assert row_kinds.kind_of({"id": name.replace(" ", "_"), "name": name, "noun": noun}, rules) == kind, name


def test_a_rows_objects_are_found_outside_the_layers_scopes_and_anything_else_is_a_stranger():
    stage = Usd.Stage.CreateInMemory()
    for path in ("/toy", "/toy/Fixtures", "/toy/Fixtures/door_1", "/toy/Fixtures/door_1/door_1", "/toy/Objects",
                 "/toy/Objects/door_2", "/toy/Objects/door_frame_1", "/toy/Effects", "/toy/Effects/door_3"):
        UsdGeom.Xform.Define(stage, path)
    assert row_kinds.objects_of(stage, "toy", "door") == ["/toy/Fixtures/door_1", "/toy/Objects/door_2"]
    assert row_kinds.objects_of(stage, "toy", "window") == []
    assert row_kinds.objects_of(stage, "elsewhere", "door") == []
    inventory = {"rows": [{"id": "door"}, {"id": "kettle"}]}
    assert row_kinds.strangers(["Objects/door_2", "Objects/kettle", "Objects/door_frame_1", "Objects/doormat"],
                               inventory) == ["Objects/door_frame_1", "Objects/doormat"]
