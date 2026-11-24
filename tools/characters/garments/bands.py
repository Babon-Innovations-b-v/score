"""A garment's bands (#225: a high-visibility jacket's retroreflective tape): strips of the cloth a set height above
its hem round the torso and above its cuff round each sleeve, cut out of the garment's triangles along their exact
edges and worn with their own library surface. Score venv (numpy).

Each band is placed on the garment as sewn at the bind: on a torso panel (a panel named `*torso*`) by its height
above the hem (the median height of the torso panels' open edge within HEM_M of the garment's lowest point); on a
sleeve (the panels named `<side>_sleeve*`) by its distance from the cuff (its open edge) along the sleeve, from the
cuff's middle to the middle of its seam to the torso. A triangle a band's edge crosses is cut along it: each new
point a weighted mix of the triangle's box points, carried so every frame, one point where two triangles share it (a
seam's too), so the tape's edge runs straight and does not step along the 1.5 cm triangles, as the triangles whose
middles lie in the band would.
"""
import numpy as np

HEM_M = 0.05  # the torso panels' open edge this near the garment's lowest point is its hem
MOST_MIXED = 3  # a new point is a mix of at most a triangle's three box points


def open_edge_points(faces):
    """The points on a mesh's open edges (an edge of one triangle only)."""
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    unique, counts = np.unique(edges, axis=0, return_counts=True)
    return np.unique(unique[counts == 1])


def placed_along(record, sewn):
    """Each triangle corner's place along its band field (m) and the field it is on: (corners x 3 floats, triangles
    of kind 0 none, 1 torso, 2 sleeve). `record` is pattern.py's (its copies' panels and box points), `sewn` the
    garment's box points as sewn (m)."""
    names = [str(name) for name in record["panel_names"]]
    panel, box, faces = np.asarray(record["panel"]), np.asarray(record["box"]), np.asarray(record["faces"])
    welded = box[faces]
    edge = open_edge_points(welded)
    along = np.full(len(box), np.nan)
    kind = np.zeros(len(faces), dtype=int)
    torso = [number for number, name in enumerate(names) if "torso" in name]
    torso_points = np.unique(box[np.isin(panel, torso)])
    if len(torso):
        lowest = sewn[torso_points, 1].min()
        rim = np.intersect1d(torso_points, edge)
        hem = np.median(sewn[rim[sewn[rim, 1] < lowest + HEM_M], 1])
        mine = np.isin(panel, torso)
        along[mine] = sewn[box[mine], 1] - hem
        kind[np.isin(panel[faces[:, 0]], torso)] = 1
    for side in ("left", "right"):
        sleeve = [number for number, name in enumerate(names) if name.startswith(f"{side}_sleeve")]
        if not sleeve:
            continue
        points = np.unique(box[np.isin(panel, sleeve)])
        rim, seam = np.intersect1d(points, edge), np.intersect1d(points, torso_points)
        if not len(rim) or not len(seam):
            continue  # a sleeve with no open cuff or not sewn to a torso has no bands
        cuff, armhole = sewn[rim].mean(axis=0), sewn[seam].mean(axis=0)
        axis = (armhole - cuff) / np.linalg.norm(armhole - cuff)
        mine = np.isin(panel, sleeve)
        along[mine] = (sewn[box[mine]] - cuff) @ axis
        kind[np.isin(panel[faces[:, 0]], sleeve)] = 2
    return along[faces], kind


def levels_of(bands, kind):
    """The band edges of a field (`bands`: {"width_m", "torso_m": [lower edges], "sleeve_m": [lower edges]})."""
    lowers = bands["torso_m"] if kind == 1 else bands["sleeve_m"] if kind == 2 else []
    return sorted([edge for lower in lowers for edge in (lower, lower + bands["width_m"])])


def in_band(value, bands, kind):
    """Whether a place along a field lies on one of its bands."""
    lowers = bands["torso_m"] if kind == 1 else bands["sleeve_m"] if kind == 2 else []
    return any(lower <= value <= lower + bands["width_m"] for lower in lowers)


def mixed(one, other, share):
    """The corner `share` of the way from corner `one` to `other`, each a tuple of (copy, weight)."""
    weights = {}
    for corner, scale in ((one, 1.0 - share), (other, share)):
        for copy, weight in corner:
            weights[copy] = weights.get(copy, 0.0) + scale * weight
    return tuple(sorted((copy, weight) for copy, weight in weights.items() if weight > 1e-12))


def split(triangle, values, level):
    """A triangle (its corners, each a tuple of (copy, weight)) cut where `values` (per corner) cross `level`: its
    pieces as (corners, values); an uncut triangle comes back whole."""
    below = [value < level for value in values]
    if all(below) or not any(below):
        return [(triangle, values)]
    lone = next(corner for corner in range(3) if below.count(below[corner]) == 1)
    first, second = (lone + 1) % 3, (lone + 2) % 3

    def cut(one, other):
        return mixed(triangle[one], triangle[other], (level - values[one]) / (values[other] - values[one]))

    near_first, near_second = cut(lone, first), cut(lone, second)
    return [((triangle[lone], near_first, near_second), (values[lone], level, level)),
            ((near_first, triangle[first], triangle[second]), (level, values[first], values[second])),
            ((near_first, triangle[second], near_second), (level, values[second], level))]


def cut(record, sewn, bands):
    """The garment's triangles cut along its bands' edges: {"faces" (corners into the box points, then the new
    points), "made" (each new point's box points and weights, MOST_MIXED each, padded with weight 0), "corners" (each
    triangle corner's copies and weights, for its texture coordinate), "banded" (a triangle on a band)}."""
    along, kind = placed_along(record, np.asarray(sewn, dtype=float))
    faces, box = np.asarray(record["faces"]), np.asarray(record["box"])
    count = len(np.asarray(record["points"]))
    made, named = [], {}
    out_faces, out_corners, banded = [], [], []

    def point_of(corner):
        """A corner's point: its box point, or a new point (one per mix of box points: shared across a seam)."""
        if len(corner) == 1:
            return int(box[corner[0][0]])
        by_box = {}
        for copy, weight in corner:
            by_box[int(box[copy])] = by_box.get(int(box[copy]), 0.0) + weight
        key = tuple(sorted((point, round(weight, 9)) for point, weight in by_box.items()))
        if key not in named:
            named[key] = count + len(made)
            made.append(key)
        return named[key]

    for number, face in enumerate(faces):
        pieces = [(tuple(((int(copy), 1.0),) for copy in face), tuple(along[number]))]
        if kind[number]:
            for level in levels_of(bands, kind[number]):
                pieces = [piece for triangle, values in pieces for piece in split(triangle, values, level)]
        for triangle, values in pieces:
            out_faces.append([point_of(corner) for corner in triangle])
            out_corners.append(triangle)
            banded.append(bool(kind[number]) and in_band(float(np.mean(values)), bands, kind[number]))
    points = np.zeros((len(made), MOST_MIXED), dtype=np.int64)
    weights = np.zeros((len(made), MOST_MIXED))
    for row, key in enumerate(made):
        for column, (point, weight) in enumerate(key):
            points[row, column], weights[row, column] = point, weight
    return {"faces": np.asarray(out_faces, dtype=np.int64), "made": points, "weights": weights,
            "corners": out_corners, "banded": np.asarray(banded)}


def corner_flat(record, corners):
    """Each triangle corner's place on its flat panel (cm), corners x 2: its copies' places, weighted."""
    flat = np.asarray(record["flat"], dtype=float)
    return np.asarray([sum(weight * flat[copy] for copy, weight in corner) for triangle in corners
                       for corner in triangle])


def frames_with(frames, made, weights):
    """The garment's points every frame (frames x points x 3) with its new points after them."""
    frames = np.asarray(frames, dtype=float)
    if not len(made):
        return frames
    new = np.einsum("fpkx,pk->fpx", frames[:, made], weights)
    return np.concatenate([frames, new], axis=1)
