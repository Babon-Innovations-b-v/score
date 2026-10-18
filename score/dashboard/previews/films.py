"""Pictures cut from a place's accepted film on the store's machine, free and light (one ffmpeg call a frame, no
render): the middle frame as a JPEG for the board's tile, and named things ringed in the frame that shows them best,
each thing's point carried through that frame's camera (the film's views.json: eye, aim, up, `fov` across the width,
as the film's own frames were drawn)."""
import json
import math
import pathlib
import shutil
import subprocess
import threading

import numpy as np
from PIL import Image, ImageDraw, ImageFont

QUALITY = 3  # ffmpeg's JPEG scale, 2 best to 31 worst
EDGE = 0.08  # a point this near the frame's edge is not shown by it
NEAREST = 0.4  # metres: a point nearer the camera than this is not shown
THING = 1.2  # metres: the size a named thing is taken to have, for its ring
CROP_LEAST = 360
LARGEST = 720
RING = (232, 96, 60)
_one_at_a_time = threading.Lock()


def tool(name):
    """ffmpeg's or ffprobe's path; an error that says so when it is not installed."""
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"{name} is not installed: the film's pictures cannot be cut")
    return found


def probe(film):
    """(frames, frames a second) of a film's first video stream; None when ffprobe cannot read it."""
    done = subprocess.run([tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-count_packets",
                           "-show_entries", "stream=r_frame_rate,nb_read_packets", "-of", "json", str(film)],
                          capture_output=True, text=True)
    streams = json.loads(done.stdout or "{}").get("streams") if done.returncode == 0 else None
    if not streams:
        return None
    above, _, below = streams[0].get("r_frame_rate", "24/1").partition("/")
    rate = float(above) / float(below or 1) if float(below or 1) else 24.0
    return int(streams[0].get("nb_read_packets") or 0), rate


def frame_picture(film, frame, rate, destination):
    """The film's frame number `frame` as a JPEG at `destination`, written once; the path, or None when ffmpeg
    cannot read it."""
    destination = pathlib.Path(destination)
    with _one_at_a_time:
        return destination if destination.is_file() else cut_frame(film, frame, rate, destination)


def cut_frame(film, frame, rate, destination):
    """ffmpeg's cut of one frame into `destination`; the path, or None when ffmpeg cannot read the film."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.stem + ".partial.jpg")
    start = max(0.0, (frame - 0.25) / rate)  # just before the frame, so the first frame decoded is it
    done = subprocess.run([tool("ffmpeg"), "-v", "error", "-y", "-ss", f"{start:.4f}", "-i", str(film),
                           "-frames:v", "1", "-q:v", str(QUALITY), str(partial)], capture_output=True)
    if done.returncode != 0 or not partial.is_file():
        return None
    partial.replace(destination)
    return destination


def shot_frame(view_number, frames, views):
    """The film's frame that shows a view: the views are the shot's frames, after the title card that leads it."""
    return max(0, frames - len(views)) + view_number


def middle_frame(frames, views):
    """The film's frame the board shows: the middle of its shot, else of the whole film."""
    return shot_frame(len(views) // 2, frames, views) if views and frames >= len(views) else frames // 2


def middle_still(film, views_text, destination):
    """The film's middle frame (of its shot) as a JPEG at `destination`, written once; None when the film cannot be
    read."""
    destination = pathlib.Path(destination)
    if destination.is_file():
        return destination
    probed = probe(film)
    if not probed or not probed[0]:
        return None
    _, views = film_views(views_text)
    return frame_picture(film, middle_frame(probed[0], views), probed[1], destination)


def film_views(text):
    """(size, [view]) of a film's views.json; ((1280, 720), []) when it names none."""
    try:
        found = json.loads(text) if text else {}
    except ValueError:
        found = {}
    if not isinstance(found, dict):
        return (1280, 720), []
    return tuple(found.get("size") or (1280, 720)), [view for view in found.get("views") or [] if "eye" in view]


def projected(view, point, size):
    """(column, row, depth) of a world point in a view's picture; None when it is behind or too near the camera."""
    eye, aim = np.asarray(view["eye"], dtype=float), np.asarray(view["aim"], dtype=float)
    ahead = (aim - eye) / np.linalg.norm(aim - eye)
    right = np.cross(ahead, np.asarray(view.get("up") or (0.0, 1.0, 0.0), dtype=float))
    right /= np.linalg.norm(right)
    up = np.cross(right, ahead)
    offset = np.asarray(point, dtype=float) - eye
    depth = float(offset @ ahead)
    if depth < NEAREST:
        return None
    scale = (size[0] / 2) / math.tan(math.radians(view.get("fov", 70.0)) / 2)
    return size[0] / 2 + scale * float(offset @ right) / depth, size[1] / 2 - scale * float(offset @ up) / depth, depth


def in_frame(spot, size):
    column, row, _ = spot
    return (EDGE * size[0] <= column <= (1 - EDGE) * size[0]) and (EDGE * size[1] <= row <= (1 - EDGE) * size[1])


def best_view(views, points, size):
    """(view index, [(name, column, row, depth)]) of the frame that shows the most of the named points, nearest the
    middle of the film on a tie; None when no frame shows any."""
    best, chosen = None, None
    middle = len(views) // 2
    for number, view in enumerate(views):
        shown = []
        for name, point in points:
            spot = projected(view, point, size)
            if spot and in_frame(spot, size):
                shown.append((name, *spot))
        rank = (len(shown), -abs(number - middle))
        if shown and (best is None or rank > best):
            best, chosen = rank, (number, shown)
    return chosen


def ring_radius(depth, size, view):
    """The pixels a THING-metre thing spans at a depth, halved: its ring's radius."""
    scale = (size[0] / 2) / math.tan(math.radians(view.get("fov", 70.0)) / 2)
    return max(18.0, min(size[1] / 3, scale * THING / 2 / depth))


def crop_box(spots, size, label):
    """The box round every ringed spot and its name below it, a margin added, at least CROP_LEAST pixels each way,
    inside the frame."""
    left = min(column - radius for _, column, _, radius in spots) - label
    right = max(column + radius for _, column, _, radius in spots) + label
    top = min(row - radius for _, _, row, radius in spots) - label
    bottom = max(row + radius for _, _, row, radius in spots) + 2 * label
    across, down = span(left, right, size[0]), span(top, bottom, size[1])
    return across[0], down[0], across[1], down[1]


def span(low, high, most):
    """(start, end) of [low, high] widened to CROP_LEAST and kept inside [0, most]: (start, end) as ints."""
    wide = min(max(high - low, CROP_LEAST), most)
    middle = (low + high) / 2
    start = min(max(0.0, middle - wide / 2), most - wide)
    return int(start), int(start + wide)


def ringed(frame, spots, size, destination):
    """The frame cut round the spots [(name, column, row, radius)] (pixels of a `size` picture), each ringed and
    named; the path."""
    with Image.open(frame) as opened:
        image = opened.convert("RGB")
    scale = image.width / size[0]
    spots = [(name, column * scale, row * scale, radius * scale) for name, column, row, radius in spots]
    pen = ImageDraw.Draw(image)
    small = ImageFont.load_default(size=max(14, image.height // 40))
    for name, column, row, radius in spots:
        pen.ellipse((column - radius, row - radius, column + radius, row + radius), outline=RING,
                    width=max(3, image.height // 200))
        below = row + radius + 4
        at = below if below + 2 * small.size < image.height else row - radius - 2 * small.size
        pen.text((max(4, column - radius), at), name, fill=RING, font=small, stroke_width=2, stroke_fill=(20, 20, 20))
    image = image.crop(crop_box(spots, image.size, small.size * 2))
    image.thumbnail((LARGEST, LARGEST))
    destination = pathlib.Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, "JPEG", quality=85)
    return destination
