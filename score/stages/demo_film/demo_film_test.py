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


def test_a_film_is_a_small_preview_until_the_creator_says_final():
    """#20: a film before the creator's yes is drawn at PREVIEW_SIZE with the review's samples; its record's `final`
    makes it once at SIZE with the films' own; the gate holds each film to the size its views planned."""
    demo, film_checks = demo_film.film_tools()
    root = folder()
    real_plan, real_render, real_cut = demo.plan, demo_film.render, demo.cut
    planned = []

    def plan(work, stages, given, jobs_each, size, ink, shots, seconds, start):
        planned.append(tuple(size))
        (work / "views").mkdir(parents=True, exist_ok=True)
        (work / "jobs").mkdir(parents=True, exist_ok=True)
        views = [{"name": "shot0-000", "eye": [0, 1.6, 0], "aim": [0, 1.6, -1], "fov": 70}]
        written = demo.film_jobs(work, "hall", stages / "hall/hall.usda", [], views, "look", 1, size, ink)
        (work / "views/hall.json").write_text(json.dumps({"size": list(size), "views": views, "moves": []}))
        return written

    def render(jobs, log_folder):
        asked = [json.loads(pathlib.Path(json.loads(path.read_text())["args"][1]).read_text()) for path in jobs]
        rendered.append([view.get("review", False) for view in asked])
        frames = log_folder / ".work/frames/hall"
        frames.mkdir(parents=True)
        Image.new("RGB", tuple(asked[0]["size"]), (90, 90, 90)).save(frames / "shot0-000-look.png")

    def cut(work, names):
        (work / "videos").mkdir()
        (work / "videos/hall.mp4").write_bytes(b"")

    rendered = []
    try:
        demo.plan, demo_film.render, demo.cut = plan, render, cut
        (root / "stage").mkdir()
        (root / "stage/hall.usda").write_text("#usda 1.0\n")
        (root / "stage/scene.json").write_text(json.dumps({"views": [{"name": "door", "eye": [0, 1.6, 0],
                                                                      "aim": [0, 1.6, -1]}]}))
        for name, film in (("preview", {"place": "hall", "camera": "door"}),
                           ("final", {"place": "hall", "camera": "door", "final": True})):
            demo_film.film_one(root / "stage", "hall", film, root / name, root / f"log-{name}")
        assert planned == [demo_film.PREVIEW_SIZE, demo_film.SIZE], planned
        assert rendered == [[True], [False]], rendered  # the review's samples for the preview only
        assert Image.open(root / "preview/concept.png").size == demo_film.PREVIEW_SIZE
    finally:
        demo.plan, demo_film.render, demo.cut = real_plan, real_render, real_cut
        shutil.rmtree(root)

    root = folder()
    clearance = film_checks.clearance_checks
    try:
        video = look_only_film(root / "cut")  # cut at SMALL, as its views planned
        (root / "out").mkdir()
        shutil.copy(video, root / "out/film.mp4")
        (root / "out/views.json").write_text(json.dumps({"size": list(SMALL), "views": [], "moves": []}))
        (root / "stage").mkdir()
        (root / "stage/hall.usda").write_text("#usda 1.0\n")
        film_checks.clearance_checks = lambda stage, views: ({}, [])
        _, _, size, faults = demo_film.film_measures(root / "out", root / "stage")
        assert size == SMALL and not any("size" in fault for fault in faults), faults
    finally:
        film_checks.clearance_checks = clearance
        shutil.rmtree(root)


def look_only_film(root):
    """A planned look-only film of SHOTS shots whose frames are all one colour, cut by demo.py: its video."""
    demo, _ = demo_film.film_tools()
    frames = root / "frames/hall"
    frames.mkdir(parents=True)
    count = round(demo_film.SECONDS * demo.RATE)
    views = [{"name": f"shot{shot}-{number:03d}"} for shot in range(demo_film.SHOTS) for number in range(count)]
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
        length = demo_film.planned_seconds(demo_film.SHOTS)
        least, most = length - demo_film.LENGTH_SLACK, length + demo_film.LENGTH_SLACK
        measured = film_checks.video_checks(video, least, most, 2.0, SMALL)
        assert measured["size"] == list(SMALL) and not any("size" in fault for fault in measured["failures"])
        assert least <= measured["seconds"] <= most, measured
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
    """The overseer, 2026-10-15: the launch's 4 s shot ended as the rocket lifted off (start 1 s + lift 5 s, the
    engines' build to release since a7a513b3)."""
    assert demo_film.motion_start({"motion": str(demo_film.REPO / "data/motion/launch.json")}) == 5.0
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
    spots = [{"name": "spot-1", "eye": [0, 1.6, 0], "aim": [1, 1, 0], "fov": 75},
             {"name": "spot-2", "eye": [0.5, 1.6, 0], "aim": [1, 1, 0], "fov": 75},
             {"name": "spot-3", "eye": [3, 1.6, 2], "aim": [0, 1, 0], "fov": 75},
             {"name": "roof", "eye": [9, 1.6, 9], "aim": [9, 9, 9.5], "fov": 75}]
    record.write_text(json.dumps({"views": spots, "floor": [[-2, -1], [2, 3]]}))
    assert demo_film.own_cameras(record, {"camera": "spot-1"}) == ["spot-1", "spot-3"], \
        "the second shot is the record camera furthest from the first, none looking up at a roof"
    assert len(json.loads(record.read_text())["views"]) == 4, "record cameras add nothing"
    cameras = demo_film.own_cameras(record, {"camera": "bed", "eye": [-1.5, 1.4, 0.5], "aim": [-4.5, 0.3, 3.5],
                                             "then": {"camera": "corner", "across": {"eye": [0.0, 1.0],
                                                                                     "aim": [1.0, 0.0]},
                                                      "fov": 90, "stand": True}})
    views = {view["name"]: view for view in json.loads(record.read_text())["views"]}
    assert cameras == ["bed", "corner"], cameras
    assert views["bed"] == {"name": "bed", "eye": [-1.5, 1.4, 0.5], "aim": [-4.5, 0.3, 3.5], "fov": 75}
    assert views["corner"] == {"name": "corner", "eye": [-2.0, 1.6, 3.0], "aim": [2.0, 1.2, -1.0], "fov": 90,
                               "stand": True}, views["corner"]
    assert demo_film.own_cameras(record, {"camera": "spot-2", "then": "spot-1"}) == ["spot-2", "spot-1"]


def test_a_film_record_leaves_out_the_prims_it_names_in_its_copy_only():
    from pxr import Usd, UsdGeom
    path = folder() / "room.usda"
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.Xform.Define(stage, "/room/Places/tube/Outside/near")
    stage.GetRootLayer().Save()
    demo_film.leave_out(path, {"camera": "spot-1"})
    opened = Usd.Stage.Open(str(path))  # held, or its prim expires with it
    assert opened.GetPrimAtPath("/room/Places/tube/Outside").IsActive()
    demo_film.leave_out(path, {"camera": "spot-1", "leave_out": ["/room/Places/tube/Outside"]})
    opened = Usd.Stage.Open(str(path), Usd.Stage.LoadAll)
    opened.Reload()
    assert not opened.GetPrimAtPath("/room/Places/tube/Outside").IsActive()


def test_a_film_record_may_name_its_own_start():
    assert demo_film.film_start({"camera": "spot-1", "start": 6}, {}) == 6.0
    assert demo_film.film_start({"camera": "spot-1"}, {}) == 0.0, "no motion record: the stage's start"
