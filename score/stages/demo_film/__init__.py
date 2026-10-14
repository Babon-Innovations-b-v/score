"""demo-film: a place's walk-through film for the paper's demo K9, from its final stage once it passes complete, with
its own sound; one place node, paid (its frames on the cheapest card through tools/props/cloud/blender_cloud.py inside
the runner's clearance, drawn by tools/blender/inside/usd_views.py as tools/review/demo.py plans them). Only the places
the world's record names have the row, so a place is filmed when it is added there, group by group.

    data/definitions/demo_films.json   {"why", "places": [place, ...]}

    make   the final stage (the neighbours output where the place shows others, else its assembly), copied into a tree
           of its own; demo.py's plan with SHOTS camera path from the owner's picked viewpoint or the scene record's
           cameras, SIZE frames, look only (no ink); the frames rendered; demo.py's cut with the stage's sound layer.
           The output: film.mp4 and views.json (each frame's view, the moves, the planner's commit); the frames are
           not kept.
    gate   film    film_checks.video_checks on film.mp4 (SIZE, a sound track that is not silent, no black or frozen
                   stretch after the title card, a length within LEAST to MOST seconds) and clearance_checks on the
                   final stage (no eye nearer a mesh than the planner's clearance)
"""
import json
import pathlib
import shutil
import subprocess
import sys

from score import checks, contracts

REPO = pathlib.Path(__file__).resolve().parents[3]
RECORD = REPO / "data/definitions/demo_films.json"
SIZE = (1280, 720)
SHOTS = 1
# The title card and one 8 s shot joined by a half-second fade (demo.py TITLE_SECONDS, SHOT_SECONDS, FADE_SECONDS).
LEAST, MOST = 9.0, 10.0
# Workbench and Cycles on a card; the cheapest first (capacity.KIND_ORDER), never an H100 (capacity.NEVER).
CLASSES = "gpu-24gb,gpu-48gb"
JOBS = 2
# 192 frames at EUR 0.0030 a frame at 720p, look only (ledger batch blender-20261009-020545-2401425: 5,292 frames,
# EUR 15.76), and a machine's set-up, rounded up.
EUROS = 1.0
TOOLS = ("tools/review/demo.py", "tools/review/film_checks.py", "tools/review/renders.py",
         "tools/review/viewer/viewpoints.py", "tools/usd/camera_paths.py", "tools/usd/scene.py", "tools/usd/sound.py",
         "tools/blender/inside/usd_views.py")


def record():
    """The world's filmed places (none when the world has no record)."""
    return json.loads(RECORD.read_text()) if RECORD.exists() else {"places": []}


def applies(place):
    return place in record()["places"]


def files(place):
    """The record, the place's scene record and picked viewpoints, and every tool file the film is made with."""
    found = {"films": "{data}/definitions/demo_films.json", "scene": "{data}/scene/" + place + ".json",
             **{f"tool {path}": "{repo}/" + path for path in TOOLS}}
    if (REPO / "data/review" / place / "viewpoints.json").exists():
        found["viewpoints"] = "{data}/review/" + place + "/viewpoints.json"
    return found


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


def render(jobs, out):
    """The frames' jobs on rented cards (the runner's clearance names them); the log kept in the output."""
    python = pathlib.Path.home() / ".farm-factory-props/env/bin/python"
    done = subprocess.run([str(python), str(REPO / "tools/props/cloud/blender_cloud.py"), *map(str, jobs),
                           "--who", "demo-film", "--classes", CLASSES], cwd=REPO, capture_output=True, text=True)
    (out / "frames.log").write_text(done.stdout[-30000:] + "\n" + done.stderr[-30000:])
    if done.returncode:
        raise RuntimeError(f"blender_cloud.py failed: {done.stderr[-2000:]}")


def make(inputs, out, seed, params):
    """The place's film from its final stage (module docstring)."""
    demo, _ = film_tools()
    stage_folder = final_stage(inputs)
    place = place_of(stage_folder)
    work = out / ".work"
    shutil.copytree(stage_folder, work / "stages" / place)
    subprocess.run(["chmod", "-R", "u+w", str(work / "stages")], check=True)
    jobs = demo.plan(work, work / "stages", [place], jobs_each=JOBS, size=SIZE, ink=False, shots=SHOTS)
    render(jobs, out)
    demo.cut(work, [place])
    shutil.copy(work / "videos" / f"{place}.mp4", out / "film.mp4")
    planned = json.loads((work / "views" / f"{place}.json").read_text())
    (out / "views.json").write_text(json.dumps(dict(planned, stage=f"{place}/{place}.usda"), indent=1))
    shutil.rmtree(work)


def film_faults(folder):
    return [f"no {name}" for name in ("film.mp4", "views.json") if not (pathlib.Path(folder) / name).exists()]


CONTRACT = contracts.Contract("demo-film", 1, film_faults, {"time": "second"})


def judge_film(output, inputs, evidence):
    """The film's measured checks (module docstring)."""
    demo, film_checks = film_tools()
    stage_folder = final_stage(inputs)
    video = film_checks.video_checks(pathlib.Path(output) / "film.mp4", LEAST, MOST, demo.TITLE_SECONDS, SIZE)
    views = json.loads((pathlib.Path(output) / "views.json").read_text())["views"]
    _, near = film_checks.clearance_checks(stage_folder / f"{place_of(stage_folder)}.usda", views)
    faults = video["failures"] + near
    reason = "; ".join(faults[:3]) if faults else (f"{video['seconds']} s at {SIZE[0]}x{SIZE[1]}, sound at "
                                                   f"{video['mean_db']} dB, every frame clear")
    return checks.Verdict("film", checks.FAIL if faults else checks.PASS, reason,
                          {"seconds": video["seconds"], "faults": len(faults)}, {"faults": "lower"}, tuple(faults))


CHECKS = (checks.Check("film", judge_film),)
