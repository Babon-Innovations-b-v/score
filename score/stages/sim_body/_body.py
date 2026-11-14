"""The sim body stage's body: a person's rig at its own build (`person_rig`, its clips played as the people build
plays them: `tools.characters.played`), its segments, its clips' frames and its mass by #64's rule."""
import pathlib

import numpy as np

from tools.characters import played

RATE = 30.0  # the rig's clips (tools/characters/skel_usd.py RATE)
# SOMA joints that carry no segment: the ground point under the body and the end sites.
NOT_SEGMENTS = ("Root", "HeadEnd", "LeftToeEnd", "RightToeEnd")
# Global age-standardised mean BMI of adults, 2016 (kg/m2): NCD-RisC, Lancet 2017;390:2627-42,
# https://doi.org/10.1016/S0140-6736(17)32129-3. Height times this is #64's rule for a body with no stated weight.
BMI = {"male": 24.5, "female": 24.8}
BODY = "people-body"  # a look's built body row: its rig.npz is the person's own build (prop_rig.py)
# A clip's standing feet stood on the bind's floor (`stood`, #70, 2026-11-05: the mean body's pickup, Kimodo's own,
# floated its skin 5 to 7 mm over its floor on frames 15 to 30, past the contact's 5 mm, so the ground pushed nothing
# and its 630 N of weight sat on the pelvis' residual). Each foot's joints (with its toes and their end), a foot
# standing when its sole moves slower than STANCE_SPEED along the floor under STANCE_HIGH over it.
FEET = (("LeftFoot", "LeftToeBase", "LeftToeEnd"), ("RightFoot", "RightToeBase", "RightToeEnd"))
STANCE_SPEED = 0.2  # m/s
STANCE_HIGH = 0.03  # m
SOLE = 0.01  # m: a foot's sole is its skin within this of its lowest point
# A toe's bend toward flat tried in this many shares, the least that lifts its foot's skin to the floor taken (#70,
# 2026-11-06: Kimodo's toe pin turns the foot alone, so a foot pitched onto its toes put its toes under the floor, the
# lunge's back foot to -14 mm, the kneeling one to -20).
TOE_STEPS = 32
TOE_FLOOR = 1e-4  # m: a foot's skin this little under its floor is on it
STOOD_HZ = 3.0  # the stood move's smoothness, half the path's 6 Hz low pass (inside/fit, Winter 2009)
# A triangle a foot may stand on faces up at least this much (its normal's up part; a tread, a deck, a ramp up to 60
# degrees), so a riser or a wall beside the sole is no ground under it (treads_stood).
UPWARD = 0.5


def segments_of(rig):
    """The rig's segment joints (indices) and, for each rig joint, the segment that carries it (its nearest kept
    joint up the tree; the root's children carry the root)."""
    names, parents = [str(name) for name in rig["names"]], rig["parents"]
    kept = [joint for joint, name in enumerate(names) if name not in NOT_SEGMENTS]

    def carrier(joint):
        while joint >= 0 and joint not in kept:
            joint = parents[joint]
        return joint

    carriers = [carrier(joint) for joint in range(len(names))]
    top = next(joint for joint in kept if carrier(parents[joint]) < 0)
    return kept, [top if found < 0 else found for found in carriers]


def body_row(single):
    """The built body row of a character's look (people-cloth's own naming)."""
    return f"{BODY}-{(single.get('look') or '').replace('/', '-')}"


def bind_offsets(rig):
    """Each joint's offset against its parent at the rig's own bind (the root's: its bind's place)."""
    bind = np.asarray(rig["bind"], dtype=float)
    return np.array([bind[joint] if parent < 0 else np.linalg.inv(bind[parent]) @ bind[joint]
                     for joint, parent in enumerate(rig["parents"])])[:, :3, 3]


def played_build(rig, built):
    """(the build, its size over the rig's, the floor lift) a person's clips are played at (person_rig's): the built
    body's (with none, the rig's own bind), its Hips' height over the rig's, the lift that stands the standing
    clip's first frame's feet where the build's bind does."""
    if built is None:
        built = {"bind": rig["bind"], "offsets": bind_offsets(rig), "source_points": rig["points"]}
    names = [str(name) for name in rig["names"]]
    hips = played.TRAVELLING_JOINT
    if names[hips] != "Hips":
        raise ValueError(f"the rig's travelling joint is {names[hips]}, not Hips")
    size = float(built["bind"][hips, 1, 3] / rig["bind"][hips, 1, 3])
    bones = {"offsets": built["offsets"], "parents": rig["parents"], "bind": built["bind"]}
    return built, size, played.floor_lift(rig, bones, names, size)


def route_clip(rig, built, scene_rig, plan):
    """A scene-made clip (scene-clips' rig.npz `clip_<its clip>`, `plan` its scene_clips.json entry) at a person's
    own build, its joints against their parents (frames x joints x 4 x 4): played as person_rig plays a clip (the
    built offsets, the floor lift), its travel kept where its route goes, along the ground and up or down its steps,
    and only the Hips' height over the route's ground scaled by the build, as a clip's travel is: the route's treads
    are the scene's, never moved with the walker's size (2026-11-04, a climber's feet on the stairwell's steps)."""
    if [str(name) for name in scene_rig["names"]] != [str(name) for name in rig["names"]]:
        raise ValueError(f"{plan['clip']}: the scene-made clips' rig has other joints than the clips rig")
    built, size, lift = played_build(rig, built)
    clip = plan["clip"]
    local = played.clip_local({**rig, f"clip_{clip}": np.asarray(scene_rig[f"clip_{clip}"], dtype=float)}, clip,
                              built["offsets"], rig["parents"], 1.0, 0.0)
    route = np.asarray(plan["route"], dtype=float)[:, 1] - float(plan["placement"]["origin"][1])
    ground = route[np.minimum(np.arange(len(local)), len(route) - 1)]
    hips = played.TRAVELLING_JOINT
    local[:, hips, 1, 3] = ground + (local[:, hips, 1, 3] - ground) * size + lift
    return local


def surface_under(ground, points, ceilings):
    """The highest ground surface (m) at each point's place across the floor (`points` n x 3) under its ceiling
    (`ceilings`, m, one a point): of the triangles (`ground` n x 3 x 3) facing up (UPWARD) whose span across the floor
    holds it; -inf where none does."""
    ground, points = np.asarray(ground, dtype=float), np.asarray(points, dtype=float)
    normals = np.cross(ground[:, 1] - ground[:, 0], ground[:, 2] - ground[:, 0])
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    flat = ground[np.abs(normals[:, 1]) >= UPWARD]
    found = np.full(len(points), -np.inf)
    if not len(flat) or not len(points):
        return found
    corner, one, two = flat[:, 0, [0, 2]], flat[:, 1, [0, 2]] - flat[:, 0, [0, 2]], flat[:, 2, [0, 2]] - flat[:, 0, [0, 2]]
    area = one[:, 0] * two[:, 1] - one[:, 1] * two[:, 0]
    keep = np.abs(area) > 1e-12
    flat, corner, one, two, area = flat[keep], corner[keep], one[keep], two[keep], area[keep]
    for start in range(0, len(points), 256):
        offset = points[None, start:start + 256, [0, 2]] - corner[:, None]
        first = (offset[..., 0] * two[:, None, 1] - offset[..., 1] * two[:, None, 0]) / area[:, None]
        second = (one[:, None, 0] * offset[..., 1] - one[:, None, 1] * offset[..., 0]) / area[:, None]
        inside = (first >= -1e-9) & (second >= -1e-9) & (first + second <= 1 + 1e-9)
        heights = (flat[:, None, 0, 1] + first * (flat[:, None, 1, 1] - flat[:, None, 0, 1])
                   + second * (flat[:, None, 2, 1] - flat[:, None, 0, 1]))
        heights = np.where(inside & (heights <= np.asarray(ceilings, dtype=float)[None, start:start + 256]), heights,
                           -np.inf)
        found[start:start + 256] = heights.max(axis=0)
    return found


def foot_over(rig, local, ground, foot):
    """A foot's skin (`foot`, FEET's joints) against the ground under it (`ground`, the triangles it may touch, its
    highest surface under each point below its ankle, `surface_under`), a frame each: (its deepest point into its
    ground, m, under 0 where it is over it; its lowest point over its ground, m), -inf and inf where none is under it;
    None for a foot the rig has no skin or pin for."""
    names = [str(name) for name in rig["names"]]
    weights, points = np.asarray(rig["weights"], dtype=float), np.asarray(rig["points"], dtype=float)
    mine = np.flatnonzero(np.isin(weights.argmax(axis=1), [names.index(name) for name in foot if name in names]))
    if not len(mine) or foot[0] not in played.FEET:
        return None
    world = played.chained(local, rig["parents"])
    skinning = world @ np.linalg.inv(np.asarray(rig["bind"]))
    placed = np.einsum("pj,fjab,pb->fpa", weights[mine], skinning[..., :3, :], np.c_[points[mine], np.ones(len(mine))])
    low, high = placed[..., [0, 2]].reshape(-1, 2).min(axis=0), placed[..., [0, 2]].reshape(-1, 2).max(axis=0)
    near = ground[((ground[:, :, [0, 2]].max(axis=1) >= low) & (ground[:, :, [0, 2]].min(axis=1) <= high)).all(axis=1)]
    ankle = world[:, names.index(foot[0]), 1, 3]
    under = np.array([surface_under(near, placed[frame], np.full(len(mine), ankle[frame])) - placed[frame, :, 1]
                      for frame in range(len(local))])
    held = np.isfinite(under)
    return np.where(held, under, -np.inf).max(axis=1), np.where(held, -under, np.inf).min(axis=1)


def ends_stood(rig, local, ground, asked):
    """`local` (a climber's scene-made clip) with its Hips moved up or down, before Kimodo's first foot keyframe and
    after its last (`asked`, the frames scene-clips asked a foot on its tread), so its standing feet rest on the ground
    under them: Kimodo was asked no foot there and no hip height (its root2d holds the hips along the floor only, a
    foot keyframe pins their height), and with no ground of its own it stood the stairwell's person_woman on nothing
    (2026-11-14: her left sole 17 cm over the landing at frame 0, 2 to 4 cm on frames 8 to 19, her leg straight, so no
    pin of the foot could reach it; 2 to 3 cm on frames 101 to 103, after her last keyframe at 93). As `stood` does on
    the bind's floor: on each frame there a foot stands (its sole slower than STANCE_SPEED, any height: Kimodo had no
    ground to stand it within STANCE_HIGH of), its lowest standing sole is brought to its ground, a frame no foot stands
    on taking the move straight between its neighbours', the move between the keyframes held at none, the whole
    smoothed as `stood` smooths (STOOD_HZ); a clip asked no foot is left as it is."""
    moved = np.array(local, dtype=float)
    if not len(asked):
        return moved
    _, speeds, _ = soles(rig, moved)
    gaps = np.full((len(moved), len(FEET)), np.inf)
    for index, foot in enumerate(FEET):
        over = foot_over(rig, moved, np.asarray(ground, dtype=float), foot)
        if over is not None:
            gaps[:, index] = np.where(speeds[:, index] < STANCE_SPEED, over[1], np.inf)
    frames = np.arange(len(moved))
    free = (frames < min(asked)) | (frames > max(asked))
    lowest = gaps.min(axis=1)
    known = ~free | np.isfinite(lowest)
    wanted = np.interp(frames, frames[known], np.where(free, -lowest, 0.0)[known])
    bend = np.diff(np.eye(len(wanted)), 2, axis=0)
    smooth = (2.0 * np.sin(np.pi * STOOD_HZ / RATE)) ** -4
    weight = np.where(free, 1.0, 1e9)  # the keyframes' span held where Kimodo put it
    move = np.linalg.solve(np.diag(weight) + smooth * bend.T @ bend, weight * wanted)
    moved[:, played.TRAVELLING_JOINT, 1, 3] += np.where(free, move, 0.0)
    return moved


def treads_stood(rig, local, ground, asked=()):
    """`local` (a climber's scene-made clip, route_clip's) with each foot, on every frame it stands, put on the ground
    under it (`ground`, the triangles it may touch in its own frame, ground_of's): Kimodo's foot keyframes hold a foot
    on its tread only at its stance's middle, made with no post-processing (scene_clips: its contact pins hold one
    floor), so between them its sole sank and floated (the stairwell's person_woman, 2026-11-14: her left sole 4.2 cm
    into her second tread as it came down flat, frame 35, 1.4 cm under at her keyframe), and before the first keyframe
    and after the last (`asked`, its keyframes' frames) her Hips stood her over it, which `ends_stood` puts right
    first. The ground under each point of a foot's skin is the highest surface under it below its ankle (`foot_over`).
    A foot any point of which is in its ground stands on it, lifted till none is; one whose sole moves slower than
    STANCE_SPEED within STANCE_HIGH over its ground stands too, lowered onto it. Each is moved by Kimodo's own
    end-effector pin (`played.pinned`: the leg's IK, the foot turned as before, eased in and out), never the Hips."""
    names = [str(name) for name in rig["names"]]
    ground = np.asarray(ground, dtype=float)
    moved = ends_stood(rig, local, ground, asked)
    _, speeds, _ = soles(rig, moved)
    for index, foot in enumerate(FEET):
        over = foot_over(rig, moved, ground, foot)
        if over is None:
            continue
        depth, gap = over
        sunk = depth > 0.0
        resting = ~sunk & np.isfinite(gap) & (speeds[:, index] < STANCE_SPEED) & (gap < STANCE_HIGH)
        if sunk.any() or resting.any():
            moved = played.pinned(moved, names, rig["parents"], rig["bind"], foot[0], sunk | resting,
                                  np.where(sunk, depth, np.where(resting, -gap, 0.0)))
    return moved


def soles(rig, local):
    """Each foot's sole over the bind's floor on every frame of `local` (the clip against its parents) on `rig`'s bind,
    surface and weights: (its lowest skin point's height, m; its sole's speed along the floor, m/s, the slower of the
    steps into and out of the frame), each frames x feet, and the lowest of the skin no foot carries (m, frames); a
    foot is the skin its FEET joints carry most."""
    names = [str(name) for name in rig["names"]]
    skinning = played.chained(np.asarray(local, dtype=float), rig["parents"]) @ np.linalg.inv(np.asarray(rig["bind"]))
    weights, points = np.asarray(rig["weights"], dtype=float), np.asarray(rig["points"], dtype=float)
    heights, speeds, feet = [], [], np.zeros(len(points), dtype=bool)
    for foot in FEET:
        mine = np.flatnonzero(np.isin(weights.argmax(axis=1), [names.index(name) for name in foot if name in names]))
        if not len(mine):
            continue
        feet[mine] = True
        placed = np.einsum("pj,fjab,pb->fpa", weights[mine], skinning[..., :3, :], np.c_[points[mine], np.ones(len(mine))])
        lowest = placed[..., 1].min(axis=1)
        sole = placed[..., 1] <= lowest[:, None] + SOLE
        centre = np.einsum("fp,fpa->fa", sole, placed[..., [0, 2]]) / sole.sum(axis=1, keepdims=True)
        step = np.linalg.norm(np.diff(centre, axis=0), axis=1) * RATE if len(centre) > 1 else np.zeros(0)
        speed = np.minimum(np.r_[step[:1], step], np.r_[step, step[-1:]]) if len(step) else np.zeros(1)
        heights.append(lowest)
        speeds.append(speed)
    rest = np.flatnonzero(~feet)
    others = (np.einsum("pj,fjab,pb->fpa", weights[rest], skinning[..., 1:2, :], np.c_[points[rest], np.ones(len(rest))])
              [..., 0].min(axis=1) if len(rest) else np.full(len(local), np.inf))
    return np.array(heights).T.reshape(len(local), -1), np.array(speeds).T.reshape(len(local), -1), others


def standing_of(heights, speeds, others):
    """Each foot's stance (frames x feet) from `soles`' heights, speeds and other skin: its sole under STANCE_SPEED
    and STANCE_HIGH and no other skin under it (a body sitting or kneeling on its floor is carried there)."""
    return (speeds < STANCE_SPEED) & (heights < STANCE_HIGH) & (heights <= others[:, None])


def stances(rig, local):
    """Each foot's stance on every frame of `local` (frames x feet, FEET's order), `stood`'s rule."""
    return standing_of(*soles(rig, local))


def stood_smoothed(values):
    """A frame by frame move (`values`, m) smoothed as `stood` smooths its own: Whittaker's smoother, the move's squared
    second differences weighed so it passes up to STOOD_HZ."""
    bend = np.diff(np.eye(len(values)), 2, axis=0)
    smooth = (2.0 * np.sin(np.pi * STOOD_HZ / RATE)) ** -4
    return np.linalg.solve(np.eye(len(values)) + smooth * bend.T @ bend, np.asarray(values, dtype=float))


def stood(rig, local):
    """`local` with its travelling joint moved up or down frame by frame so its standing feet's soles rest on the
    bind's floor (y = 0): on every frame a foot stands (`soles` under STANCE_SPEED and STANCE_HIGH, and no other skin
    under it: a body sitting or kneeling on its floor is carried there, never pushed into it) the lowest
    standing sole is brought to it, a frame no foot stands on (a jump's flight) taking the move straight between its
    neighbours' (the first's or the last's beyond them), the whole smoothed (Whittaker's smoother: the move's squared
    second differences weighed so it passes up to STOOD_HZ), so it never leaves what its standing frames ask.
    A frame's own rotations are never changed; a clip on which no foot stands is as it came."""
    heights, speeds, others = soles(rig, local)
    standing = standing_of(heights, speeds, others)
    on = standing.any(axis=1)
    if not on.any():
        return np.asarray(local, dtype=float)
    frames = np.arange(len(local))
    move = stood_smoothed(np.interp(frames, frames[on], np.where(standing, heights, np.inf).min(axis=1)[on]))
    moved = np.array(local, dtype=float)
    moved[:, played.TRAVELLING_JOINT, 1, 3] -= move
    return moved


def foot_lowest(rig, local, foot):
    """The lowest point (m, frames) of the skin the FEET entry `foot`'s joints carry most, over `local` on `rig`."""
    names = [str(name) for name in rig["names"]]
    weights = np.asarray(rig["weights"], dtype=float)
    mine = np.flatnonzero(np.isin(weights.argmax(axis=1), [names.index(name) for name in foot if name in names]))
    carried = np.flatnonzero(weights[mine].any(axis=0))
    skinning = (played.chained(np.asarray(local, dtype=float), rig["parents"])[:, carried]
                @ np.linalg.inv(np.asarray(rig["bind"])[carried]))
    points = np.c_[np.asarray(rig["points"], dtype=float)[mine], np.ones(len(mine))]
    return np.einsum("pj,fjb,pb->fp", weights[mine][:, carried], skinning[..., 1, :], points).min(axis=1)


def toes_lifted(rig, local):
    """`local` with each foot's toe, on every frame its foot's skin is under the bind's floor, bent the least share
    (of TOE_STEPS) of the way toward flat (`played.toward_flat`) that brings that skin up to the floor (within
    TOE_FLOOR), or the share that lifts it most when none does; a frame whose foot is not under, and a foot the rig
    has no toe or skin of, is left as it is."""
    names = [str(name) for name in rig["names"]]
    weights = np.asarray(rig["weights"])
    moved = np.array(local, dtype=float)
    for foot in FEET:
        if not all(name in names for name in foot) or not np.isin(
                weights.argmax(axis=1), [names.index(name) for name in foot]).any():
            continue
        low = np.flatnonzero(foot_lowest(rig, moved, foot) < -TOE_FLOOR)
        if not len(low):
            continue
        steps = np.linspace(0.0, 1.0, TOE_STEPS + 1)
        heights = np.stack([foot_lowest(rig, played.toward_flat(moved[low], names, rig["parents"], rig["bind"],
                                                                foot[1:], step), foot) for step in steps], axis=1)
        enough = heights >= -TOE_FLOOR
        share = steps[np.where(enough.any(axis=1), enough.argmax(axis=1), heights.argmax(axis=1))]
        moved[low] = played.toward_flat(moved[low], names, rig["parents"], rig["bind"], foot[1:], share)
    return moved


def person_rig(rig, built, contacts=None):
    """The clips rig at a person's own build, as the people build plays its clips (`tools.characters.played`, the
    people route's one definition: prop_build.py's clip_world and floor_lift): the built body's bind and surface
    (rig.npz's moved mean surface), every clip's joint offsets the built ones and its travel (Hips) scaled by the built
    Hips' height over the rig's, every clip lifted so the standing clip's first frame puts the feet where the bind
    does; and that size. With no build, the rig's own bind is the build, size 1: its clips were posed on SOMA's
    zero-identity body, 7 cm shorter than the template its bind and surface are, and their own offsets floated its
    skin 26 to 57 mm over its ground (#70). Each clip's standing feet then stand on the bind's floor (`stood`):
    Kimodo's own clips float and sink theirs. Then a clip with Kimodo's foot contacts in `contacts` ({clip: its
    foot_contacts}, `contacts_of`) has Kimodo's own foot correction run on the build's bones (`played.contacted`):
    its feet on their contact frames held at the bind's own ankle and toe heights, so a longer leg meets the floor;
    and the toes its toe pin carried under the floor with a foot pitched onto them bent back up (`toes_lifted`)."""
    built, size, lift = played_build(rig, built)
    found = dict(rig, bind=np.asarray(built["bind"]), points=np.asarray(built["source_points"]))
    for key in [key for key in rig if key.startswith("clip_")]:
        clip = key[len("clip_"):]
        found[key] = stood(found, played.clip_local(rig, clip, built["offsets"], rig["parents"], size, lift))
        if clip in (contacts or {}):
            found[key] = toes_lifted(found, played.contacted(found[key], rig["names"], rig["parents"], found["bind"],
                                                             contacts[clip]))
    return found, size


def contacts_of(folder, rig):
    """{clip: Kimodo's foot_contacts} of the rig's clips whose Kimodo motion (people-clips-made's
    `motions/<clip>.npz`, Kimodo's own output) under `folder` carries them."""
    found = {}
    for clip in [key[len("clip_"):] for key in rig if key.startswith("clip_")]:
        motion = pathlib.Path(folder) / "motions" / f"{clip}.npz"
        if motion.exists():
            with np.load(motion) as saved:
                if "foot_contacts" in saved.files:
                    found[clip] = saved["foot_contacts"]
    return found


def standing_height(rig):
    """The rig's own standing height at its bind pose (metres, its surface's top over its lowest point)."""
    points = np.asarray(rig["points"])
    return float(points[:, 1].max() - points[:, 1].min())


def mass_of(single, height):
    """A character's body mass record: the stated weight, else height squared times the reference BMI of its sex
    (the mean of both when none is stated), marked estimated (#64)."""
    if single.get("weight"):
        return {"kg": float(single["weight"]), "source": "stated weight"}
    stated = single.get("height")
    tall = float(stated or height)
    sex = single.get("sex")
    bmi = BMI[sex] if sex in BMI else sum(BMI.values()) / len(BMI)
    return {"kg": round(bmi * tall ** 2, 2), "source": "estimated", "height": round(tall, 4),
            "height from": "stated" if stated else "the SOMA body's own standing height",
            "sex": sex if sex in BMI else "not stated", "bmi": bmi}


def clip_frames(rig, clip, kept):
    """The clip's segment frames in the world, frame by frame (frames x segments x 4 x 4): its joints' transforms
    against their parents chained down the tree."""
    return played.chained(np.asarray(rig[f"clip_{clip}"], dtype=float), rig["parents"])[:, kept]
