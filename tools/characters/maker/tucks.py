"""The prop route's tucks: each skin or hard part's open border against a garment (a wrist, a boot top, the neck) run
on under the garment as a hidden band, so no gap opens between them in a clip (people/skin.py `bare_hands`' rule,
which already seals the shipped hands). A Pixal3D person is one welded surface: cut into parts, a hand and its sleeve
meet edge to edge, and joins.py asks the sleeve to reach LEAST_OVERLAP (1 cm) past where the hand begins, which an
edge-to-edge seam never does. Plain numpy and scipy.

A part's border loops are its edges used by one of its triangles; only a loop most of whose points lie within
GARMENT_NEAR of a garment is tucked (a boot's sole or a cut between two pieces of one part is not), and of it only the
edges both of whose ends lie that near (a boot's loop that runs on round its sole tucked its sole 24 cm from any
cloth). Each point of the
loop is carried TUCK_LENGTH along the bone nearest it (of those touching its strongest joint: the forearm at a wrist,
the shin at a boot top, the neck at the collar), away from the part, and drawn in TUCK_SHRINK of the way to the bone's
line, and at least to TUCK_GAP inside the nearest garment point's distance from that line, so the band lies inside
whatever garment goes round that limb (run down the neck from the jaw, a fixed share left it 2 cm out in front of the
throat); the loop is joined to the band by triangles
wound as the part's own. Run on from the part's middle, a flat patch's tuck stood out of the player's hip; run on
along the part's own surface, Pixal3D's jagged borders sent spikes out of his collar and wrist (2026-10-10). The
band's points take the weights of the nearest garment points, so it moves with the cloth over it.
"""
import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

TUCK_LENGTH = 0.04
# A tuck's band is drawn in towards its bone by this share of its distance from it, under the garment round it.
TUCK_SHRINK = 0.2
# And at least this far inside the garment's distance from the bone.
TUCK_GAP = 0.012
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


def radial(places, starts, directions):
    """Each place's offset across its bone's line (from the line to it)."""
    along = ((places - starts) * directions).sum(1, keepdims=True)
    return places - (starts + along * directions)


def tucked_ring(places, middle, starts, directions, garment_points, tree):
    """A ring carried TUCK_LENGTH along its bones, away from the part's middle, and drawn in towards the bones' lines:
    by TUCK_SHRINK of its distance from them, and at least to TUCK_GAP inside the nearest garment point's distance
    from the same line (so it lies inside the garment's tube round the limb)."""
    away = np.sign(((places - middle) * directions).sum(1, keepdims=True))
    away[away == 0] = 1.0
    moved = places + away * directions * TUCK_LENGTH
    across = radial(moved, starts, directions)
    reach = np.linalg.norm(across, axis=1)
    cloth = np.linalg.norm(radial(garment_points[tree.query(moved)[1]], starts, directions), axis=1)
    wanted = np.clip(np.minimum(reach * (1 - TUCK_SHRINK), cloth - TUCK_GAP), 0.0, None)
    return moved - across * (1 - wanted / np.maximum(reach, 1e-9))[:, None]


def inside(places, outer):
    """Whether each place lies under the person's outer surface at rest (the whole mesh, `outer`): behind the face
    normal at the nearest place on it."""
    nearest, _, triangle = trimesh.proximity.closest_point(outer, places)
    return ((places - nearest) * outer.face_normals[triangle]).sum(1) < 0


def tucked(points, faces, weights, garment_points, garment_weights, bones, outer, least_edges=6):
    """The part with a tuck under every border loop of at least `least_edges` edges that meets a garment: (points,
    faces, weights), the band's points appended after the part's own. `bones` gives each joint's bones as (start,
    end) places; `outer` is the whole person at rest, which a band edge must lie under to be kept."""
    tree = cKDTree(garment_points)
    middle = points.mean(0)
    by_cloth = np.isfinite(tree.query(points, distance_upper_bound=GARMENT_NEAR)[0])
    new_points, new_faces, new_weights = [points], [faces], [weights]
    total = len(points)
    for loop in loops(border_edges(faces), len(points)):
        if len(loop) < least_edges:
            continue
        if by_cloth[np.unique(loop)].mean() < GARMENT_SHARE:
            continue
        loop = loop[by_cloth[loop[:, 0]] & by_cloth[loop[:, 1]]]
        ring = np.unique(loop)
        starts, directions = nearest_bones(points[ring], weights[ring].argmax(1), bones)
        moved = tucked_ring(points[ring], middle, starts, directions, garment_points, tree)
        hidden = dict(zip(ring, inside(moved, outer)))
        keep = np.array([hidden[first] and hidden[second] for first, second in loop], bool)
        if not keep.any():
            continue
        loop = loop[keep]
        kept = np.isin(ring, loop)
        ring, moved = ring[kept], moved[kept]
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
