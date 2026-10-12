"""Kimodo's clips fitted to a prop-route person's own bulk (#5, captain 2026-10-12: the hands went into the torso in
waiting, pointing and shouting because the clips were written for SOMA-X's mean body, slimmer than a Pixal3D person
in clothes). For every frame of a clip, each limb's far end (forearm and hand, shin and foot) is tested against the
body it must not enter (the torso for an arm, the other leg for a leg), skinned as the engine skins it; where it
goes in deeper than DEPTH_MOST, the limb is swung outward about its root joint (shoulder, hip), towards the side it
hangs on, by the least angle that clears it. The angles are spread over the frames around (the most within SPREAD
frames, then averaged), so the limb eases out and back instead of jumping.

    cleared, notes = clearance.cleared(world, fit_rig, names, parents)   # world: (frames, joints, 4, 4)
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
LIMBS = {
    "LeftArm": {"ends": ("LeftForeArm", "LeftHand"), "body": ("Hips", "Spine1", "Spine2", "Chest")},
    "RightArm": {"ends": ("RightForeArm", "RightHand"), "body": ("Hips", "Spine1", "Spine2", "Chest")},
    "LeftLeg": {"ends": ("LeftShin", "LeftFoot", "LeftToeBase", "LeftToeEnd"),
                "body": ("RightLeg", "RightShin", "RightFoot", "RightToeBase", "RightToeEnd")},
    "RightLeg": {"ends": ("RightShin", "RightFoot", "RightToeBase", "RightToeEnd"),
                 "body": ("LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase", "LeftToeEnd")},
}


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


def outward_axis(frame, root, end, names):
    """The axis that swings the limb's far end away from the body's middle line (hips to chest)."""
    hips, chest = frame[names.index("Hips"), :3, 3], frame[names.index("Chest"), :3, 3]
    pivot, far = frame[root, :3, 3], frame[end, :3, 3]
    line = (chest - hips) / max(np.linalg.norm(chest - hips), 1e-9)
    side = pivot - (hips + line * np.dot(pivot - hips, line))
    axis = np.cross(far - pivot, side)
    size = np.linalg.norm(axis)
    return (axis / size if size > 1e-9 else None), pivot


def limb_angles(world, fit_rig, names, parents, root_name, limb):
    """The least outward angle (radians) per frame that keeps the limb's far end out of its body part."""
    weights, points = fit_rig["weights"], fit_rig["points"]
    inverse = np.linalg.inv(fit_rig["bind"])
    point_normals = normals(points, fit_rig["faces"])
    ends = [names.index(name) for name in limb["ends"]]
    body = [names.index(name) for name in limb["body"]]
    moving = weights[:, ends].sum(axis=1) >= SHARE
    still = weights[:, body].sum(axis=1) >= SHARE
    root = names.index(root_name)
    chain = below(root, parents)
    angles = np.zeros(len(world))
    for number, frame in enumerate(world):
        skin = frame @ inverse
        body_points = skinned(points[still], weights[still], skin)
        body_normals = turned(point_normals[still], weights[still], skin)
        if depth(skinned(points[moving], weights[moving], skin), body_points, body_normals) <= DEPTH_MOST:
            continue
        axis, pivot = outward_axis(frame, root, ends[-1], names)
        if axis is None:
            continue
        angle = 0.0
        while angle < np.radians(MOST_DEGREES):
            angle += np.radians(STEP_DEGREES)
            skin = swing(frame, chain, pivot, axis, angle) @ inverse
            if depth(skinned(points[moving], weights[moving], skin), body_points, body_normals) <= DEPTH_MOST:
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
    """The clip's world transforms with each limb swung clear of its body part; notes per limb (frames moved, the
    largest angle in degrees)."""
    world = world.copy()
    notes = {}
    for root_name, limb in LIMBS.items():
        angles = spread(limb_angles(world, fit_rig, names, parents, root_name, limb))
        root = names.index(root_name)
        chain = below(root, parents)
        ends = [names.index(name) for name in limb["ends"]]
        for number in np.nonzero(angles)[0]:
            axis, pivot = outward_axis(world[number], root, ends[-1], names)
            if axis is not None:
                world[number] = swing(world[number], chain, pivot, axis, angles[number])
        notes[root_name] = {"frames": int((angles > 0).sum()), "most_degrees": round(float(np.degrees(angles.max())), 1)}
    return world, notes
