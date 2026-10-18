"""A finding's picture: the thing marked on the frame of the place's accepted film that shows it largest, cropped
round it (the film's own views.json gives each frame's camera; no render, no cloud).

    film = pictures.film(store, place)                   # None when the place has no accepted film
    view = pictures.best_view(film, box, visible)        # the frame showing the box largest, its camera seeing it
    pictures.draw(film, [(view, box, path)], folder)     # each crop written, marked

The film is the demo film (score/stages/demo_film): a title card, then the shot's frames, its views.json's views in
order, cross-faded in over the first FADE frames, so view n is the video's frame n + (frames - views). Whether the
camera sees the thing, not a wall in front of it, is `visible`'s (seen.py).
"""
import dataclasses
import subprocess

import numpy as np
from PIL import Image, ImageDraw

FADE = 12  # demo.py FADE_SECONDS at RATE: the first views are cross-faded from the title card
MOST_OF_FRAME = 0.6  # a box larger than this share of the frame is too close to show what it is
SHOWN = 0.5  # the least share of a box's picture that must be in the frame
CROP = (480, 300)  # the least crop round a box, in pixels, so the place round it shows
INK = (240, 60, 40)


@dataclasses.dataclass
class Film:
    output: str
    video: str
    size: tuple
    views: list
    offset: int  # the video's frame of view 0


def frame_count(video):
    """The number of frames of a video (ffprobe)."""
    said = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                           "stream=nb_read_packets", "-of", "csv=p=0", str(video)], capture_output=True, text=True,
                          check=True).stdout
    return int(said.strip().split(",")[0])


def film(store, place):
    """The place's accepted film with its views, or None."""
    output = store.accepted(f"demo-film@{place}")
    if not output:
        return None
    listing = store.listing(output)
    if "film.mp4" not in listing or "views.json" not in listing:
        return None
    planned = store.read_file(output, "views.json")
    video = str(store.objects.path(f"blobs/{listing['film.mp4']}"))
    views = planned.get("views", [])
    return Film(output=output, video=video, size=tuple(planned.get("size", (1280, 720))), views=views,
                offset=frame_count(video) - len(views))


def corners(box):
    """The eight corners of a box given as (low, high)."""
    low, high = np.asarray(box[0], dtype=float), np.asarray(box[1], dtype=float)
    return np.array([[(low, high)[pick >> axis & 1][axis] for axis in range(3)] for pick in range(8)])


def projected(view, points, size):
    """The points in the view's picture (pixels), or None when any is behind the camera. `fov` is the angle across
    the picture."""
    eye, aim, up = (np.asarray(view[key], dtype=float) for key in ("eye", "aim", "up"))
    forward = (aim - eye) / np.linalg.norm(aim - eye)
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    upward = np.cross(right, forward)
    relative = points - eye
    depth = relative @ forward
    if (depth <= 0.05).any():
        return None
    focal = (size[0] / 2) / np.tan(np.radians(view["fov"]) / 2)
    across = size[0] / 2 + focal * (relative @ right) / depth
    down = size[1] / 2 - focal * (relative @ upward) / depth
    return np.stack([across, down], axis=1)


def frame_box(view, box, size):
    """The box's rectangle in the view's picture, cut to the frame, when it stands in front of the camera with at
    least SHOWN of it in the frame; or None."""
    points = projected(view, corners(box), size)
    if points is None:
        return None
    left, top = points.min(axis=0)
    right, bottom = points.max(axis=0)
    whole = max((right - left) * (bottom - top), 1e-6)
    cut = max(left, 0), max(top, 0), min(right, size[0]), min(bottom, size[1])
    if cut[2] <= cut[0] or cut[3] <= cut[1] or (cut[2] - cut[0]) * (cut[3] - cut[1]) / whole < SHOWN:
        return None
    return tuple(float(edge) for edge in cut)


def framed(film, box):
    """[(area, view number, rectangle)] of every frame past the fade that frames the box without filling it, the
    largest first."""
    area_most = MOST_OF_FRAME * film.size[0] * film.size[1]
    found = []
    for number, view in enumerate(film.views):
        rectangle = frame_box(view, box, film.size) if number >= FADE else None
        if rectangle is not None:
            area = (rectangle[2] - rectangle[0]) * (rectangle[3] - rectangle[1])
            if area <= area_most:
                found.append((area, number, rectangle))
    return sorted(found, key=lambda item: -item[0])


def best_view(film, box, visible=lambda view: True):
    """(view number, rectangle, area) of the frame that shows the box largest without filling it and whose camera
    sees it (`visible`), or None."""
    return next(((number, rectangle, area) for area, number, rectangle in framed(film, box)
                 if visible(film.views[number])), None)


def frames(film, numbers, folder):
    """{view number: the PNG of its video frame}, every frame asked for taken in one pass of ffmpeg."""
    numbers = sorted(set(numbers))
    if not numbers:
        return {}
    folder.mkdir(parents=True, exist_ok=True)
    chosen = "+".join(f"eq(n\\,{number + film.offset})" for number in numbers)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", film.video, "-vf", f"select='{chosen}'", "-vsync", "0",
                    str(folder / "frame-%04d.png")], check=True)
    return {number: folder / f"frame-{rank:04d}.png" for rank, number in enumerate(numbers, 1)}


def crop_round(rectangle, size):
    """The crop of the frame round a rectangle: the rectangle with half its size again round it, at least CROP,
    kept in the frame."""
    left, top, right, bottom = rectangle
    width = min(size[0], max(CROP[0], (right - left) * 2))
    height = min(size[1], max(CROP[1], (bottom - top) * 2))
    middle = ((left + right) / 2, (top + bottom) / 2)
    start = (min(max(0, middle[0] - width / 2), size[0] - width), min(max(0, middle[1] - height / 2), size[1] - height))
    return int(start[0]), int(start[1]), int(start[0] + width), int(start[1] + height)


def cropped(frame, rectangle, path):
    """The frame cropped round the rectangle, the rectangle drawn on it; the path."""
    with Image.open(frame) as image:
        shown = image.convert("RGB")
        ImageDraw.Draw(shown).rectangle(rectangle, outline=INK, width=3)
        shown.crop(crop_round(rectangle, shown.size)).save(path)
    return path


def draw(film, wanted, folder):
    """Each (view number, rectangle, path) written as its crop of the film's frame; the paths written."""
    taken = frames(film, [number for number, _, _ in wanted], folder / "frames")
    return [cropped(taken[number], rectangle, path) for number, rectangle, path in wanted]
