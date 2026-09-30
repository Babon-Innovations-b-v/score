"""How each part of an outfit hangs from the skeleton: its skin weights, taken from the body.

Every part is either cloth that follows the body under it, a hard part that rides as one piece
on the cloth or on one joint, or a piece of the body itself. All of them end up with the body's
own 27 joints, so every clip plays on every outfit with no conversion of any kind.
"""
import fit
import numpy as np
import trimesh
from scipy.spatial import cKDTree

# The joints each limb of a drape may take its weights from, so a sleeve by the ribs does not
# follow the chest and two trouser legs by each other do not swap.
CHAINS = {
    "left_arm": ("LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand"),
    "right_arm": ("RightShoulder", "RightArm", "RightForeArm", "RightHand"),
    "left_leg": ("LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase"),
    "right_leg": ("RightLeg", "RightShin", "RightFoot", "RightToeBase"),
}
# How many rounds of neighbour averaging a drape's weights get, so folds do not pinch.
CLOTH_SMOOTHING = 6
# A trouser leg keeps to its own leg only below this far under the body's crotch.
UNDER_THE_CROTCH = 0.10
# The skin kept round the head: these joints, and nothing below this height (the stand collar
# covers the neck from about 1.44 m).
HEAD_JOINTS = ("Neck1", "Neck2", "Head", "HeadEnd")
NECK_CUT = float(fit.y(1.42))


class Body:
    """The body at its bind pose, in metres, facing +z with +x its left: what an outfit is built
    on. `joints` is each kept joint's place, by name."""

    def __init__(self, points, faces, weights, joint_names, joint_places):
        self.points = points
        self.faces = faces.astype(np.int64)
        self.weights = weights
        self.joint_names = list(joint_names)
        self.joints = {name: np.asarray(place, dtype=float)
                       for name, place in zip(joint_names, joint_places)}


def from_the_body(points, body, faces=None):
    """Every point's weights, blended from the nearest place on the body's surface (or on the
    body triangles in `faces`)."""
    faces = body.faces if faces is None else faces
    surface = trimesh.Trimesh(body.points, faces, process=False)
    nearest, _, triangle = trimesh.proximity.closest_point(surface, points)
    corners = faces[triangle]
    share = trimesh.triangles.points_to_barycentric(body.points[corners], nearest)
    share = np.clip(share, 0.0, None)
    share /= share.sum(axis=1, keepdims=True)
    return np.einsum("pc,pcj->pj", share, body.weights[corners])


def on_one_joint(count, joint_names, joint):
    """Every point on one joint and nothing else."""
    weights = np.zeros((count, len(joint_names)))
    weights[:, joint_names.index(joint)] = 1.0
    return weights


def averaged(weights, faces, rounds):
    """Weights averaged with their neighbours' `rounds` times, then shared out to one again."""
    edges = trimesh.Trimesh(np.zeros((len(weights), 3)), faces, process=False).edges_unique
    for _ in range(rounds):
        total = weights.copy()
        count = np.ones(len(weights))
        np.add.at(total, edges[:, 0], weights[edges[:, 1]])
        np.add.at(total, edges[:, 1], weights[edges[:, 0]])
        np.add.at(count, edges.ravel(), 1)
        weights = total / count[:, None]
    return weights / weights.sum(axis=1, keepdims=True)


def of_a_drape(points, faces, limbs, body):
    """A drape's weights: from the nearest body surface, a sleeve only from its own arm and a
    trouser leg below the crotch only from its own leg, then averaged over neighbours."""
    weights = from_the_body(points, body)
    owner = body.weights.argmax(axis=1)
    names = body.joint_names
    crotch = min(body.points[owner == names.index(side + "Leg"), 1].max()
                 for side in ("Left", "Right")) - UNDER_THE_CROTCH
    for limb, chain in CHAINS.items():
        mine = limbs == limb
        if limb.endswith("leg"):
            mine &= points[:, 1] < crotch
        if not mine.any():
            continue
        allowed = np.isin(owner, [names.index(name) for name in chain])
        weights[mine] = from_the_body(points[mine], body, body.faces[allowed[body.faces].all(axis=1)])
    return averaged(weights, faces, CLOTH_SMOOTHING)


def at_the_cloth(cloth, cloth_weights, points):
    """The cloth's weights at the nearest place on the cloth to each point."""
    closest, _, triangle = trimesh.proximity.closest_point(cloth, points)
    corners = cloth.faces[triangle]
    share = trimesh.triangles.points_to_barycentric(cloth.triangles[triangle], closest)
    share = np.clip(share, 0.0, 1.0)
    share /= share.sum(axis=1, keepdims=True)
    return np.einsum("pk,pkj->pj", share, cloth_weights[corners])


def at_the_nearest_point(points, source_points, source_weights):
    """The weights of the nearest source point to each point."""
    _, nearest = cKDTree(source_points).query(points)
    return source_weights[nearest]


def piece_of_the_body(body, kept):
    """The body's triangles where `kept` is true of all three corners: points, faces, weights."""
    faces = body.faces[kept[body.faces].all(axis=1)]
    used, renumbered = np.unique(faces, return_inverse=True)
    return body.points[used], renumbered.reshape(-1, 3), body.weights[used]


def bare_hands(body):
    """The body's own hands."""
    hands = [body.joint_names.index(f"{side}Hand") for side in ("Left", "Right")]
    return piece_of_the_body(body, np.isin(body.weights.argmax(axis=1), hands))


def head_and_neck(body):
    """The body's own head and the top of its neck, cut under the collar."""
    joints = [body.joint_names.index(name) for name in HEAD_JOINTS]
    kept = np.isin(body.weights.argmax(axis=1), joints) & (body.points[:, 1] > NECK_CUT)
    return piece_of_the_body(body, kept)
