"""Measure the base minute a game shot's stars stand at: find the game's own star field (builders.stars, its seed's)
among the shot's lit dots, whatever way it is turned, and fit that turn to the game's (orbits.stars_turn) to read the
minute, so a scene record's stars `turn` is measured, never typed by eye.

    .venv/bin/python tools/usd/star_turn.py <place> <view>=<shot> [<view>=<shot> ...]

Each shot is the game's picture from one of the place's record views (its eye, aim and field of view across); it
prints one JSON line a shot: how many dots it found, how many stars of the field landed on them, the minute within
the Moon's lap and how far (degrees) the turn found is from the game's turn at that minute.

How it finds the field (lost-in-space star identification): a dot is a pixel brighter than its 3 x 3 neighbours and
than PEAK with nothing over AROUND in the ring 3 to 5 pixels out (a star alone on the night); each dot is a way out of
the camera. For a pair of the brightest dots their angle apart is looked up among every pair of the field's stars
(within TOLERANCE); each match gives a turn (the two stars onto the two dots), and the turn that lays the most stars
within HIT of a dot wins, as soon as one lays ENOUGH. The camera's own turn (its view) carries that into the place's
frame, and the minute is the one in a lap (every STEP minutes) whose turn is nearest.
"""
import argparse
import json
import math
import pathlib
import sys

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import builders  # noqa: E402
import effects  # noqa: E402
import orbits  # noqa: E402
import scene  # noqa: E402

PEAK = 45
AROUND = 22
TOLERANCE = 0.12
HIT = 0.2
USE = 15
ENOUGH = 15
STEP = 0.25
LAP_MINUTES = 2.0 * math.pi / orbits.MOON_RATE / orbits.REAL_SECONDS_PER_MINUTE


def field_ways(stars):
    """The game's star field's ways (unit, n x 3) as builders.stars draws them from the record's seed and count."""
    numbers = iter(builders.pcg32_floats(int(stars["seed"]), int(stars["count"]) * 4))
    ways = []
    for _ in range(int(stars["count"])):
        way = np.array([next(numbers) * np.float32(2.0) - np.float32(1.0) for _ in range(3)], dtype=np.float64)
        next(numbers)  # the star's size
        ways.append(way / np.linalg.norm(way))
    return np.array(ways)


def dots(path):
    """The shot's lone lit dots (x, y in pixels, brightest first, centred on their 3 x 3) and the picture's height and
    width."""
    grey = np.asarray(Image.open(path).convert("L")).astype(np.float64)
    ring = np.ones((11, 11), dtype=bool)
    ring[3:8, 3:8] = False
    lone = (grey == ndimage.maximum_filter(grey, size=3)) & (grey > PEAK) & (
        ndimage.maximum_filter(grey, footprint=ring) < AROUND)
    rows, columns = np.nonzero(lone)
    keep = (rows > 0) & (rows < grey.shape[0] - 1) & (columns > 0) & (columns < grey.shape[1] - 1)
    rows, columns = rows[keep], columns[keep]
    offsets = np.array([-1.0, 0.0, 1.0])
    found = []
    for row, column in zip(rows, columns):
        patch = grey[row - 1:row + 2, column - 1:column + 2]
        found.append((column + (patch.sum(axis=0) @ offsets) / patch.sum(), row + (patch.sum(axis=1) @ offsets) /
                      patch.sum(), grey[row, column]))
    found.sort(key=lambda spot: -spot[2])
    return np.array([spot[:2] for spot in found]).reshape(-1, 2), grey.shape


def camera_ways(points, shape, fov):
    """Each dot as a unit way in the camera's own axes (x right, y up, looking down -z), its field of view across."""
    height, width = shape
    focal = (width / 2.0) / math.tan(math.radians(fov) / 2.0)
    ways = np.column_stack([(points[:, 0] - width / 2.0) / focal, -(points[:, 1] - height / 2.0) / focal,
                            -np.ones(len(points))])
    return ways / np.linalg.norm(ways, axis=1)[:, None]


def camera_turn(view):
    """The camera's axes in the place's frame (columns: x right, y up, z back), as usd_views.py stands it."""
    eye, aim = np.asarray(view["eye"], dtype=np.float64), np.asarray(view["aim"], dtype=np.float64)
    back = (eye - aim) / np.linalg.norm(eye - aim)
    across = np.cross(np.asarray(view.get("up", [0.0, 1.0, 0.0]), dtype=np.float64), back)
    across /= np.linalg.norm(across)
    return np.column_stack([across, np.cross(back, across), back])


def triad(first, second, onto_first, onto_second):
    """The turn taking `first` onto `onto_first` and `second` as near `onto_second` as it goes."""
    def axes(one, two):
        cross = np.cross(one, two)
        cross /= np.linalg.norm(cross)
        return np.column_stack([one, cross, np.cross(one, cross)])
    return axes(onto_first, onto_second) @ axes(first, second).T


class Catalogue:
    """Every pair of the field's stars by the angle between them, for looking pairs up by angle."""

    def __init__(self, ways):
        self.ways = ways
        first, second = np.triu_indices(len(ways), 1)
        apart = np.arccos(np.clip(np.einsum("ij,ij->i", ways[first], ways[second]), -1.0, 1.0))
        order = np.argsort(apart)
        self.first, self.second, self.apart = first[order], second[order], apart[order]

    def pairs_apart(self, angle, tolerance):
        """The pairs of stars `angle` radians apart, within `tolerance`."""
        low, high = np.searchsorted(self.apart, [angle - tolerance, angle + tolerance])
        return self.first[low:high], self.second[low:high]


def hits(catalogue, seen, turn, bound):
    """How many of the field's stars ahead of the camera, turned by `turn`, land within `bound` of a dot."""
    turned = catalogue.ways @ turn.T
    distances, _ = seen.query(turned[turned[:, 2] < -0.3], distance_upper_bound=bound)
    return int(np.isfinite(distances).sum())


def identify(catalogue, ways):
    """The turn (field into the camera's axes) laying the most stars on the dots (`ways`, brightest first), and how
    many it lays."""
    seen = cKDTree(ways)
    bound = 2.0 * math.sin(math.radians(HIT) / 2.0)
    best = (0, None)
    top = ways[:USE]
    for one in range(len(top)):
        for two in range(one + 1, len(top)):
            angle = math.acos(float(np.clip(top[one] @ top[two], -1.0, 1.0)))
            if angle < math.radians(2.0):
                continue
            firsts, seconds = catalogue.pairs_apart(angle, math.radians(TOLERANCE))
            for star, other in [*zip(firsts, seconds), *zip(seconds, firsts)]:
                turn = triad(catalogue.ways[star], catalogue.ways[other], top[one], top[two])
                laid = hits(catalogue, seen, turn, bound)
                if laid > best[0]:
                    best = (laid, turn)
            if best[0] >= ENOUGH:
                return best
    return best


def apart_degrees(one, two):
    """How far apart two turns are, degrees."""
    return math.degrees(math.acos(float(np.clip((np.trace(one.T @ two) - 1.0) / 2.0, -1.0, 1.0))))


def nearest_minute(place_turn, frame):
    """The minute within a lap whose game turn (orbits.stars_turn in `frame`) is nearest the turn found, and how far."""
    return min((apart_degrees(place_turn, orbits.stars_turn(minute, frame)), float(minute))
               for minute in np.arange(0.0, LAP_MINUTES, STEP))[::-1]


def place_frame(place, axes):
    """The Moon's own space onto the place's frame: the place's seat (its ground) or, on the Earth site, as it is."""
    return np.eye(3) if axes == "site" else effects.place_ground(place).frame


def measure(view, shot, catalogue, frame):
    """One shot's measurement: dots, stars laid on them, the minute and how far the turn is from the game's."""
    points, shape = dots(shot)
    laid, turn = identify(catalogue, camera_ways(points, shape, float(view["fov"])))
    found = {"view": view["name"], "dots": len(points), "stars": laid}
    if turn is not None:
        found["minute"], found["off_degrees"] = nearest_minute(camera_turn(view) @ turn, frame)
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("place")
    parser.add_argument("shots", nargs="+", help="<view>=<the game's shot from it>")
    parser.add_argument("--axes", choices=("site", "seat"), default="seat",
                        help="the Earth site's axes (the Moon's own) or the place's seat on the Moon")
    arguments = parser.parse_args()
    record = scene.record(arguments.place)
    catalogue = Catalogue(field_ways(record["environment"]["stars"]))
    frame = place_frame(arguments.place, arguments.axes)
    views = {view["name"]: view for view in record["views"]}
    for item in arguments.shots:
        name, shot = item.split("=", 1)
        print(json.dumps(measure(views[name], shot, catalogue, frame)), flush=True)


if __name__ == "__main__":
    main()
