"""The render-twice check (#216): the first frames rendered by a second editor process must match the full pass's.
Higgsfield found dark rectangles that held still through 4 of their 7 final renders; one render alone cannot show
them, a second render of the same frames can. A frame is cut into TILE-pixel tiles and each tile's mean brightness
compared; a tile that differs by more than TILE_LIMIT is a fault. Every check gives its largest tile difference, so
the first runs show how far apart two clean renders of the same frame fall.
"""
import pathlib

import numpy as np
from PIL import Image

TILE = 32
TILE_LIMIT = 0.05  # of the brightness range 0..1, a tile's mean
LUMA = np.array([0.2126, 0.7152, 0.0722])  # Rec. 709


def brightness(path):
    """The picture's brightness, 0..1 a pixel."""
    with Image.open(path) as opened:
        return np.asarray(opened.convert("RGB"), dtype=np.float64) @ LUMA / 255.0


def tile_means(picture):
    """Each whole tile's mean brightness, rows by columns (a strip short of a tile at the edges left out)."""
    rows, columns = picture.shape[0] // TILE, picture.shape[1] // TILE
    cut = picture[:rows * TILE, :columns * TILE]
    return cut.reshape(rows, TILE, columns, TILE).mean(axis=(1, 3))


def compare(first, second):
    """Two renders of one frame: the largest tile difference and each tile past TILE_LIMIT (its pixel box, both
    means)."""
    one, two = brightness(first), brightness(second)
    if one.shape != two.shape:
        return {"largest": 1.0, "faults": [{"size": [list(one.shape), list(two.shape)]}]}
    means_one, means_two = tile_means(one), tile_means(two)
    difference = np.abs(means_one - means_two)
    faults = [{"box": [int(column) * TILE, int(row) * TILE, TILE, TILE], "full": round(float(means_one[row, column]), 4),
               "check": round(float(means_two[row, column]), 4)}
              for row, column in zip(*np.nonzero(difference > TILE_LIMIT))]
    return {"largest": round(float(difference.max()), 4) if difference.size else 0.0, "faults": faults}


def check(full, check_folder, frames):
    """The check pass's frames against the same-named frames of the full pass: same when `frames` were checked and
    no tile of any differs."""
    names = sorted(path.name for path in pathlib.Path(check_folder).glob("*.png"))
    found = {}
    for name in names:
        other = pathlib.Path(full) / name
        found[name] = (compare(other, pathlib.Path(check_folder) / name) if other.exists()
                       else {"largest": 1.0, "faults": [{"missing": "full"}]})
    largest = max((one["largest"] for one in found.values()), default=0.0)
    faulty = sorted(name for name, one in found.items() if one["faults"])
    return {"same": len(names) == frames and not faulty, "checked": len(names), "asked": frames,
            "largest": largest, "tile": TILE, "limit": TILE_LIMIT, "faulty": faulty,
            "frames": {name: one for name, one in found.items() if one["faults"]}}
