"""The prop route's tucks: each skin or hard part's open border against a garment (a wrist, a boot top, the neck) run
on under the garment as a hidden band, so no gap opens between them in a clip (people/skin.py `bare_hands`' rule,
which already seals the shipped hands). A Pixal3D person is one welded surface: cut into parts, a hand and its sleeve
meet edge to edge, and joins.py asks the sleeve to reach LEAST_OVERLAP (1 cm) past where the hand begins, which an
edge-to-edge seam never does. Plain numpy and scipy.

A part's border loops are its edges used by one of its triangles; only a loop most of whose points lie within
GARMENT_NEAR of a garment is tucked (a boot's sole or a cut between two pieces of one part is not). Each point of the
loop is carried TUCK_LENGTH along the bone nearest it (of those touching its strongest joint: the forearm at a wrist,
the shin at a boot top, the neck at the collar), away from the part, and drawn in TUCK_SHRINK of the way to the bone's
line, so the band lies inside whatever garment goes round that limb; the loop is joined to the band by triangles
wound as the part's own. Run on from the part's middle, a flat patch's tuck stood out of the player's hip; run on
along the part's own surface, Pixal3D's jagged borders sent spikes out of his collar and wrist (2026-10-10). The
band's points take the weights of the nearest garment points, so it moves with the cloth over it.
"""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

TUCK_LENGTH = 0.04
# A tuck's band is drawn in towards its bone by this share of its distance from it, under the garment round it.
TUCK_SHRINK = 0.2
GARMENT_NEAR = 0.01
GARMENT_SHARE = 0.5


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


def nearest_bones(places, joints, bones):
    """Each point's nearest bone among those touching its joint (`bones`: each joint's bones as (start, end) places):
    the bone's start and unit direction."""
    starts, directions = np.zeros((len(places), 3)), np.zeros((len(places), 3))
    for index, (place, joint) in enumerate(zip(places, joints)):
        best = None
        for start, end in bones[joint]:
            line = end - start
            share = np.clip((place - start) @ line / max(line @ line, 1e-12), 0.0, 1.0)
            gap = np.linalg.norm(place - (start + share * line))
            if best is None or gap < best[0]:
                best = (gap, start, line / max(np.linalg.norm(line), 1e-12))
        starts[index], directions[index] = best[1], best[2]
    return starts, directions


def tucked_ring(places, middle, starts, directions):
    """A ring carried TUCK_LENGTH along its bones, away from the part's middle, and drawn in towards the bones' lines
    by TUCK_SHRINK of its distance from them."""
    away = np.sign(((places - middle) * directions).sum(1, keepdims=True))
    away[away == 0] = 1.0
    moved = places + away * directions * TUCK_LENGTH
    along = ((moved - starts) * directions).sum(1, keepdims=True)
    across = moved - (starts + along * directions)
    return moved - across * TUCK_SHRINK


def tucked(points, faces, weights, garment_points, garment_weights, bones, least_edges=6):
    """The part with a tuck under every border loop of at least `least_edges` edges that meets a garment: (points,
    faces, weights), the band's points appended after the part's own. `bones` gives each joint's bones as (start,
    end) places."""
    tree = cKDTree(garment_points)
    middle = points.mean(0)
    new_points, new_faces, new_weights = [points], [faces], [weights]
    total = len(points)
    for loop in loops(border_edges(faces), len(points)):
        if len(loop) < least_edges:
            continue
        ring = np.unique(loop)
        near, _ = tree.query(points[ring], distance_upper_bound=GARMENT_NEAR)
        if np.isfinite(near).mean() < GARMENT_SHARE:
            continue
        starts, directions = nearest_bones(points[ring], weights[ring].argmax(1), bones)
        moved = tucked_ring(points[ring], middle, starts, directions)
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
