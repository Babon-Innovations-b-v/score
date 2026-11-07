"""The floor each LabValidation camera sees (MoGe-2's point map, on_moge.py) and GEM-X's body levelled onto it.

GEM-X's world has no floor of its own: its up is the network's per-frame gravity estimate (gem/motion/codec/world.py,
the gravity view: R_c2gv = R_gv R_c^T a frame), and its camera there, R_c2w = R(global_orient) R(incam
global_orient)^T, stood a few degrees off level and moved from frame to frame on a static tripod (subject2's squats,
Cam0: its roll -12 to 0 degrees, p5 to p95). The lab's floor is level, so the floor the camera sees is the up.
`seen` fits it in the camera's frame; `levelled` turns GEM-X's whole clip, one rigid turn, by the least turn that puts
the floor's normal, as GEM-X's camera holds it over the clip, on the world's up. GEM-X's camera-frame body itself is
not taken (its depth jitters 20 to 30 mm a frame against its world path's 1 mm), nor is each frame turned on its own
(the frames' turns spread up to 5 degrees, p95, and a frame's turn about its Hips would move a standing foot 17 mm a
degree). Nothing of the body's own pose changes: its shape and every joint against its parent stay GEM-X's SOMA."""
import numpy as np
from scipy.spatial.transform import Rotation

UP_LIKE = np.cos(np.radians(35.0))  # a point map normal within 35 deg of the camera's own down-to-up axis is floor-like
INLIER = 0.02  # m: a point within this of the plane is on it (RANSAC and its refit)
TRIES = 400  # RANSAC draws, seeded: the same video gives the same floor
PERSON_MARGIN = 0.15  # the person's box (GEM-X's joints projected) grown by this share of its size, left out


def camera_to_world(gemx):
    """GEM-X's camera in its world a frame (frames x 3 x 3): R(global_orient) R(incam global_orient)^T."""
    world = Rotation.from_rotvec(np.asarray(gemx["global_orient"], dtype=float)).as_matrix()
    camera = Rotation.from_rotvec(np.asarray(gemx["incam_global_orient"], dtype=float)).as_matrix()
    return world @ np.swapaxes(camera, 1, 2)


def person_boxes(gemx):
    """GEM-X's body in its image a frame: (u0, v0, u1, v1) pixels of its joints projected through its K, grown by
    PERSON_MARGIN (frames x 4). The camera frame's joints are the world ones turned by R_c2w^T about the Hips, the Hips
    at its rest offset plus the camera-frame translation."""
    names = [str(name) for name in gemx["joint_names"]]
    hips = names.index("Hips")
    world_hips = np.asarray(gemx["world_transforms"], dtype=float)[:, hips, :3, 3]
    camera_hips = world_hips - np.asarray(gemx["root_translation"]) + np.asarray(gemx["incam_transl"])
    turn = np.swapaxes(camera_to_world(gemx), 1, 2)
    joints = np.einsum("fab,fjb->fja", turn, np.asarray(gemx["joints"], dtype=float) - world_hips[:, None]) + camera_hips[:, None]
    seen = np.einsum("fab,fjb->fja", np.asarray(gemx["K"], dtype=float), joints)
    pixels = seen[..., :2] / seen[..., 2:]
    low, high = pixels.min(axis=1), pixels.max(axis=1)
    grow = PERSON_MARGIN * (high - low)
    return np.c_[low - grow, high + grow]


def gemx_frame(gemx, video_frame):
    """The GEM-X frame nearest a source video frame."""
    return int(np.abs(np.asarray(gemx["source_frame"]) - video_frame).argmin())


def floor_points(moge, gemx):
    """The floor-like points of every MoGe frame (n x 3, m, camera frame): valid, outside the person's box at the
    nearest GEM-X frame, their normal within UP_LIKE of the camera's -y."""
    boxes, stride = person_boxes(gemx), int(moge["stride"])
    found = []
    for index, video_frame in enumerate(np.asarray(moge["frames"])):
        points, normals, valid = moge["points"][index], moge["normal"][index], moge["mask"][index]
        rows, cols = np.indices(valid.shape)
        u0, v0, u1, v1 = boxes[gemx_frame(gemx, video_frame)]
        outside = ~((cols * stride >= u0) & (cols * stride <= u1) & (rows * stride >= v0) & (rows * stride <= v1))
        up_like = -normals[..., 1] > UP_LIKE
        found.append(points[valid & outside & up_like & np.isfinite(points).all(axis=-1)])
    return np.concatenate(found).astype(float)


def plane_of(points):
    """(unit normal, offset) of the least squares plane through `points` (n . x = offset)."""
    centre = points.mean(axis=0)
    normal = np.linalg.svd(points - centre, full_matrices=False)[2][-1]
    return normal, float(normal @ centre)


def seen(moge, gemx):
    """The floor in GEM-X's camera frame: {normal (unit, pointing up: its y below 0 in OpenCV's axes), offset (m),
    inliers, rms mm, tilt deg (its angle to GEM-X's up a frame: median, p5, p95)}, by RANSAC over the floor-like
    points (seeded) and a least squares refit on the inliers; None when fewer than 200 floor-like points are left."""
    points = floor_points(moge, gemx)
    if len(points) < 200:
        return None
    draws = np.random.default_rng(0).integers(0, len(points), size=(TRIES, 3))
    best = None
    for draw in draws:
        normal = np.cross(points[draw[1]] - points[draw[0]], points[draw[2]] - points[draw[0]])
        if np.linalg.norm(normal) < 1e-9:
            continue
        normal /= np.linalg.norm(normal)
        count = int((np.abs((points - points[draw[0]]) @ normal) < INLIER).sum())
        if best is None or count > best[0]:
            best = (count, normal, float(normal @ points[draw[0]]))
    _, normal, offset = best
    inliers = points[np.abs(points @ normal - offset) < INLIER]
    normal, offset = plane_of(inliers)
    if normal[1] > 0:
        normal, offset = -normal, -offset
    gemx_up = np.swapaxes(camera_to_world(gemx), 1, 2)[:, :, 1]
    tilt = np.degrees(np.arccos(np.clip(gemx_up @ normal, -1.0, 1.0)))
    return {"normal": normal.tolist(), "offset": offset, "inliers": len(inliers), "points": len(points),
            "rms mm": float(np.sqrt(np.mean((inliers @ normal - offset) ** 2)) * 1000),
            "tilt deg": [float(np.median(tilt)), float(np.percentile(tilt, 5)), float(np.percentile(tilt, 95))]}


def least_turn(vector, onto):
    """The least turn (3 x 3) taking the unit vector `vector` onto the unit vector `onto`."""
    axis = np.cross(vector, onto)
    angle = np.arctan2(np.linalg.norm(axis), vector @ onto)
    if np.linalg.norm(axis) < 1e-12:
        return np.eye(3)
    return Rotation.from_rotvec(axis / np.linalg.norm(axis) * angle).as_matrix()


def levelled(world, gemx, normal):
    """GEM-X's world transforms (frames x joints x 4 x 4) turned as a whole, about the world's origin, by the least
    turn that puts the seen floor's normal (`normal`, GEM-X's camera frame) on +y as GEM-X's camera holds it over the
    clip (R_c2w(t) n, averaged over the frames); and that turn's angle and the spread of the frames' own (deg: the
    largest frame's angle from the mean). One rigid turn: every joint against every other, on every frame, is GEM-X's."""
    world = np.asarray(world, dtype=float)
    seen = np.einsum("fab,b->fa", camera_to_world(gemx), np.asarray(normal, dtype=float))
    if len(seen) != len(world):
        raise ValueError(f"GEM-X's result has {len(seen)} frames, its SOMA body {len(world)}")
    mean = seen.mean(axis=0) / np.linalg.norm(seen.mean(axis=0))
    turn = least_turn(mean, np.array([0.0, 1.0, 0.0]))
    moved = world.copy()
    moved[..., :3, :] = np.einsum("ab,fjbc->fjac", turn, world[..., :3, :])
    spread = np.degrees(np.arccos(np.clip(seen @ mean, -1.0, 1.0)))
    return moved, float(np.degrees(np.arccos(np.clip(mean[1], -1.0, 1.0)))), float(spread.max())
