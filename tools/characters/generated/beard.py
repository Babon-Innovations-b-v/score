"""A generated man's beard split off and regrown as short facial-hair strands (`beard_split`, `beard_strands`).

TRELLIS.2 makes a beard and stubble as lumpy solid skin painted dark. Its triangles are labelled like the scalp hair
(`labels.py`'s colour vote, settled by neighbours, kept where it joins the chin, the beard's and the skin's colours
read again on what was labelled, so the shaded neck reads as skin), its colour read first on the chin in front
(CHIN), within the jaw's region: under the nose, over the throat (THROAT_M under the eyes), in front of the ears.
Under it the skin is the same triangles smoothed (Taubin's, TAUBIN rounds, the beard's edge held, so the lumps go and
the jaw keeps its size), painted the model's skin darkened towards the beard's colour (STUBBLE_DARK) away from its
edge. The strands are rooted on that skin at a beard's density (DENSITY: some 60 to 100 hairs a cm2 on a full beard's
cheeks and chin), the style's stubble at the beard's edge rising to its full length inside (`beard_lengths`: the
model's lumps stand only a millimetre or two, far short of the hairs the close-up shows), leaving the skin out at
OUT_ANGLE and lying down the jaw (gravity along the skin), curled a little each its own way (CURL), a beard hair's
thickness (RADIUS). Under the chin (NECK_UNDER_NOSE_M under the nose) the roots thin out towards the beard's edge
over NECK_FADE_M (`neck_kept`), so the beard fades out down the neck instead of ending on a line (round 1, cut at
THROAT_M, 2026-11-26). Its colour is read on the beard's darkest triangles (DARKEST)."""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from tools.characters.generated import labels
from tools.characters.whole import hair

CHIN = {"under_nose_m": 0.065, "radius_m": 0.012}
THROAT_M = 0.16
HOLE_M2 = 4e-4  # a piece of skin inside the beard smaller than this is the beard's (4 cm2; the lips are more)
MOUTH_UNDER_NOSE_M = 0.035
# The mouth's piece from this far under the nose down to the chin's bottom (CHIN's depth and its radius under it) is
# the chin under the lower lip: a light patch of the beard joined to the lips (the hoodie man's chin, its lumps
# painted pale, showed bare under his regrown beard, 2026-11-28)
LIP_UNDER_NOSE_M = 0.05
GREY_UNDER_NOSE_M = 0.085  # over this (the chin's bottom), a triangle the clothes' colours claim is a beard's grey
# hairs (a grey hood's colour took the grey of a beard's chin, 2026-11-26)
EARS_BEHIND_M = 0.01  # the beard reaches back to this far behind the head's middle (the ears' front)
OVER_NOSE_M = 0.004  # and up to just over the nose's tip (the moustache under it)
# rounds, shrink, swell: the pass band (1/shrink + 1/swell, 0.01) keeps only the jaw's broad shape, some 5 cm and up.
# At (400, 0.5, -0.53) (pass band 0.11) and (1200, 0.5, -0.51) (0.04) the hoodie man's chin knobs, 1.5 to 2 cm across
# and some 5 mm high, passed and stood through his beard as pale lumps (2026-11-28)
TAUBIN = (4000, 0.5, -0.5025)
STUBBLE_DARK = 0.5  # the skin under the beard this far toward its colour (the close-up: dark between the jaw's hairs)
STUBBLE_EDGE_M = 0.006
DENSITY = 0.8e6  # hairs a m2 (a full beard; a style's `beard_density_m2`, read off the close-up, before it)
FULL_FROM_EDGE_M = 0.012  # a beard hair's length rises from stubble at the beard's edge to full this far in
DARKEST = 30  # the beard's colour read on its darkest this percent (the paint mixes the skin between its hairs)
LENGTH_SPREAD = 0.3
OUT_ANGLE = 0.3  # the share of a strand's first direction straight out of the skin
POINTS = 8
CURL = 0.35  # a strand's tip turned off its way by up to this share of its length
RADIUS = 0.00005
SEED = 226
NECK_UNDER_NOSE_M = 0.06
NECK_FADE_M = 0.025


def beard_room(points, faces, frame):
    """Where a beard may be: the jaw's region (under the nose's tip, over the throat, in front of the ears)."""
    middles = points[faces].mean(axis=1)
    eyes = frame["eyes_middle"]
    return ((middles[:, 1] < frame["nose"][1] + OVER_NOSE_M) & (middles[:, 1] > eyes[1] - THROAT_M)
            & (middles[:, 2] > frame["centre"][2] - EARS_BEHIND_M))


def chin_seeds(points, faces, frame):
    """The chin's front triangles, where the beard's colour is read."""
    middles = points[faces].mean(axis=1)
    target = np.array([frame["middle_x"], frame["nose"][1] - CHIN["under_nose_m"]])
    near = np.linalg.norm(middles[:, [0, 1]] - target, axis=1) < CHIN["radius_m"]
    front = middles[near, 2].max()
    return np.flatnonzero(near & (middles[:, 2] > front - 0.01))


def beard_labels(points, faces, colours, frame, scalp_hair):
    """Each triangle's beard label (never one of the scalp's hair) and the beard's colour model."""
    rng = np.random.default_rng(SEED)
    found = labels.seeds(points, faces, frame, colours)
    chin = chin_seeds(points, faces, frame)
    neighbours = labels.adjacency(points, faces)
    room = beard_room(points, faces, frame) & ~scalp_hair
    clothes = found["clothes"]
    face = np.linalg.norm(points[faces].mean(axis=1) - frame["nose"], axis=1) < labels.SKIN_REACH_M
    beard_examples, skin_examples = colours[chin], colours[found["skin"]]
    grey_chin = points[faces].mean(axis=1)[:, 1] > frame["nose"][1] - GREY_UNDER_NOSE_M
    for _ in range(labels.READS):
        kind = labels.nearest_kind(colours, [beard_examples, skin_examples, colours[clothes]], rng)
        bearded = (kind == 0) | ((kind == 2) & grey_chin)
        candidate = (labels.settled(bearded.astype(float), neighbours) > labels.HAIR_SHARE) & room
        beard = labels.connected_to(candidate, chin, neighbours)
        beard_examples = colours[beard]
        skin_examples = colours[face & (kind == 1) & ~beard & ~scalp_hair]
    beard |= holes_in(points, faces, beard, room, neighbours, frame)
    dark = colours[beard][:, 0] <= np.percentile(colours[beard][:, 0], DARKEST)
    return beard, labels.colour_model(colours[beard][dark])


def holes_in(points, faces, beard, room, neighbours, frame):
    """The beard's small holes (pieces of other triangles in its room under HOLE_M2, joined over the triangles'
    neighbours) but the mouth, and the mouth's piece under the lower lip (LIP_UNDER_NOSE_M) down to the chin's
    bottom: a generated beard's light lumps on the chin (grey hairs, painted pale) read as skin."""
    other = room & ~beard
    inside = np.flatnonzero(other)
    count, piece = connected_components(neighbours[other][:, other], directed=False)
    corners = points[faces[inside]]
    area = np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1) / 2.0
    sizes = np.bincount(piece, weights=area, minlength=count)
    mouth = np.array([frame["middle_x"], frame["nose"][1] - MOUTH_UNDER_NOSE_M, frame["nose"][2]])
    middles = points[faces[inside]].mean(axis=1)
    mouth_piece = piece[np.argmin(np.linalg.norm(middles - mouth, axis=1))]
    under = frame["nose"][1] - middles[:, 1]
    chin = (piece == mouth_piece) & (under > LIP_UNDER_NOSE_M) & (under < CHIN["under_nose_m"] + CHIN["radius_m"])
    found = np.zeros(len(faces), dtype=bool)
    found[inside[((sizes[piece] < HOLE_M2) & (piece != mouth_piece)) | chin]] = True
    return found


def welded(points, faces):
    """The points merged where they coincide (a generated mesh splits them along its texture's seams): (unique
    points, each point's unique index)."""
    unique, index = np.unique(np.round(points / 1e-7).astype(np.int64), axis=0, return_inverse=True)
    merged = np.zeros((len(unique), 3))
    np.add.at(merged, index.ravel(), points)
    counts = np.bincount(index.ravel(), minlength=len(unique))[:, None]
    return merged / counts, index.ravel()


def taubin(points, faces, held):
    """The points smoothed TAUBIN rounds over the triangles' edges, the `held` points kept."""
    edges = np.vstack([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    count = len(points)
    graph = coo_matrix((np.ones(len(edges) * 2), (np.r_[edges[:, 0], edges[:, 1]], np.r_[edges[:, 1], edges[:, 0]])),
                       shape=(count, count)).tocsr()
    graph.data[:] = 1.0
    degree = np.maximum(np.asarray(graph.sum(axis=1)), 1.0)
    moved = points.copy()
    rounds, shrink, swell = TAUBIN
    for _ in range(rounds):
        for factor in (shrink, swell):
            step = factor * (graph @ moved / degree - moved)
            moved = moved + np.where(held[:, None], 0.0, step)
    return moved


def beard_split(points, faces, beard):
    """The skin under the beard: (smoothed points for every point of the model, outward normals per point of the
    smoothed skin). Only the beard's points move; its edge (points
    shared with other triangles) holds."""
    merged, index = welded(points, faces)
    welded_faces = index[faces]
    inside = np.zeros(len(merged), dtype=bool)
    inside[np.unique(welded_faces[beard])] = True
    edge = np.zeros(len(merged), dtype=bool)
    edge[np.unique(welded_faces[~beard])] = True
    smooth = taubin(merged, welded_faces[beard], ~inside | edge)
    normals = vertex_normals(smooth, welded_faces[beard])
    return smooth[index], normals[index]


def vertex_normals(points, faces):
    """Area-weighted point normals of the triangles (0 for a point on none)."""
    corners = points[faces]
    face_normal = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    normals = np.zeros_like(points)
    for corner in range(3):
        np.add.at(normals, faces[:, corner], face_normal)
    return hair.unit(normals)


def oriented(normals, places, frame):
    """The normals turned to face out of the head (away from its middle's upright, a little down)."""
    away = places - frame["centre"]
    away[:, 1] *= 0.3
    return normals * np.sign(np.einsum("pi,pi->p", normals, away) + 1e-12)[:, None]


def stubble_colours(points, faces, beard, skin_srgb, beard_srgb):
    """The smoothed skin's colours per point (sRGB): the skin's, darker towards the beard's away from its edge."""
    edge = points[np.unique(faces[~beard])]
    inner = np.unique(faces[beard])
    distance = np.zeros(len(points))
    distance[inner] = cKDTree(edge).query(points[inner], workers=-1)[0]
    share = STUBBLE_DARK * np.clip(distance / STUBBLE_EDGE_M, 0.0, 1.0)
    return skin_srgb * (1.0 - share[:, None]) + beard_srgb * share[:, None]


def beard_lengths(places, smooth, faces, beard, style):
    """Each root's beard length: the style's stubble at the beard's edge rising to its full length (both read off the
    close-up) FULL_FROM_EDGE_M in."""
    edge = smooth[np.unique(faces[~beard])]
    inward = cKDTree(edge).query(places, workers=-1)[0]
    stubble, full = style["beard_stubble_m"], style["beard_length_m"]
    return stubble + (full - stubble) * np.clip(inward / FULL_FROM_EDGE_M, 0.0, 1.0)


def neck_kept(places, smooth, faces, beard, frame, rng):
    """Which roots are kept: all over the chin's line, under it fewer towards the beard's edge (none at it)."""
    edge = smooth[np.unique(faces[~beard])]
    inward = cKDTree(edge).query(places, workers=-1)[0]
    share = np.clip(inward / NECK_FADE_M, 0.0, 1.0)
    share = share * share * (3.0 - 2.0 * share)
    neck = places[:, 1] < frame["nose"][1] - NECK_UNDER_NOSE_M
    return rng.random(len(places)) < np.where(neck, share, 1.0)


def beard_strands(smooth, faces, beard, normals, frame, style):
    """The beard's strands: (counts, points (n x 3), radius per point)."""
    rng = np.random.default_rng(SEED)
    triangles = faces[beard]
    corners = smooth[triangles]
    area = np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1).sum() / 2.0
    places, picked, weights = hair.on_triangles(smooth, triangles, int(area * style.get("beard_density_m2", DENSITY)),
                                                rng)
    kept = neck_kept(places, smooth, faces, beard, frame, rng)
    places, picked, weights = places[kept], picked[kept], weights[kept]
    normal = hair.unit(np.einsum("pc,pcd->pd", weights, normals[triangles[picked]]))
    normal = oriented(normal, places, frame)
    length = beard_lengths(places, smooth, faces, beard, style) * (1.0 + rng.uniform(-LENGTH_SPREAD, LENGTH_SPREAD,
                                                                                       len(places)))
    down = hair.tangent(np.tile([0.0, -1.0, 0.0], (len(places), 1)), normal)
    way = hair.unit(down * (1.0 - OUT_ANGLE) + normal * OUT_ANGLE + rng.normal(0.0, 0.15, (len(places), 3)))
    curl = hair.unit(np.cross(way, rng.normal(size=(len(places), 3))))
    along = np.linspace(0.0, 1.0, POINTS)
    lying = hair.unit(way[:, None] * (1.0 - 0.5 * along[None, :, None]) + down[:, None] * 0.5 * along[None, :, None])
    steps = lying * (length / (POINTS - 1))[:, None, None]
    path = places[:, None] + np.concatenate([np.zeros((len(places), 1, 3)), np.cumsum(steps[:, 1:], axis=1)], axis=1)
    path += curl[:, None] * (CURL * rng.random(len(places)) * length)[:, None, None] * (along ** 2)[None, :, None]
    taper = 1.0 - 0.6 * np.clip((along - 0.7) / 0.3, 0.0, 1.0)
    radius = np.tile(RADIUS * taper, len(places))
    return np.full(len(places), POINTS, np.int64), path.reshape(-1, 3), radius
