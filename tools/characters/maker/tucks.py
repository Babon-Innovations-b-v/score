"""The prop route's tucks: each skin or hard part's open border against a garment (a wrist, a boot top, the neck) run
on under the garment as a hidden band, so no gap opens between them in a clip (people/skin.py `bare_hands`' rule,
which already seals the shipped hands). A Pixal3D person is one welded surface: cut into parts, a hand and its sleeve
meet edge to edge, and joins.py asks the sleeve to reach LEAST_OVERLAP (1 cm) past where the hand begins, which an
edge-to-edge seam never does. Plain numpy and scipy.

A part's border loops are its edges used by one of its triangles. Each loop is moved TUCK_LENGTH away from the part
(from the part's middle through the loop's middle) and drawn in TUCK_INSET towards the loop's own middle, and joined
to the loop by a band of triangles wound as the part's own. The band's points take the weights of the nearest garment
points, so it moves with the cloth over it.
"""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

TUCK_LENGTH = 0.04
TUCK_INSET = 0.003


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


def tucked(points, faces, weights, garment_points, garment_weights, least_edges=6):
    """The part with a tuck under every border loop of at least `least_edges` edges: (points, faces, weights), the
    band's points appended after the part's own."""
    middle = points.mean(0)
    tree = cKDTree(garment_points)
    new_points, new_faces, new_weights = [points], [faces], [weights]
    total = len(points)
    for loop in loops(border_edges(faces), len(points)):
        if len(loop) < least_edges:
            continue
        ring = np.unique(loop)
        centre = points[ring].mean(0)
        away = centre - middle
        away /= max(np.linalg.norm(away), 1e-9)
        inward = centre - points[ring]
        inward /= np.maximum(np.linalg.norm(inward, axis=1, keepdims=True), 1e-9)
        moved = points[ring] + away * TUCK_LENGTH + inward * TUCK_INSET
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
