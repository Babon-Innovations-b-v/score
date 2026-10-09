"""Render-and-compare: each object of a place rendered alone and set beside its close-up, scored by its outline and by
DINOv2, so a swapped, broken or wrong-scale model shows as a low score instead of waiting for the owner's eye.

    .venv/bin/python tools/usd/compare.py <stage.usda> --out <folder> [--closeups <folder of <row>.png>] [--cloud]
                                          [--who "<session>"]

For every inventory row with a close-up (the row's `close_up` or `closeup` file, or <row>.png in --closeups), the
row's first object is rendered alone (annotate.py: nothing else drawn) from YAWS ways round it at ELEVATION, framed on
its own bounds, since a close-up is a three-quarter picture whose camera was never recorded: every way is scored, and the
one most like the close-up stands for the close-up's camera. Two numbers per object:

    outline   the overlap (intersection over union) of the object's mask with the close-up's (its pixels apart from
              the plain background, the largest piece), each cut to its own box and set in the same square
    likeness  DINOv2's cosine likeness of the two pictures, each cut to its box on white (similar.py, a rented card;
              facebook/dinov2-base, Apache-2.0)

The objects are listed worst first (lowest likeness), each with both pictures, in <out>/compare.json. The idea is
WorldAct's placement by render-and-compare (arXiv 2605.15843: candidate renders ranked by DINOv2 likeness to the
object's own pixels), used here as a check: nothing is moved.
"""
import argparse
import json
import math
import pathlib
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import annotate  # noqa: E402

YAWS = 8
ELEVATION = 20.0
FOV = 30.0
SIZE = (384, 384)
SQUARE = 128
# The renders run on a rented card (Cycles on the card), or on a processor machine when no card is in stock.
RENDER_CLASSES = ("gpu-24gb", "gpu-48gb", "gpu-80gb", "cpu-32c-128gb", "cpu-32c-64gb")
# A close-up's background is its border's colour; a pixel further from it than this (0 to 255, any channel) is the
# object's.
BACKGROUND_STEP = 24


def closeup_of(row, folder=None):
    """A row's close-up file, or None."""
    for key in ("close_up", "closeup"):
        value = row.get(key)
        if isinstance(value, str) and pathlib.Path(value).expanduser().exists():
            return pathlib.Path(value).expanduser()
    if folder is not None and (pathlib.Path(folder) / f"{row['id']}.png").exists():
        return pathlib.Path(folder) / f"{row['id']}.png"
    return None


def closeup_mask(picture):
    """The object's pixels in a close-up: apart from the border's colour, the largest piece, holes filled."""
    pixels = np.asarray(picture.convert("RGB"), dtype=np.int16)
    border = np.concatenate([pixels[0], pixels[-1], pixels[:, 0], pixels[:, -1]])
    background = np.median(border, axis=0)
    apart = np.abs(pixels - background).max(axis=2) > BACKGROUND_STEP
    labels, count = ndimage.label(ndimage.binary_opening(apart, iterations=2))
    if count == 0:
        return apart
    largest = np.argmax(ndimage.sum(np.ones_like(labels), labels, index=range(1, count + 1))) + 1
    return ndimage.binary_fill_holes(labels == largest)


def boxed(mask):
    """A mask cut to its box and set in the middle of a SQUARE by SQUARE square, keeping its proportions."""
    rows, columns = np.where(mask)
    if len(rows) == 0:
        return np.zeros((SQUARE, SQUARE), dtype=bool)
    cut = mask[rows.min():rows.max() + 1, columns.min():columns.max() + 1]
    scale = SQUARE / max(cut.shape)
    size = (max(1, round(cut.shape[1] * scale)), max(1, round(cut.shape[0] * scale)))
    shrunk = np.asarray(Image.fromarray(cut.astype(np.uint8) * 255).resize(size, Image.BILINEAR)) > 127
    square = np.zeros((SQUARE, SQUARE), dtype=bool)
    top, left = (SQUARE - shrunk.shape[0]) // 2, (SQUARE - shrunk.shape[1]) // 2
    square[top:top + shrunk.shape[0], left:left + shrunk.shape[1]] = shrunk
    return square


def outline(first, second):
    """The overlap of two masks, each boxed: intersection over union, 0 to 1."""
    one, other = boxed(first), boxed(second)
    union = np.logical_or(one, other).sum()
    return float(np.logical_and(one, other).sum() / union) if union else 0.0


def cut_on_white(picture, mask):
    """A picture cut to the mask's box, everything outside the mask white."""
    pixels = np.asarray(picture.convert("RGB")).copy()
    pixels[~mask] = 255
    rows, columns = np.where(mask)
    if len(rows) == 0:
        return Image.fromarray(pixels)
    return Image.fromarray(pixels[rows.min():rows.max() + 1, columns.min():columns.max() + 1])


def object_bounds(stage_path):
    """Each laid object's box (low, high) in the stage's frame, by prim path."""
    from pxr import Usd, UsdGeom
    import resting
    stage = Usd.Stage.Open(str(stage_path))
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    found = {}
    for path, prim in resting.objects_of(stage, stage.GetDefaultPrim().GetName()).items():
        box = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        found[path] = (np.array(box.GetMin()), np.array(box.GetMax()))
    return found


def ring_views(name, path, low, high):
    """YAWS views round one object, at ELEVATION, each framing its bounds."""
    middle = (low + high) / 2
    radius = max(0.05, float(np.linalg.norm(high - low)) / 2)
    distance = radius / math.sin(math.radians(FOV / 2)) * 1.05
    views = []
    for step in range(YAWS):
        yaw, pitch = math.radians(360.0 * step / YAWS), math.radians(ELEVATION)
        way = np.array([math.sin(yaw) * math.cos(pitch), math.sin(pitch), math.cos(yaw) * math.cos(pitch)])
        views.append(annotate.view(f"{name}-yaw{step}", middle + way * distance, middle, fov=FOV, only=[path]))
    return views


def chosen(stage_path, rows, closeups):
    """{row: (first object's prim path, close-up file)} for every row with a close-up and an object on the stage."""
    paths = sorted(object_bounds(stage_path))
    found = {}
    for row in rows:
        picture = closeup_of(row, closeups)
        path = next((path for path in paths if path.rsplit("/", 1)[-1].rsplit("_", 1)[0] == row["id"]), None)
        if picture is not None and path is not None:
            found[row["id"]] = (path, picture)
    return found


def ways(out, row, path, picture):
    """Each yaw's render of one object beside its close-up: [(view name, outline score, render cut file)], the cuts
    written into out."""
    target = closeup_mask(Image.open(picture))
    found = []
    for step in range(YAWS):
        name = f"{row}-yaw{step}"
        seen = annotate.load(out / "renders", name)
        mask = annotate.mask(seen, path)
        cut = out / "cuts" / f"{name}.png"
        cut_on_white(Image.open(seen["look"]), mask).save(cut)
        found.append((name, outline(mask, target), cut))
    return found


def best_of(scored, likeness):
    """The way that matches the close-up best: by DINOv2 likeness when it was measured, else by outline."""
    return max(scored, key=lambda way: (likeness.get(way[0], -1.0), way[1]))


def compare(stage_path, rows, out, closeups=None, cloud=False, who="compare", reuse=False):
    """Every object with a close-up rendered and scored (with `reuse`, from the renders already in <out>/renders); the
    list, worst likeness first. Every way round each object is scored, and the best stands for the close-up's camera."""
    out = pathlib.Path(out)
    bounds = object_bounds(stage_path)
    picked = chosen(stage_path, rows, closeups)
    views = [view for row, (path, _) in picked.items() for view in ring_views(row, path, *bounds[path])]
    if not reuse:
        annotate.run(stage_path, views, out / "renders", cloud, SIZE, RENDER_CLASSES)
    (out / "cuts").mkdir(parents=True, exist_ok=True)
    pairs, scored = {}, {}
    for row, (path, picture) in sorted(picked.items()):
        closeup_cut = out / "cuts" / f"{row}-closeup.png"
        cut_on_white(Image.open(picture), closeup_mask(Image.open(picture))).save(closeup_cut)
        scored[row] = ways(out, row, path, picture)
        pairs.update({name: [str(cut), str(closeup_cut)] for name, _, cut in scored[row]})
    likeness = similar_scores(pairs, out, cloud, who)
    found = []
    for row, (path, picture) in sorted(picked.items()):
        name, score, cut = best_of(scored[row], likeness)
        found.append({"row": row, "object": path, "view": name, "outline": round(score, 3),
                      "likeness": round(likeness[name], 3) if name in likeness else None,
                      "render": str(cut), "closeup": str(picture)})
    found.sort(key=lambda entry: (entry["likeness"] if entry["likeness"] is not None else 2.0, entry["outline"]))
    (out / "compare.json").write_text(json.dumps(found, indent=1) + "\n")
    return found


def similar_scores(pairs, out, cloud, who):
    """DINOv2's likeness of each pair on a rented card; none without the cloud (no model runs on this PC)."""
    if not cloud or not pairs:
        return {}
    (out / "pairs.json").write_text(json.dumps(pairs, indent=1))
    sys.path.insert(0, str(REPO / "tools/props/cloud"))
    import similar
    return similar.likeness(pairs, out / "likeness.json", who)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("stage", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--closeups", type=pathlib.Path)
    parser.add_argument("--cloud", action="store_true", help="render and score on rented machines")
    parser.add_argument("--who", default="compare")
    parser.add_argument("--reuse", action="store_true", help="score the renders already in <out>/renders")
    options = parser.parse_args()
    import complete
    place = options.stage.stem
    rows = json.loads(complete.recorded_inventory(place, options.stage).read_text())["rows"]
    for entry in compare(options.stage, rows, options.out, options.closeups, options.cloud, options.who,
                                     options.reuse):
        likeness = "no likeness" if entry["likeness"] is None else f"likeness {entry['likeness']:.2f}"
        print(f"{entry['row']:24} outline {entry['outline']:.2f}  {likeness}  ({entry['view']})")


if __name__ == "__main__":
    main()
