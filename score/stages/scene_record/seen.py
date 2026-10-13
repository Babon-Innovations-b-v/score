"""Which seated places a place's own views can see, so its record shows only those (the concept decides: the old
station's C4 shows none of the base, its views stand within 15 m looking in).

A neighbour is seen when one of its sample points (its floor's corners and middle, at its foot and its roof) stands
inside one of the record's views' frames, near enough to show (its size across at least MIN_ANGLE degrees from the
eye), and nothing of the place itself lies between: the place's own stage (its seed's drawn world, less its places,
old ground and glass) and its made ground. A place a door leads to is always shown (its doorway opens onto it).
"""
import json
import math
import pathlib
import re

import numpy as np

# A view's frame: VIEW_FOV degrees across (the record's views'), its height by a 16:9 picture.
ASPECT = 16 / 9
# A neighbour shows when its size across spans at least this many degrees from the eye (a few pixels of a view).
MIN_ANGLE = 0.5
# A neighbour with no plan stands as a box this wide, deep and tall (metres).
DEFAULT_SIZE = (10.0, 10.0, 5.0)
# Its roof's sample points stand this high over its floor when its plan says no walls' height.
DEFAULT_HIGH = 3.0
SEEN_THROUGH = re.compile(r"glass|window|porthole|(^|_)pane(_|$)")
LEFT_OUT = ("Places", "Ground", "Terrain", "Water", "Sky", "Environment", "Backdrop", "Outside")


def size_of(plans, stage):
    """A neighbour's floor wide and deep and its height, from its plan (else DEFAULT_SIZE)."""
    path = pathlib.Path(plans) / f"{stage}.json"
    if not path.exists():
        return DEFAULT_SIZE
    plan = json.loads(path.read_text())
    if "w" not in plan:
        return DEFAULT_SIZE
    words = plan.get("height", "")
    high = next((float(word) for word in words.replace(",", " ").split() if word.replace(".", "", 1).isdigit()),
                DEFAULT_HIGH)
    return float(plan["w"]), float(plan["d"]), high


def samples(entry, size):
    """A neighbour's sample points in this place's frame: its floor's corners and middle, at its foot and its roof."""
    wide, deep, high = size
    local = np.array([[across, up, along] for across in (-wide / 2, 0.0, wide / 2) for along in (-deep / 2, 0.0, deep / 2)
                      for up in (0.2, high)])
    axes = rotation_matrix(entry["rotation"]) if "rotation" in entry else np.eye(3)
    return np.asarray(entry["at"], dtype=float) + local @ axes


def rotation_matrix(quaternion):
    """[x, y, z, w] as a 3 x 3 whose rows are the turned x, y and z axes (writer.quaternion's inverse)."""
    x, y, z, w = quaternion
    matrix = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                       [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                       [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    return matrix.T


def in_frame(view, points, fov):
    """Which points stand inside a view's frame (in front of the eye, within half its width and height)."""
    eye, aim = np.asarray(view["eye"], dtype=float), np.asarray(view["aim"], dtype=float)
    forward = (aim - eye) / np.linalg.norm(aim - eye)
    right = np.cross(forward, [0.0, 1.0, 0.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    way = points - eye
    ahead = way @ forward
    across = np.degrees(np.arctan2(np.abs(way @ right), ahead))
    rise = np.degrees(np.arctan2(np.abs(way @ up), ahead))
    half_high = math.degrees(math.atan(math.tan(math.radians(fov / 2)) / ASPECT))
    return (ahead > 0) & (across <= fov / 2) & (rise <= half_high)


def occluders(place, seeds, made_ground):
    """The place's own drawn world as one trimesh: its seed less its places, old ground and glass, and its made ground
    (terrain outside.meshes' parts, already in the place's frame)."""
    import trimesh
    from pxr import Usd
    from score.stages.terrain import sight
    stage = Usd.Stage.Open(str(pathlib.Path(seeds) / place / f"{place}.usda"))
    # shortcut: what is seen through is found by its prim's name (dome_glass, glass_east, the camp's
    # dome_window_panel_*, a hatch's window, a porthole: a baked model's glass is in its picture, not its mesh); a
    # window's frame is let through with it
    skipped = [str(prim.GetPath()) for prim in stage.Traverse() if SEEN_THROUGH.search(prim.GetName().lower())]
    skipped += [f"/{place}/{name}" for name in LEFT_OUT]
    own = sight.gathered(stage, skipped)
    parts = [own] + [trimesh.Trimesh(points, triangles, process=False)
                     for points, triangles, _ in (made_ground or {}).values()]
    return trimesh.util.concatenate([part for part in parts if len(part.faces)])


def visible(views, entries, plans, rays, fov):
    """The names of the entries one of the views sees (module docstring)."""
    found = set()
    for entry in entries:
        points = samples(entry, size_of(plans, entry["stage"]))
        span = float(np.linalg.norm(points.max(axis=0) - points.min(axis=0)))
        for view in views:
            eye = np.asarray(view["eye"], dtype=float)
            distance = np.linalg.norm(points - eye, axis=1)
            near = np.degrees(2 * np.arctan(span / 2 / np.maximum(distance, 1e-6))) >= MIN_ANGLE
            framed = in_frame(view, points, fov) & near
            if not framed.any():
                continue
            if rays is None or unblocked(rays, eye, points[framed]):
                found.add(entry["name"])
                break
    return found


def unblocked(rays, eye, points):
    """Whether a straight line from the eye reaches any of the points before the place's own world stops it."""
    ways = points - eye
    lengths = np.linalg.norm(ways, axis=1)
    origins = np.repeat(eye[None, :], len(points), axis=0)
    hits, index, _ = rays.intersects_location(origins, ways / lengths[:, None], multiple_hits=False)
    first = np.full(len(points), np.inf)
    for hit, ray in zip(hits, index):
        first[ray] = min(first[ray], float(np.linalg.norm(hit - eye)))
    return bool((first >= lengths - 0.5).any())
