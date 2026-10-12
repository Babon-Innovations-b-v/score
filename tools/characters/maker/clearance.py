"""Kimodo's clips fitted to a prop-route person's own bulk (#5, captain 2026-10-12: the hands went into the torso in
waiting, pointing and shouting because the clips were written for SOMA-X's mean body, slimmer than a Pixal3D person
in clothes). For every frame of a clip, each pass's limb end (forearm and hand, shin and foot) is tested against the
body it must not enter, skinned as the engine skins it; where it goes in deeper than DEPTH_MOST, the limb is swung
about its root joint (shoulder, hip) by the least angle that clears it: outward, away from the body's middle line,
or, for an arm folded over the other, forward, so it lies in front. The angles are spread over the frames around
(the most within SPREAD frames, then averaged), so the limb eases out and back instead of jumping.

    cleared, notes = clearance.cleared(world, fit_rig, names, parents)   # world: (frames, joints, 4, 4)

Measured on the player's clips (2026-10-12, before the passes against the legs and the other arm): his hands went
into his torso in waiting, the right arm swung out 16.5 degrees there; after it, hands still went 5 to 34 mm into
the thigh beside them (standing, walking, pointing) and 40 to 53 mm into the other arm folded over them (waiting).
"""
import numpy as np
from scipy.spatial import cKDTree

DEPTH_MOST = 0.001
# How near a moving point must lie to the body's surface for its nearest point's normal to say inside or out.
NEAR = 0.06
STEP_DEGREES = 1.5
MOST_DEGREES = 45.0
SPREAD = 4
SHARE = 0.5
TORSO = ("Hips", "Spine1", "Spine2", "Chest")
LEGS = ("LeftLeg", "LeftShin", "RightLeg", "RightShin")
LEFT_LEG = ("LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase", "LeftToeEnd")
RIGHT_LEG = ("RightLeg", "RightShin", "RightFoot", "RightToeBase", "RightToeEnd")
# (root joint, its far end's joints, the body it must stay out of, the way it swings), in the order they run.
PASSES = (
    ("LeftArm", ("LeftForeArm", "LeftHand"), TORSO + LEGS, "out"),
    ("RightArm", ("RightForeArm", "RightHand"), TORSO + LEGS, "out"),
    ("LeftArm", ("LeftForeArm", "LeftHand"), ("RightArm", "RightForeArm", "RightHand"), "forward"),
    ("RightArm", ("RightForeArm", "RightHand"), ("LeftArm", "LeftForeArm", "LeftHand"), "out"),
    ("LeftLeg", LEFT_LEG[1:], RIGHT_LEG, "out"),
    ("RightLeg", RIGHT_LEG[1:], LEFT_LEG, "out"),
)


def below(joint, parents):
    """The joint and every joint under it."""
    found = [joint]
    for child, parent in enumerate(parents):
        if parent in found and child not in found:
            found.append(child)
    return found


def normals(points, faces):
    """Area-weighted vertex normals."""
    corners = points[faces]
    face_normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    found = np.zeros_like(points)
    for corner in range(3):
        np.add.at(found, faces[:, corner], face_normals)
    return found / np.maximum(np.linalg.norm(found, axis=1, keepdims=True), 1e-12)


def skinned(points, weights, skin):
    """Points posed by linear blend skinning with per-joint matrices `skin` (joints, 4, 4)."""
    blended = np.einsum("pj,jab->pab", weights, skin)
    return np.einsum("pab,pb->pa", blended[:, :3, :3], points) + blended[:, :3, 3]


def turned(normal_points, weights, skin):
    blended = np.einsum("pj,jab->pab", weights, skin[:, :3, :3])
    found = np.einsum("pab,pb->pa", blended, normal_points)
    return found / np.maximum(np.linalg.norm(found, axis=1, keepdims=True), 1e-12)


def depth(moving, body_points, body_normals):
    """The deepest a moving point lies inside the body's surface (0 when none does), read by its nearest body
    point's normal within NEAR."""
    distance, nearest = cKDTree(body_points).query(moving, distance_upper_bound=NEAR)
    found = distance < np.inf
    if not found.any():
        return 0.0
    inside = -np.einsum("ij,ij->i", moving[found] - body_points[nearest[found]], body_normals[nearest[found]])
    return float(max(0.0, inside.max()))


def swing(frame, chain, pivot, axis, angle):
    """The frame's world transforms with the chain's joints turned by `angle` (radians) about `axis` at `pivot`."""
    from scipy.spatial.transform import Rotation
    turn = np.eye(4)
    turn[:3, :3] = Rotation.from_rotvec(axis * angle).as_matrix()
    turn[:3, 3] = pivot - turn[:3, :3] @ pivot
    moved = frame.copy()
    moved[chain] = turn @ frame[chain]
    return moved


def swing_axis(frame, root, end, names, way):
    """The axis that swings the limb's far end towards `way`: "out", away from the body's middle line (hips to
    chest), or "forward", the way the chest faces (left shoulder to right, crossed with up); the pivot."""
    at = {name: frame[names.index(name), :3, 3] for name in ("Hips", "Chest", "LeftArm", "RightArm")}
    pivot, far = frame[root, :3, 3], frame[end, :3, 3]
    up = (at["Chest"] - at["Hips"]) / max(np.linalg.norm(at["Chest"] - at["Hips"]), 1e-9)
    if way == "out":
        towards = pivot - (at["Hips"] + up * np.dot(pivot - at["Hips"], up))
    else:
        towards = np.cross(at["LeftArm"] - at["RightArm"], up)
    axis = np.cross(far - pivot, towards)
    size = np.linalg.norm(axis)
    return (axis / size if size > 1e-9 else None), pivot


def pass_angles(world, fit_rig, names, parents, step):
    """The least angle (radians) per frame that keeps a pass's limb end out of its body."""
    root_name, ends_names, body_names, way = step
    weights, points = fit_rig["weights"], fit_rig["points"]
    inverse = np.linalg.inv(fit_rig["bind"])
    point_normals = normals(points, fit_rig["faces"])
    ends = [names.index(name) for name in ends_names]
    moving = weights[:, ends].sum(axis=1) >= SHARE
    # Each body joint's own points (those it weighs most): read one joint at a time, a point's nearest neighbour is
    # on the same surface, where a mixed set read a hand inside a folded arm as outside the other hand next to it.
    owner = weights.argmax(axis=1)
    groups = [owner == names.index(name) for name in body_names]
    root = names.index(root_name)
    chain = below(root, parents)
    angles = np.zeros(len(world))

    def deepest(skin, bodies):
        moved = skinned(points[moving], weights[moving], skin)
        return max(depth(moved, body_points, body_normals) for body_points, body_normals in bodies)

    for number, frame in enumerate(world):
        skin = frame @ inverse
        bodies = [(skinned(points[group], weights[group], skin), turned(point_normals[group], weights[group], skin))
                  for group in groups if group.any()]
        if deepest(skin, bodies) <= DEPTH_MOST:
            continue
        axis, pivot = swing_axis(frame, root, ends[-1], names, way)
        if axis is None:
            continue
        angle = 0.0
        while angle < np.radians(MOST_DEGREES):
            angle += np.radians(STEP_DEGREES)
            if deepest(swing(frame, chain, pivot, axis, angle) @ inverse, bodies) <= DEPTH_MOST:
                break
        angles[number] = angle
    return angles


def spread(angles):
    """Each frame's angle the most within SPREAD frames around it, then averaged over the same window: eased."""
    padded = np.pad(angles, SPREAD, mode="edge")
    most = np.array([padded[at:at + 2 * SPREAD + 1].max() for at in range(len(angles))])
    padded = np.pad(most, SPREAD, mode="edge")
    eased = np.array([padded[at:at + 2 * SPREAD + 1].mean() for at in range(len(angles))])
    return np.maximum(eased, angles)


def cleared(world, fit_rig, names, parents):
    """The clip's world transforms with each pass's limb swung clear of its body; notes per pass (frames moved, the
    largest angle in degrees)."""
    world = world.copy()
    notes = {}
    for step in PASSES:
        root_name, ends_names, _, way = step
        angles = spread(pass_angles(world, fit_rig, names, parents, step))
        root = names.index(root_name)
        chain = below(root, parents)
        for number in np.nonzero(angles)[0]:
            axis, pivot = swing_axis(world[number], root, names.index(ends_names[-1]), names, way)
            if axis is not None:
                world[number] = swing(world[number], chain, pivot, axis, angles[number])
        notes[f"{root_name} {way} of {step[2][0]}"] = {"frames": int((angles > 0).sum()),
                                       "most_degrees": round(float(np.degrees(angles.max())), 1)}
    return world, notes
