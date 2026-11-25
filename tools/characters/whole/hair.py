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
- `combed`: ROOTS roots on the scalp by area (`roots`), thinning out over HAIRLINE_SOFT_M either side of the hairline,
  the strands rooted there fine and short (FINE_LENGTH_M, FINE_RADIUS) as a real hairline's are (a hard edge of full
  strands read as a wig's, owner 2026-11-25); each strand stepped STEP_M at a time away from the parting (the style's
  side and offset; the parting ends at the crown, the hair behind it combed back and out), the roots within
  PART_CROSS_M of it first leaning across it (`part_lean`: combed straight away from their first step, the hair of the
  two sides left a bare strip some 5 to 10 mm wide, "hairline is also still just crazy gap", owner 2026-11-25), each
  strand with its own lean (LEAN) and layer (LAYER_SPREAD) so the hair is not laid in flat sheets, turning to gravity
  below the crown, lying LAYER over the skin (a strand rooted nearer the parting higher, as hair lies over the hair
  rooted under it), free once below the head's widest (HUG_OVER_EYES_M) so the bob hangs as a curtain, one the skin
  holds from falling moved out over it (`draped`). A strand in
  front of the head never falls over the face: within the face's width it runs across (the fringe to the style's
  fringe side) until it is past the eyes. Its end falls at the bob's line (END_BELOW_EYES_M under the eyes, spread
  ENDS_SPREAD_M), its tip turned in; the style's wave across it; POINTS points, its radius tapered RADIUS.

`measured` reads the groom on its head and `faults` names what is past a limit:
- roots off the scalp: a root further than ROOT_OFF_M from the scalp's skin (off the skin, or on the face or an ear);
- strands before the eyes: any strand point in the box before the eyes (EYE_BOX: past their outer corners, from
  over the brows to the cheeks, in front of the eyeballs' middles);
- bald scalp: the share of the scalp whose outward column (COVER_RADIUS_M wide, COVER_DEPTH_M deep) holds no hair;
- clumps: the most strands in one CLUMP_CELL_M cell over the 99th percentile of the cells holding hair;
- strays: strand points standing further than STRAY_M off the skin over the eyes (a strand standing out straight);
- a wide parting: the widest run of scalp across the parting no strand covers seen from straight above, at stations
  along it from the hairline to the crown (`parting_bare`, past PART_BARE_M);
- gaps in the roots: a place on the scalp further than ROOT_GAP_M from its nearest root (`root_gap`);
- a hard hairline: the forehead's root density per area of skin rising from a tenth to nine tenths of the hair's full
  density over less than HAIRLINE_SOFT_LIMIT_M (`hairline_soft`).
"""
import numpy as np
import trimesh
from scipy.spatial import cKDTree

ROOTS = 80000
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
LAYER_SPREAD = 0.35  # each strand's own layer, varied by up to this share of it (one layer read as flat sheets)
LEAN = 0.12  # each strand's own level lean off the comb on the head, a share of its direction (one read as sheets)
PART_CROSS_M = 0.01  # roots this near the parting may first lean across it, as roots grow, before the comb turns
PART_LEAN = 2.5  # them away: up to this much of the comb's direction across it (a thin, uneven parting line)
HAIRLINE_SOFT_M = 0.006  # the roots thin out over this much either side of the hairline (no hard edge)
FINE_LENGTH_M = 0.012  # a fine hair at the soft hairline's outer edge is this long, full length at its inner edge
FINE_RADIUS = 0.4  # and this share of a strand's radius
ROOT_RISE_M = 0.012  # along which a strand rises from its root to its layer
FACE_HALF_M = 0.058  # the face's half width from the eyes' middle: a strand within it in front never falls
FACE_FRONT_M = 0.035  # a place this far in front of the head's middle is in front of the head
SWEEP_DOWN = 0.18  # how much a strand running across the forehead falls for each metre across
PART_ENDS_BEHIND_M = 0.02  # the parting ends this far behind the head's middle (the crown)
PART_FADE_M = 0.03  # over which the comb turns from across to straight back
TURN = 0.4  # how much of its wanted direction a strand lying on the head takes each step
TURN_HANGING = 0.8  # and one hanging: it drops as soon as it leaves the head
SNAG_DOWN = 0.7  # a hanging strand heading down at least this steeply that the skin holds is snagged (`draped`)
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
PART_BARE_M = 0.003  # the widest strip of scalp the parting may show from above (a real parting: a thin line)
PART_READ = {"across_m": 0.008, "on_m": 0.002, "station_m": 0.004, "cell_m": 0.0001, "fine_m": 0.0002,
             "upright": 0.6}
ROOT_GAP_M = 0.0025  # no place on the scalp further than this from a root
HAIRLINE_SOFT_LIMIT_M = 0.006  # the forehead's root density rises from a tenth to nine tenths over at least this
HAIRLINE_READ = {"front_deg": 45.0, "from_m": -0.01, "to_m": 0.02, "band_m": 0.001, "full_from_m": 0.01}


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


def over_hairline(points, eyes, centre):
    """Each point's height over the hairline (HAIRLINE) at its angle round the head (m, negative under it)."""
    angle, _ = around(points, centre)
    table = np.asarray(HAIRLINE)
    return points[:, 1] - np.asarray(eyes, float).mean(axis=0)[1] - np.interp(angle, table[:, 0], table[:, 1])


def scalp_mask(points, faces, eyes, under_m=0.0):
    """Which of the skin's triangles are the scalp: every corner over the hairline (HAIRLINE; lowered `under_m`, the
    soft hairline's fine hairs), on the head and none an ear."""
    middle, centre, _ = head_frame(points, eyes)
    angle, radius = around(points, centre)
    over = over_hairline(points, eyes, centre) > -under_m
    near = (points[:, 1] > middle[1] - 0.12) & (radius < 0.16)
    keep = over & near & ~is_ear(points, centre, angle, radius)
    return keep[faces].all(axis=1)


def roots(points, faces, eyes, rng):
    """ROOTS roots on the scalp by area, thinning out over HAIRLINE_SOFT_M either side of the hairline: (the roots,
    each one's share into the hair, 0 at the soft hairline's outer edge to 1 at its inner edge and over)."""
    _, centre, _ = head_frame(points, eyes)
    found, shares = [], []
    while sum(len(place) for place in found) < ROOTS:
        places = on_triangles(points, faces[scalp_mask(points, faces, eyes, HAIRLINE_SOFT_M)], ROOTS, rng)[0]
        share = np.clip((over_hairline(places, eyes, centre) + HAIRLINE_SOFT_M) / (2.0 * HAIRLINE_SOFT_M), 0.0, 1.0)
        kept = rng.random(len(places)) < share
        found.append(places[kept])
        shares.append(share[kept])
    return np.concatenate(found)[:ROOTS], np.concatenate(shares)[:ROOTS]


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
    _, index = surface[2].query(places, workers=-1)
    return surface[0][index], surface[1][index]


def comb(places, normals, side, sweep, middle, centre, hanging):
    """Each strand's wanted direction at its place: away from the parting (`side`, +1 on her left of it) and a little
    back over the head, turning to gravity below the crown, straight down once hanging; in front of the head within
    the face's width, across to `sweep` and only a little down."""
    count = len(places)
    down = np.tile([0.0, -1.0, 0.0], (count, 1))
    # The parting runs from the hairline to the crown only: behind it the hair is combed back and down, never away
    # from a parting down the back of the head (one there showed the scalp in a strip to the nape, 2026-11-25), and
    # back and out from the head's upright, never all straight back: on a round head straight back runs every strand
    # to the one point at the back of it, where they gathered in a clump (2026-11-25).
    behind = np.clip((centre[2] - places[:, 2] - PART_ENDS_BEHIND_M) / PART_FADE_M, 0.0, 1.0)[:, None]
    outward = np.zeros((count, 3))
    outward[:, [0, 2]] = places[:, [0, 2]] - centre[[0, 2]]
    back = unit(unit(outward) + [0.0, 0.0, -1.0])
    away = np.stack([side, np.zeros(count), np.full(count, -0.35)], axis=1) * (1.0 - behind) + back * behind
    over = tangent(away, normals)
    fall = np.clip((middle[1] + CROWN_ABOVE_EYES_M - places[:, 1]) / FALL_M, 0.0, 1.0)[:, None]
    direction = over * (1.0 - fall) + (over * 0.25 + tangent(down, normals)) * fall
    direction[hanging] = down[hanging] + HANG_OUT * unit(outward[hanging])
    front = (places[:, 2] - centre[2] > FACE_FRONT_M) & (np.abs(places[:, 0] - middle[0]) < FACE_HALF_M)
    across = np.stack([sweep, np.full(count, -SWEEP_DOWN), np.zeros(count)], axis=1)
    direction[front] = tangent(across[front], normals[front])
    return unit(direction)


def stepped(points, faces, eyes, style, rng):
    """Every strand's path from its root (strands x steps x 3; a strand that ended stays at its last place)."""
    skin = head_surface(points, faces, eyes)
    middle, centre, top = head_frame(points, eyes)
    rooted, inner = roots(points, faces, eyes, rng)
    parting = middle[0] + (1.0 if style["parting_side"] == "left" else -1.0) * style["parting_m"]
    side = np.where(rooted[:, 0] > parting, 1.0, -1.0)
    sweep = np.where(side > 0.0, 1.0, 1.0 if style["fringe_side"] == "left" else -1.0)
    from_part = np.abs(rooted[:, 0] - parting) + np.maximum(0.0, top - rooted[:, 1]) * 0.6
    layer = LAYER[0] + (LAYER[1] - LAYER[0]) * (1.0 - np.clip(from_part / np.percentile(from_part, 98), 0.0, 1.0))
    layer = layer * (1.0 + rng.uniform(-LAYER_SPREAD, LAYER_SPREAD, len(rooted)))
    lean = rng.normal(0.0, LEAN, (len(rooted), 3)) * [1.0, 0.0, 1.0]  # level: one leaning down crossed the eyes
    crossing = part_lean(rooted, side, parting, centre, rng)
    reach = FINE_LENGTH_M + (style["length_m"] - FINE_LENGTH_M) * inner
    ends = middle[1] - END_BELOW_EYES_M + rng.normal(0.0, ENDS_SPREAD_M / 2.0, len(rooted))
    place = rooted.copy()
    direction = None
    path, alive, travelled = [place.copy()], np.ones(len(place), dtype=bool), np.zeros(len(place))
    for _ in range(int(style["length_m"] / STEP_M)):
        _, normal = nearest_on(skin, place)
        hanging = place[:, 1] < middle[1] + HUG_OVER_EYES_M
        # The lean only while lying on the head: a hanging strand leaning in at the face's side ran before the eyes.
        wanted = unit(comb(place, normal, side, sweep, middle, centre, hanging) + lean * ~hanging[:, None])
        turn = np.where(hanging, TURN_HANGING, TURN)[:, None]
        direction = (unit(wanted + crossing) if direction is None
                     else unit(direction * (1.0 - turn) + wanted * turn))
        moved = place + direction * STEP_M
        on, normal = nearest_on(skin, moved)
        height = np.einsum("pi,pi->p", moved - on, normal)
        wanted_height = layer * np.clip((travelled + STEP_M) / ROOT_RISE_M, 0.0, 1.0)
        free = moved[:, 1] < middle[1] + HUG_OVER_EYES_M
        lift = np.where(free, np.maximum(wanted_height - height, 0.0), wanted_height - height)
        moved = moved + normal * lift[:, None]
        moved = draped(moved, place, direction, free, centre)
        alive &= (moved[:, 1] > ends) & (travelled + STEP_M <= reach)
        place = np.where(alive[:, None], moved, place)
        travelled += np.where(alive, STEP_M, 0.0)
        path.append(place.copy())
        if not alive.any():
            break
    return np.stack(path, axis=1), centre, inner


def draped(moved, place, direction, free, centre):
    """A hanging strand heading down that the skin held from going half its step down (snagged behind an ear, where
    the skin turns under, it stood still and was left out as a strand that never left its root, a hole of roots
    there, 2026-11-25) moved half a step out from the head's upright, so it falls over what holds it."""
    snagged = free & (direction[:, 1] < -SNAG_DOWN) & (moved[:, 1] - place[:, 1] > -0.5 * STEP_M * -direction[:, 1])
    outward = np.zeros((len(moved), 3))
    outward[:, [0, 2]] = moved[:, [0, 2]] - centre[[0, 2]]
    return moved + unit(outward) * (0.5 * STEP_M * snagged)[:, None]


def part_lean(rooted, side, parting, centre, rng):
    """Each root's first lean across the parting: roots within PART_CROSS_M of it lean over it by up to PART_LEAN
    (fading with their distance from it and behind the crown, where there is no parting), so the hair of both sides
    meets over a thin line instead of leaving a bare strip as wide as the hair's first steps."""
    behind = np.clip((centre[2] - rooted[:, 2] - PART_ENDS_BEHIND_M) / PART_FADE_M, 0.0, 1.0)
    near = np.clip(1.0 - np.abs(rooted[:, 0] - parting) / PART_CROSS_M, 0.0, 1.0)
    crossing = np.zeros((len(rooted), 3))
    crossing[:, 0] = -side * near * (1.0 - behind) * rng.uniform(0.0, PART_LEAN, len(rooted))
    return crossing


def lengths_along(strands):
    """Each strand's length from its root at each of its points."""
    steps = np.linalg.norm(np.diff(strands, axis=1), axis=2)
    return np.concatenate([np.zeros((len(strands), 1)), np.cumsum(steps, axis=1)], axis=1)


def tipped(path, centre):
    """The strands' last TIP_IN_M turned in towards the head's upright under the bob; a strand shorter than twice
    that (the hairline's fine hairs) less, none at all at TIP_IN_M, so its root stays on the scalp."""
    lengths = lengths_along(path)
    long = np.clip(lengths[:, -1:] / TIP_IN_M - 1.0, 0.0, 1.0)
    share = long * np.clip(1.0 - (lengths[:, -1:] - lengths) / TIP_IN_M, 0.0, 1.0) ** 2
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
    path, centre, inner = stepped(points, faces, eyes, style, rng)
    reach = FINE_LENGTH_M + (style["length_m"] - FINE_LENGTH_M) * inner
    moved = np.linalg.norm(path[:, -1] - path[:, 0], axis=1) > np.minimum(0.02, reach / 2.0)
    strands = waved(resampled(tipped(path[moved], centre), POINTS), style, rng)
    fine = FINE_RADIUS + (1.0 - FINE_RADIUS) * inner[moved]
    radius = (fine[:, None] * np.linspace(RADIUS[0], RADIUS[1], POINTS)[None]).reshape(-1)
    return np.full(len(strands), POINTS, np.int64), strands.reshape(-1, 3), radius


def dense(counts, points):
    """The strands read every DENSE_M: (places, the strand each is on)."""
    counts = np.asarray(counts, np.int64)
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    steps = np.linalg.norm(np.diff(points, axis=0), axis=1)
    steps[(starts + counts - 1)[:-1]] = 0.0  # no step from one strand's last point to the next one's root
    along = np.concatenate([[0.0], np.cumsum(steps)])  # length along every strand, run on through the next
    base, total = along[starts], along[starts + counts - 1] - along[starts]
    wanted = np.floor(total / DENSE_M + 1e-9).astype(np.int64) + 1
    owner = np.repeat(np.arange(len(counts)), wanted)
    at = base[owner] + (np.arange(len(owner)) - np.repeat(np.cumsum(wanted) - wanted, wanted)) * DENSE_M
    segment = np.clip(np.searchsorted(along, at, side="right") - 1, starts[owner], starts[owner] + counts[owner] - 2)
    share = np.clip((at - along[segment]) / np.maximum(steps[segment], 1e-12), 0.0, 1.0)
    return points[segment] + (points[segment + 1] - points[segment]) * share[:, None], owner


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
    cells -= cells.min(axis=0)
    span = cells.max(axis=0) + 1
    cell = (cells[:, 0] * span[1] + cells[:, 1]) * span[2] + cells[:, 2]  # one number a cell, so unique runs on 1-D
    strands_in = np.unique(cell * (int(owner.max()) + 1) + owner) // (int(owner.max()) + 1)
    _, per_cell = np.unique(strands_in, return_counts=True)
    return float(per_cell.max() / np.percentile(per_cell, 99))


def fine_samples(counts, points, radius, keep):
    """The strands' points with `keep` true, and every segment between two of them, read every PART_READ's fine_m:
    (places, their radius)."""
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    last = np.zeros(len(points), dtype=bool)
    last[starts + counts - 1] = True
    first = np.flatnonzero(~last & keep & np.roll(keep, -1))
    spans = np.linalg.norm(points[first + 1] - points[first], axis=1)
    pieces = np.maximum(1, np.ceil(spans / PART_READ["fine_m"]).astype(np.int64))
    segment = np.repeat(np.arange(len(first)), pieces)
    share = (np.arange(len(segment)) - np.repeat(np.cumsum(pieces) - pieces, pieces)) / pieces[segment]
    begin, end = first[segment], first[segment] + 1
    places = points[begin] + (points[end] - points[begin]) * share[:, None]
    return places, radius[begin] + (radius[end] - radius[begin]) * share


def parting_bare(counts, points, radius, skin_points, skin_faces, eyes, style):
    """The widest strip of scalp the parting shows from above (m): at every station along it (each PART_READ station_m
    from the hairline back to the crown, where the scalp faces up), the longest run of scalp across it (within
    across_m) that no strand covers and that reaches within on_m of the parting's line, a strand covering what lies
    within its radius of it seen from straight above."""
    middle, centre, _ = head_frame(skin_points, eyes)
    parting = middle[0] + (1.0 if style["parting_side"] == "left" else -1.0) * style["parting_m"]
    scalp = np.unique(skin_faces[scalp_mask(skin_points, skin_faces, eyes)])
    normals = np.asarray(trimesh.Trimesh(skin_points, skin_faces, process=False).vertex_normals)[scalp]
    upward = scalp[normals[:, 1] > PART_READ["upright"]]
    band = upward[np.abs(skin_points[upward, 0] - parting) < PART_READ["across_m"]]
    if not len(band):
        return 0.0
    keep = (np.abs(points[:, 0] - parting) < PART_READ["across_m"] + 0.005) & (points[:, 1] > skin_points[band, 1].min()
                                                                              - 0.005)
    places, widths = fine_samples(counts, points, radius, keep)
    tree, under = cKDTree(places[:, [0, 2]]), cKDTree(skin_points[upward][:, [0, 2]])
    across = np.arange(parting - PART_READ["across_m"], parting + PART_READ["across_m"], PART_READ["cell_m"])
    front, back = skin_points[band, 2].max(), max(skin_points[band, 2].min(), centre[2])
    widest = 0.0
    for station in np.arange(back, front, PART_READ["station_m"]):
        cells = np.stack([across, np.full(len(across), station)], axis=1)
        on_scalp = np.isfinite(under.query(cells, distance_upper_bound=0.003)[0])
        gap, index = tree.query(cells, distance_upper_bound=RADIUS[0])
        found = np.isfinite(gap)
        covered = found & (gap <= widths[np.minimum(index, len(widths) - 1)] + 1e-9)
        run, touches = 0, False
        for bare, on_line in zip(on_scalp & ~covered, np.abs(across - parting) < PART_READ["on_m"]):
            run, touches = (run + 1, touches or on_line) if bare else (0, False)
            widest = max(widest, run * PART_READ["cell_m"] * touches)
    return float(widest)


def root_gap(roots_at, skin_points, skin_faces, eyes):
    """The farthest any place on the scalp past the soft hairline (HAIRLINE_SOFT_M over it, where the roots are at
    their full density) lies from its nearest root (m)."""
    scalp = skin_faces[scalp_mask(skin_points, skin_faces, eyes, -HAIRLINE_SOFT_M)]
    samples = on_triangles(skin_points, scalp, COVER_SAMPLES, np.random.default_rng(SEED + 3))[0]
    return float(cKDTree(roots_at).query(samples)[0].max())


def hairline_soft(roots_at, skin_points, skin_faces, eyes):
    """Over how much (m) the forehead's root density, per area of skin, rises from a tenth to nine tenths of the
    hair's full density (HAIRLINE_READ: the forehead within front_deg of the face's front, read in band_m bands of
    height over the hairline, full from full_from_m over it): a hard hairline rises within one band."""
    _, centre, _ = head_frame(skin_points, eyes)
    head = skin_faces[(skin_points[skin_faces][..., 1] > np.asarray(eyes, float).mean(axis=0)[1]).all(axis=1)]
    skin = on_triangles(skin_points, head, ROOTS, np.random.default_rng(SEED + 4))[0]
    bands = np.arange(HAIRLINE_READ["from_m"], HAIRLINE_READ["to_m"] + 1e-9, HAIRLINE_READ["band_m"])

    def per_band(places):
        front = around(places, centre)[0] < HAIRLINE_READ["front_deg"]
        return np.histogram(over_hairline(places[front], eyes, centre), bins=bands)[0].astype(float)

    density = per_band(roots_at) / np.maximum(per_band(skin), 1.0)
    full = density[bands[:-1] >= HAIRLINE_READ["full_from_m"]].mean()
    middles = bands[:-1] + HAIRLINE_READ["band_m"] / 2.0
    low = middles[np.argmax(density >= 0.1 * full)]
    high = middles[np.argmax(density >= 0.9 * full)]
    return float(max(high - low, 0.0) + HAIRLINE_READ["band_m"])


def farthest_off(mesh, places):
    """The distances off the skin `mesh` of the places that may be the farthest: a place's nearest skin point lies on a
    triangle whose corners are all within the longest edge of it, so its distance is at least
    sqrt(corner^2 - edge^2) and at most `corner` (its nearest corner's); only places whose `corner` reaches the
    largest such floor are read. The farthest is exactly whole.closest's, read on a few places instead of millions."""
    from tools.characters import whole
    corner = cKDTree(mesh.vertices).query(places, workers=-1)[0]
    edge = float(mesh.edges_unique_length.max())
    floor = np.sqrt(np.maximum(corner ** 2 - edge ** 2, 0.0)).max()
    return whole.closest(mesh, places[corner >= floor])[1]


def measured(counts, points, skin_points, skin_faces, eyes, style, radius):
    """The groom read on its head at the build's bind (the checks the module docstring names)."""
    from tools.characters import whole
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    scalp = trimesh.Trimesh(skin_points, skin_faces[scalp_mask(skin_points, skin_faces, eyes, HAIRLINE_SOFT_M)],
                            process=False)
    off = whole.closest(scalp, points[starts])[1]
    mesh = trimesh.Trimesh(skin_points, skin_faces, process=False)
    places, owner = dense(counts, points)
    middle = np.asarray(eyes, float).mean(axis=0)
    high = places[places[:, 1] > middle[1]]
    stand = farthest_off(mesh, high) if len(high) else np.zeros(1)
    return {"strands": int(len(counts)),
            "roots off the scalp": int((off > ROOT_OFF_M).sum()),
            "root farthest off the scalp mm": round(float(off.max()) * 1000.0, 2),
            "points before the eyes": int(before_eyes(places, eyes).sum()),
            "scalp bald share": round(bald_share(places, skin_points, skin_faces, eyes), 4),
            "clump ratio": round(clump_ratio(places, owner), 2),
            "farthest off the skin over the eyes mm": round(float(stand.max()) * 1000.0, 1),
            "parting bare from above mm": round(parting_bare(counts, points, radius, skin_points, skin_faces, eyes,
                                                             style) * 1000.0, 1),
            "scalp farthest from a root mm": round(root_gap(points[starts], skin_points, skin_faces, eyes) * 1000.0, 2),
            "hairline soft over mm": round(hairline_soft(points[starts], skin_points, skin_faces, eyes) * 1000.0, 1)}


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
    if found["parting bare from above mm"] > PART_BARE_M * 1000.0:
        lines.append(f"hair: the parting bare {found['parting bare from above mm']:.1f} mm wide from above (limit "
                     f"{PART_BARE_M * 1000.0:.0f})")
    if found["scalp farthest from a root mm"] > ROOT_GAP_M * 1000.0:
        lines.append(f"hair: a gap in the roots, scalp {found['scalp farthest from a root mm']:.1f} mm from a root "
                     f"(limit {ROOT_GAP_M * 1000.0:.1f})")
    if found["hairline soft over mm"] < HAIRLINE_SOFT_LIMIT_M * 1000.0:
        lines.append(f"hair: a hard hairline, the roots thinning out over {found['hairline soft over mm']:.0f} mm "
                     f"(limit at least {HAIRLINE_SOFT_LIMIT_M * 1000.0:.0f})")
    return lines
