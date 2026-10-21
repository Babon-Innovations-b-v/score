"""The row-kind classification (row_kinds.py) on rows written here and on the house rules (data/checks/row-kinds.json):
each row's kind comes from its reading noun first, then its name's last word; a scene's emitting, moving and loose
rows are picked out; a row's objects are found on a stage made here, outside the layers' own scopes.

Run: .venv/bin/python score/stages/row_kinds_test.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score.stages import row_kinds  # noqa: E402

RULES = {"door": {"nouns": ["door", "hatch"], "does": ["moves"]},
         "kettle": {"nouns": ["kettle"], "does": ["emits", "loose"]},
         "loose": {"nouns": ["chair", "cylinder"], "does": ["loose"]}}


def test_the_noun_decides_before_the_name():
    # a "door panel" is a panel (its noun), not a door; a row read with no noun falls back on its name's last word
    assert row_kinds.kind_of({"id": "door_panel", "name": "door panel", "noun": "panel"}, RULES) is None
    assert row_kinds.kind_of({"id": "airlock_door", "name": "airlock door", "noun": "door"}, RULES) == "door"
    assert row_kinds.kind_of({"id": "gas_cylinder", "name": "gas cylinder"}, RULES) == "loose"
    assert row_kinds.kind_of({"id": "round_hatch"}, RULES) == "door"
    assert row_kinds.kind_of({"id": "light_switch", "name": "light switch", "noun": "switch"}, RULES) is None
    # a noun of two words is matched whole: a "floor plate" is no plate, though "plate" is a loose noun
    assert row_kinds.kind_of({"id": "floor_plate", "name": "floor plate", "noun": "floor plate"},
                             {"loose": {"nouns": ["plate"], "does": ["loose"]}}) is None


def test_a_kind_can_do_more_than_one_thing():
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
    assert row_kinds.does("computer", rules) == {"shows", "loose"}


def test_a_row_s_objects_are_found_outside_the_layers_scopes():
    from pxr import Usd, UsdGeom
    stage = Usd.Stage.CreateInMemory()
    for path in ("/toy", "/toy/Fixtures", "/toy/Fixtures/door_1", "/toy/Fixtures/door_1/door_1", "/toy/Objects",
                 "/toy/Objects/door_2", "/toy/Objects/door_frame_1", "/toy/Effects", "/toy/Effects/door_3"):
        UsdGeom.Xform.Define(stage, path)
    assert row_kinds.objects_of(stage, "toy", "door") == ["/toy/Fixtures/door_1", "/toy/Objects/door_2"]
    assert row_kinds.objects_of(stage, "toy", "window") == []
    assert row_kinds.objects_of(stage, "elsewhere", "door") == []


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
