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
strands into it).

Round 3 of the hair (2026-11-27), each break applied once, seen red, reverted: the grey fit ignoring the spread
(`fibre.grey_fit` given none: white share 0.84 and melanin 0.96 for 0.7 and 0.6 on a made-up swatch table); the photo's
backdrop read by colour alone (`labels.CLOSEUP["smooth"]` unbounded: none of a silver bob as light as the backdrop
held); a hair-white bit the clothes' colours claim never a stray (`labels.over_clothes` saying nothing is over the
clothes: the forehead island 0% hair) or brows taken whatever their paint (`labels.BROWS_DARKER` -inf, round 2's
rule: 0%), or never (+inf: the dark brows 100% hair); the forehead rooted wherever the paint says
(`strands.FOREHEAD["deg"]` 0: roots 3 cm over the eyes).

Round 2 of the hair (2026-11-26): the skin at the hole's edge is laid onto the scalp (`scalp.laid`, over the toy with
its hair's foot raised 3 mm more into a lip, standing up to 11 mm); the layer runs from the scalp's side to the outer
surface of a 2 cm spherical shell (`volume.layered`); the grooves of a corrugated plane and the streaks painted 30
degrees off a plane's u axis are read as its flow (`flow.grooves`, `flow.streaks`); a picture of straight strands
reads straight and of strands waving 5 mm every 4 cm their wave (`curl.curl_of`); the roots fade into the skin over
4 mm, none on the chin, and a beard thins out to its edge under the chin (`strands.hairline_fade`, `grows_here`,
`beard.neck_kept`). Breaks that turn these rows red (each applied once, seen red, reverted): `scalp.laid` returning
the points unchanged (a 7.7 mm lip); the layer turned round (`volume.layered` giving 1 less it); the normals' tensor's
axes read largest first (`flow.tensor_axes`: the groove read across the grooves); the strands' way read across them
(`curl.strand_ways` less a quarter turn: neither picture right); `strands.FADE_M` 2 mm (full at 2 mm);
`strands.LOWEST_UNDER_EYES_M` 1 m (roots on the chin); `beard.NECK_UNDER_NOSE_M` 1 m (the beard's edge kept whole).

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

The whole head's run (`head.py`; 2026-11-26, round 1): a photo's iris (MediaPipe's circle 15% wide, a catchlight on
it) is unrolled onto the eyeball's UV with its pupil at the photo's share, no reflection left in the iris and the
white outside it (`eyes.iris_picture`); a photo with dense lashes gets the full lashes and one with a few fewer
(`lids.lash_share`); the paint's dark baked band is lifted to the skin round it, plain skin and dark hair left
(`skin.paint_shade`); a painted brow wearing the photo is skin (`skin.skin_triangles`). Breaks that turn their rows
red (each applied once, seen red, reverted): MediaPipe's iris circle taken as it is (`eyes.iris_found`: the pupil
read at 0.26); no reflection taken off and no detail clipped (`eyes.IRIS_PICTURE` catchlight 100, detail (0, 10):
the reflection ten times the iris); every photo full of lashes (`lids.LASH_PHOTO` full 0.01); no lift
(`skin.PAINT_SHADE` gain 1); the photo's share ignored (`skin.skin_triangles` with no shares: the brow left).
Round 2 (2026-11-26): a point on a steep side is on the front (`skin.visible`); the paint on the skin is given the
photo skin's mean and spread, the hair left (`skin.paint_toned`); a hidden layer stays behind the face the lid's
move pulls forward (`lids.layers_kept`). Breaks that turn their rows red (each applied once, seen red, reverted):
no slope allowance (`skin.VISIBLE_SLOPE` 0: the steep point is paint); no broad scale (`paint_toned`'s
`broad_scale` 1: the rust patch and shade band keep their spread); the mask ignored (every texel toned: the hair
too); nothing hidden (`lids.LAYERS` hidden_m 1: the hidden layer pulled onto the face).
Round 3 (2026-11-27): a hollow the model's front shuts reads shut and the photo's darker, warmer light in it is
divided out per channel (`skin.occlusion`, `skin.shading`); the photo's fringe (strands with skin between, from the
top edge) and lid openings are left out of its face, its brows and a moustache under the pupils kept
(`skin.face_mask`, `skin.eye_openings`); the model's painted fringe wears no photo, its beard's middle may
(`skin.model_hair_free`); the share rises over EDGE_FEATHER_M from its outer edge (`skin.grid_share`). Breaks that
turn their rows red (each applied once, seen red, reverted): the old clip (`skin.SHADING_RANGE` (0.8, 1.25): the
hollow kept its shade); no occlusion term (`occlusion` all 0); every place hair (`skin.hair_zone` always true: the
moustache left out); no hair taken out (`hair` none: the fringe kept); no lid openings (`EYE_GROW_M` and the polygon
dropped); no feather (`EDGE_FEATHER_M` 1e-9: the edge at full share).

The cloth (`cloth.py`), on toys: a grid painted jacket over jeans with a fleck of T-shirt and stray jeans faces in the
jacket comes out clean after the vote and the islands; a tube's distance over its surface from its top loop is its
height under it, so the jeans ride a waistband's width; a walk whose last frame repeats its first is a cycle a frame
shorter and its travel carries on cycle after cycle; the body under the clothes is pushed in to the margin under a
close shell and not at all under a far one. Breaks that turn its rows red (each applied once, seen red, reverted,
2026-11-26): no islands joined (`cloth.ISLAND_FACES` 0: 2 stray faces); the distance counted in edges, not metres
(`over_surface` lengths all 1); no closed cycle seen (`cloth.CLOSED_DEGREES` 0: 5 frames a cycle); the push read
the wrong way (`margin + over` in `cloth.pushes`).
The sim mesh (`cloth_mesh.py`), on toys: a body column inside a two-walled open garment tube with a sliver and a speck
is laid onto the inner wall as one manifold piece whose only rims are the tube's two ends; a needle left in a grid is
collapsed and two triangles meeting at a point are made two fans; points bound over and under a bent sheet come back
exactly at rest and are carried rigidly when it turns and moves, and a piece of mesh with no riding point rides
whole. Breaks that turn their rows red (each applied once, seen red, reverted, 2026-11-26): the last hit taken for
the first (`laid_over`'s `first`: the outer wall); no collapse rounds (`slivers_collapsed` rounds 0); no extra fan
(`fans_split`'s `extra` empty); the offset added unturned (`carried` without its frame); `anchored` returning
`riding` alone. Round 4 (2026-11-27), each applied once, seen red, reverted: the normals unturned (`skinned_normals`
returning its normals: the cloth shaded as it stood); the drawn surface not moved off its skinned place (`displaced`
returning zeros); the jacket allowed on a leg (`allowed` without `LEGS`: the shards
at the hem). Round 5 (2026-11-27), each applied once, seen red, reverted: a long coat's hem read off every face of a
band (`outer_share` the plain share: the hem stays at its start, 0.9 m); the scarf needing to stand 1 m forward
(`SCARF_FORWARD_M` 1.0: no scarf found); the paint read at the file's places as stored (`file_places` returning its
places: the top's red read as the bottom's blue); the under body's sRGB left unlinearised (`under_colours`: the
jacket's grey 0.5, not 0.214). Cloth round 5 (2026-11-27), each applied once, seen red, reverted: no skirt (`skirted`'s
share 0: the coat's middle on one thigh); the sleeve's faces not given their copies (`sleeves_cut`: sleeve and side
still share points under the shoulder); no cover (`covered` returning no faces); `SHORT_LEAST` 0 (the 1 mm edge kept).

The colour (`colour.py`), on a toy front (a jacket painted dark grey-green with darker fold stripes over trousers
painted black, boots at the bottom painted as black as the trousers with a trace of red) and its photo (a sage
jacket with no stripes, navy trousers, brown boots): after toning, the jacket, trousers and boots each read within a
few Lab units of the photo's, and the jacket's painted folds keep most of their depth. Breaks that turn its rows red
(each applied once, seen red, reverted, 2026-11-26): no height in the clusters (`colour.HEIGHT_LAB` 0: the boots
fall in with the trousers and miss their brown); each cluster its own move (`colour.merged` and `garments` giving every
cluster its own garment: the fold stripes flattened to the photo's plain jacket); no spread kept
(`colour.SPREAD_RANGE` (0, 0): the folds gone). On a toy bust (dark hair on top, a face painted skin in its left
half and dark in its right, the hollow head's back seen through it, over a jacket painted dark grey-green; its photo
dark hair, a light skin face and a sage jacket), the hair and both face halves keep their paint within 2 Lab units and
the jacket still moves to within 6 of the photo's. Break that turns its row red (applied once, seen red, reverted,
2026-11-26): no body kept (`colour.bodily` all False: the face's two halves joined into one garment and moved to the
photo's skin, the dark half cream, as on b_hoodie_man's head). A swapped model (its head and body two primitives, each
on its own picture) is toned through the file: each picture keeps its size and each half's jacket reaches the photo's
sage. Break that turns its row red (applied once, seen red, reverted, 2026-11-26): the model read through trimesh's
`force="mesh"` (the old `model_of`: one 512 x 256 atlas written over the first picture, both jackets off the sage).

The tethered cloth (`cloth_tether.py`), on a curtain swung toward and away from a ball behind it, its top row riding,
feeling g toward the ball: the riding row stays on its targets, every point within its tether, none deeper toward the
ball than its target or the clearance, the loose cloth hangs over a centimetre off its targets and no edge stretches
past 5%; the gravity felt beyond the rest hang is none unturned, g times the square root of two turned a quarter and
twice g turned over; round a box body a point is inside only where all its nearest body points' planes say so. Breaks
that turn their rows red (each applied once, seen red, reverted, 2026-11-27): no retraction (`retracted` returning its
positions: the curtain into the ball past its target); one plane asked (`NEIGHBOURS` 1: 48 outside points pushed); the
whole of g felt (`turned_gravity` returning GRAVITY).
"""
import functools

import numpy as np
import pytest
import trimesh
from scipy.spatial import cKDTree

from tools.characters.generated import (__main__, beard, cloth, cloth_tether, colour, curl, eyes, fibre, flow,
                                        head_swap, labels, lids, scalp, skin, strands, volume)
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
    """Whether the ball, where it rests before EYE_FORWARD_M moves it forward, is behind every lid margin over and
    under the pupil (by at least RIM_GAP_M less a tenth of a millimetre) and its cornea's apex behind the opening's rim
    but within 2 mm of it."""
    result = made()
    centres = np.array(result["stats"]["eye_centres_m"])
    radius = result["stats"]["eye_diameter_mm"] / 2000.0
    gaps, apexes = [], []
    for centre in centres:
        angles = np.radians(np.r_[np.arange(45, 140, 10), np.arange(225, 320, 10)])
        edge = 1.0 / np.sqrt(np.cos(angles) ** 2 / OPENING_M[0] ** 2 + np.sin(angles) ** 2 / OPENING_M[1] ** 2)
        x, y = centre[0] + edge * np.cos(angles), centre[1] + edge * np.sin(angles)
        margin = surface(x, y)
        resting = centre[2] - eyes.EYE_FORWARD_M
        gaps.append(margin - (resting + np.sqrt(radius ** 2 - edge ** 2)))
        apexes.append(margin.mean() - (resting + radius * (1 + eyes.CORNEA_RISE)))
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
    field = flow.flow_field(points, faces, np.zeros((len(points), 2)), np.zeros((4, 4, 3), np.uint8), hair_faces,
                            space)
    counts, strand_points, _ = strands.regrown(space, field, patch, (points, faces[~hair_faces & skin_like]),
                                               hairline, frame, style)
    each = strand_points.reshape(len(counts), -1, 3)
    roots_off = trimesh.Trimesh(patch["points"], patch["triangles"]).nearest.on_surface(each[:, 0])[1]
    into = np.linalg.norm(each - HEAD, axis=2).min(axis=1) < RADIUS - 0.004
    reach = np.linalg.norm(each[:, -1] - each[:, 0], axis=1)
    return (np.percentile(roots_off, 99) < 0.002 and into.mean() < 0.01 and np.median(reach) > 0.02,
            f"roots off {np.percentile(roots_off, 99) * 1000:.2f} mm, into {into.mean():.3f}, "
            f"reach {np.median(reach) * 1000:.1f} mm")


def shell_layers():
    """The layer read across a 2 cm thick spherical shell of hair round a head's middle: at its inner 2 mm and at its
    outer 2 mm (0 is the scalp's side, 1 the outer surface)."""
    low = np.full(3, -0.12)
    shape = (121, 121, 121)
    middles = low + np.argwhere(np.ones(shape, dtype=bool)) * volume.VOXEL_M
    distance = np.linalg.norm(middles, axis=1).reshape(shape)
    filled = (distance > 0.09) & (distance < 0.11)
    layer, _ = volume.layered(filled, low, np.zeros(3))
    return (float(layer[filled & (distance < 0.092)].mean()) < 0.2, float(layer[filled & (distance > 0.108)].mean())
            > 0.8)


def skin_laid():
    """The model's skin at the hole's edge after `scalp.laid`: its largest distance off the scalp (m), over the toy
    with its hair's foot standing 3 mm more as a lip round the hole (the toy's edge already stands up to 8 mm)."""
    points, faces, _, _, frame = toy()
    hair_faces = labelled()
    patch = scalp.scalp_patch(points, faces, hair_faces, frame)
    start = scalp.origin(frame)
    edge = np.unique(faces[hair_faces])
    lip = np.unique(faces[~hair_faces])
    lip = lip[np.isin(lip, edge)]
    lifted = points.copy()
    lifted[lip] += scalp_way(lifted[lip], start) * 0.003
    laid = scalp.laid(lifted, faces, hair_faces, patch, frame)
    return float(trimesh.Trimesh(patch["points"], patch["triangles"]).nearest.on_surface(laid[lip])[1].max())


def scalp_way(places, start):
    """Unit ways from `start` to the places."""
    away = places - start
    return away / np.linalg.norm(away, axis=1, keepdims=True)


def groove_and_streak():
    """The cosines of the read groove way and paint streak way with the true ones, on a corrugated plane (grooves
    along y, 3 mm apart) and on a flat plane painted with streaks running 30 degrees off its u axis."""
    xs, ys = np.meshgrid(np.linspace(0.0, 0.03, 61), np.linspace(0.0, 0.03, 61))
    flat = np.column_stack([xs.ravel(), ys.ravel(), np.zeros(xs.size)])
    corner = (np.arange(60)[:, None] * 61 + np.arange(60)[None, :]).ravel()
    faces = np.vstack([np.column_stack([corner, corner + 1, corner + 62]),
                       np.column_stack([corner, corner + 62, corner + 61])])
    wavy = flat + np.column_stack([np.zeros((xs.size, 2)), 0.0005 * np.sin(2.0 * np.pi * xs.ravel() / 0.003)])
    middle = np.abs(flat[faces].mean(axis=1)[:, :2] - 0.015).max(axis=1) < 0.01
    groove, _ = flow.grooves(wavy, faces, middle)
    rows, columns = np.mgrid[:512, :512]
    along = np.radians(30.0)
    texture = (127 + 100 * np.sin(2.0 * np.pi * (-columns * np.sin(along) - rows * np.cos(along)) / 8.0))
    texture = np.repeat(texture[..., None], 3, axis=2).astype(np.uint8)
    uv = flat[:, :2] / 0.03
    streak, _ = flow.streaks(flat, faces, uv, texture, middle)
    truth = np.array([np.cos(along), np.sin(along), 0.0])
    return (round(float(np.median(np.abs(groove[:, 1]))), 2) > 0.95,
            round(float(np.median(np.abs(streak @ truth))), 2) > 0.95)


def photo_waves():
    """The curl read off pictures of strands 1.2 mm apart: straight ones and ones waving 5 mm every 4 cm."""
    metre = 0.0004
    rows, columns = np.mgrid[:curl.SIZE, :curl.SIZE] * metre
    found = []
    for amplitude in (0.0, 0.005):
        phase = (columns - amplitude * np.sin(2.0 * np.pi * rows / 0.04)) / 0.0012
        lab = np.stack([50.0 + 20.0 * np.sin(2.0 * np.pi * phase), np.zeros_like(phase), np.zeros_like(phase)], -1)
        angle, _, _ = curl.strand_ways(lab, metre)
        usable = np.zeros(angle.shape, dtype=bool)
        usable[50:-50, 50:-50] = True
        found.append(curl.curl_of(curl.lines_of(angle, usable, metre)))
    straight, waving = found
    return (straight["wave_m"] == 0.0 and straight["curly"] == 0.0,
            0.0035 < waving["wave_m"] < 0.0065 and 0.03 < waving["period_m"] < 0.05 and waving["curly"] > 0.5)


def roots_and_beard_fade():
    """The roots' density share at the paint's hairline, 2 and 4 mm over it; whether the chin in front grows
    scalp hair; the share of beard roots kept at the beard's edge under the chin and NECK_FADE_M in."""
    fade = strands.hairline_fade(np.array([0.0, 0.002, 0.004]))
    frame = {"centre": np.zeros(3), "eyes": np.array([[-0.03, 0.0, 0.08], [0.03, 0.0, 0.08]]),
             "eyes_middle": np.array([0.0, 0.0, 0.08]), "nose": np.array([0.0, -0.035, 0.1])}
    chin = strands.grows_here(np.array([[0.0, -0.1, 0.06]]), frame)[0]
    smooth = np.array([[0.0, -0.14, 0.05], [0.0, -0.14 + beard.NECK_FADE_M, 0.05], [1.0, 1.0, 1.0]])
    places = np.repeat(smooth[:2], 2000, axis=0)
    faces = np.array([[0, 0, 2], [0, 1, 1]])
    kept = beard.neck_kept(places, smooth, faces, np.array([False, True]), frame, np.random.default_rng(3))
    return (round(float(fade[0]), 2) == hair.BABY_DENSITY[1] and 0.6 < fade[1] < 0.8 and fade[2] == 1.0,
            chin == 0.0, kept[:2000].mean() < 0.05 and kept[2000:].mean() > 0.95)


def swatch_rows():
    """A strand swatch table as `fibre.swatch_table` writes one, from a made-up smooth law: a pure head's lightness
    falling with its melanin (lighter for more redness), a grey head's the white strands' and the pigmented ones'
    mixed, its spread rising as they differ."""
    rows, whitest = [], 80.0 * (1.0 - fibre.SWATCH["melanin"][0]) ** 0.7 + 6.0
    for case in fibre.swatch_cases():
        pigmented = 80.0 * (1.0 - case["melanin"]) ** 0.7 + 6.0 + 4.0 * case["redness"]
        white = case["white_share"]
        lightness = white * whitest + (1.0 - white) * pigmented
        spread = 4.0 + 0.4 * white * (1.0 - white) * (whitest - pigmented)
        rows.append({**{key: case[key] for key in ("melanin", "redness", "white_share")},
                     "lab": [lightness, 2.0, 3.0], "spread": spread})
    return rows


def fibre_fitted():
    """A darker head gets more melanin, a redder hue more redness, and a grey head the white share and melanin whose
    swatch shows its lightness and spread (0.7 and 0.6 here)."""
    rows = swatch_rows()
    dark = fibre.fibre_of(np.array([0.1, 0.07, 0.05]), np.array([12.0, 2.0, 3.0]), 6.0, rows)
    light = fibre.fibre_of(np.array([0.5, 0.4, 0.3]), np.array([45.0, 4.0, 12.0]), 6.0, rows)
    pigmented, whitest = 80.0 * 0.4 ** 0.7 + 6.0, 80.0 * (1.0 - fibre.SWATCH["melanin"][0]) ** 0.7 + 6.0
    grey = fibre.fibre_of(np.array([0.65, 0.65, 0.64]), np.array([0.7 * whitest + 0.3 * pigmented, 2.0, 3.0]),
                          4.0 + 0.4 * 0.7 * 0.3 * (whitest - pigmented), rows)
    return (dark["melanin"] > light["melanin"] and light["redness"] > dark["redness"] - 1e-9
            and light["white_share"] == 0.0 and abs(grey["white_share"] - 0.7) < 0.03
            and abs(grey["melanin"] - 0.6) < 0.03,
            f"dark {dark['melanin']}, light {light['melanin']}, grey white {grey['white_share']} m {grey['melanin']}")


def silver_photo():
    """A 512-pixel close-up on a plain light grey backdrop (L 81): a silver bob as light as the backdrop (L 78, its
    strands' lightness spread 5), a skin face with two dark pupils under it: (sRGB picture, the hair's truth)."""
    size = 512
    rows, columns = np.mgrid[:size, :size]
    lab = np.zeros((size, size, 3))
    lab[...] = (81.0, 0.8, 1.9)
    head = ((columns - 256) / 150.0) ** 2 + ((rows - 230) / 190.0) ** 2 < 1.0
    hair = head & (rows < 330)
    strands = np.random.default_rng(5).normal(0.0, 5.0, size)[columns]
    lab[hair] = np.stack([78.0 + strands, np.full(size, 3.0)[columns], np.full(size, 4.0)[columns]], -1)[hair]
    face = ((columns - 256) / 95.0) ** 2 + ((rows - 250) / 130.0) ** 2 < 1.0
    face &= rows > 120
    lab[face] = (70.0, 15.0, 22.0)
    for column in (215, 297):
        lab[np.hypot(columns - column, rows - 200) < 5] = (10.0, 0.0, 0.0)
    from skimage.color import lab2rgb
    return np.clip(lab2rgb(lab), 0.0, 1.0), hair & ~face & (rows < 200 + labels.CLOSEUP["chin"] * 82)


def silver_hair_read():
    """The share of a silver bob's pixels the photo's hair holds, and the share of what it holds that is not hair."""
    picture, truth = silver_photo()
    found = labels.photo_hair(picture)
    return round(float((found & truth).sum() / truth.sum()), 2), round(float((found & ~truth).sum() / found.sum()), 2)


def white_bits_kept_as_hair():
    """The share of a white island on the toy's forehead labelled hair, the toy's hair silver and its coat a scarf's
    cream (the island nearer the cream, as an older woman's fringe bits were), and of brows painted in the dark toy
    hair's own colour there."""
    points, faces, colours, truth, frame = toy()
    middles = points[faces].mean(axis=1)
    over = middles[:, 1] - frame["eyes_middle"][1]
    forehead = (over > labels.FACE_BOX["over_eyes_m"]) & (over < 0.03) & (middles[:, 2] > 0.0) & ~truth
    forehead &= cKDTree(middles[truth]).query(middles, workers=-1)[0] < labels.STRAY_M / 2.0
    silver = colours.copy()
    silver[truth] = (82.0, 1.0, 2.0)
    silver[len(trimesh.creation.icosphere(subdivisions=4).faces):] = (90.0, 3.0, 9.0)
    silver[forehead] = (89.0, 3.0, 8.0)
    browed = colours.copy()
    browed[forehead] = COLOURS["hair"]
    found = [labels.hair_labels(points, faces, painted, frame, False, 0.3)[0][forehead] for painted in (silver, browed)]
    return int(forehead.sum() > 5), round(float(found[0].mean()), 2), round(float(found[1].mean()), 2)


def forehead_roots():
    """Whether hair roots 3 cm over the eyes in front of the forehead, beside it 40 degrees round, and 6 cm over
    them in front."""
    frame = {"centre": np.zeros(3), "eyes": np.array([[-0.03, 0.0, 0.08], [0.03, 0.0, 0.08]]),
             "eyes_middle": np.array([0.0, 0.0, 0.08])}
    turned = np.radians(40.0)
    places = np.array([[0.0, 0.03, 0.09], [0.09 * np.sin(turned), 0.03, 0.09 * np.cos(turned)], [0.0, 0.06, 0.08]])
    return tuple(strands.grows_here(places, frame).tolist())


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
    flat = eyes.luminance(lit / light)
    glossy = albedo + 0.12
    cleaned, excess = skin.gloss_free(np.array([glossy, albedo]), np.full(2, eyes.luminance(albedo)),
                                      np.tile(albedo / albedo[0], (2, 1)))
    left = eyes.luminance(cleaned[0]) / eyes.luminance(albedo) - 1.0
    return [bool(flat.std() / flat.mean() < 0.02),
            bool(left < excess[0] / 2.0 and np.allclose(cleaned[0] / cleaned[0, 0], albedo / albedo[0], atol=0.01)),
            bool(np.abs(cleaned[1] - albedo).max() < 0.005)]


def skin_hollow_light_off():
    """A hollow the model's own front shuts reads shut, and the photo's darker, warmer light in it is divided out to
    the skin's colour round it (the render makes the hollow's shade again)."""
    grid = skin_flat_grid(lambda x, y: np.ones(x.shape + (3,)) * 0.5)
    rows, cols = np.indices(grid["depth"].shape)
    pit = np.hypot(rows - 100, cols - 100) < 30
    grid["depth"] = np.where(pit, 0.1 - 0.015, 0.1)
    shut = skin.occlusion(grid)
    albedo = np.array([0.5, 0.3, 0.22])
    lit = albedo * (1.0 - shut[..., None] * np.array([0.6, 0.8, 0.9]))
    light, _ = skin.shading(grid, lit, np.ones(shut.shape))
    flat = lit / light
    inner = np.hypot(rows - 100, cols - 100) < 10
    return [bool(shut[inner].mean() > shut[~pit].mean() + 0.3),
            bool(np.abs(flat[inner].mean(axis=0) / flat[~pit].mean(axis=0) - 1.0).max() < 0.08)]


def skin_photo_kept_off():
    """The photo's face leaves out its fringe (strands with skin between, from the top edge) and its lid openings but
    keeps its brows and a moustache under the pupils; the model's painted fringe wears no photo, its beard's middle
    may; the share rises over EDGE_FEATHER_M from its outer edge."""
    rows, cols = np.indices((200, 200))
    photo = np.ones((200, 200, 3)) * [0.85, 0.65, 0.55]
    strands = (rows < 70) & ((rows < 40) | (cols % 10 < 6))
    photo[strands] = 0.7
    photo[(np.abs(rows - 80) < 3) & (np.abs(cols - 60) < 20)] = [0.2, 0.15, 0.1]
    photo[(np.abs(rows - 150) < 5) & (np.abs(cols - 100) < 30)] = [0.2, 0.15, 0.1]  # a moustache, by a hair's
    photo[(rows > 150) & (np.abs(cols - 100) < 4)] = [0.2, 0.15, 0.1]  # line to the picture's edge
    pupils = np.array([[60.0, 100.0], [140.0, 100.0]])
    face = skin.face_mask(photo, 2000.0, pupils)
    marks = {"eyes": [{"upper": [[50, 100], [60, 95], [70, 100]], "lower": [[50, 100], [60, 105], [70, 100]]}]}
    opening = skin.eye_openings(face.shape, marks, 2000.0)
    grid = skin_flat_grid(lambda x, y: np.ones(x.shape + (3,)) * [0.85, 0.65, 0.55])
    grid["colour"][(grid["ys"] > 0.03)[:, None] & np.ones((1, len(grid["xs"])), bool)] = 0.7
    grid["colour"][(grid["ys"] < -0.03)[:, None] & (np.abs(grid["xs"]) < 0.02)[None, :]] = [0.2, 0.15, 0.1]
    free = skin.model_hair_free(grid, np.array([[-0.03, 0.0], [0.03, 0.0]]))
    flat = np.zeros(grid["depth"].shape)
    flat[20:180, 20:180] = 1.0
    share = skin.grid_share(grid, flat, np.full(flat.shape, np.inf))
    return [bool(face[55, 103] < 0.2), bool(face[80, 60] > 0.8), bool(face[150, 100] > 0.8),
            bool(opening[100, 60] and not opening[120, 60]),
            bool(free[190, 100] == 0 and free[100, 100] == 1 and free[20, 100] == 1),
            bool(share[100, 22] < 0.3 and share[100, 40] > 0.95)]


def skin_shares():
    """A point wears the photo only facing forward, on the front, inside the photo's face and clear of the eye."""
    grid = skin_flat_grid(lambda x, y: np.ones(x.shape + (3,)) * 0.5)
    grid["facing"][:, :40] = 0.05  # the left side turned away
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
def iris_unrolled():
    """A photo's iris (radius 30 px, its pupil 9 px, a catchlight on its pupil's edge, MediaPipe's circle 15% wide):
    its pupil read at its share, the catchlight gone from the iris picture, the white outside it."""
    picture = np.ones((300, 400, 3)) * (0.85, 0.82, 0.8)
    rows, cols = np.mgrid[:300, :400]
    marks = lid_marks(60.0, 40.0)
    for eye in marks["eyes"]:
        col, row = eye["iris_centre"][0], 150.0
        eye["iris_centre"], eye["iris_radius"] = [col + 2.0, row - 1.0], 30.0 / eyes.IRIS_PICTURE["radius"]
        eye["upper"] = (np.asarray(eye["upper"]) + [0.0, 50.0]).tolist()
        eye["lower"] = (np.asarray(eye["lower"]) + [0.0, 50.0]).tolist()
        out = np.hypot(cols - col, rows - row)
        picture[out < 30.0] = (0.3, 0.18, 0.1) * (1.0 + 0.15 * np.sin(np.arctan2(rows - row, cols - col) * 12))[
            out < 30.0, None]
        picture[out < 9.0] = 0.02
        picture[np.hypot(cols - col - 13, rows - row + 12) < 4.0] = 1.0
    sclera = (0.68, 0.58, 0.5)
    texture, stats = eyes.iris_picture(picture, marks, sclera, 0.125)
    size = len(texture)
    across = (np.arange(size) + 0.5) / size - 0.5
    out = np.hypot(*np.meshgrid(across, across)) / 0.125
    ring = (out > 0.4) & (out < 0.8)
    light = eyes.luminance(texture)
    return [bool(abs(stats["pupil_share"] - 0.3) < 0.025), bool(light[ring].max() < 1.5 * np.median(light[ring])),
            bool(np.allclose(texture[out > 1.1], sclera))]


def lashes_by_photo():
    """A photo with dense dark lashes over its upper lids gets the full lashes; one with a few gets fewer, never under
    the least."""
    shares = []
    for every in (2, 9):
        picture = np.ones((200, 400, 3)) * 0.75
        marks = lid_marks(30.0, 12.0)
        for eye in marks["eyes"]:
            for col, row in np.asarray(eye["upper"])[2:-2]:
                for step in range(-12, 13, every):
                    picture[int(row) - 14:int(row) - 1, int(col) + step] = 0.1
        shares.append(lids.lash_share(picture, marks))
    return [shares[0] == 1.0, lids.LASH_PHOTO["least"] <= shares[1] < 0.8]


def paint_lifted():
    """The paint's dark baked band (a socket's shade) lifted to the skin round it, plain skin left, a dark-haired
    piece (not skin's colour) left alone."""
    def paint(x, y):
        colour = np.ones(x.shape + (3,)) * np.array([0.8, 0.62, 0.52])
        colour[np.abs(y) < 0.003] *= 0.75
        colour[x > 0.03] = (0.1, 0.08, 0.07)
        return colour
    grid = skin_flat_grid(paint, 0.1)
    gain, dark = skin.paint_shade(grid)
    middle = len(grid["ys"]) // 2
    lifted = skin.linear(grid["colour"][middle, 50]) * gain[middle, 50]
    plain = skin.linear(grid["colour"][middle + 40, 50])
    return [bool(np.abs(lifted / plain - 1.0).max() < 0.15), bool(np.allclose(gain[middle + 40, 50], 1.0)),
            bool(dark[middle, 190] == 0.0)]


def steep_point_seen():
    """A point on a steep side (facing 0.3, its depth read 2 mm off by the front's pixels) is on the front; one 5 mm
    behind it is not."""
    grid = skin_flat_grid(lambda x, y: np.ones(x.shape + (3,)) * 0.5)
    grid["facing"][:] = 0.3
    points = np.array([[0.0, 0.0, 0.102], [0.0, 0.0, 0.095]])
    return skin.visible(grid, points).tolist()


def paint_toned():
    """The model's warm, dark skin paint (its broad tone a shade band and a rust patch) given the photo skin's colour
    statistics: its mean within a Lab unit of the photo's, its broad spread no wider than the photo's, its hair (not
    skin) untouched."""
    rows, cols = np.mgrid[:200, :200]
    texture = np.ones((200, 200, 3)) * np.array([0.55, 0.33, 0.22])
    texture[60:80] *= 0.6  # a baked shade band
    texture[120:160, 20:80] = (0.62, 0.3, 0.12)  # a rust patch
    texture[:, 180:] = (0.1, 0.08, 0.07)  # hair
    mask = cols < 170
    photo = np.ones((150, 150, 3)) * np.array([0.82, 0.62, 0.54])
    photo *= (1.0 + 0.03 * np.sin(np.arange(150) / 7.0))[:, None, None]
    photo_lab = skin.rgb2lab(photo)
    held = np.ones((150, 150), bool)
    toned, _ = skin.paint_toned(texture, mask, 2000.0, photo_lab, held)
    lab = skin.rgb2lab(toned)
    inner = (cols < 160) & (cols > 10)
    broad = skin.smoothed_over(lab, inner.astype(float), skin.PAINT_TONE["broad_m"] * 2000.0)
    photo_broad = skin.smoothed_over(photo_lab, held.astype(float), skin.PAINT_TONE["broad_m"] / skin.STEP_M)
    return [bool(np.abs(lab[inner].mean(axis=0) - photo_lab.mean(axis=(0, 1))).max() < 1.5),
            bool((broad[inner].std(axis=0) <= photo_broad.std(axis=(0, 1)) + 0.5).all()),
            bool(np.array_equal(toned[:, 180:], texture[:, 180:]))]


def layers_kept():
    """A hidden layer 3 mm behind the face, both pulled 5 mm forward onto one depth by the lid's move: the hidden layer
    stays at least LAYERS' `hidden_m` behind the face, the face moves as it was moved, a layer not free is left."""
    grid_x, grid_y = np.meshgrid(np.linspace(-0.005, 0.005, 21), np.linspace(-0.005, 0.005, 21))
    face = np.column_stack([grid_x.ravel(), grid_y.ravel(), np.zeros(grid_x.size)])
    hidden = face - [0.0, 0.0, 0.003]
    was = np.vstack([face, hidden])
    moved = was.copy()
    moved[:, 2] = 0.005
    free = np.ones(len(was), bool)
    kept = lids.layers_kept(was, moved, free)
    free[len(face):] = False
    left = lids.layers_kept(was, moved, free)
    count = len(face)
    return [bool((kept[:count] - kept[count:]).min() >= lids.LAYERS["hidden_m"] - 1e-9),
            bool(np.allclose(kept[:count], 0.005)), bool(np.allclose(left[count:], 0.005))]


def skin_wears_photo():
    """A dark painted patch (a painted brow) on skin is skin where it wears the photo and stays the model's own where
    it does not (all but its edge, which its neighbours settle)."""
    points, triangles = grid_mesh(np.linspace(0, 0.12, 61), np.linspace(0, 0.04, 21), lambda x, y: 0.0 * x)
    middles = points[triangles].mean(axis=1)
    brow = (np.abs(middles[:, 1] - 0.02) < 0.008) & ((np.abs(middles[:, 0] - 0.03) < 0.02)
                                                     | (np.abs(middles[:, 0] - 0.09) < 0.02))
    likeness = (~brow).astype(np.float64)
    shares = (points[:, 0] < 0.06).astype(np.float64)
    found = skin.skin_triangles(points, triangles, likeness, shares)
    left = brow & (middles[:, 0] < 0.06)
    right = brow & (middles[:, 0] > 0.06)
    return [bool(found[left].all()), bool(found[right].mean() < 0.2)]


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


def cloth_grid(rows=30, columns=30):
    """A flat grid (x right, y up, 1 cm apart) as triangles: (points, faces)."""
    x, y = np.meshgrid(np.arange(columns) * 0.01, np.arange(rows) * 0.01)
    points = np.stack([x.ravel(), y.ravel(), np.zeros(x.size)], 1)
    corner = (np.arange(rows - 1)[:, None] * columns + np.arange(columns - 1)[None]).ravel()
    faces = np.concatenate([np.stack([corner, corner + 1, corner + columns], 1),
                            np.stack([corner + 1, corner + columns + 1, corner + columns], 1)])
    return points, faces


def cloth_kinds_settled():
    """A grid painted jacket over jeans with a fleck of shirt in the jacket and a few jeans faces in it: after the
    vote and the islands, how many faces are of the wrong kind (0)."""
    points, faces = cloth_grid()
    middles = points[faces].mean(1)
    wanted = np.where(middles[:, 1] > 0.15, cloth.KINDS.index("jacket"), cloth.KINDS.index("jeans"))
    found = wanted.copy()
    found[np.flatnonzero(middles[:, 1] > 0.2)[[5, 40, 41, 300]]] = cloth.KINDS.index("shirt")
    found[np.flatnonzero(middles[:, 1] > 0.2)[[100, 230]]] = cloth.KINDS.index("jeans")
    free = np.ones(len(faces), bool)
    return int((cloth.islands_joined(faces, cloth.settled(faces, found, free), free) != wanted).sum())


def cloth_waistband():
    """A tube (radius 15 cm, 40 cm long) whose top loop is the jeans' top: each point's distance over its surface from
    that loop against its height under it (within 2 mm), and which ride (the band's width under the top)."""
    turns, rows = 60, 41
    angle, height = np.meshgrid(np.arange(turns) * 2 * np.pi / turns, np.arange(rows) * 0.01)
    points = np.stack([0.15 * np.cos(angle.ravel()), height.ravel(), 0.15 * np.sin(angle.ravel())], 1)
    corner = (np.arange(rows - 1)[:, None] * turns + np.arange(turns)[None]).ravel()
    right = (corner // turns) * turns + (corner + 1) % turns
    faces = np.concatenate([np.stack([corner, right, corner + turns], 1),
                            np.stack([right, right + turns, corner + turns], 1)])
    top = np.flatnonzero(points[:, 1] > 0.395)
    distance = cloth.over_surface(points, faces, top)
    under = 0.40 - points[:, 1]
    riding = distance < cloth.WAISTBAND_M
    return [bool(np.abs(distance - under).max() < 0.002), bool(np.all(riding == (under < cloth.WAISTBAND_M - 1e-9)))]


def cloth_walk_tiled():
    """A two-joint walk of 5 frames whose last repeats its first 0.3 m on: its cycle (4 frames, 0.3 m), and the
    tiled walk's tenth frame (the third cycle's second frame) 0.6 m on from the clip's second."""
    worlds = np.tile(np.eye(4), (5, 2, 1, 1))
    for frame in range(5):
        worlds[frame, :, 2, 3] = 0.075 * frame
        turn = np.radians(20.0 * np.sin(frame / 4 * 2 * np.pi))
        worlds[frame, 1, :3, :3] = [[np.cos(turn), -np.sin(turn), 0], [np.sin(turn), np.cos(turn), 0], [0, 0, 1]]
    length, travel = cloth.cycle_of(worlds)
    played, inside, cycle, _ = cloth.tiled(worlds, 12)
    moved = played[9, 0, 2, 3] - worlds[1, 0, 2, 3]
    return [length, round(float(travel[2]), 6), int(inside[9]), round(float(moved), 6)]


def cloth_body_pushed():
    """A body ball (radius 1) under a shell ball: pushed in to the margin under a shell 5 mm over it, never moved
    under a shell 10 cm over it, never outward."""
    ball = trimesh.creation.icosphere(subdivisions=3)
    found = []
    for shell_radius in (1.005, 1.1):
        moves = cloth.pushes(ball.vertices, ball.faces, ball.vertex_normals, ball.vertices * shell_radius,
                             ball.faces, cloth.MARGIN_M)
        inward = -np.einsum("pd,pd->p", moves, ball.vertex_normals)
        found.append(round(float(inward.mean()), 3))
    return found


def cloth_tube_laid():
    """A body column (radius 10 cm, 60 cm tall, closed) inside a two-walled garment tube (walls at 12.6 and 13 cm,
    40 cm tall, open at both ends) with a sliver and a speck off it: the sim mesh laid over the body and cleaned is one
    piece with two rims (the tube's ends), no edge on three faces, at the inner wall's radius."""
    turn = trimesh.transformations.rotation_matrix(np.pi / 2, (1, 0, 0))
    body = trimesh.creation.cylinder(radius=0.1, height=0.6, sections=48, transform=turn)
    walls = []
    for radius in (0.126, 0.13):
        wall = trimesh.creation.cylinder(radius=radius, height=0.4, sections=64, transform=turn)
        wall.update_faces(np.abs(wall.face_normals[:, 1]) < 0.5)  # the caps off: an open tube
        wall.remove_unreferenced_vertices()
        walls.append(wall)
    sliver = trimesh.Trimesh([[0.2, 0.0, 0.0], [0.2, 0.01, 0.0], [0.2, 0.02, 1e-12]], [[0, 1, 2]])
    speck = trimesh.Trimesh([[0.5, 0.0, 0.0], [0.5, 0.01, 0.0], [0.5, 0.0, 0.01]], [[0, 1, 2]])
    shell = trimesh.util.concatenate(walls + [sliver, speck])
    garment = np.arange(len(shell.faces))
    points, faces = cloth.cloth_mesh.laid_over((body.vertices, body.faces), np.zeros(len(body.vertices), int),
                                               (shell.vertices, shell.faces), garment, np.zeros(len(garment), int),
                                               (["Hips"], [-1]), edge=0.02)
    points, faces = cloth.cloth_mesh.cleaned(points, faces)
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    shared = np.unique(edges, axis=0, return_counts=True)[1].max()
    radius = np.hypot(points[:, 0], points[:, 2])
    return [len(cloth.cloth_mesh.rims(faces)), len(np.unique(cloth.cloth_mesh.pieces_of(faces, len(points)))),
            int(shared), bool(np.abs(radius - 0.126).max() < 0.002)]


def cloth_mesh_mended():
    """A needle triangle in a grid collapsed (no corner under ANGLE_LEAST, the grid's other faces kept), and two
    triangles meeting at one point only made two fans (that point given twice)."""
    points, faces = cloth_grid(6, 6)
    points = np.vstack([points, [[0.0195, 0.0101, 0.0]]])  # half a millimetre off point 8: a needle to 13
    needle = int(np.flatnonzero((faces == 7).any(1) & (faces == 8).any(1) & (faces == 13).any(1))[0])
    faces = np.vstack([np.delete(faces, needle, axis=0), [[7, 36, 13], [36, 8, 13]]])
    mended_points, mended_faces = cloth.cloth_mesh.slivers_collapsed(points, faces)
    bow = cloth.cloth_mesh.fans_split(np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [-1, 0, 0], [0, -1, 0.0]]),
                                      np.array([[0, 1, 2], [0, 3, 4]]))
    return [bool(cloth.cloth_mesh.corner_angles(mended_points, mended_faces).min() >= cloth.cloth_mesh.ANGLE_LEAST),
            len(mended_faces) >= len(faces) - 3, len(bow[0]), sorted(bow[1].ravel().tolist())]


def cloth_drawn_rides():
    """Points over and under a bent sheet bound to it move by none of the sheet's own move off its targets at rest and
    by all of a move the whole sheet makes off them; normals turn with their skinned turn (a zero one stays zero); a
    piece of the mesh with no riding point rides whole, one with a riding point keeps its loose."""
    points, faces = cloth_grid(8, 8)
    points[:, 2] = 0.3 * points[:, 0] ** 2
    render = np.random.default_rng(4).uniform([0.005, 0.005, -0.01], [0.065, 0.065, 0.01], (200, 3))
    binding = cloth.cloth_mesh.bound(render, points, faces)
    targets = np.stack([points, points + (0.0, 0.1, 0.0)])
    positions = np.stack([points, points + (0.0, 0.1, 0.03)])
    off = cloth.cloth_mesh.displaced(binding, positions, targets, faces)
    turn = trimesh.transformations.rotation_matrix(0.7, (0.3, 1.0, 0.2))
    moves = np.stack([np.eye(4), turn])[:, None]
    normals = np.array([[0.0, 0.0, 1.0], [0.0, 0.0, 0.0]])
    shaded = cloth.skinned_normals(normals, np.ones((2, 1)), moves)
    two = np.vstack([faces, faces + len(points)])
    riding = np.zeros(2 * len(points), bool)
    riding[0] = True
    anchored = cloth.anchored(two, riding)
    return [bool(np.abs(off[0]).max() < 1e-12), bool(np.abs(off[1] - (0.0, 0.0, 0.03)).max() < 1e-12),
            int(anchored[:len(points)].sum()), bool(anchored[len(points):].all()),
            bool(np.abs(shaded[1, 0] - turn[:3, 2]).max() < 1e-9), bool(np.abs(shaded[:, 1]).max() == 0.0)]

def cloth_jacket_off_legs():
    """[a face at the hips hanging from the hips may be jacket, the same face hanging from a thigh may not, a face
    under the wrist hanging from the hand may not], then under a long coat's hem at 0.6 m [the thigh's face at 0.92 m
    may, one at 0.7 m may, one at 0.5 m may not, the hand's may not]."""
    names = ["Hips", "Spine2", "Neck2", "Chest", "LeftFoot", "RightFoot", "LeftHand", "RightHand"]
    bind = np.repeat(np.eye(4)[None], len(names), axis=0)
    bind[:, 1, 3] = [1.0, 1.15, 1.5, 1.3, 0.06, 0.06, 0.85, 0.85]
    person = {"names": names, "bind": bind}
    middles = np.array([[0.1, 0.92, 0.1], [0.1, 0.92, 0.1], [0.3, 0.8, 0.0]])
    short = cloth.allowed(person, middles, np.array(["Hips", "LeftLeg", "LeftHand"]))["jacket"].tolist()
    middles = np.array([[0.1, 0.92, 0.1], [0.1, 0.7, 0.1], [0.1, 0.5, 0.1], [0.3, 0.8, 0.0]])
    long = cloth.allowed(person, middles, np.array(["LeftLeg", "LeftLeg", "LeftLeg", "LeftHand"]), hem=0.6)
    return [short, long["jacket"].tolist()]


def cloth_hem_found():
    """A coat (a ring of radius 20 cm from 0.6 to 1.2 m, its paint the jacket's) over two legs (rings of 7 cm either
    side, from the floor to 1.0 m, their paint the jeans', so inside the coat they outnumber it): the hem read from
    0.9 m down, in metres (0.6), and read off every face of a band rather than its outermost (`outer_share` broken:
    under 0.9 m the legs outnumber the coat and the hem stays at its start)."""
    angles = np.linspace(0, 2 * np.pi, 120, endpoint=False)
    coat = [[0.2 * np.cos(a), y, 0.2 * np.sin(a)] for a in angles for y in np.arange(0.605, 1.2, 0.01)]
    legs = [[side * 0.09 + 0.07 * np.cos(a), y, 0.07 * np.sin(a)] for side in (-1, 1) for a in angles
            for y in np.arange(0.005, 1.0, 0.005)]
    middles = np.array(coat + legs)
    nearer = np.r_[np.ones(len(coat), bool), np.zeros(len(legs), bool)]
    clothes = np.ones(len(middles), bool)
    found = cloth.jacket_hem(middles, nearer, clothes, 0.9)
    band = np.abs(middles[:, 1] - 0.8) < 0.01
    return [round(found, 2), bool(nearer[band].mean() < cloth.HEM_SHARE)]


def cloth_scarf_split():
    """A front of a chest: a cream scarf (two strands 3 to 9 cm off the middle, 4 cm forward) over a black shirt (the
    middle 3 cm, behind it) inside a camel jacket: [the scarf's faces found, the shirt's found]; the same front with the
    two colours side by side at one depth (a hoodie's grey and its dark drawstrings) has no scarf."""
    names = ["Spine1", "Chest", "Neck2"]
    bind = np.repeat(np.eye(4)[None], len(names), axis=0)
    bind[:, 1, 3] = [1.05, 1.2, 1.5]
    xs, ys = np.meshgrid(np.arange(-0.105, 0.106, 0.005), np.arange(1.1, 1.45, 0.005))
    xs, ys = xs.ravel(), ys.ravel()
    scarf = (np.abs(xs) > 0.03) & (np.abs(xs) < 0.09)
    shirt = np.abs(xs) <= 0.03
    middles = np.r_[np.c_[xs, ys, np.where(scarf, 0.12, 0.08)], np.c_[np.full(400, 0.2), np.linspace(1.1, 1.4, 400),
                                                                     np.full(400, 0.05)]]
    lab = np.r_[np.where(scarf[:, None], [85.0, 1.0, 8.0], np.where(shirt[:, None], [5.0, 0.0, 0.0], [58.0, 13.0, 24.0])),
                np.tile([58.0, 13.0, 24.0], (400, 1))]
    jacket = np.r_[~scarf & ~shirt, np.ones(400, bool)]
    person = {"names": names, "bind": bind, "lab": lab, "head": np.zeros(len(middles), bool)}
    strongest = np.full(len(middles), "Chest")
    found = cloth.scarf_split(person, middles, strongest, {"jacket": jacket})
    flat = middles.copy()
    flat[:, 2] = np.where(jacket, flat[:, 2], 0.08)
    none = cloth.scarf_split(person, flat, strongest, {"jacket": jacket})
    return [bool(np.array_equal(found["scarf"][:len(xs)], scarf)), bool(np.array_equal(found["shirt"][:len(xs)], shirt)),
            none == {}]


def cloth_under_coloured():
    """A person painted a mid grey jacket (L 53.4: sRGB 0.5), a camel shirt (CIELAB 58, 13, 24) and black trousers:
    the body under them [the trunk the jacket's grey in linear RGB (0.214), the legs near black], and with no jacket
    [the trunk the shirt's camel] (the trunk's and legs' fixed white and denim showed as patches)."""
    kinds = np.array([cloth.KINDS.index(kind) for kind in ("jacket", "shirt", "jeans")])
    person = {"lab": np.array([[53.389, 0.0, 0.0], [58.0, 13.0, 24.0], [3.0, 0.0, 0.0]])}
    found = cloth.under_colours(person, kinds)
    shirt_only = cloth.under_colours(person, np.where(kinds == cloth.KINDS.index("jacket"),
                                                      cloth.KINDS.index("shirt"), kinds))
    return [bool(np.allclose(found[0], 0.214, atol=0.003)), bool(found[1].max() < 0.01),
            bool(shirt_only[0][0] > shirt_only[0][2] * 1.5)]


SKIRT_NAMES = ["Hips", "LeftLeg", "RightLeg", "Chest", "LeftArm", "LeftForeArm", "LeftHand", "RightArm",
               "RightForeArm", "RightHand"]


def skirt_person(points, faces, weights):
    """A toy person on SKIRT_NAMES: the hips at 1 m, the hip joints at 0.9 m 10 cm either side, the chest at 1.3 m,
    the shoulders (Arm joints) at 1.4 m 20 cm either side."""
    bind = np.repeat(np.eye(4)[None], len(SKIRT_NAMES), axis=0)
    places = {"Hips": (0, 1.0), "LeftLeg": (0.1, 0.9), "RightLeg": (-0.1, 0.9), "Chest": (0, 1.3),
              "LeftArm": (0.2, 1.4), "LeftForeArm": (0.2, 1.15), "LeftHand": (0.2, 0.9), "RightArm": (-0.2, 1.4),
              "RightForeArm": (-0.2, 1.15), "RightHand": (-0.2, 0.9)}
    for name, (x, y) in places.items():
        bind[SKIRT_NAMES.index(name), :2, 3] = x, y
    return {"names": SKIRT_NAMES, "bind": bind, "points": points, "faces": faces, "weights": weights}


def cloth_skirted():
    """A coat panel 40 cm wide from 1.1 m down to 0.5 m (1 cm apart), skinned to the hips over the hip joints (0.9 m)
    and to the thigh on its side under them, its outer lowest corner a cuff (on the left hand): under the hip joints its middle at
    the hem hangs from both thighs alike and from the pelvis the most (SKIRT_HIPS's hem share and SKIRT_MIDDLE), its
    side at the hem from its own thigh and the pelvis's hem share; over the hip joints and at the cuff the weights are
    their own, every row sums to one; a short jacket (all over 0.9 m) is left."""
    x, y = np.meshgrid(np.linspace(-0.2, 0.2, 41), np.linspace(0.5, 1.1, 61))
    points = np.round(np.c_[x.ravel(), y.ravel(), np.full(x.size, 0.1)], 6)
    corner = (np.arange(60)[:, None] * 41 + np.arange(40)[None]).ravel()
    faces = np.r_[np.c_[corner, corner + 1, corner + 42], np.c_[corner, corner + 42, corner + 41]]
    weights = np.zeros((len(points), len(SKIRT_NAMES)))
    weights[points[:, 1] >= 0.9, 0] = 1.0
    weights[(points[:, 1] < 0.9) & (points[:, 0] > 0), 1] = 1.0
    weights[(points[:, 1] < 0.9) & (points[:, 0] <= 0), 2] = 1.0
    cuff = int(np.flatnonzero((points[:, 0] == 0.2) & (points[:, 1] == 0.5))[0])
    weights[cuff] = 0.0
    weights[cuff, SKIRT_NAMES.index("LeftHand")] = 1.0
    kinds = np.full(len(faces), cloth.KINDS.index("jacket"))
    found = cloth.skirted(skirt_person(points, faces, weights), kinds)
    middle = int(np.flatnonzero((points[:, 0] == 0.0) & (points[:, 1] == 0.5))[0])
    side = int(np.flatnonzero((points[:, 0] == -0.2) & (points[:, 1] == 0.5))[0])
    over = points[:, 1] >= 0.9
    short = np.where((points[faces][:, :, 1] >= 0.9).all(1), cloth.KINDS.index("jacket"), cloth.KINDS.index("jeans"))
    return [round(float(found[middle, 0]), 3), bool(np.isclose(found[middle, 1], found[middle, 2])),
            [round(float(value), 3) for value in found[side, :3]], bool(np.allclose(found[over], weights[over])),
            bool(np.allclose(found[cuff], weights[cuff])), bool(np.allclose(found.sum(1), 1.0)),
            bool(np.allclose(cloth.skirted(skirt_person(points, faces, weights), short), weights))]


def cloth_sleeve_cut():
    """A flat garment 30 cm wide from 0.9 m to 1.5 m whose weights turn from the chest to the left arm between 15 and
    25 cm out: under 8 cm below the shoulder its sleeve (faces mostly the arm's) shares no point with its side, the
    sleeve's cut points are the arm's alone and the side's the chest's alone, a sleeve point 2.5 cm off the cut is
    eased toward the arm and one 10 cm off keeps its weights, every cut edge is closed by two flap faces on each
    piece and every flap point stands FLAP_M in from its edge point; over the cut's top the two pieces stay joined;
    the sleeve's faces between the cut and the arm's line (25 cm out) are copied onto the chest COVER_IN_M in, under
    the cut's top only, so the side stays closed where the sleeve leaves it."""
    x, y = np.meshgrid(np.linspace(0.0, 0.3, 13), np.linspace(0.9, 1.5, 25))
    points = np.c_[x.ravel(), y.ravel(), np.full(x.size, 0.1)]
    corner = (np.arange(24)[:, None] * 13 + np.arange(12)[None]).ravel()
    faces = np.r_[np.c_[corner, corner + 1, corner + 14], np.c_[corner, corner + 14, corner + 13]]
    arm = np.clip((points[:, 0] - 0.15) / 0.1, 0.0, 1.0)
    weights = np.zeros((len(points), len(SKIRT_NAMES)))
    weights[:, SKIRT_NAMES.index("LeftArm")] = arm
    weights[:, SKIRT_NAMES.index("Chest")] = 1.0 - arm
    garment = {"points": points, "faces": faces, "weights": weights, "riding": np.zeros(len(points), bool),
               "normals": np.tile([0.0, 0.0, 1.0], (len(points), 1)), "source": np.arange(len(points))}
    person = skirt_person(points, faces, weights)
    for name in ("LeftArm", "LeftHand"):  # the arm's line down the sleeve's middle, 25 cm out
        person["bind"][SKIRT_NAMES.index(name), 0, 3] = 0.25
    found = cloth.sleeves_cut(person, garment)
    sleeve, cut, flaps = found["sleeve"], found["cut"], found["flaps"]
    count = len(points) + int(cut.sum()) // 2
    shared = np.intersect1d(found["faces"][sleeve], found["faces"][~sleeve])
    low = found["points"][shared, 1] < 1.4 - cloth.CUT_UNDER_SHOULDER_M - 0.03
    copies = np.arange(len(points), count)
    originals = found["source"][copies]
    pick = lambda x_place, y_place: int(np.flatnonzero(  # noqa: E731
        np.isclose(found["points"][:count, 0], x_place) & np.isclose(found["points"][:count, 1], y_place))[-1])
    eased = found["weights"][pick(0.225, 1.0), SKIRT_NAMES.index("LeftArm")]
    edge_count = len(copies) - 1
    cover, closing = flaps[:len(flaps) - 4 * edge_count], flaps[len(flaps) - 4 * edge_count:]
    flap_points = np.unique(closing[:, 2])
    depth = np.linalg.norm(found["points"][flap_points] - found["points"][found["source"][flap_points]], axis=1)
    cover_points = np.unique(cover)
    cover_middles = found["points"][found["source"][cover]].mean(1)
    covers = [bool(len(cover) > 0), bool(np.allclose(found["weights"][cover_points, SKIRT_NAMES.index("Chest")], 1.0)),
              bool(np.allclose(np.linalg.norm(found["points"][cover_points] - found["points"][found["source"][
                  cover_points]], axis=1), cloth.COVER_IN_M)),
              bool((cover_middles[:, 0] < 0.25).all() and (cover_middles[:, 1] < 1.4 - cloth.CUT_UNDER_SHOULDER_M).all())]
    return [bool(len(copies) > 0), int(low.sum()), bool(shared.size > 0),
            bool(np.allclose(found["weights"][copies, SKIRT_NAMES.index("LeftArm")], 1.0)),
            bool(np.allclose(found["weights"][originals, SKIRT_NAMES.index("Chest")], 1.0)),
            bool(0.8 < eased < 0.95), bool(np.allclose(found["weights"][pick(0.3, 1.0)], weights[pick(0.3, 1.0)])),
            bool(np.all(closing[:, 2] >= count)), bool(np.allclose(depth, cloth.FLAP_M)), covers]


def cloth_short_edge_collapsed():
    """A tiny triangle of 1 mm sides set in a 1 cm hexagon (no corner under ANGLE_LEAST) collapsed: no edge under
    3 mm is left (the hoodie man's jeans kept a 1 mm edge, read as a stretch of 0.68)."""
    ring = np.array([[np.cos(angle), np.sin(angle), 0.0] for angle in np.arange(6) * np.pi / 3]) * 0.01
    inner = np.array([[np.cos(angle), np.sin(angle), 0.0] for angle in np.arange(3) * 2 * np.pi / 3]) * 0.000577
    points = np.r_[ring, inner]
    faces = [[6, 7, 8]]
    for side in range(6):
        near = 6 + (side // 2)
        faces.append([side, (side + 1) % 6, near if side % 2 == 0 else 6 + ((side + 1) // 2) % 3])
    for inner_point in range(3):
        faces.append([6 + inner_point, 6 + (inner_point + 1) % 3, (2 * inner_point + 1) % 6])
    mesh = trimesh.Trimesh(points, np.array(faces), process=False)
    trimesh.repair.fix_winding(mesh)
    before = cloth.cloth_mesh.corner_angles(points, np.asarray(mesh.faces)).min()
    mended, mended_faces = cloth.cloth_mesh.slivers_collapsed(points, np.asarray(mesh.faces))
    return [bool(before >= cloth.cloth_mesh.ANGLE_LEAST),
            bool(cloth.cloth_mesh.edge_lengths(mended, mended_faces).min() >= 0.003)]


def cloth_paint_read_from_top():
    """A picture red in its top half and blue in its bottom, read at a face whose glTF texture places lie near the
    top (v 0.1, glTF's v runs down): red, not blue (`file_places` left out: every face read its mirror row)."""
    picture = np.zeros((8, 8, 3))
    picture[:4, :, 0] = 1.0
    picture[4:, :, 2] = 1.0
    places = cloth.file_places(np.array([[0.4, 0.1], [0.6, 0.1], [0.5, 0.15]]))
    lab = cloth.face_paint(picture, places, np.array([[0, 1, 2]]))[0]
    return bool(lab[1] > 50 and lab[2] > 30)


def colour_toy():
    """A toy front (points on a plane facing +z, 0.6 m by 1.2 m, UV its box) painted as TRELLIS.2 paints, and its photo
    (RGBA, a margin of air round the person): (points, uv, paint texture, photo)."""
    xs, ys = np.meshgrid(np.linspace(0.0, 0.6, 150), np.linspace(0.0, 1.2, 300))
    points = np.column_stack([xs.ravel(), ys.ravel(), np.zeros(xs.size)])
    uv = np.column_stack([xs.ravel() / 0.6, ys.ravel() / 1.2])
    height = 1.0 - (np.arange(128) + 0.5) / 128  # the texture's rows, top down, as heights
    paint = np.zeros((128, 64, 4), np.uint8)
    paint[..., 3] = 255
    fold = (np.arange(128) // 6) % 2 == 1
    paint[height > 0.5, :, :3] = (65, 72, 68)
    paint[(height > 0.5) & fold, :, :3] = (48, 54, 51)
    paint[(height <= 0.5) & (height > 0.1), :, :3] = (7, 7, 8)
    paint[height <= 0.1, :, :3] = (14, 3, 0)
    grain = np.random.default_rng(2).integers(-5, 6, paint[..., :3].shape)  # boots, trousers overlap
    paint[..., :3] = np.clip(paint[..., :3].astype(int) + grain, 0, 255).astype(np.uint8)
    photo = np.zeros((280, 160, 4), np.uint8)
    rows = 1.0 - (np.arange(240) + 0.5) / 240
    person = photo[20:260, 20:140]
    person[..., 3] = 255
    person[rows > 0.5, :, :3] = (131, 137, 123)
    person[(rows <= 0.5) & (rows > 0.1), :, :3] = (15, 15, 21)
    person[rows <= 0.1, :, :3] = (89, 51, 41)
    noise = np.random.default_rng(3).integers(-3, 4, person[..., :3].shape)
    person[..., :3] = np.clip(person[..., :3].astype(int) + noise, 0, 255).astype(np.uint8)
    return points, uv, paint, photo


def colour_body_toy():
    """A toy bust as `colour_toy`'s front: (points, uv, paint, photo, the paint's texture rows as heights)."""
    xs, ys = np.meshgrid(np.linspace(0.0, 0.6, 150), np.linspace(0.0, 1.2, 300))
    points = np.column_stack([xs.ravel(), ys.ravel(), np.zeros(xs.size)])
    uv = np.column_stack([xs.ravel() / 0.6, ys.ravel() / 1.2])
    height = 1.0 - (np.arange(128) + 0.5) / 128
    paint = np.zeros((128, 64, 4), np.uint8)
    paint[..., 3] = 255
    paint[height > 0.9, :, :3] = (47, 37, 32)
    paint[(height <= 0.9) & (height > 0.6), :32, :3] = (166, 109, 99)
    paint[(height <= 0.9) & (height > 0.6), 32:, :3] = (55, 39, 35)
    paint[height <= 0.6, :, :3] = (65, 72, 68)
    grain = np.random.default_rng(2).integers(-3, 4, paint[..., :3].shape)
    paint[..., :3] = np.clip(paint[..., :3].astype(int) + grain, 0, 255).astype(np.uint8)
    photo = np.zeros((280, 160, 4), np.uint8)
    rows = 1.0 - (np.arange(240) + 0.5) / 240
    person = photo[20:260, 20:140]
    person[..., 3] = 255
    person[rows > 0.9, :, :3] = (36, 28, 23)
    person[(rows <= 0.9) & (rows > 0.6), :, :3] = (208, 158, 137)
    person[rows <= 0.6, :, :3] = (131, 137, 123)
    noise = np.random.default_rng(3).integers(-3, 4, person[..., :3].shape)
    person[..., :3] = np.clip(person[..., :3].astype(int) + noise, 0, 255).astype(np.uint8)
    return points, uv, paint, photo, height


def colour_body_kept():
    """The toy bust toned: its hair, the face's skin half and its dark half each within 2 Lab units of their paint;
    the jacket within 6 of the photo's sage."""
    from skimage.color import rgb2lab
    points, uv, paint, photo, height = colour_body_toy()
    centres, table, _ = colour.fitted(points, colour.texel_colours(paint, uv), photo)
    before = rgb2lab(paint[..., :3] / 255.0)
    after = rgb2lab(colour.toned_texture(paint, colour.heights_of(points), uv, centres, table)[..., :3] / 255.0)
    face = (height < 0.88) & (height > 0.62)

    def moved(rows, columns):
        return float(np.linalg.norm(after[rows][:, columns].reshape(-1, 3).mean(0)
                                    - before[rows][:, columns].reshape(-1, 3).mean(0)))

    sage = rgb2lab(np.array([[[131, 137, 123]]], float) / 255.0)[0, 0]
    jacket = float(np.linalg.norm(after[height < 0.55].reshape(-1, 3).mean(0) - sage))
    return [moved(height > 0.92, slice(None)) < 2.0, moved(face, slice(2, 30)) < 2.0,
            moved(face, slice(34, 62)) < 2.0, jacket < 6.0]


def colour_toned():
    """The toy's paint toned toward its photo: the jacket, trousers and boots within 6 Lab units of the photo's (the
    boots' trace of red never lost to the trousers), and the jacket's fold stripes keeping over half their depth."""
    from skimage.color import rgb2lab
    points, uv, paint, photo = colour_toy()
    centres, table, _ = colour.fitted(points, colour.texel_colours(paint, uv), photo)
    toned = rgb2lab(colour.toned_texture(paint, colour.heights_of(points), uv, centres, table)[..., :3] / 255.0)
    height = 1.0 - (np.arange(128) + 0.5) / 128
    fold = (np.arange(128) // 6) % 2 == 1

    def lab_of(rgb):
        return rgb2lab(np.array(rgb, float)[None, None] / 255.0)[0, 0]

    def off(rows, rgb):
        return float(np.linalg.norm(toned[rows].reshape(-1, 3).mean(0) - lab_of(rgb)))

    jacket, flat = height > 0.55, (height > 0.55) & ~fold
    depth_before = lab_of((65, 72, 68))[0] - lab_of((48, 54, 51))[0]
    depth_after = toned[flat].reshape(-1, 3)[:, 0].mean() - toned[jacket & fold].reshape(-1, 3)[:, 0].mean()
    return [off(jacket, (131, 137, 123)) < 6.0, off((height < 0.45) & (height > 0.15), (15, 15, 21)) < 6.0,
            off(height < 0.06, (89, 51, 41)) < 6.0, bool(depth_after > 0.5 * depth_before)]


def colour_two_parts():
    """The toy front as a swapped model's two textured primitives (its left half on the paint, its right half on the
    paint at twice the size), toned through the file: each picture keeps its size and each half's jacket reads within
    6 Lab units of the photo's sage."""
    import pathlib
    import tempfile
    from PIL import Image
    from skimage.color import rgb2lab
    from tools.props import glb_file
    points, uv, paint, photo = colour_toy()
    grid = np.arange(points.shape[0]).reshape(300, 150)
    scene = trimesh.Scene()
    halves = (("left", slice(0, 75), paint), ("right", slice(74, 150), paint.repeat(2, 0).repeat(2, 1)))
    for name, columns, picture in halves:
        block = grid[:, columns]
        corners = block[:-1, :-1].ravel(), block[:-1, 1:].ravel(), block[1:, :-1].ravel(), block[1:, 1:].ravel()
        triangles = np.vstack([np.column_stack([corners[0], corners[1], corners[3]]),
                               np.column_stack([corners[0], corners[3], corners[2]])])
        used = np.unique(triangles)
        mesh = trimesh.Trimesh(points[used], np.searchsorted(used, triangles), process=False)
        material = trimesh.visual.material.PBRMaterial(name=name, baseColorTexture=Image.fromarray(picture))
        mesh.visual = trimesh.visual.TextureVisuals(uv=uv[used], material=material)
        scene.add_geometry(mesh, geom_name=name)
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        scene.export(folder / "model.glb")
        Image.fromarray(photo).save(folder / "photo.png")
        colour.toned(folder / "model.glb", folder / "photo.png", folder / "toned.glb", folder / "colour.json")
        document, views = glb_file.read(folder / "toned.glb")
        parts = colour.parts_of(document, views)
        pictures = [colour.picture_of(document, views, image) for _, _, image in parts]
    sage = rgb2lab(np.array([[[131, 137, 123]]], float) / 255.0)[0, 0]
    jackets = [rgb2lab(colour.texel_colours(picture, part_uv)[part_points[:, 1] > 0.7]).mean(0)
               for (part_points, part_uv, _), picture in zip(parts, pictures)]
    return [[picture.shape[:2] for picture in pictures], [bool(np.linalg.norm(jacket - sage) < 6.0) for jacket in jackets]]


def tether_curtain():
    """A curtain (30 cm square, 2 cm apart, its top row riding) swung 2.5 cm toward and away from a ball behind it,
    as tethered cloth feeling g toward the ball (its limb turned a quarter): [its riding row on its targets, every point
    within its tether, no point deeper toward the ball than its target or half a millimetre past the clearance, the
    loose cloth hanging over a centimetre off its targets, no edge stretched past 5%]."""
    xs, ys = np.meshgrid(np.linspace(-0.15, 0.15, 16), np.linspace(0.0, -0.3, 16))
    points = np.column_stack([xs.ravel(), ys.ravel(), np.zeros(xs.size)])
    grid = np.arange(256).reshape(16, 16)
    corners = grid[:-1, :-1].ravel(), grid[:-1, 1:].ravel(), grid[1:, :-1].ravel(), grid[1:, 1:].ravel()
    faces = np.vstack([np.column_stack([corners[0], corners[2], corners[1]]),
                       np.column_stack([corners[1], corners[2], corners[3]])])
    riding = np.zeros(256, bool)
    riding[:16] = True
    ball = trimesh.creation.icosphere(3, 0.1)
    centre = np.array([0.0, -0.25, -0.13])
    frames = 45
    targets = np.repeat(points[None], frames, axis=0)
    targets[:, :, 2] -= 0.025 * np.sin(np.arange(frames) / 30.0 * 4.0 * np.pi)[:, None]
    body = np.repeat((np.asarray(ball.vertices) + centre)[None], frames, axis=0)
    tether = cloth_tether.tethers(cloth_tether.TETHER_M["jeans"], -points[:, 1])
    least = cloth_tether.allowances(targets, body, np.asarray(ball.faces), 0.0015)
    run = cloth_tether.tethered(targets, tether, faces, body, np.asarray(ball.faces), 30.0, least,
                                np.tile([0.0, 0.0, -9.81], (frames, 256, 1)))

    def depth(positions):
        return 0.1 - np.linalg.norm(positions - centre, axis=2)

    edges = cloth_tether.edges_of(faces)
    built = np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1)
    now = np.linalg.norm(run[:, edges[:, 0]] - run[:, edges[:, 1]], axis=2)
    return [float(np.abs(run[:, riding] - targets[:, riding]).max()) == 0.0,
            bool((np.linalg.norm(run - targets, axis=2) - tether).max() < 1e-9),
            bool((depth(run) - np.maximum(depth(targets), -0.0015)).max() < 0.0005),
            bool(np.linalg.norm(run - targets, axis=2).max() > 0.01), bool((now / built - 1.0).max() < 0.05)]


def tether_gravity():
    """The gravity a point feels beyond its rest hang (m/s^2), its limb unturned, turned a quarter and turned over."""
    moves = np.repeat(np.eye(4)[None, None], 3, axis=0)
    moves[1, 0, :3, :3] = [[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]
    moves[2, 0, :3, :3] = np.diag([-1.0, -1.0, 1.0])
    felt = cloth_tether.turned_gravity(np.ones((1, 1)), moves)[:, 0]
    return [round(float(np.linalg.norm(force)), 2) for force in felt]


def tether_inside_read():
    """A box body's points round it: (outside points the planes push past 1 mm, inside points they leave past 1 mm
    in, inside points), each read off the box's NEIGHBOURS nearest points' planes."""
    box = trimesh.creation.box((0.2, 0.4, 0.1)).subdivide().subdivide().subdivide()
    points = np.random.default_rng(0).uniform([-0.15, -0.25, -0.08], [0.15, 0.25, 0.08], (3000, 3))
    truth = trimesh.proximity.signed_distance(box, points)
    corners = np.asarray(box.vertices)
    over, normals = cloth_tether.outside(points, corners, cloth_tether.vertex_normals(corners, np.asarray(box.faces)))
    pushed = points + np.maximum(0.0, 0.002 - over)[:, None] * normals
    after = trimesh.proximity.signed_distance(box, pushed)
    moved = np.linalg.norm(pushed - points, axis=1)
    return [int(((truth < -0.003) & (moved > 0.001)).sum()), int(((truth > 0.001) & (after > 0.001)).sum()),
            int((truth > 0.001).sum())]


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
    ("the hair's skin is laid onto the scalp at the hole's edge, no lip standing", lambda: skin_laid() < 0.002, True),
    ("a strand's layer runs from the scalp's side to the shell's outer surface", shell_layers, (True, True)),
    ("the shell's grooves and paint streaks are read as its flow", groove_and_streak, (True, True)),
    ("the photo's straight hair reads straight, its waves their size", photo_waves, (True, True)),
    ("the roots fade in over the hairline, none on the chin, the beard fades down the neck", roots_and_beard_fade,
     (True, True, True)),
    ("a darker hair gets more melanin, a grey head the white share and melanin whose swatch shows its lightness and "
     "spread", lambda: bool(fibre_fitted()[0]), True),
    ("the photo's hair holds a silver bob as light as its backdrop and little else",
     lambda: (lambda found: (found[0] > 0.9, found[1] < 0.05))(silver_hair_read()), (True, True)),
    ("a hair-white bit on the forehead the clothes' colour claims is hair, the dark brows there never",
     white_bits_kept_as_hair, (1, 1.0, 0.0)),
    ("no roots on the forehead under the hairline table, beside it and over it the paint's", forehead_roots,
     (0.0, 1.0, 1.0)),
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
    ("a hollow the model shuts reads shut, the photo's darker, warmer light in it divided out", skin_hollow_light_off,
     [True, True]),
    ("the photo's fringe and lid openings are kept off, its brows and moustache kept; the model's painted fringe "
     "wears no photo, its beard's middle may; the share rises from its outer edge", skin_photo_kept_off, [True] * 6),
    ("a point wears the photo only facing forward, on the front, in the photo's face, clear of the eye; the T-zone "
     "holds the nose", skin_shares, [True] * 7),
    ("the photo's iris is unrolled onto the eyeball: its pupil's share read, the catchlight gone, the white outside",
     iris_unrolled, [True, True, True]),
    ("the paint's dark baked shade is lifted to the skin round it, plain skin and hair left",
     paint_lifted, [True, True, True]),
    ("a painted brow wearing the photo is skin, one not wearing it keeps its own material", skin_wears_photo,
     [True, True]),
    ("a point on a steep side is on the front, one behind it is not", steep_point_seen, [True, False]),
    ("the paint on the skin gets the photo skin's colour and spread, the hair keeps its paint", paint_toned,
     [True, True, True]),
    ("a hidden layer never comes through the lid the move pulls forward", layers_kept, [True, True, True]),
    ("the lids' triangles split in four and closed round them with no crack", split_closed, [True, True, True]),
    ("the photo's opening is read round each eye and held inside the ball", photo_opening, [True] * 4),
    ("the lids moved onto the photo's opening, thin over the eye and never inside it", lids_reshaped,
     [True, True, True]),
    ("upper lashes rise from the margin, lower ones fall, all leaving forward", lashes_grown, [True] * 6),
    ("a photo with dense lashes gets the full lashes, one with a few gets fewer", lashes_by_photo, [True, True]),
    ("the brow's hairs grow where the photo's brow is dark, lying on the skin", brows_follow_photo, [True, True]),
    ("the painted brow is painted over with the skin round it", brow_painted_over, [True, True]),
    ("a garment's kinds follow the paint: a fleck or stray faces join the piece round them", cloth_kinds_settled, 0),
    ("the jeans ride the skin a waistband's width under their top, measured over the cloth", cloth_waistband,
     [True, True]),
    ("a walk's repeated last frame is dropped and its travel carried on cycle after cycle", cloth_walk_tiled,
     [4, 0.3, 1, 0.6]),
    ("the body under the clothes is pushed in to the margin under a close shell, never under a far one",
     cloth_body_pushed, [round(cloth.MARGIN_M - 0.005, 3), 0.0]),
    ("a garment's sim mesh is laid over the body onto its inner wall: one piece, its two ends its only rims, manifold, "
     "the sliver and the speck gone", cloth_tube_laid, [2, 1, 2, True]),
    ("a remeshed needle is collapsed and a bow tie split into two fans", cloth_mesh_mended,
     [True, True, 6, [0, 1, 2, 3, 4, 5]]),
    ("the drawn surface rides its sim mesh exactly at rest and rigidly when it moves; a piece hung by nothing rides "
     "whole; its own normals turn with its skinning", cloth_drawn_rides, [True, True, 1, True, True, True]),
    ("a face hanging from a leg is jacket only above a long coat's hem, never a hand's under its wrist",
     cloth_jacket_off_legs, [[True, False, False], [True, True, False, False]]),
    ("a long coat's hem is read from the outside, under the trousers it hangs over", cloth_hem_found, [0.6, True]),
    ("a scarf standing forward of the shirt in the open front is its own garment; one depth is no scarf",
     cloth_scarf_split, [True, True, True]),
    ("a long coat under the hip joints hangs from both thighs and the pelvis as a skirt; its cuff, its top and a "
     "short jacket keep their own", cloth_skirted, [0.45, True, [0.3, 0.0, 0.7], True, True, True, True]),
    ("a sleeve fused to the side is cut off it under the shoulder, each piece eased onto its own limb, every cut "
     "edge closed by a flap, the side covered", cloth_sleeve_cut,
     [True, 0, True, True, True, True, True, True, True, [True, True, True, True]]),
    ("a remeshed edge under a third of the mesh's edge is collapsed", cloth_short_edge_collapsed, [True, True]),
    ("a face's paint is read at its own row of the picture, glTF's v running down", cloth_paint_read_from_top, True),
    ("the body under the clothes wears the person's own shirt and trousers", cloth_under_coloured, [True, True, True]),
    ("the paint is toned toward the photo garment by garment: the jacket's sage, the boots' brown under trousers "
     "painted as black, the folds kept", colour_toned, [True] * 4),
    ("the body is never toned: hair and a face painted half skin, half dark keep their paint, the jacket is toned",
     colour_body_kept, [True] * 4),
    ("a swapped model's head and body pictures are each toned through their own UVs and kept at their own size",
     colour_two_parts, [[(128, 64), (256, 128)], [True, True]]),
    ("tethered cloth: riding points on their targets, every point within its tether, never deeper than its target, "
     "the loose cloth swinging, the edges held", tether_curtain, [True] * 5),
    ("tethered cloth feels only the gravity its turn adds to its rest hang", tether_gravity, [0.0, 13.87, 19.62]),
    ("a point is inside the body only where all its nearest body points' planes say so",
     lambda: (lambda found: (found[0] <= 5, found[1] <= 0.03 * found[2]))(tether_inside_read()), (True, True)),
])
def test_a_generated_head_gets_real_eyes_and_regrown_hair(case, made_value, wanted):
    assert made_value() == wanted, case
