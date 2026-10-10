"""A world's demo: a walk-through video of each place from its OpenUSD stage, and one video of the world in story order.

    .venv/bin/python tools/review/demo.py plan <out> --stages <stage root> [--jobs-each N] [--keep <earlier out>] \
        <film>[@<place>][=<camera>,...] [...]
    ~/.farm-factory-props/env/bin/python tools/props/cloud/blender_cloud.py <out>/jobs/*.json --who <session> \
        --classes gpu-24gb,gpu-48gb,gpu-80gb --detach
    .venv/bin/python tools/review/demo.py cut <out> <film>[:<Title>] [...]
    .venv/bin/python tools/review/film_checks.py films <out> <film> [...]

`plan` writes, per film, the views of its shots (`<out>/views/<film>.json`) and its cloud Blender jobs that render them
with the review's scene script (`../blender/inside/usd_views.py`, Cycles on a card), its stage folder and every place
its stage shows as inputs. A film is a place's, or one of its own from a place's stage (`film@place`: the Mars camp's
grounds from the camp's outside cameras). A shot starts at one of the scene record's own cameras (the player's spots;
the cameras named, else a few spread over the record, none looking up at a roof) and walks from there at the player's
eye height, as the game is seen: a walk-through path (tools/usd/camera_paths.py: RRT* on the stage's own floors, every
point of it the clearance from walls, objects and the place's people, a person who walks swept over the shot's
moments; in a room, on its recorded floor) from the camera's spot towards what it looks at, stopping well short of it,
while the view keeps on that thing, held near level. Where no clear path goes forward the walk goes sideways, still
looking at it; where none goes either way, or the camera stands on no floor of the stage, the eye stands and the view
turns a few degrees. A shot starts, walking or standing, where it keeps the clearance too: at the camera's spot, else
the nearest clear spot within MOVE_MOST of it; with none, the shot is left out. The frames follow the stage's own
time, one shot after the other, so its characters move through the whole video. The views file keeps every shot's
move (its path or spot and its seed) and the planner's commit, so a film can be planned again as it was: with
`--keep`, a shot of the earlier take whose every frame stands clear (measured at the frame's own moment) is kept as it
was, its looks linked from that take's frames and only its ink lines rendered; the rest is planned and rendered anew.

Every frame is drawn with the game's ink lines over it, as the game draws them over every frame and the review's
views draw them (usd_views.py's `ink`); the game's night glow is drawn where the stage carries it (its sky's glow),
and what the stage does not carry the scene record lists as game only. `cut` makes each film's video from its inked
frames (the shots joined by short cross-fades, opened by a title card with its plain name, given as `film:Title`)
and, given more than one, the world's video with the films in the order given. A film whose stage has a sound layer
(tools/usd/sound.py) is heard too: each shot's sound is what its camera hears along its frames (sound.soundtrack),
cross-faded with the pictures. `film_checks.py` measures the films; `showcase.py` cuts the showcase from them.

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
# How far a shot's camera may be moved to stand clear of walls, objects and people (camera_paths.CLEARANCE), tried in
# rings this far apart at this many headings each (metres).
MOVE_MOST = 1.5
MOVE_STEP = 0.1
MOVE_HEADINGS = 16
# While a shot's move is planned its people stand where they are at every this many of its frames and its last, so a
# walking person's box is swept over the shot (the checks measure every frame).
PEOPLE_EVERY = 6
# Minutes a frame's ink lines alone take on a 24 GB card (a one-sample pass render and the ink rule), the import aside
# (2026-10-10: 9 to 17 s a frame; a hub frame with its look and its ink took about 0.95 min, look and lines together).
LINES_MINUTES = 0.25
# Minutes a frame takes on a 24 GB card, the import aside (the hub at 1920x1080 on an L4, 2026-10-10: 42 s; at
# 1280x720 the square and the hub took 14 to 20 s).
FRAME_MINUTES = 0.7
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


def stands_clear(scenes, eye):
    """Whether an eye keeps the clearance from the place's meshes and its people (camera_paths.stands_clear)."""
    return bool(camera_paths.stands_clear(*camera_paths.clearances(scenes, eye))[0])


def clear_spot(scenes, eye, floored):
    """The eye itself when it stands clear, else the nearest spot round it within MOVE_MOST that does and that a
    straight line from the eye reaches through no mesh (on the floor under it, no more than a step up or down, where
    `floored`; at the eye's own height where not); None when there is none."""
    eye = np.asarray(eye, dtype=float)
    if stands_clear(scenes, eye):
        return eye
    headings = np.linspace(0.0, 2.0 * np.pi, MOVE_HEADINGS, endpoint=False)
    for radius in np.arange(MOVE_STEP, MOVE_MOST + 1e-9, MOVE_STEP):
        flat = eye[[0, 2]] + radius * np.column_stack([np.cos(headings), np.sin(headings)])
        if floored:
            spots = camera_paths.eyes_over(scenes, flat, camera_paths.EYE_HEIGHT, np.full(len(flat), eye[1]))
            good = np.isfinite(spots[:, 1]) & (np.abs(spots[:, 1] - eye[1]) <= camera_paths.STEP_RISE)
        else:
            spots = np.column_stack([flat[:, 0], np.full(len(flat), eye[1]), flat[:, 1]])
            good = np.ones(len(flat), dtype=bool)
        for spot in spots[good]:
            if seen_from(scenes, eye, spot) and stands_clear(scenes, spot):
                return spot
    return None


def seen_from(scenes, eye, spot):
    """Whether a straight line from the eye to the spot passes through no mesh of the place (people aside: an eye may
    start inside a person's box)."""
    span = spot - eye
    length = float(np.linalg.norm(span))
    return camera_paths.first_hits(scenes["still"], eye[None], (span / max(length, 1e-9))[None])[0] > length


def shot_move(scenes, view, room, seed):
    """How a shot moves from its camera: {"camera", "move": "walk", "path"} where a walk is clear (in a room, on its
    `floor`), else {"camera", "move": "stand", "eye", "level"}: on the floor under the camera, its view held near level,
    or at the camera's own eye looking where it looks when it stands on no floor of the stage. Its start stands clear
    of walls, objects and people (clear_spot), `moved` metres from the camera's own spot; None when no spot near the
    camera does."""
    eye = start_eye(scenes, view)
    floored = eye is not None
    spot = clear_spot(scenes, eye if floored else view["eye"], floored)
    if spot is None:
        return None
    moved = round(float(np.linalg.norm((spot - (eye if floored else np.asarray(view["eye"])))[[0, 2]])), 3)
    found = {"camera": view["name"], "seed": seed, "moved": moved}
    path = walk_path(scenes, spot, view, room, seed) if floored else None
    if path is not None:
        return dict(found, move="walk", path=[[round(float(value), 4) for value in point] for point in path])
    return dict(found, move="stand", eye=[round(float(value), 4) for value in spot], level=floored)


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


def shot_times(number, time_rate):
    """The stage's time codes of a shot's frames, the film's shots one after the other at consecutive moments."""
    frames = round(SHOT_SECONDS * RATE)
    return [round((number * frames + index) * time_rate / RATE) for index in range(frames)]


def people_over(stage, time_rate):
    """For a shot's number, the place's people's boxes at every PEOPLE_EVERY of its frames and its last."""
    def boxes(number):
        times = shot_times(number, time_rate)
        return camera_paths.people_boxes(stage, times[::PEOPLE_EVERY] + times[-1:])
    return boxes


def kept_shots(keep, film, scenes, stage):
    """An earlier take's shots of this film (<keep>/views/<film>.json) whose eye stands clear of the place's meshes and
    of its people at every frame: {number: (its move, its views)}; none when there is no earlier take."""
    path = keep / "views" / f"{film}.json" if keep else None
    if path is None or not path.exists():
        return {}
    earlier = json.loads(path.read_text())
    views = earlier["views"]
    clear = camera_paths.stands_clear(*camera_paths.frame_clearances(scenes, stage, views))
    found = {}
    for number, move in enumerate(earlier["moves"]):
        shot = [index for index, view in enumerate(views) if shot_of(view) == f"shot{number}"]
        if shot and clear[shot].all():
            found[number] = (dict(move, kept=str(keep)), [views[index] for index in shot])
    return found


def shot_of(view):
    """The shot a frame's view belongs to (`shot<n>`, from its name `shot<n>-<frame>`)."""
    return view["name"].split("-")[0]


def stage_of(stages, place):
    return stages / place / f"{place}.usda"


def chosen(given):
    """A film as given to plan, `place`, `place=camera,camera` or `film@place=camera,...` (a film of its own from a
    place's stage and record: the Mars camp's grounds from the camp's outside cameras): (film, place, the cameras
    named)."""
    film, _, names = given.partition("=")
    film, _, place = film.partition("@")
    return film, place or film, [name for name in names.split(",") if name]


def film_shots(record, stage, scenes, cameras, earlier):
    """A film's shots: an earlier take's where it stands clear (`earlier`, kept_shots) and its camera is the same,
    else a new move from the camera: the moves, and each shot's views at its moments of the stage's time with
    whether it is new."""
    rate = renders.stage_rate(stage)
    people_at = people_over(stage, rate)
    room = record.get("floor") if record.get("inside") else None
    frames = round(SHOT_SECONDS * RATE)
    moves, shots = [], []
    for view in cameras:
        number = len(moves)
        if number in earlier and earlier[number][0]["camera"] == view["name"]:
            moves.append(earlier[number][0])
            shots.append((earlier[number][1], False))
            continue
        move = shot_move(camera_paths.with_people(scenes, people_at(number)), view, room, seed=number)
        if move is None:
            print(f"{view['name']}: no spot within {MOVE_MOST} m of the camera stands clear; the shot is left out")
            continue
        moves.append(move)
        timed = [dict(frame, frame=time) for frame, time in
                 zip(shot_frames(move, view, number, frames), shot_times(number, rate))]
        shots.append((timed, True))
    return moves, shots


def planned_with():
    """The commit the planner ran from, so a re-plan can be run from the same code."""
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True,
                          check=True).stdout.strip()


def linked_frames(keep, out, film, views):
    """A kept shot's looks, linked from the earlier take's frames into this one's."""
    frames = out / "frames" / film
    frames.mkdir(parents=True, exist_ok=True)
    for view in views:
        link = frames / f"{view['name']}-look.png"
        if not link.exists():
            link.symlink_to(keep / "frames" / film / f"{view['name']}-look.png")


def film_jobs(out, film, stage, shown, views, kind, jobs_each):
    """Cloud jobs for a film's frames of one kind ("look": rendered with their ink; "lines": the ink lines alone over
    looks rendered before), `jobs_each` at most, the frames dealt out between them in turn: the job files."""
    flags, minutes = (({"ink": True}, FRAME_MINUTES + LINES_MINUTES) if kind == "look"
                      else ({"lines_only": True}, LINES_MINUTES))
    frames = out / "frames" / film
    count = min(jobs_each, len(views))
    written = []
    for part in range(count):
        share = [dict(view, **flags) for view in views[part::count]]
        name = f"{film}-{part}" if kind == "look" else f"{film}-lines-{part}"
        path = out / "views" / f"{name}.json"
        path.write_text(json.dumps({"size": list(SIZE), "views": share}, indent=1))
        job = {"script": str((REPO / "tools/blender/inside/usd_views.py").relative_to(REPO)),
               "args": [str(stage), str(path), str(frames)],
               "inputs": [str(stage.parent), *map(str, shown), str(path)], "outputs": [str(frames)],
               "minutes": round(10 + minutes * len(share))}
        (out / "jobs" / f"{name}.json").write_text(json.dumps(job, indent=1))
        written.append(out / "jobs" / f"{name}.json")
    return written


def plan(out, stages, places, jobs_each=1, keep=None):
    """Each place's views and its cloud jobs (`jobs_each` a place for its new frames and as many for the ink lines of
    the frames it keeps from the earlier take in `keep`); the job files. The views file records every shot's move
    (its path or its spot, its seed, how far its start moved, the take it was kept from) and the planner's commit."""
    (out / "views").mkdir(parents=True, exist_ok=True)
    (out / "jobs").mkdir(parents=True, exist_ok=True)
    written = []
    for given in places:
        film, place, names = chosen(given)
        stage = stage_of(stages, place)
        record = scene_record.record(place)
        if not record or not record.get("views"):
            raise SystemExit(f"{place} has no scene record with cameras (data/scene/{place}.json)")
        scenes = camera_paths.place_scenes(stage)
        moves, shots = film_shots(record, stage, scenes, shot_cameras(record, names=names),
                                  kept_shots(keep, film, scenes, stage))
        views = [view for shot, _ in shots for view in shot]
        new = [view for shot, fresh in shots if fresh for view in shot]
        old = [view for shot, fresh in shots if not fresh for view in shot]
        (out / "views" / f"{film}.json").write_text(json.dumps(
            {"size": list(SIZE), "views": views, "moves": moves, "stage": str(stage), "planned_with": planned_with()},
            indent=1))
        if old and keep.resolve() != out.resolve():
            linked_frames(keep, out, film, old)
        shown = [stages / name for name in renders.places_shown(record) if name != place]
        written += film_jobs(out, film, stage, shown, new, "look", jobs_each) if new else []
        written += film_jobs(out, film, stage, shown, old, "lines", jobs_each) if old else []
        walked = sum(move["move"] == "walk" for move in moves)
        print(f"{film}: {len(views)} frames, {len(new)} new and {len(old)} kept, {walked} of {len(moves)} shots walk")
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


def inked(frames, name):
    """A frame with the game's ink lines over it, as the game draws them over every frame: <name>-ink.png, laid here
    from its look and its lines (usd_views.py's <name>-lines.png) when the cloud drew the lines alone."""
    ink = frames / f"{name}-ink.png"
    if ink.exists():
        return ink
    with Image.open(frames / f"{name}-look.png") as look, Image.open(frames / f"{name}-lines.png") as lines:
        Image.alpha_composite(look.convert("RGBA"), lines.convert("RGBA")).convert("RGB").save(ink)
    return ink


def cut_place(out, place, title):
    """A place's video: its title card, then its shots drawn with their ink, joined by cross-fades; its length in
    seconds."""
    frames = out / "frames" / place
    planned = json.loads((out / "views" / f"{place}.json").read_text())
    views = planned["views"]
    missing = [view["name"] for view in views if not (frames / f"{view['name']}-look.png").exists()
               or not any((frames / f"{view['name']}-{kind}.png").exists() for kind in ("ink", "lines"))]
    if missing:
        raise SystemExit(f"{place}: {len(missing)} of {len(views)} frames not rendered with their ink (first "
                         f"{missing[0]}); render its jobs again")
    for view in views:
        inked(frames, view["name"])
    stage = planned.get("stage")
    voiced = bool(stage) and (pathlib.Path(stage).parent / "layers/sound.usda").exists()
    shots = sorted({shot_of(view) for view in views}, key=lambda name: int(name[4:]))
    work = out / "clips" / place
    work.mkdir(parents=True, exist_ok=True)
    title_card(title, work / "title.png")
    silence = ["-f", "lavfi", "-t", TITLE_SECONDS, "-i", f"anullsrc=r={SAMPLE_RATE}:cl=stereo", "-c:a", "aac",
               "-shortest"] if voiced else []
    ffmpeg("-loop", "1", "-t", TITLE_SECONDS, "-i", work / "title.png", *silence, *encode(work / "title.mp4"))
    clips, seconds = [work / "title.mp4"], [TITLE_SECONDS]
    for shot in shots:
        ffmpeg("-framerate", RATE, "-i", frames / f"{shot}-%03d-ink.png", *encode(work / f"{shot}.mp4"))
        if voiced:
            renders.heard(stage, [view for view in views if shot_of(view) == shot], RATE,
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
    parser.add_argument("--keep", type=pathlib.Path, help="plan: an earlier take whose clear shots are kept")
    options = parser.parse_args()
    if options.step == "plan":
        if not options.stages:
            raise SystemExit("plan needs --stages")
        plan(options.out.resolve(), options.stages.resolve(), options.places, options.jobs_each,
             options.keep.resolve() if options.keep else None)
    else:
        cut(options.out.resolve(), options.places)


if __name__ == "__main__":
    main()
