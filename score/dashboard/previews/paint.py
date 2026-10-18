"""The painted models of a paint output, from its own files: each take's surface pieces (a .ply named by its
surface) seen three-quarter from above, every piece in its library surface's colour, nearest points drawn last; one
cell per take, named."""
import math
import pathlib
from collections import defaultdict

import numpy as np
from PIL import Image, ImageDraw, ImageFont

CELL = 200
COLUMNS = 3
MOST_TAKES = 9
MOST_POINTS = 12000
BACKGROUND = (238, 236, 230)
INK = (29, 32, 38)
GREY = (150, 150, 150)
AZIMUTH = math.radians(-35.0)
ELEVATION = math.radians(28.0)


def view():
    """Turn about y, then tilt about x: a three-quarter view from above."""
    turn = np.array([[math.cos(AZIMUTH), 0, math.sin(AZIMUTH)], [0, 1, 0],
                     [-math.sin(AZIMUTH), 0, math.cos(AZIMUTH)]])
    tilt = np.array([[1, 0, 0], [0, math.cos(ELEVATION), -math.sin(ELEVATION)],
                     [0, math.sin(ELEVATION), math.cos(ELEVATION)]])
    return tilt @ turn


def takes(files, known):
    """{take: [(surface, path)]} of the .ply pieces named by a surface the library holds (part pieces skipped),
    grouped by the folder they sit in."""
    found = defaultdict(list)
    for name, path in files:
        stored = pathlib.PurePosixPath(name)
        if stored.suffix == ".ply" and stored.stem in known:
            found[stored.parent.name].append((stored.stem, path))
    return dict(sorted(found.items())[:MOST_TAKES])


def points_of(path):
    """A piece's points (its mesh's vertices, or its point cloud's), at most MOST_POINTS."""
    import trimesh
    loaded = trimesh.load(str(path), file_type="ply", process=False)
    found = np.asarray(getattr(loaded, "vertices", np.zeros((0, 3))), dtype=float)
    if len(found) > MOST_POINTS:
        found = found[np.linspace(0, len(found) - 1, MOST_POINTS).astype(int)]
    return found


def cell(pieces, known):
    """One take drawn: every piece's points projected, in its surface's colour."""
    picture = Image.new("RGB", (CELL, CELL), BACKGROUND)
    coloured = [(points_of(path), known[surface][0]) for surface, path in pieces]
    coloured = [(points, rgb) for points, rgb in coloured if len(points)]
    if not coloured:
        return picture
    turned = [(points @ view().T, rgb) for points, rgb in coloured]
    every = np.vstack([points for points, _ in turned])
    low, high = every.min(axis=0), every.max(axis=0)
    scale = (CELL - 24) / max(high[0] - low[0], high[1] - low[1], 1e-6)
    pixels = np.array(picture)
    stacked = np.vstack([np.c_[points, np.tile(rgb, (len(points), 1))] for points, rgb in turned])
    for x, y, depth, red, green, blue in stacked[np.argsort(stacked[:, 2])]:
        column = int(12 + (x - low[0]) * scale)
        row = int(CELL - 12 - (y - low[1]) * scale)
        pixels[max(row - 1, 0):row + 1, max(column - 1, 0):column + 1] = (red, green, blue)
    return Image.fromarray(pixels)


def picture(files, known, destination):
    """The sheet of painted takes; the path, or None when no piece is named by a library surface."""
    found = takes(files, known)
    if not found:
        return None
    rows = -(-len(found) // COLUMNS)
    sheet = Image.new("RGB", (COLUMNS * CELL, rows * CELL), BACKGROUND)
    pen = ImageDraw.Draw(sheet)
    small = ImageFont.load_default(size=11)
    for number, (take, pieces) in enumerate(found.items()):
        left, top = (number % COLUMNS) * CELL, (number // COLUMNS) * CELL
        sheet.paste(cell(pieces, known), (left, top))
        pen.text((left + 4, top + 3), take[:28], fill=INK, font=small)
    destination = pathlib.Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, format="PNG")
    return destination
