"""Small hardware laid as library pieces (#212): a lock, knob, handle, hinge or latch the finish list read off the
close-up as a hardware mark (finish_ask.piece_row: its box, kind, library piece, the finish it is mounted on and the
finish it is) placed on the made model where the close-up shows it, in place of the blob TRELLIS.2 draws there.

    placements(marks, model, camera, size, finish_of, part_of, picture)   ([placement], [gap]) of a take's hardware
                                                                          marks

A placement, in the take's own frame (metres, the model file's axes, as a decal's): `at` the point on the face the
piece is mounted on under its box's middle, `normal` that face's facing, `up` the close-up's up laid on it, `size`
[wide, tall] its box laid on that face, `part` the part of the face it is joined to, `finish` the finish (0-based, the
list's) it is painted in (the piece's own finish, else its face's), and `cut`: the blob cut away, every vertex of the
model within `radius` of the line through the cut's own `at` along `normal` and between `depth` under the face and
`rise` over it moved onto the face (the face's surface fills the cut, flat; the last `falloff` of the radius eased, so
no step rings it), its faces left as they are. The faces it
flattens (`cut_faces`) are covered as a print under a mark is (route_parts.covered_prints): the blob's own finish there
takes its face's.

The piece's box is the list's box measured again on the close-up (`piece_box`): the list's boxes run loose and off
the piece by up to half themselves (tc6's locker: the lower-left lock's box held only a corner of the lock), so the
piece is the patch of pixels apart from the face's colour by PIECE_DE, opened PIECE_OPEN times (a door's seam, a line of
a few pixels, is no piece), that overlaps the box most within the box grown PIECE_GROW of its sides each way (the list's box where that patch runs
PIECE_MOST times past it). The face is read
round that box, never under it (the blob is there): the faces seen on a RING_GRID x RING_GRID grid over the box grown
RING_GROW times, outside the box, of any finish but the piece's own and turned within FACE_TURN of the most of them,
their mean normal its facing and the median of their points along it its plane. Its library piece is then stood on that plane, scaled evenly and moved until the close-up sees it fill the box
(`fitted`), so its size and spot are the piece's as the close-up shows it, its own depth seen aslant included, never
the blob's. The blob is the model's own: its vertices standing BLOB_LOW over the face within
SEARCH half diagonals of the piece, joined by the mesh's edges, a group standing BLOB_HIGH at its highest (a face's
own bumps stand under it); the nearest group no other piece took is cut (TRELLIS.2 laid the tc6 locker's lower-left
knob 0.14 m off its lock), its middle the cut's `at`, its farthest vertex across the face grown by CUT_MARGIN its
flat core (the radius less its falloff, so no part of the blob is only eased); the cut's `at` and the piece's are then laid on the model's own surface round each (`surface_height`), the
piece's on its cut's where it stands in it. A cut stops short of its face's edge (blob_cut), and moves only the blob's vertices (standing CUT_STANDS over the
face) and the face's own (look.py cut_away: turned within the cut's `edge_turn` of its facing), never an edge to
another face. With no such group, or one reaching past CUT_MOST half diagonals,
the cut is the piece's own spot and half diagonal.
"""
import numpy as np

import route_cast as cast

RING_GROW = 2.2   # the box grown this many times each way: the face round it is read in that ring (#212)
RING_GRID = 15
RING_FEWEST = 8   # a piece whose face is seen at fewer ring points than this is a gap: no face to lay it on
# The face round a piece is the ring's faces turned within FACE_TURN degrees of the most of them, of any finish but the
# piece's own: the gas stove's knobs sit on a printed panel the split cut into several finishes, and their ring, the box
# grown, reaches over the stove's top edge.
FACE_TURN = 25.0
# Metres under the face a vertex may lie and still be lifted onto it: the face's own bumps and the groove TRELLIS.2
# rings its blobs with (at 0.002 the tc6 locker's lock blobs left that groove standing as a ring of folds).
CUT_DEPTH = 0.006
CUT_RISE = 2.0    # a vertex is cut only up to this many times the piece's larger side over the face
CUT_MARGIN = 1.2  # the cut's radius: the blob's farthest standing vertex across the face grown by this
FALLOFF = 0.25    # the outer share of a cut's radius over which its lift eases to none (look.py cut_away)
# Degrees a vertex's normal may turn from a cut's facing past its flat core and still be moved (the cut's `edge_turn`,
# look.py cut_away): the gas stove's knobs fill their narrow side panel, and drawn in with it the stove's top and foot
# were pinched in.
EDGE_TURN = 60.0
CUT_STANDS = 0.002  # metres: a vertex standing this over a cut's face is the blob's, moved however it is turned
EDGE_SHARE = 0.9  # a cut stops at this share of the way to its face's nearest edge (edge_reach)
GROOVE, GROOVE_TURN = 0.015, 10.0  # metres past an edge the face may go on, and degrees off its way: a groove
LEAST_FALLOFF = 0.1  # a cut's falloff, narrowed to stop short of an edge, never under this share of its radius
# The face under a cut is the model's own round it (surface_height): its vertices from the cut's radius to SURROUND
# times it, within SURFACE_REACH under the plane read round the box (the tc6 locker's doors bow: their plane read
# round the box lay 6 mm over the face at the locks, and the flattened blobs stood as rings over it).
SURROUND, SURFACE_REACH = 1.5, 0.02
SEARCH = 5.0      # the blob is looked for within this many of the piece's half diagonals of its middle
FIT_ROUNDS = 4    # rounds of fitted's scale and move
CUT_MOST = 4.0    # a group reaching further than this many half diagonals is no blob but the face standing off its plane
BLOB_LOW, BLOB_HIGH = 0.004, 0.008  # metres: a blob's vertex stands this over the face; a blob this at its highest
PIECE_GROW = 1.0  # a piece is looked for in its box grown this many of its sides each way (piece_box)
# sRGB distance from the face's colour (the grown box's median) of a piece's pixels, and the openings that drop a thin
# line from them: at 25 and one opening the tc6 locker's right locks joined their door's seam and its soft shadow,
# 39 x 141 px for a lock of about 30 x 43.
PIECE_DE, PIECE_OPEN = 40.0, 2
# A patch wider or taller than this many times the list's box is the print round the piece, not the piece (the gas
# stove's knobs on their red and white printed panel): the list's box is kept.
PIECE_MOST = 1.3


def ring_pixels(box):
    """The close-up pixels of a RING_GRID x RING_GRID grid over `box` ([left, top, wide, tall]) grown RING_GROW times
    about its middle, those inside the box left out."""
    left, top, wide, tall = box
    middle = np.array([left + wide / 2, top + tall / 2])
    steps = (np.arange(RING_GRID) + 0.5) / RING_GRID - 0.5
    grid = np.array([[across, down] for down in steps for across in steps]) * RING_GROW * np.array([wide, tall])
    outside = (np.abs(grid[:, 0]) > wide / 2) | (np.abs(grid[:, 1]) > tall / 2)
    return middle + grid[outside]


def on_plane(camera, size, pixels, normal, offset):
    """Where the close-up's rays through `pixels` meet the plane {point: point . normal = offset}, in the model file's
    own frame (route_cast.pixel_ways: the rays' ways, the same in any frame of one scale); NaN where a ray runs along
    it."""
    ways = cast.pixel_ways(camera, size, pixels)
    eye = np.asarray(camera[0], dtype=float)
    along = ways @ normal
    reach = np.where(np.abs(along) > 1e-9, (offset - eye @ normal) / np.where(along == 0, 1, along), np.nan)
    return eye + ways * reach[:, None]


def face_round(mark, model, camera, size, finish_of, part_of):
    """(normal, offset, part) of the face a hardware mark is mounted on, read round its box (module docstring), or
    (None, None, why)."""
    faces, points = cast.cast_points(model, camera, size, ring_pixels(mark["box"]))
    kept = (faces >= 0) & (finish_of[np.maximum(faces, 0)] != mark.get("print_finish"))
    turned = model.mesh.face_normals[faces[kept]]
    if len(turned):  # the faces turned as most of them are: the face, not one beyond an edge
        alike = turned @ turned.T > np.cos(np.radians(FACE_TURN))
        kept[np.flatnonzero(kept)[~alike[int(alike.sum(1).argmax())]]] = False
    if kept.sum() < RING_FEWEST:
        return None, None, f"its face is seen at {int(kept.sum())} points round its box, under {RING_FEWEST}"
    normal = model.mesh.face_normals[faces[kept]].mean(0)
    normal /= max(float(np.linalg.norm(normal)), 1e-9)
    if normal @ (np.asarray(camera[0]) - points[kept].mean(0)) < 0:  # a face is seen from the side it faces
        normal = -normal
    offset = float(np.median(points[kept] @ normal))
    return normal, offset, int(np.bincount(part_of[faces[kept]]).argmax())


def piece_box(box, picture):
    """The piece's own box ([left, top, wide, tall] close-up pixels) measured on the close-up (`picture`, RGBA 0-255)
    about the list's `box` (module docstring); the list's box where no patch of pixels apart from the face is."""
    from scipy import ndimage
    left, top, wide, tall = box
    rows, columns = picture.shape[:2]
    low_column, low_row = max(0, int(left - PIECE_GROW * wide)), max(0, int(top - PIECE_GROW * tall))
    high_column = min(columns, int(np.ceil(left + (1 + PIECE_GROW) * wide)))
    high_row = min(rows, int(np.ceil(top + (1 + PIECE_GROW) * tall)))
    crop = picture[low_row:high_row, low_column:high_column].astype(float)
    shown = crop[..., 3] > 127
    if not shown.any():
        return list(box)
    face = np.median(crop[..., :3][shown], axis=0)
    apart = ndimage.binary_opening(shown & (np.linalg.norm(crop[..., :3] - face, axis=-1) > PIECE_DE),
                                   iterations=PIECE_OPEN)
    patches, count = ndimage.label(apart)
    if not count:
        return list(box)
    inside = np.zeros(apart.shape, dtype=bool)
    inside[max(0, int(top) - low_row):int(np.ceil(top + tall)) - low_row,
           max(0, int(left) - low_column):int(np.ceil(left + wide)) - low_column] = True
    overlap = np.bincount(patches[inside].ravel(), minlength=count + 1)[1:]
    if not overlap.any():
        return list(box)
    found_rows, found_columns = np.nonzero(patches == int(overlap.argmax()) + 1)
    found = [int(low_column + found_columns.min()), int(low_row + found_rows.min()),
             int(np.ptp(found_columns)) + 1, int(np.ptp(found_rows)) + 1]
    return list(box) if found[2] > PIECE_MOST * wide or found[3] > PIECE_MOST * tall else found


def blob_groups(model, at, normal, half, rise):
    """([its vertices' indices] of each group of the model's vertices standing BLOB_LOW to `rise` over the face within
    SEARCH half diagonals of `at`, joined by the mesh's edges, that stands BLOB_HIGH at its highest; the model's
    vertices in the take's own frame)."""
    from scipy import sparse
    from scipy.sparse.csgraph import connected_components
    middle, side = model.frame
    vertices = np.asarray(model.mesh.vertices) * side + middle
    offset = vertices - at
    height = offset @ normal
    across = np.linalg.norm(offset - np.outer(height, normal), axis=1)
    standing = (height > BLOB_LOW) & (height < rise) & (across < SEARCH * half)
    edges = model.mesh.edges_unique
    edges = edges[standing[edges[:, 0]] & standing[edges[:, 1]]]
    graph = sparse.coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])), shape=(len(vertices),) * 2)
    _, group = connected_components(graph, directed=False)
    found = [np.flatnonzero(standing & (group == number)) for number in np.unique(group[standing])]
    return [members for members in found if height[members].max() >= BLOB_HIGH], vertices


def surface_height(vertices, centre, normal, reach):
    """The height over the plane through `centre` (along `normal`) of the model's own surface about it: the median of
    its vertices within `reach` ((nearest, farthest) across the plane) lying SURFACE_REACH under to BLOB_LOW over the
    plane (neither a blob nor what lies behind the face); 0 where none does."""
    offset = vertices - centre
    height = offset @ normal
    across = np.linalg.norm(offset - np.outer(height, normal), axis=1)
    near = (across >= reach[0]) & (across < reach[1]) & (height > -SURFACE_REACH) & (height < BLOB_LOW)
    return float(np.median(height[near])) if near.any() else 0.0


def edge_reach(model, vertices, centre, normal, rise, core):
    """How far across the face from `centre` its nearest edge lies past the blob's `core`: the nearest vertex there
    within `rise` of the face whose normal turns from the face's by more than EDGE_TURN (another face, not a bump), and
    past which the face does not go on (no vertex of the face, on it and turned with it, lies GROOVE further out within
    GROOVE_TURN degrees of it: a door's seam is a groove the face goes on past, the gas stove's side panel ends at its
    top's fold); infinity where none does."""
    offset = vertices - centre
    height = offset @ normal
    way = offset - np.outer(height, normal)
    across = np.linalg.norm(way, axis=1)
    facing = model.mesh.vertex_normals @ normal
    near = (np.abs(height) < rise) & (across > core)
    off = np.flatnonzero(near & (facing < np.cos(np.radians(EDGE_TURN))))
    on = np.flatnonzero(near & (np.abs(height) < CUT_DEPTH) & (facing > np.cos(np.radians(FACE_TURN))))
    if not len(off):
        return np.inf
    if len(on):
        ways = way / np.maximum(across, 1e-12)[:, None]
        aligned = ways[off] @ ways[on].T > np.cos(np.radians(GROOVE_TURN))
        beyond = (across[on][None, :] > across[off][:, None]) & (across[on][None, :] < across[off][:, None] + GROOVE)
        off = off[~(aligned & beyond).any(1)]
    return float(across[off].min()) if len(off) else np.inf


def blob_cut(model, at, normal, half, rise, taken):
    """(the cut's point, its radius, its falloff, the piece's point) of the blob nearest `at` that no piece has taken
    (`taken`, a set of the groups' first vertex, added to): the group's middle laid on the face round it and its reach,
    and the piece's point laid on the face under it (module docstring); the piece's own spot and `half` where no group
    is. A cut stops at EDGE_SHARE of the way to its face's edge (edge_reach), its flat core shrunk to keep
    LEAST_FALLOFF of it eased (the gas stove's knobs fill their narrow side panel: cut past it, the stove's top lip and
    foot were drawn in)."""
    groups, vertices = blob_groups(model, at, normal, half, rise)
    groups = [members for members in groups if int(members[0]) not in taken]
    if not groups:
        lift = surface_height(vertices, at, normal, (0.0, 2 * half))
        return at + lift * normal, half, FALLOFF, at + lift * normal
    laid = [vertices[members] - np.outer((vertices[members] - at) @ normal, normal) for members in groups]
    nearest = int(np.argmin([np.linalg.norm(points.mean(0) - at) for points in laid]))
    centre = laid[nearest].mean(0)
    core = float(np.linalg.norm(laid[nearest] - centre, axis=1).max()) * CUT_MARGIN
    if core > CUT_MOST * half:  # no blob: the face stands off the plane read round the box
        lift = surface_height(vertices, at, normal, (0.0, 2 * half))
        return at + lift * normal, half, FALLOFF, at + lift * normal
    radius = min(core / (1 - FALLOFF), EDGE_SHARE * edge_reach(model, vertices, centre, normal, rise, core))
    falloff = 1 - min(core, radius * (1 - LEAST_FALLOFF)) / radius
    taken.add(int(groups[nearest][0]))
    centre = centre + surface_height(vertices, centre, normal, (radius, SURROUND * radius)) * normal
    if np.linalg.norm((at - centre) - ((at - centre) @ normal) * normal) < radius:  # the piece stands in its cut
        return centre, radius, falloff, at + ((centre - at) @ normal) * normal
    return centre, radius, falloff, at + surface_height(vertices, at, normal, (0.0, 2 * half)) * normal


def seen_at(camera, size, points):
    """The close-up pixels ([column, row]) the `points` (the model file's own frame) are seen at through `camera`
    (close_up_camera's: eye, right, up, field), as route_cast casts its pixels."""
    eye, right, up, field = camera
    focal = size[0] / 2 / np.tan(field / 2)
    relative = np.asarray(points, dtype=float) - eye
    depth = relative @ np.cross(up, right)
    return np.c_[size[0] / 2 + focal * (relative @ right) / depth, size[1] / 2 - focal * (relative @ up) / depth]


def fitted(mark, camera, size, plane, axes, at):
    """(the piece's point on its face, its (wide, tall)) fitted to its box: its library piece (the mark's
    `piece_size`, wide, tall and deep) standing on the face (`plane`: normal, offset) along `axes` (right, up), scaled
    evenly and moved on the face until the box round its corners as the close-up sees them spans the mark's box and
    shares its middle (FIT_ROUNDS rounds from `at`). Seen aslant its depth widens its box (the gas stove's knobs, 23 mm
    deep on a side seen at a slant, read 60% too wide laid flat)."""
    normal, offset = plane
    right, up = axes
    wide, tall, deep = mark["piece_size"]
    left, top, box_wide, box_tall = mark["box"]
    goal = np.array([left + box_wide / 2, top + box_tall / 2])
    scale = 1.0
    for _ in range(FIT_ROUNDS):
        corners = np.array([at + scale * (across * wide / 2 * right + upward * tall / 2 * up + out * deep * normal)
                            for across in (-1, 1) for upward in (-1, 1) for out in (0, 1)])
        seen = seen_at(camera, size, corners)
        low, high = seen.min(0), seen.max(0)
        scale *= float(np.mean([box_wide / max(high[0] - low[0], 1e-9), box_tall / max(high[1] - low[1], 1e-9)]))
        moved = on_plane(camera, size, [goal, (low + high) / 2], normal, offset)
        at = at + moved[0] - moved[1]
    return at, (scale * wide, scale * tall)


def placement(mark, number, model, seen, finish_of, part_of, taken):
    """One hardware mark's placement (module docstring), or (None, why it cannot be laid); `seen` the close-up's
    (camera, size, picture RGBA), `taken` the blobs other pieces cut (blob_cut)."""
    camera, size, picture = seen
    mark = dict(mark, box=piece_box(mark["box"], picture))
    normal, offset, part = face_round(mark, model, camera, size, finish_of, part_of)
    if normal is None:
        return None, part
    left, top, wide, tall = mark["box"]
    pixels = [[left + wide / 2, top + tall / 2], [left, top + tall / 2], [left + wide, top + tall / 2],
              [left + wide / 2, top], [left + wide / 2, top + tall]]
    middle, west, east, north, south = on_plane(camera, size, pixels, normal, offset)
    if not np.isfinite([middle, west, east, north, south]).all():
        return None, "its face is seen edge-on"
    up = (north - south) - ((north - south) @ normal) * normal
    if np.linalg.norm(up) < 1e-9:
        return None, "its box has no height on its face"
    up /= np.linalg.norm(up)
    right = np.cross(up, normal)
    across, upward = abs(float((east - west) @ right)), abs(float((north - south) @ up))
    if mark.get("piece_size"):
        middle, (across, upward) = fitted(mark, camera, size, (normal, offset), (right, up), middle)
    half = float(np.hypot(across, upward)) / 2
    rise = CUT_RISE * max(across, upward)
    cut_at, radius, falloff, middle = blob_cut(model, middle, normal, half, rise, taken)
    rounded = lambda vector: [round(float(value), 5) for value in vector]  # noqa: E731
    own = mark.get("print_finish")
    return {"hardware": mark["hardware"], "kind": mark.get("kind"), "moves": mark.get("moves"), "part": part,
            "finish": own if own is not None else mark["on_finish"], "at": rounded(middle), "normal": rounded(normal),
            "up": rounded(up), "size": [round(across, 5), round(upward, 5)], "layer": number,
            "cut": {"at": rounded(cut_at), "radius": round(radius, 5), "depth": CUT_DEPTH, "rise": round(rise, 5),
                    "falloff": round(falloff, 4), "edge_turn": EDGE_TURN, "stands": CUT_STANDS},
            "what": mark.get("what", ""), "from": {"close_up_box": mark["box"], "seen": "close-up"}}, None


def cut_faces(model, placement):
    """The faces a placement's cut flattens: their middles within its radius of the line through its point along its
    facing, and from its depth under its face to its rise over it (look.py cut_away's vertices, by the faces')."""
    middle, side = model.frame
    reach = model.mesh.triangles_center * side + middle - np.asarray(placement["cut"]["at"])
    normal = np.asarray(placement["normal"])
    height = reach @ normal
    across = np.linalg.norm(reach - np.outer(height, normal), axis=1)
    cut = placement["cut"]
    return np.flatnonzero((across < cut["radius"]) & (height > -cut["depth"]) & (height < cut["rise"]))


def placements(marks, model, camera, size, finish_of, part_of, picture):
    """([placement], [gap]) of a take's hardware marks (shape finish_ask.PIECE) cast through its own close-up
    (`model` a route_cast.Model, `camera` close_up_camera's, `size` the close-up's, `picture` it, RGBA 0-255);
    `finish_of` and `part_of` each face's finish and part. A mark with a gap, or that cannot be laid, is a gap naming
    why."""
    found, gaps, taken = [], [], set()
    for number, mark in enumerate(marks):
        if mark.get("gap"):
            gaps.append({"what": mark.get("what", ""), "hardware": mark.get("hardware"), "why": mark["gap"]})
            continue
        laid, why = placement(mark, number, model, (camera, size, picture), finish_of, part_of, taken)
        if laid is None:
            gaps.append({"what": mark.get("what", ""), "hardware": mark["hardware"], "why": why})
        else:
            found.append(laid)
    return found, gaps
