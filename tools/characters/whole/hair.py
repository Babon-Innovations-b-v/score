"""A person's strand hair combed on the head it is worn on (#223): roots on that head's own scalp, each strand laid
from its root by the style (`data/people/hair/<look>.json`: its length, wave, parting and fringe), and the checks
that fail a groom that does not sit on its head.

The groom grown in Blender on the made person's hair shell (`../hair/groom.py`, #227) does not fit the face's head
the whole person wears: brought onto it point by point (each point dropped to its nearest skin), whole rows of
strands collapsed into flat blocks over the eyes, the crown showed bald and strands stood out straight
(2026-11-25). So the hair is combed again here on the worn head, at the build's bind, in the rig's frame (y up, the
face looking along +z, the person's left +x):

- `scalp_mask`: the head's skin above its hairline, read off the eyes (the head's middle behind them): HAIRLINE gives
  the hairline's height over the eyes round the head (the forehead's front, the temples, over the ears, the nape),
  and the ears (skin standing EAR_OUT_M further off the head's upright than the skull round it) are left out.
- `combed`: ROOTS roots on the scalp by area; each strand stepped STEP_M at a time away from the parting (the style's
  side and offset; the parting ends at the crown, the hair behind it combed straight back), turning to gravity below the
  crown, lying LAYER over the skin (a strand rooted nearer the parting higher, as hair lies over the hair rooted under
  it), free once below the head's widest (HUG_OVER_EYES_M) so the bob hangs as a curtain. A strand in front of the head
  never falls over the face: within the face's width it runs across (the fringe to the style's fringe side) until it is
  past the eyes. Its end falls at the bob's line (END_BELOW_EYES_M under the eyes, spread ENDS_SPREAD_M), its tip turned
  in; the style's wave across it; POINTS points, its radius tapered RADIUS.

`measured` reads the groom on its head and `faults` names what is past a limit:
- roots off the scalp: a root further than ROOT_OFF_M from the scalp's skin (off the skin, or on the face or an ear);
- strands before the eyes: any strand point in the box before the eyes (EYE_BOX: past their outer corners, from
  over the brows to the cheeks, in front of the eyeballs' middles);
- bald scalp: the share of the scalp whose outward column (COVER_RADIUS_M wide, COVER_DEPTH_M deep) holds no hair;
- clumps: the most strands in one CLUMP_CELL_M cell over the 99th percentile of the cells holding hair;
- strays: strand points standing further than STRAY_M off the skin over the eyes (a strand standing out straight).
"""
import numpy as np
import trimesh
from scipy.spatial import cKDTree

ROOTS = 42000
POINTS = 32
STEP_M = 0.003
RADIUS = (0.00012, 0.00003)  # a strand's radius at its root and its tip (groom.py's)
# The hairline's height over the eyes' middle (m) round the head, by the angle off the face's front (degrees): the
# forehead's front, the temples, over the ear, behind it, the nape.
HAIRLINE = ((0.0, 0.072), (30.0, 0.066), (55.0, 0.045), (75.0, 0.030), (95.0, 0.032), (115.0, -0.030),
            (140.0, -0.060), (180.0, -0.072))
EAR_OUT_M = 0.010  # skin this much further off the head's upright than the skull at its height and angle is an ear
SURFACE_M = 0.0012  # the head's skin is read at about this spacing as strands are stepped over it
CROWN_ABOVE_EYES_M = 0.10  # the turn to gravity starts this far over the eyes
FALL_M = 0.06  # and is whole this far under that
HUG_OVER_EYES_M = -0.005  # over this height the hair lies on the head; under it it hangs
LAYER = (0.0015, 0.014)  # how far a strand lies off the skin: from the hairline's roots to the parting's
ROOT_RISE_M = 0.012  # along which a strand rises from its root to its layer
FACE_HALF_M = 0.058  # the face's half width from the eyes' middle: a strand within it in front never falls
FACE_FRONT_M = 0.035  # a place this far in front of the head's middle is in front of the head
SWEEP_DOWN = 0.18  # how much a strand running across the forehead falls for each metre across
PART_ENDS_BEHIND_M = 0.02  # the parting ends this far behind the head's middle (the crown)
PART_FADE_M = 0.03  # over which the comb turns from across to straight back
TURN = 0.4  # how much of its wanted direction a strand lying on the head takes each step
TURN_HANGING = 0.8  # and one hanging: it drops as soon as it leaves the head
HANG_OUT = 0.08  # a hanging strand's lean out from the head's upright, for each metre down
END_BELOW_EYES_M = 0.105  # the bob's ends: the jaw and the neck's top under the eyes
ENDS_SPREAD_M = 0.012
TIP_IN_M = 0.03  # the last of a strand that turns in under the bob
TIP_TURN_M = 0.008  # how far its very tip turns in
SEED = 223
# The checks.
ROOT_OFF_M = 0.001
EYE_BOX = {"beside_m": 0.018, "over_m": 0.035, "under_m": 0.03, "behind_m": 0.0}  # round the eyes, m
COVER_RADIUS_M = 0.003
COVER_DEPTH_M = 0.03
COVER_SAMPLES = 6000
BALD_LIMIT = 0.005  # the scalp's share that may show through
CLUMP_CELL_M = 0.004
CLUMP_LIMIT = 4.0  # the most strands in a cell over the 99th percentile of the cells holding hair
STRAY_M = 0.035
DENSE_M = 0.002  # the strands are read at this spacing by the checks


def unit(vectors):
    return vectors / np.maximum(np.linalg.norm(vectors, axis=-1, keepdims=True), 1e-12)


def tangent(vectors, normals):
    """The vectors laid flat on the surface with `normals`, unit length."""
    return unit(vectors - normals * np.einsum("pi,pi->p", vectors, normals)[:, None])


def head_frame(points, eyes):
    """The eyes' middle, the head's middle (at the eyes' height, x and z of the skull's top) and its top's height."""
    middle = np.asarray(eyes, float).mean(axis=0)
    cap = points[points[:, 1] > middle[1] + 0.04]
    return middle, np.array([cap[:, 0].mean(), middle[1], cap[:, 2].mean()]), float(cap[:, 1].max())


def around(points, centre):
    """Each point's angle off the face's front round the head's upright (degrees, 0..180) and its distance off it."""
    flat = points[:, [0, 2]] - centre[[0, 2]]
    return np.degrees(np.abs(np.arctan2(flat[:, 0], flat[:, 1]))), np.linalg.norm(flat, axis=1)


def is_ear(points, centre, angle, radius):
    """Points beside the head standing EAR_OUT_M further off its upright than the skull's median at their height
    (1 cm rows) and angle (10 degree sectors)."""
    keys = np.round((points[:, 1] - centre[1]) / 0.01) * 100 + np.round(angle / 10.0)
    skull = np.zeros(len(points))
    for key in np.unique(keys):
        mine = keys == key
        skull[mine] = np.median(radius[mine])
    return (radius - skull > EAR_OUT_M) & (angle > 60.0) & (angle < 130.0)


def scalp_mask(points, faces, eyes):
    """Which of the skin's triangles are the scalp: every corner over the hairline (HAIRLINE), on the head and none an
    ear."""
    middle, centre, _ = head_frame(points, eyes)
    angle, radius = around(points, centre)
    table = np.asarray(HAIRLINE)
    over = points[:, 1] - middle[1] > np.interp(angle, table[:, 0], table[:, 1])
    near = (points[:, 1] > middle[1] - 0.12) & (radius < 0.16)
    keep = over & near & ~is_ear(points, centre, angle, radius)
    return keep[faces].all(axis=1)


def on_triangles(points, faces, count, rng):
    """`count` places on the triangles, by area."""
    corners = points[faces]
    area = np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1) / 2.0
    picked = rng.choice(len(faces), size=count, p=area / area.sum())
    weights = rng.dirichlet(np.ones(3), count)
    return np.einsum("pc,pcd->pd", weights, corners[picked]), picked, weights


def head_surface(points, faces, eyes):
    """The head's skin read every SURFACE_M or so: (places, their smooth outward normals, a tree of the places)."""
    middle = np.asarray(eyes, float).mean(axis=0)
    normals = np.asarray(trimesh.Trimesh(points, faces, process=False).vertex_normals)
    head = faces[(points[faces][..., 1] > middle[1] - 0.25).all(axis=1)]
    corners = points[head]
    area = np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1).sum() / 2.0
    places, picked, weights = on_triangles(points, head, int(area / SURFACE_M ** 2), np.random.default_rng(SEED + 2))
    return places, unit(np.einsum("pc,pcd->pd", weights, normals[head[picked]])), cKDTree(places)


def nearest_on(surface, places):
    """Each place's nearest point on the head's skin and the outward normal there."""
    _, index = surface[2].query(places)
    return surface[0][index], surface[1][index]


def comb(places, normals, side, sweep, middle, centre, hanging):
    """Each strand's wanted direction at its place: away from the parting (`side`, +1 on her left of it) and a little
    back over the head, turning to gravity below the crown, straight down once hanging; in front of the head within
    the face's width, across to `sweep` and only a little down."""
    count = len(places)
    down = np.tile([0.0, -1.0, 0.0], (count, 1))
    # The parting runs from the hairline to the crown only: behind it the hair is combed straight back and down, never
    # away from a parting down the back of the head (one there showed the scalp in a strip to the nape, 2026-11-25).
    behind = np.clip((centre[2] - places[:, 2] - PART_ENDS_BEHIND_M) / PART_FADE_M, 0.0, 1.0)
    away = np.stack([side * (1.0 - behind), np.zeros(count), -0.35 - 0.65 * behind], axis=1)
    over = tangent(away, normals)
    fall = np.clip((middle[1] + CROWN_ABOVE_EYES_M - places[:, 1]) / FALL_M, 0.0, 1.0)[:, None]
    direction = over * (1.0 - fall) + (over * 0.25 + tangent(down, normals)) * fall
    outward = np.zeros((count, 3))
    outward[:, [0, 2]] = places[:, [0, 2]] - centre[[0, 2]]
    direction[hanging] = down[hanging] + HANG_OUT * unit(outward[hanging])
    front = (places[:, 2] - centre[2] > FACE_FRONT_M) & (np.abs(places[:, 0] - middle[0]) < FACE_HALF_M)
    across = np.stack([sweep, np.full(count, -SWEEP_DOWN), np.zeros(count)], axis=1)
    direction[front] = tangent(across[front], normals[front])
    return unit(direction)


def stepped(points, faces, eyes, style, rng):
    """Every strand's path from its root (strands x steps x 3; a strand that ended stays at its last place)."""
    skin = head_surface(points, faces, eyes)
    middle, centre, top = head_frame(points, eyes)
    rooted = on_triangles(points, faces[scalp_mask(points, faces, eyes)], ROOTS, rng)[0]
    parting = middle[0] + (1.0 if style["parting_side"] == "left" else -1.0) * style["parting_m"]
    side = np.where(rooted[:, 0] > parting, 1.0, -1.0)
    sweep = np.where(side > 0.0, 1.0, 1.0 if style["fringe_side"] == "left" else -1.0)
    from_part = np.abs(rooted[:, 0] - parting) + np.maximum(0.0, top - rooted[:, 1]) * 0.6
    layer = LAYER[0] + (LAYER[1] - LAYER[0]) * (1.0 - np.clip(from_part / np.percentile(from_part, 98), 0.0, 1.0))
    ends = middle[1] - END_BELOW_EYES_M + rng.normal(0.0, ENDS_SPREAD_M / 2.0, len(rooted))
    place = rooted.copy()
    direction = None
    path, alive, travelled = [place.copy()], np.ones(len(place), dtype=bool), np.zeros(len(place))
    for _ in range(int(style["length_m"] / STEP_M)):
        _, normal = nearest_on(skin, place)
        hanging = place[:, 1] < middle[1] + HUG_OVER_EYES_M
        wanted = comb(place, normal, side, sweep, middle, centre, hanging)
        turn = np.where(hanging, TURN_HANGING, TURN)[:, None]
        direction = wanted if direction is None else unit(direction * (1.0 - turn) + wanted * turn)
        moved = place + direction * STEP_M
        on, normal = nearest_on(skin, moved)
        height = np.einsum("pi,pi->p", moved - on, normal)
        wanted_height = layer * np.clip((travelled + STEP_M) / ROOT_RISE_M, 0.0, 1.0)
        free = moved[:, 1] < middle[1] + HUG_OVER_EYES_M
        lift = np.where(free, np.maximum(wanted_height - height, 0.0), wanted_height - height)
        moved = moved + normal * lift[:, None]
        alive &= moved[:, 1] > ends
        place = np.where(alive[:, None], moved, place)
        travelled += np.where(alive, STEP_M, 0.0)
        path.append(place.copy())
        if not alive.any():
            break
    return np.stack(path, axis=1), centre


def lengths_along(strands):
    """Each strand's length from its root at each of its points."""
    steps = np.linalg.norm(np.diff(strands, axis=1), axis=2)
    return np.concatenate([np.zeros((len(strands), 1)), np.cumsum(steps, axis=1)], axis=1)


def tipped(path, centre):
    """The strands' last TIP_IN_M turned in towards the head's upright under the bob."""
    lengths = lengths_along(path)
    share = np.clip(1.0 - (lengths[:, -1:] - lengths) / TIP_IN_M, 0.0, 1.0) ** 2
    inward = np.zeros_like(path)
    inward[..., [0, 2]] = centre[[0, 2]] - path[..., [0, 2]]
    return path + unit(inward) * (share * TIP_TURN_M)[..., None]


def resampled(path, count):
    """Each strand at `count` points evenly along its length."""
    lengths = lengths_along(path)
    found = np.zeros((len(path), count, 3))
    for index in range(len(path)):
        wanted = np.linspace(0.0, lengths[index, -1], count)
        for axis in range(3):
            found[index, :, axis] = np.interp(wanted, lengths[index], path[index, :, axis])
    return found


def waved(strands, style, rng):
    """The style's wave across each strand, rising from its root over ROOT_RISE_M."""
    across = unit(np.cross(np.gradient(strands, axis=1), np.array([0.0, 1.0, 0.0])))
    lengths = lengths_along(strands)
    phase = rng.uniform(0.0, 2.0 * np.pi, (len(strands), 1))
    amount = style["wave_m"] * np.sin(2.0 * np.pi * lengths / style["wave_period_m"] + phase)
    return strands + across * (amount * np.clip(lengths / ROOT_RISE_M, 0.0, 1.0))[..., None]


def combed(points, faces, eyes, style):
    """The groom on this head at the build's bind: (counts, points, radius), POINTS points a strand; a strand that
    never left its root is left out."""
    rng = np.random.default_rng(SEED)
    path, centre = stepped(points, faces, eyes, style, rng)
    moved = np.linalg.norm(path[:, -1] - path[:, 0], axis=1) > 0.02
    strands = waved(resampled(tipped(path[moved], centre), POINTS), style, rng)
    radius = np.tile(np.linspace(RADIUS[0], RADIUS[1], POINTS), len(strands))
    return np.full(len(strands), POINTS, np.int64), strands.reshape(-1, 3), radius


def dense(counts, points):
    """The strands read every DENSE_M: (places, the strand each is on)."""
    found, owner, start = [], [], 0
    for index, count in enumerate(counts):
        strand = points[start:start + count]
        start += count
        lengths = lengths_along(strand[None])[0]
        wanted = np.arange(0.0, lengths[-1] + 1e-9, DENSE_M)
        found.append(np.stack([np.interp(wanted, lengths, strand[:, axis]) for axis in range(3)], axis=1))
        owner.append(np.full(len(wanted), index))
    return np.concatenate(found), np.concatenate(owner)


def before_eyes(places, eyes):
    """Which places are in the box before the eyes (EYE_BOX)."""
    eyes = np.asarray(eyes, float)
    middle = eyes.mean(axis=0)
    return ((places[:, 0] > eyes[:, 0].min() - EYE_BOX["beside_m"])
            & (places[:, 0] < eyes[:, 0].max() + EYE_BOX["beside_m"])
            & (places[:, 1] < middle[1] + EYE_BOX["over_m"]) & (places[:, 1] > middle[1] - EYE_BOX["under_m"])
            & (places[:, 2] > middle[2] - EYE_BOX["behind_m"]))


def bald_share(places, points, faces, eyes):
    """The share of the scalp whose outward column holds no hair."""
    scalp = faces[scalp_mask(points, faces, eyes)]
    samples, picked, weights = on_triangles(points, scalp, COVER_SAMPLES, np.random.default_rng(SEED + 1))
    normals = np.asarray(trimesh.Trimesh(points, faces, process=False).vertex_normals)
    normal = unit(np.einsum("pc,pcd->pd", weights, normals[scalp[picked]]))
    tree = cKDTree(places)
    covered = np.zeros(len(samples), dtype=bool)
    for depth in np.arange(COVER_RADIUS_M, COVER_DEPTH_M, COVER_RADIUS_M):
        covered |= np.isfinite(tree.query(samples + normal * depth, distance_upper_bound=COVER_RADIUS_M)[0])
    return float(1.0 - covered.mean())


def clump_ratio(places, owner):
    """The most strands in one CLUMP_CELL_M cell over the 99th percentile of the cells holding hair."""
    cells = np.floor(places / CLUMP_CELL_M).astype(np.int64)
    strands_in = np.unique(np.concatenate([cells, owner[:, None]], axis=1), axis=0)[:, :3]
    _, per_cell = np.unique(strands_in, axis=0, return_counts=True)
    return float(per_cell.max() / np.percentile(per_cell, 99))


def measured(counts, points, skin_points, skin_faces, eyes):
    """The groom read on its head at the build's bind (the checks the module docstring names)."""
    from tools.characters import whole
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    scalp = trimesh.Trimesh(skin_points, skin_faces[scalp_mask(skin_points, skin_faces, eyes)], process=False)
    off = whole.closest(scalp, points[starts])[1]
    mesh = trimesh.Trimesh(skin_points, skin_faces, process=False)
    places, owner = dense(counts, points)
    middle = np.asarray(eyes, float).mean(axis=0)
    high = places[places[:, 1] > middle[1]]
    stand = whole.closest(mesh, high)[1] if len(high) else np.zeros(1)
    return {"strands": int(len(counts)),
            "roots off the scalp": int((off > ROOT_OFF_M).sum()),
            "root farthest off the scalp mm": round(float(off.max()) * 1000.0, 2),
            "points before the eyes": int(before_eyes(places, eyes).sum()),
            "scalp bald share": round(bald_share(places, skin_points, skin_faces, eyes), 4),
            "clump ratio": round(clump_ratio(places, owner), 2),
            "farthest off the skin over the eyes mm": round(float(stand.max()) * 1000.0, 1)}


def faults(found):
    """What is past its limit, one line each."""
    lines = []
    if found["roots off the scalp"]:
        lines.append(f"hair: {found['roots off the scalp']} roots off the scalp (limit 0, {ROOT_OFF_M * 1000:.0f} mm)")
    if found["points before the eyes"]:
        lines.append(f"hair: {found['points before the eyes']} strand points in front of the eyes (limit 0)")
    if found["scalp bald share"] > BALD_LIMIT:
        lines.append(f"hair: {found['scalp bald share']:.1%} of the scalp bald (limit {BALD_LIMIT:.1%})")
    if found["clump ratio"] > CLUMP_LIMIT:
        lines.append(f"hair: a clump of {found['clump ratio']:.1f} times the dense hair's strands (limit "
                     f"{CLUMP_LIMIT:.1f})")
    if found["farthest off the skin over the eyes mm"] > STRAY_M * 1000.0:
        lines.append(f"hair: a strand standing {found['farthest off the skin over the eyes mm']:.0f} mm off the head "
                     f"(limit {STRAY_M * 1000.0:.0f})")
    return lines
