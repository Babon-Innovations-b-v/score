"""The kit's faces on any build (#112): a face's head set on a build's neck, and everything made
for take C's head (the eyes, the hairstyles, the brows and irises) carried onto it.

Every body here is the same mesh, point for point, whatever its build: SAM 3D Body only moves
the points. So a face is simply the head points of the body SAM read off that face's picture,
and it goes onto a build by those same points: stood on the build's own Head joint, blended into
the build's neck between two heights (on the template), so below the collar the neck is always
the build's and the collar fits whichever face is worn.

Anything made on the template's head (the MakeHuman eyes, a hairstyle's shell, the brows' and
irises' places) follows a head by how the head's points near it moved: each point moves as the
nearest head points did, weighted by nearness. A hair point that ends up inside the new skull is
pushed back out over it.
"""
import numpy as np
import trimesh
from scipy.spatial import cKDTree

import fit

HEAD_JOINTS = ("Neck1", "Neck2", "Head", "HeadEnd")
# The neck blends from the build's to the face's between these template heights: the collar's
# top is at about 1.49 m on the template.
BLEND = (1.50, 1.565)
# How many head points a carried point follows, and how far out a hair point must stay.
NEAREST = 10
HAIR_CLEAR = 0.0015


def template_body():
    """The template at its bind pose as a skin.Body: what take C's look was fitted on."""
    import skin
    from paths import DRESSING
    kept = DRESSING / "template_body.npz"
    if not kept.exists():
        import body as builder
        layer = builder.build_layer("low")
        names = list(layer.public_joint_names)
        parents = layer.output_joint_parent_ids.detach().numpy().astype(int)
        kept_joints, _, carries = builder.joints_worth_keeping(names, parents)
        world, points = builder.average_bind_pose(layer)
        weights = builder.kept_weights(layer, carries, len(kept_joints))
        DRESSING.mkdir(parents=True, exist_ok=True)
        np.savez(kept, points=points, faces=layer.faces.detach().numpy(), weights=weights,
                 joint_names=np.array([names[old] for old in kept_joints]),
                 joints=world[kept_joints][:, :3, 3])
    data = np.load(kept)
    return skin.Body(data["points"], data["faces"], data["weights"], list(data["joint_names"]),
                     data["joints"])


def head_share(template):
    """Each point's share of the face's head (1) against the build's neck (0), by the point's
    height on the template, zero off the head's joints."""
    owner = template.weights.argmax(axis=1)
    on_head = np.isin(owner, [template.joint_names.index(name) for name in HEAD_JOINTS])
    low, high = BLEND
    rise = np.clip((template.points[:, 1] - low) / (high - low), 0.0, 1.0)
    return np.where(on_head, rise * rise * (3 - 2 * rise), 0.0)


def transplanted(build, face_body, template):
    """The build's points with the face's head on its neck (a new array; the build's own below
    the blend)."""
    share = head_share(template)[:, None]
    placed = face_body.points - face_body.joints["Head"] + build.joints["Head"]
    return build.points * (1 - share) + placed * share


class Carrier:
    """Carries points made on one head onto another made of the same points."""

    def __init__(self, source_points, target_points, template):
        owner = template.weights.argmax(axis=1)
        self.on_head = np.where(np.isin(owner, [template.joint_names.index(name)
                                                for name in HEAD_JOINTS]))[0]
        self.source = source_points[self.on_head]
        self.moved = target_points[self.on_head] - self.source
        self.tree = cKDTree(self.source)

    def __call__(self, points):
        distance, nearest = self.tree.query(points, k=NEAREST)
        weight = 1.0 / np.maximum(distance, 1e-4) ** 2
        weight /= weight.sum(axis=1, keepdims=True)
        return points + np.einsum("pk,pkc->pc", weight, self.moved[nearest])


def kept_outside(points, faces, head_points, head_faces, clear=HAIR_CLEAR):
    """A shell's points pushed out of a head: any point under the skin, or closer to it than
    `clear`, goes out along the skin's normal to `clear` over it; its neighbours follow a little
    so the shell stays smooth."""
    head = trimesh.Trimesh(head_points, head_faces, process=False)
    closest, distance, triangle = trimesh.proximity.closest_point(head, points)
    normal = head.face_normals[triangle]
    side = np.einsum("ij,ij->i", points - closest, normal)
    push = np.clip(clear - side, 0.0, None)
    moved = points + normal * push[:, None]
    if not push.any():
        return moved, 0
    edges = trimesh.Trimesh(points, faces, process=False).edges_unique
    delta = moved - points
    for _ in range(3):
        total = delta.copy()
        count = np.ones(len(points))
        np.add.at(total, edges[:, 0], delta[edges[:, 1]])
        np.add.at(total, edges[:, 1], delta[edges[:, 0]])
        np.add.at(count, edges.ravel(), 1)
        smooth = total / count[:, None]
        delta = np.where((np.linalg.norm(smooth, axis=1) > np.linalg.norm(delta, axis=1))[:, None],
                         smooth, delta)
    return points + delta, int((push > 0).sum())


def head_joint_shift(build):
    """How far the build's head sits from the template's: what takes a point on the build's head
    back to where the face's drawing was made."""
    return np.asarray(build.joints["Head"]) - fit.OURS["Head"]
