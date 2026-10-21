"""Runs inside Blender: the code-built bodies of big objects seen up close (pieces_bodies.py, bodies.py: the owner's rule
of 2026-10-18, PRD #10), each at the size the layout lays it, its parts naming their library material, and what of
each the room can see.

    import pieces; whole = pieces.build("console_body", (2.4, 1.1, 0.9), {})

Sizes are (wide, tall, deep) in metres in the kit frame (shapes.py): front toward -z, the back on the wall. The old
kits' builders (the hub's, the camp's, the Earth rooms', the ship rooms' and the hangar ship's plates, trims and
fittings) went with the old kits on 2026-10-21: the owner, "remove all old, all old stuff is retired".
"""

import json
import math

import numpy as np

import bmesh
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

import pieces_bodies
import shapes


def parts_seen(parts, samples=80, views=((0.0, 0.0), (35.0, 0.0), (-35.0, 0.0), (0.0, 30.0), (0.0, -30.0))):
    """Per part name (an object's name before Blender's .001), the share of its front-facing surface the room can see
    from in front of the piece (five views, straight on and 35/30 degrees off): a slat buried in its plate reads 0.
    Sampled at points spread over its surface by area (a face's middle alone hid a spoke behind the boss it runs
    through), a point seen when nothing of the piece lies between it and a view it faces."""
    together = bmesh.new()
    for part in parts:
        together.from_mesh(part.data)
    tree = BVHTree.FromBMesh(together)
    together.free()
    directions = []
    for across, up in views:
        turn = Matrix.Rotation(math.radians(across), 3, "Z") @ Matrix.Rotation(math.radians(up), 3, "X")
        directions.append((turn @ Vector((0.0, 1.0, 0.0))).normalized())  # the kit's front (-z) is Blender's +y
    counts = {}
    for part in parts:
        seen = shown = 0
        for point, normal in surface_points(part, samples):
            facing = [direction for direction in directions if normal.dot(direction) > 0.1]
            if not facing:
                continue
            shown += 1
            start = point + normal * 0.0003
            seen += any(tree.ray_cast(start, direction, 10.0)[0] is None for direction in facing)
        total = counts.setdefault(part.name.split(".")[0], [0, 0])
        total[0] += seen
        total[1] += shown
    return {name: round(seen / shown, 3) if shown else 0.0 for name, (seen, shown) in sorted(counts.items())}


def surface_points(part, count):
    """`count` points on a part's surface, spread by area (a fixed seed, so a build reads the same each time), each
    with its triangle's normal."""
    mesh = part.data
    mesh.calc_loop_triangles()
    triangles = list(mesh.loop_triangles)
    if not triangles:
        return []
    areas = np.array([triangle.area for triangle in triangles])
    chosen = np.random.default_rng(7).choice(len(triangles), size=count, p=areas / areas.sum())
    weights = np.random.default_rng(11).dirichlet((1.0, 1.0, 1.0), size=count)
    found = []
    for index, weight in zip(chosen, weights):
        triangle = triangles[index]
        corners = [mesh.vertices[vertex].co for vertex in triangle.vertices]
        found.append((sum((corner * float(share) for corner, share in zip(corners, weight)), Vector()),
                      triangle.normal))
    return found


BUILDERS = dict(pieces_bodies.BUILDERS)


def build(kind, size, laid, name):
    """One code-built piece of `kind` at `size`, as one object whose material slots name library materials; which of
    its parts the room can see (parts_seen) rides on it as the custom property `parts_seen`, as JSON."""
    parts = BUILDERS[kind](tuple(size), laid)
    seen, off = checked_from_the_room(kind, parts)
    whole = shapes.joined(parts, name)
    whole["parts_seen"] = json.dumps(seen)
    whole["prints_off"] = json.dumps(off)
    return whole


def checked_from_the_room(kind, parts):
    """parts_seen and prints_off from the front the room sees a body from."""
    return parts_seen(parts), prints_off(parts)


PRINT_PARTS = ("label", "sticker", "sheet", "note", "decal", "outlines")
# How far the face under a print may step in or out across its footprint before the print counts as lying over a
# part (a vent's hood, a handle, a bolt): a flat clear area reads under 2 mm.
FLAT_UNDER = 0.002


def prints_off(parts):
    """The prints (labels, stickers, sheets, notes) that do not lie on a clear flat area (round six: a decal is placed
    by rule, never over a vent, a handle or a tool): for each, rays from just in front of its back face straight back
    on a 4 x 4 grid over its footprint, against the rest of the piece; a ray meeting nothing, or the hits stepping
    more than FLAT_UNDER, puts the print off. Their part names, numbered."""
    found = []
    for index, part in enumerate(parts):
        if part.name.split(".")[0] not in PRINT_PARTS:
            continue
        others = [other for other in parts if other is not part]
        together = bmesh.new()
        for other in others:
            together.from_mesh(other.data)
        tree = BVHTree.FromBMesh(together)
        together.free()
        points = [vertex.co for vertex in part.data.vertices]
        back = min(point.y for point in points)  # Blender's +y is the kit's front: the back face has the least y
        middle_x = sorted(point.x for point in points)
        middle_z = sorted(point.z for point in points)
        span_x, span_z = (middle_x[0], middle_x[-1]), (middle_z[0], middle_z[-1])
        depths = []
        for across in np.linspace(0.15, 0.85, 4):
            for up in np.linspace(0.15, 0.85, 4):
                start = Vector((span_x[0] + (span_x[1] - span_x[0]) * across, back + 0.0005,
                                span_z[0] + (span_z[1] - span_z[0]) * up))
                hit = tree.ray_cast(start, Vector((0.0, -1.0, 0.0)), 0.05)[0]
                depths.append(None if hit is None else hit.y)
        if None in depths or max(depths) - min(depths) > FLAT_UNDER:
            found.append(f"{part.name.split('.')[0]}#{index}")
    return found
