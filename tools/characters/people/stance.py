"""A clip's feet brought in to a relaxed stance, by turning the legs at the hip and the knee: numpy only.

Kimodo stands people with their feet far apart: across the clips' standing poses the ankles are 1.6 to 2.2 times as
far apart as the hip joints (the standing clip 2.14, waiting 1.82, the bench 1.90; measured on the clips' own joints,
2026-10-09), where a person standing as they choose has them about as far apart as the hips or a little less
(`joins.py` cites the study). Asking in the sentence for "feet close together" moved some draws to 1.1 and left others
at 1.8, so the sentence cannot hold it (owner, 2026-10-09: "why do they stand so wide").

So each clip's feet are brought in here, the same way all through the clip: for each foot the median of its spacing
from the middle of the hips, across the hips, over the clip, and where that is wider than half of WIDEST times the
hips' spacing, one fixed move in towards the middle along the hips' median line, the same in every frame. A planted foot stays planted
(its move does not change during the clip) and a walk, whose feet pass close under the hips, is not moved at all.
Each leg reaches its moved ankle by turning at the hip and bending at the knee in the plane it already bends in (two
bones, solved exactly); the foot keeps its own turn, so it stays flat on the floor where it was.
"""
import numpy as np

# The widest a clip's ankles may stand across the hips, over the hip joints' spacing.
WIDEST = 1.0
LEG = ("Leg", "Shin", "Foot")


def turn_between(first, second):
    """The rotation matrix that turns direction `first` onto direction `second` by the shortest way."""
    first, second = first / np.linalg.norm(first), second / np.linalg.norm(second)
    axis = np.cross(first, second)
    sine, cosine = np.linalg.norm(axis), float(first @ second)
    if sine < 1e-12:
        return np.eye(3)
    axis /= sine
    cross = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + sine * cross + (1 - cosine) * cross @ cross


def below(joint, parents):
    """The joint and every joint under it."""
    found = [joint]
    for child in range(len(parents)):
        if parents[child] == joint:
            found += below(child, parents)
    return found


def hips_line(world, names):
    """Each frame's middle of the hip joints, the unit line from the right hip to the left on the floor, and the
    spacing of the hips."""
    left, right = world[:, names.index("LeftLeg"), :3, 3], world[:, names.index("RightLeg"), :3, 3]
    across = left - right
    across[:, 1] = 0.0
    spacing = np.linalg.norm(across, axis=1)
    return (left + right) / 2, across / spacing[:, None], spacing


def moves_in(world, names):
    """For each side, the distance its ankle is moved in towards the middle, the same in every frame: {side: metres}."""
    middle, across, spacing = hips_line(world, names)
    allowed = WIDEST * float(np.median(spacing)) / 2
    found = {}
    for side, sign in (("Left", 1.0), ("Right", -1.0)):
        ankle = world[:, names.index(side + "Foot"), :3, 3]
        out = float(np.median(np.einsum("fd,fd->f", ankle - middle, across))) * sign
        found[side] = max(0.0, out - allowed)
    return found


def knee_for(hip, knee, ankle, target):
    """Where the knee goes for the ankle to reach `target` with the thigh and shin keeping their lengths, bending in
    the plane the leg bends in now."""
    thigh, shin = np.linalg.norm(knee - hip), np.linalg.norm(ankle - knee)
    reach = target - hip
    distance = float(np.clip(np.linalg.norm(reach), abs(thigh - shin) + 1e-6, thigh + shin - 1e-6))
    along = reach / np.linalg.norm(reach)
    bend = (knee - hip) - ((knee - hip) @ along) * along
    if np.linalg.norm(bend) < 1e-9:
        bend = np.cross(along, [1.0, 0.0, 0.0])
    bend /= np.linalg.norm(bend)
    first = (thigh * thigh + distance * distance - shin * shin) / (2 * distance)
    height = np.sqrt(max(thigh * thigh - first * first, 0.0))
    return hip + along * first + bend * height


def narrowed(world, names, parents):
    """The clip's world joint transforms (frames, joints, 4, 4) with the feet brought in (the module's header says
    how); a clip already within WIDEST comes back as it is."""
    moves = moves_in(world, names)
    if not any(moves.values()):
        return world
    world = world.copy()
    # One line for the whole clip, so a planted foot is moved the same way in every frame and does not slide as the
    # hips turn.
    _, across, _ = hips_line(world, names)
    across = np.median(across, axis=0)
    across /= np.linalg.norm(across)
    for side, sign in (("Left", 1.0), ("Right", -1.0)):
        if not moves[side]:
            continue
        hip_joint, knee_joint, foot_joint = (names.index(side + bone) for bone in LEG)
        foot_and_toes = below(foot_joint, parents)
        shin_only = [joint for joint in below(knee_joint, parents) if joint not in foot_and_toes]
        thigh_only = [joint for joint in below(hip_joint, parents) if joint not in shin_only + foot_and_toes]
        for frame in range(len(world)):
            hip, knee, ankle = (world[frame, joint, :3, 3] for joint in (hip_joint, knee_joint, foot_joint))
            shift = -sign * moves[side] * across
            target = ankle + shift
            new_knee = knee_for(hip, knee, ankle, target)
            thigh_turn = turn_between(knee - hip, new_knee - hip)
            shin_turn = turn_between(thigh_turn @ (ankle - knee), target - new_knee) @ thigh_turn
            for joint in thigh_only:
                world[frame, joint, :3, :3] = thigh_turn @ world[frame, joint, :3, :3]
                world[frame, joint, :3, 3] = hip + thigh_turn @ (world[frame, joint, :3, 3] - hip)
            for joint in shin_only:
                world[frame, joint, :3, :3] = shin_turn @ world[frame, joint, :3, :3]
                world[frame, joint, :3, 3] = new_knee + shin_turn @ (world[frame, joint, :3, 3] - knee)
            for joint in foot_and_toes:
                world[frame, joint, :3, 3] = world[frame, joint, :3, 3] + shift
    return world
