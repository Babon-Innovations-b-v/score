"""A model's feet: where it stands on what is under it, and whether they lie in one plane.

A foot is a cluster, across (x) and along (z), of the points within `band` of the model's lowest point, two points
joined when they lie closer than `link`; its height is its lowest point. A model whose feet do not lie in one plane in
its own frame (+y up) tips onto three of them when dropped and leaves the others in the air: the greenhouse's water
tank (take water_tank-r1, 2026-10-12) stood on four legs ending 0, 2.2, 5.2 and 12.7 cm over its lowest, and the drop
tipped it 7.5 degrees, one foot 7 cm off the floor. Used in three places: the paint levels a take's feet before its
bake (`level`), the resting triage judges each foot of a laid object, and the settle refuses a tip that uneven feet
cause.
"""
import numpy as np

# Points sampled over a mesh's surface beside its vertices, so a foot of a few vertices (a box leg's four corners, a
# tenth of a metre apart) is still one cluster.
SAMPLES = 20000


def surface_points(vertices, faces):
    """A mesh's vertices, then SAMPLES points over its surface (seeded): the first len(vertices) rows are the
    vertices."""
    import trimesh
    mesh = trimesh.Trimesh(np.asarray(vertices, dtype=np.float64), np.asarray(faces), process=False)
    samples = mesh.sample(SAMPLES, seed=0) if mesh.area > 0 else np.zeros((0, 3))
    return np.vstack([mesh.vertices, samples])


def feet(points, band, link):
    """The feet of points standing on +y: [(indices into points, lowest y)], lowest first; [] for no points."""
    points = np.asarray(points, dtype=np.float64)
    if not len(points):
        return []
    low = np.nonzero(points[:, 1] <= points[:, 1].min() + band)[0]
    cluster = linked(points[low][:, [0, 2]], link)
    found = [(low[cluster == index], float(points[low[cluster == index], 1].min())) for index in range(cluster.max() + 1)]
    return sorted(found, key=lambda foot: foot[1])


def linked(flat, link):
    """Each point's cluster, two points joined when they lie within `link`, numbered by each cluster's first point:
    the components every pair within `link` gives (as scipy's connected_components numbers them), found without
    listing the pairs. A grid of squares whose diagonal is `link` joins every point in one square; two squares within
    two of each other join when any of their points lie within `link` (a nearest-point query). Listing the pairs, a
    wide flat base's low band had nearly every pair within reach: garage_vehicle_lift's paint took 28 GB and was
    stopped (env1, 2026-10-28)."""
    from scipy.sparse.csgraph import connected_components
    from scipy import sparse
    from scipy.spatial import cKDTree
    side = link / np.sqrt(2.0)
    squares = np.floor(flat / side).astype(np.int64)
    keys, square_of = np.unique(squares, axis=0, return_inverse=True)
    square_of = square_of.ravel()
    members = [np.nonzero(square_of == index)[0] for index in range(len(keys))]
    trees = [cKDTree(flat[found]) for found in members]
    where = {tuple(key): index for index, key in enumerate(keys)}
    reach = np.nextafter(link, np.inf)  # query_pairs joins at a distance of `link` itself
    first, second = [], []
    for index, key in enumerate(keys):
        for across in range(-2, 3):
            for along in range(-2, 3):
                other = where.get((key[0] + across, key[1] + along))
                if other is None or other <= index:
                    continue
                near, _ = trees[other].query(flat[members[index]], k=1, distance_upper_bound=reach)
                if np.isfinite(near).any():
                    first.append(index)
                    second.append(other)
    joins = sparse.coo_matrix((np.ones(len(first)), (first, second)), shape=(len(keys), len(keys)))
    _, square_cluster = connected_components(joins, directed=False)
    cluster = square_cluster[square_of]
    _, firsts = np.unique(cluster, return_index=True)
    order = np.argsort(np.argsort(firsts))  # renumbered by each cluster's first point, as the pairs' graph numbers them
    return order[cluster]


def model_scale(points):
    """(height, footprint diagonal) of points standing on +y: the lengths a model's own-frame shares are of."""
    points = np.asarray(points, dtype=np.float64)
    span = points.max(axis=0) - points.min(axis=0)
    return float(span[1]), float(np.hypot(span[0], span[2]))


def level(vertices, faces, band, link, tolerance, most):
    """A mesh's vertices with every foot over `tolerance` above the lowest one brought down onto the level plane through it, each
    foot's points stretched over the band (a point at the foot's bottom moved the whole gap, one at the band's top not
    at all), when the model has three feet or more; feet joined into one cluster are one foot and left as they are.

    The level plane, not the plane through three of the feet: the model is generated upright in its own frame, so a
    plane through uneven feet leans the whole model (the water tank's 7.5 degrees), and turning it level again leaves
    a foot in the air; stretching the short legs keeps it upright with every foot down. A foot over `most` above the
    lowest is no short leg but a fault of the model, and a foot with no vertex in the band cannot be stretched: neither
    is moved, both come back in `refused`.
    The feet are found on the mesh's surface (surface_points), its vertices moved. Returns (vertices, {"feet": count,
    "gaps": each foot's gap before, "levelled": gaps brought down, "refused": gaps over most})."""
    points = np.array(vertices, dtype=np.float64)
    found = [(members[members < len(points)], low) for members, low in feet(surface_points(points, faces), band, link)]
    lowest = found[0][1] if found else 0.0
    gaps = [round(height - lowest, 6) for _, height in found]
    record = {"feet": len(found), "gaps": gaps, "levelled": [], "refused": []}
    if len(found) < 3:
        return points, record
    top = points[:, 1].min() + band
    for (members, height), gap in zip(found, gaps):
        if gap <= tolerance:
            continue
        if gap > most or not len(members):
            record["refused"].append(gap)
            continue
        reach = np.clip((top - points[members, 1]) / (top - height), 0.0, 1.0)
        points[members, 1] -= gap * reach
        record["levelled"].append(gap)
    return points, record
