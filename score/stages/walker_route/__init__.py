"""A walker's route and its motion (#128, owner 2026-11-17: "we need like a path finding algorithm, that can splice the
path into kimodo makable clips, and fills it then"): the route found on the place's walkable floor, cut into pieces
Kimodo can make, each piece made from the pose the last one ended in, and the pieces joined into one motion whose
travel is the clips' own (never a clip slid along a line).

    route     the shortest way through the walker's spots on the physics check's own walkers' floor
              (place_build/ready `route`: its Recast-style spans, every solid's footprint taken off and the floor
              eroded by half a WALKWAY, doors open as passages, a stair flight a run of spans a riser apart), its
              corners kept by line of sight and rounded
    timed     the route walked one frame of Kimodo's RATE at a time: PACE on the flat, one tread a step on a flight
              (scene_clips' STEP_FRAMES cadence), eased from standing over EASE seconds at its start and back to
              standing at its end (its start and its stop)
    pieces    the frames cut where a flight starts or ends, and a stretch longer than PIECE_FRAMES into even pieces:
              each piece is a flat walk (WALKING, Kimodo's post-processing holding its feet on its floor) or a climb
              (STAIRS up or down, each foot asked on its tread at its stance middles, no post-processing: scene_clips'
              Not held); a piece shorter than LEAST_FRAMES joins the one before it
    asked     each piece in its own Kimodo canonical frame (its first root at the origin, its first heading +Z, its
              lowest ground Kimodo's floor): the dense root2d path and heading, and, for every piece after the first,
              a fullbody keyframe on each of its first OVERLAP frames holding the pose the piece before stood in
              there (so positions and velocities match across the join); a piece is made TAIL frames past its end so
              its own ending never shows
    joined    the pieces back in the scene's frame, each kept up to the next one's start and blended into it over the
              OVERLAP frames both hold, the foot standing across the join kept on its spot (`anchored`)
    measured  per stance (a foot's contact run in Kimodo's own foot_contacts) its joint's travel across the floor
              (`skate`, at most SKATE_MOST), the hips' distance from the route's line (at most ROUTE_MOST) and the body's
              clearance from every upright solid face between KNEE and HEAD over its ground (the route's highest within
              GROUND_AHEAD frames, so a flight's next treads are stood on, not walked into; at least BODY_RADIUS)

Kimodo runs in its own environment (tools/characters/clips/walker_route.py, free on this PC's card): this file holds
numpy, json and math at its top so that program loads it by path; the planning reads the scene through
place_build/ready, imported inside the functions that need it.
"""
import json
import math
import pathlib

import numpy as np

RATE = 30  # Kimodo's frames a second (scene_clips.RATE)
PACE = 1.0  # metres a second on the flat (scene_clips.WALK_PACE, the owner's 1.0 m/s walks)
STEP_FRAMES = 17.25  # frames a step (scene_clips.STEP_FRAMES): a climber takes one tread a step
FIRST_STANCE = 24  # scene_clips.FIRST_STANCE: the right foot's first stance middle of a walk from standing
EASE = 1.0  # seconds from standing to the pace, and back to standing at the end
PIECE_FRAMES = 210  # the longest piece, 7 s (Kimodo makes at most 10 s a prompt, with TAIL past it)
LEAST_FRAMES = 45  # a shorter piece joins the one before it
OVERLAP = 4  # frames a piece shares with the one before it, held to its pose
TAIL = 24  # frames a piece is made past its end
HELD_KEYS = 6  # at most this many keyframes (every other frame) hold a foot planted across a join
HOLD = 12  # frames the walker stands at its route's start before it sets off and at its end once it has stopped
FLAT_RELIEF = 0.02  # metres of ground change under which frames are flat (scene_clips.FLAT_RELIEF)
FLIGHT_SLOPE = 0.15  # rise over run along the route above which a frame is on a flight
WALKING = "a person walking forward slowly and calmly"  # scene_clips.WALKING
STAIRS = {"up": "a person walking up a flight of stairs at a steady, easy pace",
          "down": "a person walking down a flight of stairs at a steady, easy pace"}  # scene_clips.STAIRS
HIP_OVER_SOLE = 1.0052  # scene_clips.HIP_OVER_SOLE: SOMA77's rest hips over its sole
FOOT_SIDE, HEEL, TOE = 0.1004, -0.0169, 0.1806  # scene_clips: the rest foot across and along from the hips
MOST_KEYFRAMES = 19  # Kimodo holds fewer than 20 a constraint type
# SOMA77 joints in Kimodo's NPZ: foot_contacts' six channels (left heel, toe, toe end, right heel, toe, toe end)
CONTACT_JOINTS = (69, 70, 71, 74, 75, 76)
SKATE_MOST = 0.02  # metres a planted foot may travel over its stance
ROUTE_MOST = 0.10  # metres the root may stand off its route
BODY_RADIUS, KNEE, HEAD = 0.25, 0.3, 1.7  # cast/measure.py's body
LEVEL = 0.7  # a face whose normal's upward share is over this is a floor or a top, not a side
GROUND_AHEAD = 12  # frames either way over which a walker's ground is its route's highest (the next treads up)
STANCE_LEAST = 3  # frames: a shorter contact run is no stance
KEYS = ("local_rot_mats", "global_rot_mats", "posed_joints", "root_positions", "smooth_root_pos", "foot_contacts",
        "global_root_heading")


# --- the route ------------------------------------------------------------------------------------------------------

def route(folder, through):
    """The walker's way through `through` (spots x, y, z) on the place_build scene's walkers' floor (ready.route):
    points and metres."""
    from score.stages.place_build import ready
    return ready.route(folder, through)


def heading_of(step):
    """Kimodo's heading of a step (dx, dz): radians about up, 0 facing +Z, pi/2 facing +X."""
    return math.atan2(step[0], step[1])


def timed(points, pace=PACE, tread=None):
    """The route walked one frame of RATE at a time (frames x 3, the route's own height) and its heading at each:
    `pace` m/s on the flat, one `tread` (m, run) every STEP_FRAMES where the route climbs, eased in from standing and
    out to standing over EASE seconds, stood HOLD frames at either end."""
    points = np.asarray(points, dtype=float)
    steps = np.linalg.norm(np.diff(points[:, [0, 2]], axis=0), axis=1)
    keep = np.concatenate([[True], steps > 1e-9])
    points = points[keep]
    along = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(points[:, [0, 2]], axis=0), axis=1))])
    if along[-1] <= 0:
        raise ValueError("the route does not go anywhere")
    fine = np.arange(0.0, along[-1], 0.01)
    fine = np.append(fine, along[-1])
    height = np.interp(fine, along, points[:, 1])
    slope = np.abs(np.gradient(height, fine)) if len(fine) > 2 else np.zeros_like(fine)
    climbing = slope > FLIGHT_SLOPE
    speed = np.where(climbing, (tread or 0.28) * RATE / STEP_FRAMES, pace)
    speed = np.convolve(np.pad(speed, 25, mode="edge"), np.ones(51) / 51, mode="valid")  # half a metre each way
    ease = pace * EASE / 2  # metres the eased start and stop take at a steady acceleration
    speed = np.minimum(speed, np.sqrt(np.maximum(fine, 0.0) / ease * pace ** 2 + 0.0025))
    speed = np.minimum(speed, np.sqrt(np.maximum(along[-1] - fine, 0.0) / ease * pace ** 2 + 0.0025))
    seconds = np.concatenate([[0.0], np.cumsum(np.diff(fine) / ((speed[1:] + speed[:-1]) / 2))])
    frames = int(seconds[-1] * RATE) + 1
    at = np.interp(np.arange(frames) / RATE, seconds, fine)
    at = np.concatenate([np.zeros(HOLD), at, np.full(HOLD, along[-1])])
    frames += 2 * HOLD
    roots = np.column_stack([np.interp(at, along, points[:, 0]), np.interp(at, along, points[:, 1]),
                             np.interp(at, along, points[:, 2])])
    ahead = np.interp(np.minimum(at + 0.3, along[-1]), along, points[:, 0]), \
        np.interp(np.minimum(at + 0.3, along[-1]), along, points[:, 2])
    behind = np.interp(np.maximum(at - 0.3, 0.0), along, points[:, 0]), \
        np.interp(np.maximum(at - 0.3, 0.0), along, points[:, 2])
    headings = np.unwrap([heading_of((ahead[0][index] - behind[0][index], ahead[1][index] - behind[1][index]))
                          for index in range(frames)])
    return roots, headings


# --- the pieces ------------------------------------------------------------------------------------------------------

def on_flight(roots):
    """Which frames climb or descend (the route's ground changing over FLIGHT_SLOPE of its run, widened by half a
    step either way so a flight's first and last treads count)."""
    rise = np.abs(np.gradient(roots[:, 1]))
    run = np.maximum(np.linalg.norm(np.gradient(roots[:, [0, 2]], axis=0), axis=1), 1e-6)
    climbing = (rise / run > FLIGHT_SLOPE) & (rise > 1e-4)
    width = int(STEP_FRAMES / 2)
    return np.convolve(climbing.astype(float), np.ones(2 * width + 1), mode="same") > 0


def pieces(roots):
    """The frames cut into pieces Kimodo can make: [{start, end, kind ("walk", "up", "down")}], end exclusive."""
    flight = on_flight(roots)
    runs, start = [], 0
    for frame in range(1, len(roots) + 1):
        if frame == len(roots) or flight[frame] != flight[start]:
            rise = roots[frame - 1, 1] - roots[start, 1]
            kind = ("up" if rise > 0 else "down") if flight[start] and abs(rise) > FLAT_RELIEF else "walk"
            runs.append({"start": start, "end": frame, "kind": kind})
            start = frame
    merged = []
    for run in runs:  # a short run joins the one before it, a climb its kind kept
        short = LEAST_FRAMES - (run["end"] - run["start"])
        if merged and short > 0 and run["kind"] == "walk" and merged[-1]["kind"] != "walk" and \
                merged[-1]["end"] - merged[-1]["start"] - short >= LEAST_FRAMES and run is runs[-1]:
            merged[-1]["end"] -= short  # the walk off a flight at the route's end is a walk: Kimodo's climb asked
            merged.append({"start": merged[-1]["end"], "end": run["end"], "kind": "walk"})  # on to its end climbed on
            continue  # over its floor (the stairwell's woman, 2026-11-17)
        if merged and (run["end"] - run["start"] < LEAST_FRAMES or merged[-1]["end"] - merged[-1]["start"] < LEAST_FRAMES):
            kind = merged[-1]["kind"] if merged[-1]["kind"] != "walk" else run["kind"]
            merged[-1] = {"start": merged[-1]["start"], "end": run["end"], "kind": kind}
        else:
            merged.append(dict(run))
    found = []
    for run in merged:  # a long run into even pieces
        count = max(1, math.ceil((run["end"] - run["start"]) / PIECE_FRAMES))
        edges = np.linspace(run["start"], run["end"], count + 1).round().astype(int)
        found += [{"start": int(low), "end": int(high), "kind": run["kind"]} for low, high in zip(edges[:-1], edges[1:])]
    return found


# --- frames ---------------------------------------------------------------------------------------------------------

def turn_y(angle):
    """The rotation turning a direction by `angle` radians about up (Kimodo's heading grows from +Z toward +X)."""
    sin, cos = math.sin(angle), math.cos(angle)
    return np.array([[cos, 0.0, sin], [0.0, 1.0, 0.0], [-sin, 0.0, cos]])


def to_frame(points, origin, heading):
    """Scene points (... x 3) in a canonical frame: `origin` at (0, 0, 0), `heading` turned to +Z."""
    return (np.asarray(points, dtype=float) - origin) @ turn_y(-heading).T


def from_frame(points, origin, heading):
    """Canonical points (... x 3) back in the scene's frame."""
    return np.asarray(points, dtype=float) @ turn_y(heading).T + origin


def moved(motion, origin, heading, inverse=False):
    """A Kimodo motion (KEYS) from its canonical frame into the scene's (or back, `inverse`): positions moved and
    turned, the root's and every global turn turned, the heading vectors turned."""
    out = {key: np.array(motion[key]) for key in KEYS if key in motion}
    turn = turn_y(-heading if inverse else heading)
    place = (lambda points: to_frame(points, origin, heading)) if inverse else \
        (lambda points: from_frame(points, origin, heading))
    for key in ("posed_joints", "root_positions", "smooth_root_pos"):
        out[key] = place(out[key])
    out["global_rot_mats"] = np.einsum("ij,...jk->...ik", turn, out["global_rot_mats"])
    out["local_rot_mats"][:, 0] = np.einsum("ij,fjk->fik", turn, out["local_rot_mats"][:, 0])
    angle = np.arctan2(out["global_root_heading"][:, 1], out["global_root_heading"][:, 0])
    angle = angle + (-heading if inverse else heading)
    out["global_root_heading"] = np.column_stack([np.cos(angle), np.sin(angle)]).astype(np.float32)
    return out


def axis_angle(matrices):
    """Rotation matrices (... x 3 x 3) as axis-angle vectors (... x 3), radians."""
    matrices = np.asarray(matrices, dtype=float)
    cos = np.clip((np.trace(matrices, axis1=-2, axis2=-1) - 1) / 2, -1.0, 1.0)
    angle = np.arccos(cos)
    axis = np.stack([matrices[..., 2, 1] - matrices[..., 1, 2], matrices[..., 0, 2] - matrices[..., 2, 0],
                     matrices[..., 1, 0] - matrices[..., 0, 1]], axis=-1)
    sin = np.sin(angle)
    small = sin < 1e-6
    scale = np.where(small, 0.5, angle / np.where(small, 1.0, 2 * sin))
    vectors = axis * scale[..., None]
    near_pi = small & (angle > 3.0)
    if near_pi.any():  # angle near pi: the axis from the symmetric part
        flat = matrices[near_pi]
        sym = (flat + np.eye(3)) / 2
        column = np.argmax(np.diagonal(sym, axis1=-2, axis2=-1), axis=-1)
        picked = sym[np.arange(len(sym)), :, column]
        picked /= np.linalg.norm(picked, axis=-1, keepdims=True)
        vectors[near_pi] = picked * angle[near_pi][:, None]
    return vectors


# --- what each piece is asked ----------------------------------------------------------------------------------------

def stance_frames(count, first, side):
    """Stance middles (frame, side) every STEP_FRAMES from `first` (its foot `side`), the sides alternating, before
    the last TAIL frames' end."""
    found, step = [], 0
    while round(first + step * STEP_FRAMES) < count:
        found.append((int(round(first + step * STEP_FRAMES)),
                      side if step % 2 == 0 else ("left" if side == "right" else "right")))
        step += 1
    return found


def next_stance(contacts, frame):
    """From a made motion's foot_contacts (frames x 6), the next stance middle after `frame` and its foot: the last
    stance whose middle is at or before `frame` with STEP_FRAMES added, the other foot."""
    middles = []
    for side, channels in (("left", [0, 1, 2]), ("right", [3, 4, 5])):
        down = np.asarray(contacts)[:, channels].any(axis=1)
        start = None
        for index, value in enumerate(np.append(down, False)):
            if value and start is None:
                start = index
            elif not value and start is not None:
                if index - start >= STANCE_LEAST:
                    middles.append(((start + index - 1) / 2, side))
                start = None
    before = [middle for middle in middles if middle[0] <= frame]
    if not before:
        return frame + FIRST_STANCE, "right"
    middle, side = max(before)
    return middle + STEP_FRAMES, "left" if side == "right" else "right"


def feet_ground(roots, headings, ground_at):
    """The ground under each frame's left and right foot (frames x 2): the higher of its heel's and its toe's,
    `ground_at` reading the ground under scene points (x, y, z), looked for from the route's height."""
    found = np.zeros((len(roots), 2))
    for column, across in enumerate((FOOT_SIDE, -FOOT_SIDE)):
        spots = []
        for root, heading in zip(roots, headings):
            sin, cos = math.sin(heading), math.cos(heading)
            spots += [[root[0] + across * cos + along * sin, root[1], root[2] - across * sin + along * cos]
                      for along in (HEEL, TOE)]
        heights = np.asarray(ground_at(np.asarray(spots)), dtype=float).reshape(len(roots), 2)
        found[:, column] = heights.max(axis=1)
    return found


def asked(piece, roots, headings, feet, before=None):
    """Kimodo's constraints for one piece (its frames start .. end + TAIL of the route, clipped to the route), in its
    canonical frame, with that frame (origin, heading, floor) and its frame count: root2d dense with its heading; for
    a climb each foot on its ground at its stance middles; for a piece after the first (`before`: the joined
    motion so far in the scene's frame), a fullbody keyframe on each of its first OVERLAP frames holding that pose."""
    start, end = piece["start"], min(piece["end"] + TAIL, len(roots))
    span = roots[start:end]
    if before is None:
        origin_xz, heading = span[0, [0, 2]], float(headings[start])
    else:
        origin_xz = before["smooth_root_pos"][start, [0, 2]]
        vector = before["global_root_heading"][start]
        heading = float(math.atan2(vector[1], vector[0]))
    lows = [span[:, 1].min()] + ([feet[start:end].min()] if piece["kind"] != "walk" else [])
    floor = float(min(lows))
    origin = np.array([origin_xz[0], floor, origin_xz[1]])
    path = to_frame(span, origin, heading)
    turned = np.unwrap(headings[start:end]) - heading
    turned = (turned + math.pi) % (2 * math.pi) - math.pi
    found = [{"type": "root2d", "frame_indices": list(range(len(span))),
              "smooth_root_2d": np.round(path[:, [0, 2]], 5).tolist(),
              "global_root_heading": np.round(np.column_stack([np.cos(turned), np.sin(turned)]), 6).tolist()}]
    if before is not None:
        held = moved({key: before[key][start:start + OVERLAP] for key in KEYS}, origin, heading, inverse=True)
        found[0]["smooth_root_2d"][:OVERLAP] = np.round(held["smooth_root_pos"][:, [0, 2]], 5).tolist()
        found[0]["global_root_heading"][:OVERLAP] = np.round(held["global_root_heading"], 6).tolist()
        found.append({"type": "fullbody", "frame_indices": list(range(OVERLAP)),
                      "root_positions": np.round(held["root_positions"], 5).tolist(),
                      "local_joints_rot": np.round(axis_angle(held["local_rot_mats"]), 6).tolist(),
                      "smooth_root_2d": np.round(held["smooth_root_pos"][:, [0, 2]], 5).tolist()})
    keys = {"left": [], "right": []}  # per foot: (frame, hips in the piece's frame, SOMA77 local turns)
    if before is not None:  # a foot planted across the join stays where it stood (the piece before's own tail)
        tail = moved({key: before[key][start:start + TAIL] for key in KEYS}, origin, heading, inverse=True)
        turns = axis_angle(tail["local_rot_mats"])
        for which, channels in (("left", [0, 1, 2]), ("right", [3, 4, 5])):
            down = np.asarray(tail["foot_contacts"])[:, channels].any(axis=1)
            frame = OVERLAP
            while frame < min(len(down), OVERLAP + 2 * HELD_KEYS) and down[frame] and down[OVERLAP - 1]:
                keys[which].append((frame, tail["root_positions"][frame], turns[frame]))
                frame += 2
    if piece["kind"] != "walk":
        first, side = (FIRST_STANCE, "right") if before is None else next_stance(before["foot_contacts"][:start + OVERLAP],
                                                                                   start + OVERLAP - 1)
        first = first - start if before is not None else first
        taken = {frame for side_keys in keys.values() for frame, _, _ in side_keys}
        for frame, which in stance_frames(len(span) - 8, max(first, OVERLAP + 2), side):
            if frame in taken:
                continue
            column = 0 if which == "left" else 1
            hips = [span[frame, 0], feet[start + frame, column] + HIP_OVER_SOLE, span[frame, 2]]
            pose = np.zeros((77, 3))
            pose[0, 1] = turned[frame]
            keys[which].append((frame, to_frame([hips], origin, heading)[0], pose))
    for which in ("left", "right"):
        mine = sorted(keys[which], key=lambda key: key[0])[:MOST_KEYFRAMES]
        if mine:
            found.append({"type": f"{which}-foot", "frame_indices": [int(key[0]) for key in mine],
                          "root_positions": np.round([key[1] for key in mine], 5).tolist(),
                          "local_joints_rot": np.round([key[2] for key in mine], 6).tolist()})
    sentence = WALKING if piece["kind"] == "walk" else STAIRS[piece["kind"]]
    return {"constraints": found, "origin": origin.tolist(), "heading": heading, "frames": len(span),
            "sentence": sentence, "postprocess": piece["kind"] == "walk"}


def seconds_of(frames):
    """The duration that makes Kimodo give exactly `frames` frames (it takes int(duration * fps))."""
    return (frames + 0.5) / RATE


def joined(before, made, start):
    """The joined motion (the scene's frame) so far with a made piece (already in the scene's frame) starting at
    route frame `start`: `before` kept up to `start`, the two blended over the OVERLAP frames both hold, then the
    piece."""
    if before is None:
        return {key: np.array(made[key]) for key in KEYS}
    out = {}
    weights = (np.arange(OVERLAP) + 1) / (OVERLAP + 1)
    for key in KEYS:
        old, new = np.asarray(before[key][start:start + OVERLAP]), np.asarray(made[key][:OVERLAP])
        if key == "foot_contacts":
            blend = np.where(weights[:, None] < 0.5, old, new)
        else:
            shape = (OVERLAP,) + (1,) * (old.ndim - 1)
            blend = old * (1 - weights.reshape(shape)) + new * weights.reshape(shape)
            if key.endswith("rot_mats"):
                left, _, right = np.linalg.svd(blend)
                blend = left @ right
            if key == "global_root_heading":
                blend /= np.linalg.norm(blend, axis=-1, keepdims=True)
        out[key] = np.concatenate([np.asarray(before[key][:start]), blend.astype(old.dtype),
                                   np.asarray(made[key][OVERLAP:])])
    return anchored(out, start)


def anchored(motion, start):
    """The joined motion with the stance standing across the join at `start` kept where it stood: from the join on,
    the whole body moved across the floor (positions only, so its pose is untouched) by the planted foot's slip off
    the spot it stood on at the join, through that stance, the last slip held after it. Kimodo holds the join's
    keyframes only loosely without its post-processing (a climb's): the stairwell's woman slid 5 cm through her first
    tread's join (2026-11-17)."""
    contacts = np.asarray(motion["foot_contacts"]) > 0.5
    if start >= len(contacts) or not contacts[start].any():
        return motion
    channel = int(np.flatnonzero(contacts[start])[-1])
    end = start
    while end < len(contacts) and contacts[end, channel]:
        end += 1
    return unslipped(motion, channel, start, end)


def unslipped(motion, channel, start, end):
    """The motion with the whole body moved across the floor, from `start` on, by contact `channel`'s joint's slip
    off where it stood at `start`, through `end`, the last slip held after it."""
    joint = np.asarray(motion["posed_joints"])[:, CONTACT_JOINTS[channel]]
    slip = np.zeros((len(joint), 3))
    slip[start:end, [0, 2]] = joint[start:end, [0, 2]] - joint[start, [0, 2]]
    slip[end:] = slip[end - 1]
    out = dict(motion)
    for key in ("posed_joints", "root_positions", "smooth_root_pos"):
        value = np.asarray(motion[key])
        out[key] = (value - (slip[:, None] if value.ndim == 3 else slip)).astype(value.dtype)
    return out


def held_feet(motion):
    """The joined motion with every stance that slips over SKATE_MOST held on its spot (`unslipped` by its slipping
    channel, the stances in order): Kimodo's post-processing leaves a stopping walker's last stance 3 to 4 cm adrift
    (the street's walkers, 2026-11-17), and a climb has none."""
    for _ in range(len(stances(np.asarray(motion["foot_contacts"]) > 0.5))):
        joints = np.asarray(motion["posed_joints"])
        over = [(start, channel, end) for channel, start, end in stances(np.asarray(motion["foot_contacts"]) > 0.5)
                if np.linalg.norm(joints[start:end, CONTACT_JOINTS[channel]][:, [0, 2]]
                                  - joints[start, CONTACT_JOINTS[channel]][[0, 2]], axis=1).max() > SKATE_MOST]
        if not over:
            break
        start, channel, end = min(over)
        motion = unslipped(motion, channel, start, end)
    return motion


# --- the measures ---------------------------------------------------------------------------------------------------

def stances(contacts):
    """Each stance (channel, first frame, end frame) of a motion's foot_contacts: contact runs of STANCE_LEAST frames
    or more."""
    found = []
    for channel in range(contacts.shape[1]):
        start = None
        for index, value in enumerate(np.append(contacts[:, channel], False)):
            if value and start is None:
                start = index
            elif not value and start is not None:
                if index - start >= STANCE_LEAST:
                    found.append((channel, start, index))
                start = None
    return found


def skates(motion):
    """Each stance's foot skate (m): the most its contact joint travels across the floor from where the stance
    began."""
    joints = np.asarray(motion["posed_joints"])
    found = []
    for channel, start, end in stances(np.asarray(motion["foot_contacts"]) > 0.5):
        track = joints[start:end, CONTACT_JOINTS[channel]][:, [0, 2]]
        found.append(float(np.linalg.norm(track - track[0], axis=1).max()))
    return found


def route_off(motion, roots):
    """The hips' distance on the floor from the route (m, each frame): to the nearest point of the route's line,
    looked for along the stretch walked within a second of that frame (so a stretch passing near another is never
    taken for it). The hips, not Kimodo's smoothed root, whose filter drifts up to 10 cm in a clip's last frames
    while the hips stand still (camp's walkers, 2026-11-17)."""
    root = np.asarray(motion["root_positions"])[:, [0, 2]]
    line = np.asarray(roots)[:, [0, 2]]
    found = np.zeros(len(root))
    for frame, point in enumerate(root):
        low, high = max(0, frame - RATE), min(len(line) - 1, frame + RATE)
        if high <= low:
            found[frame] = float(np.linalg.norm(point - line[low]))
            continue
        found[frame] = float(segment_distance(point[None], line[low:high], line[low + 1:high + 1]).min())
    return found


def segment_distance(points, starts, ends):
    """Distance from each 2D point (n x 2) to each segment (m x 2 ends): n x m."""
    direction = ends - starts
    length = np.maximum((direction ** 2).sum(axis=1), 1e-12)
    share = np.clip(((points[:, None] - starts[None]) * direction[None]).sum(axis=2) / length[None], 0.0, 1.0)
    nearest = starts[None] + share[..., None] * direction[None]
    return np.linalg.norm(points[:, None] - nearest, axis=2)


def clearance(points, grounds, triangles):
    """Each point's (x, z of the body's middle) distance across the floor to the nearest solid face standing upright
    (its normal within LEVEL of level) that reaches between KNEE and HEAD over its ground (`grounds`, one a point);
    `triangles` n x 3 x 3; inf where none is near."""
    triangles = np.asarray(triangles, dtype=float)
    found = np.full(len(points), np.inf)
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]) if len(triangles) else []
    if len(triangles):  # a floor, tread or table top is stood on or reached over, never walked into: its sides are
        upright = np.abs(normals[:, 1]) <= LEVEL * np.maximum(np.linalg.norm(normals, axis=1), 1e-12)
        triangles = triangles[upright]
    if not len(triangles):
        return found
    low, high = triangles[:, :, 1].min(axis=1), triangles[:, :, 1].max(axis=1)
    flat = triangles[:, :, [0, 2]]
    box_low, box_high = flat.min(axis=1), flat.max(axis=1)
    for index, (point, ground) in enumerate(zip(np.asarray(points)[:, [0, 2]], grounds)):
        near = (high >= ground + KNEE) & (low <= ground + HEAD) & \
            np.all(box_low <= point + 1.5, axis=1) & np.all(box_high >= point - 1.5, axis=1)
        if not near.any():
            continue
        tris = flat[near]
        one, two = tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]
        area = one[:, 0] * two[:, 1] - one[:, 1] * two[:, 0]
        offset = point - tris[:, 0]
        safe = np.where(np.abs(area) > 1e-12, area, 1.0)
        first = (offset[:, 0] * two[:, 1] - offset[:, 1] * two[:, 0]) / safe
        second = (one[:, 0] * offset[:, 1] - one[:, 1] * offset[:, 0]) / safe
        inside = (np.abs(area) > 1e-12) & (first >= 0) & (second >= 0) & (first + second <= 1)
        if inside.any():
            found[index] = 0.0
            continue
        edges = segment_distance(point[None], np.concatenate([tris[:, 0], tris[:, 1], tris[:, 2]]),
                                 np.concatenate([tris[:, 1], tris[:, 2], tris[:, 0]]))
        found[index] = float(edges.min())
    return found


def measures(motion, roots, triangles):
    """A walker's measures: its stances' foot skate (m), its root's distance from its route and its body's least
    clearance from every solid, with whether each is within its limit."""
    skate = skates(motion)
    off = route_off(motion, roots)
    root = np.asarray(motion["root_positions"])
    count = min(len(root), len(roots))
    ground = np.array([roots[max(0, frame - GROUND_AHEAD):frame + GROUND_AHEAD + 1, 1].max() for frame in range(count)])
    clear = clearance(root[:count], ground, triangles)
    least = float(clear.min()) if len(clear) else float("inf")
    return {"stances": len(skate), "skate max": round(max(skate), 4) if skate else None,
            "skate median": round(float(np.median(skate)), 4) if skate else None,
            "skate over": int(sum(value > SKATE_MOST for value in skate)),
            "route off max": round(float(off.max()), 4), "route off mean": round(float(off.mean()), 4),
            "clearance least": round(least, 4) if np.isfinite(least) else None,
            "within": bool((not skate or max(skate) <= SKATE_MOST) and off.max() <= ROUTE_MOST
                           and least >= BODY_RADIUS)}


def plan_file(folder):
    """The plan a walkers' run writes and Kimodo's program reads."""
    return pathlib.Path(folder) / "walkers.json"


def write_plan(folder, place, walkers):
    """The walkers' plan (per walker its route frames, headings, feet ground and pieces) as JSON."""
    plan_file(folder).write_text(json.dumps({"place": place, "walkers": walkers}))
