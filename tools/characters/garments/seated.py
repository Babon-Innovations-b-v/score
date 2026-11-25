"""Whether a worn garment stays where its pattern seats it (#225; the owner, 2026-11-24, on a tee sliding off the
left shoulder during the walk: "clothes falling off"). Score venv (numpy, scipy, trimesh).

The garment is sewn on the body at its bind (an A-pose), where GarmentCode's pattern puts it, and worn through the
turn into the clip: the seams' middle and the cloth over the body are judged against the sewn garment; the seams'
and the neckline's moves against the clip's first frame (every point tied to the skin under it there, its nearest
place on the body's surface, and that place carried with the skin over every clip frame: the arms lowered out of
the A-pose stretch the skin under a seam, never the place a seated seam is on).

- shoulder seams off centre: when sewn, the middle of the two shoulder seams to a side of the body's middle (the
  body's points at the seams' height, the arms' A-pose either side), along x.
- shoulder seam off the shoulder's top: each side's shoulder seam (the points its front and back torso panels share
  above the armhole) on every clip frame on the skin (SKIN_M) whose normals face up (SHOULDER_UP), the shoulder's
  line from the neck to the arm; a seam slid off the shoulder lies on the arm's side, its skin facing out.
- shoulder seam moved over the clip: as far as each seam has moved from its places on the skin at the clip's first
  frame, the mean over the seam's points, its worst frame.
- neckline drop: the neckline's points (GarmentCode's `right_collar` and `left_collar`) fallen below their places on
  the skin at the clip's first frame, the deepest point on the worst frame.
- body through cloth: the body's points the sewn garment covers (cloth within COVER_M of them, not at an open edge)
  that stand out past the cloth over them, between its points too (the cloth's triangles, not only its points): the
  most on a frame and the deepest.
- torn: the cloth's edges stretched past TORN_STRETCH times their sewn length on a frame, the most on one frame. A
  woven or knit cloth barely stretches; a tee caught under the walking arm was left behind in the world and drawn
  out into a flap a metre long (2026-11-25), its edges up to 16 times their length, every other check passing.
"""
import numpy as np
from scipy.spatial import cKDTree

CENTRE_M = 0.015  # the shoulder seams' middle this far to a side of the body's middle when sewn fails them
SHOULDER_UP = 0.5  # the skin under a seated shoulder seam faces at least this much up (within 60 degrees)
SKIN_M = 0.02  # a seated shoulder seam lies on the skin, this near
SEAM_MOVE_M = 0.025  # a shoulder seam's mean move off its places on the shoulder over the clip that fails it
NECK_DROP_M = 0.025  # a neckline point's fall below its place on the skin that fails it
COVER_M = 0.02  # a body point with the sewn cloth this near is covered by it
THROUGH_M = 0.003  # a covered body point this far out past its cloth pokes through (the cloth's thickness)
OVER_DEGREES = 60.0  # cloth whose normal is further off the body point's is beside it, not over it
TORN_STRETCH = 2.0  # an edge this many times its sewn length is torn
TORN_EDGES = 20  # this many torn edges on a frame fail the garment (a sewn tee standing has 2: its seams' ends)
NEAREST = 6  # cloth points whose triangles are searched for a body point's nearest place on the cloth


def shared_chains(record, first, second):
    """The box mesh's points the panels `first` and `second` both hold, split into the chains the garment's edges
    join them in: a list of index arrays."""
    names = [str(name) for name in record["panel_names"]]
    panel, box = np.asarray(record["panel"]), np.asarray(record["box"])
    both = np.intersect1d(box[panel == names.index(first)], box[panel == names.index(second)])
    welded = box[np.asarray(record["faces"])]
    edges = np.concatenate([welded[:, [0, 1]], welded[:, [1, 2]], welded[:, [2, 0]]])
    inside = np.isin(edges, both).all(axis=1)
    parent = {int(point): int(point) for point in both}

    def root(point):
        while parent[point] != point:
            parent[point] = parent[parent[point]]
            point = parent[point]
        return point

    for one, other in edges[inside]:
        parent[root(int(one))] = root(int(other))
    chains = {}
    for point in both:
        chains.setdefault(root(int(point)), []).append(int(point))
    return [np.asarray(sorted(chain)) for chain in chains.values()]


def shoulder_seams(record):
    """Each side's shoulder seam: of the chains its front and back torso panels share, the one highest up (the other
    is the side seam). {side: box point indices}; a garment with no torso panels has none."""
    names = [str(name) for name in record["panel_names"]]
    points = np.asarray(record["points"])
    found = {}
    for side in ("left", "right"):
        front, back = f"{side}_ftorso", f"{side}_btorso"
        if front in names and back in names:
            chains = shared_chains(record, front, back)
            found[side] = max(chains, key=lambda chain: points[chain, 1].mean())
    return found


def neckline(record):
    """The neckline's box points (GarmentCode's collar labels), none when the garment has no neckline."""
    labels = [np.asarray(record[key]) for key in ("label/right_collar", "label/left_collar") if key in record]
    return np.unique(np.concatenate(labels)) if labels else np.zeros(0, dtype=int)


def nearest_on(points, faces, queries):
    """Each query's nearest place on the triangle mesh (points, faces): (the place, its triangle, its distance)."""
    import trimesh
    points, faces = np.asarray(points, dtype=float), np.asarray(faces)
    if not len(queries):
        return np.zeros((0, 3)), np.zeros(0, dtype=int), np.zeros(0)
    around = [[] for _ in range(len(points))]
    for number, face in enumerate(faces):
        for corner in face:
            around[corner].append(number)
    widest = max(len(triangles) for triangles in around)
    padded = np.array([triangles + [triangles[0]] * (widest - len(triangles)) for triangles in around])
    _, near = cKDTree(points).query(queries, k=min(NEAREST, len(points)))
    candidates = padded[near.reshape(len(queries), -1)].reshape(len(queries), -1)
    repeated = np.repeat(np.asarray(queries, dtype=float), candidates.shape[1], axis=0)
    places = trimesh.triangles.closest_point(points[faces[candidates.ravel()]], repeated)
    distances = np.linalg.norm(places - repeated, axis=1).reshape(candidates.shape)
    best = distances.argmin(axis=1)
    rows = np.arange(len(queries))
    return (places.reshape(*candidates.shape, 3)[rows, best], candidates[rows, best], distances[rows, best])


def barycentric(corners, place):
    """The place's weights on its triangle's corners (triangles x 3 x 3, places x 3)."""
    import trimesh
    return trimesh.triangles.points_to_barycentric(corners, place)


def tied(bind, faces, points):
    """Each point's place on the body's skin at its bind: (its triangle, the place's weights on that triangle's
    corners)."""
    faces = np.asarray(faces)
    place, triangle, _ = nearest_on(bind, faces, points)
    return triangle, barycentric(np.asarray(bind)[faces[triangle]], place)


def carried(frames, faces, triangle, weights):
    """The tied places on the skin over the frames (frames x places x 3)."""
    corners = np.asarray(frames)[:, np.asarray(faces)[triangle]]
    return np.einsum("fpcx,pc->fpx", corners, weights)


def off_centre(sewn, bind, seams):
    """How far the middle of the sewn shoulder seams lies to a side of the body's middle at their height (m, along
    x: the median of the body's points within 5 cm of the seams' mean height)."""
    left, right = sewn[seams["left"]].mean(axis=0), sewn[seams["right"]].mean(axis=0)
    height = (left[1] + right[1]) / 2.0
    bind = np.asarray(bind)
    middle = np.median(bind[np.abs(bind[:, 1] - height) < 0.05, 0])
    return abs((left[0] + right[0]) / 2.0 - middle)


def seam_moves(worn, body_frames, faces, seam):
    """A seam's mean move off its places on the skin each clip frame (m): each point's distance from its place (tied
    at the clip's first frame), less what it was there."""
    worn, body_frames = np.asarray(worn), np.asarray(body_frames)
    triangle, weights = tied(body_frames[0], faces, worn[0, seam])
    places = carried(body_frames, faces, triangle, weights)
    distances = np.linalg.norm(worn[:, seam] - places, axis=2)
    return np.abs(distances - distances[0]).mean(axis=1)


def on_top(worn, body_frames, faces, seam):
    """Where a seam sits on the body each clip frame: how upward the skin under it faces (the mean of its points'
    nearest skin normals' up part, 1 on a shoulder's top, 0 down the arm's side) and its mean distance off the skin
    (m)."""
    faces = np.asarray(faces)
    ups, distances = [], []
    for cloth, body in zip(np.asarray(worn), np.asarray(body_frames)):
        _, triangle, distance = nearest_on(body, faces, cloth[seam])
        facing = normals(body, faces)[faces[triangle]].mean(axis=1)
        ups.append(np.mean(facing[:, 1] / np.linalg.norm(facing, axis=1)))
        distances.append(distance.mean())
    return np.asarray(ups), np.asarray(distances)


def neck_drops(worn, body_frames, faces, points):
    """Each neckline point's fall below its place on the skin each clip frame (tied at the clip's first frame), less
    what it hung below it there (m, frames x points; a rise counts zero)."""
    worn, body_frames = np.asarray(worn), np.asarray(body_frames)
    triangle, weights = tied(body_frames[0], faces, worn[0, points])
    places = carried(body_frames, faces, triangle, weights)
    below = places[:, :, 1] - worn[:, points, 1]
    return np.maximum(0.0, below - below[0])


def normals(points, faces):
    """Each point's normal: the area-weighted sum of its triangles' (outward for a body whose triangles wind
    outward)."""
    points, faces = np.asarray(points, dtype=float), np.asarray(faces)
    crossed = np.cross(points[faces[:, 1]] - points[faces[:, 0]], points[faces[:, 2]] - points[faces[:, 0]])
    found = np.zeros_like(points)
    for corner in range(3):
        np.add.at(found, faces[:, corner], crossed)
    return found / np.maximum(np.linalg.norm(found, axis=1, keepdims=True), 1e-12)


def open_edge_points(faces):
    """The points on a mesh's open edges (an edge of one triangle only)."""
    faces = np.asarray(faces)
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    unique, counts = np.unique(edges, axis=0, return_counts=True)
    return np.unique(unique[counts == 1])


def standing_out(body, outward, place, corners):
    """How far each body point stands out past the cloth at its place (m, negative under it): along the normal of
    the cloth's triangle there (its `corners`), turned to the body's own outward normal at the point; NaN where the
    cloth there is not over the point but beside it (its normal more than OVER_DEGREES off the body's)."""
    facing = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    facing /= np.maximum(np.linalg.norm(facing, axis=1, keepdims=True), 1e-12)
    agree = np.sum(facing * outward, axis=1)
    facing *= np.sign(agree)[:, None]
    found = np.sum((body - place) * facing, axis=1)
    found[np.abs(agree) < np.cos(np.radians(OVER_DEGREES))] = np.nan
    return found


def through(cloth, cloth_faces, body, body_faces, covered, held, sides=None):
    """How far each covered body point stands out past the cloth over it (m, negative under it), the lesser of two
    readings, so both must find it out: past the cloth at its nearest place now (NaN where that place is at the
    cloth's open edge: the point no longer under it), and past the cloth at the place it was under when sewn
    (`held`: the cloth's triangle and weights there), carried with the cloth. A point out past the nearest cloth
    alone faces another fold; out past its own sewn place alone, the cloth has slid off it (the seams' measure).
    `sides` (+1 or -1 a body point) turns the body's normals outward where its triangles do not wind outward (a
    garment under another, GarmentCode's panels wound either way)."""
    cloth, cloth_faces = np.asarray(cloth, dtype=float), np.asarray(cloth_faces)
    body = np.asarray(body, dtype=float)
    outward = normals(body, body_faces) * (1.0 if sides is None else np.asarray(sides)[:, None])
    outward = outward[covered]
    place, triangle, _ = nearest_on(cloth, cloth_faces, body[covered])
    corners = cloth[cloth_faces[triangle]]
    nearest = standing_out(body[covered], outward, place, corners)
    at_edge = (np.isin(cloth_faces[triangle], open_edge_points(cloth_faces)) & (barycentric(corners, place) > 1e-3))
    nearest[at_edge.any(axis=1)] = np.nan
    sewn_triangle, sewn_weights = held
    corners = cloth[cloth_faces[sewn_triangle]]
    own = standing_out(body[covered], outward, np.einsum("pcx,pc->px", corners, sewn_weights), corners)
    return np.minimum(nearest, own)


def held_under(sewn, cloth_faces, bind, covered):
    """The cloth's place over each covered body point when sewn: its triangle and weights."""
    cloth_faces = np.asarray(cloth_faces)
    place, triangle, _ = nearest_on(sewn, cloth_faces, np.asarray(bind)[covered])
    return triangle, barycentric(np.asarray(sewn, dtype=float)[cloth_faces[triangle]], place)


def measured(garment, body):
    """The seating measures of one garment over the clip. `garment`: {"record" (pattern.py's npz, its points in cm,
    GarmentCode's frame), "sewn" (points x 3, m, at the bind), "worn" (frames x points x 3), "faces"}; `body`:
    {"bind", "faces", "frames" (the clip's frames, the garment's frames' bodies)}."""
    record, sewn, worn = garment["record"], np.asarray(garment["sewn"]), np.asarray(garment["worn"])
    bind, faces, frames = np.asarray(body["bind"]), np.asarray(body["faces"]), np.asarray(body["frames"])
    found = {"frames": int(len(worn))}
    seams = shoulder_seams(record)
    if len(seams) == 2:
        found["shoulder seams off centre mm"] = round(float(off_centre(sewn, bind, seams)) * 1000.0, 1)
    for side, seam in seams.items():
        ups, distances = on_top(worn, frames, faces, seam)
        found[f"{side} shoulder seam least upward skin"] = round(float(ups.min()), 2)
        found[f"{side} shoulder seam farthest off the skin mm"] = round(float(distances.max()) * 1000.0, 1)
        found[f"{side} shoulder seam off its top frame"] = int(np.argmin(ups - (distances > SKIN_M)))
        moves = seam_moves(worn, frames, faces, seam)
        found[f"{side} shoulder seam moved over the clip mm"] = round(float(moves.max()) * 1000.0, 1)
        found[f"{side} shoulder seam moved worst frame"] = int(moves.argmax())
    neck = neckline(record)
    if len(neck):
        drops = neck_drops(worn, frames, faces, neck)
        found["neckline drop mm"] = round(float(drops.max()) * 1000.0, 1)
        found["neckline drop worst frame"] = int(drops.max(axis=1).argmax())
    _, _, distance = nearest_on(sewn, garment["faces"], bind)
    covered = np.flatnonzero(distance < COVER_M)
    held = held_under(sewn, garment["faces"], bind, covered)
    at_sewing = np.isfinite(through(sewn, garment["faces"], bind, faces, covered, held))
    covered, held = covered[at_sewing], (held[0][at_sewing], held[1][at_sewing])
    out = np.array([through(cloth, garment["faces"], frame, faces, covered, held)
                    for cloth, frame in zip(worn, frames)])
    poking = np.nan_to_num(out, nan=-1.0) > THROUGH_M
    found["body points covered"] = int(len(covered))
    found["most body points through on a frame"] = int(poking.sum(axis=1).max())
    found["body through deepest mm"] = round(float(max(0.0, np.nanmax(out))) * 1000.0, 1)
    stretch = stretched(sewn, worn, garment["faces"])
    found["most edges torn on a frame"] = int((stretch > TORN_STRETCH).sum(axis=1).max())
    found["most stretched edge"] = round(float(stretch.max()), 2)
    return found


def stretched(sewn, worn, faces):
    """Each of the cloth's edges' length on every frame over its sewn length (frames x edges)."""
    faces = np.asarray(faces)
    edges = np.unique(np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1), axis=0)
    rest = np.maximum(np.linalg.norm(sewn[edges[:, 0]] - sewn[edges[:, 1]], axis=1), 1e-9)
    return np.linalg.norm(worn[:, edges[:, 0]] - worn[:, edges[:, 1]], axis=2) / rest


def outward_sides(points, faces, body):
    """+1 when most of a garment's triangles at the bind face away from the body (the nearest body point to each of
    its points), else -1: its winding, one way for the whole garment (judged point by point, a cap's points whose
    normal stands square to the way to the body were read the wrong way round, 2026-11-24)."""
    from scipy.spatial import cKDTree
    points = np.asarray(points, dtype=float)
    _, nearest = cKDTree(np.asarray(body, dtype=float)).query(points)
    away = np.sum(normals(points, faces) * (points - np.asarray(body)[nearest]), axis=1)
    return np.full(len(points), 1.0 if np.median(away) >= 0.0 else -1.0)


def layered(under, over, bind):
    """A garment worn under another (`under`, `over`: {"sewn", "worn", "faces"} as `measured` takes them; `bind`
    the body's points at the bind): the under garment's points the over one covers when sewn that stand out
    through it over the clip, as the body's through its cloth (`through`). A shirt's or trousers' cloth out through
    the coat or jacket over it shows on the outside."""
    under_sewn, over_sewn = np.asarray(under["sewn"], dtype=float), np.asarray(over["sewn"], dtype=float)
    sides = outward_sides(under_sewn, under["faces"], bind)
    _, _, distance = nearest_on(over_sewn, over["faces"], under_sewn)
    covered = np.flatnonzero(distance < COVER_M)
    held = held_under(over_sewn, over["faces"], under_sewn, covered)
    at_sewing = np.isfinite(through(over_sewn, over["faces"], under_sewn, under["faces"], covered, held, sides))
    covered, held = covered[at_sewing], (held[0][at_sewing], held[1][at_sewing])
    out = np.array([through(cloth, over["faces"], frame, under["faces"], covered, held, sides)
                    for cloth, frame in zip(np.asarray(over["worn"]), np.asarray(under["worn"]))])
    poking = np.nan_to_num(out, nan=-1.0) > THROUGH_M
    return {"points covered": int(len(covered)), "most points through on a frame": int(poking.sum(axis=1).max()),
            "through deepest mm": round(float(max(0.0, np.nanmax(out))) * 1000.0, 1) if len(covered) else 0.0}


def layer_faults(under_name, over_name, found):
    """The fault line of a garment out through the one over it (none when it stays under)."""
    if not found["most points through on a frame"]:
        return []
    return [f"{under_name} through {over_name}: {found['most points through on a frame']} points on a frame, "
            f"{found['through deepest mm']} mm deep (limit {THROUGH_M * 1000.0:.0f} mm)"]


def faults(found):
    """The measures past their limits, one line each (none when the garment stays seated)."""
    lines = []
    if found.get("shoulder seams off centre mm", 0.0) > CENTRE_M * 1000.0:
        lines.append(f"shoulder seams off centre when sewn: {found['shoulder seams off centre mm']} mm "
                     f"(limit {CENTRE_M * 1000.0:.0f})")
    for side in ("left", "right"):
        up = found.get(f"{side} shoulder seam least upward skin")
        off = found.get(f"{side} shoulder seam farthest off the skin mm")
        if up is not None and (up < SHOULDER_UP or off > SKIN_M * 1000.0):
            lines.append(f"{side} shoulder seam off the shoulder's top: the skin under it faces {up} up (limit "
                         f"{SHOULDER_UP}), {off} mm off it (limit {SKIN_M * 1000.0:.0f})")
        moved = found.get(f"{side} shoulder seam moved over the clip mm", 0.0)
        if moved > SEAM_MOVE_M * 1000.0:
            lines.append(f"{side} shoulder seam moved over the clip: {moved} mm (limit {SEAM_MOVE_M * 1000.0:.0f})")
    if found.get("neckline drop mm", 0.0) > NECK_DROP_M * 1000.0:
        lines.append(f"neckline drop: {found['neckline drop mm']} mm (limit {NECK_DROP_M * 1000.0:.0f})")
    if found.get("most body points through on a frame", 0):
        lines.append(f"body through cloth: {found['most body points through on a frame']} points on a frame, "
                     f"{found['body through deepest mm']} mm deep (limit {THROUGH_M * 1000.0:.0f} mm)")
    if found.get("most edges torn on a frame", 0) > TORN_EDGES:
        lines.append(f"torn: {found['most edges torn on a frame']} edges past {TORN_STRETCH:.0f} times their length "
                     f"on a frame (limit {TORN_EDGES}), the most {found['most stretched edge']} times")
    return lines
