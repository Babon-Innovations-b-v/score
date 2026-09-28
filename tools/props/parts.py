"""Cut a made mesh into parts, and settle what each part is made of.

A generated mesh arrives as one welded lump, so nothing can follow its parts: colour bleeds from a
solar panel into the body beside it, and no wall can be made straight. CoACD (MIT) cuts the lump
into near-convex pieces; a panel standing off a body, a leg, a tank and a mast come out as pieces of
their own. Each piece is then one part: it takes one finish, and touching pieces of one finish that
together fill a straight shell are joined, so one wall is one part and not a stack of slabs.
"""
import numpy as np
import trimesh

# A finish that stands out from a body is only given to a part most of which reads that way: a real
# solar array is dark all over, a slab of body in shadow only in patches. Measured on the drone.
DECISIVE = {"solar": 0.6}
# A part this small a share of the whole, unlike everything touching it, is a stray blob.
STRAY_SHARE = 0.02
# A small part keeps its own finish when at least this share of it shows that finish.
CLEARLY_ITS_OWN = 0.7
# How much of their shared straight shell two parts must already fill to be joined into it.
FILLED_TO_JOIN = 0.92


# The most corners one part's shell may have. More costs triangles and buys roundness nobody sees
# at the size a prop is drawn; fewer and a tank turns into a gem.
SHELL_CORNERS = 64


def thinned(hull):
    """The part's shell with at most SHELL_CORNERS corners, still convex. Done after the parts are
    settled, because a coarse shell makes neighbours look as if they fill each other and join."""
    if len(hull.vertices) <= SHELL_CORNERS:
        return hull
    import fast_simplification
    keep = 1.0 - SHELL_CORNERS / len(hull.vertices)
    vertices, _ = fast_simplification.simplify(hull.vertices.astype(np.float32), hull.faces.astype(np.int32),
                                               target_reduction=keep)
    return trimesh.convex.convex_hull(vertices) if len(vertices) >= 4 else hull


def cut(mesh, threshold=0.05):
    """Near-convex pieces of the mesh, as hulls. Lower threshold, more and tighter pieces."""
    import coacd
    coacd.set_log_level("error")
    hulls = coacd.run_coacd(coacd.Mesh(mesh.vertices, mesh.faces), threshold=threshold,
                            preprocess_mode="auto", max_convex_hull=-1, seed=0)
    return [trimesh.Trimesh(vertices, faces, process=True) for vertices, faces in hulls]


def outside_by(hull, points):
    """How far each point lies outside a convex hull: the most it is past any of its face planes.
    Zero or less is inside."""
    planes = hull.face_normals
    offsets = (planes * hull.triangles[:, 0]).sum(1)
    return (points @ planes.T - offsets).max(axis=1)


def piece_of_each_face(mesh, hulls):
    """The piece whose hull each face's centre is inside, or nearest to."""
    centres = mesh.triangles_center
    best = np.full(len(centres), np.inf)
    piece = np.zeros(len(centres), dtype=int)
    for index, hull in enumerate(hulls):
        outside = outside_by(hull, centres)
        closer = outside < best
        best[closer] = outside[closer]
        piece[closer] = index
    return piece


def seen_parts(hulls, piece):
    """The parts at least one surface face belongs to, and each face's part renumbered to match.
    A piece the cutter left wholly inside others owns no face: nothing can see it, and it has no
    finish to take, so it goes."""
    owned = np.unique(piece)
    renumber = np.full(len(hulls), -1)
    renumber[owned] = np.arange(len(owned))
    return [hulls[index] for index in owned], renumber[piece]


def finish_shares(mesh, finish, piece, count):
    """For each piece, its finishes with the share of its area each covers, most first."""
    kinds = sorted(set(finish))
    index = np.array([kinds.index(name) for name in finish])
    votes = np.zeros((count, len(kinds)))
    np.add.at(votes, (piece, index), mesh.area_faces)
    shares = votes / np.maximum(votes.sum(1, keepdims=True), 1e-12)
    return [[(kinds[column], row[column]) for column in np.argsort(-row) if row[column] > 0]
            for row in shares]


def choose(ranked):
    """Each part's finish: the one covering most of it, unless that one needs a clearer majority."""
    chosen = []
    for options in ranked:
        allowed = [name for name, share in options if share >= DECISIVE.get(name, 0.0)]
        chosen.append(allowed[0] if allowed else options[0][0])
    return chosen


def touching(first, second, slack=0.02):
    """Whether two parts' boxes meet, allowing a sliver of a gap."""
    gap = slack * max(np.ptp(first.bounds, axis=0).max(), np.ptp(second.bounds, axis=0).max())
    return bool(np.all(first.bounds[0] - gap <= second.bounds[1])
                and np.all(second.bounds[0] - gap <= first.bounds[1]))


def adopt(hulls, chosen, clear=None):
    """A small part unlike everything touching it takes the finish its neighbours mostly have,
    unless most of it clearly shows its own: a yellow cone on a grey box is a part, a few dark
    faces on a gold drum are a stray. `clear` is each part's share of its own finish."""
    total = sum(max(hull.volume, 0.0) for hull in hulls)
    settled = list(chosen)
    for index, hull in enumerate(hulls):
        if hull.volume > STRAY_SHARE * total:
            continue
        if clear is not None and clear[index] >= CLEARLY_ITS_OWN:
            continue
        around = [chosen[other] for other, near in enumerate(hulls)
                  if other != index and touching(hull, near)]
        if around and chosen[index] not in around:
            settled[index] = max(set(around), key=around.count)
    return settled


def filled_share(first, second, shell, samples=6000, seed=0):
    """How much of the shared shell the two parts really fill, found by throwing points into it."""
    generator = np.random.default_rng(seed)
    low, high = shell.bounds
    points = low + generator.random((samples, 3)) * (high - low)
    in_shell = outside_by(shell, points) <= 0
    if not in_shell.any():
        return 1.0
    covered = ((outside_by(first, points) <= 0) | (outside_by(second, points) <= 0)) & in_shell
    return covered.sum() / in_shell.sum()


def join(hulls, chosen):
    """Join touching parts of one finish while the two already fill almost all of the straight
    shell round both: a wall's slabs become one part, a tank bulging off a drum stays its own."""
    hulls, chosen = list(hulls), list(chosen)
    joined = True
    while joined:
        joined = False
        for first in range(len(hulls)):
            for second in range(first + 1, len(hulls)):
                if chosen[first] != chosen[second] or not touching(hulls[first], hulls[second]):
                    continue
                shell = trimesh.convex.convex_hull(np.vstack([hulls[first].vertices,
                                                              hulls[second].vertices]))
                if filled_share(hulls[first], hulls[second], shell) >= FILLED_TO_JOIN:
                    hulls[first] = shell
                    del hulls[second], chosen[second]
                    joined = True
                    break
            if joined:
                break
    return hulls, chosen
