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
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import breadth_first_order, connected_components, dijkstra
from scipy.spatial import cKDTree

import ict

ROUNDS = 30
# The identity's pull toward the model's mean, against the mean squared size of its modes: enough to keep a face a
# face where the body's coarser head says little (the body's head is 18,056-point SOMA, the face 26,719 points).
IDENTITY_PULL = 0.02
EYE_WEIGHT = 40.0  # each eye centre's weight against one face point's, so the eyes sit in the body's eye joints
TRIM_METRES = 0.012  # a face point further than this from the body's skin is left out of a round's solve
KEEP_SHARE = 0.9  # and only the nearest share of the rest are taken, so lids and lips that differ do not pull
BLEND_METRES = 0.04  # how far in from the face's border the body's skin still shapes the face
BORDER_SMOOTHING = 3  # border points each side whose moves onto the skin are averaged for the band behind them
WALL_REACH = 0.05  # metres: no leg of the wall along the face's border is longer
# A body point this near the face's border (metres) whose nearest face point lies more than BORDER_INSIDE in from the
# border is cut with the face's middle. The wall's points are the body points nearest the border, half of them inside
# it; kept, the cut's border crossed the face's to and fro and the strip folded over itself (flaps on the neck,
# notches over the scalp).
BORDER_NEAR = 0.025
BORDER_INSIDE = 0.001
CENTRE_BEHIND = 0.08  # the head's centre for the border's projection: this far behind the eyes
CENTRE_BELOW = 0.03  # and this far below them
MODEL_METRE = 100.0  # ICT-FaceKit's points are in centimetres
# ICT's face piece ends on each ear's helix rim; the ear's back is its head_and_neck piece's. A head_and_neck point
# whose normal turns more than 60 degrees from facing out of the head's centre faces the head: the ear's back. Left
# out, the rim was the face's border, laid on the skin, and the ears lay glued flat onto the head (#226, 2026-11-24).
EAR_BACK_FACING = 0.5
# An ear stands off the head as an ear: its outer edge (its skin within EAR_REACH of the helix's back) at most this
# far from the head's skin behind it, in mm (cephaloauricular distance, adult norms about 15 to 22; ICT's generic ear
# at the officer's scale 19.5), and its back, from the helix to its root on the head, this deep in mm (ICT's 5.6).
EAR_REACH = 0.01
EAR_PROTRUSION_MM = (12.0, 30.0)
EAR_DEPTH_MM = (3.0, 15.0)


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
    """The body's outer head and neck skin as a trimesh: its triangles with every corner above the shoulders, none in
    the eye and mouth bags SOMA-X fills in itself (`filled`), whose MHR offsets are no skin's."""
    above = (body["points"][:, 1] > body["joint_LeftEye"][1] - 0.25) & ~body["filled"]
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


def ear_backs(model):
    """Each ear's back, as head_and_neck point indices: grown from the face's border through head_and_neck points
    facing the head (EAR_BACK_FACING), the parts standing wholly further out to the side than the eyes (the neck's
    cut end under the jaw also faces in, but crosses the middle)."""
    points, triangles = model["neutral"], model["triangles"]
    first, last = ict.PIECES["head_and_neck"]
    head = triangles[(triangles <= last).all(axis=1)]
    normal = trimesh.Trimesh(points, head, process=False).vertex_normals
    out = points - (eye_centres(points).mean(axis=0) + np.array([0.0, -CENTRE_BELOW, -CENTRE_BEHIND]) * MODEL_METRE)
    facing = np.einsum("pd,pd->p", normal, out / np.linalg.norm(out, axis=1, keepdims=True))
    loop = border_loop(piece_triangles(model, "face"))
    allowed = np.zeros(len(points), dtype=bool)
    allowed[first:last + 1] = facing[first:last + 1] < EAR_BACK_FACING
    allowed[loop] = True
    graph = edge_graph(points, head)
    grown_back = grown(graph, loop, allowed)
    grown_back[loop] = False
    edges = graph.tocoo()
    inside = grown_back[edges.row] & grown_back[edges.col]
    labels = connected_components(coo_matrix((np.ones(inside.sum()), (edges.row[inside], edges.col[inside])),
                                             shape=graph.shape), directed=False)[1]
    eye_side = np.abs(eye_centres(points)[:, 0]).max()
    parts = [np.flatnonzero(grown_back & (labels == label)) for label in np.unique(labels[grown_back])]
    backs = [part for part in parts if (np.abs(points[part, 0]) > eye_side).all()]
    if len(backs) != 2:
        raise RuntimeError(f"found {len(backs)} ear backs on ICT's head, not two")
    return backs


def skin_triangles(model):
    """The face's skin: ICT's face piece and each ear's back (ear_backs), with the triangles spanning the two."""
    triangles = model["triangles"]
    on = np.zeros(len(model["neutral"]), dtype=bool)
    on[:ict.PIECES["face"][1] + 1] = True
    on[np.concatenate(ear_backs(model))] = True
    return triangles[on[triangles].all(axis=1)]


def ears(model):
    """Each ear's helix rim (the face piece's border along its back) and root (the skin's border along it), as point
    indices: [(rim, root), ...]."""
    triangles = model["triangles"]
    face_loop = border_loop(piece_triangles(model, "face"))
    skin_loop = border_loop(skin_triangles(model))
    found = []
    for back in ear_backs(model):
        touching = np.unique(triangles[np.isin(triangles, back).any(axis=1)])
        found.append((np.intersect1d(face_loop, touching), np.intersect1d(skin_loop, touching)))
    return found


def ear_measures(points, ear_list, skin, head):
    """Each ear's (protrusion, depth) in mm: the largest distance from the `head` mesh (the skin behind it) of its skin
    (`skin` triangles) within EAR_REACH of its helix, and its helix's mean distance from its root."""
    measured = []
    for rim, root in ear_list:
        along, _ = graph_distance(points, skin, rim)
        _, apart, _ = trimesh.proximity.closest_point(head, points[along < EAR_REACH])
        depth = np.linalg.norm(points[rim][:, None] - points[root][None], axis=2).min(axis=1).mean()
        measured.append((round(float(apart.max()) * 1000, 1), round(float(depth) * 1000, 1)))
    return measured


def ears_standing(measured):
    """The measures, refused when an ear is squashed: its protrusion or depth outside EAR_PROTRUSION_MM, EAR_DEPTH_MM."""
    for side, (protrusion, depth) in enumerate(measured):
        if not (EAR_PROTRUSION_MM[0] <= protrusion <= EAR_PROTRUSION_MM[1] and
                EAR_DEPTH_MM[0] <= depth <= EAR_DEPTH_MM[1]):
            raise RuntimeError(f"ear {side} is squashed: it stands {protrusion} mm off the head (wanted "
                               f"{EAR_PROTRUSION_MM}), {depth} mm rim to root (wanted {EAR_DEPTH_MM})")
    return measured


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
    """The face's points moved onto the body's skin by their share of the body (on the border fully, fading to none
    BLEND_METRES in), and that share. Where ICT's face stands off the body's head (its jaw's sides stood up to 20 mm
    off the officer's) the band round the border follows its border down, so no gap opens under it. Each point moves
    as its nearest border point moves, the border's moves smoothed along it (BORDER_SMOOTHING): snapped onto the skin
    one by one, the ears, which stand off the head within the band, were crushed flat onto it. Points off the face's
    triangles move with their nearest point on them; the share is 0 off them."""
    skin = np.unique(face_triangles)
    distance, nearest = graph_distance(points, face_triangles, loop)
    share = body_share(distance)
    snapped, _, _ = trimesh.proximity.closest_point(head, points[loop])
    reach = np.arange(-BORDER_SMOOTHING, BORDER_SMOOTHING + 1)
    border_move = (snapped - points[loop])[(np.arange(len(loop))[:, None] + reach) % len(loop)].mean(axis=1)
    move_of = np.zeros_like(points)
    move_of[loop] = border_move
    move = np.zeros_like(points)
    reached = nearest >= 0
    move[reached] = move_of[nearest[reached]] * share[reached, None]
    move[loop] = snapped - points[loop]  # the border itself lands on the skin
    rest = np.setdiff1d(np.arange(len(points)), skin)
    _, owner = cKDTree(points[skin]).query(points[rest])
    move[rest] = move[skin[owner]]
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


def border_edges(triangles):
    """The edges of a triangle set used by one triangle only, as sorted point pairs."""
    edges = np.sort(np.vstack([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]]), axis=1)
    unique, counts = np.unique(edges, axis=0, return_counts=True)
    return {tuple(edge) for edge in unique[counts == 1]}


def edge_graph(points, triangles):
    """The mesh's edges as a sparse graph weighted by their lengths."""
    edges = np.unique(np.sort(np.vstack([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]]), axis=1),
                      axis=0)
    lengths = np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1)
    return coo_matrix((lengths, (edges[:, 0], edges[:, 1])), shape=(len(points), len(points))).tocsr()


def wall(graph, stops):
    """A closed path of body points through the stops in order, each leg the shortest along the mesh's edges."""
    path = []
    for start, end in zip(stops, np.roll(stops, -1)):
        _, before = dijkstra(graph, directed=False, indices=start, return_predecessors=True, limit=WALL_REACH)
        leg = [end]
        while leg[-1] != start:
            if before[leg[-1]] < 0:
                raise RuntimeError(f"no path on the body from point {start} to {end} within {WALL_REACH} m")
            leg.append(before[leg[-1]])
        path.extend(leg[::-1][:-1])
    return np.array(path)


def under_face(points, face_points, face_triangles, loop):
    """Which points lie under the face: their nearest face point more than BORDER_INSIDE in from its border (a point
    beside the face is nearest the border) and they on its underside (the body's scalp behind an ear is nearest the
    ear's back, but on its outer side)."""
    mesh = trimesh.Trimesh(face_points, face_triangles, process=False)
    closest, apart, triangle = trimesh.proximity.closest_point(mesh, points)
    inward, _ = graph_distance(face_points, face_triangles, loop)
    corners = face_triangles[triangle]
    weights = trimesh.triangles.points_to_barycentric(face_points[corners], closest)
    depth = np.einsum("pc,pc->p", weights, inward[corners])
    above = np.einsum("pd,pd->p", points - closest, mesh.face_normals[triangle])
    return (depth > BORDER_INSIDE) & (apart < BORDER_NEAR) & (above < BORDER_INSIDE)


def inside_border(body_points, face_points, face_triangles, loop):
    """The body points within BORDER_NEAR of the face's border that lie under the face."""
    near = np.flatnonzero(cKDTree(face_points[loop]).query(body_points)[0] < BORDER_NEAR)
    under = np.zeros(len(body_points), dtype=bool)
    under[near] = under_face(body_points[near], face_points, face_triangles, loop)
    return under


def grown(graph, start, allowed):
    """The points reached from the `start` points through `allowed` points along the mesh's edges."""
    edges = graph.tocoo()
    step = allowed[edges.row] & allowed[edges.col]
    walkable = coo_matrix((np.ones(step.sum()), (edges.row[step], edges.col[step])), shape=graph.shape).tocsr()
    labels = connected_components(walkable, directed=False)[1]
    return np.isin(labels, np.unique(labels[start])) & allowed


def covered(body_points, body_triangles, face_points, face_triangles, loop, middle):
    """Which body points lie under the laid face: a wall of body points is drawn along the face's border (which lies
    on the skin), and the body is filled from the point under the face's `middle` up to it. Cut by nearness instead,
    the neck under the jaw and the skin in front of the ear lay near the face behind its border and were cut 27 mm
    and more past it. The body points under the face near its border and joined to that fill go with it
    (inside_border)."""
    graph = edge_graph(body_points, body_triangles)
    tree = cKDTree(body_points)
    _, stops = tree.query(face_points[loop])
    stops = stops[np.concatenate([[True], np.diff(stops) != 0])]
    blocked = np.zeros(len(body_points), dtype=bool)
    blocked[wall(graph, stops)] = True
    _, seed = tree.query(middle)
    if blocked[seed]:
        raise RuntimeError("the face's middle lies on its own border's wall")
    kept_edges = graph.tocoo()
    open_edges = ~blocked[kept_edges.row] & ~blocked[kept_edges.col]
    walkable = coo_matrix((np.ones(open_edges.sum()), (kept_edges.row[open_edges], kept_edges.col[open_edges])),
                          shape=graph.shape)
    reached = breadth_first_order(walkable, seed, directed=False, return_predecessors=False)
    under = np.zeros(len(body_points), dtype=bool)
    under[reached] = True
    under = grown(graph, np.flatnonzero(under), under | inside_border(body_points, face_points, face_triangles, loop))
    if under.sum() > len(body_points) / 2:
        raise RuntimeError("the face's border wall leaks: the fill under the face reached half the body")
    return under


def kept_body(triangles, under):
    """The body's triangles left once every triangle touching a covered point is cut, and islands cut off by it
    (only the largest connected part of the body is kept), the cut widened at any point its border passes twice (a
    pinch, where two corners of the cut meet: its border would be no single loop)."""
    under = under.copy()
    while True:
        kept = triangles[~under[triangles].any(axis=1)]
        parts = trimesh.graph.connected_components(np.vstack([kept[:, [0, 1]], kept[:, [1, 2]]]), min_len=1)
        largest = set(max(parts, key=len).tolist())
        kept = kept[np.array([triangle[0] in largest for triangle in kept])]
        border = np.array(sorted(border_edges(kept)))
        passes = np.bincount(border.reshape(-1), minlength=len(under))
        if not (passes > 2).any():
            return kept
        under |= passes > 2


def border_places(points, border):
    """Each point's place along a closed polyline (its nearest point on it, in segments from the polyline's first
    point), counted on from the first point's place so that no step between neighbours goes more than half round."""
    segment = np.roll(border, -1, axis=0) - border
    offset = points[:, None, :] - border[None]
    along = np.clip(np.einsum("mnd,nd->mn", offset, segment) / np.einsum("nd,nd->n", segment, segment), 0.0, 1.0)
    best = np.argmin(np.linalg.norm(offset - along[..., None] * segment[None], axis=2), axis=1)
    place = best + along[np.arange(len(points)), best]
    count = len(border)
    steps = (np.diff(place) + count / 2) % count - count / 2
    return np.concatenate([[place[0]], place[0] + np.cumsum(steps)])


def zipper(outer, inner, outer_points, inner_points):
    """Triangles joining two closed loops of point indices (both in one numbering) running the same way round: each
    inner point placed along the outer loop (border_places, never stepping back), and the two walked together by
    those places. (Walked by the shorter diagonal instead, the walk fell out of step where the cut stood far from the
    face's border behind the ears, and the strip crossed the head.)"""
    count_outer, count_inner = len(outer), len(inner)
    start = int(np.argmin(border_places(inner_points, outer_points) % count_outer))
    inner, inner_points = np.roll(inner, -start), np.roll(inner_points, -start, axis=0)
    place = np.maximum.accumulate(border_places(inner_points, outer_points))
    place = np.append(place, place[0] + count_outer)  # the inner loop's start again, once round
    triangles, at_outer, at_inner = [], 0, 0
    while at_outer < count_outer or at_inner < count_inner:
        advance_outer = at_inner >= count_inner or (at_outer < count_outer and at_outer + 1 <= place[at_inner + 1])
        if advance_outer:
            triangles.append([outer[at_outer], outer[(at_outer + 1) % count_outer], inner[at_inner % count_inner]])
            at_outer += 1
        else:
            triangles.append([outer[at_outer % count_outer], inner[(at_inner + 1) % count_inner], inner[at_inner]])
            at_inner += 1
    return np.array(triangles)


def same_way(loop, points, centre):
    """The loop turned to run anticlockwise as seen from the head's centre's (around, up) angles."""
    flat = directions(points[loop], centre)
    area = np.sum(flat[:, 0] * np.roll(flat[:, 1], -1) - np.roll(flat[:, 0], -1) * flat[:, 1])
    return loop if area > 0 else loop[::-1]


def alongside(loop, points, guide, guide_points):
    """The loop turned to run the way the guide loop runs: the guide's nearest point to each of its points steps
    forward round the guide more than back. (By the turn of its angles about the head's centre it went wrong where a
    border passes behind the centre, at the back of the neck.)"""
    _, nearest = cKDTree(guide_points[guide]).query(points[loop])
    step = (np.diff(np.append(nearest, nearest[0])) + len(guide) // 2) % len(guide) - len(guide) // 2
    return loop if step.sum() >= 0 else loop[::-1]


def seam(body_points, body_triangles, face_points, face_triangles, loop, centre, filled):
    """The body cut under the face, its `filled` points (the eye and mouth bags) with it, and the strip joining the
    cut to the face's border: (the body's kept triangles, the strip in one numbering, body points first and the
    face's after them, the face's loop, the cut's loop)."""
    used = np.unique(face_triangles)
    furthest, _ = cKDTree(face_points[loop]).query(face_points[used])
    under = covered(body_points, body_triangles, face_points, face_triangles, loop,
                    face_points[used[np.argmax(furthest)]]) | filled
    kept = kept_body(body_triangles, under)
    face_loop = same_way(loop, face_points, centre)
    body_loop = alongside(border_loop(kept), body_points, face_loop, face_points)
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
    body per model point, the body's kept triangles and the strip joining them (strip indices: body points first,
    then the model's points offset by the body's count), and each ear's measures (ears_standing: refused when one is
    squashed)."""
    scale, turn, shift, coefficients = fit_pose_and_identity(model, body)
    points = scale * shaped(model, coefficients) @ turn.T + shift
    face_triangles = skin_triangles(model)
    loop = border_loop(face_triangles)
    points, share = laid_on_skin(points, face_triangles, loop, head_mesh(body))
    kept, strip, face_loop, body_loop = seam(body["points"], body["triangles"], points, face_triangles, loop,
                                             head_centre(body), body["filled"])
    behind = trimesh.Trimesh(np.vstack([body["points"], points]), np.vstack([kept, strip]), process=False)
    measured = ears_standing(ear_measures(points, ears(model), face_triangles, behind))
    return {"points": points, "scale": scale, "turn": turn, "shift": shift, "identity": coefficients,
            "share": share, "kept": kept, "strip": strip, "face_loop": face_loop, "body_loop": body_loop,
            "ears": measured}
