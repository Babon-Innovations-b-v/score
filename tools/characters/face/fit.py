"""ICT-FaceKit's face fitted onto a SOMA body's head (#226): its identity and pose solved to the body's face, its
border laid on the body's skin, the body's face under it cut away and the two joined into one skin.

Plain numpy, scipy and trimesh. `fitted` takes the body (`body_face.py`'s file) and the packed model (`ict.load`) and
returns the fitted face's points in metres (every piece of the model), the similarity it was laid with and the seam:
the body's triangles kept, the strip joining the face's border to the cut, and each face point's share of the body
(1 on the border, 0 past `BLEND_METRES`), which the expressions use to blend the two.
"""
import heapq

import numpy as np
import trimesh
from scipy.spatial import cKDTree

import ict

ROUNDS = 30
# The identity's pull toward the model's mean, against the mean squared size of its modes: enough to keep a face a
# face where the body's coarser head says little (the body's head is 18,056-point SOMA, the face 26,719 points).
IDENTITY_PULL = 0.02
EYE_WEIGHT = 40.0  # each eye centre's weight against one face point's, so the eyes sit in the body's eye joints
TRIM_METRES = 0.012  # a face point further than this from the body's skin is left out of a round's solve
KEEP_SHARE = 0.9  # and only the nearest share of the rest are taken, so lids and lips that differ do not pull
BLEND_METRES = 0.025  # how far in from the face's border the body's skin still shapes the face
COVER_METRES = 0.015  # a body point is under the face when it lies within this of it and inside its border
CENTRE_BEHIND = 0.08  # the head's centre for the border's projection: this far behind the eyes
CENTRE_BELOW = 0.03  # and this far below them


def eye_centres(points):
    """The two eyeballs' centres (left, right) of a model-topology point array: each eyeball piece's mean point."""
    return np.stack([points[slice(first, last + 1)].mean(axis=0) for first, last in
                     (ict.PIECES["eyeball_left"], ict.PIECES["eyeball_right"])])


def similarity(source, target, weights):
    """The weighted scale, turn and shift taking `source` points onto `target` (Umeyama)."""
    share = weights / weights.sum()
    source_mean, target_mean = share @ source, share @ target
    centred_source, centred_target = source - source_mean, target - target_mean
    covariance = (centred_target * share[:, None]).T @ centred_source
    left, singular, right = np.linalg.svd(covariance)
    sign = np.diag([1.0, 1.0, np.sign(np.linalg.det(left @ right))])
    turn = left @ sign @ right
    scale = np.trace(np.diag(singular) @ sign) / (share @ (centred_source ** 2).sum(axis=1))
    return scale, turn, target_mean - scale * turn @ source_mean


def identity_solve(model, scale, turn, shift, rows, targets, weights):
    """The identity weights placing the model's `rows` points nearest `targets` once laid by the similarity."""
    modes = model["identities"][:, rows, :].astype(np.float64)  # (modes, rows, 3)
    local = ((targets - shift) @ turn) / scale - model["neutral"][rows]
    root = np.sqrt(weights)[:, None]
    matrix = (modes * root[None]).reshape(len(modes), -1).T
    wanted = (local * root).reshape(-1)
    normal = matrix.T @ matrix
    pull = IDENTITY_PULL * np.trace(normal) / len(normal)
    return np.linalg.solve(normal + pull * np.eye(len(normal)), matrix.T @ wanted)


def shaped(model, coefficients):
    """The model's points (model units) with identity weights."""
    return model["neutral"] + np.tensordot(coefficients, model["identities"], axes=1)


def head_mesh(body):
    """The body's head and neck as a trimesh (its triangles with every corner above the shoulders)."""
    above = body["points"][:, 1] > body["joint_LeftEye"][1] - 0.25
    triangles = body["triangles"][above[body["triangles"]].all(axis=1)]
    return trimesh.Trimesh(body["points"], triangles, process=False)


def fit_pose_and_identity(model, body):
    """Solve the face's similarity and identity to the body's head: eyes on the eye joints, the narrow face on the
    body's skin. Returns (scale, turn, shift, identity weights)."""
    head = head_mesh(body)
    eyes = np.stack([body["joint_LeftEye"], body["joint_RightEye"]])
    rows = np.arange(ict.NARROW_FACE + 1)
    eye_rows = [np.arange(first, last + 1) for first, last in (ict.PIECES["eyeball_left"], ict.PIECES["eyeball_right"])]
    coefficients = np.zeros(len(model["identities"]))
    model_eyes = eye_centres(model["neutral"])
    scale = np.linalg.norm(eyes[0] - eyes[1]) / np.linalg.norm(model_eyes[0] - model_eyes[1])
    turn, shift = np.eye(3), eyes.mean(axis=0) - scale * model_eyes.mean(axis=0)
    for _ in range(ROUNDS):
        points = shaped(model, coefficients)
        laid = scale * points[rows] @ turn.T + shift
        nearest, distance, _ = trimesh.proximity.closest_point(head, laid)
        keep = distance < min(TRIM_METRES, np.quantile(distance, KEEP_SHARE))
        source = np.vstack([points[rows][keep], eye_centres(points)])
        target = np.vstack([nearest[keep], eyes])
        weights = np.concatenate([np.ones(keep.sum()), [EYE_WEIGHT * keep.sum() / 1000.0] * 2])
        scale, turn, shift = similarity(source, target, weights)
        coefficients = identity_solve(model, scale, turn, shift, np.concatenate([rows[keep], *eye_rows]),
                                      np.vstack([nearest[keep]] + [np.repeat(eye[None], len(eye_row), axis=0)
                                                                    for eye, eye_row in zip(eyes, eye_rows)]),
                                      np.concatenate([np.ones(keep.sum())] + [np.full(len(eye_row), EYE_WEIGHT /
                                                                                      len(eye_row))
                                                                              for eye_row in eye_rows]))
    return scale, turn, shift, coefficients


def piece_triangles(model, piece):
    """The model's triangles of one piece (every corner within its points)."""
    first, last = ict.PIECES[piece]
    triangles = model["triangles"]
    return triangles[((triangles >= first) & (triangles <= last)).all(axis=1)]


def border_loop(triangles):
    """The longest closed border loop of a triangle set, as point indices in order."""
    edges = np.sort(np.vstack([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]]), axis=1)
    unique, counts = np.unique(edges, axis=0, return_counts=True)
    following = {}
    for triangle in triangles:
        for start, end in ((triangle[0], triangle[1]), (triangle[1], triangle[2]), (triangle[2], triangle[0])):
            following[(start, end)] = True
    single = {tuple(edge) for edge in unique[counts == 1]}
    step = {}
    for start, end in following:
        if (min(start, end), max(start, end)) in single:
            step[start] = end
    loops, seen = [], set()
    for start in step:
        if start in seen:
            continue
        loop, point = [], start
        while point not in seen:
            seen.add(point)
            loop.append(point)
            point = step[point]
        loops.append(loop)
    return np.array(max(loops, key=len))


def graph_distance(points, triangles, sources):
    """Each point's distance along the mesh's edges to the nearest source point, and which source that is."""
    neighbours = [[] for _ in range(len(points))]
    for triangle in triangles:
        for start, end in ((triangle[0], triangle[1]), (triangle[1], triangle[2]), (triangle[2], triangle[0])):
            length = float(np.linalg.norm(points[start] - points[end]))
            neighbours[start].append((end, length))
            neighbours[end].append((start, length))
    distance = np.full(len(points), np.inf)
    nearest = np.full(len(points), -1)
    queue = [(0.0, int(source), int(source)) for source in sources]
    for _, source, _ in queue:
        distance[source], nearest[source] = 0.0, source
    heapq.heapify(queue)
    while queue:
        reached, point, source = heapq.heappop(queue)
        if reached > distance[point]:
            continue
        for neighbour, length in neighbours[point]:
            if reached + length < distance[neighbour]:
                distance[neighbour], nearest[neighbour] = reached + length, source
                heapq.heappush(queue, (reached + length, neighbour, source))
    return distance, nearest


def body_share(distance):
    """How much of the body's skin shapes a face point at a distance in from the border: 1 on it, 0 past
    BLEND_METRES, smooth between."""
    along = np.clip(1.0 - distance / BLEND_METRES, 0.0, 1.0)
    return along * along * (3.0 - 2.0 * along)


def laid_on_skin(points, face_triangles, loop, head):
    """The face's points with its border put on the body's skin and the move faded inward; the face points' share
    of the body. Points of other pieces move with their nearest face point."""
    snapped, _, _ = trimesh.proximity.closest_point(head, points[loop])
    move = np.zeros_like(points)
    move[loop] = snapped - points[loop]
    face_count = ict.PIECES["face"][1] + 1
    distance, nearest = graph_distance(points[:face_count], face_triangles, loop)
    share = body_share(distance)
    move[:face_count] = move[nearest] * share[:, None]
    rest = np.arange(face_count, len(points))
    _, owner = cKDTree(points[:face_count]).query(points[rest])
    move[rest] = move[owner]
    return points + move, share


def head_centre(body):
    """The point the face's border is projected from: inside the head, behind and below the eyes."""
    eyes = (body["joint_LeftEye"] + body["joint_RightEye"]) / 2.0
    return eyes + [0.0, -CENTRE_BELOW, -CENTRE_BEHIND]


def directions(points, centre):
    """Points as (around, up) angles seen from the centre, the face looking along +z."""
    offset = points - centre
    return np.stack([np.arctan2(offset[:, 0], offset[:, 2]),
                     np.arctan2(offset[:, 1], np.hypot(offset[:, 0], offset[:, 2]))], axis=1)


def inside_polygon(points, polygon):
    """Whether each 2D point lies inside a closed 2D polygon (even-odd rule)."""
    inside = np.zeros(len(points), dtype=bool)
    start = polygon
    end = np.roll(polygon, -1, axis=0)
    for (x_start, y_start), (x_end, y_end) in zip(start, end):
        crosses = (y_start > points[:, 1]) != (y_end > points[:, 1])
        at = (x_end - x_start) * (points[:, 1] - y_start) / np.where(y_end == y_start, 1e-12, y_end - y_start) + x_start
        inside ^= crosses & (points[:, 0] < at)
    return inside


def covered(body_points, face_points, face_triangles, loop, centre):
    """Which body points lie under the laid face: inside its border seen from the head's centre and near it."""
    polygon = directions(face_points[loop], centre)
    within = inside_polygon(directions(body_points, centre), polygon)
    face = trimesh.Trimesh(face_points, face_triangles, process=False)
    candidates = np.flatnonzero(within)
    _, distance, _ = trimesh.proximity.closest_point(face, body_points[candidates])
    under = np.zeros(len(body_points), dtype=bool)
    under[candidates[distance < COVER_METRES]] = True
    return under


def kept_body(triangles, under):
    """The body's triangles left once every triangle touching a covered point is cut, and islands cut off by it
    (only the largest connected part of the body is kept)."""
    kept = triangles[~under[triangles].any(axis=1)]
    parts = trimesh.graph.connected_components(np.vstack([kept[:, [0, 1]], kept[:, [1, 2]]]), min_len=1)
    largest = set(max(parts, key=len).tolist())
    return kept[np.array([triangle[0] in largest for triangle in kept])]


def zipper(outer, inner, outer_points, inner_points):
    """Triangles joining two closed loops of point indices (both in one numbering) running the same way round:
    walk both, each step advancing the loop whose next edge makes the shorter diagonal."""
    start = int(np.argmin(np.linalg.norm(inner_points - outer_points[0], axis=1)))
    inner = np.roll(inner, -start)
    inner_points = np.roll(inner_points, -start, axis=0)
    triangles, at_outer, at_inner = [], 0, 0
    count_outer, count_inner = len(outer), len(inner)
    while at_outer < count_outer or at_inner < count_inner:
        next_outer, next_inner = (at_outer + 1) % count_outer, (at_inner + 1) % count_inner
        advance_outer = at_inner >= count_inner or (at_outer < count_outer and
                                                    np.linalg.norm(outer_points[next_outer] - inner_points[at_inner % count_inner]) <=
                                                    np.linalg.norm(inner_points[next_inner] - outer_points[at_outer % count_outer]))
        if advance_outer:
            triangles.append([outer[at_outer % count_outer], outer[next_outer], inner[at_inner % count_inner]])
            at_outer += 1
        else:
            triangles.append([outer[at_outer % count_outer], inner[next_inner], inner[at_inner % count_inner]])
            at_inner += 1
    return np.array(triangles)


def same_way(loop, points, centre):
    """The loop turned to run anticlockwise as seen from the head's centre's (around, up) angles."""
    flat = directions(points[loop], centre)
    area = np.sum(flat[:, 0] * np.roll(flat[:, 1], -1) - np.roll(flat[:, 0], -1) * flat[:, 1])
    return loop if area > 0 else loop[::-1]


def seam(body_points, body_triangles, face_points, face_triangles, loop, centre):
    """The body cut under the face and the strip joining the cut to the face's border: (the body's kept triangles,
    the strip in one numbering, body points first and the face's after them, the face's loop, the cut's loop)."""
    under = covered(body_points, face_points, face_triangles, loop, centre)
    kept = kept_body(body_triangles, under)
    face_loop = same_way(loop, face_points, centre)
    body_loop = same_way(border_loop(kept), body_points, centre)
    strip = zipper(face_loop + len(body_points), body_loop, face_points[face_loop], body_points[body_loop])
    return kept, strip, face_loop, body_loop


def joined_skin(body_points, kept, strip, face_points, face_triangles, centre):
    """One skin's triangles (body points first, the face's after them): the kept body, the strip and the face, the
    strip and the face turned to face out from the head's centre as the body does."""
    points = np.vstack([body_points, face_points])
    return np.vstack([kept, outward(strip, points, centre), outward(face_triangles + len(body_points), points, centre)])


def outward(triangles, points, centre):
    """The triangles turned so most face away from the centre (a strip or a piece laid the wrong way round)."""
    corners = points[triangles]
    normal = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    facing = np.einsum("td,td->t", normal, corners.mean(axis=1) - centre)
    return triangles if np.sum(facing > 0) >= len(triangles) / 2 else triangles[:, ::-1]


def fitted(body, model):
    """The face laid on the body: every model point in metres, the similarity and identity, the face's share of the
    body per face point, the body's kept triangles and the strip joining them (strip indices: body points first,
    then the model's points offset by the body's count)."""
    scale, turn, shift, coefficients = fit_pose_and_identity(model, body)
    points = scale * shaped(model, coefficients) @ turn.T + shift
    face_triangles = piece_triangles(model, "face")
    loop = border_loop(face_triangles)
    points, share = laid_on_skin(points, face_triangles, loop, head_mesh(body))
    kept, strip, face_loop, body_loop = seam(body["points"], body["triangles"], points, face_triangles, loop,
                                             head_centre(body))
    return {"points": points, "scale": scale, "turn": turn, "shift": shift, "identity": coefficients,
            "share": share, "kept": kept, "strip": strip, "face_loop": face_loop, "body_loop": body_loop}
