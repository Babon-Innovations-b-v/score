"""The face joins the body as one shut skin moved by every control (#226): the face's border, the body cut under it and
the strip between them make one skin with no open edge, every triangle turned the same way and the cut within one body
edge of the face's border all round (fit.seam and
fit.joined_skin), the body's skin shapes the face fully on its border and not past the blend (fit.body_share), a face
standing off the head is laid on it at its border and keeps its middle, an ear standing off within the band keeps
its height (fit.laid_on_skin), an ear squashed onto the head is refused and one standing off it passes
(fit.ear_measures, fit.ears_standing), the skin under the face near its border is cut and the skin beside it kept
(fit.inside_border), brow hairs lie on the skin, grow up at the brow's head and outward and down at its tail and move
with the skin (strands.brow_strands, strands.checked), a lash curls up off an upper lid and down off a lower and
turns with its card (strands.lash_frame, strands.lash_line), and
MHR's 72 controls each move the face, through ICT expressions or the body's own offsets, a name ICT lacks refused
(expressions.mapping).

Shapes made here: a coarse sphere for the body's head and a finer sphere's cap for the face, laid on it (one
with a bump for an ear); a strip standing off a sphere for an ear; one card triangle for a lash.

Breaks that turn it red (each applied once and seen red, 2026-11-24):
- the shut skin: zipper's `advance_outer` made `at_outer < count_outer` (the strip walks the face's loop first and
  leaves triangles that cross); and, apart, joined_skin's `outward(strip, ...)` made `strip` (the strip turned
  against the body's skin); and, apart, covered's `blocked[wall(graph, stops)] = True` made
  `blocked[stops[:1]] = True` (no wall along the border: the fill under the face leaks and is refused).
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
"""
import pathlib
import sys

import numpy as np
import pytest
import trimesh

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import expressions  # noqa: E402
import fit  # noqa: E402
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


@pytest.mark.parametrize("case, made, wanted", [
    ("the face's border, the cut and the strip are one shut skin", shut_skin, True),
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
])
def test_the_face_joins_the_body_as_one_shut_skin_moved_by_every_control(case, made, wanted):
    assert made() == wanted, case
