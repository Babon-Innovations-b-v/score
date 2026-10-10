"""A world's demo: a walk-through video of each place from its OpenUSD stage, and one video of the world in story order.

    .venv/bin/python tools/review/demo.py plan <out> --stages <stage root> [--jobs-each N] \
        <film>[@<place>][=<camera>,...] [...]
    ~/.farm-factory-props/env/bin/python tools/props/cloud/blender_cloud.py <out>/jobs/*.json --who <session> \
        --classes gpu-24gb,gpu-48gb,gpu-80gb
    .venv/bin/python tools/review/demo.py cut <out> <film>[:<Title>] [...]

`plan` writes, per film, the views of its shots (`<out>/views/<film>.json`) and its cloud Blender jobs that render them
with the review's scene script (`../blender/inside/usd_views.py`, Cycles on a card), its stage folder and every place
its stage shows as inputs. A film is a place's, or one of its own from a place's stage (`film@place`: the Mars camp's
grounds from the camp's outside cameras). A shot starts at one of the scene record's own cameras (the player's spots;
the cameras named, else a few spread over the record, none looking up at a roof) and walks from there at the player's
eye height, as the game is seen: a walk-through path (tools/usd/camera_paths.py: RRT* on the stage's own floors, every
step clear of walls and objects; in a room, on its recorded floor) from the camera's spot towards what it looks at,
stopping well short of it, while the view keeps on that thing, held near level. Where no clear path goes forward the
walk goes sideways, still looking at it; where none goes either way, or the camera stands on no floor of the stage, the
eye stands and the view turns a few degrees. The frames follow the stage's own time, one shot after the other, so its
characters move through the whole video. `cut` makes each film's video from its frames (the shots joined by short cross-
fades, opened by a title card with its plain name, given as `film:Title`) and, given more than one, the world's video
with the films in the order given. A film whose stage has a sound layer (tools/usd/sound.py) is heard too: each shot's
sound is what its camera hears along its frames (sound.soundtrack), cross-faded with the pictures.

The videos are made outside the repo, like the review pages; nothing they make is committed.
"""
import argparse
import json
import math
import pathlib
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import renders  # noqa: E402  (puts tools/usd on the path)
import camera_paths  # noqa: E402  (tools/usd)
import scene as scene_record  # noqa: E402  (tools/usd)

SIZE = (1920, 1080)
RATE = 24
SHOT_SECONDS = 8.0
SHOTS = 4
FADE_SECONDS = 0.5
TITLE_SECONDS = 2.0
# A walk's pace (metres a second: slow inside a room, a walker's outside), the share of the way to what it looks at
# it may go at most (it stops well short of it), the shorter walks tried when the whole one is blocked, the share of the
# reach a sideways walk goes, the shortest
# walk worth taking and how far round its start and end the path may wander (metres).
PACE_INSIDE = 0.45
PACE_OUTSIDE = 1.1
WALK_SHARE = 0.5
WALK_TRIES = (1.0, 0.5)
SIDE_SHARE = 0.5
SHORTEST_WALK = 0.5
WANDER = 2.0
# How far the view may look up or down from level (degrees): the eye reads the place, not its ceiling or its feet.
LOOK_UP = 8.0
LOOK_DOWN = 25.0
# How far over or under the walker's eye a record's camera may be held and still stand on the floor under it (metres).
HELD = 1.0
# How far a standing shot's view turns (degrees), where no walk is clear.
TURN_DEGREES = 10.0
# A camera this steep (its aim over its eye by more than this share of the distance) looks at a roof: not a shot.
STEEPEST = 0.6
# Minutes a frame takes on a 24 GB card, the import aside (the square and the hub on an L4, 2026-10-09: 14 to 20 s).
FRAME_MINUTES = 0.3
FONT = pathlib.Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
# The sound track's sample rate (tools/usd/sound.py's).
SAMPLE_RATE = 48000


def shot_cameras(record, count=SHOTS, names=()):
    """The record's cameras named, in that order; else up to `count` of them, spread over its list: the player's spots,
    none looking up at a roof."""
    if names:
        found = {view["name"]: view for view in record.get("views", [])}
        missing = [name for name in names if name not in found]
        if missing:
            raise SystemExit(f"the scene record has no camera {', '.join(missing)}")
        return [found[name] for name in names]
    level = [view for view in record.get("views", []) if not steep(view)]
    if len(level) <= count:
        return level
    picks = np.linspace(0, len(level) - 1, count).round().astype(int)
    return [level[index] for index in picks]


def steep(view):
    eye, aim = np.asarray(view["eye"], dtype=float), np.asarray(view["aim"], dtype=float)
    return (aim[1] - eye[1]) > STEEPEST * np.linalg.norm(aim - eye)


def turned(eye, aim, degrees):
    """The aim turned about the eye's up (y) by `degrees`."""
    angle = math.radians(degrees)
    offset = np.asarray(aim, dtype=float) - eye
    cosine, sine = math.cos(angle), math.sin(angle)
    return eye + np.array([cosine * offset[0] + sine * offset[2], offset[1], -sine * offset[0] + cosine * offset[2]])


def eased(frames):
    """A shot's progress at each of its frames, from 0 to 1, starting and ending slowly."""
    shares = np.linspace(0.0, 1.0, frames)
    return 0.5 - 0.5 * np.cos(np.pi * shares)


def levelled(eye, aim):
    """The aim moved up or down about the eye so the view looks no more than LOOK_UP above level or LOOK_DOWN below."""
    offset = np.asarray(aim, dtype=float) - eye
    across = max(float(np.linalg.norm(offset[[0, 2]])), 1e-6)
    pitch = min(max(math.degrees(math.atan2(offset[1], across)), -LOOK_DOWN), LOOK_UP)
    return eye + np.array([offset[0], across * math.tan(math.radians(pitch)), offset[2]])


def start_eye(scenes, view):
    """Where a shot's walk starts: the camera's spot at eye height over the floor under it, or None when no floor of
    the stage lies within HELD of the camera's own eye height under it (a camera on a balcony the stage does not
    draw). The floor is looked for from STEP_RISE over where the camera's own eye height puts it, so from under a desk
    top or a table."""
    spot = np.asarray(view["eye"], dtype=float)
    top = spot[1] - camera_paths.EYE_HEIGHT + camera_paths.STEP_RISE - camera_paths.CLIMB
    found = camera_paths.eyes_over(scenes, [spot[[0, 2]]], camera_paths.EYE_HEIGHT, [top])[0]
    return found if np.isfinite(found[1]) and abs(found[1] - spot[1]) <= HELD else None


def walk_goals(eye, aim, reach):
    """Where a walk may go, in the order tried: towards the aim (the whole reach, then shorter), then sideways either
    way, (x, z) each."""
    towards = (np.asarray(aim, dtype=float) - eye)[[0, 2]]
    way = towards / max(float(np.linalg.norm(towards)), 1e-6)
    forward = min(reach, WALK_SHARE * float(np.linalg.norm(towards)))
    side = np.array([-way[1], way[0]]) * reach * SIDE_SHARE
    return [eye[[0, 2]] + way * forward * share for share in WALK_TRIES] + [eye[[0, 2]] + side, eye[[0, 2]] - side]


def on_floor(goal, floor):
    """Whether (x, z) lies on a room's floor (its corners), or anywhere when there is none."""
    return floor is None or bool(np.all(goal >= floor[0]) and np.all(goal <= floor[1]))


def walk_path(scenes, eye, view, room, seed):
    """A shot's walk from its start eye: a walkable path of eyes (camera_paths.leg), or None where none is. In a room
    (`room`: the scene record's `floor`, its (x, z) corners) the walk keeps to its floor: a stage may run a room's floor
    on past its walls (a flat with no ground of its own stands on y = 0 everywhere)."""
    floor = np.asarray(room, dtype=float) if room is not None else None
    reach = (PACE_OUTSIDE if floor is None else PACE_INSIDE) * SHOT_SECONDS
    for goal in walk_goals(eye, view["aim"], reach):
        if np.linalg.norm(goal - eye[[0, 2]]) < SHORTEST_WALK or not on_floor(goal, floor):
            continue
        end = camera_paths.eyes_over(scenes, [goal], camera_paths.EYE_HEIGHT, [eye[1]])[0]
        if not np.isfinite(end[1]) or abs(eye[1] - end[1]) > camera_paths.STEP_RISE:
            continue
        low = np.minimum(eye[[0, 2]], end[[0, 2]]) - WANDER
        high = np.maximum(eye[[0, 2]], end[[0, 2]]) + WANDER
        if floor is not None:
            low = np.maximum(low, np.minimum(floor[0], eye[[0, 2]]))
            high = np.minimum(high, np.maximum(floor[1], eye[[0, 2]]))
        path = camera_paths.leg(scenes, eye, end, (*low, *high), seed)
        if path is not None:
            return path
    return None


def shot_move(scenes, view, room, seed):
    """How a shot moves from its camera: {"camera", "move": "walk", "path"} where a walk is clear (in a room, on its
    `floor`), else {"camera", "move": "stand", "eye", "level"}: on the floor under the camera, its view held near level,
    or at the camera's own eye looking where it looks when it stands on no floor of the stage."""
    eye = start_eye(scenes, view)
    path = walk_path(scenes, eye, view, room, seed) if eye is not None else None
    if path is not None:
        return {"camera": view["name"], "move": "walk", "path": [point.tolist() for point in path]}
    if eye is None:
        return {"camera": view["name"], "move": "stand", "eye": view["eye"], "level": False}
    return {"camera": view["name"], "move": "stand", "eye": eye.tolist(), "level": True}


def walked_frames(path, view, number, frames):
    """A walk's frames: eyes along the path, eased at both ends, each looking at the camera's aim held near level."""
    corners = np.array(path)
    along = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(corners, axis=0), axis=1))])
    spots = eased(frames) * along[-1]
    eyes = np.column_stack([np.interp(spots, along, corners[:, axis]) for axis in range(3)])
    return [renders.looking(f"shot{number}-{frame:03d}", eye, levelled(eye, view["aim"]),
                            fov=float(view.get("fov", 75.0)), look_only=True) for frame, eye in enumerate(eyes)]


def standing_frames(eye, aim, view, number, frames):
    """A standing shot's frames: the eye still, the view eased through a turn of TURN_DEGREES about the aim (each shot
    turns the other way from the one before)."""
    eye = np.asarray(eye, dtype=float)
    side = 1.0 if number % 2 == 0 else -1.0
    return [renders.looking(f"shot{number}-{frame:03d}", eye, turned(eye, aim, side * TURN_DEGREES * (share - 0.5)),
                            fov=float(view.get("fov", 75.0)), look_only=True)
            for frame, share in enumerate(eased(frames))]


def shot_frames(move, view, number, frames):
    """One shot's frames from its camera, as its move says."""
    if move["move"] == "walk":
        return walked_frames(move["path"], view, number, frames)
    eye = np.asarray(move["eye"], dtype=float)
    aim = levelled(eye, view["aim"]) if move["level"] else np.asarray(view["aim"], dtype=float)
    return standing_frames(eye, aim, view, number, frames)


def place_moves(record, scenes, cameras):
    """Each camera's shot move (shot_move), seeded by its place in the film."""
    room = record.get("floor") if record.get("inside") else None
    return [shot_move(scenes, view, room, seed=number) for number, view in enumerate(cameras)]


def place_views(cameras, moves, time_rate):
    """Every frame of a film as usd_views views, its shots one after the other, at consecutive moments of the stage's
    time."""
    frames = round(SHOT_SECONDS * RATE)
    views = [view for number, (camera, move) in enumerate(zip(cameras, moves))
             for view in shot_frames(move, camera, number, frames)]
    return [dict(view, frame=round(index * time_rate / RATE)) for index, view in enumerate(views)]


def stage_of(stages, place):
    return stages / place / f"{place}.usda"


def chosen(given):
    """A film as given to plan, `place`, `place=camera,camera` or `film@place=camera,...` (a film of its own from a
    place's stage and record: the Mars camp's grounds from the camp's outside cameras): (film, place, the cameras
    named)."""
    film, _, names = given.partition("=")
    film, _, place = film.partition("@")
    return film, place or film, [name for name in names.split(",") if name]


def plan(out, stages, places, jobs_each=1):
    """Each place's views and its cloud jobs (`jobs_each` a place, its frames dealt out between them in turn, so each
    job has as many); the job files."""
    (out / "views").mkdir(parents=True, exist_ok=True)
    (out / "jobs").mkdir(parents=True, exist_ok=True)
    written = []
    for given in places:
        film, place, names = chosen(given)
        stage = stage_of(stages, place)
        record = scene_record.record(place)
        if not record or not record.get("views"):
            raise SystemExit(f"{place} has no scene record with cameras (data/scene/{place}.json)")
        cameras = shot_cameras(record, names=names)
        moves = place_moves(record, camera_paths.place_scenes(stage), cameras)
        views = place_views(cameras, moves, renders.stage_rate(stage))
        kept = [{"camera": move["camera"], "move": move["move"]} for move in moves]
        (out / "views" / f"{film}.json").write_text(json.dumps({"size": list(SIZE), "views": views, "moves": kept,
                                                                  "stage": str(stage)}, indent=1))
        frames = out / "frames" / film
        shown = [stages / name for name in renders.places_shown(record) if name != place]
        jobs = min(jobs_each, len(views))
        for part in range(jobs):
            share = views[part::jobs]
            path = out / "views" / f"{film}-{part}.json"
            path.write_text(json.dumps({"size": list(SIZE), "views": share}, indent=1))
            job = {"script": str((REPO / "tools/blender/inside/usd_views.py").relative_to(REPO)),
                   "args": [str(stage), str(path), str(frames)],
                   "inputs": [str(stage.parent), *map(str, shown), str(path)], "outputs": [str(frames)],
                   "minutes": round(10 + FRAME_MINUTES * len(share))}
            (out / "jobs" / f"{film}-{part}.json").write_text(json.dumps(job, indent=1))
            written.append(out / "jobs" / f"{film}-{part}.json")
        walked = sum(move["move"] == "walk" for move in moves)
        print(f"{film}: {len(views)} frames in {jobs} jobs, {walked} of {len(moves)} shots walk")
    return written


def title_card(name, path):
    """A plain card: the place's name, white on black."""
    card = Image.new("RGB", SIZE, (0, 0, 0))
    draw = ImageDraw.Draw(card)
    font = ImageFont.truetype(str(FONT), SIZE[1] // 13)
    width = draw.textlength(name, font=font)
    draw.text(((SIZE[0] - width) / 2, SIZE[1] / 2 - SIZE[1] // 22), name, font=font, fill=(235, 235, 235))
    card.save(path)


def ffmpeg(*arguments):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, arguments)], check=True)


def encode(out):
    return ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-r", str(RATE), "-movflags", "+faststart", out]


def has_sound(clip):
    """Whether a clip carries a sound track."""
    found = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of",
                            "csv=p=0", str(clip)], capture_output=True, text=True, check=True).stdout
    return bool(found.strip())


def joined(clips, seconds, out):
    """Clips of the given lengths joined by cross-fades of FADE_SECONDS, their sound too when every clip has some."""
    if len(clips) == 1:
        shutil.copy(clips[0], out)
        return
    voiced = all(has_sound(clip) for clip in clips)
    graph, previous, sound, offset = [], "[0:v]", "[0:a]", 0.0
    for number in range(1, len(clips)):
        offset += seconds[number - 1] - FADE_SECONDS
        label = f"[v{number}]"
        graph.append(f"{previous}[{number}:v]xfade=transition=fade:duration={FADE_SECONDS}:offset={offset:.3f}{label}")
        previous = label
        if voiced:
            graph.append(f"{sound}[{number}:a]acrossfade=d={FADE_SECONDS}[a{number}]")
            sound = f"[a{number}]"
    inputs = [part for clip in clips for part in ("-i", clip)]
    mapped = ["-map", previous] + (["-map", sound, "-c:a", "aac", "-b:a", "160k"] if voiced else [])
    ffmpeg(*inputs, "-filter_complex", ";".join(graph), *mapped, *encode(out))


def named(given):
    """A place as given on the command line, `place` or `place:Title`: (place, its card's title)."""
    place, _, title = given.partition(":")
    return place, title or place.replace("_", " ").capitalize()


def cut_place(out, place, title):
    """A place's video: its title card, then its shots, joined by cross-fades; its length in seconds."""
    frames = out / "frames" / place
    planned = json.loads((out / "views" / f"{place}.json").read_text())
    views = planned["views"]
    missing = [view["name"] for view in views if not (frames / f"{view['name']}-look.png").exists()]
    if missing:
        raise SystemExit(f"{place}: {len(missing)} of {len(views)} frames not rendered (first {missing[0]}); "
                         "render its jobs again")
    stage = planned.get("stage")
    voiced = bool(stage) and (pathlib.Path(stage).parent / "layers/sound.usda").exists()
    shots = sorted({view["name"].split("-")[0] for view in views}, key=lambda name: int(name[4:]))
    work = out / "clips" / place
    work.mkdir(parents=True, exist_ok=True)
    title_card(title, work / "title.png")
    silence = ["-f", "lavfi", "-t", TITLE_SECONDS, "-i", f"anullsrc=r={SAMPLE_RATE}:cl=stereo", "-c:a", "aac",
               "-shortest"] if voiced else []
    ffmpeg("-loop", "1", "-t", TITLE_SECONDS, "-i", work / "title.png", *silence, *encode(work / "title.mp4"))
    clips, seconds = [work / "title.mp4"], [TITLE_SECONDS]
    for shot in shots:
        ffmpeg("-framerate", RATE, "-i", frames / f"{shot}-%03d-look.png", *encode(work / f"{shot}.mp4"))
        if voiced:
            renders.heard(stage, [view for view in views if view["name"].split("-")[0] == shot], RATE,
                          work / f"{shot}.mp4")
        clips.append(work / f"{shot}.mp4")
        seconds.append(SHOT_SECONDS)
    video = out / "videos" / f"{place}.mp4"
    video.parent.mkdir(parents=True, exist_ok=True)
    joined(clips, seconds, video)
    return sum(seconds) - FADE_SECONDS * (len(clips) - 1)


def cut(out, places):
    """Every place's video and, for more than one, the world's in the order given."""
    places = [named(given) for given in places]
    lengths = [cut_place(out, place, title) for place, title in places]
    if len(places) > 1:
        joined([out / "videos" / f"{place}.mp4" for place, _ in places], lengths, out / "videos" / "world.mp4")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("step", choices=["plan", "cut"])
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("places", nargs="+")
    parser.add_argument("--stages", type=pathlib.Path, help="plan: the folder holding each place's stage folder")
    parser.add_argument("--jobs-each", type=int, default=1, help="plan: cloud jobs a place, its frames dealt out")
    options = parser.parse_args()
    if options.step == "plan":
        if not options.stages:
            raise SystemExit("plan needs --stages")
        plan(options.out.resolve(), options.stages.resolve(), options.places, options.jobs_each)
    else:
        cut(options.out.resolve(), options.places)


if __name__ == "__main__":
    main()
