"""demo-film and demo-film-extra: walk-through films for the paper's demo K9, from a place's final stage once it passes
complete, with its own sound; place nodes, paid (the frames on the cheapest card through
tools/props/cloud/blender_cloud.py inside the runner's clearance, drawn by tools/blender/inside/usd_views.py as
tools/review/demo.py plans them).

    data/definitions/demo_films/<film>.json   {"place", "camera" (a camera of the place's scene record), "why",
                                               and optionally "eye" and "aim" or "across" (a spot of its own for
                                               that camera, own_cameras), "then" (its second shot's camera: a
                                               record camera's name or a spot of its own), "start", "leave_out",
                                               "final" (the creator's yes: true)}

A film named for its place (<place>.json) is the place's own film, the demo-film row; any other film of a place (the
ship's hull through the hangar: hull.json, place hangar) is the demo-film-extra row's, which makes all of them for
that place. One file a film, so adding a film moves no other film's key; a place with no file has no node.

A film is one batch (#21, the owner's batch of 2026-10-20): its frames are bought once, after the creator's yes, and
never again inside it. Before the yes everything is free: the creator looks at the free local preview
(tools/review/film_preview.py: the same plan, a few frames drawn on this PC) and the forecast (`python -m
score.stages.demo_film forecast <place>`: frames, cards, card minutes and euros, likely and high, from a scan of the
stage for fog, volumes and glass); then he writes `"final": true` in the film's record. A film without it has no
node, so nothing is priced or bought for it. A frame job that dies or passes its deadline is a hole: its film fails
the gate, and a new film is a new batch and a new yes.

    make   the final stage (the neighbours output where the place shows others, else its assembly), copied into a tree
           of its own; demo.py's plan with a camera path a shot, SHOTS shots: the first starting at the film's camera
           and the second at its `then`, else at the record camera standing furthest from the first (its first frame that
           camera's view, unless the planner had to move its start clear or level it: views.json's moves say),
           frames over SECONDS at demo.RATE, look only (no ink); the frames rendered once at SIZE with the films'
           samples, dealt over the jobs `forecast` sizes (capacity.machines_for on the likely frame minutes), each
           job's deadline its frames at the forecast's high frame minutes; demo.py's cut with the stage's sound
           layer. Per film:
           film.mp4, views.json (each frame's view, the moves, the planner's commit) and concept.png, the first frame
           (for the place's own film, demo K8's still beside the concept), and bed.wav where the stage has sound (what
           the camera hears standing at its first view before it walks, demo.BED_SECONDS, which the showcase lays under
           the place's cards); the other frames are not kept. The own
           film's files lie in the output's root, each extra film's in a folder of its name.
    gate   film    film_checks.video_checks on each film.mp4 (the size its views.json planned, a sound track that is not silent, no black or
                   frozen stretch after the title card, a length within LENGTH_SLACK of planned_seconds for its
                   shots) and clearance_checks on the final stage (no eye nearer a mesh, a person or a mover than the
                   planner's clearance)
"""
import json
import pathlib
import shutil
import subprocess
import sys

import numpy as np

from score import checks, contracts

REPO = pathlib.Path(__file__).resolve().parents[3]
FILMS = REPO / "data/definitions/demo_films"
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
# A film starts this long before the first one-off moment of its place's motion record (motion_start), so the moment
# lands about a second into the shot (the launch's lift-off; overseer, 2026-10-15).
LEAD = 1.0
# Workbench and Cycles on a card; the cheapest first (capacity.KIND_ORDER), never an H100 (capacity.NEVER).
CLASSES = "gpu-24gb,gpu-48gb"
# Two shots of 96 frames: a 96-frame film over 8 cards cost EUR 1.48 to 1.75 with parking (ledger 2026-10-18:
# greenhouse, airlock, hangar, garage), most of it the frames' card time, so twice the measured 1.6.
EUROS = 3.2
# A frame's card minutes, the forecast's high, where the stage holds fog, a volume or glass: the airlock's frames
# inside its pump's fog took 47 s to 17 min each (2026-10-18). Its likely, and both for a stage without them, is
# demo.FRAME_MINUTES (0.7, the measured 42 s).
FOG_FRAME_MINUTES = 17.0
# A frame job's minutes before its frames (demo.film_jobs' 10): the stage and its shown places loaded.
JOB_LEAD_MINUTES = 10
TOOLS = ("tools/review/demo.py", "tools/review/film_checks.py", "tools/review/renders.py",
         "tools/review/viewer/viewpoints.py", "tools/usd/camera_paths.py", "tools/usd/scene.py", "tools/usd/sound.py",
         "tools/usd/hearing.py", "tools/blender/inside/usd_views.py")
OUTPUTS = ("film.mp4", "views.json", "concept.png")


def films():
    """{film: its record} of every film the world names (none without the folder)."""
    return {path.stem: json.loads(path.read_text()) for path in sorted(FILMS.glob("*.json"))}


def said_yes(film):
    """Whether the creator said yes to the film (its record's `final`), after its free preview and forecast."""
    return film.get("final") is True


def extras(place):
    """The names of the place's films other than its own that the creator said yes to."""
    return [name for name, film in films().items() if film["place"] == place and name != place and said_yes(film)]


def applies(place):
    film = films().get(place, {})
    return film.get("place") == place and said_yes(film)


def applies_extra(place):
    return bool(extras(place))


def common_files(place):
    """The place's seed scene record, motion record and picked viewpoints where it has them, the surfaces' sounds (the
    soundtrack's footsteps), and every tool file a film is made with. A ship room has no seed record (its record is its assembly's scene.json, which demo.plan reads
    first), so it declares none, as stills.files (2026-10-16: demo-film@cockpit refused, data/scene/cockpit.json
    missing)."""
    found = {f"tool {path}": "{repo}/" + path for path in TOOLS}
    found["sound surfaces"] = "{data}/sound/surfaces.json"  # the walker's footsteps by the kit kind underfoot
    if (REPO / "data/scene" / f"{place}.json").exists():
        found["scene"] = "{data}/scene/" + place + ".json"
    if (REPO / "data/motion" / f"{place}.json").exists():
        found["motion"] = "{data}/motion/" + place + ".json"
    if (REPO / "data/review" / place / "viewpoints.json").exists():
        found["viewpoints"] = "{data}/review/" + place + "/viewpoints.json"
    return found


def files(place):
    """The place's own film record and the common files."""
    return {"film " + place: "{data}/definitions/demo_films/" + place + ".json", **common_files(place)}


def extra_files(place):
    """Each of the place's other film records and the common files."""
    return {**{"film " + name: "{data}/definitions/demo_films/" + name + ".json" for name in extras(place)},
            **common_files(place)}


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


def named_films(inputs):
    """{film: its record} of the film records among the node's inputs."""
    return {name.removeprefix("film "): json.loads(pathlib.Path(path).read_text())
            for name, path in inputs.items() if name.startswith("film ")}


def render(jobs, out):
    """The frames' jobs on rented cards (the runner's clearance names them); the log kept in the output."""
    python = pathlib.Path.home() / ".farm-factory-props/env/bin/python"
    done = subprocess.run([str(python), str(REPO / "tools/props/cloud/blender_cloud.py"), *map(str, jobs),
                           "--who", "demo-film", "--classes", CLASSES], cwd=REPO, capture_output=True, text=True)
    with (out / "frames.log").open("a") as log:
        log.write(done.stdout[-30000:] + "\n" + done.stderr[-30000:])
    if done.returncode:
        raise RuntimeError(f"blender_cloud.py failed: {done.stderr[-2000:]}")


def motion_start(inputs):
    """The stage's second a film starts at: LEAD before the first one-off moment of the place's motion record (a
    motion that does not loop: its start, or for a climb its lift-off), never before 0; 0 with no such motion."""
    if "motion" not in inputs:
        return 0.0
    motions = json.loads(pathlib.Path(inputs["motion"]).read_text()).get("motions", [])
    moments = [motion["start"] + motion.get("climb", {}).get("lift", 0.0) for motion in motions
               if not motion.get("loop")]
    return max(0.0, min(moments) - LEAD) if moments else 0.0


def film_start(film, inputs):
    """The second the film starts at: its record's own `start` where it names one (the airlock's 6 s, after its pump's
    fog clears: inside that fog a frame took 47 s to 17 min, 2026-10-18), else motion_start's."""
    return float(film["start"]) if "start" in film else motion_start(inputs)


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
    planned = forecast(work / "stages" / place / f"{place}.usda", len(cameras))
    print(f"{name}: {forecast_line(planned)}", flush=True)
    jobs = demo.plan(work, work / "stages", [given], jobs_each=planned["jobs"], size=SIZE, ink=False,
                     shots=len(cameras), seconds=SECONDS, start=start)
    with_deadlines(jobs, planned["high_frame_minutes"])
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


def slow_parts(stage_path):
    """What in the stage makes a frame slow, by a free scan of its composed prims: {"fog": plain-card puff emitters
    (steam, fog, mist), "volumes": UsdVol volumes, "glass": UsdPreviewSurfaces drawn see-through (opacity under 1)},
    each a list of prim paths."""
    from pxr import Usd, UsdShade, UsdVol
    stage = Usd.Stage.Open(str(stage_path))
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


def forecast(stage_path, shots):
    """A film's free forecast before the creator's yes: its frames; the jobs they are dealt over
    (capacity.machines_for on the likely frame minutes and blender_cloud's set-up, a card a job); the likely and high
    minutes a frame (demo.FRAME_MINUTES; FOG_FRAME_MINUTES high where the scan finds fog, a volume or glass); the card
    minutes and the euros, likely and high (EUROS scaled from its measured film by frames and frame minutes); and what
    the scan found."""
    demo, _ = film_tools()
    sys.path.insert(0, str(REPO / "tools/props/cloud"))
    import blender_cloud
    import capacity
    frames = round(shots * SECONDS * demo.RATE)
    slow = slow_parts(stage_path)
    likely = demo.FRAME_MINUTES
    high = FOG_FRAME_MINUTES if any(slow.values()) else likely
    euros = EUROS * frames / round(SHOTS * SECONDS * demo.RATE)
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


def with_deadlines(jobs, frame_minutes):
    """Each frame job's deadline from its frames at `frame_minutes` (the forecast's high): a job past it is stopped
    and its frames are a hole, never run again inside the batch."""
    for job_path in jobs:
        job = json.loads(pathlib.Path(job_path).read_text())
        views = json.loads(pathlib.Path(job["args"][1]).read_text())["views"]
        job["minutes"] = round(JOB_LEAD_MINUTES + frame_minutes * len(views))
        pathlib.Path(job_path).write_text(json.dumps(job, indent=1))


def own_cameras(record_path, film):
    """The film's cameras, SHOTS at most, its own spots added to the stage's record copy as the cameras they name (the
    scene record itself untouched): the first its `camera`, the second its `then`, else the record camera standing
    furthest from the first (second_camera); one only where the record holds no other."""
    record = json.loads(record_path.read_text())
    first = film_view(record, film["camera"], film)
    then = film.get("then")
    second = (film_view(record, then if isinstance(then, str) else then["camera"], then if isinstance(then, dict)
                        else {}) if then else second_camera(record, first))
    shots = [first] + ([second] if second else [])
    record["views"] = [view for view in record.get("views", []) if view["name"] not in {shot["name"] for shot in shots}]
    record["views"] += shots
    record_path.write_text(json.dumps(record, indent=1))
    return [shot["name"] for shot in shots][:SHOTS]


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
    film = named_films(inputs)[place]
    film_one(stage_folder, place, film, out, out, film_start(film, inputs))


def make_extra(inputs, out, seed, params):
    """Each of the place's other films, in a folder of its name."""
    stage_folder = final_stage(inputs)
    for name, film in sorted(named_films(inputs).items()):
        film_one(stage_folder, name, film, out / name, out, film_start(film, inputs))


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


def film_measures(folder, stage_folder):
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
    _, near = film_checks.clearance_checks(stage_folder / f"{place_of(stage_folder)}.usda", views)
    return video["seconds"], video["mean_db"], size, video["failures"] + near


def film_verdict(folders, inputs):
    """The `film` verdict over the given films' folders (module docstring)."""
    stage_folder = final_stage(inputs)
    measured = {folder.name: film_measures(folder, stage_folder) for folder in folders}
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
