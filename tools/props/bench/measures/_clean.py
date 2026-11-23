"""How clean a mesh is, read on its welded corners: closed or open, pieces and crumbs, bad faces, its thinnest wall,
how densely it is cut and how much of it is flat. The same numbers are read on the truth, whose own value is the
reference for the measures a kind sets (triangles, flat share, pieces)."""
import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from score.stages.place_build import shapes

from . import _mesh

CRUMB = 0.001  # a piece under this share of the area is a crumb
WALL_POINTS = 1000  # inward rays for the thinnest wall
WALL_PERCENTILE = 5  # the thinnest wall: this percentile of how far each ray goes before it leaves (the gate's)
RAY_START = 1e-4  # metres a ray starts inside the surface (the gate's)


def edges(faces):
    """(each undirected edge, how many faces hold it, how many edges two faces hold the same way round)."""
    directed = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    undirected, held = np.unique(np.sort(directed, axis=1), axis=0, return_counts=True)
    _, same_way = np.unique(directed, axis=0, return_counts=True)
    return undirected, held, int((same_way > 1).sum())


def pieces(corners, faces, area):
    """(the area of each piece, largest first): faces joined through shared corners."""
    rows = np.concatenate([faces[:, 0], faces[:, 1]])
    columns = np.concatenate([faces[:, 1], faces[:, 2]])
    graph = coo_matrix((np.ones(len(rows)), (rows, columns)), shape=(len(corners), len(corners)))
    _, label = connected_components(graph, directed=False)
    return np.sort(np.bincount(label[faces[:, 0]], weights=area))[::-1]


def thinnest(corners, faces):
    """(the thinnest wall in metres, the share of inward rays that met the far side): rays from surface points
    against their face's normal."""
    mesh = trimesh.Trimesh(corners, faces, process=False)
    points, picked = _mesh.sampled(corners, faces, WALL_POINTS, seed=5)
    inward = -mesh.face_normals[picked]
    starts = points + inward * RAY_START
    where, index, _ = mesh.ray.intersects_location(starts, inward, multiple_hits=False)
    if len(index) == 0:
        return 0.0, 0.0
    return float(np.percentile(np.linalg.norm(where - starts[index], axis=1), WALL_PERCENTILE)), len(index) / len(points)


def cleanliness(vertices, faces):
    """{watertight, open edges and their length, non-manifold edges, a face's edge held twice the same way, degenerate
    and repeated faces, pieces, the largest's area share, crumbs and their share, thinnest wall, triangles a m2, flat
    share, swell}."""
    corners, welded = _mesh.welded(vertices, faces)
    area = _mesh.areas(corners, welded)
    spoiled = (welded[:, 0] == welded[:, 1]) | (welded[:, 1] == welded[:, 2]) | (welded[:, 0] == welded[:, 2])
    degenerate = spoiled | (area <= (_mesh.diagonal(corners) * _mesh.WELD) ** 2)
    kept = welded[~degenerate]
    undirected, held, wound_against = edges(kept)
    open_edges = undirected[held == 1]
    whole = pieces(corners, kept, area[~degenerate])
    crumbs = whole[whole < CRUMB * whole.sum()]
    wall, met = thinnest(corners, kept)
    return {"watertight": bool(len(open_edges) == 0 and (held <= 2).all() and wound_against == 0),
            "open_edges": int(len(open_edges)),
            "open_length": round(float(np.linalg.norm(corners[open_edges[:, 0]] - corners[open_edges[:, 1]],
                                                      axis=1).sum()), 4),
            "non_manifold_edges": int((held > 2).sum()),
            "wound_against": wound_against,
            "degenerate_faces": int(degenerate.sum()),
            "repeated_faces": int(len(kept) - len(np.unique(np.sort(kept, axis=1), axis=0))),
            "pieces": int(len(whole)), "largest_share": round(float(whole[0] / whole.sum()), 5),
            "crumbs": int(len(crumbs)), "crumb_share": round(float(crumbs.sum() / whole.sum()), 5),
            "thinnest": round(wall, 5), "rays_met": round(met, 3),
            "triangles_per_m2": round(float(len(faces) / area.sum()), 2),
            "flat_share": round(shapes.flat_share(_mesh.normals(corners, kept), area[~degenerate]), 4),
            "swell": round(shapes.section(_mesh.sampled(corners, kept, shapes.SAMPLES, seed=shapes.SEED)[0])[1], 4)}
