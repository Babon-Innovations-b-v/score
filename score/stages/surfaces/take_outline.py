"""A take's outline against its own close-up as the likeness gate scores it (score/stages/props/likeness_row.py
whole_best_way over pixal_cut's cut), in numpy, scipy and PIL alone, so the bake's job scores it on the card:
likeness.py cannot load in the bake's Python (its candidate check, tools/usd/compare.py, pulls in pxr through
annotate.py). The bake's stand-square turns a Pixal3D take only when its turned pose's outline is at least its made
pose's (route_bake.stood_square; #36, 2026-10-30: lab's desk_divider outlined 0.467 as made and 0.296 turned 20
degrees).

    cut(path)                           the close-up's object: its Pixal3D cut-out's largest piece, holes filled
    look_down(size)                     the one look-down its close-up is drawn and checked at
    look_downs(size, cut)               the look-downs the gate holds it at: the stated one, and for a row lying
                                        flat the one its close-up shows too (likeness_row.shown_look_down)
    best(points, triangles, cut, down)  the best outline of YAWS ways round the mesh, at that look-down

The ring, the square and the outline are tools/usd/compare.py's and the silhouette likeness.py's, written again here
(kept the same by the surfaces test against likeness_row.whole_best_way); the look-down is read from
tools/props/closeup/check.py itself, a file the bake row declares (route_bake.bake_files).
"""
import functools
import importlib.util
import math
import pathlib

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

REPO = pathlib.Path(__file__).resolve().parents[3]
CHECK = REPO / "tools/props/closeup/check.py"
YAWS, FOV, SQUARE = 8, 30.0, 128  # compare.py's ring and square
SIDE = 384  # likeness.SIDE


@functools.cache
def closeup_check():
    """tools/props/closeup/check.py loaded by its path (numpy, scipy and PIL), off the import path."""
    spec = importlib.util.spec_from_file_location("closeup_check", CHECK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def look_down(size):
    """check.look_down: from straight above for a row of `size` (wide, deep, tall) that lies flat, else its stated
    look-down."""
    return float(closeup_check().look_down(size))


def shown_look_down(target, size):
    """likeness_row.shown_look_down: the look-down a close-up of a row of `size` shows, read off its cut `target`'s
    height:width on the close-up check's own view, to the half degree."""
    check = closeup_check()
    rows, columns = np.where(target)
    seen = (rows.max() - rows.min() + 1) / (columns.max() - columns.min() + 1)
    downs = np.arange(0.0, check.TOP_DOWN_DEGREES + 0.5, 0.5)
    return float(downs[np.argmin([abs(np.log(check.expected_proportion(size, down) / seen)) for down in downs])])


def look_downs(size, target):
    """The look-downs likeness_row.whole_best_way holds a take at: its stated one, and for a row that lies flat the
    one its close-up's cut `target` shows too; its outline is the better of them."""
    stated = look_down(size)
    return [stated, shown_look_down(target, size)] if size and closeup_check().lies_flat(size) else [stated]


def cut(path):
    """The close-up's object as likeness_row.pixal_cut cuts a Pixal3D input: its alpha's largest piece, holes
    filled."""
    labels, count = ndimage.label(np.asarray(Image.open(path).convert("RGBA"))[..., 3] > 127)
    if count == 0:
        raise ValueError(f"{path}: Pixal3D's cut-out holds no object")
    largest = np.argmax(ndimage.sum(np.ones_like(labels), labels, index=range(1, count + 1))) + 1
    return ndimage.binary_fill_holes(labels == largest)


def silhouette(points, triangles, step, down):
    """likeness.silhouette: the mesh's mask seen from way `step` of YAWS, `down` degrees above level, framed on its
    box's middle."""
    low, high = points.min(axis=0), points.max(axis=0)
    middle = (low + high) / 2
    radius = max(0.05, float(np.linalg.norm(high - low)) / 2)
    distance = radius / math.sin(math.radians(FOV / 2)) * 1.05
    yaw, pitch = math.radians(360.0 * step / YAWS), math.radians(down)
    back = np.array([math.sin(yaw) * math.cos(pitch), math.sin(pitch), math.cos(yaw) * math.cos(pitch)])
    right = np.array([math.cos(yaw), 0.0, -math.sin(yaw)])
    up = np.cross(back, right)
    seen = points - (middle + back * distance)
    depth = -seen @ back
    focal = SIDE / 2 / math.tan(math.radians(FOV / 2))
    pixels = np.stack([SIDE / 2 + focal * (seen @ right) / depth, SIDE / 2 - focal * (seen @ up) / depth], axis=1)
    picture = Image.new("L", (SIDE, SIDE), 0)
    draw = ImageDraw.Draw(picture)
    for corner in pixels[triangles]:
        draw.polygon([tuple(point) for point in corner], fill=255)
    return np.asarray(picture) > 127


def boxed(mask):
    """compare.boxed: a mask cut to its box and set in the middle of a SQUARE by SQUARE square, its proportions
    kept."""
    rows, columns = np.where(mask)
    if len(rows) == 0:
        return np.zeros((SQUARE, SQUARE), dtype=bool)
    piece = mask[rows.min():rows.max() + 1, columns.min():columns.max() + 1]
    scale = SQUARE / max(piece.shape)
    size = (max(1, round(piece.shape[1] * scale)), max(1, round(piece.shape[0] * scale)))
    shrunk = np.asarray(Image.fromarray(piece.astype(np.uint8) * 255).resize(size, Image.BILINEAR)) > 127
    square = np.zeros((SQUARE, SQUARE), dtype=bool)
    top, left = (SQUARE - shrunk.shape[0]) // 2, (SQUARE - shrunk.shape[1]) // 2
    square[top:top + shrunk.shape[0], left:left + shrunk.shape[1]] = shrunk
    return square


def outline(first, second):
    """compare.outline: the overlap of two masks, each boxed, intersection over union."""
    one, other = boxed(first), boxed(second)
    union = np.logical_or(one, other).sum()
    return float(np.logical_and(one, other).sum() / union) if union else 0.0


def best(points, triangles, target, down):
    """The best of YAWS ways' outlines of the mesh, each silhouette's holes filled, against the cut `target`, at
    look-down `down` (likeness_row.whole_best_way's outline)."""
    return max(round(outline(ndimage.binary_fill_holes(silhouette(points, triangles, step, down)), target), 4)
               for step in range(YAWS))
