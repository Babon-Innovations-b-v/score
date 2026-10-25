"""demo-film and demo-film-extra: walk-through films for the paper's demo K9, from a place's final stage once it passes
complete, with its own sound; place nodes, paid (the frames on the cheapest card through
tools/cloud/blender_cloud.py inside the runner's clearance, drawn by tools/blender/inside/usd_views.py as
tools/review/demo.py plans them).

    a locked film script's walk-through or hero still   its `shows`: {"place", and optionally "film" (another film
                                               of the place than its own), "camera" (a camera of the place's scene
                                               record, else its first), "eye" and "aim" or "across" (a spot of its
                                               own for that camera, own_cameras), "then" (its second shot's camera:
                                               a record camera's name or a spot of its own), "start", "leave_out"}

The films are the creator's locked film scripts' (CONTEXT.md "film script"; final.scripts), never a record written
per place: the old per-place film records (data/definitions/demo_films) were the old concepts' and are retired
(owner, 2026-10-21: all old stuff is retired). A segment naming no `film` shows the place's own film, the demo-film
row; one naming a `film` (the ship's hull through the hangar: film hull, place hangar) is the demo-film-extra row's,
which makes all of them for that place. A place no locked script shows has no node.

A film is one batch (#21, the owner's batch of 2026-10-20): its frames are bought once, after the creator's yes, and
never again inside it. Before the yes everything is free: the creator looks at the free local preview
(tools/review/film_preview.py: the same plan, a few frames drawn on this PC) and the forecast (`python -m
score.stages.demo_film forecast <place>`: frames, cards, card minutes and euros, likely and high, from a scan of the
stage for fog, volumes and glass); his lock of the script is the yes (`final`). A film without it keeps
its node (the basket takes it), but its row is Blocked before anything is bought (require_yes); a film whose
forecast's high passes the euros its run was cleared at is Blocked the same way (refuse_over_clearance), so a dearer
film is a new ask at the forecast's price. A frame job that dies or passes its deadline is a gap: its film fails
the gate, and a new film is a new batch and a new yes.

    make   the final stage (the neighbours output where the place shows others, else its assembly), copied into a tree
           of its own; demo.py's plan with a camera path a shot, SHOTS shots: the first starting at the film's camera
           and the second at its `then`, else at the record camera standing furthest from the first (its first frame that
           camera's view, unless the planner had to move its start clear or level it: views.json's moves say),
           frames over SECONDS at demo.RATE, look only (no ink), each with the camera's motion blur
           (motion_blurred: the next frame's camera and a shutter set by how fast the picture moves, drawn by
           blender/film_frames.py); the frames rendered once at SIZE with the films' samples, dealt over the jobs
           `forecast` sizes (capacity.machines_for on the likely frame minutes), each
           job's deadline its frames at the forecast's high frame minutes; demo.py's cut with the stage's sound
           layer. Per film:
           film.mp4, views.json (each frame's view, the moves, the planner's commit) and concept.png, the first frame
           (for the place's own film, demo K8's still beside the concept), and bed.wav where the stage has sound (what
           the camera hears standing at its first view before it walks, demo.BED_SECONDS, which the showcase lays under
           the place's cards); the other frames are not kept. The own
           film's files lie in the output's root, each extra film's in a folder of its name.
    gate   film    film_checks.video_checks on each film.mp4 (the size its views.json planned, a sound track that is not silent, no black or
                   frozen stretch after the title card, a length within LENGTH_SLACK of planned_seconds for its
                   shots) and clearance_checks on the final stage (no eye nearer a mesh, a person or a moving thing than the
                   planner's clearance, at each frame's own moment); every shot at least SECONDS; a frame showing a
                   person where the place's design stands people; no thing seen moving in a shot without a sound of its own
                   (shots.py)
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

import numpy as np

from score import checks, contracts, graph
from score.stages import people_rows
from score.stages.demo_film import shots

REPO = pathlib.Path(__file__).resolve().parents[3]
SIZE = (1280, 720)
# Two shots a place, each from its own camera, so a finished place stays on screen about 7 s unbroken instead of 3.5 s
# (the finish plan for world 1, 2026-10-18); a place whose record holds one camera only gets one.
SHOTS = 2
# A place's shot: 4 s at demo.RATE (24), 96 frames, half the demo's SHOT_SECONDS, so a film's frames cost half (the
# overseer's plan, 2026-10-15).
SECONDS = 4.0
# How far a film's length may stand off its planned length (planned_seconds), seconds.
LENGTH_SLACK = 0.5
# The height over the floor (metres) of a spot given `across` a room's floor: its eye at the walker's, its aim at a
# standing person's chest, so the view runs level across the room.
ACROSS_EYE = 1.6
ACROSS_AIM = 1.2
# Workbench and Cycles on a 24 GB card only: the forecast prices that card, and a dearer class taken when it is out
# of stock would be a fallback chain inside the batch (#21); none in stock waits for a card of the run's warm pool
# (no stock never makes a gap: owner, 2026-10-23).
CLASSES = "gpu-24gb"
# Two shots of 96 frames: a 96-frame film over 8 cards cost EUR 1.48 to 1.75 with parking (ledger 2026-10-18:
# greenhouse, airlock, hangar, garage), most of it the frames' card time, so twice the measured 1.6 likely; the row's
# estimate (what its clearance reserves while the stage is unmeasured) is twice the measured high, 1.75.
LIKELY_EUROS = 3.2
EUROS = 3.5
# A plain frame's high over its likely: the measured films' high over their median (1.75 / 1.6).
FRAME_SPREAD = 1.75 / 1.6
# A frame's card minutes, the forecast's high, where the stage holds fog, a volume or glass: the airlock's frames
# inside its pump's fog took 47 s to 17 min each (2026-10-18). Its likely is demo.FRAME_MINUTES (0.7, the measured
# 42 s); a stage without them is priced high at FRAME_SPREAD times that.
FOG_FRAME_MINUTES = 17.0
# A frame job's minutes before its frames (demo.film_jobs' 10): the stage and its shown places loaded.
JOB_LEAD_MINUTES = 10
# The frames' Blender script: usd_views.py's views, each with the camera's motion blur.
FRAMES_SCRIPT = "score/stages/demo_film/blender/film_frames.py"
TOOLS = ("tools/review/demo.py", "tools/review/film_checks.py", "tools/review/renders.py",
         "tools/review/viewer/viewpoints.py", "tools/usd/camera_paths.py", "tools/usd/scene.py", "tools/usd/sound.py",
         "tools/usd/hearing.py", "tools/blender/inside/usd_views.py", FRAMES_SCRIPT)
# A frame's motion blur (owner, 2026-10-21: "make the animations very profesional looking"): the shutter open for
# half a frame (a film camera's 180 degrees), shortened where the picture moves so fast it would streak further than
# MOST_STREAK of its width in one frame; a camera whose picture moves under STILL_PIXELS a frame gets none. Only the
# camera's move and the stage's moving transforms blur (film_frames.py), so a frame costs what it did: unmeasured.
SHUTTER = 0.5
MOST_STREAK = 0.012
STILL_PIXELS = 0.5
OUTPUTS = ("film.mp4", "views.json", "concept.png")


# A segment's `shows` keys a film takes over (own_cameras, leave_out, film_start); the rest is the script's.
FILM_KEYS = ("camera", "eye", "aim", "across", "fov", "stand", "then", "start", "leave_out")


def films_of(scripts):
    """{film: its record} of every film the scripts ({name: script}) show, each with its `script`, its place and the
    segment's own camera keys: the first segment showing it decides; `final` is true, the script being locked."""
    from score.stages.demo_film import final
    found = {}
    for name, script in scripts.items():
        for _, segment in final.shown(script):
            shows = segment["shows"]
            found.setdefault(shows.get("film") or shows["place"], {
                "place": shows["place"], "script": name, "final": True,
                **{key: shows[key] for key in FILM_KEYS if key in shows}})
    return found


def films():
    """{film: its record} of every film the creator's locked scripts show."""
    from score.stages.demo_film import final
    return films_of(final.scripts())


def said_yes(film):
    """Whether the creator said yes to the film (its `final`: his lock of the script that shows it)."""
    return film.get("final") is True


def extras(place):
    """The names of the place's films other than its own."""
    return [name for name, film in films().items() if film["place"] == place and name != place]


def applies(place):
    return films().get(place, {}).get("place") == place


def require_yes(named):
    """Refuse the row (Blocked) before anything is bought while a film of `named` ({film: record}) has no `final`:
    the node stands and can go in the basket, but its frames are bought only after the creator's yes."""
    waiting = sorted(name for name, film in named.items() if not said_yes(film))
    if waiting:
        raise graph.Blocked(f"no yes yet for {', '.join(waiting)}: see the free preview and forecast "
                            "(python -m score.stages.demo_film forecast <place>), then write \"final\": true")


def applies_extra(place):
    return bool(extras(place))


def common_files(place):
    """The people its design stands (its entry of data/people/rows.json: seen_faults), the surfaces' sounds (the
    soundtrack's footsteps), and every tool file a film is made with. No place has a seed record (retired 2026-10-21):
    its record is its assembly's scene.json, which demo.plan reads first."""
    found = {f"tool {path}": "{repo}/" + path for path in TOOLS}
    found["sound surfaces"] = "{data}/sound/surfaces.json"  # the walker's footsteps by the kit kind underfoot
    found["people"] = ("{data}/people/rows.json", people_rows.place_part(place))
    return found


def script_files(names):
    """The locked film scripts that show the named films, keyed `script <name>`: a lock or its change makes them again."""
    from score.stages.demo_film import final
    every = films()
    return {"script " + script: "{dashboard}/" + f"{final.LOCKED}/{script}.json"
            for script in sorted({every[name]["script"] for name in names if name in every})}


def files(place):
    """The locked scripts showing the place's own film and the common files."""
    return {**script_files([place]), **common_files(place)}


def extra_files(place):
    """The locked scripts showing the place's other films and the common files."""
    return {**script_files(extras(place)), **common_files(place)}


def film_tools():
    """demo.py and film_checks.py, imported with the review tools' folders on the path, the path put back after."""
    kept = list(sys.path)
    sys.path[:0] = [str(REPO / "tools/review"), str(REPO / "tools/usd")]
    try:
        import demo
        import film_checks
    finally:
        sys.path[:] = kept
    return demo, film_checks


def final_stage(inputs):
    """The folder of the stage the place ends with: its neighbours output where it has one, else its assembly."""
    return pathlib.Path(inputs.get("neighbours") or inputs["assembly"])


def place_of(folder):
    return next(pathlib.Path(folder).glob("*.usda")).stem


def named_films(inputs, place, own):
    """{film: its record} of the place's films the locked scripts among the node's inputs show: its own (`own`) or
    its others."""
    found = films_of({name.removeprefix("script "): json.loads(pathlib.Path(path).read_text())
                      for name, path in inputs.items() if name.startswith("script ")})
    return {name: film for name, film in found.items() if film["place"] == place and (name == place) == own}


def render(jobs, out):
    """The frames' jobs on rented cards (the runner's clearance names them); the log kept in the output."""
    python = pathlib.Path.home() / ".farm-factory-props/env/bin/python"
    done = subprocess.run([str(python), str(REPO / "tools/cloud/blender_cloud.py"), *map(str, jobs),
                           "--who", "demo-film", "--classes", CLASSES], cwd=REPO, capture_output=True, text=True)
    with (out / "frames.log").open("a") as log:
        log.write(done.stdout[-30000:] + "\n" + done.stderr[-30000:])
    if done.returncode:
        raise RuntimeError(f"blender_cloud.py failed: {done.stderr[-2000:]}")


def film_start(film):
    """The second the film starts at: its segment's own `start` where it names one (a pump's fog cleared first:
    inside that fog a frame took 47 s to 17 min, 2026-10-18), else the stage's start."""
    return float(film.get("start", 0.0))


def film_one(stage_folder, name, film, out, log_folder, start=0.0):
    """One film of the place's final stage, its files written into `out` (module docstring)."""
    demo, _ = film_tools()
    place = place_of(stage_folder)
    work = log_folder / ".work"
    shutil.copytree(stage_folder, work / "stages" / place)
    subprocess.run(["chmod", "-R", "u+w", str(work / "stages")], check=True)
    cameras = own_cameras(work / "stages" / place / "scene.json", film)
    leave_out(work / "stages" / place / f"{place}.usda", film)
    given = f"{place}={','.join(cameras)}" if name == place else f"{name}@{place}={','.join(cameras)}"
    planned = film_forecast(stage_folder, film)  # the figure its clearance reserved (own_forecast)
    print(f"{name}: {forecast_line(planned)}", flush=True)
    refuse_over_clearance(name, planned, cleared_euros())
    jobs = demo.plan(work, work / "stages", [given], jobs_each=planned["jobs"], size=SIZE, ink=False,
                     shots=len(cameras), seconds=SECONDS, start=start)
    with_deadlines(jobs, planned["high_frame_minutes"])
    motion_blurred(jobs, json.loads((work / "views" / f"{name}.json").read_text())["views"], SIZE[0])
    render(jobs, log_folder)
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(work / "frames" / name / "shot0-000-look.png", out / "concept.png")
    demo.cut(work, [name])
    shutil.copy(work / "videos" / f"{name}.mp4", out / "film.mp4")
    if (work / "videos" / f"{name}-bed.wav").exists():
        shutil.copy(work / "videos" / f"{name}-bed.wav", out / "bed.wav")
    planned = json.loads((work / "views" / f"{name}.json").read_text())
    (out / "views.json").write_text(json.dumps(dict(planned, stage=f"{place}/{place}.usda"), indent=1))
    shutil.rmtree(work)


def film_forecast(stage_folder, film):
    """The forecast of one film of the place's final stage (`stage_folder`, read only): its shots as own_cameras
    picks them and the stage as its `leave_out` leaves it. The clearance (own_forecast) and the make (film_one) both
    price the film by it, so they hold one figure."""
    place = place_of(stage_folder)
    record = json.loads((pathlib.Path(stage_folder) / "scene.json").read_text())
    shots = len(film_cameras(record, film)[:SHOTS])
    return forecast(pathlib.Path(stage_folder) / f"{place}.usda", shots, film.get("leave_out", ()))


def cleared_forecast(planned):
    """What a node's clearance reserves for its films' forecasts (`planned`): their highs added up, no minutes (the
    runner's figures for an unmeasured run, compute.run_forecast's estimate)."""
    return {"euros": round(sum(film["high_euros"] for film in planned), 2), "minutes": None, "high_minutes": None,
            "measured": 0}


def own_forecast(inputs):
    """The place's own film's forecast from the node's inputs, which its clearance reserves (graph.Stage.forecast)."""
    stage_folder = final_stage(inputs)
    place = place_of(stage_folder)
    return cleared_forecast([film_forecast(stage_folder, named_films(inputs, place, True)[place])])


def extra_forecast(inputs):
    """The place's other films' forecasts from the node's inputs, added up: what its clearance reserves."""
    stage_folder = final_stage(inputs)
    named = named_films(inputs, place_of(stage_folder), False)
    return cleared_forecast([film_forecast(stage_folder, film) for _, film in sorted(named.items())])


def slow_parts(stage_path, left_out=()):
    """What in the stage makes a frame slow, by a free scan of its composed prims with the `left_out` prims inactive
    (a film's leave_out, in the scan's own session layer: the file untouched): {"fog": plain-card puff emitters
    (steam, fog, mist), "volumes": UsdVol volumes, "glass": UsdPreviewSurfaces drawn see-through (opacity under 1)},
    each a list of prim paths."""
    from pxr import Usd, UsdShade, UsdVol
    stage = Usd.Stage.Open(str(stage_path))
    stage.SetEditTarget(stage.GetSessionLayer())
    for path in left_out:
        stage.OverridePrim(path).SetActive(False)
    found = {"fog": [], "volumes": [], "glass": []}
    for prim in stage.Traverse():
        look, card = prim.GetAttribute("score:effect:look"), prim.GetAttribute("score:effect:card")
        if look and look.Get() == "puff" and card and card.Get() == "plain":
            found["fog"].append(str(prim.GetPath()))
        elif prim.IsA(UsdVol.Volume):
            found["volumes"].append(str(prim.GetPath()))
        elif prim.IsA(UsdShade.Shader) and UsdShade.Shader(prim).GetIdAttr().Get() == "UsdPreviewSurface":
            opacity = UsdShade.Shader(prim).GetInput("opacity")
            if opacity and opacity.Get() is not None and float(opacity.Get()) < 1.0:
                found["glass"].append(str(prim.GetPath()))
    return found


def forecast(stage_path, shots, left_out=()):
    """A film's free forecast before the creator's yes: its frames; the jobs they are dealt over
    (capacity.machines_for on the likely frame minutes and blender_cloud's set-up, a card a job); the likely and high
    minutes a frame (demo.FRAME_MINUTES; high FOG_FRAME_MINUTES where the scan finds fog, a volume or glass, else FRAME_SPREAD times
    the likely); the card
    minutes and the euros, likely and high (LIKELY_EUROS scaled from its measured film by frames and frame minutes); and what
    the scan found, the `left_out` prims inactive."""
    demo, _ = film_tools()
    sys.path.insert(0, str(REPO / "tools/cloud"))
    import blender_cloud
    import capacity
    frames = round(shots * SECONDS * demo.RATE)
    slow = slow_parts(stage_path, left_out)
    likely = demo.FRAME_MINUTES
    high = FOG_FRAME_MINUTES if any(slow.values()) else likely * FRAME_SPREAD
    euros = LIKELY_EUROS * frames / round(SHOTS * SECONDS * demo.RATE)
    return {"frames": frames, "jobs": capacity.machines_for(frames, likely, blender_cloud.SETUP_MINUTES),
            "frame_minutes": likely, "high_frame_minutes": high, "card_minutes": round(frames * likely),
            "high_card_minutes": round(frames * high), "euros": round(euros, 2),
            "high_euros": round(euros * high / likely, 2),
            "slow": {kind: len(paths) for kind, paths in slow.items()}}


def forecast_line(planned):
    """The forecast in one line, as the creator reads it before his yes."""
    slow = ", ".join(f"{count} {kind}" for kind, count in planned["slow"].items() if count) or "no fog, volume or glass"
    return (f"{planned['frames']} frames on {planned['jobs']} cards, EUR {planned['euros']} likely and "
            f"{planned['high_euros']} high ({planned['card_minutes']} to {planned['high_card_minutes']} card minutes; "
            f"{slow})")


def cleared_euros():
    """The euros the runner's clearance reserved for this process's paid run (SCORE_SPEND_TICKET and the store beside
    it, compute.spending), or None outside a cleared run."""
    from score.adapters import compute
    from score.store import Store
    ticket = os.environ.get(compute.TICKET, "").split()
    if len(ticket) != 2 or not os.environ.get(compute.STORE):
        return None
    cleared = Store.in_folder(os.environ[compute.STORE]).clearances(*ticket)
    return max(cleared, key=lambda clearance: clearance["at"])["euros"] if cleared else None


def refuse_over_clearance(name, planned, cleared):
    """Refuse the film (Blocked) before its frames are bought when its forecast's high passes what the creator's yes
    was cleared at (`cleared`, None outside a cleared run): a dearer film is a new ask at the forecast's price."""
    if cleared is not None and planned["high_euros"] > cleared + 1e-6:
        raise graph.Blocked(f"{name}: the forecast's high EUR {planned['high_euros']} passes the EUR {cleared:.2f} "
                            f"cleared ({forecast_line(planned)}); a new ask at the forecast's price")


def with_deadlines(jobs, frame_minutes):
    """Each frame job's deadline from its frames at `frame_minutes` (the forecast's high): a job past it is stopped
    and its frames are a gap, never run again inside the batch."""
    for job_path in jobs:
        job = json.loads(pathlib.Path(job_path).read_text())
        views = json.loads(pathlib.Path(job["args"][1]).read_text())["views"]
        job["minutes"] = round(JOB_LEAD_MINUTES + frame_minutes * len(views))
        pathlib.Path(job_path).write_text(json.dumps(job, indent=1))


def picture_speed(view, later, wide):
    """How far the picture moves from `view` to `later` (the next frame's), pixels across a picture `wide` pixels: the
    line of sight's turn and the eye's move across it at the aim's distance, at the view's focal length."""
    eye, aim = np.asarray(view["eye"], dtype=float), np.asarray(view["aim"], dtype=float)
    then_eye, then_aim = np.asarray(later["eye"], dtype=float), np.asarray(later["aim"], dtype=float)
    look, then_look = aim - eye, then_aim - then_eye
    distance = float(np.linalg.norm(look))
    look, then_look = look / distance, then_look / float(np.linalg.norm(then_look))
    turn = float(np.arccos(np.clip(look @ then_look, -1.0, 1.0)))
    move = then_eye - eye
    across = float(np.linalg.norm(move - (move @ look) * look))
    focal = wide / 2.0 / np.tan(np.radians(float(view["fov"])) / 2.0)
    return float(focal * (turn + across / distance))


def shutter_for(speed, wide):
    """The share of a frame the shutter stays open for a picture moving `speed` pixels a frame (SHUTTER, shortened so
    nothing streaks further than MOST_STREAK of the width); 0 under STILL_PIXELS."""
    return 0.0 if speed < STILL_PIXELS else round(min(SHUTTER, MOST_STREAK * wide / speed), 3)


def blur_of(view, later, wide):
    """A view's "blur" for film_frames.py, the camera of its shot's next frame `later` (None for a shot's last frame,
    or a camera standing still): {"eye", "aim", "up", "shutter", "codes": the time codes between the two}."""
    if later is None:
        return None
    shutter = shutter_for(picture_speed(view, later, wide), wide)
    if not shutter:
        return None
    return {"eye": later["eye"], "aim": later["aim"], "up": later.get("up", [0.0, 1.0, 0.0]), "shutter": shutter,
            "codes": max(1, int(later.get("frame", 1)) - int(view.get("frame", 0)))}


def motion_blurred(jobs, views, wide):
    """Each frame job drawn by FRAMES_SCRIPT, every view in it given its blur (blur_of) towards the next frame of its
    shot among the film's `views` (in order), at a picture `wide` pixels."""
    demo, _ = film_tools()
    following = {view["name"]: (later if demo.shot_of(later) == demo.shot_of(view) else None)
                 for view, later in zip(views, [*views[1:], None]) if later is not None}
    for job_path in jobs:
        job = json.loads(pathlib.Path(job_path).read_text())
        listing = pathlib.Path(job["args"][1])
        dealt = json.loads(listing.read_text())
        blurred = [dict(view, blur=found) if (found := blur_of(view, following.get(view["name"]), wide)) else view
                   for view in dealt["views"]]
        listing.write_text(json.dumps(dict(dealt, views=blurred), indent=1))
        pathlib.Path(job_path).write_text(json.dumps(dict(job, script=FRAMES_SCRIPT), indent=1))


def own_cameras(record_path, film):
    """The film's cameras, SHOTS at most, its own spots added to the stage's record copy as the cameras they name (the
    scene record itself untouched): the first its `camera`, the second its `then`, else the record camera standing
    furthest from the first (second_camera); one only where the record holds no other."""
    record = json.loads(record_path.read_text())
    shots = film_cameras(record, film)
    record["views"] = [view for view in record.get("views", []) if view["name"] not in {shot["name"] for shot in shots}]
    record["views"] += shots
    record_path.write_text(json.dumps(record, indent=1))
    return [shot["name"] for shot in shots][:SHOTS]


def film_cameras(record, film):
    """The film's camera views in the scene record: the first its `camera`, the second its `then`, else the record
    camera standing furthest from the first (second_camera); one only where the record holds no other."""
    first = film_view(record, film.get("camera") or first_camera(record), film)
    then = film.get("then")
    second = (film_view(record, then if isinstance(then, str) else then["camera"], then if isinstance(then, dict)
                        else {}) if then else second_camera(record, first))
    return [first] + ([second] if second else [])


def first_camera(record):
    """The scene record's first camera's name (the plan's first view, as the scene record writes them)."""
    if not record.get("views"):
        raise ValueError("the scene record has no camera to start the film at")
    return record["views"][0]["name"]


def film_view(record, name, spot):
    """A film's camera as a record view: a spot of its own where it gives one ("eye" and "aim", or "across" the
    record's floor), its "fov" else the record's own 75, and "stand" where its shot stands rather than walks
    (demo.shot_move), so a film can frame what no record camera does (the greenhouse's crop bed, 2026-10-18); else
    the record's camera of that name."""
    held = {"stand": True} if spot.get("stand") else {}
    if "eye" in spot:
        return {"name": name, "eye": spot["eye"], "aim": spot["aim"], "fov": spot.get("fov", 75), **held}
    if "across" in spot:
        return dict(across(record, spot["across"]), name=name, fov=spot.get("fov", 75), **held)
    found = [view for view in record.get("views", []) if view["name"] == name]
    if not found:
        raise ValueError(f"the scene record has no camera {name}")
    return found[0]


def across(record, shares):
    """A spot given as shares of the record's floor ({"eye": [x, z], "aim": [x, z]}, 0 at its low corner and 1 at its
    high one), so it keeps its place in the room when the room is built again at another size (the ship's rooms at
    1.5 times, 2026-10-18): {"eye", "aim"} at ACROSS_EYE and ACROSS_AIM over the floor at y = 0."""
    low, high = (np.asarray(corner, dtype=float) for corner in record["floor"])
    def point(share, height):
        flat = low + np.asarray(share, dtype=float) * (high - low)
        return [round(float(flat[0]), 3), height, round(float(flat[1]), 3)]
    return {"eye": point(shares["eye"], ACROSS_EYE), "aim": point(shares["aim"], ACROSS_AIM)}


def second_camera(record, first):
    """The record camera whose eye stands furthest from the first's, none looking up at a roof (demo.steep) and none
    the first itself: a film's second shot where its record names none; None where there is no other."""
    demo, _ = film_tools()
    others = [view for view in record.get("views", []) if view["name"] != first["name"] and not demo.steep(view)]
    if not others:
        return None
    return max(others, key=lambda view: float(np.linalg.norm(np.subtract(view["eye"], first["eye"]))))


def leave_out(stage_path, film):
    """The prims a film record's `leave_out` names, made inactive in the film's copy of the stage: a joined tube's own
    outside ground showing up inside the room it joins (tools/usd/scene.py write_places leaves a shown place's
    Outside active; it covered the greenhouse's crop bed, 2026-10-18), until the stage itself leaves it out."""
    if not film.get("leave_out"):
        return
    from pxr import Usd
    stage = Usd.Stage.Open(str(stage_path))
    for path in film["leave_out"]:
        stage.OverridePrim(path).SetActive(False)
    stage.GetRootLayer().Save()


def make(inputs, out, seed, params):
    """The place's own film, in the output's root."""
    stage_folder = final_stage(inputs)
    place = place_of(stage_folder)
    film = named_films(inputs, place, True)[place]
    require_yes({place: film})
    film_one(stage_folder, place, film, out, out, film_start(film))


def make_extra(inputs, out, seed, params):
    """Each of the place's other films, in a folder of its name."""
    stage_folder = final_stage(inputs)
    named = named_films(inputs, place_of(stage_folder), False)
    require_yes(named)
    for name, film in sorted(named.items()):
        film_one(stage_folder, name, film, out / name, out, film_start(film))


def film_faults(folder):
    return [f"no {name}" for name in OUTPUTS if not (pathlib.Path(folder) / name).exists()]


def extra_faults(folder):
    filmed = [path for path in pathlib.Path(folder).iterdir() if path.is_dir()]
    return [f"{path.name}: {fault}" for path in filmed for fault in film_faults(path)] or ([] if filmed
                                                                                            else ["no film"])


CONTRACT = contracts.Contract("demo-film", 1, film_faults, {"time": "second"})
EXTRA_CONTRACT = contracts.Contract("demo-film-extra", 1, extra_faults, {"time": "second"})


def planned_seconds(shots):
    """A film's planned length: its title card and its shots joined by half-second fades (demo.py TITLE_SECONDS,
    FADE_SECONDS): 2 + 4 + 4 - 2 x 0.5 = 9 s for two shots."""
    demo, _ = film_tools()
    return demo.TITLE_SECONDS + shots * (SECONDS - demo.FADE_SECONDS)


def film_measures(folder, stage_folder, people=0):
    """One film's video checks, at the size its views planned, its length within
    LENGTH_SLACK of its planned length for the shots its views hold, and its frames' clearance: (seconds, mean dB,
    size, faults)."""
    demo, film_checks = film_tools()
    planned = json.loads((folder / "views.json").read_text())
    length = planned_seconds(len(planned.get("moves", [])))
    size = tuple(planned.get("size", SIZE))
    video = film_checks.video_checks(folder / "film.mp4", length - LENGTH_SLACK, length + LENGTH_SLACK,
                                     demo.TITLE_SECONDS, size)
    views = planned["views"]
    stage = stage_folder / f"{place_of(stage_folder)}.usda"
    _, near = film_checks.clearance_checks(stage, views)
    return video["seconds"], video["mean_db"], size, video["failures"] + near + seen_faults(stage, views, people)


def seen_faults(stage, views, people=0):
    """What the film's frames fail to show (the owner's review of 2026-10-18): a shot shorter than SECONDS, nobody in
    view in any frame where the stage holds people, and a thing seen moving in a shot with no sound of its own
    (shots.py). A film with no frames planned shows nothing to judge here: the video checks fail it."""
    if not views:
        return []
    demo, _ = film_tools()
    frames = {}
    for view in views:
        frames[demo.shot_of(view)] = frames.get(demo.shot_of(view), 0) + 1
    found = [f"{shot}: {count / demo.RATE:.2f} s, under a steady shot's {SECONDS:g} s"
             for shot, count in frames.items() if count < round(SECONDS * demo.RATE)]
    seen = shots.people_seen(stage, views)
    if seen is not None and not any(seen.values()):
        found.append("the place holds people and no frame shows one")
    elif seen is None and people:  # the motion layer's bodies: the design stands people the stage never got (#26)
        found.append(f"the place's design stands {people} people and the film's stage holds none")
    found += [f"{shot}: {path} moves in view with no sound" for shot, paths in shots.silent_moving(stage, views).items()
              for path in paths]
    return found


def cast_people(place, rows):
    """How many people the place's design stands (data/people/rows.json at `rows`): its people and its crowd's count
    (one at least where SAM 3 could not part the crowd); 0 with none, or no rows read."""
    found = json.loads(pathlib.Path(rows).read_text()) if rows else {"places": {}}
    crowd = people_rows.crowd_row(place, found)
    return len(people_rows.persons(place, found)) + ((people_rows.crowd_count(crowd[1]) or 1) if crowd else 0)


def film_verdict(folders, inputs):
    """The `film` verdict over the given films' folders (module docstring)."""
    stage_folder = final_stage(inputs)
    people = cast_people(place_of(stage_folder), inputs.get("people"))
    measured = {folder.name: film_measures(folder, stage_folder, people) for folder in folders}
    faults = [fault for _, _, _, found in measured.values() for fault in found]
    reason = "; ".join(faults[:3]) if faults else "; ".join(
        f"{seconds} s at {size[0]}x{size[1]}, sound at {loud} dB, every frame clear"
        for seconds, loud, size, _ in measured.values())
    return checks.Verdict("film", checks.FAIL if faults else checks.PASS, reason,
                          {"films": len(measured), "faults": len(faults)}, {"faults": "lower"}, tuple(faults))


def judge_film(output, inputs, evidence):
    return film_verdict([pathlib.Path(output)], inputs)


def judge_extra(output, inputs, evidence):
    return film_verdict(sorted(path for path in pathlib.Path(output).iterdir() if path.is_dir()), inputs)


CHECKS = (checks.Check("film", judge_film),)
EXTRA_CHECKS = (checks.Check("film", judge_extra),)
