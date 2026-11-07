"""A GEM-X SOMA body (on_gemx.py's npz: SOMA's 78 public joints, its world transforms every frame, the person's own
bind, rest mesh, faces and skin weights) as the sim body stage hands a person to its run: the rig's 27 joints (the
fingers, jaw and eyes merged into what is left above them, as the people route drops them: body.py's UNSEEN), each
joint's frame turned onto the clips rig's template frame (a relabelling of the joint's axes, its bind turned with it,
so the skin and the movement are the same to the last bit of rounding: the static calibration table is read on the
template's frames), and the clip put on the floor: first as a whole, its feet's lowest point over the clip at y = 0
(GEM-X's raw world has no floor of its own; its Contact/IK postprocess, left off, is what would ground it), then as
the stage stands every clip (`sim_body.stood`). Both move only the travelling joint up or down.
SOMA's shape and pose are never changed (#70: SOMA is the truth)."""
import numpy as np

from score.stages import sim_body
from score.stages.sim_body import _body
from tools.characters import played
from tools.labval import _floor, _supports

# The joints the people route drops (tools/characters/people/body.py UNSEEN, which imports SOMA itself and so is not
# imported here; the test reads that file's tuple and fails when the two differ).
UNSEEN = ("Thumb", "Index", "Middle", "Ring", "Pinky", "Jaw", "Eye")
RATE = 30.0  # GEM-X Motion's timeline (its motion-video normalises every clip to 30 Hz), the stage's sim_body.RATE
# GEM-X's static contact (its network's static_conf_logits, upstream's order: left ankle, left foot, right ankle, right
# foot, left wrist, right wrist): a foot is seen standing when its ankle or its foot is over STATIC (upstream's own
# Contact/IK reads the logits' sign, sigmoid 0.5). Measured on 12 trials of subjects 2 to 5 (#98, 2026-11-07, against
# the plates over 5% of the weight): GEM-X's static alone recall 0.92, precision 0.94 (a rolling foot at heel strike
# and push-off is not static); with the stage's own stance on the stood clip (`sim_body.stances`) 0.95 and 0.93.
SEEN_FEET = ((0, 1), (2, 3))  # left, right: sim_body's FEET order
STATIC = 0.5
# A seen stance's gaps of at most BRIDGE frames are filled (`bridged`): GEM-X's still right foot in a squat blinked
# out of stance for 1 to 8 frames at a time (its estimate sliding, 17% of subject2_squats1's frames), shifting the
# load onto the left; a walk's swing lasts 8 to 19 frames (#98, 2026-11-07).
BRIDGE = 6  # frames: 0.2 s at RATE
# GEM-X's world drifts up and down over a clip (its root's vertical rollout): standing feet rose 30 to 80 mm off the
# clip's lowest point (#98, 2026-11-07: 12 of 64 trials but the drop jumps, squatsAsym 0 to 70 mm over 13 s), past the
# stage's STANCE_HIGH, so `stood` stood none of them. A support stays where it is between flights (`undrifted`): the
# frames on which a foot is still (its sole, `sim_body.soles`, under STANCE_SPEED along the floor and up or down, no
# other skin under it, within STANCE_HIGH of the lowest foot; a jump's top is slow only along the floor) hold their
# still feet's lowest sole at their span's median, a span ending at a flight (`flight`: frames with no foot still over
# which the lowest sole rises more than STANCE_HIGH over the supports either side, or after which the support stands
# more than that higher or lower, reached faster than STEP_SPEED over at least FALL frames: a drop jump's step off its
# box and its jump, each support keeping its own height). A walk's change of foot is no flight, nor the drift (5 to 20
# mm/s: squatsAsym's 70 mm over 13 s, a trunk-sway walk's 40 over 2), nor a jump of GEM-X's world over a few frames
# (43 mm down in 5 near squatsAsym's end); a step off a drop jump's box, or a jump, took 8 to 26 frames on 7 drop
# jumps (150 to 400 mm).
STEP_SPEED = 0.1  # m/s
FALL = 8  # frames


def roots_fixed(parents):
    """SOMA's parents with its root (its own parent, or none) as -1."""
    return np.array([-1 if parent < 0 or parent == joint else parent for joint, parent in enumerate(parents)])


def kept(names, parents):
    """(the kept joints' old numbers, their parents in the new numbering, each old joint's carrier in the new)."""
    keep = [not any(mark in name for mark in UNSEEN) for name in names]
    number = {old: new for new, old in enumerate(joint for joint, yes in enumerate(keep) if yes)}
    carriers = []
    for joint in range(len(names)):
        walk = joint
        while not keep[walk]:
            if parents[walk] < 0:
                raise ValueError(f"{names[joint]} hangs from no kept joint")
            walk = parents[walk]
        carriers.append(number[walk])
    joints = sorted(number)
    return joints, np.array([-1 if parents[joint] < 0 else number[parents[joint]] for joint in joints]), carriers


def merged(weights, carriers, count):
    """Each dropped joint's skin weight handed to its carrier."""
    found = np.zeros((len(weights), count))
    for joint, carrier in enumerate(carriers):
        found[:, carrier] += weights[:, joint]
    return found


def reframed(world, bind, template_bind):
    """(world, bind) with each joint's axes turned onto the template's bind frame: C = B^T T on the rotations, so the
    bind's rotation is the template's, its place its own, and every frame's world rotation W C; W B^-1, which skins the
    mesh, is unchanged. And the largest turn applied (degrees)."""
    turn = np.swapaxes(bind[:, :3, :3], 1, 2) @ template_bind[:, :3, :3]
    new_bind, new_world = bind.copy(), world.copy()
    new_bind[:, :3, :3] = bind[:, :3, :3] @ turn
    new_world[..., :3, :3] = world[..., :3, :3] @ turn
    angles = np.degrees(np.arccos(np.clip((np.trace(turn, axis1=1, axis2=2) - 1.0) / 2.0, -1.0, 1.0)))
    return new_world, new_bind, float(angles.max())


def against_parents(world, parents):
    """Each joint's transform against its parent's (frames x joints x 4 x 4), the root's its world."""
    local = world.copy()
    for joint, parent in enumerate(parents):
        if parent >= 0:
            local[:, joint] = np.linalg.inv(world[:, parent]) @ world[:, joint]
    return local


def floored(rig, local):
    """`local` moved up or down as a whole so its feet's lowest skin point over the clip is at y = 0 (`sim_body.soles`),
    and that move (m)."""
    heights = sim_body.soles(rig, local)[0]
    moved = np.array(local, dtype=float)
    moved[:, played.TRAVELLING_JOINT, 1, 3] -= float(heights.min())
    return moved, float(heights.min())


def flight(lowest, support, before, after):
    """Whether the frames between the still frames `before` and `after` are a flight: the lowest sole (`lowest`,
    frames) rises over both supports (`support`, frames) by more than STANCE_HIGH, or the support after stands more
    than that above or below the one before, reached faster than STEP_SPEED over at least FALL frames (a step off a
    box; not the drift, nor a jump of GEM-X's in a frame or two)."""
    if after - before < 2:
        return False
    rises = lowest[before + 1:after].max() > max(support[before], support[after]) + _body.STANCE_HIGH
    step = abs(support[after] - support[before])
    falls = after - before >= FALL and step * RATE / (after - before) > STEP_SPEED
    return bool(rises or (step > _body.STANCE_HIGH and falls))


def undrifted(rig, local):
    """`local` moved up or down so the still feet's lowest sole keeps one height through each span of support
    (above), the lowest span's at y = 0, the move between spans and over unsupported frames taken straight
    between its neighbours and smoothed as `sim_body.stood` smooths; and that lowest span's height before (m). A clip
    with no still foot is put on the floor as a whole (`floored`)."""
    heights, speeds, others = sim_body.soles(rig, local)
    step = np.abs(np.diff(heights, axis=0)) * RATE if len(heights) > 1 else np.zeros((0, heights.shape[1]))
    rising = np.minimum(np.r_[step[:1], step], np.r_[step, step[-1:]]) if len(step) else np.zeros_like(heights)
    lowest = heights.min(axis=1)
    still = ((speeds < _body.STANCE_SPEED) & (rising < _body.STANCE_SPEED) & (heights <= others[:, None]) &
             (heights <= lowest[:, None] + _body.STANCE_HIGH))
    support = np.where(still, heights, np.inf).min(axis=1)
    on = np.isfinite(support)
    if not on.any():
        return floored(rig, local)
    frames = np.arange(len(local))
    held, starts = np.flatnonzero(on), [0]
    starts += [place for place in range(1, len(held)) if flight(lowest, support, held[place - 1], held[place])]
    drift, levels = np.zeros(len(local)), []
    for first, last in zip(starts, starts[1:] + [len(held)]):
        span = held[first:last]
        levels.append(float(np.median(support[span])))
        drift[span] = support[span] - levels[-1]
    floor = min(levels)
    move = sim_body.stood_smoothed(np.interp(frames, held, drift[held])) + floor
    moved = np.array(local, dtype=float)
    moved[:, played.TRAVELLING_JOINT, 1, 3] -= move
    return moved, floor


def seen_stance(gemx, rig, local):
    """Each foot's stance (frames x 2, left and right) the video shows: GEM-X's static contact on its ankle or foot
    (`gemx`'s static_conf_logits, over STATIC), or the stage's own stance on the stood clip (`sim_body.stances`)."""
    kinematic = sim_body.stances(rig, local)
    if gemx is None or "static_conf_logits" not in gemx:
        return bridged(kinematic)
    static = 1.0 / (1.0 + np.exp(-np.asarray(gemx["static_conf_logits"], dtype=float))) > STATIC
    if len(static) != len(local):
        raise ValueError(f"{len(static)} frames of GEM-X's static contact for a clip of {len(local)}")
    return bridged(kinematic | np.stack([static[:, list(columns)].any(axis=1) for columns in SEEN_FEET], axis=1))


def bridged(stance):
    """`stance` (frames x feet) with each foot's gaps of at most BRIDGE frames between two of its standing frames
    filled: a foot does not lift for so short a time."""
    found = np.array(stance, dtype=bool)
    for foot in range(found.shape[1]):
        standing = np.flatnonzero(found[:, foot])
        for before, after in zip(standing[:-1], standing[1:]):
            if 1 < after - before <= BRIDGE + 1:
                found[before:after, foot] = True
    return found


def person(soma, template, gemx=None, moge=None, activity=None):
    """(the rig {names, parents, bind, points, faces, weights, stance: each foot's seen stance, `seen_stance`}, its
    segments' frames frames x segments x 4 x 4, the segments' names, the record) of a GEM-X SOMA body `soma` on the
    clips rig `template` (people-clips-made's rig.npz: its joints, its mesh's faces and its bind's frames). A body of
    other joints or another mesh topology than the template's raises: the landmark set is the template's faces. With
    `gemx` (its result's contact_ik.npz: GEM-X's own Contact/IK post-processing, which holds a foot it sees static
    where it stood; its camera; its contacts) its world transforms are taken for `soma`'s, and the floor `moge` sees
    (on_moge.py's npz; `_floor.seen`) levels them (`_floor.levelled`) before they are undrifted onto the floor
    (`undrifted`) and stood. With `activity` (the trial's, `labval.activity_of`) the chair or box it rests on beside
    the floor is the rig's `supports` (`_supports.under`: triangles, the person's frame)."""
    if gemx is not None:
        soma = dict(soma, world=np.asarray(gemx["world_transforms"], dtype=float))
    if float(soma["fps"]) != RATE:
        raise ValueError(f"a SOMA body at {float(soma['fps'])} Hz; GEM-X Motion and the stage run at {RATE}")
    names = [str(name) for name in soma["names"]]
    joints, parents, carriers = kept(names, roots_fixed(np.asarray(soma["parents"])))
    rig_names = [names[joint] for joint in joints]
    if rig_names != [str(name) for name in template["names"]]:
        raise ValueError(f"GEM-X's kept joints {rig_names} are not the clips rig's {list(template['names'])}")
    if not np.array_equal(np.asarray(soma["faces"]), np.asarray(template["faces"])):
        raise ValueError("the GEM-X body's mesh is not the clips rig's topology (on_gemx.py's LOD must be the rig's)")
    world, bind, turned = reframed(np.asarray(soma["world"], dtype=float)[:, joints],
                                   np.asarray(soma["bind"], dtype=float)[joints],
                                   np.asarray(template["bind"], dtype=float))
    rig = {"names": np.array(rig_names), "parents": parents, "bind": bind,
           "points": np.asarray(soma["points"], dtype=float), "faces": np.asarray(soma["faces"]),
           "weights": merged(np.asarray(soma["weights"], dtype=float), carriers, len(joints))}
    if rig_names[played.TRAVELLING_JOINT] != "Hips":
        raise ValueError(f"the travelling joint is {rig_names[played.TRAVELLING_JOINT]}, not Hips")
    record = {}
    if moge is not None:
        floor_seen = _floor.seen(moge, gemx)
        if floor_seen is None:
            raise ValueError("MoGe-2 saw too little floor beside the person to level the clip on")
        world, tilt, spread = _floor.levelled(world, gemx, floor_seen["normal"])
        record["floor seen"] = {**{key: floor_seen[key] for key in ("inliers", "rms mm", "tilt deg")},
                                "levelled deg": round(tilt, 3), "GEM-X's up spread deg": round(spread, 3)}
    local, floor = undrifted(rig, against_parents(world, parents))
    stood = sim_body.stood(rig, local)
    rig["stance"] = seen_stance(gemx, rig, stood)
    rig["supports"], supported = _supports.under(rig, stood, activity)
    if supported:
        record["supports"] = supported
    segments = sim_body.segments_of(rig)[0]
    lift = local[:, played.TRAVELLING_JOINT, 1, 3] - stood[:, played.TRAVELLING_JOINT, 1, 3]
    record = {**record, "frames": len(world), "joints dropped": len(names) - len(joints),
              "frames turned onto the template's, deg most": round(turned, 3),
              "put on the floor mm": round(1000 * floor, 2),
              "stood move mm": [round(1000 * float(value), 2) for value in (lift.min(), np.median(lift), lift.max())],
              "stance share": [round(float(share), 3) for share in rig["stance"].mean(axis=0)]}
    return rig, played.chained(stood, parents)[:, segments], [rig_names[joint] for joint in segments], record
