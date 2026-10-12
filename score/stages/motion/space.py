"""The motion stage's measures of space, read off the composed stage: each mover's own shape (the convex hull of its
meshes in its own frame) and where it stands at a moment, the still things round it as points on their surfaces, and
how deep one thing reaches into a mover's hull."""
import numpy as np
from pxr import Usd, UsdGeom

# Scopes of a place's stage that are not things a mover can strike: the sky, the lights, the sounds, the materials,
# and the ground and water, which the `grounded` gate judges instead.
NOT_THINGS = ("Sky", "Lights", "Sound", "Library", "Environment", "Looks", "Water", "Terrain", "Ground", "Ground_look",
              "Effects")
GROUNDS = ("Ground", "Terrain")
WATERS = ("Water",)
# What a code-built mesh says it plainly is (tools/usd/placeholders.py's `score:plain`) when it is a surface, not a
# thing: a neighbour's harbour (the far city's) is water wherever it stands in the stage.
PLAIN_SURFACES = {"water": "water", "ground": "ground", "sky": "sky"}
# How many points a mover's hull is built from at most (a ferry's mesh is 54,000): a seeded pick of its vertices.
HULL_POINTS = 20000
# A still triangle meeting a mover's sweep is cut until no side is longer than this many sampling spacings.
SPLIT_LONGEST = 8


def shown_meshes(prim):
    """Every mesh under a prim that is drawn: not a guide or proxy (a collision shape), not made invisible."""
    found = []
    for each in Usd.PrimRange(prim):
        if not each.IsA(UsdGeom.Mesh):
            continue
        imageable = UsdGeom.Imageable(each)
        if imageable.ComputePurpose() in (UsdGeom.Tokens.guide, UsdGeom.Tokens.proxy):
            continue
        if imageable.ComputeVisibility() == UsdGeom.Tokens.invisible:
            continue
        found.append(each)
    return found


def world_matrix(prim, code):
    return np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(code))


def mesh_triangles(mesh, code):
    """A mesh's points in the world at a time code and its faces cut into triangles (index triples)."""
    geometry = UsdGeom.Mesh(mesh)
    points = np.asarray(geometry.GetPointsAttr().Get(code) or [], dtype=np.float64)
    if not len(points):
        return np.zeros((0, 3)), np.zeros((0, 3), dtype=np.int64)
    matrix = world_matrix(mesh, code)
    world = points @ matrix[:3, :3] + matrix[3, :3]
    counts = np.asarray(geometry.GetFaceVertexCountsAttr().Get(code) or [], dtype=np.int64)
    indices = np.asarray(geometry.GetFaceVertexIndicesAttr().Get(code) or [], dtype=np.int64)
    triangles, first = [], 0
    for count in counts:  # a fan from each face's first corner
        corners = indices[first:first + count]
        triangles += [(corners[0], corners[step], corners[step + 1]) for step in range(1, count - 1)]
        first += count
    return world, np.asarray(triangles, dtype=np.int64).reshape(-1, 3)


def surface_points(points, triangles, spacing, seed=0):
    """Points over the triangles about `spacing` apart (each triangle's corners, and its inside by area), so a wall
    with few corners still shows where it stands."""
    if not len(triangles):
        return points
    corners = points[triangles]
    areas = 0.5 * np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1)
    wanted = np.floor(areas / (spacing * spacing)).astype(np.int64)
    draws = np.random.default_rng(seed)
    which = np.repeat(np.arange(len(triangles)), wanted)
    first, second = draws.random(len(which)), draws.random(len(which))
    flip = first + second > 1.0
    first[flip], second[flip] = 1.0 - first[flip], 1.0 - second[flip]
    inside = (corners[which, 0] + first[:, None] * (corners[which, 1] - corners[which, 0])
              + second[:, None] * (corners[which, 2] - corners[which, 0]))
    return np.concatenate([points, inside])


def thinned(points, spacing):
    """One point to each cube `spacing` wide: as near a surface as before, far fewer to test."""
    if not len(points):
        return points
    _, first = np.unique(np.floor(points / spacing).astype(np.int64), axis=0, return_index=True)
    return points[np.sort(first)]


class Shape:
    """A mover's shape in its own frame: the convex hull of its drawn meshes where they stand at `code`, its points
    over their surfaces, its lowest corners."""

    def __init__(self, prim, code, spacing):
        from scipy.spatial import ConvexHull
        self.prim = prim
        to_own = np.linalg.inv(world_matrix(prim, code))
        own_points, own_surface = [], []
        for mesh in shown_meshes(prim):
            points, triangles = mesh_triangles(mesh, code)
            if len(points):
                own_points.append(points @ to_own[:3, :3] + to_own[3, :3])
                surface = surface_points(points, triangles, spacing)
                own_surface.append(surface @ to_own[:3, :3] + to_own[3, :3])
        if not own_points:
            raise ValueError(f"{prim.GetPath()} draws no mesh")
        points = np.concatenate(own_points)
        if len(points) > HULL_POINTS:
            points = points[np.random.default_rng(0).choice(len(points), HULL_POINTS, replace=False)]
        self.hull = ConvexHull(points)
        self.corners = points[self.hull.vertices]
        self.surface = thinned(np.concatenate(own_surface), spacing)
        self.low, self.high = self.corners.min(axis=0), self.corners.max(axis=0)
        self.middle = (self.low + self.high) / 2
        self.radius = float(np.linalg.norm(self.corners - self.middle, axis=1).max())
        self.poses = {}

    def placed(self, code):
        """The mover's own-to-world transform at a time code (each read once)."""
        if code not in self.poses:
            self.poses[code] = world_matrix(self.prim, code)
        return self.poses[code]

    def depth(self, world_points, code):
        """How deep each world point lies inside the mover's hull at a time code, metres (below zero outside)."""
        if not len(world_points):
            return np.zeros(0)
        to_own = np.linalg.inv(self.placed(code))
        own = world_points @ to_own[:3, :3] + to_own[3, :3]
        planes = self.hull.equations  # outward normal and offset: inside where normal . x + offset <= 0
        return -(own @ planes[:, :3].T + planes[:, 3]).max(axis=1)

    def in_world(self, own, code):
        matrix = self.placed(code)
        return own @ matrix[:3, :3] + matrix[3, :3]


def swept_box(shape, codes, margin):
    """The world box the mover's hull passes through over the time codes, grown by a margin."""
    spots = np.concatenate([shape.in_world(shape.corners, code) for code in codes])
    return spots.min(axis=0) - margin, spots.max(axis=0) + margin


def scope_of(prim, place):
    """The place's scope a prim stands in (Objects, Structure, Water ...)."""
    parts = str(prim.GetPath()).split("/")
    return parts[2] if len(parts) > 2 and parts[1] == place else ""


def plainly(mesh):
    """What surface a code-built mesh says it plainly is (water, ground, sky), or None."""
    attribute = mesh.GetAttribute("score:plain")
    return PLAIN_SURFACES.get(attribute.Get()) if attribute and attribute.HasValue() else None


def still_meshes(stage, place, movers):
    """Every drawn mesh of the place a mover could strike: not in a scope that is no thing, not a plain surface, not
    part of a mover."""
    moving = [str(path) for path in movers]
    found = []
    for mesh in shown_meshes(stage.GetPrimAtPath(f"/{place}")):
        path = str(mesh.GetPath())
        inside = any(path == each or path.startswith(each + "/") for each in moving)
        if scope_of(mesh, place) in NOT_THINGS or plainly(mesh) or inside:
            continue
        found.append(mesh)
    return found


def mesh_box(mesh, boxes):
    box = boxes.ComputeWorldBound(mesh).ComputeAlignedRange()
    return np.asarray(box.GetMin(), dtype=np.float64), np.asarray(box.GetMax(), dtype=np.float64)


def overlaps(first, second):
    return bool(np.all(first[0] <= second[1]) and np.all(second[0] <= first[1]))


def corners_near(corners, box, spacing):
    """The triangles (corner triples) that meet the box, each cut in four until none meeting it is longer than
    SPLIT_LONGEST spacings: a wall's one big quad is sampled only where the mover passes."""
    while True:
        near = np.all(corners.max(axis=1) >= box[0], axis=1) & np.all(corners.min(axis=1) <= box[1], axis=1)
        corners = corners[near]
        longest = np.linalg.norm(corners - np.roll(corners, 1, axis=1), axis=2).max(axis=1) if len(corners) else []
        long = np.asarray(longest) > SPLIT_LONGEST * spacing
        if not np.any(long):
            return corners
        first, second, third = (corners[long][:, index] for index in range(3))
        halves = [(first + second) / 2, (second + third) / 2, (third + first) / 2]
        pieces = [np.stack(triple, axis=1) for triple in ((first, halves[0], halves[2]), (halves[0], second, halves[1]),
                                                          (halves[2], halves[1], third), tuple(halves))]
        corners = np.concatenate([corners[~long], *pieces])


def still_points_near(meshes, box, code, spacing):
    """{mesh path: points over its surface} for each still mesh whose box meets `box`, only the points inside it."""
    found, boxes = {}, UsdGeom.BBoxCache(code, ["default", "render"])
    for mesh in meshes:
        if not overlaps(mesh_box(mesh, boxes), box):
            continue
        points, triangles = mesh_triangles(mesh, code)
        corners = corners_near(points[triangles], box, spacing) if len(triangles) else np.zeros((0, 3, 3))
        points = points[np.all((points >= box[0]) & (points <= box[1]), axis=1)]
        spots = surface_points(np.concatenate([points, corners.reshape(-1, 3)]),
                               np.arange(len(corners) * 3).reshape(-1, 3) + len(points), spacing)
        spots = thinned(spots[np.all((spots >= box[0]) & (spots <= box[1]), axis=1)], spacing)
        if len(spots):
            found[str(mesh.GetPath())] = spots
    return found


def surface_meshes(stage, place, surface):
    """The place's meshes of a surface ("water" or "ground"): its own scopes for it, and any mesh that plainly is it."""
    scopes = WATERS if surface == "water" else GROUNDS
    return [mesh for mesh in shown_meshes(stage.GetPrimAtPath(f"/{place}"))
            if scope_of(mesh, place) in scopes or plainly(mesh) == surface]


def heights_under(meshes, spots, code):
    """The height of the highest of the meshes' surfaces under each [x, z] spot (NaN where none lies under it)."""
    heights = np.full(len(spots), np.nan)
    for mesh in meshes:
        points, triangles = mesh_triangles(mesh, code)
        if not len(triangles):
            continue
        corners = points[triangles]
        low, high = corners[:, :, [0, 2]].min(axis=1), corners[:, :, [0, 2]].max(axis=1)
        for index, spot in enumerate(spots):
            near = np.all((low <= spot) & (spot <= high), axis=1)
            if near.any():
                height = height_in(corners[near], spot)
                if height is not None:
                    heights[index] = height if np.isnan(heights[index]) else max(heights[index], height)
    return heights


def height_in(corners, spot):
    """The highest height over [x, z] `spot` of the triangles (corner triples) it lies in, by their barycentric
    weights; None when it lies in none."""
    one, two, three = corners[:, 0], corners[:, 1], corners[:, 2]
    across = ((two[:, 2] - three[:, 2]) * (one[:, 0] - three[:, 0])
              + (three[:, 0] - two[:, 0]) * (one[:, 2] - three[:, 2]))
    usable = np.abs(across) > 1e-12
    one, two, three, across = one[usable], two[usable], three[usable], across[usable]
    off_x, off_z = spot[0] - three[:, 0], spot[1] - three[:, 2]
    first = ((two[:, 2] - three[:, 2]) * off_x + (three[:, 0] - two[:, 0]) * off_z) / across
    second = ((three[:, 2] - one[:, 2]) * off_x + (one[:, 0] - three[:, 0]) * off_z) / across
    third = 1.0 - first - second
    hit = (first >= -1e-9) & (second >= -1e-9) & (third >= -1e-9)
    if not hit.any():
        return None
    return float((first * one[:, 1] + second * two[:, 1] + third * three[:, 1])[hit].max())
