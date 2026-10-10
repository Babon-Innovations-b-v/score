"""The prop route's tucks: each skin or hard part's open border against a garment (a wrist, a boot top, the neck) run
on under the garment as a hidden band, so no gap opens between them in a clip (people/skin.py `bare_hands`' rule,
which already seals the shipped hands). A Pixal3D person is one welded surface: cut into parts, a hand and its sleeve
meet edge to edge, and joins.py asks the sleeve to reach LEAST_OVERLAP (1 cm) past where the hand begins, which an
edge-to-edge seam never does. Plain numpy and scipy.

A part's border loops are its edges used by one of its triangles; only a loop most of whose points lie within
GARMENT_NEAR of a garment is tucked (a boot's sole or a cut between two pieces of one part is not). Each point of the
loop is carried TUCK_LENGTH on along the part's own surface (away from its neighbours inside the part, averaged
along the loop, the surface's normal taken out) and TUCK_INSET under it (against its normal), and the loop is joined to the band by triangles wound
as the part's own. Run on from the part's middle instead, a flat patch's tuck stuck out of the hip (2026-10-10). The
band's points take the weights of the nearest garment points, so it moves with the cloth over it.
"""
import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

TUCK_LENGTH = 0.04
TUCK_INSET = 0.003
GARMENT_NEAR = 0.01
GARMENT_SHARE = 0.5
LOOP_SMOOTHING = 4


def border_edges(faces):
    """The directed edges (as the triangles wind them) used by one triangle only."""
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    undirected = np.sort(edges, axis=1)
    _, inverse, counts = np.unique(undirected, axis=0, return_inverse=True, return_counts=True)
    return edges[counts[inverse.reshape(-1)] == 1]


def loops(edges, count):
    """The border edges grouped by the loop (connected piece) they belong to: a list of edge arrays."""
    graph = coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])), shape=(count, count))
    _, label = connected_components(graph, directed=False)
    return [edges[label[edges[:, 0]] == number] for number in np.unique(label[edges[:, 0]])]


def onward(points, faces, ring, normals):
    """Each ring point's way on along the surface: from the mean of its neighbours off the ring to it, the normal's
    part taken out, unit length."""
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    edges = np.concatenate([edges, edges[:, ::-1]])
    on_ring = np.zeros(len(points), bool)
    on_ring[ring] = True
    inner = edges[on_ring[edges[:, 0]] & ~on_ring[edges[:, 1]]]
    total = np.zeros((len(points), 3))
    count = np.zeros(len(points))
    np.add.at(total, inner[:, 0], points[inner[:, 1]])
    np.add.at(count, inner[:, 0], 1)
    behind = np.where(count[ring, None] > 0, total[ring] / np.maximum(count[ring, None], 1), points[ring] - normals[ring])
    way = points[ring] - behind
    way -= (way * normals[ring]).sum(1, keepdims=True) * normals[ring]
    return way / np.maximum(np.linalg.norm(way, axis=1, keepdims=True), 1e-9)


def along_the_loop(ways, loop, ring, normals, rounds=LOOP_SMOOTHING):
    """The ring points' ways averaged with their neighbours' along the loop `rounds` times (a jagged border gives a
    point a way sideways), the normal's part taken out again, unit length."""
    place = {vertex: index for index, vertex in enumerate(ring)}
    first = np.array([place[vertex] for vertex in loop[:, 0]])
    second = np.array([place[vertex] for vertex in loop[:, 1]])
    for _ in range(rounds):
        total, count = ways.copy(), np.ones(len(ways))
        np.add.at(total, first, ways[second])
        np.add.at(total, second, ways[first])
        np.add.at(count, first, 1)
        np.add.at(count, second, 1)
        ways = total / count[:, None]
    ways -= (ways * normals).sum(1, keepdims=True) * normals
    return ways / np.maximum(np.linalg.norm(ways, axis=1, keepdims=True), 1e-9)


def tucked(points, faces, weights, garment_points, garment_weights, least_edges=6):
    """The part with a tuck under every border loop of at least `least_edges` edges that meets a garment: (points,
    faces, weights), the band's points appended after the part's own."""
    tree = cKDTree(garment_points)
    normals = trimesh.Trimesh(points, faces, process=False).vertex_normals
    new_points, new_faces, new_weights = [points], [faces], [weights]
    total = len(points)
    for loop in loops(border_edges(faces), len(points)):
        if len(loop) < least_edges:
            continue
        ring = np.unique(loop)
        near, _ = tree.query(points[ring], distance_upper_bound=GARMENT_NEAR)
        if np.isfinite(near).mean() < GARMENT_SHARE:
            continue
        way = along_the_loop(onward(points, faces, ring, normals), loop, ring, normals[ring])
        moved = points[ring] + way * TUCK_LENGTH - normals[ring] * TUCK_INSET
        number = {vertex: total + index for index, vertex in enumerate(ring)}
        first, second = loop[:, 0], loop[:, 1]
        far_first = np.array([number[vertex] for vertex in first])
        far_second = np.array([number[vertex] for vertex in second])
        # The border edge a->b runs one way round the part's last triangle; the band's triangles run b->a->a' and
        # b->a'->b', so the band faces the way the part does.
        new_faces.append(np.concatenate([np.stack([second, first, far_first], 1),
                                         np.stack([second, far_first, far_second], 1)]))
        new_points.append(moved)
        new_weights.append(garment_weights[tree.query(moved)[1]])
        total += len(ring)
    return np.concatenate(new_points), np.concatenate(new_faces), np.concatenate(new_weights)
