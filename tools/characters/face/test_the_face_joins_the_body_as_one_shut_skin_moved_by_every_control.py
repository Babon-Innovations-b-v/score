"""The face joins the body as one shut skin moved by every control (#226): the face's border, the body cut under it and
the strip between them make one skin with no open edge, every triangle turned the same way and the cut within one body
edge of the face's border all round (fit.seam and
fit.joined_skin), the body's skin shapes the face fully on its border and not past the blend (fit.body_share), a face
standing off the head is laid on it at its border and keeps its middle (fit.laid_on_skin), and
MHR's 72 controls each move the face, through ICT expressions or the body's own offsets, a name ICT lacks refused
(expressions.mapping).

Shapes made here: a coarse sphere for the body's head and a finer sphere's cap for the face, laid on it.

Breaks that turn it red (each applied once and seen red, 2026-11-24):
- the shut skin: zipper's `advance_outer` made `at_outer < count_outer` (the strip walks the face's loop first and
  leaves triangles that cross); and, apart, joined_skin's `outward(strip, ...)` made `strip` (the strip turned
  against the body's skin); and, apart, covered's `blocked[wall(graph, stops)] = True` made
  `blocked[stops[:1]] = True` (no wall along the border: the fill under the face leaks and is refused).
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
    ("every one of MHR's 72 controls moves the face", controls_moving_the_face, True),
    ("a mapping onto an expression ICT lacks is refused", a_missing_name_refused, True),
])
def test_the_face_joins_the_body_as_one_shut_skin_moved_by_every_control(case, made, wanted):
    assert made() == wanted, case
