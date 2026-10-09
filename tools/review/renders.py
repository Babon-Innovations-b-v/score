"""The review page's pictures that no stage drew: each made model and its labelled parts, and the assembled scene from
fixed cameras and along a walk, all rendered by headless Blender (`tools/blender/session.py batch`, no window, the
machine's lock). The scene is the place's OpenUSD stage (tools/usd/export.py); no game engine is involved.

A kit room (a layout of pieces in frames of their own) is drawn from inside: from each wall's middle across the room
at eye height, from high in a corner with its roof left out (a cutaway), and walked round inside, lit by its own
lamps where the game hangs them (HubKit), as point lights.

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
# Inside a room: how far in from a wall a view stands, how far round the middle the walk goes (a share of the half
# floor), the roof's draw layer a cutaway leaves out, and a lamp's watts in Blender for each unit of the game's
# strength over each metre of its reach.
WALL_IN = 0.6
ROOM_WALK = 0.45
ROOF_LAYER = 2
LAMP_WATTS = 60.0
# A player's eye over the floor he stands on (2099: the head 1.65 m over the body's feet), for the walk inside a room.
STANDING = 1.6


# Where the Blender work runs: None for this PC's Blender (one at a time, the machine's lock), else a rented machine
# held for the page's whole build (tools/props/cloud/blender_cloud.Machine), set by page.py --cloud.
CLOUD = None
CLOUD_CLASSES = ("gpu-24gb", "gpu-48gb", "gpu-80gb", "cpu-32c-128gb", "cpu-32c-64gb")


def blender(script, *arguments, inputs=(), outputs=()):
    """Run a Blender script here, or on a rented card when CLOUD is set (its inputs sent, its outputs brought back)."""
    if CLOUD:
        CLOUD.run(script, arguments, inputs, outputs, minutes=20)
        return
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
    sources = {pathlib.Path(entry["path"]).parent for group in groups for member in group["members"]
               for entry in member["files"]}
    blender(MODEL_SHOTS, folder / "shots.json", folder, inputs=[folder / "shots.json", *sorted(sources)],
            outputs=[folder])
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


def room_views(low, high):
    """Inside a room: from each wall's middle across to the opposite wall at eye height, and from high in a corner
    looking down across it with its roof left out."""
    middle = (low + high) / 2
    views = []
    for name, side in (("from-north", (0.0, -1.0)), ("from-east", (1.0, 0.0)), ("from-south", (0.0, 1.0)),
                       ("from-west", (-1.0, 0.0))):
        half = (high - low) / 2
        eye = middle + np.array([side[0] * (half[0] - WALL_IN), 0.0, side[1] * (half[2] - WALL_IN)])
        aim = middle - np.array([side[0] * half[0], 0.0, side[1] * half[2]])
        views.append(looking(name, [eye[0], low[1] + EYE_HEIGHT, eye[2]], [aim[0], low[1] + 1.2, aim[2]], fov=75.0))
    corner = np.array([low[0] + (high[0] - low[0]) * 0.1, high[1] + max(high - low) * 0.35,
                       low[2] + (high[2] - low[2]) * 0.1])
    views.append(dict(looking("cutaway", corner, [middle[0], low[1], middle[2]], fov=70.0), hide_layers=[ROOF_LAYER]))
    return views


def room_walk(low, high):
    """Once round inside the room at eye height, looking across it."""
    middle = (low + high) / 2
    half = (high - low) / 2 * ROOM_WALK
    frames = []
    for number in range(WALK_FRAMES):
        turn = 2 * math.pi * number / WALK_FRAMES
        eye = [middle[0] + half[0] * math.sin(turn), low[1] + EYE_HEIGHT, middle[2] + half[2] * math.cos(turn)]
        aim = [middle[0] - half[0] * math.sin(turn), low[1] + 1.2, middle[2] - half[2] * math.cos(turn)]
        frames.append(looking(f"walk-{number:03d}", eye, aim, fov=75.0, look_only=True))
    return frames


def room_lights(kit):
    """A kit room's lamps where HubKit hangs their lights: a little in front of the piece, at its kind's `high`."""
    lights = []
    for laid in kit["pieces"]:
        light = kit.get("kinds", {}).get(laid["kind"], {}).get("light")
        if light is None or "part" in laid:
            continue
        size = np.asarray(laid["size"], dtype=float)
        at = (np.asarray(laid["at"], dtype=float) + np.asarray(laid["y"]) * size[1] * float(light.get("high", 0.5))
              - np.asarray(laid["z"]) * (size[2] / 2 + 0.05))
        lights.append({"at": [round(float(value), 3) for value in at], "radius": 0.1,
                       "energy": round(LAMP_WATTS * float(light.get("strength", 0.1)) * float(light.get("reach", 4.0)),
                                       1)})
    return lights


def render_stage(stage, views, size, folder, plain=False, lights=(), shown=()):
    """The stage drawn from the views; `shown` are the other places' stages it references (its scene record's
    `places`, exported beside it), sent with it when it renders elsewhere."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "views.json").write_text(json.dumps({"size": list(size), "views": views, "plain": plain,
                                                   "lights": list(lights)}, indent=1))
    beside = [pathlib.Path(stage).parent.parent / name for name in shown]
    blender(SCENE_VIEWS, stage, folder / "views.json", folder,
            inputs=[pathlib.Path(stage).parent, *beside, folder / "views.json"], outputs=[folder])


def walk_video(folder, out, stage=None, walk=()):
    """The walk's frames as a small looping video, with what the walk hears from the stage's sound layer laid under it
    (tools/usd/sound.py; none when the stage has no sounds), and a strip of a few of them for where a video does not
    play."""
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg is needed for the walk's video")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(WALK_RATE), "-i",
                    str(folder / "walk-%03d-look.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "26",
                    "-movflags", "+faststart", str(out / "walk.mp4")], check=True)
    if stage is not None and walk and (pathlib.Path(stage).parent / "layers/sound.usda").exists():
        heard(stage, walk, WALK_RATE, out / "walk.mp4")
    chosen = [folder / f"walk-{number:03d}-look.png" for number in range(0, WALK_FRAMES, WALK_FRAMES // STRIP_FRAMES)]
    frames = [Image.open(path).convert("RGB") for path in chosen[:STRIP_FRAMES]]
    strip = Image.new("RGB", (WALK_SIZE[0] * len(frames), WALK_SIZE[1]))
    for number, frame in enumerate(frames):
        strip.paste(frame, (number * WALK_SIZE[0], 0))
    strip.save(out / "walk-strip.jpg", quality=85)


def heard(stage, views, frame_rate, video):
    """The video with what its camera hears along its views laid under it (sound.soundtrack), in place."""
    import sound  # noqa: E402  (tools/usd)
    rate = stage_rate(stage)
    moments = [{"eye": view["eye"], "aim": view["aim"], "time": view.get("frame", 0) / rate} for view in views]
    track = pathlib.Path(video).with_suffix(".wav")
    sound.soundtrack(stage, moments, frame_rate, track)
    voiced = pathlib.Path(video).with_name(pathlib.Path(video).stem + "-sound.mp4")
    sound.with_sound(video, track, voiced)
    voiced.replace(video)
    track.unlink()


def stage_rate(stage):
    """The stage's time codes a second (the root's; 24 when it names none, as USD reads it)."""
    from pxr import Sdf
    layer = Sdf.Layer.FindOrOpen(str(stage))
    return layer.timeCodesPerSecond if layer.HasTimeCodesPerSecond() else 24.0


def timed(walk, stage):
    """The walk's frames at consecutive moments of the stage's time, WALK_RATE a second, so its characters move."""
    rate = stage_rate(stage)
    return [dict(view, frame=round(number * rate / WALK_RATE)) for number, view in enumerate(walk)]


def record_views(scene):
    """The scene record's own cameras (data/scene/<place>.json `views`: the player's spots, inside a room at standing
    height), each naming the game's shot from about the same place; the first also drawn with the game's ink lines
    over it (`ink`), one extra picture a place."""
    return [dict(looking(view["name"], view["eye"], view["aim"], fov=float(view.get("fov", 75.0))),
                 game=view.get("game"), **({"ink": True} if number == 0 else {}))
            for number, view in enumerate(scene.get("views", []))]


def cutaway(scene):
    """A room's cutaway: from high over one corner of its floor looking down across it, its roof left out."""
    low, high = np.asarray(scene["floor"][0], dtype=float), np.asarray(scene["floor"][1], dtype=float)
    middle = (low + high) / 2
    reach = float(np.linalg.norm(high - low))
    eye = [low[0] + (high[0] - low[0]) * 0.1, float(scene.get("ceiling", 3.0)) + reach * 0.35,
           low[1] + (high[1] - low[1]) * 0.1]
    return dict(looking("cutaway", eye, [middle[0], 0.0, middle[1]], fov=70.0), hide_layers=[ROOF_LAYER])


def record_walk(scene):
    """The walk: inside a room once round its floor at standing height looking across it; outside, from each of the
    player's spots to the next, looking where the spots look."""
    if scene.get("inside"):
        low, high = np.asarray(scene["floor"][0], dtype=float), np.asarray(scene["floor"][1], dtype=float)
        middle, half = (low + high) / 2, (high - low) / 2 * ROOM_WALK
        frames = []
        for number in range(WALK_FRAMES):
            turn = 2 * math.pi * number / WALK_FRAMES
            eye = [middle[0] + half[0] * math.sin(turn), STANDING, middle[1] + half[1] * math.cos(turn)]
            aim = [middle[0] - half[0] * math.sin(turn), 1.2, middle[1] - half[1] * math.cos(turn)]
            frames.append(looking(f"walk-{number:03d}", eye, aim, fov=75.0, look_only=True))
        return frames
    spots = scene.get("views", [])
    frames = []
    for number in range(WALK_FRAMES):
        position = number / WALK_FRAMES * len(spots)
        first, second = spots[int(position) % len(spots)], spots[(int(position) + 1) % len(spots)]
        share = position - int(position)
        eye = (1 - share) * np.asarray(first["eye"], dtype=float) + share * np.asarray(second["eye"], dtype=float)
        aim = (1 - share) * np.asarray(first["aim"], dtype=float) + share * np.asarray(second["aim"], dtype=float)
        frames.append(looking(f"walk-{number:03d}", eye, aim, fov=75.0, look_only=True))
    return frames


def places_shown(scene):
    """The other places a scene record shows (and the ones they show), by stage name, each once."""
    import scene as scene_record
    found, waiting = [], [entry["stage"] for entry in (scene or {}).get("places", [])]
    while waiting:
        name = waiting.pop()
        if name not in found:
            found.append(name)
            waiting += [entry["stage"] for entry in (scene_record.record(name) or {}).get("places", [])]
    return found


def scene_shots(place, stages, out, plain=False, room=None, kit=False, scene=None):
    """Every stage drawn from the same fixed cameras (set from the newest stage), and the newest one walked round, in
    their materials on their ground (`plain`: in one grey, a debug view). `stages` is {label: stage.usda}, the newest
    last. With the place's scene record (`scene`), the cameras are its own (the player's spots; a room from inside at
    standing height and from a cutaway above) and the light is the stage's own; without one, `room` is a kit room's
    layout, drawn from inside by its lamps, and `kit` a kit laid outdoors, drawn from round it and from inside its
    extent. The views' names per stage, and the newest stage's import report as Blender read it."""
    low, high = stage_extent(list(stages.values())[-1])
    newest = list(stages)[-1]
    if scene is not None and scene.get("views"):
        views = record_views(scene) + ([cutaway(scene)] if scene.get("inside") else [])
        walk, lights = record_walk(scene), []
    elif room is not None:
        views, walk, lights = room_views(low, high), room_walk(low, high), room_lights(room)
    else:
        views = game_views(place, stages[newest]) + on_the_ground(stages[newest], fixed_views(low, high))
        if kit:
            views += [view for view in room_views(low, high) if view["name"] != "cutaway"]
        walk, lights = on_the_ground(stages[newest], walk_views(low, high)), []
    walk = timed(walk, stages[newest])
    shown = places_shown(scene)
    for label, stage in stages.items():
        render_stage(stage, views, VIEW_SIZE, out / "scene" / label, plain, lights, shown)
    render_stage(stages[newest], walk, WALK_SIZE, out / "scene" / "walk", plain, lights, shown)
    walk_video(out / "scene" / "walk", out / "scene", stages[newest], walk)
    report = json.loads((out / "scene" / newest / "report.json").read_text())
    return {"views": [view["name"] for view in views], "report": report, "room": room is not None,
            "lamps": len(lights), "games": {view["name"]: view.get("game") for view in views if view.get("game")},
            "recorded": scene is not None, "extent": [low.round(2).tolist(), high.round(2).tolist()]}
