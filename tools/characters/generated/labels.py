"""Which of a generated person's triangles are its hair (`hair_labels`), read from the model's own paint and place.

TRELLIS.2 paints the hair onto one solid shell with the head (no separate hair part, no scalp under it). Each triangle
gets the base colour its texture shows over it (`face_colours`: the texture read at its corners and middle, in CIELAB),
and the hair's colour is read where only hair can be: the head's top (TOP_M under its highest point), the skin's on
the cheeks beside the nose (`head_frame` finds the nose as the head's frontmost point). A triangle looks like hair when
its colour lies nearer the hair's than the skin's (each measured in its own spread) and within HAIR_SPREAD of it; that
likeness is then settled by its neighbours (SETTLE rounds of averaging over the triangles' edges, so the hairline runs
where the paint's edge runs, not along single triangles) and kept only where it joins the top's hair (one connected
piece) and lies on the head or hangs from it: never on the face in front (FACE_BOX: a fringe stops over the brows)
and, for a style with a beard, never in front of the ears under the eyes (the beard stays paint, like the brows).
"""
import numpy as np
import trimesh
from PIL import Image
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
from skimage.color import rgb2lab

TOP_M = 0.015  # the hair's colour is read on the triangles this far under the head's top
NOSE_BAND_M = (0.08, 0.26)  # the nose is the frontmost point this far under the top
SKIN_HUE = {"least_l": 35.0, "a": (4.0, 35.0), "b": (6.0, 40.0)}  # a skin's colour in CIELAB
EYES_OVER_NOSE_M = 0.035  # the eyes' line over the nose's tip
EYES_HALF_M = 0.031  # each eye's half the eyes' distance off the middle
EYES_BEHIND_NOSE_M = 0.02
CHEEK = {"beside_m": 0.035, "under_eyes_m": 0.03, "radius_m": 0.012}  # where the skin's colour is read
CLOTHES_UNDER_EYES_M = 0.34  # the clothes' colours are read this far under the eyes and lower
CLOTHES_SHARE = 0.75  # a bust's: its lowest this share of the way from the eyes down
NOT_HAIR_DELTA = 6.0
BOTTOM_M = 0.03  # the model's lowest this is clothes whatever its colour (a bust's cut through a dark coat)
K_NEAREST = 7  # a colour is the kind whose this many nearest examples lie nearest it
EXAMPLES = 6000  # each kind read from at most this many examples
READS = 4  # the hair's colour read again on what was labelled hair this many times
SEED = 223
STRAY_M = 0.02
BROWS_OVER_EYES_M = 0.05
CLOSEUP = {"size": 512, "delta": 10.0, "columns": (0.4, 0.6), "filled": 0.5, "rows": (0.015, 0.08)}
HAIR_SHARE = 0.65  # a triangle is hair when this share of its neighbourhood reads as hair (the paint's soft edge
# read at a half crept a few mm onto the face)
SKIN_REACH_M = 0.12  # the skin's colour read again on the skin this near the nose (its shaded sides too)
NEIGHBOURS = 10  # each triangle's neighbours: this many nearest
NEIGHBOUR_M = 0.006  # within this
SETTLE = 6  # rounds of averaging the likeness over the triangles' edges
FACE_BOX = {"half_m": 0.06, "over_eyes_m": 0.015, "under_eyes_m": 0.16, "behind_front_m": 0.05}
BEARD = {"under_eyes_m": 0.02}  # with a beard, nothing under this and in front of the head's middle is scalp hair
HANG_M = 0.32  # hair hangs at most this far under the eyes (to the shoulders)
SAMPLE_WEIGHTS = ((1, 0, 0), (0, 1, 0), (0, 0, 1), (1 / 3, 1 / 3, 1 / 3))


def loaded(path, height_m):
    """The glb as one mesh scaled so it stands `height_m` tall (y up, the face looking along +z): (points, faces, uv,
    texture as an (h, w, 3) uint8 array)."""
    mesh = trimesh.load(str(path), force="mesh", process=False)
    points = np.asarray(mesh.vertices, float)
    points = points * (height_m / np.ptp(points[:, 1]))
    texture = np.asarray(mesh.visual.material.baseColorTexture.convert("RGB"))
    return points, np.asarray(mesh.faces), np.asarray(mesh.visual.uv, float), texture


def face_colours(faces, uv, texture):
    """Each triangle's base colour in CIELAB: the texture read at its corners and middle, averaged."""
    height, width = texture.shape[:2]
    corners = uv[faces]
    total = np.zeros((len(faces), 3))
    for weights in SAMPLE_WEIGHTS:
        at = np.einsum("c,fcd->fd", np.asarray(weights, float), corners)
        column = np.clip((at[:, 0] % 1.0) * (width - 1), 0, width - 1).astype(int)
        row = np.clip((1.0 - at[:, 1] % 1.0) * (height - 1), 0, height - 1).astype(int)
        total += texture[row, column] / 255.0
    return rgb2lab((total / len(SAMPLE_WEIGHTS))[None])[0]


def skin_like(colours):
    """Which colours (CIELAB) are a skin's: light enough and in skin's hues (warm, a little red, more yellow)."""
    return ((colours[:, 0] > SKIN_HUE["least_l"]) & (colours[:, 1] > SKIN_HUE["a"][0])
            & (colours[:, 1] < SKIN_HUE["a"][1])
            & (colours[:, 2] > SKIN_HUE["b"][0]) & (colours[:, 2] < SKIN_HUE["b"][1]))


def head_frame(points, faces, colours):
    """The head's frame: {top, middle_x, nose, eyes (2 x 3), eyes_middle, centre}. The nose is the frontmost
    skin-coloured triangle NOSE_BAND_M under the top (a lock of hair or a collar in front of the face is not); the
    centre is hair.py's: the eyes' height, the nose's x and the z of the head's cap."""
    top = points[:, 1].max()
    middles = points[faces].mean(axis=1)
    band = (middles[:, 1] < top - NOSE_BAND_M[0]) & (middles[:, 1] > top - NOSE_BAND_M[1]) & skin_like(colours)
    nose = middles[band][np.argmax(middles[band, 2])]
    middle_x = float(nose[0])
    cap = points[(points[:, 1] > top - 0.10) & (np.abs(points[:, 0] - middle_x) < 0.12)]
    eyes_y, eyes_z = nose[1] + EYES_OVER_NOSE_M, nose[2] - EYES_BEHIND_NOSE_M
    eyes = np.array([[middle_x - EYES_HALF_M, eyes_y, eyes_z], [middle_x + EYES_HALF_M, eyes_y, eyes_z]])
    centre = np.array([middle_x, eyes_y, float(np.median(cap[:, 2]))])
    return {"top": float(top), "middle_x": middle_x, "nose": nose, "eyes": eyes, "eyes_middle": eyes.mean(axis=0),
            "centre": centre}


def colour_model(colours):
    """A colour's median and spread (L, a, b; one sigma, read robustly)."""
    median = np.median(colours, axis=0)
    return median, 1.4826 * np.median(np.abs(colours - median), axis=0)


def seeds(points, faces, frame, colours):
    """Where each colour is read: {hair: the head's top triangles, skin: the cheeks' beside the nose, clothes: every
    triangle CLOTHES_UNDER_EYES_M under the eyes, or for a bust its lowest CLOTHES_SHARE under them (the clothes and
    whatever skin shows there), less any within NOT_HAIR_DELTA of the top's colours (hair hanging that low), and the
    model's lowest BOTTOM_M}."""
    middles = points[faces].mean(axis=1)
    top = np.flatnonzero(middles[:, 1] > frame["top"] - TOP_M)
    cheeks = []
    for side in (-1.0, 1.0):
        target = frame["eyes_middle"] + np.array([side * CHEEK["beside_m"], -CHEEK["under_eyes_m"], 0.0])
        near = middles[np.abs(middles[:, 0] - target[0]) < CHEEK["radius_m"]]
        near = near[np.abs(near[:, 1] - target[1]) < CHEEK["radius_m"]]
        front = near[:, 2].max()
        cheeks.append(np.flatnonzero((np.linalg.norm(middles[:, [0, 1]] - target[[0, 1]], axis=1) < CHEEK["radius_m"])
                                     & (middles[:, 2] > front - 0.01)))
    eyes = frame["eyes_middle"][1]
    under = min(CLOTHES_UNDER_EYES_M, CLOTHES_SHARE * (eyes - points[:, 1].min()))
    clothes = np.flatnonzero(middles[:, 1] < eyes - under)
    near_hair = cKDTree(colours[top]).query(colours[clothes], workers=-1)[0] < NOT_HAIR_DELTA
    bottom = np.flatnonzero(middles[:, 1] < points[:, 1].min() + BOTTOM_M)
    return {"hair": top, "skin": np.concatenate(cheeks), "clothes": np.union1d(clothes[~near_hair], bottom)}


def nearest_kind(colours, examples, rng):
    """Each colour's kind by its K_NEAREST nearest example colours (CIELAB) of each kind, the kind whose are nearest
    on average: (kind index per colour, in the order of `examples`)."""
    distances = []
    for found in examples:
        picked = found if len(found) <= EXAMPLES else found[rng.choice(len(found), EXAMPLES, replace=False)]
        distances.append(cKDTree(picked).query(colours, k=min(K_NEAREST, len(picked)), workers=-1)[0]
                         .reshape(len(colours), -1).mean(axis=1))
    return np.argmin(np.stack(distances, axis=1), axis=1)


def adjacency(points, faces):
    """The triangles' neighbours as a symmetric sparse matrix: the NEIGHBOURS nearest by their middles within
    NEIGHBOUR_M (a generated mesh's triangles are often joined at a corner only, or not at all, across its seams)."""
    middles = points[faces].mean(axis=1)
    distance, index = cKDTree(middles).query(middles, k=NEIGHBOURS + 1, distance_upper_bound=NEIGHBOUR_M, workers=-1)
    rows = np.repeat(np.arange(len(faces)), NEIGHBOURS)
    columns = index[:, 1:].ravel()
    kept = np.isfinite(distance[:, 1:].ravel())
    rows, columns = rows[kept], columns[kept]
    count = len(faces)
    ones = np.ones(len(rows) * 2)
    return coo_matrix((ones, (np.r_[rows, columns], np.r_[columns, rows])), shape=(count, count)).tocsr()


def settled(score, neighbours):
    """The likeness averaged with its edge neighbours SETTLE times."""
    degree = np.asarray(neighbours.sum(axis=1)).ravel()
    for _ in range(SETTLE):
        score = (score + neighbours @ score) / (1.0 + degree)  # (a pair met twice counts twice)
    return score


def allowed(points, faces, frame, beard, reach_m):
    """Where scalp hair may be: on the head or hanging from it to the shoulders, never further under the top than the
    style's length (`reach_m`: a bob's ends over the scarf under them), never on the face in front (over the
    brows a fringe may lie), and with a beard never in front of the head's middle under the eyes."""
    middles = points[faces].mean(axis=1)
    eyes = frame["eyes_middle"]
    under = eyes[1] - middles[:, 1]
    face = ((np.abs(middles[:, 0] - frame["middle_x"]) < FACE_BOX["half_m"])
            & (middles[:, 1] < eyes[1] + FACE_BOX["over_eyes_m"]) & (under < FACE_BOX["under_eyes_m"])
            & (middles[:, 2] > frame["nose"][2] - FACE_BOX["behind_front_m"]))
    keep = ~face & (under < HANG_M) & (middles[:, 1] > frame["top"] - reach_m)
    if beard:
        keep &= ~((under > BEARD["under_eyes_m"]) & (middles[:, 2] > frame["centre"][2]))
    return keep


def hair_labels(points, faces, colours, frame, beard, reach_m):
    """Each triangle's label (True: hair) and the colours' models: (labels, {hair, skin: (median Lab, spread)}). The
    hair's colour is read on the head's top and the skin's on the cheeks, then READS times again on all the triangles
    labelled so (their lights and shadows; the skin's within SKIN_REACH_M of the nose), against the clothes'."""
    rng = np.random.default_rng(SEED)
    found = seeds(points, faces, frame, colours)
    neighbours = adjacency(points, faces)
    room = allowed(points, faces, frame, beard, reach_m)
    clothes = found["clothes"][~np.isin(found["clothes"], found["hair"])]
    hair_examples, skin_examples = colours[found["hair"]], colours[found["skin"]]
    face = np.linalg.norm(points[faces].mean(axis=1) - frame["nose"], axis=1) < SKIN_REACH_M
    labels = np.zeros(len(faces), dtype=bool)
    for _ in range(READS):
        kind = nearest_kind(colours, [hair_examples, skin_examples, colours[clothes]], rng)
        candidate = (settled((kind == 0).astype(float), neighbours) > HAIR_SHARE) & room
        labels = connected_to(candidate, found["hair"], neighbours)
        hair_examples = colours[labels]
        skin_examples = colours[face & (kind == 1) & ~labels]
    labels |= strays_of(points, faces, (kind == 0) & room & ~labels & ~brows(points, faces, frame), labels)
    return labels, {"hair": colour_model(colours[labels]), "skin": colour_model(colours[found["skin"]])}


def brows(points, faces, frame):
    """The face's front from the cheeks to BROWS_OVER_EYES_M over the eyes: dark paint there is brows, never a stray."""
    middles = points[faces].mean(axis=1)
    return ((np.abs(middles[:, 0] - frame["middle_x"]) < FACE_BOX["half_m"])
            & (middles[:, 1] < frame["eyes_middle"][1] + BROWS_OVER_EYES_M)
            & (middles[:, 2] > frame["nose"][2] - FACE_BOX["behind_front_m"]))


def strays_of(points, faces, loose, labels):
    """The `loose` hair-coloured triangles within STRAY_M of the labelled hair: a generated model's thin painted
    tendrils and wisps round the hair's outline, too thin to settle or to join over their neighbours (left on the
    model, they stood as dark wires round the regrown hair, 2026-11-26)."""
    middles = points[faces].mean(axis=1)
    near = cKDTree(middles[labels]).query(middles[loose], distance_upper_bound=STRAY_M, workers=-1)[0] < STRAY_M
    found = np.zeros(len(faces), dtype=bool)
    found[np.flatnonzero(loose)[near]] = True
    return found


def connected_to(candidate, top, neighbours):
    """The candidate triangles in a piece (joined over the triangles' edges) holding one of the `top` triangles."""
    inside = np.flatnonzero(candidate)
    _, piece = connected_components(neighbours[candidate][:, candidate], directed=False)
    top_pieces = np.unique(piece[np.searchsorted(inside, np.intersect1d(top, inside))])
    labels = np.zeros(len(candidate), dtype=bool)
    labels[inside[np.isin(piece, top_pieces)]] = True
    return labels


def closeup_hair(path):
    """The hair's colour in the close-up photograph the model was made from: (sRGB 0..1, CIELAB), read under the
    head's top: the first rows of the picture's middle (CLOSEUP["columns"]) that differ from the plain backdrop (its
    top corners' colour) by more than CLOSEUP["delta"], then CLOSEUP["rows"] of the picture's height under them."""
    picture = Image.open(path).convert("RGB")
    picture = np.asarray(picture.resize((CLOSEUP["size"], CLOSEUP["size"]))) / 255.0
    lab = rgb2lab(picture)
    corner = CLOSEUP["size"] // 16
    backdrop = np.median(np.concatenate([lab[:corner, :corner].reshape(-1, 3), lab[:corner, -corner:].reshape(-1, 3)]),
                         axis=0)
    differs = np.linalg.norm(lab - backdrop, axis=-1) > CLOSEUP["delta"]
    left, right = (int(share * CLOSEUP["size"]) for share in CLOSEUP["columns"])
    rows = np.flatnonzero(differs[:, left:right].mean(axis=1) > CLOSEUP["filled"])
    first = int(rows[0])
    low, high = (first + int(share * CLOSEUP["size"]) for share in CLOSEUP["rows"])
    region = differs[low:high, left:right]
    return (np.median(picture[low:high, left:right][region], axis=0),
            np.median(lab[low:high, left:right][region], axis=0))
