"""Neighbours inside a room (the owner, 2026-10-18: a section of the walkway tube cut through the airlock room, its
curved panels left and right of the inner door). On a place's assembled OpenUSD stage (read only), the room is the
convex hull of its own walls, floor and ceiling (its Objects' and Structure's children named for one, ROOM_WORDS);
a neighbour's geometry (anything under /<place>/Places) with a point deeper than INSET inside that hull stands in
the room. A place with its own ground (/<place>/Outside) is outdoors and has no room.

    found = room.intrusions(stage, place)   # [{"prim", "inside", "points", "depth"}], deepest first; [] outdoors
"""
import re

import numpy as np
from pxr import Usd, UsdGeom
from scipy.spatial import ConvexHull

from score.stages.terrain import sight

ROOM_WORDS = re.compile(r"wall|floor|roof|ceiling|deck", re.I)
INSET = 0.25  # metres inside the room's shell: a tube's end meeting the wall at a door is not inside
GROUPS = ("Objects", "Structure")


def shell_prims(stage, place):
    """The place's own wall, floor and ceiling prims."""
    found = []
    for group in GROUPS:
        holder = stage.GetPrimAtPath(f"/{place}/{group}")
        if holder:
            found += [child for child in holder.GetChildren() if ROOM_WORDS.search(child.GetName())]
    return found


def shell_points(stage, place, cache):
    """Every point of the place's walls, floor and ceiling in the stage's frame."""
    parts = []
    for holder in shell_prims(stage, place):
        for prim in Usd.PrimRange(holder):
            made = sight.mesh_triangles(prim, cache) if prim.IsA(UsdGeom.Mesh) else None
            if made is not None:
                parts.append(made[0])
    return np.concatenate(parts) if parts else np.zeros((0, 3))


def depth_inside(hull, points):
    """Each point's depth inside the hull (its distance to the nearest face; negative outside)."""
    return -(points @ hull.equations[:, :3].T + hull.equations[:, 3]).max(axis=1)


def neighbour_meshes(stage, place):
    """Every drawn mesh of the place's neighbours."""
    holder = stage.GetPrimAtPath(f"/{place}/Places")
    if not holder:
        return []
    return [prim for prim in Usd.PrimRange(holder) if prim.IsA(UsdGeom.Mesh) and sight.is_seen(prim, ())]


def intrusions(stage, place):
    """Each neighbour mesh with points deeper than INSET inside the room, deepest first; [] for an outdoor place or
    one with no shell."""
    if stage.GetPrimAtPath(f"/{place}/Outside"):
        return []
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    shell = shell_points(stage, place, cache)
    if len(shell) < 4:
        return []
    hull = ConvexHull(shell)
    found = []
    for prim in neighbour_meshes(stage, place):
        made = sight.mesh_triangles(prim, cache)
        if made is None:
            continue
        depths = depth_inside(hull, made[0])
        inside = depths > INSET
        if inside.any():
            found.append({"prim": str(prim.GetPath()), "inside": int(inside.sum()), "points": len(depths),
                          "depth": round(float(depths.max()), 2)})
    return sorted(found, key=lambda item: -item["depth"])
