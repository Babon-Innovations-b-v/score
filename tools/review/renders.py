"""The review page's pictures that no stage drew: each made model and its labelled parts, and the assembled scene from
fixed cameras and along a walk, all rendered by headless Blender (`tools/blender/session.py batch`, no window, the
machine's lock). The scene is the place's OpenUSD stage (tools/usd/export.py); no game engine is involved.

Two runs of a stage are drawn from the same cameras: a model's takes share one camera set from both, and every stage
is rendered from cameras set from the newest stage's extent.
"""
import json
import math
import pathlib
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
SESSION = REPO / "tools/blender/session.py"
MODEL_SHOTS = REPO / "tools/blender/inside/review_models.py"
SCENE_VIEWS = REPO / "tools/blender/inside/usd_views.py"
sys.path.insert(0, str(REPO / "tools/usd"))

MODEL_SIZE = (480, 480)
VIEW_SIZE = (960, 540)
WALK_SIZE = (480, 270)
EYE_HEIGHT = 1.7
LENS = 60.0
# The walk: once round the place at eye height, looking at its middle, this many frames at this many a second.
WALK_FRAMES = 60
WALK_RATE = 12
STRIP_FRAMES = 6
# How much room is left round the place in a fixed view, and how far out the walk goes, as shares of its radius.
VIEW_ROOM = 1.15
WALK_OUT = 1.35


def blender(script, *arguments):
    command = [sys.executable, str(SESSION), "batch", str(script), "--", *map(str, arguments)]
    if subprocess.run(command, stdout=subprocess.DEVNULL).returncode != 0:
        raise RuntimeError(f"the Blender batch {script.name} failed; run it by hand to see its output: {command}")


# --- models -------------------------------------------------------------------------------------------------------

def parts_member(name, take, colours):
    """A labelled take as one member: every surface's .ply drawn in that surface's colour."""
    return {"name": name, "up": "y",
            "files": [{"path": str(path), "colour": colours[path.stem]["colour"] if path.stem in colours else None}
                      for path in take["surfaces"]]}


def model_groups(names, runs, colours):
    """Per model, its labelled parts and its made model, each a group holding every run's take of it."""
    groups = []
    for model in names:
        parts = [parts_member(f"{model}--parts--{label}", run["takes"][model], colours)
                 for label, run in runs.items() if run and model in run["takes"] and run["takes"][model]["surfaces"]]
        made = [{"name": f"{model}--made--{label}", "files": [{"path": str(run["models"][model])}]}
                for label, run in runs.items() if run and model in run["models"]]
        groups += [{"name": f"{model}-{what}", "members": members}
                   for what, members in (("parts", parts), ("made", made)) if members]
    return groups


def model_shots(names, runs, colours, out):
    """Every model's shots in out/models; the names of the shots made, with Blender's count of each one's triangles."""
    folder = out / "models"
    groups = model_groups(names, runs, colours)
    if not groups:
        return {}
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "shots.json").write_text(json.dumps({"size": list(MODEL_SIZE), "groups": groups}, indent=1))
    blender(MODEL_SHOTS, folder / "shots.json", folder)
    return json.loads((folder / "shots-report.json").read_text())


# --- the scene ----------------------------------------------------------------------------------------------------

def stage_extent(stage):
    """The place's drawn objects' box in the stage's own frame (metres, y up), colliders and the ground left out:
    (low, high)."""
    from pxr import Usd, UsdGeom
    opened = Usd.Stage.Open(str(stage))
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    objects = opened.GetDefaultPrim().GetChild("Objects")
    box = cache.ComputeWorldBound(objects if objects.IsValid() else opened.GetPseudoRoot()).ComputeAlignedRange()
    return np.array(box.GetMin()), np.array(box.GetMax())


def on_the_ground(stage, views, level=None):
    """The views with every eye and aim lifted by the ground's height under it (the stage's Ground; a flat place's
    ground is y = 0), so an eye at 1.7 m is 1.7 m over the ground where it stands. `level` is the height the views
    already stand on at each (x, z), taken off first (the game's views stand on the level ball)."""
    from pxr import Usd
    import resting
    opened = Usd.Stage.Open(str(stage))
    height = resting.ground_height(opened, opened.GetDefaultPrim().GetName())
    lifted = []
    for view in views:
        points = np.array([view["eye"], view["aim"]])
        under = np.nan_to_num(height(points[:, [0, 2]]))
        if level is not None:
            under = under - level(points[:, [0, 2]])
        lifted.append(dict(view, eye=[*map(float, points[0] + [0, under[0], 0])],
                           aim=[*map(float, points[1] + [0, under[1], 0])]))
    return lifted


def looking(name, eye, aim, fov=LENS, look_only=False):
    view = {"name": name, "eye": [round(float(value), 4) for value in eye],
            "aim": [round(float(value), 4) for value in aim], "up": [0.0, 1.0, 0.0], "fov": fov}
    return dict(view, look_only=True) if look_only else view


def fixed_views(low, high):
    """Four views from the sides at eye height and one from high on a corner, each holding the whole place."""
    middle = (low + high) / 2
    radius = float(np.linalg.norm((high - low)[[0, 2]]) / 2)
    distance = radius * VIEW_ROOM / math.tan(math.radians(LENS) / 2)
    aim = np.array([middle[0], max(1.0, middle[1] * 0.5), middle[2]])
    views = []
    for name, heading in (("from-plus-z", 0), ("from-plus-x", 90), ("from-minus-z", 180), ("from-minus-x", 270)):
        turn = math.radians(heading)
        eye = middle + distance * np.array([math.sin(turn), 0.0, math.cos(turn)])
        views.append(looking(name, [eye[0], EYE_HEIGHT, eye[2]], aim))
    corner = middle + distance * np.array([0.6, 0.75, 0.6])
    views.append(looking("from-above", corner, aim))
    return views


def game_views(place, stage):
    """The game's own bench cameras for the place, where tools/usd/views.py knows them (the wreck), lifted by the
    hills under them when the stage has its ground (views.py lays them on the level ball)."""
    if place != "wreck":
        return []
    import views
    found = [views.place_view(name, *ends) for name, ends in views.WRECK_VIEWS.items()]
    from pxr import Usd
    opened = Usd.Stage.Open(str(stage))
    if not opened.GetDefaultPrim().GetChild("Ground").IsValid():
        return found
    radius = views.MOON_RADIUS
    return on_the_ground(stage, found, lambda flat: np.sqrt(radius ** 2 - (flat ** 2).sum(axis=1)) - radius)


def walk_views(low, high):
    """Once round the place at eye height, a little outside it, always looking at its middle."""
    middle = (low + high) / 2
    radius = float(np.linalg.norm((high - low)[[0, 2]]) / 2) * WALK_OUT
    aim = [middle[0], 1.0, middle[2]]
    frames = []
    for number in range(WALK_FRAMES):
        turn = 2 * math.pi * number / WALK_FRAMES
        eye = [middle[0] + radius * math.sin(turn), EYE_HEIGHT, middle[2] + radius * math.cos(turn)]
        frames.append(looking(f"walk-{number:03d}", eye, aim, fov=70.0, look_only=True))
    return frames


def render_stage(stage, views, size, folder, plain=False):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "views.json").write_text(json.dumps({"size": list(size), "views": views, "plain": plain}, indent=1))
    blender(SCENE_VIEWS, stage, folder / "views.json", folder)


def walk_video(folder, out):
    """The walk's frames as a small looping video, and a strip of a few of them for where a video does not play."""
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg is needed for the walk's video")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(WALK_RATE), "-i",
                    str(folder / "walk-%03d-look.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "26",
                    "-movflags", "+faststart", str(out / "walk.mp4")], check=True)
    chosen = [folder / f"walk-{number:03d}-look.png" for number in range(0, WALK_FRAMES, WALK_FRAMES // STRIP_FRAMES)]
    frames = [Image.open(path).convert("RGB") for path in chosen[:STRIP_FRAMES]]
    strip = Image.new("RGB", (WALK_SIZE[0] * len(frames), WALK_SIZE[1]))
    for number, frame in enumerate(frames):
        strip.paste(frame, (number * WALK_SIZE[0], 0))
    strip.save(out / "walk-strip.jpg", quality=85)


def scene_shots(place, stages, out, plain=False):
    """Every stage drawn from the same fixed cameras (set from the newest stage), and the newest one walked round, in
    their materials on their ground (`plain`: in one grey, a debug view). `stages` is {label: stage.usda}, the newest
    last. The views' names per stage, and the newest stage's import report as Blender read it."""
    low, high = stage_extent(list(stages.values())[-1])
    newest = list(stages)[-1]
    views = game_views(place, stages[newest]) + on_the_ground(stages[newest], fixed_views(low, high))
    for label, stage in stages.items():
        render_stage(stage, views, VIEW_SIZE, out / "scene" / label, plain)
    render_stage(stages[newest], on_the_ground(stages[newest], walk_views(low, high)), WALK_SIZE,
                 out / "scene" / "walk", plain)
    walk_video(out / "scene" / "walk", out / "scene")
    report = json.loads((out / "scene" / newest / "report.json").read_text())
    return {"views": [view["name"] for view in views], "report": report,
            "extent": [low.round(2).tolist(), high.round(2).tolist()]}
