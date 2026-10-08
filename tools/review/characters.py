"""The review page's characters: each of a place's people seen close from the front, each group and the crowd from where
the cast says they are seen, and a short moving shot of each, all rendered by headless Blender from the place's OpenUSD
stage with its characters layer (tools/characters/cast.py). Who is where is read from the place's cast
(`data/characters/<place>.json`), the record the layer was written from.

A character's close view is taken from the first of a ring of eyes round its front with a clear line to it (a wall
may stand in front of somebody), with any crowd left out so one of a group standing in it is seen; a group is seen from in front of its band; a crowd from the cast's own `views`
(the balcony over the square) and from what it faces. The moving shots are consecutive frames of the stage's time,
so every character plays its clip and starts where the cast started it.
"""
import json
import math
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "tools/characters"))
sys.path.insert(0, str(HERE))
import renders  # noqa: E402

CASTS = REPO / "data/characters"
STILL_SIZE = (640, 640)
WIDE_SIZE = (960, 540)
MOVE_SIZE = (480, 360)
# A still is drawn this far into the stage's time, in seconds, so every character is under way in its clip.
STILL_SECONDS = 0.5
# A moving shot: this many frames at this many a second.
MOVE_FRAMES = 24
MOVE_RATE = 12
# A close view: how far from the character, how high the eye and the aim, the angle across, and the turns round its
# front the eye tries in order (degrees; 0 is straight in front).
CLOSE_DISTANCE = 2.6
EYE_HEIGHT = 1.6
AIM_HEIGHT = 1.0
CLOSE_FOV = 40.0
RING = (0, 35, -35, 70, -70, 110, -110, 180)
# A group's view: how far in front of its band's middle and how high.
GROUP_BACK = 9.0
GROUP_HIGH = 3.0


def cast_of(place):
    """The place's cast, or None when it has none."""
    path = CASTS / f"{place}.json"
    return json.loads(path.read_text()) if path.exists() else None


def ahead(at, turn, distance, round_by=0.0):
    """A point `distance` in front of a character at `at` turned `turn` degrees (its front is -z), swung `round_by`."""
    angle = math.radians(turn + round_by)
    return [at[0] - math.sin(angle) * distance, at[1], at[2] - math.cos(angle) * distance]


def close_view(single, frame):
    """One character seen close, from the first clear eye round its front."""
    at = single["at"] if not single.get("path") else single["path"][0]
    eyes = [ahead(at, single["turn"], CLOSE_DISTANCE, turn) for turn in RING]
    eyes = [[eye[0], at[1] + EYE_HEIGHT, eye[2]] for eye in eyes]
    return {"name": f"close-{single['name']}", "eye": eyes[0], "eyes": eyes, "aim": [at[0], at[1] + AIM_HEIGHT, at[2]],
            "up": [0, 1, 0], "fov": CLOSE_FOV, "frame": frame, "look_only": True, "hide_crowds": True}


def group_view(group, frame):
    """A group seen from in front of its band's middle, looking along what it faces back at it."""
    left, near, across, along = group["band"]
    middle = [left + across / 2, group.get("height", 0.0), near + along / 2]
    to = group["facing_to"]
    heading = math.atan2(to[0] - middle[0], to[2] - middle[2])
    eye = [middle[0] + math.sin(heading) * GROUP_BACK, middle[1] + GROUP_HIGH, middle[2] + math.cos(heading) * GROUP_BACK]
    return {"name": f"group-{group['name']}", "eye": eye, "aim": [middle[0], middle[1] + AIM_HEIGHT, middle[2]],
            "up": [0, 1, 0], "fov": 60.0, "frame": frame, "look_only": True}


def crowd_views(crowd, frame):
    """The crowd from the cast's own views, and from above what it faces, looking back over it."""
    left, near, wide, long = crowd["spread"]
    middle = [left + wide / 2, 1.0, near + long / 2]
    to = crowd["facing_to"]
    views = [{"name": f"crowd-{view['name']}", "eye": view["eye"], "aim": view["aim"], "up": [0, 1, 0],
              "fov": view.get("fov", 60.0), "frame": frame, "look_only": True} for view in crowd.get("views", [])]
    views.append({"name": f"crowd-{crowd['name']}-faced", "eye": [to[0], to[1] + 3.0, to[2]], "aim": middle,
                  "up": [0, 1, 0], "fov": 70.0, "frame": frame, "look_only": True})
    return views


def moving(view, first, step):
    """A view's moving shot: MOVE_FRAMES consecutive frames of it, look alone."""
    return [dict(view, name=f"{view['name']}-{number:03d}", frame=first + number * step, look_only=True)
            for number in range(MOVE_FRAMES)]


def video(folder, name, out):
    """A moving shot's frames as a small looping video."""
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg is needed for the characters' moving shots")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(MOVE_RATE), "-i",
                    str(folder / f"{name}-%03d-look.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "26",
                    "-movflags", "+faststart", str(out / f"{name}.mp4")], check=True)


def plan(place, stage):
    """Every view the page draws of the place's characters, by kind, and the moving shots' views; None without a
    cast."""
    import cast as casting
    found = cast_of(place)
    if found is None:
        return None
    rate = renders.stage_rate(stage)
    frame = round(STILL_SECONDS * rate)
    step = max(1, round(rate / MOVE_RATE))
    singles = casting.characters_of(found)
    named = {person["name"] for person in found.get("people", [])}
    closes = [close_view(single, frame) for single in singles]
    wides = [group_view(group, frame) for group in found.get("groups", [])]
    if found.get("crowd"):
        wides += crowd_views(found["crowd"], frame)
    moves = [view for view in closes if view["name"].removeprefix("close-") in named] + wides
    return {"closes": closes, "wides": wides, "moves": [view["name"] for view in moves],
            "move_views": [frame_view for view in moves for frame_view in moving(view, frame, step)],
            "who": [{"name": single["name"], "character": single["character"], "doing": single["doing"]}
                    for single in singles],
            "crowd": found.get("crowd", {}).get("count", 0), "why": casting_reasons(found), "note": found.get("note", "")}


def casting_reasons(found):
    """Each entry of the cast and why it is there."""
    entries = found.get("people", []) + found.get("groups", []) + ([found["crowd"]] if found.get("crowd") else [])
    return [{"name": entry["name"], "why": entry.get("why", "")} for entry in entries]


def words(place):
    """What the page says of the cast, read from it now (why each entry is there, the note when nobody is), so a
    reworded cast needs no new renders."""
    found = cast_of(place) or {}
    return {"why": casting_reasons(found), "note": found.get("note", "")}


def shots(place, stage, out):
    """The characters' pictures and moving shots under <out>/characters; what the page shows of them, or None."""
    planned = plan(place, stage)
    if planned is None:
        return None
    folder = out / "characters"
    for views, size, kind in ((planned["closes"], STILL_SIZE, "close"), (planned["wides"], WIDE_SIZE, "wide"),
                              (planned["move_views"], MOVE_SIZE, "moves")):
        if views:
            renders.render_stage(stage, views, size, folder / kind)
    for name in planned["moves"]:
        video(folder / "moves", name, folder)
    return {"closes": [view["name"] for view in planned["closes"]], "wides": [view["name"] for view in planned["wides"]],
            "moves": planned["moves"], "who": planned["who"], "crowd": planned["crowd"], "why": planned["why"],
            "note": planned["note"]}
