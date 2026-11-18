"""One body from the SOMA bodies GEM-X made of a trial's cameras (#98, MOTOR #1): one camera's body leans along its
line of sight, so where it puts the pelvis between the feet, and with it the split of the weight between them, is
that camera's depth error (subject2_squats1 across Cam0 to Cam4: the hips 0.60, 0.65, 0.54, 0.36 and 0.40 of the way
from the right foot to the left, the plates' share 0.48). LabValidation's five cameras stand on both sides of the
walkway, so their errors cancel in the mean.

Each camera's body is first its own (`_soma.viewed`: GEM-X's Contact/IK world levelled on the floor MoGe-2 sees in
that camera). The cameras' clips start a few frames apart (1 to 3 frames on the demo trials), so each view is put on
the first view's timeline by the shift that best matches its pose (the distances from the Hips to every joint, which no
camera's place or heading changes; sub-frame by a parabola), then turned about the up and moved, one rigid move for the
clip, onto the views' mean (least squares over every joint and frame both hold; the floor is level in each, so only
the heading and the place are free). The fused body is then every joint's turn against its parent averaged over the
views that hold the frame (unit quaternions, each view's weight equal), the travelling joint's place averaged, and the
rig's bind and rest mesh averaged over the views: one SOMA body, its joints and skin GEM-X's, the mean of what the
cameras saw. A view whose pose matches the first's worse than JOIN is left out (its record says so). The lab's
calibration is not used: the views are put together by their own bodies."""
import numpy as np
from scipy.spatial.transform import Rotation

from tools.characters import played

SHIFT_MOST = 15  # frames either way a view's clip may start from the first's (0.5 s at 30 Hz)
OVERLAP = 0.5  # a shift is tried only while at least this share of the first view's frames is in both
JOIN = 0.9  # a view joins when its pose's correlation with the first view's, at its shift, is at least this
# A view whose clip ends before the first's (its shift: 8 frames of 47 on a walk) fades in or out over RAMP frames
# there, so the fused body does not jump by the views' spread (40 to 75 mm, `heading_fit`'s miss) where it leaves.
RAMP = 6  # frames
FEET = ("RightFoot", "LeftFoot")


def pose_signal(world, hips):
    """The distances from the Hips to every joint a frame (frames x joints): no camera's place or heading moves them."""
    places = world[:, :, :3, 3]
    return np.linalg.norm(places - places[:, hips:hips + 1], axis=2)


def matched(signal, reference, shift):
    """The correlation of `signal` read at frame f + `shift` against `reference` at f, over the frames both hold (each
    joint's mean taken out), and how many frames that is."""
    first, last = max(0, -shift), min(len(reference), len(signal) - shift)
    if last - first < 2:
        return -1.0, 0
    mine, theirs = signal[first + shift:last + shift], reference[first:last]
    mine, theirs = mine - mine.mean(axis=0), theirs - theirs.mean(axis=0)
    scale = np.sqrt((mine ** 2).sum() * (theirs ** 2).sum())
    return (float((mine * theirs).sum() / scale) if scale > 0 else -1.0), last - first


def delay(signal, reference):
    """(the shift in frames, sub-frame, at which `signal` read at f + shift best matches `reference` at f, that match's
    correlation): integer shifts within SHIFT_MOST holding OVERLAP of `reference`'s frames, refined by a parabola."""
    scores = {}
    for shift in range(-SHIFT_MOST, SHIFT_MOST + 1):
        score, overlap = matched(signal, reference, shift)
        if overlap >= OVERLAP * len(reference):
            scores[shift] = score
    best = max(scores, key=scores.get)
    before, after = scores.get(best - 1), scores.get(best + 1)
    bend = (before - 2 * scores[best] + after) if before is not None and after is not None else 0.0
    return (best + (0.5 * (before - after) / bend if bend < 0 else 0.0)), scores[best]


def quaternions(local):
    """Each joint's turn against its parent as unit quaternions (frames x joints x 4, scipy's x, y, z, w)."""
    frames, joints = local.shape[:2]
    return Rotation.from_matrix(local[..., :3, :3].reshape(-1, 3, 3)).as_quat().reshape(frames, joints, 4)


def resampled(local, shift, frames):
    """(each joint's quaternion and translation against its parent read at frame f + `shift` for f < `frames`, linear
    between the two frames around it (the quaternion normalised, on the nearer one's side), and each frame's weight:
    0 outside the view's clip, rising over RAMP frames from an end where the view's clip ends before the first's)."""
    turns, places = quaternions(local), local[..., :3, 3]
    at = np.arange(frames) + shift
    inside = (at >= 0) & (at <= len(local) - 1)
    low = np.clip(np.floor(at).astype(int), 0, len(local) - 1)
    high = np.clip(low + 1, 0, len(local) - 1)
    part = np.clip(at - low, 0.0, 1.0)[:, None, None]
    sides = np.sign((turns[low] * turns[high]).sum(axis=-1, keepdims=True))
    sides[sides == 0] = 1.0
    turn = (1 - part) * turns[low] + part * sides * turns[high]
    turn /= np.linalg.norm(turn, axis=-1, keepdims=True)
    weight = inside.astype(float)
    if shift < 0:
        weight *= np.clip((at + 1) / RAMP, 0.0, 1.0)
    if len(local) - 1 - shift < frames - 1:
        weight *= np.clip((len(local) - at) / RAMP, 0.0, 1.0)
    return turn, (1 - part) * places[low] + part * places[high], weight


def composed(turns, places):
    """4 x 4 transforms from quaternions and translations."""
    found = np.zeros(turns.shape[:-1] + (4, 4))
    found[..., :3, :3] = Rotation.from_quat(turns.reshape(-1, 4)).as_matrix().reshape(turns.shape[:-1] + (3, 3))
    found[..., :3, 3] = places
    found[..., 3, 3] = 1.0
    return found


def heading_fit(places, onto, inside):
    """The one rigid move (4 x 4: a turn about the up, y, and a translation) that best puts the joints' places
    `places` onto `onto` (frames x joints x 3) over the frames `inside` (least squares, Kabsch in the floor's plane),
    and the joints' root mean square miss after it (m)."""
    mine, theirs = places[inside].reshape(-1, 3), onto[inside].reshape(-1, 3)
    mine_mean, theirs_mean = mine.mean(axis=0), theirs.mean(axis=0)
    flat_mine, flat_theirs = (mine - mine_mean)[:, [0, 2]], (theirs - theirs_mean)[:, [0, 2]]
    cross = (flat_mine[:, 0] * flat_theirs[:, 1] - flat_mine[:, 1] * flat_theirs[:, 0]).sum()
    dot = (flat_mine * flat_theirs).sum()
    angle = np.arctan2(cross, dot)  # in the (x, z) plane, x toward z: -angle about +y
    turn = Rotation.from_rotvec([0.0, -angle, 0.0]).as_matrix()
    move = np.eye(4)
    move[:3, :3], move[:3, 3] = turn, theirs_mean - turn @ mine_mean
    miss = np.sqrt(np.mean(np.sum((mine @ turn.T + move[:3, 3] - theirs) ** 2, axis=1)))
    return move, float(miss)


def feet_share(world, names):
    """The Hips' place between the feet a clip (median over its frames): 0 over the right foot, 1 over the left, along
    the line between them on the floor."""
    right, left, hips = (world[:, names.index(name), :3, 3][:, [0, 2]] for name in (*FEET, "Hips"))
    line = left - right
    return float(np.median(((hips - right) * line).sum(axis=1) / np.maximum((line * line).sum(axis=1), 1e-9)))


def mean_turns(turns, weights):
    """The weighted mean of unit quaternions (views x frames x joints x 4, weights views x frames), each view's on the
    first's side, normalised."""
    sides = np.sign((turns * turns[:1]).sum(axis=-1, keepdims=True))
    sides[sides == 0] = 1.0
    total = (sides * turns * weights[:, :, None, None]).sum(axis=0)
    return total / np.linalg.norm(total, axis=-1, keepdims=True)


def aligned(worlds, weights):
    """Each view's one rigid move (`heading_fit`) onto the first view's joints' places, then again onto the views'
    mean after those moves; and each view's miss after the last (m)."""
    onto = worlds[0]
    for _ in range(2):
        fits = [heading_fit(world, onto, weight > 0) for world, weight in zip(worlds, weights)]
        moved = [world @ move[:3, :3].T + move[:3, 3] for world, (move, _) in zip(worlds, fits)]
        onto = sum(world * weight[:, None, None] for world, weight in zip(moved, weights)) / \
            weights.sum(axis=0)[:, None, None]
    return fits


def fused(views):
    """(the rig, its transforms against the parents frames x joints x 4 x 4 on the first view's timeline, GEM-X's
    static contact for it or None, the record) of one body from `views`, each (rig, transforms against the parents,
    GEM-X's contact_ik npz or None) of one camera, the first the trial's own (module docstring)."""
    rig, local, _ = views[0]
    names, parents = [str(name) for name in rig["names"]], np.asarray(rig["parents"])
    if list(np.flatnonzero(parents < 0)) != [0]:
        raise ValueError("a fused body needs one root, the first joint")
    hips, frames = names.index("Hips"), len(local)
    reference = pose_signal(played.chained(local, parents), hips)
    taken, record = [], {"views": []}
    for index, (view_rig, view_local, view_gemx) in enumerate(views):
        if [str(name) for name in view_rig["names"]] != names or not np.array_equal(view_rig["parents"], parents):
            raise ValueError(f"view {index}'s joints are not the first view's")
        view_world = played.chained(view_local, parents)
        shift, match = (0.0, 1.0) if index == 0 else delay(pose_signal(view_world, hips), reference)
        entry = {"shift frames": round(shift, 3), "pose match": round(match, 4), "joined": bool(match >= JOIN),
                 "hips between the feet": round(feet_share(view_world, names), 3)}
        record["views"].append(entry)
        if entry["joined"]:
            taken.append({"index": index, "shift": shift, "rig": view_rig, "gemx": view_gemx,
                          **dict(zip(("turns", "places", "weight"), resampled(view_local, shift, frames)))})
    weights = np.stack([view["weight"] for view in taken])
    worlds = [played.chained(composed(view["turns"], view["places"]), parents)[..., :3, 3] for view in taken]
    for view, (move, miss) in zip(taken, aligned(worlds, weights)):
        root = move @ composed(view["turns"][:, 0], view["places"][:, 0])
        view["turns"][:, 0], view["places"][:, 0] = Rotation.from_matrix(root[:, :3, :3]).as_quat(), root[:, :3, 3]
        turned = float(np.degrees(np.arctan2(move[0, 2], move[0, 0])))
        record["views"][view["index"]].update({"turned deg": round(turned, 2), "miss mm": round(1000 * miss, 1)})
    places = np.stack([view["places"] for view in taken])
    fused_local = composed(mean_turns(np.stack([view["turns"] for view in taken]), weights),
                           (places * weights[:, :, None, None]).sum(axis=0) / weights.sum(axis=0)[:, None, None])
    bind = np.array(rig["bind"], dtype=float)
    bind[:, :3, 3] = np.mean([np.asarray(view["rig"]["bind"], dtype=float)[:, :3, 3] for view in taken], axis=0)
    fused_rig = {**rig, "bind": bind,
                 "points": np.mean([np.asarray(view["rig"]["points"], dtype=float) for view in taken], axis=0)}
    record["hips between the feet"] = round(feet_share(played.chained(fused_local, parents), names), 3)
    return fused_rig, fused_local, fused_contact(taken, weights, frames), record


def fused_contact(taken, weights, frames):
    """GEM-X's static contact for the fused body ({static_conf_logits}: each view's probability at its nearest frame,
    averaged over the views that hold the frame and have it, back to a logit), or None when the first view has none."""
    if taken[0]["gemx"] is None or "static_conf_logits" not in taken[0]["gemx"]:
        return None
    total, count = 0.0, 0.0
    for view, weight in zip(taken, weights):
        if view["gemx"] is None or "static_conf_logits" not in view["gemx"]:
            continue
        logits = np.asarray(view["gemx"]["static_conf_logits"], dtype=float)
        nearest = np.clip(np.rint(np.arange(frames) + view["shift"]).astype(int), 0, len(logits) - 1)
        total = total + weight[:, None] / (1.0 + np.exp(-logits[nearest]))
        count = count + weight[:, None]
    chance = np.clip(total / np.maximum(count, 1e-9), 1e-6, 1 - 1e-6)
    return {"static_conf_logits": np.log(chance / (1 - chance))}
