"""Checks for the duplicate check on made-up inventories: one object made twice fails, placed again passes, a reason or
a reuse excuses it, code rows and a scene whose takes are not stored are left alone.

Plain python: python3 tools/props/scene/duplicates_test.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import duplicates  # noqa: E402


def a_row(name, kind="generate", **changes):
    row = {"id": name, "kind": kind, "name": f"the {name}"}
    row.update(changes)
    return row


def two_places(first, second):
    return {"hub": {"rows": [first]}, "lab": {"rows": [second]}}


def test_one_object_made_twice_fails():
    found = duplicates.problems(two_places(a_row("desklamp"), a_row("desklamp")),
                                {"hub": {"desklamp_1": "desklamp-r6"}, "lab": {"desklamp_1": "desklamp-lab1"}})
    assert len(found) == 1 and "made twice" in found[0], found


def test_one_model_placed_in_both_passes():
    assert duplicates.problems(two_places(a_row("desklamp"), a_row("desklamp")),
                               {"hub": {"desklamp_1": "desklamp-r6"}, "lab": {"desklamp_1": "desklamp-r6"}}) == []


def test_a_row_about_to_be_made_again_fails():
    found = duplicates.problems(two_places(a_row("kettle"), a_row("kettle")), {"hub": {"kettle": "kettle-r1"}, "lab": {}})
    assert len(found) == 1 and "not made yet" in found[0], found


def test_a_stated_reason_excuses_it():
    second = a_row("power_unit", own_model="a battery cabinet, not the small ground power unit")
    assert duplicates.problems(two_places(a_row("power_unit"), second),
                               {"hub": {"power_unit": "power_unit-g1"}, "lab": {"power_unit": "power_unit-r3"}}) == []


def test_a_reuse_must_name_a_row_and_its_take():
    models = {"hub": {"kettle": "kettle-r1"}, "lab": {"kettle": "kettle-r2"}}
    assert any("made from kettle-r2" in line for line in
               duplicates.problems(two_places(a_row("kettle"), a_row("kettle", reuse="hub:kettle")), models))
    assert any("no inventory row" in line for line in
               duplicates.problems(two_places(a_row("kettle"), a_row("kettle", reuse="hub:pot")), models))


def test_code_rows_and_unstored_scenes_are_left_alone():
    assert duplicates.problems(two_places(a_row("conduit_box", "code"), a_row("conduit_box", "code")), {}) == []
    assert duplicates.problems(two_places(a_row("kettle"), a_row("kettle")), {"hub": {"kettle": "kettle-r1"}}) == []


def test_far_scenery_names_the_same_object():
    found = duplicates.problems(two_places(a_row("far_palm"), a_row("palm")),
                                {"hub": {"far_palm": "palm-a"}, "lab": {"palm": "palm-b"}})
    assert len(found) == 1, found


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("duplicates: all checks passed")
