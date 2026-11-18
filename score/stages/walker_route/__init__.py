"""A walker's route and its motion (#128, owner 2026-11-17: "we need like a path finding algorithm, that can splice the
path into kimodo makable clips, and fills it then"): the route found on the place's walkable floor, cut into pieces
Kimodo can make, each piece made from the pose the last one ended in, and the pieces joined into one motion whose
travel is the clips' own (never a clip slid along a line).

    route     the shortest way through the walker's spots on the physics check's own walkers' floor (a walker given
              `seconds`, its film's length, walks on round its spots until it lasts that long: `filled`)
              (place_build/ready `route`: its Recast-style spans, every solid's footprint taken off and the floor
              eroded by half a WALKWAY, doors open as passages, a stair flight a run of spans a riser apart), its
              corners kept by line of sight and rounded
    timed     the route walked one frame of Kimodo's RATE at a time: PACE on the flat, one tread a step on a flight
              (scene_clips' STEP_FRAMES cadence), eased from standing over EASE seconds at its start and back to
              standing at its end (its start and its stop)
    pieces    the frames cut where a flight starts or ends, and a stretch longer than PIECE_FRAMES into even pieces:
              each piece is a flat walk (WALKING, Kimodo's post-processing holding its feet on its floor) or a climb
              (STAIRS up or down, each foot asked on its tread at its stance middles, moved onto the tread's middle
              where the cadence put it across a riser (`footed`, `on_tread`), no post-processing: scene_clips' Not
              held); a piece shorter than LEAST_FRAMES joins the one before it
    asked     each piece in its own Kimodo canonical frame (its first root at the origin, its first heading +Z, its
              lowest ground Kimodo's floor): the dense root2d path and heading, and, for every piece after the first,
              a fullbody keyframe on each of its first OVERLAP frames holding the pose the piece before stood in
              there (so positions and velocities match across the join); a piece is made TAIL frames past its end so
              its own ending never shows
    upright   a flat piece made again from the next seed while it walks crouched or with its hands hanging
              (`posture`, `slouched`: its knees never straightening within KNEE_STRAIGHT, a hand swinging under
              SWING_LEAST), at most SEED_TRIES seeds, else refused
    joined    the pieces back in the scene's frame, each kept up to the next one's start and blended into it over the
              OVERLAP frames both hold, the foot standing across the join kept on its spot (`anchored`)
    grounded  the joined motion raised or lowered, frame by frame, so its standing foot stands on the scene's ground
              under it (`foot_gaps`, `standing_gap`, eased over GROUND_EASE frames; walker_route `ground`, before the
              rig): Kimodo's climb walks on up past a flight's last tread
    doors     a door marked `score:opens` (place_build/ready's swing_of: its hinge and turn) swings open SWING_SECONDS
              before it stands open OPEN_AHEAD before each walker crosses its plane and shut SHUT_AFTER past it
              (`door_swings`), written as time samples on its own prim (`swung_in`)
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
# A flat walk's sentence (owner, 2026-11-18, the street walker: "rlly walks like a monkey"): scene_clips.WALKING's "a
# person walking forward slowly and calmly" let its hands hang or clasp (of six seeds on street's walker_r1's route, each
# hand's swing 0.01 to 0.13 m); this one swung them 0.11 to 0.36 m on the same seeds, its knees and lean alike.
WALKING = "a person walks forward at a relaxed, steady pace with an upright posture, swinging both arms naturally"
STAIRS = {"up": "a person walking up a flight of stairs at a steady, easy pace",
          "down": "a person walking down a flight of stairs at a steady, easy pace"}  # scene_clips.STAIRS
HIP_OVER_SOLE = 1.0052  # scene_clips.HIP_OVER_SOLE: SOMA77's rest hips over its sole
FOOT_SIDE, HEEL, TOE = 0.1004, -0.0169, 0.1806  # scene_clips: the rest foot across and along from the hips
MOST_KEYFRAMES = 19  # Kimodo holds fewer than 20 a constraint type
# SOMA77 joints in Kimodo's NPZ: foot_contacts' six channels (left heel, toe, toe end, right heel, toe, toe end)
CONTACT_JOINTS = (69, 70, 71, 74, 75, 76)
SKATE_MOST = 0.02  # metres a planted foot may travel over its stance
PLANTED_SPEED = 0.25  # m/s: a foot's ball moving slower across the floor stands
GROUND_EASE = 9  # frames over which the body's lift onto its standing foot's ground is eased (`grounded`)
GROUND_MOST = 0.03  # metres a standing foot may stand over or in the ground under it
ROUTE_MOST = 0.10  # metres the root may stand off its route
BODY_RADIUS, KNEE, HEAD = 0.25, 0.3, 1.7  # cast/measure.py's body
LEVEL = 0.7  # a face whose normal's upward share is over this is a floor or a top, not a side
GROUND_AHEAD = 12  # frames either way over which a walker's ground is its route's highest (the next treads up)
STANCE_LEAST = 3  # frames: a shorter contact run is no stance
OPEN_AHEAD = 1.5  # seconds before a walker crosses an opening door's plane its leaf stands open
SHUT_AFTER = 1.5  # seconds after it crosses that the leaf starts swinging shut
SWING_SECONDS = 1.0  # seconds a leaf takes to swing open, or shut
SWING_POINTS = 9  # samples along a swing, eased in and out
DOOR_REACH = 0.6  # metres past a door's edge, and a knee over or under its foot, a root crossing its plane goes through
# A flat walk's posture (`posture`, `slouched`; the same evidence): whatever its sentence, a third of Kimodo's samples
# walked crouched, knees never straighter than 12 to 14 degrees and the hips 3 cm low (seeds 3 and 6 of six), where
# the rest straightened them to 0 to 6 at each stride; a piece over KNEE_STRAIGHT, or a hand swinging under
# SWING_LEAST, is made again from the next of SEED_TRIES seeds (SEED_STRIDE apart), else refused.
KNEE_STRAIGHT = 8.0  # degrees: a walking piece's knees straighten at least this far, each leg, at some stride
SWING_LEAST = 0.15  # metres: each hand's fore-and-aft swing about the hips (5th to 95th percentile) while walking
WALKING_SPEED = 0.6  # metres a second of the hips over which a frame is walking, not easing from or to standing
SEED_TRIES, SEED_STRIDE = 12, 100  # six were too few: street's walker_plaza2 slouched in all six (2026-11-18)
LEGS = ((67, 68, 69), (72, 73, 74))  # SOMA77's hip, knee and ankle joints (LeftLeg, LeftShin, LeftFoot; Right...)
HANDS = (14, 42)  # SOMA77's LeftHand and RightHand
KEYS = ("local_rot_mats", "global_rot_mats", "posed_joints", "root_positions", "smooth_root_pos", "foot_contacts",
        "global_root_heading")


# --- the route ------------------------------------------------------------------------------------------------------

def route(folder, through):
    """The walker's way through `through` (spots x, y, z) on the place_build scene's walkers' floor (ready.route):
    points and metres."""
    from score.stages.place_build import ready
    return ready.route(folder, through)


def round_again(through, count):
    """The walker's spots walked on round their loop, the last back to the first, to `count` spots in all: a walker
    filled to its film's length (`filled`) keeps walking rather than standing at its last spot. Refused for fewer than
    three spots: two would walk back on themselves, a turn on the spot no clip makes."""
    if len(through) < 3:
        raise ValueError(f"{len(through)} spots make no loop to walk round again: give at least three")
    return [list(through[index % len(through)]) for index in range(count)]


def filled(folder, through, seconds=None, tread=None):
    """The walker's route (`route`) and its timing (`timed`), walked on round its spots (`round_again`, a spot more at a
    time) until it lasts `seconds` (the clip's own, its film's length at the clip's rate): the spots walked, the route's
    points, its metres, the frames' roots and headings. Without `seconds`, the spots once."""
    walked, before = [list(spot) for spot in through], 0.0
    while True:
        points, metres = route(folder, walked)
        roots, headings = timed(points, tread=tread)
        if not seconds or seconds_of(len(roots)) >= seconds:
            return walked, points, metres, roots, headings
        if metres <= before:
            raise ValueError(f"walking on round {len(through)} spots does not lengthen the route past {metres} m")
        walked, before = round_again(through, len(walked) + 1), metres


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


def foot_grounds(roots, headings, ground_at):
    """The ground under each frame's left and right foot's heel and toe (frames x 2 sides x 2), the foot laid at rest
    beside the hips on the route, `ground_at` reading the ground under scene points (x, y, z), looked for from the
    route's height."""
    found = np.zeros((len(roots), 2, 2))
    for column, across in enumerate((FOOT_SIDE, -FOOT_SIDE)):
        spots = []
        for root, heading in zip(roots, headings):
            sin, cos = math.sin(heading), math.cos(heading)
            spots += [[root[0] + across * cos + along * sin, root[1], root[2] - across * sin + along * cos]
                      for along in (HEEL, TOE)]
        found[:, column] = np.asarray(ground_at(np.asarray(spots)), dtype=float).reshape(len(roots), 2)
    return found


def feet_ground(grounds):
    """The ground under each frame's left and right foot (frames x 2) from `foot_grounds`: the higher of its heel's
    and its toe's."""
    return np.asarray(grounds).max(axis=2)


def footed(grounds):
    """Whether each frame's left and right foot (frames x 2) lies whole on one tread or floor (`foot_grounds`: its
    heel's and its toe's ground within FLAT_RELIEF), not across a riser."""
    grounds = np.asarray(grounds)
    return np.abs(grounds[:, :, 0] - grounds[:, :, 1]) <= FLAT_RELIEF


def on_tread(frame, column, whole):
    """A climb's stance moved onto its tread: the middle of the run of frames on which foot `column` lies whole on
    one tread (`whole`: `footed`), the run nearest `frame` within half a step; on a floor longer than a step the
    nearest frame within half a step on which it lies whole, `frame` itself where none is near. The cadence alone
    put the stairwell's woman's feet across her risers, heel on one tread and toe in the next (2026-11-18)."""
    whole = np.asarray(whole, dtype=bool)
    reach = int(STEP_FRAMES / 2)
    near = [index for index in range(max(0, frame - reach), min(len(whole), frame + reach + 1)) if whole[index, column]]
    if not near:
        return frame
    nearest = min(near, key=lambda index: abs(index - frame))
    first, end = nearest, nearest + 1
    while first > 0 and whole[first - 1, column]:
        first -= 1
    while end < len(whole) and whole[end, column]:
        end += 1
    if end - first > STEP_FRAMES:  # a floor longer than a step: the cadence's own frame, or its nearest whole one
        return nearest
    return (first + end - 1) // 2


def asked(piece, roots, headings, feet, before=None, whole=None):
    """Kimodo's constraints for one piece (its frames start .. end + TAIL of the route, clipped to the route), in its
    canonical frame, with that frame (origin, heading, floor) and its frame count: root2d dense with its heading; for
    a climb each foot on its ground at its stance middles, each moved onto its tread's middle (`on_tread`, `whole`:
    the plan's `footed`, when given); for a piece after the first (`before`: the joined
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
            column = 0 if which == "left" else 1
            if whole is not None:
                frame = min(max(on_tread(start + frame, column, whole) - start, OVERLAP + 2), len(span) - 9)
            if frame in taken:
                continue
            taken.add(frame)
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


def foot_gaps(motion, ground_at):
    """Each frame's left and right foot's height over the ground under it (frames x 2, m; negative inside it): the
    least over its CONTACT_JOINTS of the joint's height over the ground under that joint (`ground_at`, looked for from
    the joint's own height), so a heel on its tread with its toe over the nosing stands at 0."""
    joints = np.asarray(motion["posed_joints"], dtype=float)
    spots = joints[:, list(CONTACT_JOINTS)].reshape(-1, 3)
    heights = np.asarray(ground_at(spots), dtype=float).reshape(len(joints), len(CONTACT_JOINTS))
    gaps = joints[:, list(CONTACT_JOINTS), 1] - heights
    return np.column_stack([gaps[:, :3].min(axis=1), gaps[:, 3:].min(axis=1)])


def standing_gap(motion, gaps):
    """Each frame's standing foot's gap (`foot_gaps`): the gap of the foot whose ball moves slower across the floor
    (the planted one), the lower of the two where both stand within PLANTED_SPEED."""
    joints = np.asarray(motion["posed_joints"], dtype=float)
    speeds = np.column_stack([np.linalg.norm(np.gradient(joints[:, joint, :][:, [0, 2]], axis=0), axis=1) * RATE
                              for joint in (CONTACT_JOINTS[1], CONTACT_JOINTS[4])])
    slower = np.where(speeds[:, 0] <= speeds[:, 1], gaps[:, 0], gaps[:, 1])
    return np.where((speeds < PLANTED_SPEED).all(axis=1), gaps.min(axis=1), slower)


def grounded(motion, ground_at):
    """The joined motion with its standing foot on the ground under it on every frame: the whole body raised or
    lowered (positions only, its pose untouched) by its standing foot's gap (`standing_gap`), eased over GROUND_EASE
    frames. Kimodo's climb holds its stance keys on a flight's treads to 2 cm but walks on up past the flight's last
    tread: the stairwell's woman stood 16 cm over her landing, dropped back onto the next flight and ended 39 cm over
    the top floor (2026-11-18, the owner: she "goes to high and, then kinda jumps down a small bit")."""
    lift = -standing_gap(motion, foot_gaps(motion, ground_at))
    half = GROUND_EASE // 2
    lift = np.convolve(np.pad(lift, half, mode="edge"), np.ones(2 * half + 1) / (2 * half + 1), mode="valid")
    out = dict(motion)
    for key in ("posed_joints", "root_positions", "smooth_root_pos"):
        value = np.array(motion[key])
        value[..., 1] += (lift[:, None] if value.ndim == 3 else lift).astype(value.dtype)
        out[key] = value
    return out


def own_frame(motion, roots, headings):
    """A scene-frame motion in its walker's placement frame (its route's start at the origin, its first heading +Z,
    its start's ground y = 0), floats as float32: the scene-clips motions/ file sim body and the rig read."""
    origin = np.array([roots[0][0], roots[0][1], roots[0][2]], dtype=float)
    own = moved(motion, origin, float(headings[0]), inverse=True)
    return {key: own[key].astype(np.float32) if own[key].dtype.kind == "f" else own[key] for key in own}


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


def measures(motion, roots, triangles, standing=None):
    """A walker's measures: its stances' foot skate (m), its root's distance from its route, its body's least
    clearance from every solid and (`standing`, each frame's standing foot's gap: `standing_gap`) how far its standing
    foot stood over or in the ground under it, with whether each is within its limit."""
    skate = skates(motion)
    ground_off = None if standing is None else float(np.abs(standing).max())
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
            "standing off ground max": None if ground_off is None else round(ground_off, 4),
            "within": bool((not skate or max(skate) <= SKATE_MOST) and off.max() <= ROUTE_MOST
                           and least >= BODY_RADIUS and (ground_off is None or ground_off <= GROUND_MOST))}


def posture(joints):
    """A made walk's posture over its walking frames (the hips over WALKING_SPEED; `joints` Kimodo's posed_joints, Y
    up): each knee's least flex (degrees, 0 straight) and each hand's fore-and-aft swing about the hips (m); None for
    a motion walking under a stride (2 STEP_FRAMES): the stairwell woman's 45 frames off her top tread, easing to a
    stop from a climbing pose, read crouched under every seed (2026-11-18), and a stride is the least a knee
    straightens in."""
    joints = np.asarray(joints, dtype=float)
    velocity = np.gradient(joints[:, 0, [0, 2]], axis=0) * RATE
    speed = np.linalg.norm(velocity, axis=1)
    walking = speed > WALKING_SPEED
    if walking.sum() < 2 * STEP_FRAMES:
        return None
    ahead = velocity[walking] / speed[walking, None]
    knees = []
    for hip, knee, ankle in LEGS:
        thigh, shin = joints[walking, hip] - joints[walking, knee], joints[walking, ankle] - joints[walking, knee]
        cosine = (thigh * shin).sum(axis=1) / np.linalg.norm(thigh, axis=1) / np.linalg.norm(shin, axis=1)
        knees.append(float((180.0 - np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))).min()))
    swings = []
    for hand in HANDS:
        along = ((joints[walking, hand] - joints[walking, 0])[:, [0, 2]] * ahead).sum(axis=1)
        swings.append(float(np.percentile(along, 95) - np.percentile(along, 5)))
    return {"knee least": [round(value, 1) for value in knees], "swing": [round(value, 3) for value in swings]}


def slouched(measured):
    """Why a walk's posture (`posture`) is no upright walk with its arms swinging, or None when it is: a knee that
    never straightens within KNEE_STRAIGHT, a hand swinging under SWING_LEAST."""
    if measured is None:
        return None
    if max(measured["knee least"]) > KNEE_STRAIGHT:
        return f"its knees never straighter than {max(measured['knee least'])} degrees, over {KNEE_STRAIGHT}"
    if min(measured["swing"]) < SWING_LEAST:
        return f"a hand swings {min(measured['swing'])} m, under {SWING_LEAST}"
    return None


def plan_file(folder):
    """The plan a walkers' run writes and Kimodo's program reads."""
    return pathlib.Path(folder) / "walkers.json"


def write_plan(folder, place, walkers):
    """The walkers' plan (per walker its route frames, headings, feet ground and pieces) as JSON."""
    plan_file(folder).write_text(json.dumps({"place": place, "walkers": walkers}))


# --- the doors they open ------------------------------------------------------------------------------------------

def crossings(roots, door):
    """The frames a walker's root crosses a door's plane through its doorway: `door` its middle, axes (across, up,
    through) and half sizes (ready.frame_of)."""
    roots = np.asarray(roots, float)
    middle, axes, half = (np.asarray(door[key], float) for key in ("middle", "axes", "half"))
    side = (roots - middle) @ axes[2]
    across = np.abs((roots - middle) @ axes[0])
    level = np.abs(roots[:, 1] - (middle[1] - half[1])) <= KNEE + DOOR_REACH
    passed = np.flatnonzero((np.sign(side[1:]) != np.sign(side[:-1])) & (across[1:] <= half[0] + DOOR_REACH)
                            & level[1:])
    return (passed + 1).tolist()


def open_windows(frames, rate=RATE):
    """The seconds a door stands open for walkers crossing it at `frames`: from OPEN_AHEAD before each crossing to
    SHUT_AFTER past it, windows that would swing shut and open again within two swings merged: [[from, to], ...]."""
    windows = []
    for frame in sorted(frames):
        start, end = frame / rate - OPEN_AHEAD, frame / rate + SHUT_AFTER
        if windows and start - windows[-1][1] <= 2 * SWING_SECONDS:
            windows[-1][1] = max(windows[-1][1], end)
        else:
            windows.append([start, end])
    return [[round(start, 4), round(end, 4)] for start, end in windows]


def swing_samples(windows, degrees):
    """The leaf's turn (degrees) over time for its open windows: shut, eased open over SWING_SECONDS up to each
    window's start, open through it, eased shut over SWING_SECONDS after: [(seconds, degrees), ...]."""
    ease = [(1 - math.cos(math.pi * share)) / 2 for share in np.linspace(0.0, 1.0, SWING_POINTS)]
    samples = []
    for start, end in windows:
        samples += [(start - SWING_SECONDS * (1 - share), degrees * eased)
                    for share, eased in zip(np.linspace(0.0, 1.0, SWING_POINTS), ease)]
        samples += [(end + SWING_SECONDS * share, degrees * (1 - eased))
                    for share, eased in zip(np.linspace(0.0, 1.0, SWING_POINTS), ease)]
    return [(round(float(seconds), 4), round(float(turn), 4)) for seconds, turn in samples]


def door_swings(doors, walkers):
    """Each opening door's swing for the walkers crossing it: `doors` {name: {middle, axes, half, hinge, degrees}},
    `walkers` {name: roots}; {door: {hinge, degrees, crossed: {walker: frames}, open: windows}} for every door a
    walker crosses."""
    swings = {}
    for name, door in sorted(doors.items()):
        crossed = {walker: crossings(roots, door) for walker, roots in sorted(walkers.items())}
        crossed = {walker: frames for walker, frames in crossed.items() if frames}
        if crossed:
            swings[name] = {"hinge": list(door["hinge"]), "degrees": float(door["degrees"]), "crossed": crossed,
                            "open": open_windows([frame for frames in crossed.values() for frame in frames])}
    return swings


def swung_in(scene_file, place, swings):
    """Each door's swing written on its own prim in the scene's root layer (so it is the strongest opinion): a hinge
    pivot (xformOp:translate:hinge and its inverse) round a rotateY:swing op, shut (0) by default and time-sampled
    over its windows at the stage's time codes. Run again, it replaces its own ops."""
    from pxr import Gf, Usd, UsdGeom
    stage = Usd.Stage.Open(str(scene_file))
    rate = stage.GetTimeCodesPerSecond()
    for name, swing in swings.items():
        prim = stage.GetPrimAtPath(f"/{place}/Objects/{name}")
        xformable = UsdGeom.Xformable(prim)
        kept = [op for op in xformable.GetOrderedXformOps() if not op.GetOpName().endswith((":hinge", ":swing"))]
        parent = np.asarray(UsdGeom.Xformable(prim.GetParent()).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
        hinge = np.append(swing["hinge"], 1.0) @ np.linalg.inv(parent)
        for attribute in ("xformOp:translate:hinge", "xformOp:rotateY:swing"):
            if prim.HasAttribute(attribute):
                prim.RemoveProperty(attribute)
        pivot = xformable.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble, "hinge")
        pivot.Set(Gf.Vec3d(*map(float, hinge[:3])))
        turn = xformable.AddRotateYOp(UsdGeom.XformOp.PrecisionFloat, "swing")
        turn.Set(0.0)
        for seconds, degrees in swing_samples(swing["open"], swing["degrees"]):
            turn.Set(degrees, Usd.TimeCode(seconds * rate))
        back = xformable.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble, "hinge", isInverseOp=True)
        xformable.SetXformOpOrder([pivot, turn, back, *kept])
    stage.GetRootLayer().Save()
