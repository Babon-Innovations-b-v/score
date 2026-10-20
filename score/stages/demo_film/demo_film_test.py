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

from score import checks, graph  # noqa: E402
from score.stages import demo_film  # noqa: E402
from score.store import PROPS_HOME  # noqa: E402

SMALL = (64, 36)
# A stage with a plain-card puff emitter (fog), as tools/usd/effects.py writes one.
FOGGED = """#usda 1.0
(
    defaultPrim = "hall"
)
def Xform "hall"
{
    def Xform "Effects"
    {
        def Xform "pump_fog"
        {
            token score:effect:look = "puff"
            token score:effect:card = "plain"
        }
    }
}
"""
GLASSED = """#usda 1.0
(
    defaultPrim = "hall"
)
def Xform "hall"
{
    def Material "pane"
    {
        def Shader "surface"
        {
            uniform token info:id = "UsdPreviewSurface"
            float inputs:opacity = 0.3
        }
    }
    def Material "wall"
    {
        def Shader "surface"
        {
            uniform token info:id = "UsdPreviewSurface"
            float inputs:opacity = 1
        }
    }
}
"""


def folder():
    (PROPS_HOME / "store-tests").mkdir(parents=True, exist_ok=True)
    return pathlib.Path(tempfile.mkdtemp(dir=PROPS_HOME / "store-tests"))


def test_only_the_named_places_have_the_row_and_it_declares_its_tools():
    """#21: a film is a batch the creator said yes to (its record's `final`); one without it keeps its node (the
    basket takes it) and its row is Blocked before anything is bought."""
    own = [name for name, film in demo_film.films().items() if film["place"] == name]
    assert all(demo_film.applies(place) for place in own)
    assert not demo_film.applies("no such place")
    root = folder()
    real = demo_film.FILMS
    try:
        for name, film in (("hall", {"place": "hall", "camera": "door"}),
                           ("yard", {"place": "yard", "camera": "gate", "final": True})):
            (root / f"{name}.json").write_text(json.dumps(film))
        demo_film.FILMS = root
        assert demo_film.applies("hall") and demo_film.applies("yard")
        made = []
        real_one = demo_film.film_one
        demo_film.film_one = lambda stage, name, film, out, log, start: made.append(name)
        try:
            (root / "stage").mkdir()
            (root / "stage/hall.usda").write_text("#usda 1.0\n")
            try:
                demo_film.make({"assembly": root / "stage", "film hall": root / "hall.json"}, root / "out", 0, {})
                raise AssertionError("a film with no yes was made")
            except graph.Blocked as blocked:
                assert "no yes yet for hall" in str(blocked), blocked
            shutil.rmtree(root / "stage")
            (root / "stage").mkdir()
            (root / "stage/yard.usda").write_text("#usda 1.0\n")
            demo_film.make({"assembly": root / "stage", "film yard": root / "yard.json"}, root / "out", 0, {})
        finally:
            demo_film.film_one = real_one
        assert made == ["yard"], made
    finally:
        demo_film.FILMS = real
        shutil.rmtree(root)
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
            (root / f"{name}.json").write_text(json.dumps({"place": place, "camera": camera, "final": True}))
        (root / "nose.json").write_text(json.dumps({"place": "hangar", "camera": "ship"}))  # no yes: Blocked
        demo_film.FILMS = root
        assert demo_film.extras("hangar") == ["hull", "nose"] and demo_film.applies_extra("hangar")
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
            try:
                demo_film.make_extra({"assembly": root / "stage", "film hull": root / "hull.json",
                                      "film nose": root / "nose.json"}, root / "out", 0, {})
                raise AssertionError("a row holding a film with no yes was made")
            except graph.Blocked as blocked:
                assert "no yes yet for nose" in str(blocked), blocked
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


def test_a_film_is_one_batch_dealt_over_the_forecast_s_cards_with_its_high_deadline():
    """#21: the frames are rendered once at SIZE with the films' samples, over the jobs the forecast sizes, each job's
    deadline its frames at the forecast's high frame minutes; the gate holds each film to the size its views
    planned."""
    demo, film_checks = demo_film.film_tools()
    root = folder()
    real_plan, real_render, real_cut = demo.plan, demo_film.render, demo.cut
    planned, deadlines = [], []

    def plan(work, stages, given, jobs_each, size, ink, shots, seconds, start):
        planned.append((tuple(size), jobs_each))
        (work / "views").mkdir(parents=True, exist_ok=True)
        (work / "jobs").mkdir(parents=True, exist_ok=True)
        views = [{"name": f"shot0-{number:03d}", "eye": [0, 1.6, 0], "aim": [0, 1.6, -1], "fov": 70}
                 for number in range(4)]
        written = demo.film_jobs(work, "hall", stages / "hall/hall.usda", [], views, "look", 2, size, ink)
        (work / "views/hall.json").write_text(json.dumps({"size": list(size), "views": views, "moves": []}))
        return written

    def render(jobs, log_folder):
        asked = [json.loads(pathlib.Path(json.loads(path.read_text())["args"][1]).read_text()) for path in jobs]
        deadlines.extend(json.loads(path.read_text())["minutes"] for path in jobs)
        assert not any(view.get("review") for job in asked for view in job["views"])
        frames = log_folder / ".work/frames/hall"
        frames.mkdir(parents=True)
        Image.new("RGB", tuple(asked[0]["size"]), (90, 90, 90)).save(frames / "shot0-000-look.png")

    def cut(work, names):
        (work / "videos").mkdir()
        (work / "videos/hall.mp4").write_bytes(b"")

    try:
        demo.plan, demo_film.render, demo.cut = plan, render, cut
        (root / "stage").mkdir()
        (root / "stage/hall.usda").write_text(FOGGED)
        (root / "stage/scene.json").write_text(json.dumps({"views": [{"name": "door", "eye": [0, 1.6, 0],
                                                                      "aim": [0, 1.6, -1]}]}))
        demo_film.film_one(root / "stage", "hall", {"place": "hall", "camera": "door", "final": True}, root / "out",
                           root / "log")
        expected = demo_film.forecast(root / "stage/hall.usda", 1)
        assert planned == [(demo_film.SIZE, expected["jobs"])], planned
        high = demo_film.FOG_FRAME_MINUTES
        assert deadlines == [round(demo_film.JOB_LEAD_MINUTES + high * 2)] * 2, deadlines
        assert Image.open(root / "out/concept.png").size == demo_film.SIZE
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


def test_the_forecast_prices_fog_and_glass_at_the_high_frame_time_and_a_plain_stage_at_the_measured_one():
    """#21: the free scan finds a plain-card puff (fog) and a see-through surface (glass), never an opaque one; a stage
    with either is priced high at FOG_FRAME_MINUTES a frame, a plain one at demo.FRAME_MINUTES likely and high."""
    demo, _ = demo_film.film_tools()
    root = folder()
    try:
        for name, text in (("plain", "#usda 1.0\ndef Xform \"hall\"\n{\n}\n"), ("fog", FOGGED), ("glass", GLASSED)):
            (root / f"{name}.usda").write_text(text)
        plain, fog, glass = (demo_film.forecast(root / f"{name}.usda", demo_film.SHOTS)
                             for name in ("plain", "fog", "glass"))
        assert plain["frames"] == 192 and plain["frame_minutes"] == demo.FRAME_MINUTES
        assert plain["high_frame_minutes"] == demo.FRAME_MINUTES * demo_film.FRAME_SPREAD
        assert plain["euros"] == demo_film.LIKELY_EUROS and plain["high_euros"] == demo_film.EUROS
        assert fog["slow"] == {"fog": 1, "volumes": 0, "glass": 0}, fog["slow"]
        assert glass["slow"] == {"fog": 0, "volumes": 0, "glass": 1}, glass["slow"]
        assert fog["high_frame_minutes"] == glass["high_frame_minutes"] == demo_film.FOG_FRAME_MINUTES
        assert fog["high_euros"] > 20 * fog["euros"] and fog["jobs"] == plain["jobs"] >= 1
        assert "1 fog" in demo_film.forecast_line(fog), demo_film.forecast_line(fog)
    finally:
        shutil.rmtree(root)


def test_a_film_whose_forecast_high_passes_its_clearance_is_blocked_before_its_frames_are_bought():
    """#21: the yes is given on the cleared price; a fogged film's forecast high passes it and is a new ask, a plain
    film's high is the row's estimate and passes; outside a cleared run nothing is compared."""
    root = folder()
    try:
        (root / "plain.usda").write_text("#usda 1.0\ndef Xform \"hall\"\n{\n}\n")
        (root / "fog.usda").write_text(FOGGED)
        plain, fog = (demo_film.forecast(root / f"{name}.usda", demo_film.SHOTS) for name in ("plain", "fog"))
        demo_film.refuse_over_clearance("hall", plain, demo_film.EUROS)
        demo_film.refuse_over_clearance("hall", fog, None)
        try:
            demo_film.refuse_over_clearance("hall", fog, demo_film.EUROS)
            raise AssertionError("a fogged film passed a plain film's clearance")
        except graph.Blocked as blocked:
            assert "a new ask" in str(blocked), blocked
    finally:
        shutil.rmtree(root)


def test_the_forecast_counts_the_shots_film_one_makes_and_leaves_the_record_alone():
    """#21: a place whose record holds one camera is forecast at one shot, as film_one plans it."""
    from score.stages.demo_film import __main__ as forecast_cli
    root = folder()
    try:
        record = {"views": [{"name": "door", "eye": [0, 1.6, 0], "aim": [0, 1.6, -1]}]}
        (root / "scene.json").write_text(json.dumps(record))
        assert forecast_cli.shots_of(root / "scene.json", {"place": "hall", "camera": "door"}) == 1
        record["views"].append({"name": "back", "eye": [5, 1.6, 5], "aim": [0, 1.6, 0]})
        (root / "scene.json").write_text(json.dumps(record))
        assert forecast_cli.shots_of(root / "scene.json", {"place": "hall", "camera": "door"}) == 2
        assert json.loads((root / "scene.json").read_text()) == record
    finally:
        shutil.rmtree(root)


def test_the_frames_ask_cards_only_so_no_card_in_stock_is_a_hole():
    """#21: the frames' classes are cards; blender_cloud takes the first one in stock and never a processor machine in
    a card's place (batch.one_class_in_stock), so a film priced on cards runs on cards or is a hole."""
    sys.path.insert(0, str(REPO / "tools/props/cloud"))
    import provider
    assert all(provider.cards(name) for name in demo_film.CLASSES.split(","))


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
