"""The face joins the body as one shut skin moved by every control (#226): the face's border, the body cut under it and
the strip between them make one skin with no open edge, every triangle turned the same way and the cut within one body
edge of the face's border all round (fit.seam and
fit.joined_skin) with no strip triangle standing as a ridge or folded into the head (fit.cleared, fit.seam_turns), a
fold or a ridge on a join refused (fit.seam_smooth), a neck too thick or long for the height refused and one in the
normal range passing (fit.neck_measures, fit.neck_normal), the throat laid on the body's skin (fit.throat_laid), the
body's skin shapes the face fully on its border and not past the blend (fit.body_share), a face
standing off the head is laid on it at its border and keeps its middle, an ear standing off within the band keeps
its height (fit.laid_on_skin), an ear squashed onto the head is refused and one standing off it passes
(fit.ear_measures, fit.ears_standing), the skin under the face near its border is cut and the skin beside it kept
(fit.inside_border), brow hairs lie on the skin, grow up at the brow's head and outward and down at its tail and move
with the skin (strands.brow_strands, strands.checked), a lash curls up off an upper lid and down off a lower and
turns with its card (strands.lash_frame, strands.lash_line), and
MHR's 72 controls each move the face, through ICT expressions or the body's own offsets, a name ICT lacks refused
(expressions.mapping), an identity past three standard deviations refused as a caricature (fit.within_population),
the cornea rises over the iris to Gullstrand's height and meets the eye at the iris's edge (face.dome), the
photographed skin's tile repeats with no seam (skin_scan.periodic), the scanned skin finish is listed with the
scan's tiles as its files, the scan named as carried and its CC BY 3.0 licence block with its credit
(finishes.written), a short, broad-jawed face is moved towards an adult's proportions and an adult's is not
(fit.adult_moves), the skin's region channels are one order where marked and drawn (face.TONES, blender_face.TONES),
a lid's skin by its eyeball is wet (face.eyeball_gap), a brow thins at its lower edge and tail (strands.thinned), the
shell over the eye is glass over the iris and a thin film over the white (face.cornea), and the skin's crevices are
its own (finishes' `own`).

Shapes made here: a coarse sphere for the body's head and a finer sphere's cap for the face, laid on it (one
with a bump for an ear); a strip standing off a sphere for an ear; one card triangle for a lash; a cylinder for a
neck; a sloped, speckled square for the skin's tile (its far edge 0.5 brighter than its near one); two small
pictures standing in for the scan's tiles.

Breaks that turn it red (each applied once and seen red, 2026-11-24):
- the shut skin: zipper's `advance_outer` made `at_outer < count_outer` (the strip walks the face's loop first and
  leaves triangles that cross); and, apart, joined_skin's `outward(strip, ...)` made `strip` (the strip turned
  against the body's skin); and, apart, covered's `blocked[wall(graph, stops)] = True` made
  `blocked[stops[:1]] = True` (no wall along the border: the fill under the face leaks and is refused).
- the join's ridge: seam's `cleared(...)` made `kept_body(body_triangles, under)` (the cut left on the face's border:
  a strip triangle folds; seen red 2026-11-25); and, apart, seam_smooth's `largest > SEAM_TURN_DEGREES` made
  `largest > 180.0` (a fold and a ridge pass; seen red 2026-11-25).
- the neck: neck_normal's range test made `False` (a thick and a long neck pass; seen red 2026-11-25); and, apart,
  sternal_notch's `min(front, ...)` made `max` (the notch read at the chin: the lengths change; seen red 2026-11-25).
- the throat: throat_laid's `throat[reached, None] *` made `0.0 *` (the throat stands 8 mm off the skin; seen red
  2026-11-25).
- the ear: laid_on_skin's band moved by its border's moves made each point's own snap onto the skin (the ears were
  crushed flat onto the head; seen red 2026-11-24).
- the squashed ear: ears_standing's range test made `True` (a squashed ear passes; seen red 2026-11-24).
- the brows: brow_strands' `+ mesh.face_normals[under] * lift[:, None]` made `-` (the hairs lie inside the skin and
  checked refuses them; seen red 2026-11-24); and, apart, brow_angle's `angle - BROW_MEET * across` made
  `-angle - ...` (the head's hairs point down; seen red 2026-11-24).
- the lashes: lash_frame's `normal[1] * rising > 0` made `normal[1] > 0` (a lower lash curls up into the lid; seen
  red 2026-11-24).
- the skin under the face: inside_border's `under_face(...)` made `False` (seen red 2026-11-24).
- the body's share: body_share's `1.0 - distance / BLEND_METRES` made `distance / BLEND_METRES`.
- the face laid on the skin: laid_on_skin's `* share[pulled, None]` made `* 0.0` (the face's border stood 10 mm off
  the head, the strip a wall).
- every control moves the face: the ICT_OF row "jawDrop" dropped (the jaw would move only by the body's own offsets:
  an unmapped control outside the five families with no ICT expression).
- a name ICT lacks: mapping's `if ict not in ict_names: raise` dropped.
- the caricature: within_population's `largest > IDENTITY_LIMIT` made `largest > 10 * IDENTITY_LIMIT` (woman_stair's
  4.6 passes; seen red 2026-11-25).
- the cornea: dome's `np.maximum(radius + TEAR_FILM_M, reach)` made `radius + TEAR_FILM_M` (no dome over the iris;
  seen red 2026-11-25).
- the skin's tile: periodic's `return values - ...` made `return values` (the tile's edges jump by the slope; seen
  red 2026-11-26).
- the adult's proportions: adult_moves' `longer = max(0.0, ...)` made the bare difference (an adult's face is
  moved; seen red 2026-11-26).
- the region channels: blender_face's TONES with "lids" and "sheen" swapped (seen red 2026-11-26).
- the waterline: eyeball_gap's `- np.median(...)` made `+` (seen red 2026-11-26).
- the brow's edge: thinned's `(0.25 + 0.75 * lower) * tail` made `tail` (a ruled lower edge; seen red 2026-11-26).
- the eye's film: cornea's `> LIMBUS_UV` made `> 1.0` (all glass; seen red 2026-11-26).
- the skin's own crevices: face_skin_light's crevices `"own": True` dropped (seen red 2026-11-26); and, apart,
  READER_KEYS without "hair" (the lashes' melanin never reaches the record: they drew brown, round 2; seen red
  2026-11-26).
- the scanned finish: written's `entry["licence"] = ...` dropped (the scan's bytes go out with no credit; seen red
  2026-11-26); and, apart, the `"carried": True` dropped from its made_with (seen red 2026-11-26).
"""
import json
import pathlib
import tempfile
import sys

import numpy as np
import pytest
import trimesh

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import expressions  # noqa: E402
import face  # noqa: E402
import finishes  # noqa: E402
import fit  # noqa: E402
import skin_scan  # noqa: E402
import strands  # noqa: E402

ICT_NAMES = sorted({name for weights in expressions.ICT_OF.values() for name in weights})
# MHR's controls with no ICT counterpart, which move the face by the body's own offsets (expressions.py).
BODY_MOVED = {"cheekSuck_L", "cheekSuck_R", "lipTightener_L", "lipTightener_R", "nasolabialFurrow_L",
              "nasolabialFurrow_R", "nostrilCompressor_L", "nostrilCompressor_R", "nostrilDilator_L",
              "nostrilDilator_R"}


def shut_skin():
    """The fixture's joined skin: every edge shared by exactly two triangles, once each way, and the cut's border
    within one body edge of the face's all the way round."""
    body = trimesh.creation.icosphere(subdivisions=4, radius=0.1)
    finer = trimesh.creation.icosphere(subdivisions=5, radius=0.1)
    cap = np.flatnonzero(finer.vertices[:, 2] > 0.06)
    inside = np.isin(finer.faces, cap).all(axis=1)
    used, renumbered = np.unique(finer.faces[inside], return_inverse=True)
    face_points, face_triangles = finer.vertices[used], renumbered.reshape(-1, 3)
    loop = fit.border_loop(face_triangles)
    centre = np.zeros(3)
    kept, strip, face_loop, body_loop = fit.seam(body.vertices, body.faces, face_points, face_triangles, loop, centre,
                                                 np.zeros(len(body.vertices), dtype=bool))
    skin = fit.joined_skin(body.vertices, kept, strip, face_points, face_triangles, centre)
    directed = np.vstack([skin[:, [0, 1]], skin[:, [1, 2]], skin[:, [2, 0]]])
    _, undirected = np.unique(np.sort(directed, axis=1), axis=0, return_counts=True)
    _, each_way = np.unique(directed, axis=0, return_counts=True)
    body_edge = np.linalg.norm(body.vertices[body.edges_unique[:, 0]] - body.vertices[body.edges_unique[:, 1]],
                               axis=1).max()
    apart = np.linalg.norm(face_points[face_loop][:, None] - body.vertices[body_loop][None], axis=2).min(axis=1)
    return bool((undirected == 2).all() and (each_way == 1).all() and apart.max() < body_edge)


def join_smooth():
    """The fixture's join (shut_skin's): the largest turn of a strip triangle from the body's skin under it, under
    SEAM_TURN_DEGREES (no ridge or fold)."""
    body = trimesh.creation.icosphere(subdivisions=4, radius=0.1)
    finer = trimesh.creation.icosphere(subdivisions=5, radius=0.1)
    cap = np.flatnonzero(finer.vertices[:, 2] > 0.06)
    inside = np.isin(finer.faces, cap).all(axis=1)
    used, renumbered = np.unique(finer.faces[inside], return_inverse=True)
    face_points, face_triangles = finer.vertices[used], renumbered.reshape(-1, 3)
    loop = fit.border_loop(face_triangles)
    kept, strip, _, _ = fit.seam(body.vertices, body.faces, face_points, face_triangles, loop, np.zeros(3),
                                 np.zeros(len(body.vertices), dtype=bool))
    points = np.vstack([body.vertices, face_points])
    turns = fit.seam_turns(points, fit.outward(strip, points, np.zeros(3)), body, np.array([], dtype=int))
    return bool(turns.max() < fit.SEAM_TURN_DEGREES)


def ridges_judged():
    """A strip of the skin's own triangles passes seam_smooth; the same turned over (a fold) and with a corner lifted
    1 cm off the skin (a ridge) are refused."""
    skin = trimesh.creation.icosphere(subdivisions=4, radius=0.1)
    strip = skin.faces[skin.triangles_center[:, 2] > 0.09]
    lifted = skin.vertices.copy()
    lifted[strip[0, 0]] *= 1.1
    judged = []
    for points, triangles in ((skin.vertices, strip), (skin.vertices, strip[:, ::-1]), (lifted, strip)):
        try:
            fit.seam_smooth(fit.seam_turns(points, triangles, skin, np.array([], dtype=int)))
            judged.append("passes")
        except RuntimeError:
            judged.append("refused")
    return judged


def neck_judged():
    """A neck as a cylinder round the Neck1 to Head line, its front drawn furthest back at 1.36 m (the notch): 53 mm
    in radius (her 334 mm girth) with the chin 110 mm from the notch passes neck_normal for a 1.668 m person; one 75
    mm in radius (too thick) and one whose chin stands 196 mm off the notch (too long) are refused; with each girth and
    length (mm, rounded)."""
    neck, head, height = np.array([0.0, 1.383, 0.0]), np.array([0.0, 1.507, 0.0]), 1.668
    judged = []
    for radius, chin_y in ((0.053, 1.46), (0.075, 1.46), (0.053, 1.55)):
        tube = trimesh.creation.cylinder(radius=radius, height=0.3, sections=96)
        tube = trimesh.Trimesh(*trimesh.remesh.subdivide_to_size(tube.vertices, tube.faces, max_edge=0.004))
        tube.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1.0, 0.0, 0.0]))
        tube.apply_translation([0.0, 1.43, 0.0])
        front = tube.vertices[:, 2] > 0.0
        tube.vertices[front, 2] *= 1.0 + 10.0 * (tube.vertices[front, 1] - 1.36) ** 2
        chin = np.array([0.0, chin_y, 0.1])
        measured = fit.neck_measures(tube, neck, head, chin, height)
        try:
            fit.neck_normal(measured)
            judged.append("passes")
        except RuntimeError:
            judged.append("refused")
        judged += [round(measured["girth_mm"]), round(measured["length_mm"])]
    return judged


def throat_on_skin():
    """A cap standing 8 mm off the head (ICT's throat stood so off SOMA's), its lower half given a throat share of 1:
    laid by throat_laid, those points lie on the skin (under 0.5 mm off, mm rounded to tenths) and the rest keep
    their place."""
    head = trimesh.creation.icosphere(subdivisions=4, radius=0.1)
    cap = trimesh.creation.icosphere(subdivisions=4, radius=0.108).vertices
    cap = cap[cap[:, 2] > 0.06]
    throat = (cap[:, 1] < 0.0).astype(float)
    laid = fit.throat_laid(cap, throat, head)
    _, apart, _ = trimesh.proximity.closest_point(head, laid[throat == 1.0])
    return [bool(apart.max() < 0.0005), bool(np.allclose(laid[throat == 0.0], cap[throat == 0.0]))]


def border_on_skin():
    """A face standing 1 cm off the head, laid on it: its border's largest distance off the skin, in mm, and whether
    its middle (past the blend) kept its place."""
    head = trimesh.creation.icosphere(subdivisions=4, radius=0.1)
    finer = trimesh.creation.icosphere(subdivisions=5, radius=0.11)
    cap = np.flatnonzero(finer.vertices[:, 2] > 0.04)
    inside = np.isin(finer.faces, cap).all(axis=1)
    used, renumbered = np.unique(finer.faces[inside], return_inverse=True)
    face_points, face_triangles = finer.vertices[used], renumbered.reshape(-1, 3)
    loop = fit.border_loop(face_triangles)
    padded = np.vstack([face_points, np.zeros((fit.ict.PIECES["face"][1] + 1 - len(face_points), 3))])
    laid, share = fit.laid_on_skin(padded, face_triangles, loop, head)
    _, distance, _ = trimesh.proximity.closest_point(head, laid[loop])
    middle = np.flatnonzero(share[:len(face_points)] == 0.0)
    return [round(float(distance.max()) * 1000, 3), bool(len(middle)) and bool(np.allclose(laid[middle],
                                                                                           face_points[middle]))]


def ear_kept():
    """A bump standing 15 mm off the head inside the band (an ear), laid on the skin with the rest of the face: its
    height off the head after, in mm, stays above 10."""
    head = trimesh.creation.icosphere(subdivisions=4, radius=0.1)
    finer = trimesh.creation.icosphere(subdivisions=5, radius=0.1)
    cap = np.flatnonzero(finer.vertices[:, 2] > 0.04)
    inside = np.isin(finer.faces, cap).all(axis=1)
    used, renumbered = np.unique(finer.faces[inside], return_inverse=True)
    face_points, face_triangles = finer.vertices[used].copy(), renumbered.reshape(-1, 3)
    loop = fit.border_loop(face_triangles)
    border_point = face_points[loop[0]]
    inward = np.array([0.0, 0.0, 0.1]) - border_point
    ear_centre = border_point + 0.01 * inward / np.linalg.norm(inward)
    ear = np.flatnonzero(np.linalg.norm(face_points - ear_centre, axis=1) < 0.006)
    face_points[ear] *= 1.15
    padded = np.vstack([face_points, np.zeros((fit.ict.PIECES["face"][1] + 1 - len(face_points), 3))])
    laid, _ = fit.laid_on_skin(padded, face_triangles, loop, head)
    return bool(np.linalg.norm(laid[ear], axis=1).max() - 0.1 > 0.010)


def ears_judged():
    """A strip standing off a sphere's side as an ear (its root on the skin, the helix's back 6 mm out, its outer edge
    14 mm out) passes ears_standing; the same strip squashed to 15% of its height is refused."""
    head = trimesh.creation.icosphere(subdivisions=4, radius=0.1)
    out = np.array([0.0, 0.003, 0.006, 0.010, 0.014])  # metres off the skin, root to edge
    angles = np.radians(np.linspace(-15.0, 15.0, 7))
    side = np.stack([np.cos(angles), np.sin(angles), np.zeros_like(angles)], axis=1)
    grid = np.arange(len(out) * len(angles)).reshape(len(out), len(angles))
    skin = np.array([triangle for row in range(len(out) - 1) for column in range(len(angles) - 1)
                     for triangle in ([grid[row, column], grid[row + 1, column], grid[row + 1, column + 1]],
                                      [grid[row, column], grid[row + 1, column + 1], grid[row, column + 1]])])
    ear_list = [(grid[2], grid[0])]
    judged = []
    for squash in (1.0, 0.15):
        points = np.vstack([side * (0.1 + height * squash) + [0.0, 0.0, -0.002 * row]
                            for row, height in enumerate(out)])
        try:
            fit.ears_standing(fit.ear_measures(points, ear_list, skin, head))
            judged.append("passes")
        except RuntimeError:
            judged.append("refused")
    return judged


def brows_grown():
    """One brow grown on a sphere's front along a line (head by the middle, tail outward): its hairs on the skin and
    none in it, the head's hairs pointing up, the tail's outward and down, and every point moved by the skin's own
    offsets."""
    skin = trimesh.creation.icosphere(subdivisions=4, radius=0.1)
    line = np.array([[0.01 + 0.01 * step, 0.03, 0.0] for step in range(5)])
    line[:, 2] = np.sqrt(0.1 ** 2 - line[:, 0] ** 2 - line[:, 1] ** 2)
    offsets = np.tile([0.0, -0.002, 0.0], (1, len(skin.vertices), 1))
    counts, points, _, shapes = strands.brow_strands(skin, offsets, line, np.array([0.0, 1.0, 0.0]),
                                                     np.random.default_rng(1))
    measures = strands.checked(counts, points, skin)
    hairs = points.reshape(len(counts), -1, 3)
    heading = hairs[:, -1] - hairs[:, 0]
    head, tail = hairs[:, 0, 0] < 0.014, hairs[:, 0, 0] > 0.046
    return [measures["strands"] == strands.BROW_HAIRS, bool((heading[head, 1] > np.abs(heading[head, 0])).mean() > 0.7),
            bool(heading[tail, 0].mean() > 0 and heading[tail, 1].mean() < 0),
            bool(np.allclose(shapes, [0.0, -0.002, 0.0]))]


def lashes_curled():
    """A lash on a card standing straight out of a lid curls up off an upper lid, down off a lower, and turns with its
    card when the card turns down (a blink)."""
    card = np.array([[0.0, 0.0, 0.0], [0.01, 0.0, 0.0], [0.005, 0.0, 0.005]])  # flat, standing out along +z
    places = ((np.array([0, 1, 2]), np.array([0.5, 0.5, 0.0])), (np.array([0, 1, 2]), np.array([0.25, 0.25, 0.5])))
    upper = strands.lash_line(*strands.lash_frame(card, *places, 1.0), 0.01, 0.35)
    lower = strands.lash_line(*strands.lash_frame(card, *places, -1.0), 0.01, 0.2)
    blink = np.radians(70.0)  # the card's out turned 70 degrees down
    turn = np.array([[1.0, 0.0, 0.0], [0.0, np.cos(blink), -np.sin(blink)], [0.0, np.sin(blink), np.cos(blink)]])
    closed = strands.lash_line(*strands.lash_frame(card @ turn.T, *places, 1.0), 0.01, 0.35)
    return [bool(upper[-1, 1] > upper[0, 1] + 0.003), bool(lower[-1, 1] < lower[0, 1] - 0.0015),
            bool(closed[-1, 1] < closed[0, 1] - 0.006)]


def skin_under_the_face():
    """The body points near the face's border that inside_border cuts: all under the face, none beside it."""
    body = trimesh.creation.icosphere(subdivisions=4, radius=0.1)
    finer = trimesh.creation.icosphere(subdivisions=5, radius=0.1)
    cap = np.flatnonzero(finer.vertices[:, 2] > 0.06)
    inside = np.isin(finer.faces, cap).all(axis=1)
    used, renumbered = np.unique(finer.faces[inside], return_inverse=True)
    face_points, face_triangles = finer.vertices[used], renumbered.reshape(-1, 3)
    loop = fit.border_loop(face_triangles)
    cut = fit.inside_border(body.vertices, face_points, face_triangles, loop)
    height = body.vertices[:, 2]
    rim = face_points[loop][:, 2].min()
    return [bool(cut.any()), bool((height[cut] > rim - 0.001).all()),
            bool(cut[(height > rim + 0.004) & (height < rim + 0.012)].all())]


def shares():
    """The body's share on the border, halfway in and past the blend."""
    return [round(float(share), 6) for share in fit.body_share(np.array([0.0, fit.BLEND_METRES / 2,
                                                                         fit.BLEND_METRES * 1.5]))]


def controls_moving_the_face():
    """Every MHR control moves the face: those mapped through ICT, and the rest by the body's own offsets."""
    matrix = expressions.mapping(ICT_NAMES)
    unmapped = {name for name, row in zip(expressions.MHR_EXPRESSIONS, matrix) if not row.any()}
    return len(expressions.MHR_EXPRESSIONS) == 72 and unmapped == BODY_MOVED


def a_missing_name_refused():
    """A mapping onto an ICT set without jawOpen is refused."""
    try:
        expressions.mapping([name for name in ICT_NAMES if name != "jawOpen"])
    except KeyError:
        return True
    return False


def caricature_refused():
    """A face 1.7 standard deviations off the mean passes, one 4.6 off it (woman_stair's at the old pull) is refused."""
    judged = []
    for weights in (np.array([1.7, -0.4]), np.array([0.2, -4.6])):
        try:
            fit.within_population(weights)
            judged.append("passes")
        except RuntimeError:
            judged.append("refused")
    return judged


def cornea_domed():
    """On a 12 mm eye with an iris 11.7 mm across: the cornea's apex about 1.2 mm out from the eye's sphere, the iris's
    edge on the sphere (under its tear film) and the side of the eye the sphere's own (mm, rounded)."""
    radius, limbus, axis = 0.012, 0.00585, np.array([0.0, 0.0, 1.0])
    edge = np.arcsin(limbus / radius)
    directions = np.array([axis, [np.sin(edge), 0.0, np.cos(edge)], [1.0, 0.0, 0.0]])
    return [round(float(reach - radius) * 1000.0, 1) for reach in face.dome(directions, axis, radius, limbus)]


def tile_repeats():
    """A sloped, speckled square's periodic part: the jump across its wrapped edges no larger than a step inside it
    (the square's own jump is the slope's 0.5), and its speckle kept (most of its spread across a row)."""
    rows = np.random.default_rng(7).normal(0.0, 0.02, (64, 64))
    square = rows + np.linspace(0.0, 0.5, 64)[None, :]
    made = skin_scan.periodic(square)
    inside = np.abs(np.diff(made, axis=1)).max()
    across = np.abs(made[:, 0] - made[:, -1]).max()
    return [bool(across <= inside), bool(made[10].std() > 0.5 * rows[10].std())]


def scanned_listed():
    """The skin finish's take-in listing with stand-in tiles: the tiles among its files, the scan named as carried,
    and its licence block the scan's CC BY 3.0 with the credit."""
    from PIL import Image

    def stand_in(folder):
        for name in ("skin_detail_colour.png", "skin_detail_height.png"):
            Image.new("L", (4, 4), 128).save(pathlib.Path(folder) / name)
        return {"colour": "skin_detail_colour.png", "height": "skin_detail_height.png", "tile_m": 0.04}

    real = finishes.skin_scan.tiles
    finishes.skin_scan.tiles = stand_in
    try:
        with tempfile.TemporaryDirectory() as folder:
            listing = json.loads(finishes.written(folder, "test").read_text())
    finally:
        finishes.skin_scan.tiles = real
    skin = next(entry for entry in listing["entries"] if entry["id"] == "face_skin_light")
    carried = [item for item in skin["made_with"] if item.get("carried")]
    return [sorted(name for name in skin["files"] if name.endswith(".png")),
            [item["source"] for item in carried], skin.get("licence", {}).get("id"),
            skin.get("licence", {}).get("credit") == skin_scan.CREDIT]


def adult_proportions():
    """A short face broad in the jaw (its height 0.79 of its width, its jaw 0.79 of it) has its chin moved down and its
    jaw's angles in towards the middle; a face already at an adult's proportions is not moved (landmarks only, cm)."""
    def face_of(height, jaw):
        marks = np.zeros((68, 3))
        marks[1], marks[15] = [-7.0, 1.5, 0.0], [7.0, 1.5, 0.0]
        marks[27], marks[30], marks[33] = [0.0, 3.0, 2.0], [0.0, -1.0, 3.0], [0.0, -2.0, 2.0]
        marks[8] = [0.0, 3.0 - height, 1.0]
        marks[4], marks[12] = [-jaw / 2.0, -4.5, 0.0], [jaw / 2.0, -4.5, 0.0]
        return marks
    short = fit.adult_moves(face_of(11.0, 11.0), np.arange(68))
    adult = fit.adult_moves(face_of(12.6, 10.0), np.arange(68))
    return [bool(short[8, 1] < -0.5), bool(short[4, 0] > 0.05 and short[12, 0] < -0.05), float(np.abs(adult).max())]


def tones_agree():
    """The skin's region channels are named in one order where the face marks them (face.TONES) and where they are
    drawn (blender_face.TONES, read from its source: it runs inside Blender)."""
    import ast
    source = ast.parse(pathlib.Path(face.__file__).with_name("blender_face.py").read_text())
    drawn = next(ast.literal_eval(node.value) for node in source.body if isinstance(node, ast.Assign)
                 and getattr(node.targets[0], "id", "") == "TONES")
    return list(drawn) == list(face.TONES)


def waterline_found():
    """A lid's skin 0.5 mm off its eyeball is wet, one 1.5 mm off half so, one 3 mm off dry (cm off the sphere of the
    eyeball piece's points, ICT's own layout)."""
    import ict
    model = {"neutral": np.zeros((ict.PIECES["eyeball_right"][1] + 1, 3))}
    for eye, side in (("left", 1.0), ("right", -1.0)):
        first, last = ict.PIECES[f"eyeball_{eye}"]
        ball = trimesh.creation.icosphere(subdivisions=3, radius=1.2).vertices
        model["neutral"][first:last + 1] = ball[np.arange(last + 1 - first) % len(ball)] + [3.2 * side, 3.6, 8.4]
    lid = np.array([[3.2, 3.6, 8.4 + 1.2 + gap] for gap in (0.05, 0.15, 0.3)])
    gaps = face.eyeball_gap(model, lid)
    return [round(float(value), 1) for value in
            np.clip((face.WET_CM[1] - gaps) / (face.WET_CM[1] - face.WET_CM[0]), 0.0, 1.0)]


def brows_thinned():
    """The brow's hairs kept fewer at its lower edge than in its middle (a soft edge) and fewer at its tail's end than
    where the tail starts (a tapering tail)."""
    kept = strands.thinned(np.array([0.5, 0.5, 0.7, 1.0]), np.array([-1.0, 0.5, 0.0, 0.0]))
    return [bool(kept[0] < 0.5 * kept[1]), bool(kept[3] < 0.5 * kept[2])]


def eye_film_split():
    """The clear shell over an eye: its middle wears the cornea's glass (finish 0), its part over the white past the
    limbus the thin tear film (finish 1)."""
    ball = trimesh.creation.icosphere(subdivisions=4, radius=0.012)
    direction = ball.vertices / 0.012
    angle = np.arccos(np.clip(direction[:, 2], -1.0, 1.0))
    around = direction[:, :2] / np.maximum(np.linalg.norm(direction[:, :2], axis=1, keepdims=True), 1e-9)
    uv = 0.5 + around * (angle * face.IRIS_UV / np.arcsin(0.00585 / 0.012))[:, None]  # the iris ring 11.7 mm across
    eyes = {"points": np.vstack([ball.vertices, ball.vertices + [0.06, 0.0, 0.0]]),
            "triangles": np.vstack([ball.faces, ball.faces + len(ball.vertices)])}
    eyes["uv"] = np.vstack([uv, uv])[eyes["triangles"]]
    eyes["shapes"] = np.zeros((1, len(eyes["points"]), 3))
    shell = face.cornea(eyes)
    centres = shell["points"][shell["triangles"]].mean(axis=1)
    middle = np.linalg.norm(centres[:, :2], axis=1).argmin()
    white = np.abs(np.arccos(np.clip(centres[:, 2] / np.linalg.norm(centres, axis=1), -1.0, 1.0))
                   - np.radians(50.0)).argmin()
    return [int(shell["finish"][middle]), int(shell["finish"][white]), bool(0 < shell["finish"].mean() < 1)]


def own_crevices():
    """The skin finishes darken their crevices by their own closeness only (`own`), the tear film over the white is
    thin, bending no light, and the lashes' and brows' records carry their fibre's melanin (`hair`) for the strands'
    shader."""
    from PIL import Image

    def stand_in(folder):
        for name in ("skin_detail_colour.png", "skin_detail_height.png"):
            Image.new("L", (4, 4), 128).save(pathlib.Path(folder) / name)
        return {"colour": "skin_detail_colour.png", "height": "skin_detail_height.png", "tile_m": 0.04}

    real = finishes.skin_scan.tiles
    finishes.skin_scan.tiles = stand_in
    try:
        with tempfile.TemporaryDirectory() as folder:
            finishes.written(folder, "test")
            records = {name: json.loads((pathlib.Path(folder) / name / "surface.json").read_text())
                       for name in ("face_skin_light", "face_skin_dark", "face_eye_film", "face_lash_dark",
                                    "face_brow_brown")}
    finally:
        finishes.skin_scan.tiles = real
    return [records["face_skin_light"]["crevices"].get("own"), records["face_skin_dark"]["crevices"].get("own"),
            records["face_eye_film"]["transmission"].get("thin"),
            records["face_lash_dark"].get("hair", {}).get("melanin", 0.0) > 0.99,
            records["face_brow_brown"].get("hair", {}).get("melanin", 0.0) > 0.8]


@pytest.mark.parametrize("case, made, wanted", [
    ("the face's border, the cut and the strip are one shut skin", shut_skin, True),
    ("the join lies on the skin: no strip triangle stands as a ridge or folds", join_smooth, True),
    ("a join lying on the skin passes, a fold or a ridge on it is refused", ridges_judged,
     ["passes", "refused", "refused"]),
    ("a neck in the normal range for the height passes, a thick or long one is refused", neck_judged,
     ["passes", 335, 109, "refused", 474, 101, "refused", 335, 194]),
    ("the throat lies on the body's skin, the face above it keeps its place", throat_on_skin, [True, True]),
    ("the body's skin shapes the face fully on the border and not past the blend", shares, [1.0, 0.5, 0.0]),
    ("a face standing off the head is laid on it at its border and keeps its middle", border_on_skin, [0.0, True]),
    ("an ear standing off the head inside the band keeps its height", ear_kept, True),
    ("an ear standing off the head passes, one squashed onto it is refused", ears_judged, ["passes", "refused"]),
    ("brow hairs lie on the skin, up at the head, outward and down at the tail, moved by the skin", brows_grown,
     [True, True, True, True]),
    ("a lash curls up off an upper lid, down off a lower, and turns down with its card", lashes_curled,
     [True, True, True]),
    ("the skin under the face near its border is cut, the skin beside it kept", skin_under_the_face,
     [True, True, True]),
    ("every one of MHR's 72 controls moves the face", controls_moving_the_face, True),
    ("a mapping onto an expression ICT lacks is refused", a_missing_name_refused, True),
    ("a caricature's identity is refused, a person's passes", caricature_refused, ["passes", "refused"]),
    ("the cornea rises over the iris and meets the eye at its edge", cornea_domed, [1.2, 0.1, 0.1]),
    ("the photographed skin's tile repeats with no seam and keeps its speckle", tile_repeats, [True, True]),
    ("the scanned skin finish carries the scan's tiles under its licence and credit", scanned_listed,
     [["skin_detail_colour.png", "skin_detail_height.png"], ["infinite_head_scan"], "CC-BY-3.0", True]),
    ("a short, broad-jawed face is moved to an adult's proportions, an adult's is not", adult_proportions,
     [True, True, 0.0]),
    ("the skin's region channels are one order where marked and where drawn", tones_agree, True),
    ("a lid's skin by its eyeball is wet, fading to dry 2 mm off", waterline_found, [1.0, 0.5, 0.0]),
    ("a brow thins out at its lower edge and its tail", brows_thinned, [True, True]),
    ("the shell over the eye is the cornea's glass in its middle and a thin tear film over the white",
     eye_film_split, [0, 1, True]),
    ("the skin's crevices are its own, the tear film over the white is thin, the lashes and brows have melanin",
     own_crevices, [True, True, True, True, True]),
])
def test_the_face_joins_the_body_as_one_shut_skin_moved_by_every_control(case, made, wanted):
    assert made() == wanted, case
