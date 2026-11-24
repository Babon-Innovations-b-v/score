"""How cleanly a model's finishes meet (#159, owner 2026-11-23: "table and toaster mesh became messy compared to run
1"): a finish given triangle by triangle on TRELLIS.2's small uneven triangles meets its neighbour in a sawtooth and
leaves specks of itself inside another, where run 1's painted picture met in smooth lines. Read on the welded mesh:

- `edge_density`: how much finish edge there is, read where finishes meet on one piece or two (NVIDIA's finishes are
  mostly pieces of their own, meeting at no shared edge): the share of points drawn on the surface that lie within
  REACH of the diagonal of a point of another finish, over two reaches, is the edges' length times the diagonal over
  the area. A jagged edge is longer than the line it stands for and every speck adds its rim; held against NVIDIA's.
- `edge_wander`: how far the finish edges (each edge two faces of different finish hold) wander from a smoothed copy
  of themselves, on the surface: each run of them between two meeting points drawn evenly and fitted by a parabola
  over WINDOW of the diagonal behind, about and ahead of each point, each point's distance from the nearest fit across
  the edge within its faces (the surface's own bend under a line going round a corner of the model is no wander), the
  mean over WINDOW. A straight, curving or cornered edge keeps to one of its fits, a sawtooth to none.
- `specks`, `speck_share`: the islands of one finish (faces of one finish joined through shared edges) that meet
  another finish and are under SPECK of the diagonal squared and under SPECK_TRIANGLES of the model's median triangle
  in area, how many and their share of the area: a triangle or two given another finish, where a detail NVIDIA
  modelled in a finish of its own (a sticker on a rack, 0.5 to 33 cm2) is cut in tens of its triangles. Given the
  faces the made model's look draws (`face_seen`, #159), only the specks it draws on at least one pixel count: tc5r's
  surgical chair counted 112, of which 98 lay where its look shows nothing (inside its seat mechanism, under its seat
  and inside its wheels) while its look read clean; a model with no look (NVIDIA's own) counts every one.
"""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.signal import savgol_coeffs
from scipy.spatial import cKDTree

from . import _mesh

WINDOW = 0.02  # the share of the diagonal a finish edge is smoothed over
RUN_LEAST = 4  # windows a run of finish edges is long at least to be smoothed
SAMPLES = 20  # points a finish edge is drawn at per WINDOW
SPECK = 0.02  # an island of one finish under (SPECK x the diagonal) squared ...
SPECK_TRIANGLES = 8  # ... and under this many of the model's median triangle in area is a speck
DENSITY_POINTS = 200000  # surface points the finish edges' length is read off
REACH = 0.01  # the share of the diagonal a point lies within another finish's to stand at a finish edge


def held_edges(faces):
    """(each edge two faces hold, as its two corners in order; those two faces): an edge one face holds is a rim and
    one more than two hold neither, so no meeting of two finishes."""
    directed = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    owner = np.tile(np.arange(len(faces)), 3)
    keys = np.sort(directed, axis=1)
    order = np.lexsort((keys[:, 1], keys[:, 0]))
    keys, owner = keys[order], owner[order]
    starts = np.flatnonzero(np.r_[True, (keys[1:] != keys[:-1]).any(1)])
    twice = starts[np.diff(np.r_[starts, len(keys)]) == 2]
    return keys[twice], np.stack([owner[twice], owner[twice + 1]], 1)


def runs(edges):
    """Each run of finish edges between two meeting points (a corner where other than two finish edges meet), or each
    closed loop: a list of corner indices in order (a loop's first corner repeated at its end)."""
    neighbours = {}
    for first, second in edges.tolist():
        neighbours.setdefault(first, []).append(second)
        neighbours.setdefault(second, []).append(first)
    used, found = set(), []

    def walk(start, step):
        line = [start, step]
        used.add((min(start, step), max(start, step)))
        while len(neighbours[line[-1]]) == 2 and line[-1] != start:
            ahead = [corner for corner in neighbours[line[-1]]
                     if (min(line[-1], corner), max(line[-1], corner)) not in used]
            if not ahead:
                break
            used.add((min(line[-1], ahead[0]), max(line[-1], ahead[0])))
            line.append(ahead[0])
        return line
    for start in [corner for corner, held in neighbours.items() if len(held) != 2] + list(neighbours):
        for step in neighbours[start]:
            if (min(start, step), max(start, step)) not in used:
                found.append(walk(start, step))
    return found


def fitted(even, closed):
    """The evenly drawn run fitted about each point by a parabola over the SAMPLES + 1 points behind it, about it
    and ahead of it (Savitzky-Golay, three copies; NaN where an open run has not that many), so a run's own curve (round
    a tube, a knob's rim) and its own corners (a label's, a carton flap's) are kept by one of them and only wander is
    lost; a closed run wraps round."""
    count, copies = len(even), []
    for place in (0, SAMPLES // 2, SAMPLES):
        taken = np.arange(count)[:, None] - place + np.arange(SAMPLES + 1)[None, :]
        weights = savgol_coeffs(SAMPLES + 1, 2, pos=place, use="dot")
        if closed:
            copies.append(np.einsum("k,nkd->nd", weights, even[taken % count]))
            continue
        whole = (taken.min(1) >= 0) & (taken.max(1) < count)
        copy = np.full_like(even, np.nan)
        copy[whole] = np.einsum("k,nkd->nd", weights, even[taken[whole]])
        copies.append(copy)
    return copies


def drawn(points, closed, window):
    """(the run drawn evenly along its length, SAMPLES points a `window`, the segment each point lies on)."""
    along = np.r_[0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    count = max(int(np.ceil(along[-1] / window * SAMPLES)), SAMPLES + 1)
    places = np.linspace(0, along[-1], count, endpoint=not closed)
    even = np.stack([np.interp(places, along, points[:, axis]) for axis in range(3)], 1)
    return even, np.clip(np.searchsorted(along, places, side="right") - 1, 0, len(points) - 2)


def wander(corners, lines, normal_of, window):
    """The finish edges' mean distance from their nearest smoothed copy (fitted) across the edge within its faces
    (`normal_of` {(corner, corner): the two faces' summed normal}), over `window`; a run under RUN_LEAST windows long
    (a speck's rim, a button's round) is too short to smooth and is left to the specks."""
    distance, length = 0.0, 0.0
    for line in lines:
        points = corners[line]
        steps = np.diff(points, axis=0)
        span = float(np.linalg.norm(steps, axis=1).sum())
        if span < RUN_LEAST * window:
            continue
        closed = line[0] == line[-1]
        even, segment = drawn(points, closed, window)
        normals = np.array([normal_of[(min(first, second), max(first, second))]
                            for first, second in zip(line[:-1], line[1:])])
        across = np.cross(steps, normals)[segment]
        across /= np.maximum(np.linalg.norm(across, axis=1, keepdims=True), 1e-12)
        apart = np.stack([np.abs(((even - copy) * across).sum(1)) for copy in fitted(even, closed)], 1)
        distance += float(np.nanmin(apart, 1).mean()) * span
        length += span
    return distance / length / window if length else 0.0


def islands(count, pairs, same, area, seen):
    """(the area of each island of one finish that meets another finish, whether any of its faces is `seen`): faces
    joined through the edges where both sides are one finish; a piece of its own, a screw modelled apart, meets none
    and is no speck."""
    kept = pairs[same]
    graph = coo_matrix((np.ones(len(kept)), (kept[:, 0], kept[:, 1])), shape=(count, count))
    _, label = connected_components(graph, directed=False)
    meeting = np.unique(label[pairs[~same]])
    shown = np.bincount(label, weights=seen.astype(float), minlength=count)[meeting] > 0
    return np.bincount(label, weights=area, minlength=count)[meeting], shown


def density(corners, faces, material, diagonal):
    """The finish edges' length times the diagonal over the area (the module docstring), read off DENSITY_POINTS
    points drawn on the surface: each finish's points against the nearest of every other finish's."""
    points, picked = _mesh.sampled(corners, faces, DENSITY_POINTS, seed=7)
    finish = material[picked]
    near = np.zeros(len(points), dtype=bool)
    for one in np.unique(finish):
        asked = np.flatnonzero((finish != one) & ~near)
        if len(asked):
            apart, _ = cKDTree(points[finish == one]).query(points[asked], distance_upper_bound=REACH * diagonal,
                                                            workers=-1)
            near[asked[np.isfinite(apart)]] = True
    return float(near.mean() / (2 * REACH))


def finish_edges(vertices, faces, face_material, face_seen=None):
    """{"edge_density", "edge_wander", "specks", "speck_share"} (the module docstring) of one model's finishes; with
    `face_seen` (each face's pixels in its look), its specks only those the look draws."""
    corners, welded = _mesh.welded(np.asarray(vertices, dtype=float), np.asarray(faces))
    area = _mesh.areas(corners, welded)
    kept = area > 0
    seen = np.ones(len(welded), dtype=bool) if face_seen is None else np.asarray(face_seen) > 0
    welded, area, material, seen = welded[kept], area[kept], np.asarray(face_material)[kept], seen[kept]
    diagonal = _mesh.diagonal(corners)
    edges, pairs = held_edges(welded)
    same = material[pairs[:, 0]] == material[pairs[:, 1]]
    face_normals = _mesh.normals(corners, welded)
    meeting = edges[~same]
    normal_of = dict(zip(map(tuple, meeting.tolist()),
                         (face_normals[pairs[~same, 0]] + face_normals[pairs[~same, 1]]).tolist()))
    small, shown = islands(len(welded), pairs, same, area, seen)
    small = small[(small < min((SPECK * diagonal) ** 2, SPECK_TRIANGLES * float(np.median(area)))) & shown]
    return {"edge_density": round(density(corners, welded, material, diagonal), 4),
            "edge_wander": round(wander(corners, runs(meeting), normal_of, WINDOW * diagonal), 5),
            "specks": int(len(small)), "speck_share": round(float(small.sum() / area.sum()), 5)}
