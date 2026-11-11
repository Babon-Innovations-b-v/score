"""A floor thing's model laid with every foot down by the resting check's own measure: each foot the triage would read
off the level plane through the model's lowest point (its foot clusters, triage.foot_clusters: LOW_BAND over the
lowest, FOOT_LINK apart, in metres at the size the place lays it) stretched down onto it, as the paint's feet.level
stretches a short leg, in the place's own copy of its baked asset.

Campgrounds, 2026-11-11: its habitat domes stood on flat ground with eleven rim feet 3.1 to 8.8 cm up and its
communications towers with a leg 3.4 cm up, and the settle's drop tipped the domes onto three feet, the others up to
9.6 cm off. The paint had passed both as "feet in one plane": it links a foot's points within 3% of the model's
footprint diagonal (0.42 m on the 14 m dome, 0.14 m on the tower), so the rim's dips and the tower's legs were each one
foot to it, where the resting check links them within 5 cm. Levelled here, not in the paint, whose every take and
bake a change there makes again.

    evened(folder, place)   [(model, the gaps brought down, metres)]: each model a floor thing of the place lays
                            (its anchor the floor, not mounted or fixed), from an asset of the folder's own
                            (assets/<model>.usdc, a copy, never a link into the store), at one size wherever it is
                            laid, with a foot off: its drawn mesh's feet brought down and its collision hull made
                            again round it; saved in place
"""
import os
import pathlib
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))

# Times a model's feet are found again and levelled: a foot brought down can leave a part of it that was linked
# through it a foot of its own.
ROUNDS = 3
# How far apart the sizes a model is laid at may be and still be levelled as one (a share).
SAME_SIZE = 0.01


def evened(folder, place):
    """Each floor thing's model of the place at `folder` with every foot down (level_feet), in its own asset:
    [(model, the gaps brought down)], the models with none left out."""
    from pxr import Usd, UsdGeom
    stage = Usd.Stage.Open(str(pathlib.Path(folder) / f"{place}.usda"))
    things = stage.GetPrimAtPath(f"/{place}/Objects")
    sizes = {}
    for prim in (things.GetChildren() if things else []):
        geo = prim.GetChild("geo")
        if geo.IsValid() and geo.IsA(UsdGeom.Mesh) and floor_thing(prim):
            matrix = np.asarray(UsdGeom.Xformable(geo).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
            sizes.setdefault(own_asset(geo, folder), []).append(np.linalg.norm(matrix[:3, :3], axis=1))
    found = []
    for asset, scales in sorted(sizes.items(), key=lambda item: str(item[0])):
        scales = np.array(scales)
        if asset is None or np.ptp(scales) > SAME_SIZE * scales.max():
            continue
        levelled = level_asset(asset, scales[0])
        if levelled:
            found.append((asset.stem, levelled))
    return found


def floor_thing(prim):
    """Whether a laid thing stands on the floor by itself: its row's anchor the floor (or none), not mounted on a wall
    or ceiling (score:mounted) and not fixed where the kit or record lays it (score:fixed)."""
    def said(name):
        return prim.GetAttribute(name).Get() if prim.HasAttribute(name) else None
    return (said("score:anchor") or "floor") == "floor" and not said("score:mounted") and not said("score:fixed")


def own_asset(geo, folder):
    """The asset file holding a laid thing's drawn points, when it is the folder's own copy (under assets/, one link
    to it): a write there changes no other output; else None."""
    stack = geo.GetAttribute("points").GetPropertyStack()
    if not stack:
        return None
    path = pathlib.Path(stack[0].layer.realPath or "")
    assets = (pathlib.Path(folder) / "assets").resolve()
    if path.parent.resolve() != assets or not path.is_file() or os.stat(path).st_nlink != 1:
        return None
    return path


def level_asset(asset, scale):
    """The asset's drawn mesh with its feet down (level_feet, at `scale`: the size it is laid at, per axis) and its
    collision hull made again round it, saved; the gaps brought down ([] and nothing written when none)."""
    import colliders
    from pxr import Gf, Usd, UsdGeom, Vt
    stage = Usd.Stage.Open(str(asset))
    root = stage.GetDefaultPrim()
    mesh = UsdGeom.Mesh(root.GetChild("geo"))
    points = np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float64)
    triangles = np.asarray(mesh.GetFaceVertexIndicesAttr().Get()).reshape(-1, 3)
    levelled, gaps = level_feet(points * scale, triangles)
    if not gaps:
        return []
    points = (levelled / scale).astype(np.float32)
    mesh.GetPointsAttr().Set(Vt.Vec3fArray.FromNumpy(points))
    mesh.GetExtentAttr().Set([Gf.Vec3f(*points.min(axis=0).tolist()), Gf.Vec3f(*points.max(axis=0).tolist())])
    if root.GetChild("collision").IsValid():
        colliders.hull(stage, str(root.GetChild("collision").GetPath()), points)
    stage.GetRootLayer().Save()
    return gaps


def level_feet(points, triangles):
    """A mesh's points (+y up, in metres) with each foot off the level plane through its lowest point (off_feet)
    brought down onto it, its points stretched over the band (one at its bottom moved the whole gap, one at the band's
    top not at all), round after round (ROUNDS) until none is off; and the gaps brought down."""
    import triage
    points = np.array(points, dtype=np.float64)
    gaps = []
    for _ in range(ROUNDS):
        lowest = float(points[:, 1].min())
        top = lowest + triage.LOW_BAND
        moved = False
        for members, foot in off_feet(points, triangles):
            gap = foot - lowest
            points[members, 1] -= gap * np.clip((top - points[members, 1]) / max(top - foot, 1e-6), 0.0, 1.0)
            gaps.append(round(gap, 4))
            moved = True
        if not moved:
            break
    return points, gaps


def off_feet(points, triangles):
    """[(the mesh's points of the foot, its lowest height)] of each foot the resting triage reads off on a level
    ground under the mesh (triage.feet_gaps: a foot whose lowest lies over TOLERANCE above the mesh's lowest and not
    within the outline of a foot that touches), its points the mesh's points in the band nearest one of its own."""
    import triage
    from scipy.spatial import cKDTree
    lowest = float(points[:, 1].min())
    feet = triage.foot_clusters(points, triangles, triage.LOW_BAND)
    down = [members for members, foot in feet if foot - lowest <= triage.TOLERANCE]
    off = [number for number, (members, foot) in enumerate(feet)
           if foot - lowest > triage.TOLERANCE and not triage.within_a_foot(members, down)]
    if not off:
        return []
    labels = np.concatenate([np.full(len(members), number) for number, (members, _) in enumerate(feet)])
    tree = cKDTree(np.vstack([members[:, [0, 2]] for members, _ in feet]))
    band = np.nonzero(points[:, 1] <= lowest + triage.LOW_BAND)[0]
    distance, nearest = tree.query(points[band][:, [0, 2]])
    near = distance <= triage.FOOT_LINK
    return [(band[near & (labels[nearest] == number)], feet[number][1]) for number in off]
