"""A generated head gets real eyes behind its lids and its painted hair regrown (#223). Each break named below turns
its row red: each painted pupil
is found on the face (eyes.pupils, a pupil missed or found on a lid or brow turns it red), the eyeball sits behind
its lid margins with its cornea behind their rim (eyes.eye_depth: a ball bulging past the lids, or one sunk far
behind them, turns it red), the painted floor inside the ball is removed and nothing outside the lid opening is
(eyes.buried), the floor beside the ball is pushed straight back and no lid point moves (eyes.pushed: a lid pushed in
or a floor left standing turns it red), the wet line lies on the lids' inner rims round both eyes (eyes.wet_strip),
both eyes gaze at one point straight ahead (eyes.made's gaze, eyes.placed: a crossed or wall-eyed pair turns it red),
the iris's colour is read off the photo's iris (eyes.photo_iris: a colour read off the eye's white or the skin round
it turns it red), a lid margin is read where the lid stands, steep or gentle, never on a bump or a curve of the
painted floor (eyes.margin_along: a margin taken on the floor lets the floor beyond it cover the iris and turns it
red), and an eye with no lid margin over or under it is refused (eyes.eye_depth).

Shapes made here: a face as a height field (a curved front, a nose, two sunken lid openings with steep walls and a
flat painted floor, an iris and a pupil painted on each floor), its paint a small picture; a sphere with rings of UV
standing in for ICT-FaceKit's eyeball; a small photo of two irises on skin with a pupil and a highlight.

The hair, on a toy painted head (a ball, its top half pushed out as a hair shell and painted dark, a nose, a body
under it in a coat's colour): the labels cover the painted top and nothing else; the scalp leaves no hole over the
hair, stays under its shell and meets the skin at its edge; the strands root on the scalp, stay out of the head and
reach into the shell; a darker colour gets more melanin and a grey head white strands. Breaks that turn its rows red
(each applied once, seen red, reverted, 2026-11-26): every triangle hair whatever its neighbours
(`labels.HAIR_SHARE` 0: extra 119%); the scalp let out through the shell (`scalp.CLEAR_M` -0.03: 165 directions
through); the scalp tucked 6 mm under the skin (`scalp.TUCK_M` 0.006: a 5.7 mm step at its edge); the head's inside
let into the hair's volume (`volume.inside_of` and `volume.seen_from` saying nothing is inside the head: 32% of the
strands into it); the lightness table turned round (`fibre.REFERENCE_L`: the dark colour less melanin than the light).

The head swap (`head_swap.py`), on a toy head (a squashed sphere with a nose, an ear and a bun) moved by a known
similarity (scale 0.3, a turn, a shift): it is found again from its points, exactly by the least-squares similarity
(which fits a turn, never a mirror, even onto the toy's mirror image) and to a millimetre (under the points' own
spacing) by the two-way trimmed ICP from a start 15% off in scale and 8 mm off in place, upright as the real starts
are, with a sixth of its points stray; the scan's best scale is read between its steps (the vertex of the parabola
through the least miss); the seam's weight is all body at the cut and none at the band's top; a UV triangle's texels
are those inside it; and the head-to-body matrix written for the glTF files moves a glTF point where the Blender
matrix moves it. Breaks that turn its rows red (each applied once, seen red, reverted, 2026-11-26): the rotation's
reflection guard dropped (`sign` left the identity: the mirror image fitted by a reflection); the scale read over the
target's spread, not the source's (`target_centred.var`); the ICP fitting every pair, not the kept share (`kept`
1.0: the strays pull the fit off); `lowest` returning the scanned step (0.26, not 0.257); `head_swap.eased` rising,
not falling, with height; `gltf_matrix`'s frame change applied on one side only (`blender_matrix @ to_blender`).

The skin, on a flat front painted with soft blobs and a photo of it under a known map: the photo is found from a start
4 px and 2% off to within a pixel (`skin.registered`); a shading that follows the normal is divided out, a highlight's
excess mostly pressed off and recoloured to the skin's, plain skin kept (`skin.shading`, `skin.gloss_free`); a point
wears the photo only facing forward, on the front, inside the photo's face and clear of the eye's floor, and the T-zone
holds the nose, not the cheek (`skin.grid_share`, `skin.point_shares`, `skin.tzone`). Breaks that turn its rows red
(each applied once, seen red, reverted, 2026-11-26): one search of half a millimetre (`skin.ROUNDS` (0.0005,): 8.7 px
off); no shading taken off (`skin.SHADING_RANGE` (1, 1)); no gloss pressed (`skin.GLOSS` left 1); every slope facing
(`skin.FACING` (-1, -0.5): the turned side wears the photo); every point on the front (`skin.VISIBLE_M` 1: the hidden
point wears it); no fade at the eye (`skin.EYE_CLEAR_M` below 0: the eye's floor wears it).

The lids (`lids.py`), on two spheres behind a flat face 4 mm in front of them, each opening an ellipse 13 mm tall over
a deep floor, the photo's 9 mm: the refined mesh keeps its area, leaves no crack and carries its UVs; the photo's
opening is read round each eye at its own scale and held inside the ball; after the reshape the opening's top and
bottom lie on the photo's, the lid's front LID_M over the eye just outside them and no lid point inside the eye; upper
lashes root just outside the margin and rise, lower ones fall, all leaving forward; a brow's hairs grow where its photo
is dark and lie on the skin; a painted brow is painted over with the skin round it. Breaks that turn their rows red
(each applied once, seen red, reverted, 2026-11-26): only the chosen triangles split, their neighbours not closed
(`lids.refined`); the corner hold dropped (`lids.photo_outline`); the lid's front 3 mm over the eye
(`lids.lid_profile`); the points not moved across (`lids.moved_across`); the lid let 3 mm into the eye
(`lids.reshaped`); the lashes' curl turned round (`lids.lid_lashes`); every brow place kept whatever the photo's
darkness (`lids.brow_hairs`); the brow left painted (`lids.unpainted`).
"""
import functools

import numpy as np
import pytest
import trimesh
from scipy.spatial import cKDTree

from tools.characters.generated import __main__, eyes, fibre, head_swap, labels, lids, scalp, skin, strands, volume
from tools.characters.whole import hair

NOSE_Y = 0.06
EYES_OVER_NOSE = 0.037
EYES_APART = 0.064
OPENING_M = (0.013, 0.006)  # half width and half height of each lid opening
SOCKET_DEPTH_M = 0.006
WALL_SHARE = 0.8  # the opening's wall rises from this share of its size to its edge
SKIN = (0.8, 0.6, 0.5)
PAINTED_IRIS = (0.3, 0.2, 0.1)


def spaced(low, high, fine_low, fine_high, fine, coarse):
    """Grid lines from low to high, `fine` apart between fine_low and fine_high and `coarse` apart elsewhere."""
    return np.unique(np.concatenate([np.arange(low, high + 1e-9, coarse), np.arange(fine_low, fine_high, fine)]))


def opening_share(x, y):
    """Each point's place in the nearer lid opening: 0 at its middle, 1 on its edge."""
    shares = [np.hypot((x - side * EYES_APART / 2) / OPENING_M[0], (y - NOSE_Y - EYES_OVER_NOSE) / OPENING_M[1])
              for side in (-1, 1)]
    return np.min(shares, axis=0)


def front_of(x, y):
    """The face's depth without its sockets: a curved front and a nose."""
    return 0.10 - 3.0 * x ** 2 + 0.025 * np.exp(-0.5 * ((x / 0.008) ** 2 + ((y - NOSE_Y) / 0.008) ** 2))


def surface(x, y):
    """The face's depth: its front with two sockets sunk SOCKET_DEPTH_M inside steep walls."""
    front = front_of(x, y)
    sunk = np.clip((1.0 - opening_share(x, y)) / (1.0 - WALL_SHARE), 0.0, 1.0)
    return front - SOCKET_DEPTH_M * sunk


@functools.lru_cache(maxsize=None)
def face():
    """The height-field face: (points, triangles, uv, texture), y up, looking along +z, its top at 0.24 m."""
    eye_y = NOSE_Y + EYES_OVER_NOSE
    xs = spaced(-0.075, 0.075, -0.05, 0.05, 0.0004, 0.002)
    ys = spaced(0.0, 0.24, eye_y - 0.012, eye_y + 0.012, 0.0004, 0.002)
    grid_x, grid_y = np.meshgrid(xs, ys)
    points = np.column_stack([grid_x.ravel(), grid_y.ravel(), surface(grid_x, grid_y).ravel()])
    width = len(xs)
    corner = (np.arange(len(ys) - 1)[:, None] * width + np.arange(width - 1)[None, :]).ravel()
    triangles = np.vstack([np.column_stack([corner, corner + 1, corner + width + 1]),
                           np.column_stack([corner, corner + width + 1, corner + width])])
    uv = np.column_stack([(points[:, 0] + 0.075) / 0.15, points[:, 1] / 0.24])
    rows, cols = np.mgrid[:600, :600]
    paint_x, paint_y = cols / 599 * 0.15 - 0.075, (599 - rows) / 599 * 0.24
    texture = np.ones((600, 600, 3)) * SKIN
    for side in (-1, 1):
        out = np.hypot(paint_x - side * EYES_APART / 2, paint_y - eye_y)
        texture[out < 0.00585] = PAINTED_IRIS
        texture[out < 0.002] = 0.02
    return points, triangles, uv, texture


def photo(iris):
    """A 400 px photo of two irises of sRGB colour `iris` on skin, each with its white, pupil and highlight."""
    picture = np.ones((400, 400, 3)) * (0.78, 0.66, 0.6)
    rows, cols = np.mgrid[:400, :400]
    for col in (170, 230):
        white = np.hypot((cols - col) / 2.2, rows - 160) < 6.5
        out = np.hypot(cols - col, rows - 160)
        picture[white] = (0.85, 0.82, 0.8)
        picture[out < 5.6] = iris
        picture[out < 2.0] = 0.02
        picture[np.hypot(cols - col - 2, rows - 158) < 1.0] = 1.0
    return picture


def face_module_iris_uv():
    """The face module's iris ring on the eyeball's UV."""
    return eyes.face_modules()[0].IRIS_UV


def sphere_eye():
    """A stand-in for ICT-FaceKit's eyeball (cm): a sphere looking along +z, its UV in rings out from its front."""
    ball = trimesh.creation.icosphere(subdivisions=4, radius=1.2)
    points = np.asarray(ball.vertices)
    theta = np.arccos(np.clip(points[:, 2] / 1.2, -1, 1))
    phi = np.arctan2(points[:, 1], points[:, 0])
    out = face_module_iris_uv() * theta / np.radians(28.0)  # the iris's edge 28 degrees off the front, as on ICT's eye
    point_uv = 0.5 + out[:, None] * np.column_stack([np.cos(phi), np.sin(phi)])
    triangles = np.asarray(ball.faces)
    eye = {"points": points, "triangles": triangles, "uv": point_uv[triangles]}
    face_module, _ = eyes.face_modules()
    return {**eye, "finish": face_module.eye_finish(eye["uv"]), "centre": np.zeros(3), "axis": np.array([0, 0, 1.0]),
            "radius": 1.2}


@functools.lru_cache(maxsize=None)
def made():
    """The eyes made on the height-field face with brown irises in its photo."""
    points, triangles, uv, texture = face()
    return eyes.made(points, triangles, uv, texture, photo((0.36, 0.2, 0.12)),
                     {"right": sphere_eye(), "left": sphere_eye()})


def pupils_found():
    """Each found pupil within half a millimetre of its painted one."""
    found = np.array(made()["stats"]["pupils_m"])
    painted = np.array([[-EYES_APART / 2, NOSE_Y + EYES_OVER_NOSE], [EYES_APART / 2, NOSE_Y + EYES_OVER_NOSE]])
    return (np.linalg.norm(found - painted, axis=1) < 0.0005).tolist()


def behind_lids():
    """Whether the ball is behind every lid margin over and under the pupil (by at least RIM_GAP_M less a tenth of a
    millimetre) and its cornea's apex behind the opening's rim but within 2 mm of it."""
    result = made()
    centres = np.array(result["stats"]["eye_centres_m"])
    radius = result["stats"]["eye_diameter_mm"] / 2000.0
    gaps, apexes = [], []
    for centre in centres:
        angles = np.radians(np.r_[np.arange(45, 140, 10), np.arange(225, 320, 10)])
        edge = 1.0 / np.sqrt(np.cos(angles) ** 2 / OPENING_M[0] ** 2 + np.sin(angles) ** 2 / OPENING_M[1] ** 2)
        x, y = centre[0] + edge * np.cos(angles), centre[1] + edge * np.sin(angles)
        margin = surface(x, y)
        gaps.append(margin - (centre[2] + np.sqrt(radius ** 2 - edge ** 2)))
        apexes.append(margin.mean() - (centre[2] + radius * (1 + eyes.CORNEA_RISE)))
    return [bool(np.min(gaps) > eyes.RIM_GAP_M - 0.0001), bool(0.0 < np.min(apexes) < 0.002)]


def floor_removed():
    """Whether every removed triangle lies inside the opening and the floor under each pupil is removed."""
    removed = made()["removed"]
    if not len(removed):
        return [True, False]
    inside = opening_share(removed[:, 0], removed[:, 1]) < 1.0
    under = [np.min(np.hypot(removed[:, 0] - side * EYES_APART / 2, removed[:, 1] - NOSE_Y - EYES_OVER_NOSE)) < 0.001
             for side in (-1, 1)]
    return [bool(inside.all()), all(under)]


def floor_pushed_lids_kept():
    """Whether every pushed point lay inside an opening at least LID_EDGE_M (less 0.2 mm, the margin found a little
    under the front's top) behind the face's front, so no lid moved, and went straight back (never forward or
    sideways), the floor beside the ball now as deep as the ball's middle (within the stats' rounding)."""
    result = made()
    start, end = result["moved_from"], result["moved_to"]
    centres = np.array(result["stats"]["eye_centres_m"])
    radius = result["stats"]["eye_diameter_mm"] / 2000.0
    on_floor = ((opening_share(start[:, 0], start[:, 1]) < 1.0)
                & (front_of(start[:, 0], start[:, 1]) - start[:, 2] > eyes.LID_EDGE_M - 0.0002))
    straight_back = np.allclose(start[:, :2], end[:, :2]) and bool((end[:, 2] <= start[:, 2]).all())
    across = np.min([np.hypot(end[:, 0] - centre[0], end[:, 1] - centre[1]) for centre in centres], axis=0)
    beside = across >= radius
    shaded = bool((end[beside, 2] <= centres[:, 2].max() + 1e-5).all())
    return [bool(on_floor.all()), straight_back, shaded, bool(len(start) > 0)]


def wet_line_on_rims():
    """Whether the wet line lies on the lids' inner rims (each triangle's centre inside or by an opening's edge and no
    deeper than a millimetre past LID_EDGE_M behind the face's front there) and runs round both eyes."""
    strip = made()["wet"]
    wet = strip["points"][strip["triangles"]].mean(axis=1)
    near_edge = opening_share(wet[:, 0], wet[:, 1]) <= 1.1
    below_front = front_of(wet[:, 0], wet[:, 1]) - wet[:, 2]
    on_rim = (below_front > -0.0002) & (below_front < eyes.LID_EDGE_M + 0.001)
    sides = {int(np.sign(x)) for x in wet[:, 0]}
    return [bool(near_edge.all()), bool(on_rim.all()), sides == {-1, 1}]


def gaze_agrees():
    """Whether both eyes' pupils (the eyeball's pupil finish) look at one point, straight ahead within a degree."""
    result = made()
    eye_points, centres = result["eyes"], np.array(result["stats"]["eye_centres_m"])
    pupil_triangles = eye_points["triangles"][eye_points["finish"] == 2]
    pupil_points = eye_points["points"][pupil_triangles].mean(axis=1)
    looks = []
    for centre in centres:
        own = pupil_points[np.linalg.norm(pupil_points - centre, axis=1) < 0.02]
        way = own.mean(axis=0) - centre
        looks.append(way / np.linalg.norm(way))
    target = np.array([centres[:, 0].mean(), centres[:, 1].mean(), centres[:, 2].max() + eyes.GAZE_M])
    aimed = [np.degrees(np.arccos(np.clip(look @ ((target - centre) / np.linalg.norm(target - centre)), -1, 1)))
             for look, centre in zip(looks, centres)]
    return bool(max(aimed) < 1.0)


def iris_read(srgb):
    """Whether the photo's iris colour is read within a tenth of its own (linear), the pupil and highlight left out."""
    colour, _, _ = eyes.photo_iris(photo(srgb))
    wanted = eyes.srgb_to_linear(srgb)
    return bool(np.all(np.abs(colour - wanted) <= 0.1 * wanted + 0.002))


def margins_read():
    """Where margin_along puts the lid on three rays out from a pupil (millimetres out, the ray sampled every
    STEP_M): a steep lid at 6 mm, a gentle one (rising 2 mm over 3.5 mm) ending at 9 mm, and a steep lid at 8 mm
    behind a 1.2 mm bump on the floor at 4 mm; and nothing along a floor that only curves up slowly."""
    out = np.arange(0.0, 0.014, eyes.STEP_M)
    steep = np.clip((out - 0.005) / 0.001, 0.0, 1.0) * 0.005
    gentle = np.clip((out - 0.0055) / 0.0035, 0.0, 1.0) * 0.002
    bumped = 0.0012 * np.exp(-0.5 * ((out - 0.004) / 0.0004) ** 2) + np.clip((out - 0.007) / 0.001, 0, 1) * 0.005
    curved = 0.19 * out
    found = [eyes.margin_along(depth, 1.0, 0.0) for depth in (steep, gentle, bumped, curved)]
    return [None if index is None else round(out[index] * 1000) for index in found]


def lidless_refused():
    """An eye with lid margins only beside it (none over or under) is refused."""
    margins = np.array([[0.012, 0.0, 0.1, 0.0], [-0.012, 0.0, 0.1, 180.0]])
    try:
        eyes.eye_depth(np.zeros(2), margins, 0.012)
    except ValueError:
        return "refused"
    return "placed"


HEAD = np.array([0.0, 1.6, 0.0])
RADIUS = 0.09
SHELL_M = 0.015
COLOURS = {"hair": (8.0, 2.0, 3.0), "skin": (70.0, 15.0, 24.0), "coat": (40.0, -5.0, 0.0)}


@functools.lru_cache(maxsize=1)
def toy():
    """(points, faces, Lab colour per face, hair truth per face, frame)."""
    ball = trimesh.creation.icosphere(subdivisions=4, radius=RADIUS)
    points = np.asarray(ball.vertices).copy()
    up = points[:, 1] / RADIUS
    front = points[:, 2] / RADIUS
    cap = np.clip((up - 0.05) / 0.15, 0.0, 1.0) * (front < 0.75)
    points += points / RADIUS * (SHELL_M * cap)[:, None]
    nose = np.exp(-((points[:, 0] / 0.015) ** 2 + ((points[:, 1] + 0.035) / 0.02) ** 2)) * (front > 0.0)
    points[:, 2] += 0.02 * nose
    points += HEAD
    body = trimesh.creation.cylinder(radius=0.16, height=0.45)
    body.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2.0, [1, 0, 0]))
    body.apply_translation([0.0, 1.6 - RADIUS - 0.04 - 0.225, 0.0])
    body = body.subdivide().subdivide()
    faces = np.vstack([np.asarray(ball.faces), np.asarray(body.faces) + len(points)])
    points = np.vstack([points, np.asarray(body.vertices)])
    truth = np.zeros(len(faces), dtype=bool)
    truth[:len(ball.faces)] = cap[np.asarray(ball.faces)].mean(axis=1) > 0.5
    colours = np.tile(COLOURS["skin"], (len(faces), 1))
    colours[truth] = COLOURS["hair"]
    colours[len(ball.faces):] = COLOURS["coat"]
    colours += np.random.default_rng(1).normal(0.0, 1.0, colours.shape)
    return points, faces, colours, truth, labels.head_frame(points, faces, colours)


def labelled():
    points, faces, colours, _, frame = toy()
    return labels.hair_labels(points, faces, colours, frame, False, 0.3)[0]


def labels_hold():
    found, truth = labelled(), toy()[3]
    missed = (truth & ~found).sum() / truth.sum()
    extra = (found & ~truth).sum() / truth.sum()
    return missed < 0.05 and extra < 0.05, f"missed {missed:.3f}, extra {extra:.3f}"


def scalp_closes():
    points, faces, _, _, frame = toy()
    hair_faces = labelled()
    patch = scalp.scalp_patch(points, faces, hair_faces, frame)
    start = scalp.origin(frame)
    directions = trimesh.creation.icosphere(subdivisions=3).vertices
    over_hair = directions[(directions[:, 1] > 0.35) & (directions[:, 2] < 0.5)]
    shell = scalp.first_hit(points, faces[hair_faces], start, over_hair)
    under = scalp.first_hit(patch["points"], patch["triangles"], start, over_hair)
    holes = int((~np.isfinite(under)).sum())
    through = int((under > shell - 0.001).sum())
    skin = trimesh.Trimesh(points, faces[~hair_faces], process=False)
    seam = patch["points"][~patch["hole"]]
    step = float(np.percentile(skin.nearest.on_surface(seam)[1], 95))
    return holes == 0 and through == 0 and step < 0.002, f"holes {holes}, through {through}, step {step * 1000:.2f} mm"


def strands_fill():
    """The strands, at a fortieth of a head's density from 1500 guides (the toy's size, not the route's)."""
    saved = hair.DENSITY, strands.GUIDES, strands.CANDIDATES
    hair.DENSITY = {key: value / 40.0 for key, value in saved[0].items()}
    strands.GUIDES, strands.CANDIDATES = 1500, 40000
    try:
        return strands_measured()
    finally:
        hair.DENSITY, strands.GUIDES, strands.CANDIDATES = saved


def strands_measured():
    points, faces, colours, _, frame = toy()
    hair_faces = labelled()
    patch = scalp.scalp_patch(points, faces, hair_faces, frame)
    body = __main__.body_of(points, faces, hair_faces, patch, None, frame)
    model, model_labels = __main__.model_near_hair(points, faces, hair_faces)
    space = volume.hair_volume(model, model_labels, body, np.random.default_rng(2), scalp.origin(frame))
    style = {"length_m": 0.3, "wave_m": 0.001, "wave_period_m": 0.05, "parting": "none", "fringe_side": "none"}
    skin_like = labels.skin_like(colours)
    hairline = __main__.hairline_of(points, faces, hair_faces, skin_like, frame)
    counts, strand_points, _ = strands.regrown(space, patch, (points, faces[~hair_faces & skin_like]), hairline, frame,
                                               style)
    each = strand_points.reshape(len(counts), -1, 3)
    roots_off = trimesh.Trimesh(patch["points"], patch["triangles"]).nearest.on_surface(each[:, 0])[1]
    into = np.linalg.norm(each - HEAD, axis=2).min(axis=1) < RADIUS - 0.004
    reach = np.linalg.norm(each[:, -1] - each[:, 0], axis=1)
    return (np.percentile(roots_off, 99) < 0.002 and into.mean() < 0.01 and np.median(reach) > 0.02,
            f"roots off {np.percentile(roots_off, 99) * 1000:.2f} mm, into {into.mean():.3f}, "
            f"reach {np.median(reach) * 1000:.1f} mm")


def fibre_follows():
    dark = fibre.fibre_of(np.array([0.1, 0.07, 0.05]), np.array([8.0, 2.0, 3.0]))
    light = fibre.fibre_of(np.array([0.5, 0.4, 0.3]), np.array([45.0, 4.0, 12.0]))
    grey = fibre.fibre_of(np.array([0.65, 0.65, 0.64]), np.array([70.0, 0.5, 1.0]))
    return (dark["melanin"] > light["melanin"] and grey["white_share"] > 0.3 and light["white_share"] == 0.0,
            f"dark {dark['melanin']}, light {light['melanin']}, grey white {grey['white_share']}")


def toy_head(count=4000, seed=0):
    """Points on a squashed sphere (radius about 0.1 m) with three bumps: a nose on its front (-y), an ear and a bun,
    so no turn maps it onto itself."""
    rng = np.random.default_rng(seed)
    way = rng.normal(size=(count, 3))
    way /= np.linalg.norm(way, axis=1, keepdims=True)
    points = way * np.array([0.08, 0.1, 0.12])
    for centre, rise in (([0, -1, 0], 0.03), ([1, 0, 0.3], 0.02), ([-0.5, 0.5, 0.7], 0.025)):
        centre = np.array(centre, float) / np.linalg.norm(centre)
        points += (rise * np.exp(-((way - centre) ** 2).sum(1) / 0.08))[:, None] * way
    return points


def turned(degrees, axis):
    """The rotation of `degrees` about the unit `axis`."""
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    angle = np.radians(degrees)
    cross = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(angle) * cross + (1 - np.cos(angle)) * cross @ cross


TRUTH = (0.3, turned(20, [0.2, 0.1, 1.0]), np.array([0.05, -0.2, 1.5]))


def nearest_among(points):
    """A nearest-index answer over `points` (a KD tree)."""
    tree = cKDTree(points)

    def answer(queries):
        return tree.query(queries)[1]
    return answer


def similarity_found():
    """The exact fit's largest point error (m), and its turn's determinant fitted onto the toy's mirror image (a
    turn, +1, never a reflection)."""
    source = toy_head()
    found = head_swap.similarity(source, head_swap.moved(source, *TRUTH))
    mirrored = head_swap.similarity(source, source * np.array([-1.0, 1.0, 1.0]))
    return (float(np.abs(head_swap.moved(source, *found) - head_swap.moved(source, *TRUTH)).max()),
            round(float(np.linalg.det(mirrored[1])), 6))


def icp_found():
    """The trimmed ICP's largest point error (m) on the clean points, from a start off in scale and turn, a fifth of
    its source points stray."""
    source = toy_head(1500, seed=1)
    target = head_swap.moved(toy_head(6000, seed=2), *TRUTH)
    strays = np.random.default_rng(3).uniform(-0.15, 0.15, size=(300, 3))
    start = (TRUTH[0] * 1.15, TRUTH[1], TRUTH[2] + np.array([0.004, -0.003, 0.005]))
    found = head_swap.trimmed_icp(np.vstack([source, strays]), target, start, nearest_among)
    clean = toy_head(500, seed=4)
    return float(np.abs(head_swap.moved(clean, *found[:3]) - head_swap.moved(clean, *TRUTH)).max())


def scale_scanned():
    """The scale `lowest` reads from misses scanned on a parabola whose least lies at 0.257."""
    scales = np.arange(0.16, 0.38, 0.02)
    return round(head_swap.lowest(scales, (scales - 0.257) ** 2 + 0.003), 6)


def seam_weights():
    """The seam's weight at the cut, halfway and at the band's top."""
    return [round(float(weight), 6) for weight in head_swap.eased([0.0, 0.5, 1.0], 1.0)]


def texel_share():
    """The texels of the lower-left half of a 64-texel square texture, over all its texels."""
    columns, _, weights = head_swap.texels_of([[0, 0], [1, 0], [0, 1]], 64)
    return len(columns) / 64 ** 2, bool((weights.sum(1) > 0.999).all())


def frames_agree():
    """The largest gap between a glTF point moved by the glTF matrix and the same point moved in Blender's frame."""
    matrix = np.eye(4)
    matrix[:3, :3] = TRUTH[0] * TRUTH[1]
    matrix[:3, 3] = TRUTH[2]
    point_gltf = np.array([0.1, 0.2, 0.3, 1.0])
    point_blender = np.array([point_gltf[0], -point_gltf[2], point_gltf[1], 1.0])
    moved_blender = matrix @ point_blender
    moved_gltf = head_swap.gltf_matrix(matrix) @ point_gltf
    return float(np.abs(moved_gltf - np.array([moved_blender[0], moved_blender[2], -moved_blender[1], 1.0])).max())
def skin_flat_grid(colour, size_m=0.1):
    """A flat front grid for the skin's step: `colour(x, y)` painted, every pixel seen and facing forward."""
    xs = (np.arange(int(size_m / skin.STEP_M)) + 0.5) * skin.STEP_M - size_m / 2
    grid_x, grid_y = np.meshgrid(xs, xs)
    ones = np.ones_like(grid_x)
    return {"xs": xs, "ys": xs, "depth": ones * 0.1, "seen": ones > 0, "facing": ones, "normal_x": 0 * ones,
            "normal_y": 0 * ones, "colour": colour(grid_x, grid_y)}


def skin_blobs(x, y):
    """A seeded paint of soft blobs a few millimetres across (the face's detail), sRGB."""
    rng = np.random.default_rng(3)
    total = np.zeros(np.shape(x))
    for centre_x, centre_y, radius in zip(rng.uniform(-0.05, 0.05, 160), rng.uniform(-0.05, 0.05, 160),
                                          rng.uniform(0.002, 0.005, 160)):
        total += np.exp(-0.5 * ((x - centre_x) ** 2 + (y - centre_y) ** 2) / radius ** 2)
    return np.stack([0.75 - 0.2 * np.tanh(total), 0.55 - 0.15 * np.tanh(total), 0.45 - 0.1 * np.tanh(total)], -1)


def skin_registered():
    """The photo found from a start 4 px and 2% off: its true place under half a pixel off over the face."""
    truth = skin.similarity(np.array([[-0.03, 0.0], [0.03, 0.0]]), np.array([[136.0, 210.0], [376.0, 200.0]]))
    rows, cols = np.mgrid[:420, :512]
    inverse = np.linalg.inv(np.vstack([truth, [0, 0, 1]]))
    model_x = inverse[0, 0] * cols + inverse[0, 1] * rows + inverse[0, 2]
    model_y = inverse[1, 0] * cols + inverse[1, 1] * rows + inverse[1, 2]
    photo = skin_blobs(model_x, model_y)
    grid = skin_flat_grid(skin_blobs, 0.08)
    start = truth * np.array([[1.02], [1.02]]) + np.array([[0, 0, 4.0], [0, 0, -3.0]])
    warp, _ = skin.registered(grid, photo, start)
    inner = slice(40, -40)
    found = np.stack(skin.mapped(warp, grid["xs"][inner], grid["ys"][inner]), -1)
    true = np.stack(skin.mapped({**warp, "matrix": truth, "displacement": 0 * warp["displacement"]},
                                grid["xs"][inner], grid["ys"][inner]), -1)
    return bool(np.abs(found - true).max() < 1.0), round(float(np.abs(found - true).max()), 3)


def skin_light_off():
    """The photo's light taken off: a shading that follows the normal flattened, a nose's gloss taken out, plain
    skin kept."""
    grid = skin_flat_grid(lambda x, y: np.ones(x.shape + (3,)) * 0.5)
    tilt = np.sin(grid["xs"] * 20.0)[None, :] * np.ones((len(grid["ys"]), 1))
    grid["normal_x"], grid["facing"] = tilt, np.sqrt(1 - tilt ** 2)
    albedo = np.array([0.5, 0.3, 0.22])
    lit = albedo * (0.9 + 0.1 * tilt)[..., None]
    light, _ = skin.shading(grid, lit, np.ones(tilt.shape))
    flat = eyes.luminance(lit / light[..., None])
    glossy = albedo + 0.12
    cleaned, excess = skin.gloss_free(np.array([glossy, albedo]), np.full(2, eyes.luminance(albedo)),
                                      np.tile(albedo / albedo[0], (2, 1)))
    left = eyes.luminance(cleaned[0]) / eyes.luminance(albedo) - 1.0
    return [bool(flat.std() / flat.mean() < 0.02),
            bool(left < excess[0] / 2.0 and np.allclose(cleaned[0] / cleaned[0, 0], albedo / albedo[0], atol=0.01)),
            bool(np.abs(cleaned[1] - albedo).max() < 0.005)]


def skin_shares():
    """A point wears the photo only facing forward, on the front, inside the photo's face and clear of the eye."""
    grid = skin_flat_grid(lambda x, y: np.ones(x.shape + (3,)) * 0.5)
    grid["facing"][:, :40] = 0.15  # the left side turned away
    mask = np.ones(grid["depth"].shape)
    mask[:40, :] = 0.0  # the bottom outside the photo's face
    turn = np.linspace(0, 2 * np.pi, 200)
    floor = np.column_stack([0.02 + np.outer(np.linspace(0, 0.005, 10), np.cos(turn)).ravel(),
                             np.outer(np.linspace(0, 0.005, 10), np.sin(turn)).ravel(), np.full(2000, 0.1)])
    coarse = {"share": skin.grid_share(grid, mask, skin.eye_floor_distance(grid, floor))}
    points = np.array([[0.0, 0.02, 0.1], [-0.04, 0.02, 0.1], [0.0, -0.04, 0.1], [0.02, 0.0, 0.1], [0.0, 0.02, 0.05]])
    shares = skin.point_shares(grid, coarse, points)
    zone = skin.tzone(np.array([[0.0, 0.0, 0.1], [0.045, 0.01, 0.1]]), np.zeros(3))
    return [bool(shares[0] > 0.95), *(bool(value < 0.05) for value in shares[1:]), bool(zone[0] > 0.9),
            bool(zone[1] < 0.1)]
LID_EYES = np.array([[-0.032, 0.0, 0.0], [0.032, 0.0, 0.0]])
LID_BALL = 0.012


def grid_mesh(xs, ys, depth):
    """A height-field mesh over the grid lines `xs`, `ys` with depth `depth(x, y)`: (points, triangles)."""
    grid_x, grid_y = np.meshgrid(xs, ys)
    points = np.column_stack([grid_x.ravel(), grid_y.ravel(), depth(grid_x, grid_y).ravel()])
    width = len(xs)
    corner = (np.arange(len(ys) - 1)[:, None] * width + np.arange(width - 1)[None, :]).ravel()
    return points, np.vstack([np.column_stack([corner, corner + 1, corner + width + 1]),
                              np.column_stack([corner, corner + width + 1, corner + width])])


def split_closed():
    """Whether half a grid's triangles split in four keep its area, leave no crack (a side inside the square used by
    one triangle only) and carry the UVs along (each new point's UV its place)."""
    points, triangles = grid_mesh(np.linspace(0, 1, 7), np.linspace(0, 1, 7), lambda x, y: 0.0 * x)
    chosen = points[triangles].mean(axis=1)[:, 0] < 0.5
    fine, carried, made = lids.refined(points, points[:, :2], triangles, chosen)
    corners = fine[made]
    area = 0.5 * np.abs(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])[:, 2]).sum()
    sides = np.sort(np.vstack([made[:, [0, 1]], made[:, [1, 2]], made[:, [2, 0]]]), axis=1)
    found, counts = np.unique(sides, axis=0, return_counts=True)
    middle = fine[found].mean(axis=1)
    inside = (middle[:, :2] > 1e-9).all(axis=1) & (middle[:, :2] < 1 - 1e-9).all(axis=1)
    return [bool(abs(area - 1.0) < 1e-9), bool((counts[inside] == 2).all()), bool(np.allclose(carried, fine[:, :2]))]


def lid_marks(half_width, half_height):
    """A photo's marks: two irises (10 px across) 200 px apart, each eye's lids an ellipse round its iris."""
    eyes_marks = []
    for col in (100.0, 300.0):
        turn = np.linspace(0.0, np.pi, 9)
        inner = 1.0 if col < 200 else -1.0  # the inner corner is towards the picture's middle
        upper = np.column_stack([col + inner * half_width * np.cos(turn), 100.0 - half_height * np.sin(turn)])
        lower = np.column_stack([col + inner * half_width * np.cos(turn), 100.0 + half_height * np.sin(turn)])
        eyes_marks.append({"upper": upper.tolist(), "lower": lower.tolist(), "iris_centre": [col, 100.0],
                           "iris_radius": 10.0})
    brows = [{"upper": [[60.0 + 80 * (col > 200) + 80 * k, 40.0] for k in (1, 0)],
              "lower": [[60.0 + 80 * (col > 200) + 80 * k, 60.0] for k in (1, 0)]} for col in (100.0, 300.0)]
    return {"eyes": eyes_marks, "brows": brows}


def photo_opening():
    """The photo's opening read round each eye (mm at 90 degrees, its half height laid by the frame's scale) and held
    inside the ball's silhouette at its corners."""
    laid = lids.photo_frame(lid_marks(30.0, 12.0), LID_EYES, 0.006)
    edges = lids.photo_outline(lid_marks(30.0, 12.0), laid, LID_EYES, LID_BALL)
    tall = [lids.edge_at(edge, 90.0) / (12.0 * laid.scale) for edge in edges]
    wide = [lids.edge_at(edge, 0.0) <= lids.CORNER_SHARE * LID_BALL + 1e-9 for edge in edges]
    return [bool(abs(value - 1.0) < 0.03) for value in tall] + [bool(value) for value in wide]


@functools.lru_cache(maxsize=1)
def lid_scene():
    """Two eyes (spheres) behind a face standing 4 mm in front of them, each opening an ellipse 13 mm tall with a deep
    floor inside; the photo's openings 9 mm tall: (points, triangles, eye views, old outlines, new edges)."""
    def depth(x, y):
        shares = [np.hypot((x - centre[0]) / 0.0115, y / 0.0065) for centre in LID_EYES]
        return np.where(np.min(shares, axis=0) < 1.0, -0.004, LID_BALL + 0.004)

    points, triangles = grid_mesh(np.arange(-0.06, 0.0601, 0.0007), np.arange(-0.027, 0.0271, 0.0007), depth)
    ball = trimesh.creation.icosphere(subdivisions=4, radius=LID_BALL)
    views = []
    for centre in LID_EYES:
        view = lids.front_view(np.asarray(ball.vertices) + centre, np.asarray(ball.faces), lids.eye_box(centre),
                               -np.inf)
        view["ball"] = view
        views.append(view)
    heads = [lids.front_view(points, triangles, lids.eye_box(centre), -1.0) for centre in LID_EYES]
    was = [lids.model_outline(head, view, centre) for head, view, centre in zip(heads, views, LID_EYES)]
    wanted = [1.0 / np.sqrt(np.cos(np.radians(lids.DEGREES)) ** 2 / 0.011 ** 2
                            + np.sin(np.radians(lids.DEGREES)) ** 2 / 0.0045 ** 2)] * 2
    return points, triangles, views, was, wanted


def lids_reshaped():
    """After the reshape: the opening's top and bottom on the photo's (within 0.4 mm), the lid's front just over the
    top and bottom margins LID_M over the eye (within 0.3 mm), and no lid point outside the opening inside the eye."""
    points, triangles, views, was, wanted = lid_scene()
    moved = lids.reshaped(points, np.zeros(len(points), bool), LID_EYES, LID_BALL,
                          [(old[0], old[1], new) for old, new in zip(was, wanted)], views)
    edge_ok, thin_ok, outside_ok = [], [], []
    for centre, view, new in zip(LID_EYES, views, wanted):
        head = lids.front_view(moved, triangles, lids.eye_box(centre), -1.0)
        found, _ = lids.model_outline(head, view, centre)
        edge_ok.append(all(abs(lids.edge_at(found, angle) - lids.edge_at(new, angle)) < 0.0004 for angle in (90, 270)))
        for angle in (90.0, 270.0):
            out = lids.edge_at(new, angle) + 0.001
            x, y = centre[0], out * np.sin(np.radians(angle))
            over = eyes.depth_at(head, [x], [y])[0] - eyes.depth_at(view, [x], [y])[0]
            thin_ok.append(abs(over - lids.LID_M) < 0.0003)
        degrees, reach = lids.polar(moved, centre)
        outside = (reach > lids.edge_at(new, degrees) + 0.0003) & (np.abs(moved[:, 0] - centre[0]) < 0.03)
        surface = eyes.depth_at(view, moved[outside, 0], moved[outside, 1])
        held = np.isfinite(surface)
        outside_ok.append(bool((moved[outside][held, 2] >= surface[held] + lids.GAP_M - 1e-6).all()))
    return [all(edge_ok), all(thin_ok), all(outside_ok)]


def lashes_grown():
    """Upper lashes root just outside the margin and rise to their tips, lower ones fall, all leaving forward."""
    points, triangles = grid_mesh(np.linspace(-0.03, 0.03, 31), np.linspace(-0.03, 0.03, 31),
                                  lambda x, y: 0.0 * x + 0.014)
    centre = np.zeros(3)
    head = lids.front_view(points, triangles, lids.eye_box(centre), -1.0)
    edge = np.full(len(lids.DEGREES), 0.008)
    found = []
    for upper in (True, False):
        made, _ = lids.lid_lashes(head, centre, edge, lids.lid_span(0.0, 180.0, upper), upper, 40,
                                  np.random.default_rng(1))
        out = np.hypot(made[:, 0, 0], made[:, 0, 1]) - 0.008
        rise = (made[:, -1, 1] - made[:, 0, 1]) * (1 if upper else -1)
        found += [bool(((out >= lids.LASH_ROOT_M[0] - 1e-9) & (out <= lids.LASH_ROOT_M[1] + 1e-9)).all()),
                  bool((rise > 0).all()), bool((made[:, -1, 2] > made[:, 0, 2]).all())]
    return found


def brows_follow_photo():
    """A brow whose photo is dark on its outer half only grows its hairs there (90 percent or more), each lying on
    the skin."""
    marks = lid_marks(30.0, 12.0)
    photo = np.full((200, 400, 3), 0.8)
    photo[35:66, 60:100] = 0.3  # the left brow's outer half (its inner end by the picture's middle, at 140 px)
    laid = lids.photo_frame(marks, LID_EYES, 0.006)
    points, triangles = grid_mesh(np.linspace(-0.07, 0.07, 71), np.linspace(-0.01, 0.05, 31),
                                  lambda x, y: 0.0 * x + 0.02)
    head = lids.front_view(points, triangles, lids.brow_box(marks["brows"][0], 0, laid), -1.0)
    hairs, _ = lids.brow_hairs(marks["brows"][0], 0, laid, lids.photo_lightness(photo), head,
                               np.random.default_rng(2))
    outer = laid(np.array([[100.0, 50.0]]), 0)[0, 0]
    share = float((hairs[:, 0, 0] < outer).mean()) if len(hairs) else 0.0
    lying = bool((np.abs(hairs[..., 2] - 0.02) < 0.001).all())
    return [bool(len(hairs) > 20 and share >= 0.9), lying]


def brow_painted_over():
    """The painted brow over an eye painted over with the skin round it (each texel within a tenth of the skin's
    colour), and the skin beside it left as it was."""
    points, triangles = grid_mesh(np.linspace(-0.06, 0.06, 121), np.linspace(-0.03, 0.06, 91),
                                  lambda x, y: 0.0 * x + 0.02)
    uv = np.column_stack([(points[:, 0] + 0.06) / 0.12, (points[:, 1] + 0.03) / 0.09])
    texture = np.ones((180, 240, 3)) * np.array(SKIN)
    rows, cols = np.mgrid[:180, :240]
    place_x, place_y = cols / 239 * 0.12 - 0.06, (179 - rows) / 179 * 0.09 - 0.03
    brow = (np.abs(place_x + 0.032) < 0.018) & (np.abs(place_y - 0.018) < 0.004)
    texture[brow] = (0.25, 0.18, 0.12)
    painted, count = lids.unpainted(points, triangles, uv, texture, LID_EYES)
    covered = np.abs(painted[brow] - np.array(SKIN)).max(axis=1) < 0.1 * np.array(SKIN).max()
    return [bool(count > 0 and covered.mean() > 0.98), bool(np.allclose(painted[~brow & (place_x > 0.0)], SKIN))]


@pytest.mark.parametrize("case, made_value, wanted", [
    ("each painted pupil is found on the face", pupils_found, [True, True]),
    ("the eyeball sits behind its lid margins, its cornea just behind their rim", behind_lids, [True, True]),
    ("the painted floor inside the ball is removed, nothing outside the opening is", floor_removed, [True, True]),
    ("the floor beside the ball is pushed straight back into the socket's shade, the lids stay", floor_pushed_lids_kept,
     [True, True, True, True]),
    ("the wet line runs on the lids' inner rims round both eyes", wet_line_on_rims, [True, True, True]),
    ("both eyes gaze at one point straight ahead", gaze_agrees, True),
    ("a brown iris is read off the photo", lambda: iris_read((0.36, 0.2, 0.12)), True),
    ("a grey-blue iris is read off the photo", lambda: iris_read((0.4, 0.47, 0.52)), True),
    ("a lid margin is read steep or gentle, past a bump on the floor, and never on a curved floor", margins_read,
     [6, 9, 8, None]),
    ("an eye with no lid over or under it is refused", lidless_refused, "refused"),
    ("the hair's labels cover the painted top and nothing else", lambda: bool(labels_hold()[0]), True),
    ("the scalp closes the hair's hole under its shell, flush with the skin", lambda: bool(scalp_closes()[0]), True),
    ("the strands root on the scalp, stay out of the head and reach into the shell",
     lambda: bool(strands_fill()[0]), True),
    ("a darker hair gets more melanin, a grey head white strands", lambda: bool(fibre_follows()[0]), True),
    ("a swapped head's similarity is found exactly, a turn never a mirror",
     lambda: (similarity_found()[0] < 1e-9, similarity_found()[1]), (True, 1.0)),
    ("a swapped head's two-way ICP lands within a millimetre", lambda: icp_found() < 1e-3, True),
    ("the head's scale is read between the scan's steps", scale_scanned, 0.257),
    ("the seam's weight is all body at the cut, none at the band's top", seam_weights, [1.0, 0.5, 0.0]),
    ("a UV triangle's texels are those inside it", lambda: (0.5 <= texel_share()[0] < 0.56, texel_share()[1]),
     (True, True)),
    ("the head-to-body matrix moves a glTF point as Blender's moves it", lambda: frames_agree() < 1e-12, True),
    ("the close-up photo is registered onto the model's front from a start off by pixels and scale",
     lambda: skin_registered()[0], True),
    ("the photo's shading and gloss are taken off, plain skin kept", skin_light_off, [True, True, True]),
    ("a point wears the photo only facing forward, on the front, in the photo's face, clear of the eye; the T-zone "
     "holds the nose", skin_shares, [True] * 7),
    ("the lids' triangles split in four and closed round them with no crack", split_closed, [True, True, True]),
    ("the photo's opening is read round each eye and held inside the ball", photo_opening, [True] * 4),
    ("the lids moved onto the photo's opening, thin over the eye and never inside it", lids_reshaped,
     [True, True, True]),
    ("upper lashes rise from the margin, lower ones fall, all leaving forward", lashes_grown, [True] * 6),
    ("the brow's hairs grow where the photo's brow is dark, lying on the skin", brows_follow_photo, [True, True]),
    ("the painted brow is painted over with the skin round it", brow_painted_over, [True, True]),
])
def test_a_generated_head_gets_real_eyes_and_regrown_hair(case, made_value, wanted):
    assert made_value() == wanted, case
