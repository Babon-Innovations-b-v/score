"""A floor thing's model stood on a footing that holds its weight, by the resting check's measure and the drop's: where
what it touches at its lowest point (within TOLERANCE) does not hold its weight, its part hanging under the footing
that would hold it is brought up level with that footing (every point of it within the cut over its lowest laid on
its lowest), in the place's own copy of its baked asset (even_feet.level_asset, before its feet are levelled).

assembly@old_station, 2026-11-12: its central hub stood on a foot at its back edge 16 to 24 cm under its four legs,
its weight 1.75 m outside what it touched, and the drop tipped it 3 degrees (cut 0.19 m); its right module's cradles
slope 8 cm along their length, so it touched at one end of each, its weight 0.6 m outside (cut 0.06 m); its left and
right tunnels, round tubes, touched along a strip beside their weight (2 to 11 cm outside by the drop's measure, the
middle of their hull's mass), and the drop rolled the left one 9 degrees (cut 0.10 and 0.09 m); its back tunnel's
sole, 1 cm deep, ends 4 cm from its hull's middle of mass, and the drop rolled it 45 degrees (cut 0.02 m). Each stands
on what the cut lays level at its foot, both its weights BALANCE inside it.

    stood(points, triangles)   (the points, [the cut, metres]): the model's points with its footing cut at the least
                               height (CUT_STEP apart, REACH at most) whose footing holds both weights BALANCE inside,
                               when its footing as made does not hold them (the surface's middle BALANCE outside it, as
                               the triage tips it, or the hull's middle of mass under BALANCE inside its sole, as the
                               drop rolls it); [] and the points as they are when it holds them or no cut within REACH
                               does
    stands(points, triangles)  whether its footing holds it as made or cut (laid_flat lays down one that never stands)
"""
import pathlib
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))

# The most a footing is cut, metres: old_station's hub was cut 0.19 m.
REACH = 0.25
# The heights a cut is tried at, metres apart.
CUT_STEP = 0.01
# How far over a model's lowest point, metres, the face its convex hull rests on in the drop is read.
SOLE = 0.01
# How many points of its surface join a model's vertices to find its footing.
SAMPLES = 20000


def stood(points, triangles):
    """The points (+y up, metres, as laid) with the footing cut where it does not hold the model's weight (module
    docstring), and the cut ([] with none)."""
    cut = needed_cut(points, triangles)
    if not cut:
        return np.asarray(points, dtype=np.float64), []
    return cut_at(points, cut), [round(cut, 4)]


def stands(points, triangles):
    """Whether the model stands on a footing that holds its weight, as made or cut (stood)."""
    return needed_cut(points, triangles) is not None


def needed_cut(points, triangles):
    """The least cut (CUT_STEP apart, REACH at most) whose footing holds the model's weight: 0.0 when its footing as
    made holds it, None when no cut does."""
    import trimesh
    points = np.asarray(points, dtype=np.float64)
    mesh = trimesh.Trimesh(points, np.asarray(triangles).reshape(-1, 3), process=False)
    if mesh.area <= 0:
        return 0.0
    dense = np.vstack([points, mesh.sample(SAMPLES, seed=0)])
    weights = weights_of(mesh)
    if holds(weights, dense, 0.0, made=True):
        return 0.0
    return next((float(height) for height in np.arange(CUT_STEP, REACH + CUT_STEP / 2, CUT_STEP)
                 if holds(weights, dense, float(height))), None)


def weights_of(mesh):
    """Where the model's weight falls (x, z): the middle of its surface by area, which the resting triage reads
    (resting.weight_at), and the middle of its convex hull's mass, which the drop's one-hull body falls by."""
    import resting
    return [np.asarray(resting.weight_at(mesh), float), np.asarray(mesh.convex_hull.center_mass, float)[[0, 2]]]


def holds(weights, dense, cut, made=False):
    """Whether the footing cut at `cut` over the lowest point (the points the cut brings level with it) holds the
    weights: each BALANCE inside it. As made (`made`): the surface's middle at most BALANCE outside the points within
    TOLERANCE over the lowest (the triage's tip), and the hull's middle of mass BALANCE inside the points within
    SOLE over it, the face the drop's one-hull body rests on (a round tunnel rolled 45 degrees on a sole 4 cm beside
    it)."""
    import triage
    lowest = float(dense[:, 1].min())

    def footing(band):
        return dense[dense[:, 1] <= lowest + band][:, [0, 2]]
    if made:
        return inside_by(weights[0], footing(triage.TOLERANCE)) >= -triage.BALANCE and \
            inside_by(weights[1], footing(SOLE)) >= triage.BALANCE
    return min(inside_by(weight, footing(cut)) for weight in weights) >= triage.BALANCE


def inside_by(point, footprint):
    """How far a point (x, z) lies inside the convex hull of the footprint's points (x, z), negative outside it;
    -inf with no hull (fewer than three points, or all on one line)."""
    from scipy.spatial import ConvexHull, QhullError
    if len(footprint) < 3:
        return -np.inf
    try:
        hull = ConvexHull(footprint)
    except QhullError:
        return -np.inf
    across = hull.equations[:, :2] @ np.asarray(point, float) + hull.equations[:, 2]
    if np.all(across <= 0):
        return float(-across.max())
    corners = footprint[hull.vertices]
    ends = np.roll(corners, -1, axis=0)
    edges = ends - corners
    share = np.clip(np.einsum("ij,ij->i", point - corners, edges) / np.einsum("ij,ij->i", edges, edges), 0.0, 1.0)
    return -float(np.min(np.linalg.norm(corners + edges * share[:, None] - point, axis=1)))


def cut_at(points, cut):
    """The points with every one within `cut` over the lowest brought level with the lowest: the part hanging under
    the footing flattened onto it, the rest as made."""
    points = np.array(points, dtype=np.float64)
    lowest = float(points[:, 1].min())
    points[points[:, 1] <= lowest + cut, 1] = lowest
    return points
