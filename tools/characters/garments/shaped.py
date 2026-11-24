"""A built person given another build (#223, several people): SOMA's own shape space laid on its bones, so the people
line's bodies are not all SOMA's mean (every built look's surface is SOMA's mean on its fitted bones: 175.7 cm, waist
73 cm, 2026-11-24).

SOMA's neutral shape model (`SOMA_neutral.npz`, nvidia/soma-x, Apache-2.0: its mean, 128 principal shape directions
and their variances, learned from SizeUSA and Triplegangers scans) gives the body's change at rest for the outfit's
`body.shape` ({direction: standard deviations}); the change is carried onto the built body at its bind through each
joint's own turn and scale from SOMA's rest to the bind (a similarity fitted on the points that joint carries most,
blended by the skin weights), each joint moved as the skin round it moves (an affine fitted on the points it and its
parent carry), the joints' offsets read again from the moved bind, and the whole person scaled to `body.height_m`
about its feet. The clips then play on the new bones as on any build (`score.stages.sim_body._body.person_rig`: its
offsets, its Hips' height). The drawn body (`points`, `weights`) is dropped: it is the made look's mesh, not this
build's.
"""
import os
import pathlib

import numpy as np

SOMA_NEUTRAL = pathlib.Path(os.environ.get("SOMA_NEUTRAL",
                                           pathlib.Path.home() / ".cache/gemx-check/soma/SOMA_neutral.npz"))
CENTIMETRES = 0.01
CARRIED = 0.6  # a point counts for a joint's turn when that joint carries more of it than this
AROUND = 0.3  # a point counts for a joint's place when the joint and its parent carry more of it than this


def model(path=SOMA_NEUTRAL):
    """SOMA's shape model at its low level of detail (the built bodies' surface): mean (m), directions (m a standard
    deviation), points x 3 and directions x points x 3."""
    found = np.load(path)
    low = np.asarray(found["lod_mid_to_low"])
    directions = np.asarray(found["shapedirs"], dtype=float).reshape(len(found["eigenvalues"]), -1, 3)
    spread = np.sqrt(np.asarray(found["eigenvalues"], dtype=float))
    return {"mean": np.asarray(found["mean"], dtype=float)[low] * CENTIMETRES,
            "directions": directions[:, low] * spread[:, None, None] * CENTIMETRES,
            "faces": np.asarray(found["triangles_low"], dtype=np.int64)}


def rest_change(shapes, shape):
    """The body's change at SOMA's rest for `shape` ({direction number: standard deviations}), points x 3 (m)."""
    found = np.zeros_like(shapes["mean"])
    for direction, amount in shape.items():
        found += float(amount) * shapes["directions"][int(direction)]
    return found


def similarity(source, target):
    """The scaled turn and move taking `source` onto `target` best (Umeyama): (scale x turn 3 x 3, move)."""
    source_middle, target_middle = source.mean(axis=0), target.mean(axis=0)
    one, other = source - source_middle, target - target_middle
    left, values, right = np.linalg.svd(one.T @ other)
    sign = np.diag([1.0, 1.0, np.sign(np.linalg.det(left @ right))])
    turn = (left @ sign @ right).T
    scale = float((values * np.diag(sign)).sum() / (one ** 2).sum())
    return scale * turn, target_middle - scale * turn @ source_middle


def joint_turns(rest, bind_points, weights, parents):
    """Each joint's scaled turn from SOMA's rest to the bind, fitted on the points it carries most; a joint carrying
    too few takes its parent's: joints x 3 x 3."""
    turns = np.tile(np.eye(3), (weights.shape[1], 1, 1))
    for joint in range(weights.shape[1]):
        mine = weights[:, joint] > CARRIED
        if mine.sum() >= 6:
            turns[joint] = similarity(rest[mine], bind_points[mine])[0]
        elif parents[joint] >= 0:
            turns[joint] = turns[parents[joint]]
    return turns


def affine(source, target):
    """The affine map taking `source` onto `target` in least squares: 4 x 3 (rows x, y, z, 1)."""
    padded = np.concatenate([source, np.ones((len(source), 1))], axis=1)
    return np.linalg.lstsq(padded, target, rcond=None)[0]


def joints_moved(bind, points, moved, weights, parents):
    """The bind with each joint's place carried as the skin round it moved (an affine on the points the joint and
    its parent carry more than AROUND of; with too few, the mean move of the points it carries most)."""
    found = np.array(bind, dtype=float)
    for joint, parent in enumerate(parents):
        carried = weights[:, joint] + (weights[:, parent] if parent >= 0 else 0.0)
        around = carried > AROUND
        place = bind[joint, :3, 3]
        if around.sum() >= 12:
            found[joint, :3, 3] = np.append(place, 1.0) @ affine(points[around], moved[around])
        else:
            heaviest = weights[:, joint] >= np.sort(weights[:, joint])[-6]
            found[joint, :3, 3] = place + (moved[heaviest] - points[heaviest]).mean(axis=0)
    return found


def offsets_of(bind, parents):
    """Each joint's place against its parent at the bind (the root's: its place), as the built rig keeps them."""
    return np.array([bind[joint] if parent < 0 else np.linalg.inv(bind[parent]) @ bind[joint]
                     for joint, parent in enumerate(parents)])[:, :3, 3]


def scaled(bind, points, height_m, centre):
    """The bind and points scaled about `centre` on the floor so the points stand `height_m` tall."""
    factor = height_m / float(points[:, 1].max() - points[:, 1].min())
    anchor = np.array([centre[0], 0.0, centre[2]])
    found = np.array(bind, dtype=float)
    found[:, :3, 3] = anchor + (bind[:, :3, 3] - anchor) * factor
    return found, anchor + (points - anchor) * factor


def built(build, weights, parents, body, shapes=None):
    """The build (a look's fit rig.npz, as a dict) given `body` ({"shape": {direction: sd}, "height_m": m}): its
    bind, offsets and surface (`source_points`) moved, the drawn body dropped."""
    shapes = shapes or model()
    points = np.asarray(build["source_points"], dtype=float)
    if len(points) != len(shapes["mean"]):
        raise ValueError(f"the build's surface has {len(points)} points, SOMA's low level {len(shapes['mean'])}")
    weights, parents = np.asarray(weights, dtype=float), np.asarray(parents)
    turns = joint_turns(shapes["mean"], points, weights, parents)
    change = rest_change(shapes, body.get("shape", {}))
    moved = points + np.einsum("pj,jab,pb->pa", weights, turns, change)
    bind = joints_moved(np.asarray(build["bind"], dtype=float), points, moved, weights, parents)
    if body.get("height_m"):
        bind, moved = scaled(bind, moved, float(body["height_m"]), bind[1, :3, 3])
    found = {key: value for key, value in build.items() if key not in ("points", "weights")}
    return dict(found, bind=bind, offsets=offsets_of(bind, parents), source_points=moved)


SIDES = (("LeftArm", 1.0), ("RightArm", -1.0))
SUNK_M = 0.002  # an arm point this far inside the torso's skin under it is sunk in it
NEAR_M = 0.05  # torso skin farther than this from an arm point is not under it
ARM_STEP_DEGREES = 2.0
ARM_MOST_DEGREES = 20.0
LOOKED_EVERY = 5  # clip frames between those the arms are cleared on
# The armpit's fold: upper-arm skin nearer the shoulder than this share of the upper arm meets the chest's skin on
# every build (a heavy and a tall build's still sunk 2 to 9 mm at 27 to 29% of the way, turned out 10 to 20 degrees;
# none past it, 2026-11-24); no cloth lies between them, the sleeve's armhole seam runs there.
ARMPIT_SHARE = 0.35


def normals(points, faces):
    """Each point's normal: the sum of its triangles' area-weighted normals, unit length."""
    corners = points[faces]
    sides = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    found = np.zeros_like(points)
    for corner in range(3):
        np.add.at(found, faces[:, corner], sides)
    return found / np.maximum(np.linalg.norm(found, axis=1, keepdims=True), 1e-12)


def sunk(points, faces, arms, torso):
    """The arm points sunk in the torso: inside its skin (along the nearest torso point's normal) past SUNK_M, that
    torso point within NEAR_M."""
    from scipy.spatial import cKDTree
    outward = normals(points, faces)
    distance, nearest = cKDTree(points[torso]).query(points[arms])
    depth = -((points[arms] - points[torso][nearest]) * outward[torso][nearest]).sum(axis=1)
    return int(((depth > SUNK_M) & (distance < NEAR_M)).sum())


def abducted(local, parents, names, angles, forward):
    """Poses (frames x joints x 4 x 4, against the parents) with each upper arm turned `angles` ({joint: degrees})
    out from the body about the chest's forward axis (`forward`, in the chest's own frame), the arm's own place
    kept."""
    from scipy.spatial.transform import Rotation
    from tools.characters import played
    found = np.array(local, dtype=float)
    worlds = played.chained(found, parents)
    chest = names.index("Chest")
    for name, side in SIDES:
        if not angles.get(name):
            continue
        joint = names.index(name)
        parent_turn = worlds[:, parents[joint], :3, :3]
        axis = np.einsum("fab,b->fa", worlds[:, chest, :3, :3], forward)
        turn = Rotation.from_rotvec(axis * np.radians(side * angles[name])).as_matrix()
        found[:, joint, :3, :3] = np.transpose(parent_turn, (0, 2, 1)) @ turn @ parent_turn @ found[:, joint, :3, :3]
    return found


def past_armpits(bind, points, arms, names):
    """The arm points past the armpit's fold: each one's share along its side's upper arm (from the Arm joint to the
    ForeArm joint, at the bind) over ARMPIT_SHARE."""
    found = np.array(arms, dtype=bool)
    middle = bind[names.index("Hips"), 0, 3]
    for side in ("Left", "Right"):
        start, end = bind[names.index(f"{side}Arm"), :3, 3], bind[names.index(f"{side}ForeArm"), :3, 3]
        mine = arms & ((points[:, 0] > middle) == ((end - start)[0] > 0.0))
        share = (points[mine] - start) @ (end - start) / float((end - start) @ (end - start))
        found[np.flatnonzero(mine)[share <= ARMPIT_SHARE]] = False
    return found


def arms_cleared(bind, points, faces, weights, names, parents, clip):
    """The bind, its skin and the clip with the upper arms carried clear of the torso: the least turn out (in
    ARM_STEP_DEGREES up to ARM_MOST_DEGREES, one for both arms) that leaves no arm point past the armpits' fold
    (`past_armpits`) sunk in the torso at the bind or on every LOOKED_EVERY'th clip frame. A wider build's arms
    posed at the mean build's angles go through its sides (a heavy build's upper arms 23 mm into its chest at the
    bind, up to 35 mm walking, 2026-11-24: the jacket's underarm cloth was caught between them and blew up). The
    mean build's arms are left as they are. (bind, points, clip, degrees)."""
    from score.stages.people_cloth import skinned
    from tools.characters import played
    names = [str(name) for name in names]
    strongest = np.asarray(weights).argmax(axis=1)
    arms = np.isin(strongest, [index for index, name in enumerate(names) if "Arm" in name or name.endswith("Hand")])
    torso = np.isin(strongest, [names.index(name) for name in ("Hips", "Spine1", "Spine2", "Chest") if name in names])
    arms = past_armpits(bind, points, arms, names)
    joints = np.tile(np.arange(weights.shape[1]), (len(weights), 1))
    forward = bind[names.index("Chest"), :3, :3].T @ np.array([0.0, 0.0, 1.0])
    bind_local = np.array([[bind[joint] if parent < 0 else np.linalg.inv(bind[parent]) @ bind[joint]
                            for joint, parent in enumerate(parents)]])
    looked = clip[::LOOKED_EVERY]
    for degrees in np.arange(0.0, ARM_MOST_DEGREES + 1e-9, ARM_STEP_DEGREES):
        angles = {name: degrees for name, _ in SIDES}
        posed = played.chained(abducted(bind_local, parents, names, angles, forward), parents)[0]
        moved = skinned(points, joints, weights, posed[None], bind)[0]
        frames = skinned(moved, joints, weights, played.chained(abducted(looked, parents, names, angles, forward),
                                                                parents), posed)
        if all(sunk(frame, faces, arms, torso) == 0 for frame in [moved, *frames]):
            return posed, moved, abducted(clip, parents, names, angles, forward), float(degrees)
    raise ValueError(f"the arms stay sunk in the torso turned out {ARM_MOST_DEGREES} degrees")
