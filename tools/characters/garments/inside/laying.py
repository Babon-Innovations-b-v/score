"""A garment's box mesh laid round the body before it is sewn, numpy and scipy only: imported by drape.py in Newton's
Python (its inside test the card's winding number) and by the garments test in score's (`winding`, on toy bodies).

GarmentCode lays each panel flat in its place round its own mean body; on another body a panel's points can stand
inside it (woman_stair's tee sleeves' fronts up to 5.7 cm inside her arms, her jeans' fronts 1.7 cm inside her
thighs, 2026-11-25). Moved straight off the skin point nearest them, as an outer layer's points were, such points went
deeper in. Laid here, a point inside the body is first put out through the skin nearest it; one that this leaves
inside (her jeans' front crotch curve laid 3 to 4 cm above her crotch, where the skin nearest it is a thigh's and
past it the other thigh, 2026-11-25) is moved instead the shortest way out along the body's six axes; then every
point is moved the layer's reach further off. A point the laying leaves inside refuses the garment (drape.py), never
sewn.
"""
import numpy as np
from scipy.spatial import cKDTree

INSIDE = 0.5  # a point's winding number past this is inside the body (1 inside a closed surface, 0 outside)
OUT_ROUNDS = 20  # steps of `clear` a point still inside is looked along each axis for the way out
AXES = np.array([[1.0, 0, 0], [-1.0, 0, 0], [0, 1.0, 0], [0, -1.0, 0], [0, 0, 1.0], [0, 0, -1.0]])


def winding(points, skin, faces):
    """Each point's generalized winding number about the body's triangles (Jacobson et al. 2013: the triangles'
    solid angles over 4 pi, Van Oosterom and Strackee's formula): about 1 inside, 0 outside, holes and all. All
    points against all triangles at once: for toy bodies (the card's winding number does the real one)."""
    towards = np.asarray(skin, dtype=float)[np.asarray(faces)][None] - np.asarray(points, dtype=float)[:, None, None]
    lengths = np.linalg.norm(towards, axis=3)
    one, two, three = towards[:, :, 0], towards[:, :, 1], towards[:, :, 2]
    volume = np.sum(one * np.cross(two, three), axis=2)
    below = (lengths[:, :, 0] * lengths[:, :, 1] * lengths[:, :, 2] + np.sum(one * two, axis=2) * lengths[:, :, 2]
             + np.sum(two * three, axis=2) * lengths[:, :, 0] + np.sum(three * one, axis=2) * lengths[:, :, 1])
    return np.arctan2(volume, below).sum(axis=1) / (2.0 * np.pi)


def laid_out(points, skin, reach, clear, inside):
    """A box mesh's points laid off the body (`inside`: points -> which stand inside it, a boolean per point): each
    point inside put `clear` (m) out through the skin point nearest it (along the way from the point to that skin
    point); one that leaves inside moved instead from where it was laid along whichever of the six axes reaches outside
    in the fewest steps of `clear` (at most OUT_ROUNDS, else left where it was laid); then every point moved `reach`
    (m) further from its nearest skin point (an outer garment's panels laid off the skin before it is sewn alone,
    drape.sewn_in_layers), but for one that move takes inside (in a fold of the skin), left where it was."""
    given = np.array(points, dtype=float)
    points = given.copy()
    skin = np.asarray(skin, dtype=float)
    tree = cKDTree(skin)
    inward = np.flatnonzero(inside(points))
    if len(inward):
        distance, nearest = tree.query(points[inward])
        out = (skin[nearest] - points[inward]) / np.maximum(distance, 1e-9)[:, None]
        points[inward] = skin[nearest] + out * clear
        inward = inward[inside(points[inward])]
    if len(inward):
        steps = np.arange(1, OUT_ROUNDS + 1) * clear
        tried = given[inward][:, None, None] + AXES[None, :, None] * steps[None, None, :, None]
        out = ~inside(tried.reshape(-1, 3)).reshape(tried.shape[:3])
        first = np.where(out.any(axis=2), out.argmax(axis=2), OUT_ROUNDS)
        axis = first.argmin(axis=1)
        found = first[np.arange(len(inward)), axis] < OUT_ROUNDS
        points[inward] = given[inward]
        points[inward[found]] = tried[np.flatnonzero(found), axis[found], first[found, axis[found]]]
    distance, nearest = tree.query(points)
    away = (points - skin[nearest]) / np.maximum(distance, 1e-9)[:, None]
    laid = skin[nearest] + away * (distance + max(reach, 0.0))[:, None]
    back = np.flatnonzero(inside(laid))
    laid[back] = points[back]
    return laid
