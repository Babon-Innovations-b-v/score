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


def test_a_row_the_concept_does_not_show_says_why():
    assert inventory.problems(an_inventory(a_row(box=None, unseen="behind the camera")), "habitat") == []
    wrong = inventory.problems(an_inventory(a_row(box=None)), "habitat")
    assert any("no 'unseen'" in line for line in wrong), wrong


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
        if found.get("no_place"):  # a line no place owns (the people's looks, #41): no scene's inventory
            continue
        assert inventory.problems(found, scene) == [], scene


def a_design(folder, scene, sha, colour):
    """A store in `folder` holding one locked concept of `scene`: its picture (a plain `colour` PNG) and its lock."""
    from PIL import Image
    _, _, Store = place.design()
    store = Store.in_folder(folder)
    objects = pathlib.Path(folder) / "objects"
    (objects / "blobs").mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 36), colour).save(objects / "blobs" / sha, "PNG")
    picks = objects / "concepts" / scene / "picks"
    picks.mkdir(parents=True, exist_ok=True)
    (picks / f"{len(list(picks.iterdir())):04d}.json").write_text(json.dumps(
        {"place": scene, "sha": sha, "by": "owner", "at": "2026-10-21T10:00:00+00:00", "environment": None}))
    return store


def test_a_scenes_style_is_its_environments_line_and_its_locked_concepts_look():
    """A scene added in the app (no place.json entry) is worded from its design alone: the environment concept's
    style line, then its locked concept's look, read once by one call on that very picture and kept."""
    asked = []
    def asker(question, picture):
        asked.append((question, picture.getpixel((0, 0))))
        return "  matte  sand-blasted steel, warm amber light "
    with tempfile.TemporaryDirectory() as folder:
        store, looks = a_design(folder, "garden_shed", "a" * 64, (200, 10, 10)), pathlib.Path(folder) / "looks"
        assert "garden_shed" not in place.places()
        assert place.unread(["garden_shed"], store, looks) == ["garden_shed"]
        assert place.kept_style("garden_shed", store, looks) is None  # a dry run's words: nothing asked
        environment = place.environment_style(store)
        assert environment == place.design()[1].style_now() and environment  # no EC version kept: today's
        style = place.style_text("garden_shed", store, asker, looks)
        assert style == f"{environment.rstrip('.')}. matte sand-blasted steel, warm amber light"
        assert asked == [(place.LOOK_QUESTION, (200, 10, 10))]
        assert place.style_text("garden_shed", store, asker, looks) == style and len(asked) == 1  # kept, asked once
        assert place.kept_style("garden_shed", store, looks) == style and place.unread(["garden_shed"], store, looks) == []
        kept = json.loads((looks / "garden_shed" / f"{'a' * 64}.json").read_text())
        assert kept["concept"] == "a" * 64 and kept["model"] == place.LOOK_MODEL
        a_design(folder, "garden_shed", "b" * 64, (10, 10, 200))  # a new lock: its look is read again
        place.style_text("garden_shed", store, asker, looks)
        assert asked[-1][1] == (10, 10, 200) and len(asked) == 2


def test_a_scene_with_no_locked_concept_or_an_empty_look_is_refused():
    with tempfile.TemporaryDirectory() as folder:
        store, looks = a_design(folder, "galley", "c" * 64, (0, 0, 0)), pathlib.Path(folder) / "looks"
        assert "no locked concept" in refusal(lambda: place.style_text("lab", store, lambda *_: "x", looks))
        assert "no locked concept" in refusal(lambda: place.unread(["lab"], store, looks))
        assert "came back empty" in refusal(lambda: place.style_text("galley", store, lambda *_: " ", looks))
        assert place.unread(["galley"], store, looks) == ["galley"]  # nothing kept for an empty answer


def test_every_place_keeps_the_design_system_shape():
    """Every place keeps its name, short name and style (its palette, materials, wear, light, pictures and plan were
    the old concepts' and were retired, 2026-10-21: a scene's are its design's)."""
    for name, entry in place.places().items():
        if name == place.SHARED:
            assert entry["scale"]["eye_height"] == 1.6
            continue
        for field in ("name", "style"):
            assert field in entry, f"{name} has no {field}"
        retired = {"plan", "palette", "materials", "wear", "light", "pictures"} & set(entry)
        assert not retired, f"{name} keeps retired fields {sorted(retired)}"


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    main()
