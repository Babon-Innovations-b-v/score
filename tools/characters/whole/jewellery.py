"""A whole person's trinkets and jewellery (#228's next slice, PRD #223): hoop earrings in the ear lobes, a chain round
the neck, a watch on the left wrist and rings on two fingers, each finished with score_lib metals and glass.

The library holds no jewellery model (score_lib checked 2026-11-24: its gold, chrome and glass are surfaces, no
earring, chain, watch or ring), so each is made on the person who wears it, as the shoes and the belt are
(`../accessories`): its size read off the skin where it is worn, carried rigidly by the joint it is worn on (the
Head, the Chest, the LeftForeArm, the hand), every finish a library surface the outfit names (`accessories.jewellery`).

- **Earrings** (`earrings`): each ear's lobe the lowest skin point within EAR_REACH_M of the ear's outermost point at
  the eyes' height; a hoop EARRING["major"] round of EARRING["wire"] wire through it, in the ear's plane.
- **Necklace** (`necklace`): a chain round the neck over its base, NECKLACE["drop"] lower at the front, on the skin
  all round (each turn's first skin out from the neck's middle along a ray, CHAIN["clear"] out), as a tube of
  CHAIN["wire"].
- **Watch** (`watch`): a strap round the wrist (WATCH["from_hand"] up the forearm from the hand's joint) on the skin
  all round, a case, its dial and its glass on the back of the wrist.
- **Rings** (`ring`): a band round a finger where the hand's skin, cut across RING["at"] of the way from the wrist
  to the fingertips, falls apart into its fingers (`fingers_at`), inside it the finger with RING["clear"] to spare.

`deepest` reads how far each piece goes into the skin over the clip, `faults` names a piece through the skin past
INTO_LIMIT_M (the earrings, through their lobes by design, are read by how far their hoop's top is from the lobe).
"""
import numpy as np
import trimesh

EAR_REACH_M = 0.035
# m; `through`: the hoop's top this far inside the lobe. A small huggie hoop, 12 mm across (#223 photoreal round 1:
# "small earrings"; 18 mm read as a statement hoop)
EARRING = {"major": 0.006, "wire": 0.0009, "through": 0.0015}
NECKLACE = {"over_neck": 0.02, "drop": 0.08, "turns": 96}  # m over the Neck1 joint, m lower at the front
CHAIN = {"wire": 0.0011, "clear": 0.0015, "sides": 8}
# A women's watch (#223 photoreal round 1: "the watch sized right and sitting on the wrist"): a 28 mm case on a 14 mm
# strap just over the wrist bone, 3 cm up from the wrist's joint, the strap 1.5 mm off the skin (at 5 cm up the
# forearm, a 31 mm case on an 18 mm strap 3 mm off it stood out as a man's watch slid up the arm)
WATCH = {"from_hand": 0.03, "strap": 0.014, "strap_thick": 0.0025, "clear": 0.0015, "case": 0.014,
         "case_tall": 0.0065, "glass": 0.0008, "turns": 48, "slice": 0.012}
# `at`: of the way from the wrist to the fingertips, the fingers' first bones; `least`: triangles a finger's cut has
RING = {"at": 0.62, "wire": 0.0011, "clear": 0.0004, "least": 6}
RINGS = (("Left", 1), ("Right", 2))  # the left ring finger and the right middle finger, counted from the little one
INTO_LIMIT_M = 0.001  # a piece this far into the skin goes through it
LOBE_LIMIT_M = 0.002  # an earring's hoop top this far off its lobe has fallen out of it


def frame_of(axis):
    """Two unit directions square to `axis` and to each other."""
    axis = axis / np.linalg.norm(axis)
    other = np.array([1.0, 0.0, 0.0]) if abs(axis[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    first = np.cross(axis, other)
    first /= np.linalg.norm(first)
    return first, np.cross(axis, first)


def tube(path, wire, sides, closed=True):
    """A round tube of radius `wire` along `path` (points x 3): points, triangles and each point's st (along, round)."""
    count = len(path)
    ahead = np.roll(path, -1, axis=0) - np.roll(path, 1, axis=0)
    if not closed:
        ahead[0], ahead[-1] = path[1] - path[0], path[-1] - path[-2]
    ahead /= np.linalg.norm(ahead, axis=1, keepdims=True)
    reference = np.where(np.abs(ahead[:, 1:2]) < 0.9, [[0.0, 1.0, 0.0]], [[1.0, 0.0, 0.0]])
    side = np.cross(ahead, reference)
    side /= np.linalg.norm(side, axis=1, keepdims=True)
    up = np.cross(ahead, side)
    angles = np.arange(sides) * 2.0 * np.pi / sides
    points = (path[:, None] + wire * (np.cos(angles)[None, :, None] * side[:, None]
                                      + np.sin(angles)[None, :, None] * up[:, None])).reshape(-1, 3)
    rows = count if closed else count - 1
    faces = []
    for row in range(rows):
        nxt = (row + 1) % count
        for corner in range(sides):
            here, across = row * sides + corner, row * sides + (corner + 1) % sides
            faces += [[here, nxt * sides + corner, across], [across, nxt * sides + corner, nxt * sides + (corner + 1)
                                                             % sides]]
    lengths = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))])
    st = np.stack([np.repeat(lengths / 0.02, sides), np.tile(angles / (2.0 * np.pi), count)], axis=1)
    return points, np.asarray(faces), st


def circle(centre, axis, radius, count):
    """`count` points round a circle of `radius` about `axis` through `centre`."""
    first, second = frame_of(axis)
    angles = np.arange(count) * 2.0 * np.pi / count
    return centre + radius * (np.cos(angles)[:, None] * first + np.sin(angles)[:, None] * second)


def disc(centre, axis, radius, tall, count):
    """A closed short cylinder (a watch's case, dial or glass): points, triangles and st (planar over the top)."""
    axis = axis / np.linalg.norm(axis)
    bottom, top = circle(centre, axis, radius, count), circle(centre + axis * tall, axis, radius, count)
    points = np.concatenate([bottom, top, [centre, centre + axis * tall]])
    faces = []
    for corner in range(count):
        nxt = (corner + 1) % count
        faces += [[corner, nxt, count + corner], [nxt, count + nxt, count + corner],
                  [2 * count, nxt, corner], [2 * count + 1, count + corner, count + nxt]]
    first, second = frame_of(axis)
    st = np.stack([(points - centre) @ first, (points - centre) @ second], axis=1) / (4.0 * radius) + 0.5
    return points, np.asarray(faces), st


def round_off(skin, centre, axis, slice_m, turns, keep=None):
    """The skin's farthest reach off `axis` through `centre` in each of `turns` turns round it, from the skin points
    within `slice_m` of the plane (and `keep`, when given, only those): radius a turn (gaps filled from neighbours)."""
    axis = axis / np.linalg.norm(axis)
    first, second = frame_of(axis)
    offset = skin - centre
    near = np.abs(offset @ axis) < slice_m
    if keep is not None:
        near &= keep
    if not near.any():
        raise SystemExit("a piece of jewellery finds no skin where it is worn")
    angle = np.arctan2(offset[near] @ second, offset[near] @ first) % (2.0 * np.pi)
    radius = np.hypot(offset[near] @ second, offset[near] @ first)
    bins = (angle / (2.0 * np.pi) * turns).astype(int) % turns
    found = np.full(turns, np.nan)
    for number in np.unique(bins):
        found[number] = radius[bins == number].max()
    known = np.flatnonzero(~np.isnan(found))
    found = np.interp(np.arange(turns), known, found[known], period=turns)
    return found, first, second


def carried(points, joint, body, frames):
    """Points laid at the build's bind carried rigidly by `joint` over `frames` (indices of the body's `worlds`)."""
    names = [str(name) for name in body["names"]]
    index = names.index(joint)
    moves = np.asarray(body["worlds"])[frames, index] @ np.linalg.inv(np.asarray(body["joints"])[index])
    homogeneous = np.concatenate([points, np.ones((len(points), 1))], axis=1)
    return np.einsum("fij,pj->fpi", moves, homogeneous)[..., :3]


def earrings(skin, eyes):
    """Each ear's hoop at the bind: {side: (points, faces, st, lobe)}. `eyes`: the two eyes' places (left first)."""
    middle = eyes.mean(axis=0)
    found = {}
    for side, sign in (("left", 1.0), ("right", -1.0)):
        level = np.abs(skin[:, 1] - middle[1]) < 0.02
        lateral = (skin[:, 0] - middle[0]) * sign
        outer = skin[level][lateral[level].argmax()]
        ear = (np.linalg.norm(skin - outer, axis=1) < EAR_REACH_M) & (lateral > lateral[level].max() - 0.02)
        lobe = skin[ear][skin[ear][:, 1].argmin()]
        centre = lobe + np.array([0.0, EARRING["through"] - EARRING["major"], 0.0])
        path = circle(centre, np.array([1.0, 0.0, 0.0]), EARRING["major"], 40)
        points, faces, st = tube(path, EARRING["wire"], CHAIN["sides"])
        found[side] = (points, faces, st, lobe)
    return found


def necklace(skin, faces, neck, chest):
    """The chain at the bind: points, faces, st. `neck` the Neck1 joint's place, `chest` the Chest's. Each turn's
    place is where a ray out from the neck's middle first meets the skin, CHAIN["clear"] out."""
    axis = neck - chest
    axis /= np.linalg.norm(axis)
    centre = neck + axis * NECKLACE["over_neck"]
    turns = NECKLACE["turns"]
    angles = np.arange(turns) * 2.0 * np.pi / turns
    side, front = np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0])
    directions = np.cos(angles)[:, None] * side + np.sin(angles)[:, None] * front
    starts = centre - np.array([0.0, 1.0, 0.0]) * (NECKLACE["drop"] * np.clip(np.sin(angles), 0.0, None) ** 2)[:, None]
    mesh = trimesh.Trimesh(skin, faces, process=False)
    hits, rays, _ = mesh.ray.intersects_location(starts, directions, multiple_hits=True)
    reach = np.full(turns, np.nan)
    for ray in range(turns):
        mine = hits[rays == ray]
        if len(mine):
            reach[ray] = np.linalg.norm(mine - starts[ray], axis=1).min()
    known = np.flatnonzero(~np.isnan(reach))
    if len(known) == 0:
        raise SystemExit("a piece of jewellery finds no skin where it is worn")
    reach = np.interp(np.arange(turns), known, reach[known], period=turns)
    curve = starts + directions * (reach + CHAIN["clear"] + CHAIN["wire"])[:, None]
    return tube(curve, CHAIN["wire"], CHAIN["sides"])


def watch(skin, forearm, hand, lateral):
    """The watch at the bind: {"strap", "case", "dial", "glass": (points, faces, st)}. `lateral` the side the back
    of the wrist faces at the bind (the arm hangs palm in)."""
    axis = hand - forearm
    axis /= np.linalg.norm(axis)
    centre = hand - axis * WATCH["from_hand"]
    radius, first, second = round_off(skin, centre, axis, WATCH["slice"], WATCH["turns"],
                                      np.linalg.norm(np.cross(skin - centre, axis), axis=1) < 0.06)
    radius = radius + WATCH["clear"]
    angles = (np.arange(WATCH["turns"] + 1) + 0.5) * 2.0 * np.pi / WATCH["turns"]
    radius = np.append(radius, radius[0])
    directions = np.cos(angles)[:, None] * first + np.sin(angles)[:, None] * second
    half = WATCH["strap"] / 2.0
    rows = [(0.0, -half), (0.0, half), (WATCH["strap_thick"], half), (WATCH["strap_thick"], -half)]
    strap = np.concatenate([centre + directions * (radius + out)[:, None] + axis * along for out, along in rows])
    count = WATCH["turns"] + 1
    faces = []
    for row in range(4):
        nxt = (row + 1) % 4
        for column in range(count - 1):
            here, there = row * count + column, nxt * count + column
            faces += [[here, there, here + 1], [here + 1, there, there + 1]]
    st = np.stack([np.tile(np.arange(count) / (count - 1), 4) * 2.0, np.repeat(np.arange(4) / 3.0, count)], axis=1)
    back = lateral - axis * (lateral @ axis)
    back /= np.linalg.norm(back)
    turn = np.arctan2(back @ second, back @ first) % (2.0 * np.pi)
    out = float(np.interp(turn, angles[:-1], radius[:-1], period=2.0 * np.pi)) + WATCH["strap_thick"]
    base = centre + back * out
    return {"strap": (strap, np.asarray(faces), st),
            "case": disc(base, back, WATCH["case"], WATCH["case_tall"], 48),
            "dial": disc(base + back * (WATCH["case_tall"] - 0.0002), back, WATCH["case"] * 0.86, 0.0001, 48),
            "glass": disc(base + back * WATCH["case_tall"], back, WATCH["case"] * 0.9, WATCH["glass"], 48)}


def fingers_at(skin, faces, hand_points, wrist, share):
    """The fingers of one hand cut across `share` of the way from the wrist to the fingertips: each finger's skin
    points there (the skin's triangles the cut crosses, joined edge to edge), ordered across the hand
    from the thinnest finger at one end (the little finger), and the hand's axis. SOMA's clips rig has no finger
    joints and the face's body's own finger joints stand up to 2 cm off its fingers (2026-11-24), so the fingers are
    read off the skin."""
    tip = hand_points[np.linalg.norm(hand_points - wrist, axis=1).argmax()]
    axis = (tip - wrist) / np.linalg.norm(tip - wrist)
    level = (hand_points - wrist) @ axis
    cut = wrist + axis * share * level.max()
    side = (skin - cut) @ axis
    corners = side[faces]
    crossing = (corners.min(axis=1) < 0.0) & (corners.max(axis=1) > 0.0)
    kept = faces[crossing & (np.linalg.norm(skin[faces].mean(axis=1) - cut, axis=1) < 0.08)]
    groups = trimesh.graph.connected_components(trimesh.graph.face_adjacency(kept), nodes=np.arange(len(kept)))
    fingers = [np.unique(kept[group]) for group in groups if len(group) >= RING["least"]]
    middles = np.array([skin[points].mean(axis=0) for points in fingers])
    across = np.linalg.svd(middles - middles.mean(axis=0))[2][0]
    order = np.argsort(middles @ across)
    sizes = [np.linalg.norm(np.cross(skin[fingers[number]] - middles[number], axis), axis=1).mean()
             for number in order]
    if sizes[-1] < sizes[0]:
        order = order[::-1]
    return [fingers[number] for number in order], axis


def ring(skin, faces, hand_points, wrist, finger):
    """A ring round the finger `finger` (counted from the little finger, 0) of one hand, on its first bone
    (RING["at"] of the way from the wrist to the fingertips): points, faces, st."""
    fingers, axis = fingers_at(skin, faces, hand_points, wrist, RING["at"])
    if len(fingers) < 4:
        raise SystemExit(f"a ring finds {len(fingers)} fingers where the rings are worn, not four")
    points = skin[fingers[finger]]
    centre = points.mean(axis=0)
    radius = np.linalg.norm(np.cross(points - centre, axis), axis=1).max()
    path = circle(centre, axis, float(radius) + RING["clear"] + RING["wire"], 40)
    return tube(path, RING["wire"], CHAIN["sides"])


def deepest(points_frames, skin_frames, skin_faces):
    """How far a piece goes into the skin at its deepest over the frames (m, 0 when never in)."""
    worst = 0.0
    for points, skin in zip(points_frames, skin_frames):
        mesh = trimesh.Trimesh(skin, skin_faces, process=False)
        nearest, _, triangle = trimesh.proximity.closest_point(mesh, points)
        into = -np.einsum("pi,pi->p", points - nearest, mesh.face_normals[triangle])
        worst = max(worst, float(into.max()))
    return worst


def faults(found):
    """Each piece past its limit, one line each."""
    lines = [f"{name} through the skin: {value} mm into it (limit {INTO_LIMIT_M * 1000.0:.0f})"
             for name, value in found.get("into the skin mm", {}).items() if value > INTO_LIMIT_M * 1000.0]
    lines += [f"{name} out of its lobe: its top {value} mm off it (limit {LOBE_LIMIT_M * 1000.0:.0f})"
              for name, value in found.get("hoop top off the lobe mm", {}).items() if value > LOBE_LIMIT_M * 1000.0]
    return lines
