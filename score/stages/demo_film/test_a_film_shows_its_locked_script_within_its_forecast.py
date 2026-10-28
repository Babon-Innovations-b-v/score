"""A film is made only as a locked film script shows it, within the forecast its yes was cleared at, and is gated on
what its frames show: only a place a locked script shows has the row, its cameras the script's or its scene record's,
its forecast prices fog and glass high before anything is bought, a film too short or too dear is refused before its
frames are rented, and its gate fails a silent, still, unpeopled or unsounded film by name. The environment's own film
is cut only from locked scripts, paced as the owner asked (about 7 s a place), at one loudness. No Blender, no spend:
stages and scripts made here, one small local ffmpeg cut.

Each test names the break that turns it red (`Break: <file>: `old` -> `new``); each was applied once and seen red.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest
score/stages/demo_film/test_a_film_shows_its_locked_script_within_its_forecast.py
"""
import json
import pathlib
import shutil
import subprocess
import sys

import pytest
from PIL import Image

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from pxr import Gf, Usd, UsdGeom, UsdMedia, UsdSkel, Vt  # noqa: E402

from score import checks, graph  # noqa: E402
from score.stages import demo_film  # noqa: E402
from score.stages.demo_film import final, needs, shots  # noqa: E402

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
# A see-through pane and an opaque wall.
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
PLAIN = "#usda 1.0\ndef Xform \"hall\"\n{\n}\n"


def scripted(*shows):
    """A locked film script whose walk-throughs show each of `shows` (a segment's `shows`)."""
    return {"segments": [{"cut": "walk-through", "shows": dict(each), "seconds": 4.0} for each in shows]}


# --- which films a place has, and their cameras --------------------------------------------------------------------

def test_only_the_places_a_locked_script_shows_have_the_row_and_it_declares_its_tools(tmp_path, monkeypatch):
    """A place's films are its locked film scripts' (the lock his yes), never a record written per place: a place a
    locked script shows has the row, keyed on that script and the people its design stands, and makes its own film
    from it at the script's camera; any other has none.
    Break: score/stages/demo_film/__init__.py: `return films().get(place, {}).get("place") == place` -> `return True`
    Break: score/stages/demo_film/__init__.py: `found["people"] = ("{data}/people/rows.json",
        people_rows.place_part(place))` -> `pass`"""
    script = scripted({"place": "yard", "camera": "gate"})
    (tmp_path / "k9.json").write_text(json.dumps(script))
    monkeypatch.setattr(final, "scripts", lambda: {"k9": script})
    made = []
    assert demo_film.applies("yard") and not demo_film.applies("hall")
    found = demo_film.files("yard")
    assert found["script k9"] == "{dashboard}/films/locked/k9.json", found
    assert found["people"][0] == "{data}/people/rows.json", "the people its design stands (seen_faults)"
    assert not any(name.startswith("film ") for name in found), "no per-place film record"
    assert all((REPO / path).exists() for path in demo_film.TOOLS)
    monkeypatch.setattr(demo_film, "film_one",
                        lambda stage, name, film, out, log, start: made.append((name, film["camera"], start)))
    (tmp_path / "stage").mkdir()
    (tmp_path / "stage/yard.usda").write_text("#usda 1.0\n")
    demo_film.make({"assembly": tmp_path / "stage", "script k9": tmp_path / "k9.json"}, tmp_path / "out", 0, {})
    assert made == [("yard", "gate", 0.0)], made


def test_another_film_of_a_place_is_the_extra_row_s_and_leaves_its_own_film_alone(tmp_path, monkeypatch):
    """The hangar's script shows its own film and the hull: the hull is the extra row's (demo-film-extra@hangar), the
    hub has none, and an extra row's output with no film folder fails its contract.
    Break: score/stages/demo_film/__init__.py: `if film["place"] == place and name != place]` -> `if film["place"] ==
        place]`"""
    script = scripted({"place": "hangar", "camera": "across"}, {"place": "hangar", "film": "hull", "camera": "ship"})
    (tmp_path / "k9.json").write_text(json.dumps(script))
    monkeypatch.setattr(final, "scripts", lambda: {"k9": script})
    made = []
    assert demo_film.extras("hangar") == ["hull"] and demo_film.applies_extra("hangar")
    assert not demo_film.applies_extra("hub") and not demo_film.applies("hull")
    assert demo_film.extra_files("hangar")["script k9"] == "{dashboard}/films/locked/k9.json"
    monkeypatch.setattr(demo_film, "film_one",
                        lambda stage, name, film, out, log, start: made.append((name, film["camera"], out.name)))
    (tmp_path / "stage").mkdir()
    (tmp_path / "stage/hangar.usda").write_text("#usda 1.0\n")
    demo_film.make_extra({"assembly": tmp_path / "stage", "script k9": tmp_path / "k9.json"}, tmp_path / "out", 0, {})
    assert demo_film.extra_faults(tmp_path / "stage") == ["no film"]
    assert made == [("hull", "ship", "hull")], made


def test_a_film_with_no_camera_starts_at_its_scene_record_s_first(tmp_path):
    """No camera named: the record's first is the first shot, the other the second; a record with none refuses.
    Break: score/stages/demo_film/__init__.py: `return record["views"][0]["name"]` -> `return
        record["views"][-1]["name"]`"""
    record = tmp_path / "scene.json"
    record.write_text(json.dumps({"views": [{"name": "spot-1", "eye": [0, 1.6, 0], "aim": [1, 1, 0], "fov": 75},
                                            {"name": "spot-2", "eye": [3, 1.6, 2], "aim": [0, 1, 0], "fov": 75}]}))
    assert demo_film.own_cameras(record, {"place": "yard"}) == ["spot-1", "spot-2"]
    record.write_text(json.dumps({"views": []}))
    with pytest.raises(ValueError, match="no camera"):
        demo_film.own_cameras(record, {"place": "yard"})


def test_a_film_s_own_spots_are_added_to_the_record_s_copy(tmp_path):
    """The second shot is the record camera standing furthest from the first (spot-3, 3.6 m off; spot-2 is 0.5 m),
    none looking up at a roof; record cameras add nothing. A spot of its own (`eye`/`aim`, or `across` the floor from
    (-2, -1) to (2, 3): shares (0, 1) are (-2, 3), (1, 0) is (2, -1)) is added as a camera of its name.
    Break: score/stages/demo_film/__init__.py: `return max(others, key=lambda view:
        float(np.linalg.norm(np.subtract(view["eye"], first["eye"]))))` -> `return others[0]`
    Break: score/stages/demo_film/__init__.py: `flat = low + np.asarray(share, dtype=float) * (high - low)` -> `flat =
        np.asarray(share, dtype=float) * (high - low)`"""
    record = tmp_path / "scene.json"
    spots = [{"name": "spot-1", "eye": [0, 1.6, 0], "aim": [1, 1, 0], "fov": 75},
             {"name": "spot-2", "eye": [0.5, 1.6, 0], "aim": [1, 1, 0], "fov": 75},
             {"name": "spot-3", "eye": [3, 1.6, 2], "aim": [0, 1, 0], "fov": 75},
             {"name": "roof", "eye": [9, 1.6, 9], "aim": [9, 9, 9.5], "fov": 75}]
    record.write_text(json.dumps({"views": spots, "floor": [[-2, -1], [2, 3]]}))
    assert demo_film.own_cameras(record, {"camera": "spot-1"}) == ["spot-1", "spot-3"]
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


def test_a_film_leaves_out_the_prims_it_names_in_its_copy_only_and_may_name_its_start(tmp_path):
    """A film naming nothing to leave out leaves the joined tube's Outside on; naming it, the copy makes it inactive.
    A film starts at its own `start` (6 s), else the stage's.
    Break: score/stages/demo_film/__init__.py: `    stage.GetRootLayer().Save()` -> `    pass`
    Break: score/stages/demo_film/__init__.py: `return float(film.get("start", 0.0))` -> `return 0.0`"""
    path = tmp_path / "room.usda"
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.Xform.Define(stage, "/room/Places/tube/Outside/near")
    stage.GetRootLayer().Save()
    demo_film.leave_out(path, {"camera": "spot-1"})
    assert Usd.Stage.Open(str(path)).GetPrimAtPath("/room/Places/tube/Outside").IsActive()
    demo_film.leave_out(path, {"camera": "spot-1", "leave_out": ["/room/Places/tube/Outside"]})
    opened = Usd.Stage.Open(str(path), Usd.Stage.LoadAll)
    opened.Reload()
    assert not opened.GetPrimAtPath("/room/Places/tube/Outside").IsActive()
    assert demo_film.film_start({"camera": "spot-1", "start": 6}) == 6.0
    assert demo_film.film_start({"camera": "spot-1"}) == 0.0


def test_a_frame_blurs_by_how_fast_its_picture_moves_towards_the_next_frame_of_its_shot(tmp_path):
    """The camera's motion blur: half a frame open (180 degrees), shorter where the picture would streak further than
    MOST_STREAK of its width, none for a camera standing still or a shot's last frame, never across a cut; the jobs
    drawn by film_frames.
    Break: score/stages/demo_film/__init__.py: `return 0.0 if speed < STILL_PIXELS else round(min(SHUTTER, MOST_STREAK *
        wide / speed), 3)` -> `return 0.0 if speed < STILL_PIXELS else SHUTTER`
    Break: score/stages/demo_film/__init__.py: `(later if demo.shot_of(later) == demo.shot_of(view) else None)` ->
        `later`"""
    wide = demo_film.SIZE[0]
    first = {"name": "shot0-000", "eye": [0, 1.6, 5], "aim": [0, 1.2, 0], "up": [0, 1, 0], "fov": 75, "frame": 0}
    walked = dict(first, name="shot0-001", eye=[0.02, 1.6, 4.98], frame=1)
    turned = dict(first, name="shot0-001", aim=[0.6, 1.2, 0], frame=1)
    assert demo_film.blur_of(first, dict(first, name="shot0-001", frame=1), wide) is None, "a camera standing still"
    assert demo_film.blur_of(first, None, wide) is None, "a shot's last frame"
    slow = demo_film.blur_of(first, walked, wide)
    assert slow["shutter"] == demo_film.SHUTTER and slow["codes"] == 1 and slow["eye"] == walked["eye"], slow
    fast = demo_film.blur_of(first, turned, wide)
    speed = demo_film.picture_speed(first, turned, wide)
    assert speed > 40 and abs(fast["shutter"] - demo_film.MOST_STREAK * wide / speed) < 1e-3, (speed, fast)
    views = [first, walked, dict(walked, name="shot1-000", eye=[3, 1.6, 3], frame=2)]
    listing, job = tmp_path / "views.json", tmp_path / "job.json"
    listing.write_text(json.dumps({"size": list(demo_film.SIZE), "views": views}))
    job.write_text(json.dumps({"script": "tools/blender/inside/usd_views.py", "args": ["stage", str(listing), "out"]}))
    demo_film.motion_blurred([job], views, wide)
    blurred = json.loads(listing.read_text())["views"]
    assert "blur" in blurred[0] and "blur" not in blurred[1] and "blur" not in blurred[2], "never across a cut"
    assert json.loads(job.read_text())["script"] == demo_film.FRAMES_SCRIPT
    assert "tool " + demo_film.FRAMES_SCRIPT in demo_film.common_files("launch")


# --- the forecast and the refusals before anything is bought -------------------------------------------------------

def test_the_forecast_prices_fog_and_glass_high_and_a_plain_stage_at_the_measured_frame_time(tmp_path):
    """#21: two shots of 4 s at 24 frames are 192 frames; the free scan finds a plain-card puff (fog) and a see-through
    pane, never the opaque wall; a stage with either is priced high at FOG_FRAME_MINUTES a frame (over 20 times its
    likely euros), a plain one at FRAME_SPREAD over the measured frame time, its high the row's estimate.
    Break: score/stages/demo_film/__init__.py: `high = FOG_FRAME_MINUTES if any(slow.values()) else likely *
        FRAME_SPREAD` -> `high = likely * FRAME_SPREAD`
    Break: score/stages/demo_film/__init__.py: `if opacity and opacity.Get() is not None and float(opacity.Get()) <
        1.0:` -> `if opacity and opacity.Get() is not None:`"""
    demo, _ = demo_film.film_tools()
    for name, text in (("plain", PLAIN), ("fog", FOGGED), ("glass", GLASSED)):
        (tmp_path / f"{name}.usda").write_text(text)
    plain, fog, glass = (demo_film.forecast(tmp_path / f"{name}.usda", demo_film.SHOTS)
                         for name in ("plain", "fog", "glass"))
    assert plain["frames"] == 192 and plain["frame_minutes"] == demo.FRAME_MINUTES
    assert plain["high_frame_minutes"] == demo.FRAME_MINUTES * demo_film.FRAME_SPREAD
    assert plain["euros"] == demo_film.LIKELY_EUROS and plain["high_euros"] == demo_film.EUROS
    assert fog["slow"] == {"fog": 1, "volumes": 0, "glass": 0}, fog["slow"]
    assert glass["slow"] == {"fog": 0, "volumes": 0, "glass": 1}, glass["slow"]
    assert fog["high_frame_minutes"] == glass["high_frame_minutes"] == demo_film.FOG_FRAME_MINUTES
    assert fog["high_euros"] > 20 * fog["euros"] and fog["jobs"] == plain["jobs"] >= 1
    assert "1 fog" in demo_film.forecast_line(fog), demo_film.forecast_line(fog)


def test_the_forecast_counts_the_shots_film_one_makes_and_leaves_the_stage_alone(tmp_path):
    """#21: a record holding one camera is forecast at one shot (96 frames), two at two (192); a prim the film leaves
    out is out of the scan, and the stage's files are untouched.
    Break: score/stages/demo_film/__init__.py: `shots = len(film_cameras(record, film)[:SHOTS])` -> `shots = SHOTS`"""
    record = {"views": [{"name": "door", "eye": [0, 1.6, 0], "aim": [0, 1.6, -1]}]}
    (tmp_path / "scene.json").write_text(json.dumps(record))
    (tmp_path / "hall.usda").write_text(FOGGED)
    film = {"place": "hall", "camera": "door"}
    assert demo_film.film_forecast(tmp_path, film)["frames"] == 96
    record["views"].append({"name": "back", "eye": [5, 1.6, 5], "aim": [0, 1.6, 0]})
    (tmp_path / "scene.json").write_text(json.dumps(record))
    assert demo_film.film_forecast(tmp_path, film)["frames"] == 192
    assert demo_film.film_forecast(tmp_path, film)["slow"]["fog"] == 1
    assert demo_film.film_forecast(tmp_path, dict(film, leave_out=["/hall/Effects"]))["slow"]["fog"] == 0
    assert json.loads((tmp_path / "scene.json").read_text()) == record
    assert (tmp_path / "hall.usda").read_text() == FOGGED


def test_a_film_whose_forecast_high_passes_its_clearance_is_blocked_before_its_frames_are_bought(tmp_path):
    """#21: a plain film's high is the row's estimate and passes; a fogged one's passes it and is a new ask; outside a
    cleared run nothing is compared.
    Break: score/stages/demo_film/__init__.py: `if cleared is not None and planned["high_euros"] > cleared + 1e-6:` ->
        `if False:`"""
    (tmp_path / "plain.usda").write_text(PLAIN)
    (tmp_path / "fog.usda").write_text(FOGGED)
    plain, fog = (demo_film.forecast(tmp_path / f"{name}.usda", demo_film.SHOTS) for name in ("plain", "fog"))
    demo_film.refuse_over_clearance("hall", plain, demo_film.EUROS)
    demo_film.refuse_over_clearance("hall", fog, None)
    with pytest.raises(graph.Blocked, match="a new ask"):
        demo_film.refuse_over_clearance("hall", fog, demo_film.EUROS)


def test_the_clearance_reserves_the_forecast_the_make_checks_against(tmp_path):
    """Fault 2026-10-25: the clearance reserved the row's EUR 3.50 while the make held the film to its own forecast,
    so a fogged film Blocked itself after it was cleared. The rows clear at their films' forecast high, the figure
    film_one refuses over, and that figure holds the film.
    Break: score/stages/demo_film/__init__.py: `round(sum(film["high_euros"] for film in planned), 2)` ->
        `round(sum(film["euros"] for film in planned), 2)`"""
    from score import stages
    (tmp_path / "stage").mkdir()
    (tmp_path / "stage/hall.usda").write_text(FOGGED)
    (tmp_path / "stage/scene.json").write_text(json.dumps({"views": [
        {"name": "door", "eye": [0, 1.6, 0], "aim": [0, 1.6, -1]},
        {"name": "back", "eye": [5, 1.6, 5], "aim": [0, 1.6, 0]}]}))
    script = {"segments": [{"cut": "walk-through", "seconds": 7, "shows": {"place": "hall"}},
                           {"cut": "walk-through", "seconds": 7, "shows": {"place": "hall", "film": "porch",
                                                                           "camera": "back"}}]}
    (tmp_path / "script.json").write_text(json.dumps(script))
    inputs = {"assembly": str(tmp_path / "stage"), "script tour": str(tmp_path / "script.json")}
    own = stages.DEMO_FILM.forecast(inputs)
    planned = demo_film.film_forecast(tmp_path / "stage", {"place": "hall"})
    assert own == {"euros": planned["high_euros"], "minutes": None, "high_minutes": None, "measured": 0}, own
    demo_film.refuse_over_clearance("hall", planned, own["euros"])
    extra = stages.DEMO_FILM_EXTRA.forecast(inputs)
    assert extra["euros"] == demo_film.film_forecast(tmp_path / "stage", {"place": "hall", "camera": "back"})[
        "high_euros"] > demo_film.EUROS, extra


def test_a_film_too_short_for_the_walk_through_that_shows_it_fails_before_its_frames_are_bought():
    """Fault 2026-10-25: a one-shot film (3.5 s) passed its own gate and Blocked the environment film's 7 s
    walk-through after everything was bought. A film's record keeps the longest walk-through showing it, and a plan
    whose shots show less is refused; a film shown only as a hero still keeps one shot.
    Break: score/stages/demo_film/__init__.py: `film["walk_seconds"] = max(film["walk_seconds"],
        float(segment.get("seconds") or 0.0))` -> `pass`
    Break: score/stages/demo_film/__init__.py: `if shown < film.get("walk_seconds", 0.0) - 1e-3:` -> `if False:`"""
    script = {"segments": [{"cut": "walk-through", "seconds": 7, "shows": {"place": "hall"}},
                           {"cut": "hero-still", "seconds": 3, "shows": {"place": "hall", "film": "porch"}}]}
    films = demo_film.films_of({"tour": script})
    assert films["hall"]["walk_seconds"] == 7.0 and films["porch"]["walk_seconds"] == 0.0, films
    two, one = [{"camera": "a"}, {"camera": "b"}], [{"camera": "a"}]
    demo_film.refuse_short("hall", two, films["hall"])
    demo_film.refuse_short("porch", one, films["porch"])
    with pytest.raises(RuntimeError, match="wants 7 s") as refused:
        demo_film.refuse_short("hall", one, films["hall"])
    assert "3.50 s" in str(refused.value)


def test_the_frames_ask_cards_only_so_no_card_in_stock_is_a_gap():
    """#21: the frames' classes are cards only (blender_cloud never takes a processor machine in a card's place), so a
    film priced on cards runs on cards or is a gap. A wording check guarding that owner rule.
    Break: score/stages/demo_film/__init__.py: `CLASSES = "gpu-24gb"` -> `CLASSES = "gpu-24gb,cpu-8c-32gb"`"""
    sys.path.insert(0, str(REPO / "tools/cloud"))
    import provider
    assert all(provider.cards(name) for name in demo_film.CLASSES.split(","))


def test_a_film_is_one_batch_dealt_over_the_forecast_s_cards_with_its_high_deadline(tmp_path, monkeypatch):
    """#21: the frames are planned at SIZE over the jobs the forecast sizes, no review frames, each job's deadline its
    frames at the forecast's high: the fogged hall's 2 frames a job at 17 minutes plus 10 to set up, 44; its first
    frame kept as concept.png.
    Break: score/stages/demo_film/__init__.py: `job["minutes"] = round(JOB_LEAD_MINUTES + frame_minutes * len(views))`
        -> `job["minutes"] = JOB_LEAD_MINUTES`"""
    demo, _ = demo_film.film_tools()
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
        assert all(view["look_only"] for job in asked for view in job["views"])
        frames = log_folder / ".work/frames/hall"
        frames.mkdir(parents=True)
        Image.new("RGB", tuple(asked[0]["size"]), (90, 90, 90)).save(frames / "shot0-000-look.png")

    def cut(work, names):
        (work / "videos").mkdir()
        (work / "videos/hall.mp4").write_bytes(b"")

    monkeypatch.setattr(demo, "plan", plan)
    monkeypatch.setattr(demo, "cut", cut)
    monkeypatch.setattr(demo_film, "render", render)
    (tmp_path / "stage").mkdir()
    (tmp_path / "stage/hall.usda").write_text(FOGGED)
    (tmp_path / "stage/scene.json").write_text(json.dumps({"views": [{"name": "door", "eye": [0, 1.6, 0],
                                                                      "aim": [0, 1.6, -1]}]}))
    demo_film.film_one(tmp_path / "stage", "hall", {"place": "hall", "camera": "door", "final": True},
                       tmp_path / "out", tmp_path / "log")
    assert planned == [(demo_film.SIZE, demo_film.forecast(tmp_path / "stage/hall.usda", 1)["jobs"])], planned
    assert deadlines == [44, 44], deadlines
    assert Image.open(tmp_path / "out/concept.png").size == demo_film.SIZE


# --- the film gate --------------------------------------------------------------------------------------------------

def look_only_film(root):
    """A planned look-only film of SHOTS shots whose frames are all one colour, cut by demo.py at SMALL: its video."""
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


@pytest.fixture(scope="module")
def still_film(tmp_path_factory):
    return look_only_film(tmp_path_factory.mktemp("cut"))


def test_a_look_only_plan_is_held_to_its_planned_length_and_size(still_film, tmp_path, monkeypatch):
    """A two-shot film is a 2 s title and two 4 s shots joined by half-second fades: 9 s, within LENGTH_SLACK; the gate
    holds a film to the size its views planned (SMALL here), never the row's default.
    Break: score/stages/demo_film/__init__.py: `return demo.TITLE_SECONDS + shots * (SECONDS - demo.FADE_SECONDS)` ->
        `return shots * SECONDS`
    Break: score/stages/demo_film/__init__.py: `size = tuple(planned.get("size", SIZE))` -> `size = SIZE`"""
    _, film_checks = demo_film.film_tools()
    assert demo_film.planned_seconds(2) == 9.0
    (tmp_path / "out").mkdir()
    shutil.copy(still_film, tmp_path / "out/film.mp4")
    (tmp_path / "out/views.json").write_text(json.dumps({"size": list(SMALL), "views": [], "moves": [{}, {}]}))
    (tmp_path / "stage").mkdir()
    (tmp_path / "stage/hall.usda").write_text("#usda 1.0\n")
    monkeypatch.setattr(film_checks, "clearance_checks", lambda stage, views: ({}, []))
    seconds, _, size, faults = demo_film.film_measures(tmp_path / "out", tmp_path / "stage")
    assert size == SMALL and not any("size" in fault for fault in faults), faults
    assert abs(seconds - 9.0) <= demo_film.LENGTH_SLACK, seconds


def test_the_gate_fails_a_silent_still_film_by_name(still_film, tmp_path, monkeypatch):
    """A film of one still colour with no sound fails `film`, naming both.
    Break: score/stages/demo_film/__init__.py: `faults = [fault for _, _, _, found in measured.values() for fault in
        found]` -> `faults = []`"""
    _, film_checks = demo_film.film_tools()
    out = tmp_path / "out"
    out.mkdir()
    shutil.copy(still_film, out / "film.mp4")
    (out / "views.json").write_text(json.dumps({"views": []}))
    (tmp_path / "stage").mkdir()
    (tmp_path / "stage/hall.usda").write_text("#usda 1.0\n")
    monkeypatch.setattr(film_checks, "clearance_checks", lambda stage, views: ({}, []))
    monkeypatch.setattr(demo_film, "SIZE", SMALL)
    verdict = demo_film.judge_film(out, {"assembly": tmp_path / "stage"}, {})
    found = " ".join(verdict.findings)
    assert verdict.answer == checks.FAIL and "no sound track" in found and "frozen" in found, found


LOOKING_NORTH = {"eye": [0.0, 1.6, 0.0], "aim": [0.0, 1.6, -10.0], "fov": 75.0}


def views(aim_z=-10.0, frames=range(4)):
    """A standing shot looking along z, one view a frame."""
    return [{"name": f"shot0-{frame:03d}", "eye": [0.0, 1.6, 0.0], "aim": [0.0, 1.6, aim_z], "fov": 75.0,
             "frame": frame} for frame in frames]


def a_stage(folder, person_at=None, door_sound=False):
    """A place with a person standing at `person_at` and a door sliding 0.5 m a frame along x at z = -5."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"hall-{person_at}-{door_sound}.usda"
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    root = UsdGeom.Xform.Define(stage, "/hall")
    stage.SetDefaultPrim(root.GetPrim())
    for group in ("Characters", "Objects"):
        UsdGeom.Xform.Define(stage, f"/hall/{group}")
    if person_at is not None:
        person = UsdSkel.Root.Define(stage, "/hall/Characters/walker")
        person.AddTranslateOp().Set(Gf.Vec3d(*person_at))
        person.CreateExtentAttr().Set(Vt.Vec3fArray([(-0.5, -0.5, -0.5), (0.5, 0.5, 0.5)]))  # no skeleton: bound given
    door = UsdGeom.Xform.Define(stage, "/hall/Objects/door")
    slide = door.AddTranslateOp()
    for frame in range(4):
        slide.Set(Gf.Vec3d(0.5 * frame, 1.0, -5.0), frame)
    UsdGeom.Cube.Define(stage, "/hall/Objects/door/leaf").CreateSizeAttr(1.0)
    if door_sound:
        UsdMedia.SpatialAudio.Define(stage, "/hall/Objects/door/Sound_0")
    stage.GetRootLayer().Save()
    return path


def test_a_view_sees_what_stands_in_front_within_its_angle_and_reach():
    """Looking north from the origin at 75 degrees: 5 m ahead is seen, 5 m behind is not, 9 m aside at 5 m ahead is
    outside the angle, 40 m ahead is past the 25 m reach, a point 3 m ahead and a little low is seen.
    Break: score/stages/demo_film/shots.py: `(np.linalg.norm(offsets, axis=1) <= reach)` -> `(np.linalg.norm(offsets,
        axis=1) <= 100 * reach)`"""
    seen = shots.in_view(LOOKING_NORTH, [[0, 1.6, -5], [0, 1.6, 5], [9, 1.6, -5], [0, 1.6, -40], [0, 1.0, -3]])
    assert seen.tolist() == [True, False, False, False, True]


def test_a_place_with_people_fails_where_no_frame_shows_one(tmp_path):
    """The owner's review of 2026-10-18: no people in any film. Nobody there is no fault; someone 6 m ahead is seen in
    all four frames; someone behind the camera in none.
    Break: score/stages/demo_film/shots.py: `int(bool(len(middles)) and bool(in_view(view, middles).any()))` -> `1`"""
    assert shots.people_seen(a_stage(tmp_path), views()) is None
    assert shots.people_seen(a_stage(tmp_path, person_at=(0, 0.5, -6)), views()) == {"shot0": 4}
    assert shots.people_seen(a_stage(tmp_path, person_at=(0, 0.5, 6)), views()) == {"shot0": 0}


def test_a_design_that_stands_people_fails_a_stage_that_holds_none(tmp_path):
    """The motion layer's bodies (#26): the design stands 2 people and the film's stage got none: it fails; a design
    standing nobody does not.
    Break: score/stages/demo_film/__init__.py: `elif seen is None and people:` -> `elif False:`"""
    film = views(frames=range(round(demo_film.SECONDS * 24)))
    stage = a_stage(tmp_path, door_sound=True)
    assert "the place's design stands 2 people and the film's stage holds none" in \
        demo_film.seen_faults(stage, film, people=2)
    assert not any("design stands" in fault for fault in demo_film.seen_faults(stage, film, people=0))


def test_a_design_s_people_and_crowd_count_its_people(tmp_path):
    """The square stands one speaker and a far crowd of 10000: 10001 people; a crowd SAM 3 could not part counts one
    at least (2); a place with no rows, or no rows read, none.
    Break: score/stages/demo_film/__init__.py: `((people_rows.crowd_count(crowd[1]) or 1) if crowd else 0)` -> `(1 if
        crowd else 0)`"""
    rows = tmp_path / "rows.json"
    square = {"rows": {"leader": {"looks": ["leader-drawn"]}, "crowd": {"crowd": "far-coat", "count": 10000}}}
    rows.write_text(json.dumps({"places": {"square": square}}))
    assert demo_film.cast_people("square", rows) == 10001
    square["rows"]["crowd"]["count"] = None
    rows.write_text(json.dumps({"places": {"square": square}}))
    assert demo_film.cast_people("square", rows) == 2
    assert demo_film.cast_people("hub", rows) == 0
    assert demo_film.cast_people("square", None) == 0


def test_a_thing_seen_moving_needs_a_sound_of_its_own(tmp_path):
    """The owner's review of 2026-10-18: no event sounds. The door seen sliding with no sound under it is named; with
    its sound, looked away from, or seen in one frame only (nothing seen moving) it is not.
    Break: score/stages/demo_film/shots.py: `quiet = [not sounded(prim) for prim in things]` -> `quiet = [True for prim
        in things]`
    Break: score/stages/demo_film/shots.py: `moving & in_view(view, now) & np.asarray(quiet)` -> `moving &
        np.asarray(quiet)`"""
    assert shots.silent_moving(a_stage(tmp_path), views()) == {"shot0": ["/hall/Objects/door"]}
    assert shots.silent_moving(a_stage(tmp_path, door_sound=True), views()) == {}
    assert shots.silent_moving(a_stage(tmp_path), views(aim_z=10.0)) == {}
    assert shots.silent_moving(a_stage(tmp_path), views(frames=[0])) == {}


# --- the environment's own film (final.py) --------------------------------------------------------------------------

def a_script(segments):
    return {"format": "score-film-script", "version": 1, "film": "toy", "size": [1280, 720], "rate": 24,
            "segments": segments}


WALKS = [{"cut": "title", "shows": {"world": "toy"}, "sound": "bed", "text": "Toy", "seconds": 2.0},
         {"cut": "walk-through", "shows": {"place": "alpha"}, "sound": "place", "text": "Alpha", "seconds": 7.0},
         {"cut": "walk-through", "shows": {"place": "beta"}, "sound": "place", "text": "Beta", "seconds": 7.0}]


def locked_in(home, monkeypatch, *films):
    """The cockpit's home `home` holding `films` ({film: script}) locked, as the Film step's Lock keeps them."""
    folder = home / final.LOCKED
    folder.mkdir(parents=True, exist_ok=True)
    for path in folder.glob("*.json"):
        path.unlink()
    for film, script in films:
        (folder / f"{film}.json").write_text(json.dumps(script))
    monkeypatch.setattr(final, "DASHBOARD", home)


def test_nothing_is_cut_before_the_creator_s_yes_and_a_sound_plan():
    """No locked script: Blocked. A script is cut only when every segment names its seconds, is a cut a row makes, and
    a walk-through plays its place's own sound; a script showing no film needs a bed.
    Break: score/stages/demo_film/final.py: `if not named:` -> `if False:`
    Break: score/stages/demo_film/final.py: `elif cut == WALK and segment.get("sound", "place") != "place":` -> `elif
        False:`"""
    with pytest.raises(graph.Blocked, match="no film script locked"):
        final.require_yes({})
    final.require_yes({"toy": a_script(WALKS)})
    assert final.plan_faults(a_script(WALKS)) == []
    unsound = a_script([{"cut": "exploded", "shows": {"place": "alpha"}},
                        {"cut": "walk-through", "shows": {"place": "alpha"}, "sound": "bed", "seconds": 7.0}])
    assert final.plan_faults(unsound) == ["segment 1 (exploded) names no seconds",
                                          "segment 1: no row makes exploded frames yet",
                                          "segment 2: a walk-through plays its place's own sound, not bed"]
    assert final.plan_faults(a_script(WALKS[:1])) == ["it shows no place's film and names no bed"]
    assert final.plan_faults(dict(a_script(WALKS[:1]), bed="sound/hum")) == []


def test_the_owner_s_pacing_fails_a_place_cut_at_three_and_a_half_seconds():
    """The owner's review of 2026-10-18: about 3.5 s a place, far too fast; about 7 s, two steady shots. Two 3.5 s
    walk-throughs of one place add to its 7 s.
    Break: score/stages/demo_film/final.py: `for place, seconds in shown_for.items() if seconds < PLACE_SECONDS - 1e-6]`
        -> `for place, seconds in shown_for.items() if False]`
    Break: score/stages/demo_film/final.py: `for segment in walks if segment["seconds"] < SHOT_SECONDS]` -> `for segment
        in walks if False]`"""
    assert final.pacing_faults(final.script_segments(a_script(WALKS))) == []
    fast = [dict(WALKS[1], seconds=3.5), dict(WALKS[2], seconds=3.0)]
    assert final.pacing_faults(final.script_segments(a_script(fast))) == [
        "beta: a walk-through of 3 s, under 3.5 s", "alpha: on screen 3.5 s, under 7 s",
        "beta: on screen 3 s, under 7 s"]
    two_shots = [dict(WALKS[1], seconds=3.5), dict(WALKS[1], seconds=3.5)]
    assert final.pacing_faults(final.script_segments(a_script(two_shots))) == []


def test_world1_s_script_is_paced_and_names_the_cuts_no_row_makes_yet(tmp_path, monkeypatch):
    """data/films/k9.json, the house's script: paced, and every plan fault a cut no row makes yet; locked, the places
    it shows are its walk-throughs' and stills' (read off the script here), and a segment naming a film is the extra
    row's.
    Break: score/stages/demo_film/final.py: `return f"{EXTRA}@{shows['place']}", shows["film"]` -> `return
        f"{OWN}@{shows['place']}", shows["film"]`"""
    k9 = json.loads((REPO / "data/films/k9.json").read_text())
    assert final.pacing_faults(final.script_segments(k9)) == []
    faults = final.plan_faults(k9)
    assert faults and all("no row makes" in fault for fault in faults), faults
    locked_in(tmp_path, monkeypatch, ("k9", k9))
    shown = sorted({segment["shows"]["place"] for segment in k9["segments"]
                    if segment["cut"] in ("walk-through", "hero-still") and (segment.get("shows") or {}).get("place")})
    assert final.shown_places() == shown and shown
    assert final.film_node({"shows": {"place": "hangar", "film": "hull"}}) == ("demo-film-extra@hangar", "hull")


def test_the_locked_script_is_the_row_s_input_and_a_new_lock_moves_its_key(tmp_path, monkeypatch):
    """The Film step's seam: the environment-film row reads only the locked scripts in the cockpit's home, so a lock,
    a changed lock and an unlock each move the files part of its key.
    Break: score/stages/demo_film/final.py: `found[f"script {film}"] = "{dashboard}/" + f"{LOCKED}/{film}.json"` ->
        `pass`"""
    from score import stages
    from score.store import Store
    world = graph.Environment("world1", 0, {**stages.world1().roots, "dashboard": str(tmp_path)})
    runner = graph.Runner(stages.STAGES, world, Store.in_folder(tmp_path / "store"))
    row = runner.stages["environment-film"]
    locked_in(tmp_path, monkeypatch)
    assert not any(name.startswith("script ") for name in runner.file_keys(row, None))
    locked_in(tmp_path, monkeypatch, ("toy", a_script(WALKS)))
    first = runner.file_keys(row, None)["script toy"]
    assert final.shown_places() == ["alpha", "beta"]
    locked_in(tmp_path, monkeypatch, ("toy", a_script(WALKS[:2])))
    assert runner.file_keys(row, None)["script toy"] != first
    assert final.shown_places() == ["alpha"]


def test_a_film_a_script_shows_waits_on_its_lock(tmp_path, monkeypatch):
    """The film layer's gaps (needs.py): a film a starter shows that no locked script shows waits on his lock, its
    node named; a locked one is no gap, and the lock is the yes.
    Break: score/stages/demo_film/needs.py: `for film in wanted(place, data) if film not in locked]` -> `for film in
        wanted(place, data)]`"""
    (tmp_path / "films").mkdir()
    walk = {"cut": "walk-through", "seconds": 4.0}
    script = {"segments": [dict(walk, shows={"place": "alpha"}), dict(walk, shows={"place": "beta"})]}
    (tmp_path / "films/env.json").write_text(json.dumps(script))
    monkeypatch.setattr(final, "scripts", lambda: {"env": {"segments": [dict(walk, shows={"place": "beta"})]}})
    found = [(gap["id"], gap["node"]) for gap in needs.gaps("alpha", tmp_path)]
    assert found == [("film:yes:alpha", "demo-film@alpha")], found
    assert needs.gaps("beta", tmp_path) == [] and needs.gaps("gamma", tmp_path) == []
    assert demo_film.films()["beta"]["final"] is True


def a_film(folder, tone, volume):
    """A place film as demo-film keeps one: 9 s at 1280x720, its sound a tone at `volume`."""
    folder.mkdir(parents=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "testsrc2=size=1280x720:rate=24:duration=9", "-f", "lavfi", "-i",
                    f"sine=frequency={tone}:duration=9,volume={volume}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-shortest", str(folder / "film.mp4")], check=True)
    return folder


def test_a_cut_runs_at_one_loudness_and_its_gate_holds_the_pacing(tmp_path, monkeypatch):
    """Two place films at very different loudness cut into one 15 s film (2 + 7 + 7 less two half-second
    transitions), each segment from its own film; the whole at TARGET_LUFS passes; a place cut at 3.5 s fails.
    Break: score/stages/demo_film/final.py: `gain = TARGET_LUFS - loudness` -> `gain = 0.0`"""
    from score.stages import design_layers
    monkeypatch.setattr(design_layers, "KEPT", tmp_path / "designs")  # no kept design shows people: no peel owed
    script = tmp_path / "toy.json"
    script.write_text(json.dumps(a_script(WALKS)))
    inputs = {"script toy": script, "demo-film@alpha": a_film(tmp_path / "alpha", 330, 0.05),
              "demo-film@beta": a_film(tmp_path / "beta", 440, 0.6)}
    out = tmp_path / "out"
    out.mkdir()
    final.make(inputs, out, 0, {})
    assert final.output_faults(out) == []
    timeline = json.loads((out / "toy" / "timeline.json").read_text())
    assert [segment["film"] for segment in timeline["segments"]] == [None, "demo-film@alpha", "demo-film@beta"]
    assert timeline["seconds"] == 15.0
    verdict = final.judge(out, inputs, {})
    assert verdict.answer == checks.PASS, verdict
    timeline["segments"][1]["seconds"] = 3.5  # the 18 Oct cut's pace, written into the record
    (out / "toy" / "timeline.json").write_text(json.dumps(timeline))
    verdict = final.judge(out, inputs, {})
    assert verdict.answer == checks.FAIL and "toy: alpha: on screen 3.5 s, under 7 s" in verdict.findings, verdict


def test_a_recorded_segment_is_cut_from_the_preview_s_take_of_that_very_segment(tmp_path):
    """A screen take is the free preview's take only while the preview was recorded from the segment the lock holds
    (a take recorded at 3 s for a segment now 4 s is Blocked); films are matched in exposure (a film at the middle
    keeps gain 1, a dark one is brought up at most GAIN_RANGE's top); the cut is 2 + 3 + 7 + 3 less three half-second
    transitions, 13.5 s.
    Break: score/stages/demo_film/final.py: `    if stale:` -> `    if False:`
    Break: score/stages/demo_film/final.py: `return round(min(GAIN_RANGE[1], max(GAIN_RANGE[0], (middle - 16.0) /
        max(luma - 16.0, 1.0))), 3)` -> `return 1.0`"""
    take = {"cut": "screen-take", "shows": {"page": "/"}, "sound": "bed", "seconds": 3.0}
    script = a_script([WALKS[0], take, WALKS[1]])
    (tmp_path / "toy.json").write_text(json.dumps({"script": script}))
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "testsrc2=size=1280x720:rate=24:duration=3", "-pix_fmt", "yuv420p", str(tmp_path / "002.mp4")],
                   check=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "sine=frequency=220:duration=5", str(tmp_path / "bed.wav")], check=True)
    inputs = {"preview toy": tmp_path / "toy.json", "take toy 2": tmp_path / "002.mp4"}
    assert final.takes("toy", script, inputs) == {2: tmp_path / "002.mp4"}
    assert set(final.recorded_files("toy", script)) == {"preview toy", "take toy 2"}
    moved = dict(script, segments=[WALKS[0], dict(take, seconds=4.0), WALKS[1]])
    with pytest.raises(graph.Blocked, match="segment\\(s\\) 2 of the free preview"):
        final.takes("toy", moved, inputs)
    assert final.matched_gain(116.0, 116.0) == 1.0 and final.matched_gain(40.0, 200.0) == final.GAIN_RANGE[1]
    alpha = a_film(tmp_path / "alpha", 330, 0.2) / "film.mp4"
    still = {"cut": "hero-still", "shows": {"place": "alpha"}, "sound": "bed", "text": "Alpha", "seconds": 3.0}
    out = tmp_path / "out"
    final.cut_one(dict(script, segments=[*script["segments"], still]), {3: alpha, 4: alpha}, out,
                  {2: tmp_path / "002.mp4"}, tmp_path / "bed.wav")
    timeline = json.loads((out / "timeline.json").read_text())
    assert [segment["cut"] for segment in timeline["segments"]] == ["title", "screen-take", "walk-through",
                                                                    "hero-still"]
    assert timeline["segments"][2]["exposure_gain"] == 1.0 and timeline["seconds"] == 13.5


def test_a_locked_script_with_recorded_segments_wants_its_preview_until_it_is_made_from_the_lock(tmp_path,
                                                                                                    monkeypatch):
    """A lock with a recorded segment and no preview wants it; a preview of the very lock, or a script with no
    recorded segment, does not; a preview recorded from another script (the take now 4 s) wants it again.
    Break: score/stages/demo_film/final.py: `if recorded(script) and (made is None or stale_segments(script, made)):` ->
        `if recorded(script) and made is None:`"""
    take = {"cut": "screen-take", "shows": {"page": "/"}, "sound": "bed", "seconds": 3.0}
    script = a_script([WALKS[0], take, WALKS[1]])
    locked_in(tmp_path, monkeypatch, ("toy", script), ("plain", a_script(WALKS)))
    assert final.previews_wanted() == ["toy"]
    (tmp_path / final.PREVIEWS).mkdir(parents=True)
    (tmp_path / final.PREVIEWS / "toy.json").write_text(json.dumps({"script": script}))
    assert final.previews_wanted() == []
    locked_in(tmp_path, monkeypatch, ("toy", dict(script, segments=[WALKS[0], dict(take, seconds=4.0), WALKS[1]])))
    assert final.previews_wanted() == ["toy"]


def toy_rig():
    """Two joints (a root at the floor, a hip 1 m over it) and three points: one on each joint, one shared half and
    half; a clip `still` at the bind and `step` with the root moved 1 m along z."""
    import numpy as np
    bind = np.tile(np.eye(4), (2, 1, 1))
    bind[1, 1, 3] = 1.0
    local = np.tile(np.eye(4), (1, 2, 1, 1))
    local[0, 1, 1, 3] = 1.0
    step = local.copy()
    step[0, 0, 2, 3] = 1.0
    return {"names": np.array(["Root", "Hips"]), "parents": np.array([-1, 0]), "bind": bind,
            "points": np.array([[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.5, 0.0]]),
            "weights": np.array([[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]]), "clip_still": local, "clip_step": step}


def test_a_peel_draws_the_clip_rigs_own_surface_and_the_records_own_push():
    """The bare mesh is the rig's points carried by its clip and skin weights (at the bind, the points themselves);
    each foot's arrow stands on the ground under it (its bottom less its recorded height over the ground), its
    length the record's push on that foot, so the same body's arrow on the Moon is a sixth of Earth's; a foot the
    ground does not push has none.
    Break: score/stages/demo_film/peel.py: `@ np.linalg.inv(np.asarray(rig["bind"], dtype=float))` -> `` (in skinned)
    Break: score/stages/demo_film/peel.py: `bottom[1] - height` -> `bottom[1]`"""
    import numpy as np
    from score.stages.demo_film import peel
    rig = toy_rig()
    assert np.allclose(peel.skinned(rig, "still")[0], rig["points"])
    assert np.allclose(peel.skinned(rig, "step")[0], rig["points"] + [0.0, 0.0, 1.0])
    bottoms = np.array([[[0.0, 0.30, 0.0], [0.2, 0.40, 0.0]]])  # 0.25 over a 0.05 step; the other foot up
    frame = {"feet": {"LeftFoot": [0.25, 750.0], "RightFoot": [0.4, 0.0]}}
    earth = peel.pushes(bottoms, [frame])
    moon = peel.pushes(bottoms, [{"feet": {"LeftFoot": [0.25, 125.0], "RightFoot": [None, 0.0]}}])
    assert np.allclose(earth[0, 0], [0.0, 0.05, 0.0, 0.0, 0.75, 0.0]) and np.isnan(earth[0, 1]).all()
    assert np.isclose(moon[0, 0, 4] * 6, earth[0, 0, 4]) and np.isnan(moon[0, 1]).all()


def sim_layer(path):
    """A sim body layer as score/stages/sim_body writes one: a guide SimBody whose segments are time-sampled Xforms,
    each with geometry of its own under it (here a cube a segment), the hips 1 m over the foot, both 0.5 m on at 1."""
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    body = UsdGeom.Xform.Define(stage, "/toy/Characters/ann/SimBody")
    UsdGeom.Imageable(body).CreatePurposeAttr(UsdGeom.Tokens.guide)
    for name, height in (("Hips", 1.0), ("LeftFoot", 0.05)):
        segment = UsdGeom.Xform.Define(stage, f"/toy/Characters/ann/SimBody/{name}")
        moved = segment.AddTranslateOp()
        for time, forward in ((0, 0.0), (1, 0.5)):
            moved.Set(Gf.Vec3d(0.0, height, forward), time)
        UsdGeom.Cube.Define(stage, f"/toy/Characters/ann/SimBody/{name}/bone").CreateSizeAttr(0.1)
    stage.GetRootLayer().Save()
    return path


def test_a_sim_body_is_read_upright_from_its_layers_time_samples_and_moves_with_them(tmp_path):
    """The sim pass draws the layer's own geometry under the person's SimBody (any geometry, a guide included) at its
    own time samples, and the feet's arrows stand under that geometry: at the first sample the hips stand over the
    foot, a sample later both have moved, never one frozen pose (owner, 2026-10-27); every pushed foot keeps its arrow.
    Break: score/stages/demo_film/peel.py: `cache = UsdGeom.BBoxCache(Usd.TimeCode(time), purposes)` ->
        `cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), purposes)`
    Break: score/stages/demo_film/peel.py: `points_to_z(starts[shown])` -> `points_to_z(starts[shown, :1])`"""
    import numpy as np
    from score.stages.demo_film import peel
    layer = sim_layer(tmp_path / "sim_bodies.usda")
    found = peel.foot_bottoms(layer, peel.sim_root("toy", "ann"), ["Hips", "LeftFoot"], [0, 1])
    assert found[0, 0, 1] - found[0, 1, 1] > 0.9  # upright: the hips over the foot (Y up)
    assert np.allclose(found[1] - found[0], [[0.0, 0.0, 0.5], [0.0, 0.0, 0.5]])
    with pytest.raises(ValueError, match="no prim of RightFoot"):
        peel.foot_bottoms(layer, peel.sim_root("toy", "ann"), ["RightFoot"], [0])
    rig = toy_rig()
    rig["clip_walking"] = np.concatenate([rig["clip_still"], rig["clip_step"]])
    frames = [{"feet": {"Hips": [None, 0.0], "LeftFoot": [0.0, 400.0]}}] * 2
    drawn = peel.person_arrays({"at": [2.0, 0.0, 1.0], "turn": 30.0, "clip": "walking"}, rig, frames, found, [0, 1])
    assert drawn["arrow_start"].shape == (2, 2, 3) and not np.isnan(drawn["arrow_start"][:, 1]).any()


def test_a_peel_never_outlasts_its_record_and_wipes_up_at_each_third():
    """A shot is the record's own frames, refused when longer; it shows clothed, mesh and sim body in thirds, each
    next one rising from the bottom over the wipe; the environment's film names it as a cut no row makes yet.
    Break: score/stages/demo_film/peel.py: `if found[-1] >= record_frames:` -> `if False:`
    Break: score/stages/demo_film/peel.py: `edge = round(tall * (1 - share))` -> `edge = round(tall * share)`"""
    from score.stages.demo_film import peel
    assert peel.source_frames(5.0, 30.0, 150)[-1] == 149
    with pytest.raises(ValueError, match="outlasts"):
        peel.source_frames(5.5, 30.0, 150)
    count = 120
    assert peel.stage_of(0, count) == (0, 0, 0.0) and peel.stage_of(60, count) == (1, 1, 0.0)
    assert peel.stage_of(119, count) == (2, 2, 0.0)
    shown, coming, share = peel.stage_of(40, count)
    assert (shown, coming) == (0, 1) and 0.4 < share < 0.6
    pictures = [Image.new("RGB", SMALL, colour) for colour in ((255, 0, 0), (0, 255, 0), (0, 0, 255))]
    frame = peel.wiped(pictures, 36, count)  # a fifth of the way up: the mesh below, the clothed above
    assert frame.getpixel((5, SMALL[1] - 2)) == (0, 255, 0) and frame.getpixel((5, SMALL[1] // 2)) == (255, 0, 0)
    peeled = a_script([{"cut": "body-peel", "shows": {"place": "alpha"}, "seconds": 5.0}])
    assert "segment 1: no row makes body-peel frames yet" in final.plan_faults(peeled)


def test_a_close_up_follows_the_walker_on_the_most_uneven_ground():
    """The close-up's walker by rule, never by hand: the cast's walker whose scene-made clip crosses the most relief,
    the first on a tie; one walker needs no record, several do, none is refused.
    Break: score/stages/demo_film/peel.py: `relief.get(name, -1.0)` -> `-relief.get(name, -1.0)`"""
    from score.stages.demo_film import peel
    walker = {"doing": "walking"}
    cast = {"place": "street", "characters": [dict(walker, name="ann"), {"name": "bo", "doing": "standing"},
                                              dict(walker, name="cy"), dict(walker, name="di")]}
    clips = {"clips": [{"name": "ann", "relief": 0.02}, {"name": "cy", "relief": 0.31}, {"name": "di", "relief": 0.31}]}
    assert peel.close_walker(cast, clips) == "cy"
    assert peel.close_walker(dict(cast, characters=cast["characters"][:2])) == "ann"
    with pytest.raises(ValueError, match="no scene-made clips"):
        peel.close_walker(cast)
    with pytest.raises(ValueError, match="no walker"):
        peel.close_walker(dict(cast, characters=[cast["characters"][1]]))


def test_a_locked_script_peels_every_place_whose_design_shows_people(tmp_path, monkeypatch):
    """A script must show a layer peel of every place whose design shows people (the designs' own layers), else the
    environment film is Blocked naming each, so the script cannot drift from the designs (owner, 2026-10-27); every
    kept design is the row's input, so a design that gains people moves its key.
    Break: score/stages/demo_film/final.py: `if place not in peeled]` -> `if False]`
    Break: score/stages/demo_film/final.py: `if design_layers.has_layer(place, "people")]` -> `]`"""
    from score.stages import design_layers
    monkeypatch.setattr(design_layers, "KEPT", tmp_path)
    for place in ("lab", "stairwell", "hangar"):
        (tmp_path / f"{place}.json").write_text("{}")
    monkeypatch.setattr(design_layers, "has_layer", lambda place, kind: kind == "people" and place != "hangar")
    assert final.peopled() == ["lab", "stairwell"]
    assert {"design lab", "design stairwell", "design hangar"} <= set(final.files())
    peel = {"cut": "body-peel", "shows": {"place": "lab"}, "seconds": 5.0}
    faults = final.plan_faults(dict(a_script([*WALKS, peel])), final.peopled())
    assert "the design of stairwell shows people and no layer peel shows them" in faults
    assert not any("design of lab" in fault for fault in faults)
