"""The made model's heading as its route laid it (#192, PRD #159): the bench's other measures set it on the truth by
the best of the cube's 24 axis turns, so a model laid a half turn off (tc4r's desk, its cable hole in the wrong
corner) or a quarter turn off (tc4r's fridge, its glass door on its side) is turned back before anything is held, and
a box-like shape cannot tell front from back. Here the model is held as laid, its up kept, turned only a quarter turn
at a time about the truth's up through the boxes' middles: the truth's surface seen from outside (_mesh.outside, so a
fridge's liner and shelves count for nothing) is held to the made model's own paint nearest it, and the turn whose
paint goes with NVIDIA's look best is its heading.

How well the paint goes with the look is their correlation in Lab, each of the truth's finishes weighted alike (a
0.06% cable hole as much as the desk's top). A correlation, not a colour difference: TRELLIS.2 paints the light of
its picture into its texture, the side it saw lighter, so a colour difference took tc4r's touch terminal, laid right,
for a half turn (40.0 against 46.6 delta E as laid) as firmly as it found the fridge's quarter turn (28.3 against
37.6), while the correlation tells them apart (terminal 0.06 against -0.16; fridge 0.42 against -0.15).
"""
import numpy as np
from scipy.spatial import cKDTree

from . import _finish, _mesh

POINTS = 50000  # truth points on its outside, each held to the made paint nearest it once turned
LEAST_POINTS = 20  # a finish with fewer of the truth's outside points is not counted (a speck carries no heading)
# A turn is the heading only when its correlation beats the model's as laid by more than MARGIN. tc4r's 15 made models
# (#192): the desk by 1.17 (a half turn), the fridge by 0.57 (a quarter); the 13 laid right by 0.04 at most, but the
# touch terminal, whose paint goes with NVIDIA's look at no turn (0.10 at best), by 0.28.
MARGIN = 0.3
# Nor is a heading read where no turn's paint goes with the look by at least FLOOR: the paint says nothing of it (the
# touch terminal, its body painted mid grey for NVIDIA's black). tc4r: the desk 0.80, the fridge 0.42; of the 13 laid
# right 9 at 0.41 to 0.90 as laid, read; the printer box 0.20, the terminal 0.10, the ladder and ceiling light under 0,
# not read.
FLOOR = 0.3
TURNS = (0, 90, 180, 270)


def turned(points, degrees, made_middle, truth_middle):
    """`points` turned `degrees` about +Z through `made_middle`, that middle moved to `truth_middle`."""
    angle = np.radians(degrees)
    turn = np.array([[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]])
    return (points - made_middle) @ turn.T + truth_middle


def finish_weights(finishes):
    """Each point's weight: one over its finish's count, so every finish weighs alike; 0 for a finish with fewer than
    LEAST_POINTS points."""
    names, index, counts = np.unique(finishes, return_inverse=True, return_counts=True)
    return np.where(counts[index] >= LEAST_POINTS, 1.0 / counts[index], 0.0)


def correlation(made_lab, truth_lab, weights):
    """The weighted correlation of two Lab colour sets (each centred on its weighted mean, all three channels as
    one vector); 0 where either has no spread."""
    made_lab = made_lab - np.average(made_lab, axis=0, weights=weights)
    truth_lab = truth_lab - np.average(truth_lab, axis=0, weights=weights)
    spread = np.sqrt((weights[:, None] * made_lab ** 2).sum() * (weights[:, None] * truth_lab ** 2).sum())
    return float((weights[:, None] * made_lab * truth_lab).sum() / spread) if spread > 0 else 0.0


def heading(truth, made):
    """{"heading": the degrees (0, 90 or 180) between the made model's heading as laid and the truth's, left out where
    no turn's paint goes with the look (FLOOR); "turns": each quarter turn's correlation}, or None where the made
    side has no paint (`painted`: {"points", "colour" linear RGB}, its route's own texture) or the truth no look.
    `truth` by finish (by_finish)."""
    painted, look = made.get("painted"), truth.get("face_look")
    if painted is None or look is None or look.get("albedo") is None:
        return None
    points, faces = _mesh.outside_faces(truth["vertices"], truth["faces"], POINTS, seed=4)
    albedo = np.asarray(look["albedo"], dtype=float)[faces]
    known = ~np.isnan(albedo).any(1)
    finishes = np.zeros(len(faces), dtype=np.int64) if truth.get("face_material") is None else \
        np.asarray(truth["face_material"])[faces]
    weights = finish_weights(finishes[known])
    if not known.any() or weights.sum() <= 0:
        return None
    truth_lab = _finish.colour_lab(albedo[known])
    made_lab = _finish.colour_lab(np.asarray(painted["colour"], dtype=float))
    made_points = np.asarray(painted["points"], dtype=float)
    made_middle = (made["vertices"].min(0) + made["vertices"].max(0)) / 2
    truth_middle = (truth["vertices"].min(0) + truth["vertices"].max(0)) / 2
    turns = {}
    for degrees in TURNS:
        _, nearest = cKDTree(turned(made_points, degrees, made_middle, truth_middle)).query(points[known])
        turns[degrees] = round(correlation(made_lab[nearest], truth_lab, weights), 4)
    best = max(TURNS, key=lambda degrees: turns[degrees])
    if turns[best] < FLOOR:
        return {"turns": turns}
    off = best if turns[best] > turns[0] + MARGIN else 0
    return {"heading": min(off, 360 - off), "turns": turns}
