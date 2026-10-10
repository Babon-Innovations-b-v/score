"""Check the star-turn measure (tools/usd/star_turn.py) on a shot made here: the game's field turned as the game
turns it at a known minute, drawn as single lit pixels from a record-like view with stray dots among them, is found
again and its minute read back within a minute, the turn within a tenth of a degree.

Run: .venv/bin/python tools/usd/star_turn_test.py   (make tests runs it with the framework's environment)
"""
import math
import pathlib
import sys
import tempfile

import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import orbits  # noqa: E402
import star_turn  # noqa: E402

STARS = {"count": 1800, "seed": 9}
VIEW = {"name": "made", "eye": [0.0, 1.6, 0.0], "aim": [-40.0, 12.0, 25.0], "fov": 70.0}
SIZE = (788, 1400)


def drawn_shot(path, minute):
    """The field at `minute` (Earth site axes) seen from VIEW, each star in front a lit pixel, with stray dots."""
    ways = star_turn.field_ways(STARS) @ orbits.stars_turn(minute, np.eye(3)).T
    camera = ways @ star_turn.camera_turn(VIEW)
    ahead = camera[:, 2] < 0
    focal = (SIZE[1] / 2.0) / math.tan(math.radians(VIEW["fov"]) / 2.0)
    columns = SIZE[1] / 2.0 + focal * camera[ahead, 0] / -camera[ahead, 2]
    rows = SIZE[0] / 2.0 - focal * camera[ahead, 1] / -camera[ahead, 2]
    picture = np.zeros(SIZE, dtype=np.uint8)
    inside = (columns >= 1) & (columns < SIZE[1] - 1) & (rows >= 1) & (rows < SIZE[0] - 1)
    picture[np.round(rows[inside]).astype(int), np.round(columns[inside]).astype(int)] = 220
    stray = np.random.default_rng(3).integers([5, 5], [SIZE[0] - 5, SIZE[1] - 5], size=(12, 2))
    picture[stray[:, 0], stray[:, 1]] = 120
    Image.fromarray(picture).save(path)
    return int(inside.sum())


def main():
    with tempfile.TemporaryDirectory() as folder:
        shot = pathlib.Path(folder) / "shot.png"
        drawn = drawn_shot(shot, 60.0)
        assert drawn > 40, drawn
        catalogue = star_turn.Catalogue(star_turn.field_ways(STARS))
        found = star_turn.measure(VIEW, shot, catalogue, np.eye(3))
        assert found["stars"] >= star_turn.ENOUGH, found
        assert abs(found["minute"] - 60.0) <= 1.0 and found["off_degrees"] < 0.1, found
    print("star_turn_test: ok")


if __name__ == "__main__":
    main()
