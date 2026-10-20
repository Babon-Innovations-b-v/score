"""Placed ground: the old station's yard on the Moon's planned ground, levelled by `tools/usd/ground.py` `levelled`
itself. The ground before is the heights picture as the repository held it before the yard was levelled (git, the
commit before LEVELLED); the ground after is `levelled` run on it with the box, height and blend the Moon's ground
record notes for the old station."""
import io
import json
import subprocess
import sys

import numpy as np
from PIL import Image

ALGORITHM = "ground_detail"
PLACE = "old_station"
PICTURE = "data/ground/moon_plan_heights.png"
LEVELLED = "d7909143"  # "old station: yard levelled": the commit whose picture first held the levelled yard
AROUND = 12.0  # metres of ground shown round the levelled box
SIDE = 64  # the page's grid at most


def heights_before(repo, record):
    """The Moon's planned heights, in metres, as the picture was before the yard was levelled."""
    shown = subprocess.run(["git", "-C", str(repo), "show", f"{LEVELLED}^:{PICTURE}"], capture_output=True,
                           check=True).stdout
    pixels = np.asarray(Image.open(io.BytesIO(shown)).convert("RGB")).astype(np.int64)
    code = (pixels[..., 0] << 8) | pixels[..., 1]
    return code / 65535 * record["span"] - record["low"]


def window(size, side, box):
    """The rows and columns of the plan's grid within AROUND of the box (across low, along low, across high, along
    high), at most SIDE of each, evenly picked."""
    at = (np.arange(size) / (size - 1) - 0.5) * side
    columns = np.nonzero((at >= box[0] - AROUND) & (at <= box[2] + AROUND))[0]
    rows = np.nonzero((at >= box[1] - AROUND) & (at <= box[3] + AROUND))[0]
    every = max(1, -(-max(len(rows), len(columns)) // SIDE))
    return rows[::every], columns[::every], at


def rounded(heights):
    return [[round(float(value), 2) for value in row] for row in heights]


def made(inputs):
    sys.path.insert(0, str(inputs.repo / "tools/usd"))
    import ground
    record = json.loads((inputs.repo / "data/ground/moon.json").read_text())
    level = record["places"][PLACE]["level"]
    before = heights_before(inputs.repo, record)
    box = level["box"]
    after = ground.levelled(before, record["side"], box[:2], box[2:], level["height"], level["blend"])
    rows, columns, at = window(before.shape[0], record["side"], box)
    cut = np.ix_(rows, columns)
    moved = np.abs(after - before)[cut]
    return {
        "example": "the old station's yard on the Moon",
        "view": "relief",
        "relief": {"size": [round(float(at[columns[-1]] - at[columns[0]]), 1),
                            round(float(at[rows[-1]] - at[rows[0]]), 1)],
                   "heights": rounded(after[cut]),
                   "steps": [{"label": "The planned Moon ground under the station, as it was", "heights":
                              rounded(before[cut])},
                             {"label": f"The yard levelled at {level['height']:.2f} m, eased back into the ground "
                                       f"over {level['blend']:.0f} m", "heights": rounded(after[cut])}]},
        "steps": [],
        "numbers": [{"label": "yard", "value": round((box[2] - box[0]) * (box[3] - box[1])), "unit": "m²",
                     "tip": "the levelled box: the station's pieces and a margin round them"},
                    {"label": "most moved", "value": round(float(moved.max()), 2), "unit": "m",
                     "tip": "the most the ground moved anywhere in the yard"}]}
