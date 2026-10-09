"""A world's demo: a walk-through video of each place from its OpenUSD stage, and one video of the world in story order.

    .venv/bin/python tools/review/demo.py plan <out> --stages <stage root> [--jobs-each N] <place>[=<camera>,...] [...]
    ~/.farm-factory-props/env/bin/python tools/props/cloud/blender_cloud.py <out>/jobs/*.json --who <session> \
        --classes gpu-24gb,gpu-48gb,gpu-80gb
    .venv/bin/python tools/review/demo.py cut <out> <place>[:<Title>] [...]

`plan` writes, per place, the views of its shots (`<out>/views/<place>.json`) and one cloud Blender job that renders
them with the review's scene script (`../blender/inside/usd_views.py`, Cycles on a card), its stage folder and every
place its stage shows as inputs. A shot starts at one of the scene record's own cameras (the player's spots, inside a
room at standing height; the cameras named, else a few spread over the record, none looking up at a roof) and moves slowly from there: the eye goes a little
way towards what it looks at while the view turns a few degrees, so no shot passes through a wall. The frames follow
the stage's own time, one shot after the other, so its characters move through the whole video. `cut` makes each
place's video from its frames (the shots joined by short cross-fades, opened by a title card with the place's plain
name, given as `place:Title`) and, given more than one place, the world's video with the places in the order given.

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
import scene as scene_record  # noqa: E402  (tools/usd)

SIZE = (1280, 720)
RATE = 24
SHOT_SECONDS = 3.5
SHOTS = 4
FADE_SECONDS = 0.5
TITLE_SECONDS = 2.0
# How far a shot's eye moves towards its aim (a share of the distance, at most the cap) and how far the view turns.
DOLLY_SHARE = 0.12
DOLLY_CAP_INSIDE = 0.8
DOLLY_CAP_OUTSIDE = 6.0
TURN_DEGREES = 10.0
# A camera this steep (its aim over its eye by more than this share of the distance) looks at a roof: not a shot.
STEEPEST = 0.6
# Minutes a frame takes on a 24 GB card, the import aside (the square and the hub on an L4, 2026-10-09: 14 to 20 s).
FRAME_MINUTES = 0.3
FONT = pathlib.Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


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


def shot_frames(view, number, frames, inside):
    """One shot's frames from a camera: the eye eased towards the aim, the view eased through its turn (each shot
    turns the other way from the one before)."""
    eye, aim = np.asarray(view["eye"], dtype=float), np.asarray(view["aim"], dtype=float)
    towards = aim - eye
    reach = min(DOLLY_SHARE * np.linalg.norm(towards), DOLLY_CAP_INSIDE if inside else DOLLY_CAP_OUTSIDE)
    step = towards / np.linalg.norm(towards) * reach
    side = 1.0 if number % 2 == 0 else -1.0
    views = []
    for frame in range(frames):
        share = frame / max(frames - 1, 1)
        eased = 0.5 - 0.5 * math.cos(math.pi * share)
        moved = eye + step * eased
        looked = turned(moved, aim + step * eased, side * TURN_DEGREES * (eased - 0.5))
        views.append(renders.looking(f"shot{number}-{frame:03d}", moved, looked, fov=float(view.get("fov", 75.0)),
                                     look_only=True))
    return views


def place_views(record, time_rate, names=()):
    """Every frame of a place's video as usd_views views, at consecutive moments of the stage's time."""
    frames = round(SHOT_SECONDS * RATE)
    views = []
    for number, view in enumerate(shot_cameras(record, names=names)):
        views += shot_frames(view, number, frames, bool(record.get("inside")))
    return [dict(view, frame=round(index * time_rate / RATE)) for index, view in enumerate(views)]


def stage_of(stages, place):
    return stages / place / f"{place}.usda"


def chosen(given):
    """A place as given to plan, `place` or `place=camera,camera`: (place, the cameras named)."""
    place, _, names = given.partition("=")
    return place, [name for name in names.split(",") if name]


def plan(out, stages, places, jobs_each=1):
    """Each place's views and its cloud jobs (`jobs_each` a place, its shots shared between them); the job files."""
    (out / "views").mkdir(parents=True, exist_ok=True)
    (out / "jobs").mkdir(parents=True, exist_ok=True)
    written = []
    for given in places:
        place, names = chosen(given)
        record = scene_record.record(place)
        if not record or not record.get("views"):
            raise SystemExit(f"{place} has no scene record with cameras (data/scene/{place}.json)")
        stage = stage_of(stages, place)
        views = place_views(record, renders.stage_rate(stage), names)
        (out / "views" / f"{place}.json").write_text(json.dumps({"size": list(SIZE), "views": views}, indent=1))
        frames = out / "frames" / place
        shown = [stages / name for name in renders.places_shown(record) if name != place]
        shots = sorted({view["name"].split("-")[0] for view in views}, key=lambda name: int(name[4:]))
        for part in range(min(jobs_each, len(shots))):
            mine = set(shots[part::jobs_each])
            share = [view for view in views if view["name"].split("-")[0] in mine]
            path = out / "views" / f"{place}-{part}.json"
            path.write_text(json.dumps({"size": list(SIZE), "views": share}, indent=1))
            job = {"script": str((REPO / "tools/blender/inside/usd_views.py").relative_to(REPO)),
                   "args": [str(stage), str(path), str(frames)],
                   "inputs": [str(stage.parent), *map(str, shown), str(path)], "outputs": [str(frames)],
                   "minutes": round(10 + FRAME_MINUTES * len(share))}
            (out / "jobs" / f"{place}-{part}.json").write_text(json.dumps(job, indent=1))
            written.append(out / "jobs" / f"{place}-{part}.json")
        print(f"{place}: {len(views)} frames in {min(jobs_each, len(shots))} jobs")
    return written


def title_card(name, path):
    """A plain card: the place's name, white on black."""
    card = Image.new("RGB", SIZE, (0, 0, 0))
    draw = ImageDraw.Draw(card)
    font = ImageFont.truetype(str(FONT), 54)
    width = draw.textlength(name, font=font)
    draw.text(((SIZE[0] - width) / 2, SIZE[1] / 2 - 32), name, font=font, fill=(235, 235, 235))
    card.save(path)


def ffmpeg(*arguments):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, arguments)], check=True)


def encode(out):
    return ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-r", str(RATE), "-movflags", "+faststart", out]


def joined(clips, seconds, out):
    """Clips of the given lengths joined by cross-fades of FADE_SECONDS."""
    if len(clips) == 1:
        shutil.copy(clips[0], out)
        return
    graph, previous, offset = [], "[0:v]", 0.0
    for number in range(1, len(clips)):
        offset += seconds[number - 1] - FADE_SECONDS
        label = f"[v{number}]"
        graph.append(f"{previous}[{number}:v]xfade=transition=fade:duration={FADE_SECONDS}:offset={offset:.3f}{label}")
        previous = label
    inputs = [part for clip in clips for part in ("-i", clip)]
    ffmpeg(*inputs, "-filter_complex", ";".join(graph), "-map", previous, *encode(out))


def named(given):
    """A place as given on the command line, `place` or `place:Title`: (place, its card's title)."""
    place, _, title = given.partition(":")
    return place, title or place.replace("_", " ").capitalize()


def cut_place(out, place, title):
    """A place's video: its title card, then its shots, joined by cross-fades; its length in seconds."""
    frames = out / "frames" / place
    views = json.loads((out / "views" / f"{place}.json").read_text())["views"]
    shots = sorted({view["name"].split("-")[0] for view in views}, key=lambda name: int(name[4:]))
    work = out / "clips" / place
    work.mkdir(parents=True, exist_ok=True)
    title_card(title, work / "title.png")
    ffmpeg("-loop", "1", "-t", TITLE_SECONDS, "-i", work / "title.png", *encode(work / "title.mp4"))
    clips, seconds = [work / "title.mp4"], [TITLE_SECONDS]
    for shot in shots:
        ffmpeg("-framerate", RATE, "-i", frames / f"{shot}-%03d-look.png", *encode(work / f"{shot}.mp4"))
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
    parser.add_argument("--jobs-each", type=int, default=1, help="plan: cloud jobs a place, its shots shared out")
    options = parser.parse_args()
    if options.step == "plan":
        if not options.stages:
            raise SystemExit("plan needs --stages")
        plan(options.out.resolve(), options.stages.resolve(), options.places, options.jobs_each)
    else:
        cut(options.out.resolve(), options.places)


if __name__ == "__main__":
    main()
