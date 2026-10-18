"""What the materials checks read of a place, from the store (read only): its accepted assembly linked into a folder
of this check's own, the objects it lays and the cameras that look at them.

The store's own checkout writes into the store's cache; this check never writes there. `linked` makes a folder of
read-only links to the stored files instead, so pxr opens the assembly where it lies.
"""
import json
import math
import pathlib

import numpy as np
from pxr import Sdf, Usd, UsdGeom

REPO = pathlib.Path(__file__).resolve().parents[4]
GROUPS = ("Objects", "Structure")
# How far off a camera's line of sight an object may lie and still count as seen by it (degrees beyond half its
# field of view), and how near an object must be to count as seen whatever its angle (metres).
SIGHT_MARGIN = 25.0
ALWAYS_SEEN = 0.5


def linked(store, output, folder):
    """A folder holding a stored output as links to its stored files; the folder."""
    folder = pathlib.Path(folder)
    for name, sha in store.listing(output).items():
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_symlink():
            target.symlink_to(store.objects.path(f"blobs/{sha}"))
    return folder


def root_stage(folder):
    """The place's root OpenUSD file in an assembly folder."""
    found = sorted(pathlib.Path(folder).glob("*.usda"))
    if len(found) != 1:
        raise FileNotFoundError(f"{folder} holds {len(found)} root stages, not one")
    return found[0]


def opened(folder, place):
    """The place's stage opened on its objects and structure only (its neighbours' references left closed)."""
    mask = Usd.StagePopulationMask([Sdf.Path(f"/{place}/{group}") for group in GROUPS])
    return Usd.Stage.OpenMasked(str(root_stage(folder)), mask)


def inventory_rows(place):
    """{row id: row} of the place's inventory, empty for a place with none."""
    path = REPO / "data/inventory" / f"{place}.json"
    return {row["id"]: row for row in json.loads(path.read_text())["rows"]} if path.exists() else {}


def attribute(prim, name):
    """A prim's authored attribute value, or None."""
    found = prim.GetAttribute(name)
    return found.Get() if found and found.HasAuthoredValue() else None


def laid_scale(transforms, prim):
    """How much the prim's placement scales lengths (the cube root of its transform's volume scale)."""
    matrix = np.array(transforms.GetLocalToWorldTransform(prim))[:3, :3]
    return float(abs(np.linalg.det(matrix)) ** (1.0 / 3.0)) or 1.0


def laid_objects(stage, place):
    """Every object the place lays under its objects and structure: {prim, group, model, row, repainted, scale, box:
    [min, max]}."""
    cache = UsdGeom.BBoxCache(Usd.TimeCode(0), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    transforms = UsdGeom.XformCache(Usd.TimeCode(0))
    found = []
    for group in GROUPS:
        root = stage.GetPrimAtPath(f"/{place}/{group}")
        for prim in root.GetChildren() if root else []:
            extent = cache.ComputeWorldBound(prim).ComputeAlignedRange()
            if extent.IsEmpty():
                continue
            found.append({"prim": prim.GetName(), "group": group,
                          "model": attribute(prim, "score:model") or prim.GetName(),
                          "row": attribute(prim, "score:row") or "",
                          "repainted": bool(attribute(prim, "score:repaint_of")),
                          "scale": laid_scale(transforms, prim), "box": [list(extent.GetMin()), list(extent.GetMax())]})
    return found


def cameras(scene, film):
    """[(eye, aim, fov)] of the place's start views (its scene record) and its film's frames."""
    views = list((scene or {}).get("views") or []) + list((film or {}).get("views") or [])
    return [(view["eye"], view["aim"], view.get("fov", 80.0)) for view in views]


def nearest(box, eyes):
    """The distance in metres from the nearest camera that has the box in sight, or None when none has."""
    low, high = np.array(box[0]), np.array(box[1])
    centre = (low + high) / 2
    best = None
    for eye, aim, fov in eyes:
        eye = np.array(eye, dtype=float)
        distance = float(np.linalg.norm(np.clip(eye, low, high) - eye))
        forward = np.array(aim, dtype=float) - eye
        towards = centre - eye
        cosine = np.dot(forward, towards) / ((np.linalg.norm(forward) * np.linalg.norm(towards)) or 1.0)
        off_sight = math.degrees(math.acos(float(np.clip(cosine, -1.0, 1.0))))
        if off_sight > fov / 2 + SIGHT_MARGIN and distance > ALWAYS_SEEN:
            continue
        best = distance if best is None else min(best, distance)
    return best


def asset_file(folder, model):
    """The model's asset file in an assembly folder, or None."""
    path = pathlib.Path(folder) / "assets" / f"{model}.usdc"
    return path if path.exists() else None
