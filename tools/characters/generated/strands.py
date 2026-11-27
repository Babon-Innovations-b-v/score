"""The generated person's hair regrown as strands in the generated hair's own shape and flow (`regrown`).

Roots on the new scalp (`scalp.py`) where the hair grew (its `rooted` points: under the shell's hair, or behind the
neck where the hair hung over a neck the model never had; never under the chin, LOWEST_UNDER_EYES_M under the eyes in
front of SIDE_DEG, where a bust's open cut let round 1 root a beard on an old woman's chin), at a real head's density
(`../whole/hair.py`'s DENSITY rising over DENSITY_RISE_M from the hairline). The density fades from full into the skin
over FADE_M (`hairline_fade`; round 1 rose over hair.py's 2 mm, a hard edge), with hair.py's baby hairs in its
BABY_BAND_M band of the skin under the paint's hairline; behind the temples (FRONT_DEG round from the face) never under
hair.py's HAIRLINE table's nape, as the model's paint there is the hair hanging over the neck, not where it grows.

GUIDES guides are grown through the hair's volume (`volume.py`) along its own flow (`flow.py`: the shell's grooves
and paint streaks), trusted by how clearly the shell points (FLOW_TRUST over CLEAR), and where it does not point
clearly along the head's comb (hair.py's `comb` from the style's parting and the crown's whorl, falling with gravity,
the roots by the parting and the whorl first leaning over them; a style with a straight fringe falls straight down),
which also gives the flow its sign at the root. Each guide keeps its lock's place across the shell (`mended`: most
just under its outer surface, UNDER_OUTER_M, the rest at a layer through it; rising to it over ROOT_RISE_M from its
root), so the strands fill the shell to its outline; a guide meeting the volume's edge at a glance turns along it
(`along_edge`), one stepping out is drawn back in (`held_in`, `turned_in`), one heading out of it ends there (the
shell's end: shoulders, the bob's line, a fringe's edge), or at the style's length. The head's strands are grown from
the guides by hair.py's `grown` (each as long as its nearest guide, blended guides, locks, a soft point cut, the wave,
wisped baby hairs, flyaways and the crown's frizz, their sizes read off the close-up: `curl.py`), each a human hair's
radius tapered at the tip. The guides' ends are not turned in: the shell's own ends say where they go.
"""
import numpy as np
from scipy.spatial import cKDTree

from tools.characters.whole import hair
from tools.characters.generated import flow
from tools.characters.generated import volume as hair_space

GUIDES = 12000
FRONT_DEG = 60.0
GRACE_M = 0.006  # a strand may stand outside the volume this long from its root (rooted on its edge)
HUG_SHARE = 0.6  # this share of the locks lies near the shell's outer surface, UNDER_OUTER_M under it on average
UNDER_OUTER_M = 0.003  # (exponentially spread; the air's distance, `volume`'s `under`), the rest through the shell
# at a layer between LAYER (0 the scalp's side, 1 the outer surface): spread through a thick shell by its layer alone,
# the outside of a big head of hair was 75% covered, its grooves bare (2026-11-26)
UNDER_SPREAD = 0.25  # each guide's own depth round its lock's, a share of it
LAYER = (0.04, 0.98)
BABY_LAYER = 0.02
ROOT_RISE_M = 0.010  # along which a guide rises from its root to its layer
ROOT_OUT = 0.6  # leaving its root a guide rises out of the scalp this much (a share of its way) over ROOT_RISE_M
ENTER_LAYER = 0.12  # and is drawn at least this far in, so it enters a thin shell before GRACE_M (round 2's first
# try skimmed along the scalp under a 6 mm shell and ended there: four guides in ten 6 mm long)
CORRECT = 0.25  # how much of its layer's error a strand mends each step, never more than a step
FLOW_TRUST = 0.9  # how much a guide takes the shell's own flow where it points clearly
CLEAR = (0.08, 0.35)  # the flow's coherence from which it is trusted at all, and fully
HOLD_M = 0.006  # a guide stepping out of the volume is drawn back in by up to this (`held_in`)
HOLD_ON = 0.5  # where its step still goes on this share of a step its way
EDGE_M = 0.004
TURN_IN = (0.5, 1.0, 2.0)
TURN_IN_ON = 0.25
GLANCE = 0.7
SMOOTH_STEPS = 2.5  # a guide's path smoothed along itself over this many steps (Gaussian), its root held: held in a
# thin shell and drawn to its layer step by step, it zigzagged some 400 degrees each 10 cm (2026-11-26)
FADE_M = 0.004  # the roots' density fades from full into the skin over this from the paint's hairline
SIDE_DEG = 100.0
LOWEST_UNDER_EYES_M = 0.04
# the forehead (this far round from the face) never roots more than `under_table_m` under hair.py's HAIRLINE table: a
# fringe painted onto the forehead is hair lying on skin, and rooted there it grew a clump down onto the brows
# (round 3, 2026-11-27: an older woman's fringe, roots 1.6 to 4.6 cm over the eyes)
FOREHEAD = {"deg": 25.0, "under_table_m": 0.02}
SEED = 223
BEHIND_BLEND_M = 0.03
CANDIDATES = 400000  # places on the scalp a root is drawn from


def roots_on(scalp, skin, hairline, frame, rng, count=None):
    """Roots: (places, 1 for a full hair's and 0 for a baby hair's). Over the scalp's hole by its depth from the seam,
    on the skin within BABY_BAND_M of the hairline (`hairline`: places on the hair's edge) as baby hairs; `count` of
    them, or as many as a head holds."""
    hole = scalp["triangles"][scalp["rooted"][scalp["triangles"]].all(axis=1)]
    on_scalp, picked, _ = hair.on_triangles(scalp["points"], hole, CANDIDATES, rng)
    band, band_over = baby_band(skin, hairline, rng, CANDIDATES / scalp_area(scalp["points"], hole))
    candidates = np.vstack([on_scalp, band])
    over = np.concatenate([scalp["depth"][hole[picked]].mean(axis=1), band_over])
    share = hairline_fade(over) * full_density(over) / hair.DENSITY["vertex"] * grows_here(candidates, frame)
    scalp_share = len(on_scalp) / len(candidates)
    area = scalp_area(scalp["points"], hole) / scalp_share
    wanted = count or int(area * np.mean(share) * hair.DENSITY["vertex"])
    chosen = rng.choice(len(candidates), size=wanted, p=share / share.sum())
    jitter = rng.normal(0.0, hair_space.SAMPLE_M * 0.5, (wanted, 3))
    return candidates[chosen] + jitter, (over[chosen] >= 0.0).astype(float)


def hairline_fade(over):
    """The roots' density, a share of the full, at `over` (m) over the paint's hairline: hair.py's baby band under it,
    rising from the band's top to full over FADE_M over it (smoothly)."""
    rise = np.clip(over / FADE_M, 0.0, 1.0)
    rise = rise * rise * (3.0 - 2.0 * rise)
    top = hair.BABY_DENSITY[1]
    return np.where(over < 0.0, hair.root_density(np.minimum(over, 0.0)), top + (1.0 - top) * rise)


def full_density(over):
    """The scalp's full root density (hairs a m2) `over` m over the hairline: the temples' at it, the vertex's
    DENSITY_RISE_M over it."""
    rise = np.clip(over / hair.DENSITY_RISE_M, 0.0, 1.0)
    return hair.DENSITY["temple"] + (hair.DENSITY["vertex"] - hair.DENSITY["temple"]) * rise


def grows_here(places, frame):
    """1 where hair grows: in front of FRONT_DEG round from the face wherever the paint says (on the forehead never
    FOREHEAD's under hair.py's HAIRLINE table), behind it only over the table (less its baby band); in front of
    SIDE_DEG never LOWEST_UNDER_EYES_M under the eyes."""
    angle, _ = hair.around(places, frame["centre"])
    over = hair.over_hairline(places, frame["eyes"], frame["centre"])
    chin = (angle < SIDE_DEG) & (places[:, 1] < frame["eyes_middle"][1] - LOWEST_UNDER_EYES_M)
    forehead = (angle < FOREHEAD["deg"]) & (over < -FOREHEAD["under_table_m"])
    return (((angle < FRONT_DEG) | (over > -hair.BABY_BAND_M)) & ~chin & ~forehead).astype(float)


def baby_band(skin, hairline, rng, per_m2):
    """Places on the skin within BABY_BAND_M of the hairline, `per_m2` of them for each m2,
    and their (negative) height over it."""
    points, faces = skin
    middles = points[faces].mean(axis=1)
    distance = cKDTree(hairline).query(middles, workers=-1)[0]
    near = faces[distance < hair.BABY_BAND_M]
    if not len(near):
        return np.zeros((0, 3)), np.zeros(0)
    places = hair.on_triangles(points, near, int(per_m2 * scalp_area(points, near)), rng)[0]
    return places, -cKDTree(hairline).query(places, workers=-1)[0]


def scalp_area(points, faces):
    """The triangles' area (m2)."""
    corners = points[faces]
    return float(np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1)
                 .sum() / 2.0)


def parting(scalp, frame, style):
    """The parting curve on the scalp (hair.py's `parting_line`), or None for a style with none (combed from the
    crown, or swept back to it)."""
    if style.get("parting") in ("none", "back"):
        return None
    faces = scalp["triangles"][scalp["rooted"][scalp["triangles"]].all(axis=1)]
    return hair.parting_line(scalp["points"], faces, frame["eyes"], style)[0]


def sides(places, line):
    """Each place's side of the parting (+1 or -1; all +1 without one)."""
    return np.ones(len(places)) if line is None else hair.parted(places, line)[0]


def from_crown(places, normals, whorl, middle):
    """A crown-combed style's way at each place: straight out of the whorl over the head, falling below the crown,
    straight down in front of the face (a fringe)."""
    out = places - whorl
    out[:, 1] = 0.0
    fall = np.clip((middle[1] + hair.CROWN_ABOVE_EYES_M - places[:, 1]) / hair.FALL_M, 0.0, 1.0)[:, None]
    down = np.tile([0.0, -1.0, 0.0], (len(places), 1))
    return hair.unit(hair.tangent(hair.unit(out) * (1.0 - fall) + down * fall, normals))


def wanted_way(places, normals, line, sweep, frame, whorl, back):
    """Each strand's wanted direction (before it is laid on the volume's layers): behind the whorl straight out of it
    and down (`from_crown`); in front of it the comb away from the parting (hair.py's `comb`), or for a style swept
    `back` towards the whorl; blended over BEHIND_BLEND_M (combed away from the parting behind the whorl too, the back
    of the head parted bare down its middle, 2026-11-26)."""
    middle, centre = frame["eyes_middle"], frame["centre"]
    crown = from_crown(places, normals, whorl, middle)
    if line is None and not back:
        return crown
    if back:
        towards = whorl - places
        towards[:, 1] = 0.0
        front = hair.unit(hair.tangent(hair.unit(towards), normals))
    else:
        hanging = places[:, 1] < middle[1] + hair.HUG_OVER_EYES_M
        front = hair.comb(places, normals, line, sweep, middle, centre, hanging)
    behind = np.clip((whorl[2] - places[:, 2]) / BEHIND_BLEND_M + 0.5, 0.0, 1.0)[:, None]
    return hair.unit(front * (1.0 - behind) + crown * behind)


def depths_of(rooted, lock, rng):
    """Each guide's place across the shell: (its depth under the outer surface (m), or nan for a guide held at a
    layer; its layer). HUG_SHARE of the locks lie UNDER_OUTER_M under the surface (exponentially spread), the rest at
    a layer drawn evenly from LAYER; each guide varied round its lock's by UNDER_SPREAD."""
    hugging = rng.random(len(rooted)) < HUG_SHARE
    lock_depth = np.where(hugging, rng.exponential(UNDER_OUTER_M, len(rooted)), np.nan)
    lock_layer = rng.uniform(*LAYER, len(rooted))
    spread = 1.0 + rng.uniform(-UNDER_SPREAD, UNDER_SPREAD, len(rooted))
    return lock_depth[lock] * spread, np.clip(lock_layer[lock] * spread, *LAYER)


def across_at(space, place):
    """The way out through the shell's layers at each place (the volume's edge's outward way where the layer has
    none)."""
    across = hair_space.read(space, "across", place)
    norm = np.linalg.norm(across, axis=1, keepdims=True)
    return np.where(norm > 0.5, across / np.maximum(norm, 1e-9), -hair.unit(hair_space.read(space, "gradient", place)))


def mended(space, place, depth, layer, inner, travelled):
    """Each guide's move across the shell this step towards its place in it (at most a step): a hugging guide's
    towards its depth under the outer surface, the rest towards their layer, both rising from the root over
    ROOT_RISE_M (entering at least ENTER_LAYER); a baby hair stays at BABY_LAYER."""
    rise = np.clip(travelled / ROOT_RISE_M, 0.0, 1.0)
    across = across_at(space, place)
    layer = np.where(inner > 0, layer, BABY_LAYER)
    target = np.maximum(layer * rise, np.minimum(layer, ENTER_LAYER))
    error = (target - hair_space.read(space, "layer", place)) * hair_space.read(space, "thick", place)
    move = across * np.clip(CORRECT * error, -hair.STEP_M, hair.STEP_M)[:, None]
    hugging = np.isfinite(depth) & (inner > 0) & (rise >= 1.0)
    under = hair_space.read(space, "under", place) - np.nan_to_num(depth)
    out = hair.unit(hair_space.read(space, "outward", place))
    hug = out * np.clip(CORRECT * under, -hair.STEP_M, hair.STEP_M)[:, None]
    return np.where(hugging[:, None], hug, move)


def signed(axis, reference):
    """The flow's axis turned to run with `reference` (a way and its reverse are one axis)."""
    return axis * np.where(np.einsum("pi,pi->p", axis, reference) < 0.0, -1.0, 1.0)[:, None]


def flow_way(space, field, place, prior, direction):
    """Each guide's wanted way: the shell's flow where it points clearly, the comb's `prior` where it does not. The
    flow is signed by the guide's last step and the comb together (at the root by the comb), so a guide never runs
    against the comb: signed by its last step alone it ran round a painted curl's flow and never reached the shoulders
    (2026-11-26)."""
    axis, clear = flow.read_axis(field, space, place)
    axis = signed(axis, prior if direction is None else hair.unit(direction + prior))
    trust = FLOW_TRUST * np.clip((clear - CLEAR[0]) / (CLEAR[1] - CLEAR[0]), 0.0, 1.0)[:, None]
    return hair.unit(trust * axis + (1.0 - trust) * prior)


def along_edge(space, place, direction):
    """The ways of guides within EDGE_M of the volume's edge heading out of it at a glance (no steeper than GLANCE,
    the cosine with the edge's inward way) turned along the edge; one heading out steeper keeps its way and ends (the
    shell's end). Drawn back in only after each step, three guides in ten on a long wavy head ended halfway down at a
    glancing edge (2026-11-26)."""
    inward = hair.unit(hair_space.read(space, "gradient", place))
    facing = np.einsum("pi,pi->p", direction, inward)
    near = hair_space.read(space, "depth", place) < EDGE_M
    turned = near & (facing < 0.0) & (facing > -GLANCE)
    return np.where(turned[:, None], hair.unit(direction - facing[:, None] * inward), direction)


def held_in(space, place, direction, moved):
    """The step's place drawn back into the volume where it left it (along the volume's inward gradient, by up to
    HOLD_M), kept where the step still goes on at least HOLD_ON of a step the guide's way (a glancing exit through a
    thin shell's side), else left outside (heading out of the shell's end): (the places, whether each lies inside)."""
    inside = hair_space.read(space, "filled", moved) > 0.5
    inward = hair.unit(hair_space.read(space, "gradient", moved))
    held = moved.copy()
    for reach in np.arange(1, int(round(HOLD_M / hair_space.VOXEL_M)) + 1) * hair_space.VOXEL_M:
        trying = ~inside & (hair_space.read(space, "filled", moved + inward * reach) > 0.5)
        onward = np.einsum("pi,pi->p", moved + inward * reach - place, direction) > HOLD_ON * hair.STEP_M
        took = trying & onward
        held = np.where(took[:, None], moved + inward * reach, held)
        inside |= took
    return turned_in(space, place, direction, held, inside)


def turned_in(space, place, direction, held, inside):
    """The guides still outside after `held_in` stepped again turned towards the volume's inside (TURN_IN, shares of
    its inward way added to their own), where that step lands inside and still goes on TURN_IN_ON of a step their way:
    a long wavy head's guides left its bumpy outer surface head-on halfway down and ended there (2026-11-26)."""
    inward = hair.unit(hair_space.read(space, "gradient", place))
    for share in TURN_IN:
        step = hair.unit(direction + inward * share) * hair.STEP_M
        trying = ~inside & (hair_space.read(space, "filled", place + step) > 0.5)
        took = trying & (np.einsum("pi,pi->p", step, direction) > TURN_IN_ON * hair.STEP_M)
        held = np.where(took[:, None], place + step, held)
        inside |= took
    return held, inside


def guides_grown(space, field, rooted, inner, line, frame, style, rng):
    """Every guide's path through the volume (guides x steps x 3; a guide that ended stays at its last place) and
    each guide's lock (its middle guide's index)."""
    side = sides(rooted, line)
    fringe = style.get("fringe_side", "none")
    sweep = (np.where(side > 0.0, 1.0, 1.0 if fringe == "left" else -1.0) if fringe in ("left", "right")
             else np.zeros(len(rooted)) if fringe == "down" else side)
    lock = hair.locks(rooted, side, rng)
    depth, layer = depths_of(rooted, lock, rng)
    whorl = line[-1] if line is not None else crown_whorl(rooted, frame)
    lean = rng.normal(0.0, 1.0, (len(rooted), 3)) * [1.0, 0.0, 1.0] * np.where(inner > 0, hair.LEAN,
                                                                               hair.BABY_LEAN)[:, None]
    reach = np.where(inner > 0, style["length_m"], rng.uniform(*hair.BABY_LENGTH_M, len(rooted)))
    crossing = hair.part_lean(rooted, line, rng) if line is not None else whorl_lean(rooted, whorl, rng)
    place, direction = rooted.copy(), None
    path, alive, travelled = [place.copy()], np.ones(len(place), dtype=bool), np.zeros(len(place))
    for _ in range(int(style["length_m"] / hair.STEP_M)):
        across = across_at(space, place)
        prior = wanted_way(place, across, line, sweep, frame, whorl, style.get("parting") == "back")
        wanted = hair.unit(hair.tangent(flow_way(space, field, place, prior, direction) + lean, across))
        rising = np.clip(1.0 - travelled / ROOT_RISE_M, 0.0, 1.0)[:, None]
        wanted = hair.unit(wanted + across * ROOT_OUT * rising * (inner > 0)[:, None])
        direction = (hair.unit(wanted + crossing) if direction is None
                     else hair.unit(direction * (1.0 - hair.TURN) + wanted * hair.TURN))
        direction = along_edge(space, place, direction)
        moved, inside = held_in(space, place, direction, place + direction * hair.STEP_M
                                + mended(space, place, depth, layer, inner, travelled))
        alive &= (inside | (travelled < GRACE_M)) & (travelled + hair.STEP_M <= reach)
        place = np.where(alive[:, None], moved, place)
        travelled += np.where(alive, hair.STEP_M, 0.0)
        path.append(place.copy())
        if not alive.any():
            break
    return np.stack(path, axis=1), lock, side


def whorl_lean(rooted, whorl, rng):
    """A crown-combed style's roots near the whorl leaning in over its middle first (hair.py's WHORL_CROSS_M and
    WHORL_LEAN): combed straight out of it, its middle stood bare (an old woman's bob, round 1)."""
    inward = whorl[[0, 2]] - rooted[:, [0, 2]]
    close = np.clip(1.0 - np.linalg.norm(inward, axis=1) / hair.WHORL_CROSS_M, 0.0, 1.0)
    crossing = np.zeros((len(rooted), 3))
    crossing[:, [0, 2]] = hair.unit(inward) * (close * rng.uniform(0.0, hair.WHORL_LEAN, len(rooted)))[:, None]
    return crossing


def smoothed(path):
    """The guides' paths smoothed along themselves over SMOOTH_STEPS (a Gaussian), the root held and the smoothing
    rising from none at it over the first steps."""
    from scipy.ndimage import gaussian_filter1d  # noqa: PLC0415
    smooth = gaussian_filter1d(path, SMOOTH_STEPS, axis=1, mode="nearest")
    hold = np.clip(np.arange(path.shape[1]) / (2.0 * SMOOTH_STEPS), 0.0, 1.0)[None, :, None]
    return path + (smooth - path) * hold


def crown_whorl(rooted, frame):
    """A crown-combed style's whorl: the root highest over the head's middle, a little behind it."""
    behind = frame["centre"] - np.array([0.0, 0.0, hair.WHORL["behind_m"]])
    score = rooted[:, 1] - 0.5 * np.linalg.norm((rooted - behind)[:, [0, 2]], axis=1)
    return rooted[np.argmax(score)]


def regrown(space, field, scalp, skin, hairline, frame, style):
    """The strands: (counts, points (n x 3), radius per point); POINTS points a strand (hair.py's)."""
    rng = np.random.default_rng(SEED)
    line = parting(scalp, frame, style)
    guide_roots, guide_inner = roots_on(scalp, skin, hairline, frame, rng, GUIDES)
    path, lock, guide_side = guides_grown(space, field, guide_roots, guide_inner, line, frame, style, rng)
    moved = np.linalg.norm(path[:, -1] - path[:, 0], axis=1) > np.where(guide_inner > 0, 0.02, 0.004)
    kept = np.flatnonzero(moved)
    renumber = np.full(len(path), -1)
    renumber[kept] = np.arange(len(kept))
    lock_kept = renumber[lock[kept]]
    lock_kept = np.where(lock_kept < 0, np.arange(len(kept)), lock_kept)
    guides = smoothed(path[kept])
    rooted, inner = roots_on(scalp, skin, hairline, frame, rng)
    strands = hair.grown(guides, rooted, sides(rooted, line), inner, {**style, "length_from": "nearest"}, rng,
                         guide_side[kept], lock_kept, frame["centre"])
    fine = hair.BABY_RADIUS + (1.0 - hair.BABY_RADIUS) * inner
    along = np.linspace(0.0, 1.0, hair.POINTS)
    taper = 1.0 - (1.0 - hair.TIP_TAPER[1]) * np.clip((along - 1.0 + hair.TIP_TAPER[0]) / hair.TIP_TAPER[0], 0.0, 1.0)
    radius = (fine[:, None] * hair.RADIUS * taper[None]).reshape(-1)
    return np.full(len(strands), hair.POINTS, np.int64), strands.reshape(-1, 3), radius
