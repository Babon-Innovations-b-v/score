"""What a place's stage collides with, in OpenUSD's own physics schema (UsdPhysics), and the free check that finds
what does not. Every collider is static: nothing here carries a rigid body or a mass (the paper's named gap, objects
are not interactive; the physics stage's trial layer is where a body moves).

    solid(prim, points, triangles)   a structure or ground mesh of the scene record (a wall, floor, ceiling, stair,
                                     ramp, the ground) collides: an exact box when it is one closed box square to its
                                     own frame (boundingCube), else its own triangles simplified (meshSimplification);
                                     a sphere or other primitive by its own shape
    hull(stage, path, points)        a made model's collision: a convex hull round its points, a guide mesh (never
                                     drawn) with a convex hull approximation, as the game's prop scene has
    hull_of(prim)                    a world model file's drawn mesh (a fixture's, a rock's) collides by a convex hull
                                     round itself: no guide prim, so what reads a fixture's meshes reads the same
    faults(stage)                    every solid prim (a gprim of kind structure or ground) with no collision, and
                                     every model (a prim naming its `score:model`) with no collider of its own

A shown place (/<place>/Places) is judged on its own stage, so its prims are not judged here; water is not solid.
"""
import numpy as np
import trimesh
from pxr import Usd, UsdGeom, UsdPhysics, Vt

SOLID_KINDS = ("structure", "ground")
NOT_JUDGED = ("Places",)
# A box's corners and faces are matched this closely (metres, square metres per square metre).
CORNER_TOLERANCE = 1e-5
AREA_TOLERANCE = 1e-4


def triangle_area(points, triangles):
    corners = points[triangles]
    return float(np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]),
                                axis=1).sum() / 2)


def is_square_box(points, triangles):
    """True when the mesh is one closed box square to its own frame: every point its triangles use a corner of their
    bounding box, all eight corners used, and its triangles covering the box's six faces exactly once."""
    points, triangles = np.asarray(points, dtype=np.float64), np.asarray(triangles, dtype=np.int64).reshape(-1, 3)
    if len(triangles) == 0:
        return False
    used = points[np.unique(triangles)]
    low, high = used.min(axis=0), used.max(axis=0)
    size = high - low
    if np.any(size <= CORNER_TOLERANCE):
        return False
    at_low, at_high = np.abs(used - low) <= CORNER_TOLERANCE, np.abs(used - high) <= CORNER_TOLERANCE
    if not np.all(at_low | at_high) or len({tuple(row) for row in at_high.tolist()}) != 8:
        return False
    surface = 2 * (size[0] * size[1] + size[1] * size[2] + size[2] * size[0])
    return abs(triangle_area(points, triangles) - surface) <= AREA_TOLERANCE * surface


def solid(prim, points=None, triangles=None):
    """A static collider on a structure or ground prim: a mesh as an exact box when it is one square to its frame,
    else by its triangles simplified; any other gprim (the ground's ball) by its own shape."""
    UsdPhysics.CollisionAPI.Apply(prim)
    if points is None:
        return
    approximation = UsdPhysics.Tokens.boundingCube if is_square_box(points, triangles) else \
        UsdPhysics.Tokens.meshSimplification
    UsdPhysics.MeshCollisionAPI.Apply(prim).CreateApproximationAttr(approximation)


def hull(stage, path, points):
    """The model's collision: a convex hull round its points, a guide mesh (never drawn) with UsdPhysics' collision
    API and a convex hull approximation."""
    shape = trimesh.convex.convex_hull(np.asarray(points, dtype=np.float64))
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(np.asarray(shape.vertices, dtype=np.float32)))
    mesh.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(shape.faces), 3, dtype=np.int32)))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(np.asarray(shape.faces, dtype=np.int32).reshape(-1)))
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreatePurposeAttr(UsdGeom.Tokens.guide)
    UsdPhysics.CollisionAPI.Apply(mesh.GetPrim())
    UsdPhysics.MeshCollisionAPI.Apply(mesh.GetPrim()).CreateApproximationAttr(UsdPhysics.Tokens.convexHull)
    return mesh


def hull_of(prim):
    """A drawn mesh collides by a convex hull round itself."""
    UsdPhysics.CollisionAPI.Apply(prim)
    UsdPhysics.MeshCollisionAPI.Apply(prim).CreateApproximationAttr(UsdPhysics.Tokens.convexHull)


def collides(prim):
    """True when the prim has the collision API and its collision is not switched off."""
    if not prim.HasAPI(UsdPhysics.CollisionAPI):
        return False
    return UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get() is not False


def kind(prim):
    found = prim.GetAttribute("score:kind")
    return found.Get() if found and found.HasValue() else None


def is_model(prim):
    found = prim.GetAttribute("score:model")
    return bool(found and found.HasValue() and found.Get())


def has_collider(model):
    """True when a gprim of the model, not of a model standing on it, collides."""
    walk = iter(Usd.PrimRange(model, Usd.TraverseInstanceProxies()))
    next(walk)
    for prim in walk:
        if is_model(prim):
            walk.PruneChildren()
        elif prim.IsA(UsdGeom.Gprim) and collides(prim):
            return True
    return False


def faults(stage):
    """[{prim, what, why}] of every solid gprim of the place with no collision and every model with no collider."""
    root = stage.GetDefaultPrim()
    left_out = {root.GetPath().AppendChild(name) for name in NOT_JUDGED}
    found = []
    walk = iter(Usd.PrimRange(root, Usd.TraverseInstanceProxies()))
    for prim in walk:
        if prim.GetPath() in left_out:
            walk.PruneChildren()
        elif prim.IsA(UsdGeom.Gprim) and kind(prim) in SOLID_KINDS and not collides(prim):
            found.append({"prim": str(prim.GetPath()), "what": kind(prim),
                          "why": "a wall, floor, stair or ground nothing can stand on or bump into: no collision"})
        elif is_model(prim) and not has_collider(prim):
            found.append({"prim": str(prim.GetPath()), "what": "model",
                          "why": f"the model {prim.GetAttribute('score:model').Get()} has no collider"})
    return found
