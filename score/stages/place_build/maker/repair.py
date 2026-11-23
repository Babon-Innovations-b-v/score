"""A made model's mesh repaired without changing its shape (#167: TRELLIS.2's dual-contoured mesh came out with 30 to
2,290 edges held by four faces, membranes of two opposite faces, collapsed faces and, on the rack, 289 hidden shells).

    repaired(positions, faces, normals=None) -> (sources, positions, faces, counts)   each kept vertex's old index
    repaired_glb(document, binary) -> (document, binary, counts)        the same on a GLB's one primitive, losslessly

Read on corners (vertices at one place are one corner: a texture seam's copies are not an open edge), in order:
- a collapsed face (two corners one) or one of no area is dropped;
- faces on the same three corners: wound against each other they are a membrane with nothing inside and go both; wound
  the same way one is kept;
- a corner whose faces fall into more than one fan (faces joined through edges two faces hold) is one corner a fan:
  each further fan's copy is moved NUDGE of the diagonal into its own fan, so two solids that touched along an edge or
  at a point no longer share it (the edge held by four faces becomes two edges held by two; its faces paired by the
  solid wedge between them, and a surface folded onto itself along the edge cut there);
- a piece (faces joined through corners) under LOOSE of the area is dropped;
- each piece is wound one way (trimesh's fix_winding) and outward as the model's own vertex normals look.
"""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

TINY = 1e-6  # a face whose area is under (TINY x the diagonal) squared has none (the bench's weld, measures/_mesh)
NUDGE = 1e-5  # a further fan's corner is moved this share of the diagonal into its fan: 10 x the bench's weld
# A piece under this share of the area is dropped: the bench's crumb (measures/_clean.CRUMB), its count barred at the
# truth's own (0 on the printer box). On tc1's four TRELLIS.2 models 692 of the 698 pieces under it lay inside the body
# (a ray test), the rest within 0.8% of the diagonal of it; the smallest pieces kept are 0.12% and up.
LOOSE = 0.001


def diagonal(positions):
    return float(np.linalg.norm(positions.max(0) - positions.min(0)))


def corners_of(positions, scale):
    """Each vertex's corner: vertices nearer than TINY of the diagonal `scale` are one corner (joined in chains)."""
    from scipy.spatial import cKDTree
    near = cKDTree(positions).query_pairs(scale * TINY, output_type="ndarray")
    graph = coo_matrix((np.ones(len(near)), (near[:, 0], near[:, 1])), shape=(len(positions), len(positions)))
    return connected_components(graph, directed=False)[1]


def crossed(positions, faces):
    """Each face's edge cross product: its normal as wound, twice its area long."""
    points = positions[faces]
    return np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0])


def areas(positions, faces):
    return 0.5 * np.linalg.norm(crossed(positions, faces), axis=1)


def unspoiled(corner_faces, area, scale):
    """The faces that keep: no two corners one, some area."""
    collapsed = (corner_faces[:, 0] == corner_faces[:, 1]) | (corner_faces[:, 1] == corner_faces[:, 2]) \
        | (corner_faces[:, 0] == corner_faces[:, 2])
    return ~collapsed & (area > (scale * TINY) ** 2)


def unrepeated(corner_faces):
    """The faces that keep of each set on the same three corners: none of a membrane (as many wound each way), else
    one wound the way most of them are."""
    ordered = np.sort(corner_faces, axis=1)
    _, group, count = np.unique(ordered, axis=0, return_inverse=True, return_counts=True)
    group = group.reshape(-1)
    lowest = np.argmin(corner_faces, axis=1)
    rolled = corner_faces[np.arange(len(corner_faces))[:, None], (lowest[:, None] + np.arange(3)) % 3]
    way = np.where(rolled[:, 1] == ordered[:, 1], 1, -1)  # +1 wound lowest, middle, highest; -1 the other way
    net = np.bincount(group, weights=way)
    first = np.full(len(count), -1)
    keeper = np.where(way == np.sign(net)[group])[0]
    first[group[keeper[::-1]]] = keeper[::-1]  # the first face of each group wound the net way
    keep = np.zeros(len(corner_faces), bool)
    keep[first[first >= 0]] = True
    return keep


def half_edges(corner_faces):
    """Every face's three edges as (start, end, the start's slot, the end's slot, its edge, how many faces hold its
    edge); half-edge place x faces + face, slots face x 3 + place, edges numbered in sorted order."""
    slots = np.arange(3 * len(corner_faces)).reshape(-1, 3)
    starts = corner_faces.T.reshape(-1)
    ends = corner_faces[:, [1, 2, 0]].T.reshape(-1)
    _, which, held = np.unique(np.sort(np.stack([starts, ends], 1), axis=1), axis=0, return_inverse=True,
                               return_counts=True)
    return starts, ends, slots.T.reshape(-1), slots[:, [1, 2, 0]].T.reshape(-1), which.reshape(-1), held


def wedge_pairs(points, members):
    """(half-edge, half-edge) pairs of each edge more than two faces hold (`members`, its half-edges; `points`, each
    half-edge's face's corners as (start, end, third)): around the edge each face is paired with the next one turning
    one way when the wedge between them is behind both, the solid they bound, so two solids touching along the edge
    keep their own faces; two faces left over are a pair."""
    first, second = [], []
    for halves in members:
        start, end, third = points[halves, 0], points[halves, 1], points[halves, 2]
        along = (end[0] - start[0]) / max(np.linalg.norm(end[0] - start[0]), 1e-30)
        wing = (third - start[0]) - np.outer((third - start[0]) @ along, along)
        across = wing[0] / max(np.linalg.norm(wing[0]), 1e-30)
        turn = np.arctan2(wing @ np.cross(along, across), wing @ across)
        normal = np.cross(end - start, third - start)
        facing = np.sign(np.einsum("ij,ij->i", normal, np.cross(along, wing)))  # +1: it looks the way the turn goes
        order = np.argsort(turn)
        taken = set()
        for place, half in enumerate(order):
            following = order[(place + 1) % len(order)]
            if facing[half] < 0 < facing[following]:
                first.append(halves[half])
                second.append(halves[following])
                taken.update((half, following))
        left = [half for half in order if half not in taken]
        if len(left) == 2:  # a fold the turn cannot tell (two faces looking one way side by side): the last two pair
            first.append(halves[left[0]])
            second.append(halves[left[1]])
    return np.array(first, dtype=np.int64), np.array(second, dtype=np.int64)


def fans(positions, faces, corner_faces, cut=()):
    """Each face corner's fan (face, slot -> a label): face corners at one corner joined through an edge two faces
    hold, or through a pair of an edge more hold (wedge_pairs) unless the edge is `cut` (its index among the sorted
    edges)."""
    count = len(corner_faces)
    rolled = faces[:, [[0, 1, 2], [1, 2, 0], [2, 0, 1]]].transpose(1, 0, 2).reshape(-1, 3)  # half-edge order
    starts, ends, start_slot, end_slot, which, held = half_edges(corner_faces)
    two = np.where(held[which] == 2)[0]
    two = two[np.argsort(which[two], kind="stable")].reshape(-1, 2)  # the two half-edges of each such edge
    more = np.where((held[which] > 2) & ~np.isin(which, cut))[0]
    more = more[np.argsort(which[more], kind="stable")]
    members = np.split(more, np.flatnonzero(np.diff(which[more])) + 1) if len(more) else []
    paired = wedge_pairs(positions[rolled], members)
    first = np.concatenate([two[:, 0], paired[0]])
    second = np.concatenate([two[:, 1], paired[1]])
    same = starts[first] == starts[second]  # wound the same way: start meets start
    rows = np.concatenate([start_slot[first], end_slot[first]])
    columns = np.concatenate([np.where(same, start_slot[second], end_slot[second]),
                              np.where(same, end_slot[second], start_slot[second])])
    graph = coo_matrix((np.ones(len(rows)), (rows, columns)), shape=(3 * count, 3 * count))
    return connected_components(graph, directed=False)[1].reshape(count, 3)


def stuck(corner_faces, fan):
    """The edges more than two faces hold whose faces are one fan at both ends: one surface folded onto itself along
    the edge, which pairing cannot part; cut there, each end's fan falls into the two sides of the fold."""
    starts, ends, start_slot, end_slot, which, held = half_edges(corner_faces)
    flat = fan.reshape(-1)
    low = np.minimum(starts, ends) == starts
    at_low = np.where(low, flat[start_slot], flat[end_slot])
    at_high = np.where(low, flat[end_slot], flat[start_slot])
    one = np.ones(len(held), bool)
    for side in (at_low, at_high):
        least = np.full(len(held), np.iinfo(np.int64).max)
        most = np.full(len(held), -1)
        np.minimum.at(least, which, side)
        np.maximum.at(most, which, side)
        one &= least == most
    return np.flatnonzero(one & (held > 2))


def split(positions, faces, corner_faces, scale):
    """(sources, positions, faces, corners split): each further fan of a corner given its own vertices, moved NUDGE of
    the diagonal toward its fan's face centres."""
    fan = fans(positions, faces, corner_faces)
    folded = stuck(corner_faces, fan)
    if len(folded):
        fan = fans(positions, faces, corner_faces, folded)
    pairs = np.unique(np.stack([corner_faces.reshape(-1), fan.reshape(-1)], 1), axis=0)
    first_fan = np.full(corner_faces.max() + 1, -1)
    first_fan[pairs[::-1, 0]] = pairs[::-1, 1]
    further = fan != first_fan[corner_faces]
    if not further.any():
        return np.arange(len(positions)), positions, faces, 0
    centres = positions[faces].mean(1)
    slot_face, slot = np.nonzero(further)
    fan_key = np.stack([corner_faces[slot_face, slot], fan[slot_face, slot]], 1)
    _, fan_of = np.unique(fan_key, axis=0, return_inverse=True)  # the direction is the corner's fan's: seam copies
    fan_of = fan_of.reshape(-1)                                     # of one fan move together and stay one corner
    towards = np.zeros((fan_of.max() + 1, 3))
    np.add.at(towards, fan_of, centres[slot_face] - positions[faces[slot_face, slot]])
    towards /= np.maximum(np.linalg.norm(towards, axis=1, keepdims=True), 1e-30)
    keys, at, new = np.unique(np.stack([faces[slot_face, slot], fan[slot_face, slot]], 1), axis=0,
                              return_index=True, return_inverse=True)
    new = new.reshape(-1)
    added = positions[keys[:, 0]] + towards[fan_of[at]] * scale * NUDGE
    faces = faces.copy()
    faces[slot_face, slot] = len(positions) + new
    split_corners = int(fan_of.max() + 1)
    return (np.concatenate([np.arange(len(positions)), keys[:, 0]]), np.concatenate([positions, added]),
            faces, split_corners)


def pieces(corner_faces, corners):
    """Each face's piece: faces joined through corners."""
    rows = np.concatenate([corner_faces[:, 0], corner_faces[:, 1]])
    columns = np.concatenate([corner_faces[:, 1], corner_faces[:, 2]])
    graph = coo_matrix((np.ones(len(rows)), (rows, columns)), shape=(corners, corners))
    return connected_components(graph, directed=False)[1][corner_faces[:, 0]]


def unloose(corner_faces, area, corners):
    """The faces of pieces of LOOSE of the area or more; the pieces dropped."""
    piece = pieces(corner_faces, corners)
    share = np.bincount(piece, weights=area) / max(area.sum(), 1e-30)
    small = share < LOOSE
    return ~small[piece], int(len(np.unique(piece[small[piece]])))


def outward(positions, faces, corner_faces, reference):
    """Which faces to turn so every face is wound like its piece (trimesh's fix_winding) and each piece looks the way
    `reference`, each face's look, does (its vertex normals' sum: TRELLIS.2's agree with its winding on 99.4% to 100%
    of tc1's faces; a signed volume of an open piece turned whole real parts inside out)."""
    import trimesh
    mesh = trimesh.Trimesh(np.zeros((corner_faces.max() + 1, 3)), corner_faces, process=False)  # its topology alone
    trimesh.repair.fix_winding(mesh)
    wound = np.asarray(mesh.faces)
    rows = np.arange(len(corner_faces))
    turned = corner_faces[rows, (np.argmin(corner_faces, 1) + 1) % 3] != wound[rows, (np.argmin(wound, 1) + 1) % 3]
    agree = np.where(turned, -1.0, 1.0) * np.einsum("ij,ij->i", crossed(positions, faces), reference)
    piece = pieces(corner_faces, corner_faces.max() + 1)
    return turned ^ (np.bincount(piece, weights=agree) < 0)[piece]


def repaired(positions, faces, normals=None):
    """(sources, positions, faces, counts): the mesh repaired (module docstring), outward as its vertex `normals` look
    (as most of its faces are wound without them); `sources` each new vertex's old index, every vertex no face holds
    left out."""
    positions = np.asarray(positions, dtype=np.float64)
    faces = np.asarray(faces, dtype=np.int64)
    scale = diagonal(positions)
    corner = corners_of(positions, scale)
    keep = unspoiled(corner[faces], areas(positions, faces), scale)
    counts = {"faces": len(faces), "collapsed": int((~keep).sum())}
    faces = faces[keep]
    keep = unrepeated(corner[faces])
    counts["repeated"] = int((~keep).sum())
    faces = faces[keep]
    sources, positions, faces, counts["corners_split"] = split(positions, faces, corner[faces], scale)
    corner = corners_of(positions, scale)
    keep, counts["loose_pieces"] = unloose(corner[faces], areas(positions, faces), corner.max() + 1)
    counts["loose_faces"] = int((~keep).sum())
    faces = faces[keep]
    reference = crossed(positions, faces) if normals is None else np.asarray(normals, np.float64)[sources][faces].sum(1)
    turned = outward(positions, faces, corner[faces], reference)
    faces[turned] = faces[turned][:, ::-1]
    counts["turned"] = int(turned.sum())
    used, faces = np.unique(faces, return_inverse=True)
    counts["kept_faces"] = len(faces.reshape(-1, 3))
    return sources[used], positions[used], faces.reshape(-1, 3), counts


# --- the GLB ---------------------------------------------------------------------------------------------------------

COMPONENTS = {5121: np.uint8, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def accessor_array(document, binary, number):
    """Accessor `number`'s values; refused unless it alone fills a tight buffer view (what the maker's GLBs hold)."""
    accessor = document["accessors"][number]
    view = document["bufferViews"][accessor["bufferView"]]
    if view.get("byteStride") or accessor.get("byteOffset", 0) or accessor.get("sparse"):
        raise ValueError(f"accessor {number}: strided, offset or sparse; repair reads tight views only")
    kind = np.dtype(COMPONENTS[accessor["componentType"]])
    width = WIDTH[accessor["type"]]
    start = view.get("byteOffset", 0)
    values = np.frombuffer(binary[start:start + accessor["count"] * width * kind.itemsize], dtype=kind)
    return values.reshape(accessor["count"], width) if width > 1 else values


def primitive_of(document):
    """The GLB's one triangle primitive; refused for any other."""
    primitives = [primitive for mesh in document.get("meshes", []) for primitive in mesh["primitives"]]
    if len(primitives) != 1 or primitives[0].get("mode", 4) != 4 or "indices" not in primitives[0]:
        raise ValueError("repair takes one indexed triangle primitive")
    return primitives[0]


def with_accessor(document, number, values):
    """Accessor `number` set to `values` (count and bounds); the bytes its view takes."""
    accessor = document["accessors"][number]
    kind = COMPONENTS[accessor["componentType"]]
    if np.issubdtype(kind, np.integer) and len(values) and values.max() > np.iinfo(kind).max:
        raise ValueError(f"accessor {number}: {values.max()} does not fit its {np.dtype(kind)}")
    values = np.ascontiguousarray(values, dtype=kind)
    accessor["count"] = int(len(values))
    if "max" in accessor or "min" in accessor:
        flat = values.reshape(len(values), -1)
        accessor["max"] = flat.max(0).tolist()
        accessor["min"] = flat.min(0).tolist()
    return values.tobytes()


def repaired_glb(document, binary):
    """(document, binary, counts): the GLB's one primitive repaired, every attribute carried with its vertex (a moved
    copy keeps its texture place and normal), the rest of the file as it was."""
    from score.stages.place_build.maker import glb
    primitive = primitive_of(document)
    positions = accessor_array(document, binary, primitive["attributes"]["POSITION"])
    faces = accessor_array(document, binary, primitive["indices"]).reshape(-1, 3)
    normals = primitive["attributes"].get("NORMAL")
    sources, moved, faces, counts = repaired(positions, faces, None if normals is None else
                                             accessor_array(document, binary, normals))
    pieces = {}
    for name, number in primitive["attributes"].items():
        values = moved if name == "POSITION" else accessor_array(document, binary, number)[sources]
        pieces[document["accessors"][number]["bufferView"]] = with_accessor(document, number, values)
    indices = primitive["indices"]
    pieces[document["accessors"][indices]["bufferView"]] = with_accessor(document, indices, faces.reshape(-1))
    return document, glb.with_views(document, binary, pieces), counts
