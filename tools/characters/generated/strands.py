"""The generated person's hair regrown as strands in the generated hair's own shape (`regrown`).

Roots on the new scalp (`scalp.py`) over the hole, at a real head's density (`../whole/hair.py`'s DENSITY rising over
DENSITY_RISE_M from the hairline, its `root_density`'s baby hairs in a BABY_BAND_M band of the skin under the paint's
hairline); behind the temples (FRONT_DEG round from the face) never under hair.py's HAIRLINE table's nape, as the
model's paint there is the hair hanging over the neck, not where it grows. GUIDES guides are grown through the hair's
volume (`volume.py`): each step along the head's comb (hair.py's `comb`, from the style's parting and the crown's
whorl, falling with gravity, the roots by the parting and the whorl first leaning over them, hair.py's `part_lean`;
a style with a straight fringe falls straight down over the forehead) laid flat on the
volume's own layers (the shell's surface direction), held at its lock's share of the volume's half thickness, so the
strands fill the shape and flow along it; a guide ends where it would leave the volume (the shell's end: shoulders,
jaw, a fringe's line) or at the style's length. The head's strands are then grown from the guides by hair.py's `grown`
(blended guides, locks, a soft point cut, the style's wave, wisped baby hairs, flyaways and the crown's frizz), the
guides' ends turned in by its `tipped`, each a human hair's radius tapered at the tip.
"""
import numpy as np
from scipy.spatial import cKDTree

from tools.characters.whole import hair
from tools.characters.generated import volume as hair_space

GUIDES = 12000
FRONT_DEG = 60.0
GRACE_M = 0.006  # a strand may stand outside the volume this long from its root (rooted on its edge)
LAYER_SHARE = (0.15, 1.0)  # each lock's layer: this share of the volume's half thickness, from its edge
CORRECT = 0.5  # how much of its layer's error a strand mends each step, never more than a step
SEED = 223
BEHIND_BLEND_M = 0.03
CANDIDATES = 400000  # places on the scalp a root is drawn from


def roots_on(scalp, skin, hairline, frame, rng, count=None):
    """Roots: (places, 1 for a full hair's and 0 for a baby hair's). Over the scalp's hole by its depth from the seam,
    on the skin within BABY_BAND_M of the hairline (`hairline`: places on the hair's edge) as baby hairs; `count` of
    them, or as many as a head holds."""
    hole = scalp["triangles"][scalp["hole"][scalp["triangles"]].all(axis=1)]
    on_scalp, picked, _ = hair.on_triangles(scalp["points"], hole, CANDIDATES, rng)
    band, band_over = baby_band(skin, hairline, rng, CANDIDATES / scalp_area(scalp["points"], hole))
    candidates = np.vstack([on_scalp, band])
    over = np.concatenate([scalp["depth"][hole[picked]].mean(axis=1), band_over])
    share = hair.root_density(over) * full_density(over) / hair.DENSITY["vertex"] * grows_here(candidates, frame)
    scalp_share = len(on_scalp) / len(candidates)
    area = scalp_area(scalp["points"], hole) / scalp_share
    wanted = count or int(area * np.mean(share) * hair.DENSITY["vertex"])
    chosen = rng.choice(len(candidates), size=wanted, p=share / share.sum())
    jitter = rng.normal(0.0, hair_space.SAMPLE_M * 0.5, (wanted, 3))
    return candidates[chosen] + jitter, (over[chosen] >= 0.0).astype(float)


def full_density(over):
    """The scalp's full root density (hairs a m2) `over` m over the hairline: the temples' at it, the vertex's
    DENSITY_RISE_M over it."""
    rise = np.clip(over / hair.DENSITY_RISE_M, 0.0, 1.0)
    return hair.DENSITY["temple"] + (hair.DENSITY["vertex"] - hair.DENSITY["temple"]) * rise


def grows_here(places, frame):
    """1 where hair grows: in front of FRONT_DEG round from the face wherever the paint says, behind it only over
    hair.py's HAIRLINE table (less its baby band)."""
    angle, _ = hair.around(places, frame["centre"])
    over = hair.over_hairline(places, frame["eyes"], frame["centre"])
    return ((angle < FRONT_DEG) | (over > -hair.BABY_BAND_M)).astype(float)


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
    faces = scalp["triangles"][scalp["hole"][scalp["triangles"]].all(axis=1)]
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


def guides_grown(space, rooted, inner, line, frame, style, rng):
    """Every guide's path through the volume (guides x steps x 3; a guide that ended stays at its last place) and
    each guide's lock (its middle guide's index)."""
    side = sides(rooted, line)
    fringe = style.get("fringe_side", "none")
    sweep = (np.where(side > 0.0, 1.0, 1.0 if fringe == "left" else -1.0) if fringe in ("left", "right")
             else np.zeros(len(rooted)) if fringe == "down" else side)
    lock = hair.locks(rooted, side, rng)
    layer = rng.uniform(*LAYER_SHARE, len(rooted))[lock]
    whorl = line[-1] if line is not None else crown_whorl(rooted, frame)
    lean = rng.normal(0.0, 1.0, (len(rooted), 3)) * [1.0, 0.0, 1.0] * np.where(inner > 0, hair.LEAN,
                                                                               hair.BABY_LEAN)[:, None]
    reach = np.where(inner > 0, style["length_m"], rng.uniform(*hair.BABY_LENGTH_M, len(rooted)))
    crossing = hair.part_lean(rooted, line, rng) if line is not None else np.zeros((len(rooted), 3))
    place, direction = rooted.copy(), None
    path, alive, travelled = [place.copy()], np.ones(len(place), dtype=bool), np.zeros(len(place))
    for _ in range(int(style["length_m"] / hair.STEP_M)):
        inward = hair_space.read(space, "gradient", place)
        outward = -hair.unit(inward)
        way = wanted_way(place, outward, line, sweep, frame, whorl, style.get("parting") == "back")
        wanted = hair.unit(hair.tangent(way + lean, outward))
        direction = (hair.unit(wanted + crossing) if direction is None
                     else hair.unit(direction * (1.0 - hair.TURN) + wanted * hair.TURN))
        depth = hair_space.read(space, "depth", place)
        target = layer * hair_space.read(space, "half", place) * np.clip(travelled / hair.ROOT_RISE_M, 0.0, 1.0)
        mend = np.clip(CORRECT * (target - depth), -hair.STEP_M, hair.STEP_M)
        moved = place + direction * hair.STEP_M + hair.unit(inward) * mend[:, None]
        inside = hair_space.read(space, "filled", moved) > 0.5
        alive &= (inside | (travelled < GRACE_M)) & (travelled + hair.STEP_M <= reach)
        place = np.where(alive[:, None], moved, place)
        travelled += np.where(alive, hair.STEP_M, 0.0)
        path.append(place.copy())
        if not alive.any():
            break
    return np.stack(path, axis=1), lock, side


def crown_whorl(rooted, frame):
    """A crown-combed style's whorl: the root highest over the head's middle, a little behind it."""
    behind = frame["centre"] - np.array([0.0, 0.0, hair.WHORL["behind_m"]])
    score = rooted[:, 1] - 0.5 * np.linalg.norm((rooted - behind)[:, [0, 2]], axis=1)
    return rooted[np.argmax(score)]


def regrown(space, scalp, skin, hairline, frame, style):
    """The strands: (counts, points (n x 3), radius per point); POINTS points a strand (hair.py's)."""
    rng = np.random.default_rng(SEED)
    line = parting(scalp, frame, style)
    guide_roots, guide_inner = roots_on(scalp, skin, hairline, frame, rng, GUIDES)
    path, lock, guide_side = guides_grown(space, guide_roots, guide_inner, line, frame, style, rng)
    moved = np.linalg.norm(path[:, -1] - path[:, 0], axis=1) > np.where(guide_inner > 0, 0.02, 0.004)
    kept = np.flatnonzero(moved)
    renumber = np.full(len(path), -1)
    renumber[kept] = np.arange(len(kept))
    lock_kept = renumber[lock[kept]]
    lock_kept = np.where(lock_kept < 0, np.arange(len(kept)), lock_kept)
    guides = hair.tipped(path[kept], frame["centre"])
    rooted, inner = roots_on(scalp, skin, hairline, frame, rng)
    strands = hair.grown(guides, rooted, sides(rooted, line), inner, style, rng, guide_side[kept], lock_kept,
                         frame["centre"])
    fine = hair.BABY_RADIUS + (1.0 - hair.BABY_RADIUS) * inner
    along = np.linspace(0.0, 1.0, hair.POINTS)
    taper = 1.0 - (1.0 - hair.TIP_TAPER[1]) * np.clip((along - 1.0 + hair.TIP_TAPER[0]) / hair.TIP_TAPER[0], 0.0, 1.0)
    radius = (fine[:, None] * hair.RADIUS * taper[None]).reshape(-1)
    return np.full(len(strands), hair.POINTS, np.int64), strands.reshape(-1, 3), radius
