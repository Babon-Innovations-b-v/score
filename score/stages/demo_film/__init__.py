"""demo-film and demo-film-extra: walk-through films for the paper's demo K9, from a place's final stage once it passes
complete, with its own sound; place nodes, paid (the frames on the cheapest card through
tools/props/cloud/blender_cloud.py inside the runner's clearance, drawn by tools/blender/inside/usd_views.py as
tools/review/demo.py plans them).

    data/definitions/demo_films/<film>.json   {"place", "camera" (a camera of the place's scene record), "why"}

A film named for its place (<place>.json) is the place's own film, the demo-film row; any other film of a place (the
ship's hull through the hangar: hull.json, place hangar) is the demo-film-extra row's, which makes all of them for
that place. One file a film, so adding a film moves no other film's key; a place with no file has no node.

    make   the final stage (the neighbours output where the place shows others, else its assembly), copied into a tree
           of its own; demo.py's plan with SHOTS camera path starting at the film's camera (its first frame that
           camera's view, unless the planner had to move its start clear or level it: views.json's moves say),
           SIZE frames over SECONDS at demo.RATE, look only (no ink); the frames rendered;
           demo.py's cut with the stage's sound layer. Per film:
           film.mp4, views.json (each frame's view, the moves, the planner's commit) and concept.png, the first frame
           (for the place's own film, demo K8's still beside the concept); the other frames are not kept. The own
           film's files lie in the output's root, each extra film's in a folder of its name.
    gate   film    film_checks.video_checks on each film.mp4 (SIZE, a sound track that is not silent, no black or
                   frozen stretch after the title card, a length within LEAST to MOST seconds) and clearance_checks
                   on the final stage (no eye nearer a mesh than the planner's clearance)
"""
import json
import pathlib
import shutil
import subprocess
import sys

from score import checks, contracts

REPO = pathlib.Path(__file__).resolve().parents[3]
FILMS = REPO / "data/definitions/demo_films"
SIZE = (1280, 720)
SHOTS = 1
# A place's shot: 4 s at demo.RATE (24), 96 frames, half the demo's SHOT_SECONDS, so a film's frames cost half (the
# overseer's plan, 2026-10-15).
SECONDS = 4.0
# The planned length: the title card and the shot joined by a half-second fade (demo.py TITLE_SECONDS, FADE_SECONDS),
# 2 + 4 - 0.5 = 5.5 s, within half a second.
LEAST, MOST = 5.0, 6.0
# A film starts this long before the first one-off moment of its place's motion record (motion_start), so the moment
# lands about a second into the shot (the launch's lift-off; overseer, 2026-10-15).
LEAD = 1.0
# Workbench and Cycles on a card; the cheapest first (capacity.KIND_ORDER), never an H100 (capacity.NEVER).
CLASSES = "gpu-24gb,gpu-48gb"
JOBS = 2
# 96 frames (SECONDS at 24) at EUR 0.0030 a frame at 720p, look only (ledger batch blender-20261009-020545-2401425:
# 5,292 frames, EUR 15.76), and a machine's set-up, rounded up (the 8 s shot's 192 frames: EUR 1.0).
EUROS = 0.7
TOOLS = ("tools/review/demo.py", "tools/review/film_checks.py", "tools/review/renders.py",
         "tools/review/viewer/viewpoints.py", "tools/usd/camera_paths.py", "tools/usd/scene.py", "tools/usd/sound.py",
         "tools/blender/inside/usd_views.py")
OUTPUTS = ("film.mp4", "views.json", "concept.png")


def films():
    """{film: its record} of every film the world names (none without the folder)."""
    return {path.stem: json.loads(path.read_text()) for path in sorted(FILMS.glob("*.json"))}


def extras(place):
    """The names of the place's films other than its own."""
    return [name for name, film in films().items() if film["place"] == place and name != place]


def applies(place):
    return films().get(place, {}).get("place") == place


def applies_extra(place):
    return bool(extras(place))


def common_files(place):
    """The place's seed scene record, motion record and picked viewpoints where it has them, and every tool file a film
    is made with. A ship room has no seed record (its record is its assembly's scene.json, which demo.plan reads
    first), so it declares none, as stills.files (2026-10-16: demo-film@cockpit refused, data/scene/cockpit.json
    missing)."""
    found = {f"tool {path}": "{repo}/" + path for path in TOOLS}
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


def film_one(stage_folder, name, film, out, log_folder, start=0.0):
    """One film of the place's final stage, its files written into `out` (module docstring)."""
    demo, _ = film_tools()
    place = place_of(stage_folder)
    work = log_folder / ".work"
    shutil.copytree(stage_folder, work / "stages" / place)
    subprocess.run(["chmod", "-R", "u+w", str(work / "stages")], check=True)
    given = f"{place}={film['camera']}" if name == place else f"{name}@{place}={film['camera']}"
    jobs = demo.plan(work, work / "stages", [given], jobs_each=JOBS, size=SIZE, ink=False, shots=SHOTS,
                     seconds=SECONDS, start=start)
    render(jobs, log_folder)
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(work / "frames" / name / "shot0-000-look.png", out / "concept.png")
    demo.cut(work, [name])
    shutil.copy(work / "videos" / f"{name}.mp4", out / "film.mp4")
    planned = json.loads((work / "views" / f"{name}.json").read_text())
    (out / "views.json").write_text(json.dumps(dict(planned, stage=f"{place}/{place}.usda"), indent=1))
    shutil.rmtree(work)


def make(inputs, out, seed, params):
    """The place's own film, in the output's root."""
    stage_folder = final_stage(inputs)
    place = place_of(stage_folder)
    film_one(stage_folder, place, named_films(inputs)[place], out, out, motion_start(inputs))


def make_extra(inputs, out, seed, params):
    """Each of the place's other films, in a folder of its name."""
    stage_folder = final_stage(inputs)
    for name, film in sorted(named_films(inputs).items()):
        film_one(stage_folder, name, film, out / name, out, motion_start(inputs))


def film_faults(folder):
    return [f"no {name}" for name in OUTPUTS if not (pathlib.Path(folder) / name).exists()]


def extra_faults(folder):
    filmed = [path for path in pathlib.Path(folder).iterdir() if path.is_dir()]
    return [f"{path.name}: {fault}" for path in filmed for fault in film_faults(path)] or ([] if filmed
                                                                                            else ["no film"])


CONTRACT = contracts.Contract("demo-film", 1, film_faults, {"time": "second"})
EXTRA_CONTRACT = contracts.Contract("demo-film-extra", 1, extra_faults, {"time": "second"})


def film_measures(folder, stage_folder):
    """One film's video checks and its frames' clearance: (seconds, mean dB, faults)."""
    demo, film_checks = film_tools()
    video = film_checks.video_checks(folder / "film.mp4", LEAST, MOST, demo.TITLE_SECONDS, SIZE)
    views = json.loads((folder / "views.json").read_text())["views"]
    _, near = film_checks.clearance_checks(stage_folder / f"{place_of(stage_folder)}.usda", views)
    return video["seconds"], video["mean_db"], video["failures"] + near


def film_verdict(folders, inputs):
    """The `film` verdict over the given films' folders (module docstring)."""
    stage_folder = final_stage(inputs)
    measured = {folder.name: film_measures(folder, stage_folder) for folder in folders}
    faults = [fault for _, _, found in measured.values() for fault in found]
    reason = "; ".join(faults[:3]) if faults else "; ".join(
        f"{seconds} s at {SIZE[0]}x{SIZE[1]}, sound at {loud} dB, every frame clear"
        for seconds, loud, _ in measured.values())
    return checks.Verdict("film", checks.FAIL if faults else checks.PASS, reason,
                          {"films": len(measured), "faults": len(faults)}, {"faults": "lower"}, tuple(faults))


def judge_film(output, inputs, evidence):
    return film_verdict([pathlib.Path(output)], inputs)


def judge_extra(output, inputs, evidence):
    return film_verdict(sorted(path for path in pathlib.Path(output).iterdir() if path.is_dir()), inputs)


CHECKS = (checks.Check("film", judge_film),)
EXTRA_CHECKS = (checks.Check("film", judge_extra),)
