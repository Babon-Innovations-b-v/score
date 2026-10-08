"""Check the scene inventories and the places' design system: the inventory's shape (inventory.py),
the refusal of a cloud run without an approved inventory, and the place file's
style text and its refusal (place.py).

Plain python, run by the gate with the system python: python3 tools/props/scene/inventory_test.py
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import inventory  # noqa: E402
import place  # noqa: E402


def a_row(**changes):
    row = {"id": "r1", "view": "v1", "box": [10, 20, 300, 400], "name": "white louvred locker",
           "kind": "generate", "anchor": "wall", "size": [0.6, 0.5, 1.9], "count": 2,
           "thing": "prop:habitat_locker"}
    row.update(changes)
    return row


def an_inventory(*rows, **changes):
    found = {"scene": "habitat", "place": "habitat",
             "plan": {"world": "w1", "seed": 7, "views": [{"id": "v1", "picture": "WORK/v1.png"}]},
             "approved": "2026-10-05, plan: w1", "migrated": "",
             "room": {"shell": "abc", "light": "place", "backdrop": "", "wall_fill": []},
             "rows": list(rows) or [a_row()]}
    found.update(changes)
    return found


def refusal(call):
    try:
        call()
    except SystemExit as stopped:
        return str(stopped)
    raise AssertionError("it was not refused")


def test_a_sound_inventory_has_no_problems():
    assert inventory.problems(an_inventory(), "habitat") == []


def test_a_row_with_no_box_on_a_kept_view_is_refused():
    wrong = inventory.problems(an_inventory(a_row(view="v9")), "habitat")
    assert any("no box, no row" in line for line in wrong), wrong


def test_a_row_must_say_its_kind_anchor_size_and_count():
    wrong = inventory.problems(an_inventory(a_row(kind="shared", anchor="somewhere", size=[1, 0, 1], count=0)), "habitat")
    assert len(wrong) == 4, wrong


def test_a_row_stands_only_on_a_row_there_is():
    host = a_row(id="r1", anchor="floor")
    assert inventory.problems(an_inventory(host, a_row(id="r2", anchor="on:r1")), "habitat") == []
    assert inventory.problems(an_inventory(host, a_row(id="r2", anchor="on:r7")), "habitat")


def test_a_mechanic_row_names_its_node_and_its_model():
    bare = a_row(kind="mechanic", thing="node:Workstation")
    assert inventory.problems(an_inventory(bare), "habitat")
    assert inventory.problems(an_inventory(a_row(kind="mechanic", thing="node:Workstation", prop="desk")), "habitat") == []


def test_a_scene_is_never_migrated_before_the_owner_approved_it():
    wrong = inventory.problems(an_inventory(approved="", migrated="2026-10-06"), "habitat")
    assert any("approval" in line for line in wrong), wrong


def test_the_cloud_refuses_a_missing_or_unapproved_inventory():
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder) / "habitat.json"
        assert "no inventory" in refusal(lambda: inventory.approved_inventory(path))
        path.write_text(json.dumps(an_inventory(approved="")))
        assert "not approved" in refusal(lambda: inventory.approved_inventory(path))
        path.write_text(json.dumps(an_inventory()))
        assert inventory.approved_inventory(path)["scene"] == "habitat"


def test_every_committed_inventory_is_sound():
    for scene, found in inventory.every_inventory().items():
        assert inventory.problems(found, scene) == [], scene


def test_the_habitat_and_the_flat_have_their_style_text_in_the_repo():
    assert "pale panelled sleep pods" in place.style_text("habitat")  # its style v2, from its picked concept K03
    assert "one-room state flat" in place.style_text("prologue_flat")


def test_a_place_with_no_style_text_or_none_at_all_is_refused():
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder) / "place.json"
        path.write_text(json.dumps({"shared": {}, "lab": {"style": {"text": ""}}}))
        assert "no style text" in refusal(lambda: place.style_text("lab", path))
        assert "no place" in refusal(lambda: place.style_text("garage", path))
        assert "no place" in refusal(lambda: place.style_text("shared", path))


def test_an_objects_picture_is_worded_from_the_place():
    wording = place.object_wording("habitat", "white louvred locker", (0.6, 0.5, 1.9))
    assert wording.startswith("one white louvred locker, 0.60 m wide") and place.style_text("habitat") in wording


def test_every_place_keeps_the_design_system_shape():
    for name, entry in place.places().items():
        if name == place.SHARED:
            assert entry["scale"]["eye_height"] == 1.6
            continue
        for field in ("style", "plan", "palette", "materials", "light", "pictures"):
            assert field in entry, f"{name} has no {field}"
        tokens = set(entry["palette"]["tokens"]) | set(entry["palette"]["accents"])
        assert all(material["token"] in tokens | {"hull"} for material in entry["materials"].values()), name


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    main()
