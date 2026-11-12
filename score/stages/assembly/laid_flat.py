"""A floor thing whose model is a slab standing on its edge that no footing holds up laid down on its broad side, in
the place's own copy of its baked asset (even_feet.evened, before the footings and feet): turned a quarter about its
long side, its foot where it stood, toward the side clear of every other thing laid there.

assembly@old_station, 2026-11-12: its power cables, a row the concept shows lying between the modules, were made as
one cable 10 m long that sags in a U between its two ends, 3.46 m up, 9 cm thick, and laid standing on the sag's
bottom: its weight 0.54 m outside the 0.8 m of it that touched, it tipped, and the drop laid it down flat, 90
degrees and 1.87 m off. Laid down here on the side away from the left tunnel, it lies as the drop rests it.

    flattened(stage, folder, place)   [(model, the side it was laid down toward)]: each floor thing of the place
                                      (even_feet.floor_thing) in an asset of its own (even_feet.own_asset) at one size
                                      wherever it is laid, standing on edge (on_edge) with no footing that holds it
                                      (footing.stands), laid down (lay_down) toward a side where none of its laid
                                      copies meets another thing (clear_side), its asset saved; one with no such side
                                      left standing for the resting gate to name
"""
import pathlib
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))

# A slab on its edge: its thin side at most THIN of its height, its long side at least its height.
THIN = 0.1
# How far, metres, a thing laid down may reach into another every way and still be clear of it: the fitting's
# BOARD_CLEAR.
CLEAR = 0.01
# What the scene record and the design build that a thing laid down must keep clear of, beside the other things
# (triage.STATIC_GROUPS): each of their pieces by its own box.
STATICS = ("Structure", "Fixtures", "Shell")


def flattened(stage, folder, place):
    """Each slab on edge of the place at `folder` (its stage open as `stage`) laid down on its broad side (module
    docstring): [(model, the side, its axis and sign in the model's frame)]."""
    from pxr import Usd, UsdGeom
    from score.stages.assembly import even_feet
    things = stage.GetPrimAtPath(f"/{place}/Objects")
    copies = {}
    for prim in (things.GetChildren() if things else []):
        geo = prim.GetChild("geo")
        if geo.IsValid() and geo.IsA(UsdGeom.Mesh) and even_feet.floor_thing(prim):
            matrix = np.asarray(UsdGeom.Xformable(geo).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
            copies.setdefault(even_feet.own_asset(geo, folder), []).append((prim, matrix))
    found = []
    for asset, laid in sorted(copies.items(), key=lambda item: str(item[0])):
        scales = np.array([np.linalg.norm(matrix[:3, :3], axis=1) for _, matrix in laid])
        if asset is None or np.ptp(scales) > even_feet.SAME_SIZE * scales.max():
            continue
        side = laid_down(asset, scales[0], laid, boxes_beside(stage, place, [prim for prim, _ in laid]))
        if side is not None:
            found.append((asset.stem, side))
    return found


def laid_down(asset, scale, laid, others):
    """The asset's model laid down on its broad side when it stands on edge with no footing that holds it and a side
    is clear for every copy (`laid`: [(prim, its geo's world matrix)]) of the `others` boxes; its collision hull made
    again, saved; the side (axis, sign), or None and nothing written."""
    import colliders
    from pxr import Gf, Usd, UsdGeom, Vt
    from score.stages.assembly import footing
    stage = Usd.Stage.Open(str(asset))
    root = stage.GetDefaultPrim()
    mesh = UsdGeom.Mesh(root.GetChild("geo"))
    points = np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float64)
    triangles = np.asarray(mesh.GetFaceVertexIndicesAttr().Get()).reshape(-1, 3)
    axis = on_edge(points * scale)
    if axis is None or footing.stands(points * scale, triangles):
        return None
    side = clear_side(points * scale, scale, axis, laid, others)
    if side is None:
        return None
    turn = turned(axis, side)
    lying = (lay_down(points * scale, axis, turn) / scale).astype(np.float32)
    mesh.GetPointsAttr().Set(Vt.Vec3fArray.FromNumpy(lying))
    mesh.GetExtentAttr().Set([Gf.Vec3f(*lying.min(axis=0).tolist()), Gf.Vec3f(*lying.max(axis=0).tolist())])
    normals = mesh.GetNormalsAttr().Get()
    if normals:
        mesh.GetNormalsAttr().Set(Vt.Vec3fArray.FromNumpy(
            (np.asarray(normals, dtype=np.float64) @ turn.T).astype(np.float32)))
    if root.GetChild("collision").IsValid():
        colliders.hull(stage, str(root.GetChild("collision").GetPath()), lying)
    stage.GetRootLayer().Save()
    return (int(axis), int(side))


def on_edge(points):
    """The model's thin horizontal axis (0 for x, 2 for z) when it is a slab standing on its edge (THIN), else None."""
    size = np.ptp(points, axis=0)
    thin, wide = (0, 2) if size[0] <= size[2] else (2, 0)
    if size[1] <= 0 or size[thin] > THIN * size[1] or size[wide] < size[1]:
        return None
    return thin


def turned(axis, side):
    """The quarter turn about the model's long horizontal axis that brings its up (+y) onto `side` (+1 or -1) of its
    thin `axis`."""
    turn = np.zeros((3, 3))
    long = 2 if axis == 0 else 0
    turn[long, long] = 1.0
    turn[axis, 1] = float(side)  # up goes to the side
    turn[1, axis] = -float(side)  # the side goes down
    return turn


def lay_down(points, axis, turn):
    """The points (at the size laid) turned by `turn` about the middle of their foot along the thin `axis`, its lowest
    kept where it was: the slab lies where it stood, reaching toward the side."""
    points = np.asarray(points, dtype=np.float64)
    pivot = np.array([0.0, float(points[:, 1].min()), 0.0])
    pivot[axis] = float(points[:, axis].min() + points[:, axis].max()) / 2
    lying = (points - pivot) @ turn.T + pivot
    lying[:, 1] += pivot[1] - lying[:, 1].min()
    return lying


def clear_side(points, scale, axis, laid, others):
    """The side (+1 or -1) of the thin `axis` the model (its `points` at the size laid, `scale` of its own) may be laid
    down toward, every copy's box laid down there
    meeting none of the `others` boxes by more than CLEAR every way: first the side its surface's middle leans to
    (+1 when it leans to neither), then the other; None when neither is clear."""
    lean = float(points[:, axis].mean() - (points[:, axis].min() + points[:, axis].max()) / 2)
    for side in ((1, -1) if lean >= 0 else (-1, 1)):
        lying = lay_down(points, axis, turned(axis, side)) / scale
        if all(not meets(world_box(lying, matrix), others) for _, matrix in laid):
            return side
    return None


def world_box(points, matrix):
    """The world box (low, high) of model points under a geo's world `matrix` (row vectors, USD's)."""
    placed = np.c_[points, np.ones(len(points))] @ matrix
    return placed[:, :3].min(axis=0), placed[:, :3].max(axis=0)


def meets(box, others):
    """Whether a box (low, high) reaches into any of the `others` boxes by more than CLEAR every way."""
    low, high = box
    return any(float(np.min(np.minimum(high, other_high) - np.maximum(low, other_low))) > CLEAR
               for other_low, other_high in others)


def boxes_beside(stage, place, own):
    """The world boxes of the place's other laid things (its Objects but `own`, and their children) and of each piece
    of its statics (STATICS)."""
    from pxr import Usd, UsdGeom
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    skipped = {str(prim.GetPath()) for prim in own}
    pieces = []
    for group in ("Objects", *STATICS):
        found = stage.GetPrimAtPath(f"/{place}/{group}")
        pieces += [prim for prim in (found.GetChildren() if found else []) if str(prim.GetPath()) not in skipped]
    boxes = []
    for prim in pieces:
        box = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        if not box.IsEmpty():
            boxes.append((np.asarray(box.GetMin(), float), np.asarray(box.GetMax(), float)))
    return boxes
