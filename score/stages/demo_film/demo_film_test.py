"""The demo-film row with no Blender and no spend: only the places the record names have the row, which declares its
tools; demo.py plans look-only frames at the row's size; a look-only plan cuts into a video of that size; and the gate
`film` fails a film with no sound and still frames by name.

Run: .venv/bin/python score/stages/demo_film/demo_film_test.py
"""
import json
import pathlib
import shutil
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from PIL import Image  # noqa: E402

from score import checks  # noqa: E402
from score.stages import demo_film  # noqa: E402
from score.store import PROPS_HOME  # noqa: E402

SMALL = (64, 36)


def folder():
    (PROPS_HOME / "store-tests").mkdir(parents=True, exist_ok=True)
    return pathlib.Path(tempfile.mkdtemp(dir=PROPS_HOME / "store-tests"))


def test_only_the_named_places_have_the_row_and_it_declares_its_tools():
    own = [name for name, film in demo_film.films().items() if film["place"] == name]
    assert all(demo_film.applies(place) for place in own) and not demo_film.applies("no such place")
    found = demo_film.files("hub")
    assert found["scene"] == "{data}/scene/hub.json"
    assert "scene" not in demo_film.files("cockpit"), "a ship room has no seed record; its assembly's record is read"
    assert found["film hub"] == "{data}/definitions/demo_films/hub.json"
    assert not any(name.startswith("film ") and name != "film hub" for name in found)
    assert all((REPO / path).exists() for path in demo_film.TOOLS)
    assert found["tool tools/review/demo.py"] == "{repo}/tools/review/demo.py"


def test_every_film_names_a_camera_its_place_s_scene_record_holds():
    """The path starts at that camera, so a place's own film's first frame is the still beside the concept (K8)."""
    from score.stages import scene_record
    for name, film in demo_film.films().items():
        if scene_record.written(film["place"]):
            continue  # a planned place's cameras are its assembled record's, made by the run, not in data/scene
        record = json.loads((REPO / "data/scene" / f"{film['place']}.json").read_text())
        assert film["camera"] in [view["name"] for view in record["views"]], (name, film)


def test_another_film_of_a_place_is_the_extra_row_s_and_leaves_its_own_film_alone():
    root = folder()
    real = demo_film.FILMS
    try:
        for name, place, camera in (("hangar", "hangar", "across"), ("hull", "hangar", "ship")):
            (root / f"{name}.json").write_text(json.dumps({"place": place, "camera": camera}))
        demo_film.FILMS = root
        assert demo_film.extras("hangar") == ["hull"] and demo_film.applies_extra("hangar")
        assert not demo_film.applies_extra("hub") and not demo_film.applies("hull")
        assert "film hull" not in demo_film.files("hangar")
        assert demo_film.extra_files("hangar")["film hull"] == "{data}/definitions/demo_films/hull.json"
        assert "film hangar" not in demo_film.extra_files("hangar")
        made = []
        real_one = demo_film.film_one
        demo_film.film_one = lambda stage, name, film, out, log, start: made.append((name, film["camera"], out.name))
        try:
            (root / "stage").mkdir()
            (root / "stage/hangar.usda").write_text("#usda 1.0\n")
            demo_film.make_extra({"assembly": root / "stage", "film hull": root / "hull.json"}, root / "out", 0, {})
        finally:
            demo_film.film_one = real_one
        assert made == [("hull", "ship", "hull")], made
        assert demo_film.extra_faults(root / "stage") == ["no film"]
    finally:
        demo_film.FILMS = real
        shutil.rmtree(root)


def test_the_plan_asks_look_only_frames_at_its_size():
    demo, _ = demo_film.film_tools()
    root = folder()
    try:
        (root / "views").mkdir()
        (root / "jobs").mkdir()
        views = [{"name": f"shot0-{number:03d}", "eye": [0, 1.6, 0], "aim": [0, 1.6, -1], "fov": 70}
                 for number in range(4)]
        written = demo.film_jobs(root, "hall", root / "hall/hall.usda", [], views, "look", 2, demo_film.SIZE, False)
        assert len(written) == 2
        asked = json.loads((root / "views/hall-0.json").read_text())
        assert asked["size"] == list(demo_film.SIZE)
        assert all(view["look_only"] and "ink" not in view for view in asked["views"])
    finally:
        shutil.rmtree(root)


def look_only_film(root):
    """A planned look-only film of one shot whose frames are all one colour, cut by demo.py: its video."""
    demo, _ = demo_film.film_tools()
    frames = root / "frames/hall"
    frames.mkdir(parents=True)
    count = round(demo_film.SECONDS * demo.RATE)
    views = [{"name": f"shot0-{number:03d}"} for number in range(count)]
    for view in views:
        Image.new("RGB", SMALL, (90, 110, 130)).save(frames / f"{view['name']}-look.png")
    (root / "views").mkdir()
    (root / "views/hall.json").write_text(json.dumps({"size": list(SMALL), "ink": False, "seconds": demo_film.SECONDS,
                                                             "views": views}))
    demo.cut(root, ["hall"])
    return root / "videos/hall.mp4"


def test_a_look_only_plan_cuts_into_a_video_of_its_size():
    _, film_checks = demo_film.film_tools()
    root = folder()
    try:
        video = look_only_film(root)
        measured = film_checks.video_checks(video, demo_film.LEAST, demo_film.MOST, 2.0, SMALL)
        assert measured["size"] == list(SMALL) and not any("size" in fault for fault in measured["failures"])
        assert demo_film.LEAST <= measured["seconds"] <= demo_film.MOST, measured
    finally:
        shutil.rmtree(root)


def test_the_gate_fails_a_silent_still_film_by_name():
    demo, film_checks = demo_film.film_tools()
    root = folder()
    clearance, size = film_checks.clearance_checks, demo_film.SIZE
    try:
        video = look_only_film(root / "cut")
        out = root / "out"
        out.mkdir()
        shutil.copy(video, out / "film.mp4")
        (out / "views.json").write_text(json.dumps({"views": []}))
        (root / "stage").mkdir()
        (root / "stage/hall.usda").write_text("#usda 1.0\n")
        film_checks.clearance_checks = lambda stage, views: ({}, [])
        demo_film.SIZE = SMALL
        verdict = demo_film.judge_film(out, {"assembly": root / "stage"}, {})
        found = " ".join(verdict.findings)
        assert verdict.answer == checks.FAIL and "no sound track" in found and "frozen" in found, found
    finally:
        film_checks.clearance_checks, demo_film.SIZE = clearance, size
        shutil.rmtree(root)


def test_a_film_starts_a_second_before_its_places_first_one_off_moment():
    """The overseer, 2026-10-15: the launch's 4 s shot ended as the rocket lifted off (start 1 s + lift 3 s)."""
    assert demo_film.motion_start({"motion": str(demo_film.REPO / "data/motion/launch.json")}) == 3.0
    assert demo_film.motion_start({"motion": str(demo_film.REPO / "data/motion/garage.json")}) == 0.0  # loops only
    assert demo_film.motion_start({}) == 0.0
    assert "motion" in demo_film.files("launch")


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)


def test_a_film_record_with_its_own_spot_adds_it_to_the_records_copy():
    record = folder() / "scene.json"
    record.write_text(json.dumps({"views": [{"name": "spot-1", "eye": [0, 1.6, 0], "aim": [1, 1, 0], "fov": 75}]}))
    demo_film.own_camera(record, {"camera": "spot-1"})
    assert len(json.loads(record.read_text())["views"]) == 1, "a film record naming a record camera adds nothing"
    demo_film.own_camera(record, {"camera": "bed", "eye": [-1.5, 1.4, 0.5], "aim": [-4.5, 0.3, 3.5]})
    views = {view["name"]: view for view in json.loads(record.read_text())["views"]}
    assert views["bed"] == {"name": "bed", "eye": [-1.5, 1.4, 0.5], "aim": [-4.5, 0.3, 3.5], "fov": 75}
    assert "spot-1" in views


def test_a_film_record_leaves_out_the_prims_it_names_in_its_copy_only():
    from pxr import Usd, UsdGeom
    path = folder() / "room.usda"
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.Xform.Define(stage, "/room/Places/tube/Outside/near")
    stage.GetRootLayer().Save()
    demo_film.leave_out(path, {"camera": "spot-1"})
    assert Usd.Stage.Open(str(path)).GetPrimAtPath("/room/Places/tube/Outside").IsActive()
    demo_film.leave_out(path, {"camera": "spot-1", "leave_out": ["/room/Places/tube/Outside"]})
    assert not Usd.Stage.Open(str(path)).GetPrimAtPath("/room/Places/tube/Outside").IsActive()


def test_a_film_record_may_name_its_own_start():
    assert demo_film.film_start({"camera": "spot-1", "start": 6}, {}) == 6.0
    assert demo_film.film_start({"camera": "spot-1"}, {}) == 0.0, "no motion record: the stage's start"
