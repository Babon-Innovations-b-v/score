"""The people route's bind by limb (owner, 2026-10-18, score #10): each region of the made mesh takes its weights only
from its own limb of the SOMA-X body under it, and the web Pixal3D grew between an arm and the chest (and between
the legs) is cut and closed, so no triangle hangs from two limbs at once. Plain numpy, scipy and trimesh.

- **Regions.** Each point of the garments (welded across their parts) takes the limb of the nearest base point
  (`GROUPS`: an arm is its upper arm, forearm and hand; a leg its thigh, shin and foot; the rest is the trunk), then
  a majority of its neighbours, LABEL_ROUNDS times, so a lone point does not change sides.
- **Bind.** A limb's point binds to the closest base triangle of its own limb; a trunk point to the closest triangle
  that is no arm's and no shin's or foot's (the thighs stay open to it, so the seat follows the hips and the legs).
  Its weights are the base's at that place (the shell bind of prop_shell.py, restricted).
- **Web.** An edge between two regions is web when the places its two ends bind to lie more than JUMP_SHARE times
  its own length apart and more than JUMP_LEAST: the base has a gap there (the armpit, the crotch) that the look
  bridged. Along the shoulder's top the two binds touch, so that seam stays and blends.
- **Underarm and crotch.** At the armpit and the crotch the base is one crease, so a web's two sides bind next to
  each other and the jump misses it; every arm-to-trunk edge more than UNDERARM_BELOW under the shoulder joint, and
  every edge between the two legs, is web too (`underarm_edges`).
- **Cut and closed.** Every triangle with a web edge is removed; each side's opening (the chain of new border edges
  of one region) is closed by a fan to a new middle point, wound as the triangle next to each edge, the middle taking
  the chain's mean place, weights and offsets. The earlier try (`cut web`, 13 Oct) cut and left a strip, which
  stretched.
- **Smoothing.** The weights are averaged with their neighbours SMOOTH_ROUNDS times (people/skin.py's six), never
  across a web edge, then each limb point keeps only its own chain's joints and the one it hangs from.
"""
import numpy as np
import trimesh
from scipy.spatial import cKDTree

GROUPS = {
    "LeftArm": ("LeftArm", "LeftForeArm", "LeftHand"),
    "RightArm": ("RightArm", "RightForeArm", "RightHand"),
    "LeftLeg": ("LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase", "LeftToeEnd"),
    "RightLeg": ("RightLeg", "RightShin", "RightFoot", "RightToeBase", "RightToeEnd"),
}
TRUNK = "trunk"
REGIONS = (TRUNK,) + tuple(GROUPS)
# The joint each limb hangs from, which its points may also take weights from.
HANGS_FROM = {"LeftArm": "LeftShoulder", "RightArm": "RightShoulder", "LeftLeg": "Hips", "RightLeg": "Hips"}
# Joints a trunk point never binds to: the arms beyond the shoulder, the legs below the knee.
NOT_TRUNK = ("LeftArm", "LeftForeArm", "LeftHand", "RightArm", "RightForeArm", "RightHand", "LeftShin", "LeftFoot",
             "LeftToeBase", "LeftToeEnd", "RightShin", "RightFoot", "RightToeBase", "RightToeEnd")
LABEL_ROUNDS = 3
JUMP_SHARE = 2.5
JUMP_LEAST = 0.02
UNDERARM_BELOW = 0.04
SMOOTH_ROUNDS = 6


def joint_regions(names):
    """Each joint's region number (REGIONS' order)."""
    found = np.zeros(len(names), int)
    for number, name in enumerate(names):
        for region, chain in GROUPS.items():
            if name in chain:
                found[number] = REGIONS.index(region)
    return found


def base_regions(base_weights, names):
    """Each base point's region: its strongest joint's."""
    return joint_regions(names)[base_weights.argmax(1)]


def edges_of(faces):
    """The unique edges of a triangle list (sorted pairs)."""
    pairs = np.sort(faces[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2), axis=1)
    return np.unique(pairs, axis=0)


def majority(labels, edges, rounds=LABEL_ROUNDS):
    """Each point's label replaced by the most common among itself and its neighbours, `rounds` times."""
    count = len(labels)
    for _ in range(rounds):
        votes = np.zeros((count, len(REGIONS)))
        np.add.at(votes, (np.arange(count), labels), 1.0)
        np.add.at(votes, (edges[:, 0], labels[edges[:, 1]]), 1.0)
        np.add.at(votes, (edges[:, 1], labels[edges[:, 0]]), 1.0)
        labels = votes.argmax(1)
    return labels


def point_regions(points, edges, base_points, base_region):
    """Each look point's region: the nearest base point's, then its neighbours' majority."""
    _, nearest = cKDTree(base_points).query(points)
    return majority(base_region[nearest], edges)


def open_joints(region, names):
    """The joints a region's points may bind to (as a mask over the joints)."""
    if region == TRUNK:
        return ~np.isin(names, NOT_TRUNK)
    return np.isin(names, GROUPS[region])


def closest_on(points, base_points, base_faces):
    """Each point's closest triangle and its place there as shares of the triangle's corners."""
    surface = trimesh.Trimesh(base_points, base_faces, process=False)
    closest, _, triangle = trimesh.proximity.closest_point(surface, points)
    shares = trimesh.triangles.points_to_barycentric(surface.triangles[triangle], closest)
    shares = np.clip(shares, 0.0, None)
    return triangle, shares / shares.sum(1, keepdims=True)


class Bound:
    """Where each look point is bound on the base: its base corners (points, 3), their shares and the place."""

    def __init__(self, corners, shares, base_points):
        self.corners = corners
        self.shares = shares
        self.places = np.einsum("pc,pcd->pd", shares, base_points[corners])

    def carried(self, values):
        """Base values (points, ...) carried to the look's points by their shares."""
        return np.einsum("pc,pc...->p...", self.shares, values[self.corners])


def bound_by_region(points, regions, base_points, base_faces, base_weights, names):
    """Every look point bound to the closest base triangle open to its region."""
    names = np.asarray(names)
    owner = base_weights.argmax(1)
    corners = np.zeros((len(points), 3), int)
    shares = np.zeros((len(points), 3))
    for region in np.unique(regions):
        mine = regions == region
        allowed = np.isin(owner, np.flatnonzero(open_joints(REGIONS[region], names)))
        faces = base_faces[allowed[base_faces].all(1)]
        triangle, found = closest_on(points[mine], base_points, faces)
        corners[mine], shares[mine] = faces[triangle], found
    return Bound(corners, shares, base_points)


def web_edges(points, edges, regions, places):
    """The edges between two regions whose binds lie a gap apart (module docstring), as a mask over `edges`."""
    between = regions[edges[:, 0]] != regions[edges[:, 1]]
    length = np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1)
    jump = np.linalg.norm(places[edges[:, 0]] - places[edges[:, 1]], axis=1)
    return between & (jump > np.maximum(JUMP_SHARE * length, JUMP_LEAST))


def underarm_edges(points, edges, regions, shoulder_heights):
    """The edges between an arm and the trunk with both ends more than UNDERARM_BELOW under that arm's shoulder joint
    (`shoulder_heights`: region number to height), and every edge between the two legs: the seams the look's webs
    lie on, cut whatever the base does there (at the armpit and the crotch the base's own surface is one crease, so
    the binds of a web's two sides lie next to each other and the jump alone misses it)."""
    first, second = regions[edges[:, 0]], regions[edges[:, 1]]
    legs = {REGIONS.index("LeftLeg"), REGIONS.index("RightLeg")}
    found = np.isin(first, list(legs)) & np.isin(second, list(legs)) & (first != second)
    trunk = REGIONS.index(TRUNK)
    lowest = np.maximum(points[edges[:, 0], 1], points[edges[:, 1], 1])
    for arm, height in shoulder_heights.items():
        across = ((first == arm) & (second == trunk)) | ((first == trunk) & (second == arm))
        found |= across & (lowest < height - UNDERARM_BELOW)
    return found


def smoothed(weights, edges, rounds=SMOOTH_ROUNDS):
    """Weights averaged with their neighbours along `edges`, `rounds` times."""
    for _ in range(rounds):
        total, count = weights.copy(), np.ones(len(weights))
        np.add.at(total, edges[:, 0], weights[edges[:, 1]])
        np.add.at(total, edges[:, 1], weights[edges[:, 0]])
        np.add.at(count, edges.ravel(), 1)
        weights = total / count[:, None]
    return weights


def kept_to_limb(weights, regions, names):
    """Each limb point's weights kept to its chain and the joint it hangs from, shared out to one again."""
    names = list(names)
    weights = weights.copy()
    for region, chain in GROUPS.items():
        mine = regions == REGIONS.index(region)
        allowed = np.isin(names, chain + (HANGS_FROM[region],))
        weights[np.ix_(mine, ~allowed)] = 0.0
    total = weights.sum(1, keepdims=True)
    return weights / np.where(total > 0, total, 1.0)


def web_faces(faces, web_pairs):
    """Which triangles carry a web edge (`web_pairs`: a set of sorted point pairs)."""
    found = np.zeros(len(faces), bool)
    for number, face in enumerate(faces):
        for first, second in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            if (min(first, second), max(first, second)) in web_pairs:
                found[number] = True
                break
    return found


def directed_borders(faces):
    """Every border edge of a triangle list as (start, end) in its triangle's winding."""
    directed = faces[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2)
    keys = np.sort(directed, axis=1)
    _, inverse, counts = np.unique(keys, axis=0, return_inverse=True, return_counts=True)
    return directed[counts[inverse.reshape(-1)] == 1]


def chains(directed, labels):
    """The new border edges grouped by region and by touching ends: lists of (start, end) rows."""
    groups = []
    for region in np.unique(labels[directed[:, 0]]):
        rows = directed[labels[directed[:, 0]] == region]
        parent = {}

        def root(vertex):
            while parent.setdefault(vertex, vertex) != vertex:
                parent[vertex] = parent[parent[vertex]]
                vertex = parent[vertex]
            return vertex

        for start, end in rows:
            parent[root(start)] = root(end)
        owner = np.array([root(start) for start in rows[:, 0]])
        groups += [rows[owner == value] for value in np.unique(owner)]
    return groups


def fan(chain, middle):
    """Triangles closing a chain to its middle point, wound against the border edge (so they face as the triangle
    next to the edge does); an open chain (its ends on a seam that stays) also gets the triangle across its ends."""
    triangles = [np.stack([chain[:, 1], chain[:, 0], np.full(len(chain), middle)], 1)]
    starts, ends = set(chain[:, 0].tolist()), set(chain[:, 1].tolist())
    first, last = sorted(starts - ends), sorted(ends - starts)
    if len(first) == 1 and len(last) == 1:
        triangles.append(np.array([[first[0], last[0], middle]]))
    return np.concatenate(triangles)


def closed(faces, labels, cut, count):
    """A part's triangles with its `cut` ones removed and each region's opening closed by a fan to a new middle
    point (numbered from `count`, the part's point count): (triangles, each middle point's chain ends)."""
    before = {tuple(row) for row in np.sort(directed_borders(faces), axis=1)}
    kept = faces[~cut]
    opened = directed_borders(kept)
    new = opened[[tuple(sorted(row)) not in before for row in opened]]
    middles, extra = [], []
    for chain in chains(new, labels):
        if len(chain) < 2:
            continue
        middles.append(np.unique(chain))
        extra.append(fan(chain, count + len(middles) - 1))
    return np.concatenate([kept] + extra), middles


def with_middles(values, middles):
    """Per-point values with each middle point's value appended: the mean of its chain ends'."""
    if not middles:
        return values
    return np.concatenate([values, np.stack([values[ends].mean(0) for ends in middles])])
