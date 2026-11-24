"""Physics against NVIDIA's authored asset: mass, colliders (there, convex, their volume and how far they stand out
of the drawn mesh), friction; and the two drops' resting poses compared. Colliders are convex pieces, each
{"vertices"} (its hull is taken) with "faces" where the piece came as a mesh, in the model's own frame."""
import numpy as np
import trimesh
from scipy.spatial import ConvexHull

from . import _mesh

GRID = 48  # cells along the colliders' box's longest side when their joined volume is counted
THIN_CELLS = 4  # cells across its thinnest side, at least
MOST_CELLS = 1_000_000  # cells counted at most (the step grows past it)
OVERHANG_POINTS = 2000  # collider surface points whose distance out of the drawn mesh is read
OVERHANG_PERCENTILE = 95
CONVEX_SHARE = 0.98  # a piece whose own volume is under this share of its hull's is not convex
FLAT_SPREAD = 1e-9  # a piece whose thinnest spread is under this share of its widest is flat (rounding, not a wall)


class Flat:
    """The hull of a piece whose points lie in a plane, on a line or at one point (#159: tc6's anesthesia machine had
    a four-cornered card among its 48 hulls, which scipy's ConvexHull refuses): no volume and no inside, its surface
    the points' outline in their plane (none on a line or a point), so it is measured as flat, never an error."""

    def __init__(self, points):
        self.points = points
        self.volume = 0.0
        self.equations = np.array([[0.0, 0.0, 0.0, 1.0]])  # no point lies inside
        middle = points.mean(0)
        _, spread, axes = np.linalg.svd(points - middle, full_matrices=False)
        self.simplices = np.zeros((0, 3), dtype=int)
        if len(spread) > 1 and spread[1] > FLAT_SPREAD * max(spread[0], 1e-12):
            ring = ConvexHull((points - middle) @ axes[:2].T).vertices
            self.simplices = np.stack([np.full(len(ring) - 2, ring[0]), ring[1:-1], ring[2:]], 1)


def hull_of(points):
    """A piece's convex hull (scipy), or its Flat hull when its points span no volume."""
    points = np.asarray(points, dtype=float)
    _, spread, _ = np.linalg.svd(points - points.mean(0), full_matrices=False)
    if len(spread) < 3 or spread[2] <= FLAT_SPREAD * max(spread[0], 1e-12):
        return Flat(points)
    return ConvexHull(points)


def hulls(colliders):
    """Each collider piece's hull (hull_of)."""
    return [hull_of(piece["vertices"]) for piece in colliders]


def convex(piece, hull):
    """Whether a piece is a convex solid: a flat one holds nothing; one given as a mesh must fill its hull (a piece
    given as points is its hull)."""
    if isinstance(hull, Flat):
        return False
    if piece.get("faces") is None:
        return True
    own = trimesh.Trimesh(np.asarray(piece["vertices"], dtype=float), np.asarray(piece["faces"]), process=False)
    return bool(own.is_watertight and abs(own.volume) >= CONVEX_SHARE * hull.volume)


def joined_volume(found):
    """The volume inside any of the hulls: one hull's own, several counted on a grid over their joined box (overlaps
    once) fine enough for THIN_CELLS across its thinnest side (GRID along the longest put no cell inside a sign
    1.2 cm thick and 2 m long, its colliders read as nothing; #163 calibration), up to MOST_CELLS."""
    if len(found) == 1:
        return float(found[0].volume)
    low = np.min([hull.points.min(0) for hull in found], axis=0)
    high = np.max([hull.points.max(0) for hull in found], axis=0)
    sides = np.maximum(high - low, 1e-9)
    step = min(float(sides.max()) / GRID, float(sides.min()) / THIN_CELLS)
    step = max(step, float(np.prod(sides) / MOST_CELLS) ** (1 / 3))
    axes = [np.arange(start + step / 2, end, step) for start, end in zip(low, high)]
    cells = np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)
    inside = np.zeros(len(cells), dtype=bool)
    for hull in found:
        inside |= (cells @ hull.equations[:, :3].T + hull.equations[:, 3] <= 1e-9).all(1)
    return float(inside.sum() * step ** 3)


def overhang(vertices, faces, found):
    """The OVERHANG_PERCENTILE of how far collider surface points lie out of the drawn mesh's convex hull (0 inside
    it). The hull, not the mesh: a sim-ready collider is convex pieces, so over an open crate's well or a chair's
    seat it spans what the drawn mesh leaves open, as NVIDIA's own do (crate_blue_a01's hull stands 12 cm off its
    open mesh); what floats a thing is a collider standing out past the shape's outline."""
    triangles = np.concatenate([hull.points[hull.simplices] for hull in found if len(hull.simplices)])
    corners = triangles.reshape(-1, 3)
    points, _ = _mesh.sampled(corners, np.arange(len(corners)).reshape(-1, 3), OVERHANG_POINTS, seed=7)
    drawn = ConvexHull(np.asarray(vertices, dtype=float)[np.unique(faces)])
    out = (points @ drawn.equations[:, :3].T + drawn.equations[:, 3]).max(1) > 0
    distance = np.zeros(len(points))
    if out.any():
        outline = trimesh.Trimesh(drawn.points, drawn.simplices, process=False)
        distance[out] = trimesh.proximity.closest_point(outline, points[out])[1]
    return float(np.percentile(distance, OVERHANG_PERCENTILE))


def physics(truth, made):
    """{"mass_ratio" made over truth, "true_density" (the truth's mass over its closed volume, else its colliders'),
    "colliders", "convex", "collider_volume_ratio", "overhang", "truth_overhang", "friction_gap"}; a measure whose
    input the made side lacks is left out."""
    truth_hulls = hulls(truth["colliders"])
    truth_volume = joined_volume(truth_hulls)
    closed = trimesh.Trimesh(*_mesh.welded(truth["vertices"], truth["faces"]), process=False)
    found = {"true_density": round(truth["mass"] / (abs(closed.volume) if closed.is_watertight else truth_volume), 2),
             "truth_overhang": round(overhang(truth["vertices"], truth["faces"], truth_hulls), 5)}
    if made.get("mass") is not None:
        found["mass_ratio"] = round(made["mass"] / truth["mass"], 4)
    if made.get("colliders") is not None:
        made_hulls = hulls(made["colliders"]) if made["colliders"] else []
        found["colliders"] = len(made_hulls)
        found["convex"] = all(convex(piece, hull) for piece, hull in zip(made["colliders"], made_hulls))
        if made_hulls:
            found["collider_volume_ratio"] = round(joined_volume(made_hulls) / truth_volume, 4)
            found["overhang"] = round(overhang(made["vertices"], made["faces"], made_hulls), 5)
    if made.get("friction") is not None and truth.get("friction") is not None:
        found["friction_gap"] = round(abs(made["friction"] - truth["friction"]), 4)
    return found


def rest_of(motion, vertices):
    """(where up points at rest, the box middle's height over the lowest point at rest) of a model moved by its
    drop's 4x4 laid-to-rest motion (its laid up is +Z)."""
    rested = _mesh.moved(vertices, motion)
    middle = _mesh.moved(((vertices.min(0) + vertices.max(0)) / 2)[None], motion)[0]
    return motion[:3, 2] / np.linalg.norm(motion[:3, 2]), float(middle[2] - rested[:, 2].min())


def rested(truth_motion, truth_vertices, made_motion, made_vertices):
    """{"rest_up": degrees between the two rests' ups, "rest_height": the gap in metres between their middles'
    heights over their lowest points}: the made model's drop against the truth's (each a Newton drop of the model
    on its convex colliders, tools/usd/drop.py, run by the bench's runner)."""
    truth_up, truth_height = rest_of(np.asarray(truth_motion, dtype=float), truth_vertices)
    made_up, made_height = rest_of(np.asarray(made_motion, dtype=float), made_vertices)
    return {"rest_up": round(float(np.degrees(np.arccos(np.clip(truth_up @ made_up, -1.0, 1.0)))), 3),
            "rest_height": round(abs(made_height - truth_height), 5)}
