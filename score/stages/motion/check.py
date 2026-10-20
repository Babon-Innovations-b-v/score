"""The motion check (#23; ideas from 4DCodeBench, arXiv 2610.03715, no code taken: it has no licence): free gates on
how each rigid move of the motion stage moves, read off the composed stage frame by frame at the stage's own rate,
against the move's intended motion in its record. "Nothing passes through anything" is the motion stage's `clear`.

    follows      a path's prim keeps to its record's curve (in its parent's frame, x and z) as the discrete Frechet
                 match allowing any speed: every frame within FOLLOW_MOST of the curve, never going back along it
                 more than FOLLOW_MOST, and over its round covering the whole curve (a closed path once round, an
                 open one from its first point to its last); a swing, spin or turn only turns about the upright (its
                 up within TILT_MOST degrees), a swing as far as its record's angle (within ANGLE_MOST); a slide or
                 climb only shifts, along one line (within LINE_MOST degrees), never turning
    steps        no frame's step (the farthest a corner of its box moves from one frame to the next) is a jump: over
                 JUMP_LEAST metres and over JUMP_RATIO times the move's 90th percentile moving step
    moving area  what moves in the place's own scopes is what the records move: every prim whose transform varies in
                 time is a moved prim or under one, and every moved prim moves (its box over STILL_MOST metres)

The moving area is read in 3D, not on a rendered picture: what moves is the prims, so a film needs no render to be
checked. Frames are read at most READS_MOST a move (a long round strided evenly)."""
import numpy as np
from pxr import Usd, UsdGeom

from score import checks
import motion_layer  # noqa: E402  (tools/usd, on the path by this package's __init__)

FOLLOW_MOST = 0.05
TILT_MOST = 0.5
ANGLE_MOST = 1.0
LINE_MOST = 2.0
JUMP_LEAST = 0.05
JUMP_RATIO = 4.0
STILL_MOST = 0.001
READS_MOST = 2400
TURNS = ("swing", "spin", "turn")
SHIFTS = ("slide", "climb")


def frame_codes(start, end, rate):
    """The time codes of every frame from `start` to `end` seconds, strided to at most READS_MOST."""
    codes = np.arange(start * rate, end * rate + 1e-9, 1.0)
    stride = max(1, int(np.ceil(len(codes) / READS_MOST)))
    return codes[::stride]


def local_at(prim, code):
    """The prim's local transform at a time code (row vectors, as OpenUSD writes them)."""
    return np.asarray(UsdGeom.Xformable(prim).GetLocalTransformation(Usd.TimeCode(float(code))))


def rotation(matrix):
    """The rotation of a transform, its scale taken off its rows."""
    return matrix[:3, :3] / np.linalg.norm(matrix[:3, :3], axis=1, keepdims=True)


def turned_from(rest, matrix):
    """The rotation from the rest transform to `matrix`, in the parent's frame (row vectors)."""
    return rotation(rest).T @ rotation(matrix)


def tilt_of(turn):
    """How far a rotation tips the upright, degrees."""
    return float(np.degrees(np.arccos(np.clip(np.array([0.0, 1.0, 0.0]) @ turn @ np.array([0.0, 1.0, 0.0]), -1, 1))))


def angle_of(turn):
    return float(np.degrees(np.arccos(np.clip((np.trace(turn) - 1.0) / 2.0, -1.0, 1.0))))


# --- follows ------------------------------------------------------------------------------------------------------

def along_curve(spots, curve, along):
    """For each spot [x, z]: (its distance to the nearest point of the curve, that point's length along it)."""
    distances, lengths = [], []
    for chunk in np.array_split(spots, max(1, len(spots) // 256)):
        apart = np.linalg.norm(chunk[:, None, :] - curve[None, :, :], axis=2)
        nearest = apart.argmin(axis=1)
        distances.append(apart[np.arange(len(chunk)), nearest])
        lengths.append(along[nearest])
    return np.concatenate(distances), np.concatenate(lengths)


def path_faults(entry, spots, curve, along):
    """A path's faults: spots off its curve, going back along it, or not covering it in its round."""
    name, total = entry["name"], float(along[-1])
    closed = entry["path"].get("closed", True)
    off, lengths = along_curve(spots, curve, along)
    faults = []
    if off.max() > FOLLOW_MOST:
        faults.append(f"{name}: {off.max():.2f} m off its path's curve at its frame {int(off.argmax())}")
    steps = np.diff(lengths)
    if closed:  # across the seam the length wraps: the shorter way round is the step
        steps = (steps + total / 2.0) % total - total / 2.0
    if len(steps) and steps.min() < -FOLLOW_MOST:
        faults.append(f"{name}: goes {-steps.min():.2f} m back along its path at its frame {int(steps.argmin()) + 1}")
    covered = float(np.clip(steps, 0.0, None).sum()) if closed else float(lengths[-1] - lengths[0])
    if abs(covered - total) > max(FOLLOW_MOST, 0.01 * total):
        faults.append(f"{name}: covers {covered:.2f} m of its {total:.2f} m path in its round")
    return faults, float(off.max())


def turn_faults(entry, kind, poses, rest):
    """A turn's faults: tipping off the upright, or a swing short of (or past) its record's angle."""
    turns = [turned_from(rest, pose) for pose in poses]
    tilt = max(tilt_of(turn) for turn in turns)
    faults = [f"{entry['name']}: tips {tilt:.1f} degrees off the upright as it turns"] if tilt > TILT_MOST else []
    if kind == "swing":
        reached, wanted = max(angle_of(turn) for turn in turns), abs(float(entry["swing"]["angle"]))
        if abs(reached - wanted) > ANGLE_MOST:
            faults.append(f"{entry['name']}: swings {reached:.1f} degrees, its record {wanted:.1f}")
    return faults, tilt


def shift_faults(entry, poses, rest):
    """A shift's faults: turning as it shifts, or shifting off one line."""
    turned = max(angle_of(turned_from(rest, pose)) for pose in poses)
    faults = [f"{entry['name']}: turns {turned:.1f} degrees as it shifts"] if turned > TILT_MOST else []
    moves = np.array([pose[3, :3] - rest[3, :3] for pose in poses])
    lengths = np.linalg.norm(moves, axis=1)
    if lengths.max() > STILL_MOST:
        line = moves[lengths.argmax()] / lengths.max()
        far = moves[lengths > 0.01]
        if len(far):
            off = np.degrees(np.arccos(np.clip(np.abs(far @ line) / np.linalg.norm(far, axis=1), -1.0, 1.0))).max()
            if off > LINE_MOST:
                faults.append(f"{entry['name']}: leaves its line by {off:.1f} degrees as it shifts")
    return faults, turned


def round_of(entry, seconds):
    """The seconds of the move's first round: (start, end) within the layer."""
    start = float(entry.get("start", 0.0))
    length = float(entry.get("length", seconds - start))
    return start, min(seconds, start + length)


def follows_one(stage, entry, rate, seconds):
    """(faults, measure) of one move against its record."""
    prim = stage.GetPrimAtPath(entry["prim"])
    kind = motion_layer.kind_of(entry)
    rest = np.asarray(UsdGeom.Xformable(prim).GetLocalTransformation(Usd.TimeCode.Default()))
    if kind == "path":
        poses = [local_at(prim, code) for code in frame_codes(*round_of(entry, seconds), rate)]
        curve, along = motion_layer.curve_of(entry["path"], rest[3, [0, 2]])
        return path_faults(entry, np.array([pose[3, [0, 2]] for pose in poses]), curve, along)
    poses = [local_at(prim, code) for code in frame_codes(0.0, seconds, rate)]
    if kind in TURNS:
        return turn_faults(entry, kind, poses, rest)
    if kind in SHIFTS:
        return shift_faults(entry, poses, rest)
    return [f"{entry['name']}: a {kind} has no intended motion this check reads"], 0.0


def judge_follows(stage, entries, rate, seconds):
    """Pass when every move keeps to its record's intended motion."""
    faults, measures = [], {}
    for entry in entries:
        found, measure = follows_one(stage, entry, rate, seconds)
        faults += found
        measures[f"{entry['name']} off"] = round(measure, 3)
    if not entries:
        return checks.Verdict("follows", checks.PASS, "nothing moves in the place")
    reason = (f"{len(faults)} faults over {len(entries)} moves" if faults else
              f"{len(entries)} moves keep to their records' paths, turns and lines")
    return checks.Verdict("follows", checks.FAIL if faults else checks.PASS, reason, measures,
                          {name: "lower" for name in measures}, tuple(faults))


# --- steps --------------------------------------------------------------------------------------------------------

def frame_steps(shape, codes):
    """The farthest a corner of the shape's box moves from each frame to the next, metres."""
    spots = np.array([shape.in_world(shape.corners, code) for code in codes])
    return np.linalg.norm(np.diff(spots, axis=0), axis=2).max(axis=1)


def jumps(steps):
    """The frames whose step is a jump: over JUMP_LEAST and JUMP_RATIO times the 90th percentile moving step."""
    moving = steps[steps > STILL_MOST]
    if not len(moving):
        return np.array([], dtype=int)
    most = max(JUMP_LEAST, JUMP_RATIO * float(np.percentile(moving, 90)))
    return np.flatnonzero(steps > most)


def judge_steps(entries, shapes, rate, seconds):
    """Pass when no move jumps from one frame to the next."""
    codes = frame_codes(0.0, seconds, rate)
    faults, measures = [], {}
    for entry in entries:
        steps = frame_steps(shapes[entry["prim"]], codes)
        measures[f"{entry['name']} largest step"] = round(float(steps.max()) if len(steps) else 0.0, 3)
        for frame in jumps(steps)[:3]:
            faults.append(f"{entry['name']}: jumps {steps[frame]:.2f} m at {codes[frame + 1] / rate:.2f} s")
    if not entries:
        return checks.Verdict("steps", checks.PASS, "nothing moves in the place")
    reason = (f"{len(faults)} jumps over {len(entries)} moves" if faults else
              f"{len(entries)} moves step smoothly frame to frame at {rate:g} a second")
    return checks.Verdict("steps", checks.FAIL if faults else checks.PASS, reason, measures, {}, tuple(faults))


# --- moving area --------------------------------------------------------------------------------------------------

def varying_prims(stage, place, scopes):
    """Every prim of the place's own scopes whose transform varies in time."""
    found = []
    for scope in scopes:
        holder = stage.GetPrimAtPath(f"/{place}/{scope}")
        for prim in Usd.PrimRange(holder) if holder else ():
            if prim.IsA(UsdGeom.Xformable) and UsdGeom.Xformable(prim).TransformMightBeTimeVarying():
                found.append(str(prim.GetPath()))
    return found


def under_any(path, roots):
    return any(path == root or path.startswith(root + "/") for root in roots)


def judge_moving_area(stage, place, entries, shapes, rate, seconds, scopes):
    """Pass when what moves is exactly what the records move."""
    named = sorted({entry["prim"] for entry in entries})
    stray = [path for path in varying_prims(stage, place, scopes) if not under_any(path, named)]
    codes = frame_codes(0.0, seconds, rate)
    still = [path for path in named if frame_steps(shapes[path], codes).sum() <= STILL_MOST]
    faults = [f"{path}: moves, yet no record moves it" for path in stray]
    faults += [f"{path}: its record moves it, yet it stands still in the stage" for path in still]
    measures = {"moved prims": len(named), "stray": len(stray), "still": len(still)}
    reason = (f"{len(stray)} prims move that no record moves, {len(still)} named ones stand still" if faults else
              f"what moves is what the records move ({len(named)} prims)")
    return checks.Verdict("moving area", checks.FAIL if faults else checks.PASS, reason, measures,
                          {"stray": "lower", "still": "lower"}, tuple(faults))
