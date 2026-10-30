"""Every row's link frames in float64 on the card (the residuals' precision; Newton's own FK is float32, and its
float32 noise is what held the shoulder's elevation plane 0.02 deg off mink's float64 minimum).

The same maths as Newton's eval_single_articulation_fk for the joints a person model has: free (position, then
the turn x, y, z, w), revolute about its axis, prismatic along it, fixed; a joint's parent link is laid before it (MJCF order).
Each row reads its joint places (joint_X_p) from its set's row of a [sets, joints] array (level 3 across sets: rows =
set x frame, each set's inside-joint moves its own places); one set by default, the model's own."""
import numpy as np
import warp as wp
from newton import JointType

FREE = int(JointType.FREE)
REVOLUTE = int(JointType.REVOLUTE)
FIXED = int(JointType.FIXED)
PRISMATIC = int(JointType.PRISMATIC)


@wp.func
def _still():
    return wp.quatd(wp.float64(0.0), wp.float64(0.0), wp.float64(0.0), wp.float64(1.0))


@wp.kernel(enable_backward=False)
def _frames(joint_q: wp.array2d[wp.float32], joint_type: wp.array[wp.int32], joint_parent: wp.array[wp.int32],
            joint_child: wp.array[wp.int32], q_start: wp.array[wp.int32], qd_start: wp.array[wp.int32],
            joint_x_p: wp.array2d[wp.transformd], row_set: wp.array[wp.int32], joint_x_c: wp.array[wp.transformd], joint_axis: wp.array[wp.vec3d],
            body_q: wp.array2d[wp.transformd]):
    row = wp.tid()
    for joint in range(joint_type.shape[0]):
        kind = joint_type[joint]
        start = q_start[joint]
        across = wp.transformd(wp.vec3d(), _still())
        if kind == REVOLUTE:
            angle = wp.float64(joint_q[row, start])
            across = wp.transformd(wp.vec3d(), wp.quat_from_axis_angle(joint_axis[qd_start[joint]], angle))
        if kind == PRISMATIC:
            across = wp.transformd(joint_axis[qd_start[joint]] * wp.float64(joint_q[row, start]), _still())
        if kind == FREE:
            place = wp.vec3d(wp.float64(joint_q[row, start]), wp.float64(joint_q[row, start + 1]),
                             wp.float64(joint_q[row, start + 2]))
            turn = wp.quatd(wp.float64(joint_q[row, start + 3]), wp.float64(joint_q[row, start + 4]),
                            wp.float64(joint_q[row, start + 5]), wp.float64(joint_q[row, start + 6]))
            across = wp.transformd(place, turn)
        parent_joint = joint_x_p[row_set[row], joint]
        parent = joint_parent[joint]
        if parent >= 0:
            parent_joint = body_q[row, parent] * parent_joint
        body_q[row, joint_child[joint]] = parent_joint * across * wp.transform_inverse(joint_x_c[joint])


class Forward:
    """The model's joint tree in float64 on the card; raises ValueError on a joint kind it does not hold. set_places
    [sets, joints, 7] (Newton's transform layout) and row_set [rows] give each row its set's joint places; neither, the
    model's own for every row."""

    def __init__(self, model, set_places=None, row_set=None):
        kinds = model.joint_type.numpy()
        unknown = sorted(set(int(kind) for kind in kinds) - {FREE, REVOLUTE, PRISMATIC, FIXED})
        if unknown:
            raise ValueError(f"joint kinds {unknown} have no float64 frames here")
        parents = model.joint_parent.numpy()
        children = model.joint_child.numpy()
        if any(parent >= 0 and parent not in children[:joint] for joint, parent in enumerate(parents)):
            raise ValueError("a joint's parent link is laid after it")
        device = model.device
        self.bodies = model.body_count
        self.joint_type = wp.array(kinds.astype(np.int32), dtype=wp.int32, device=device)
        self.joint_parent = wp.array(parents.astype(np.int32), dtype=wp.int32, device=device)
        self.joint_child = wp.array(children.astype(np.int32), dtype=wp.int32, device=device)
        self.q_start = wp.array(model.joint_q_start.numpy()[:-1].astype(np.int32), dtype=wp.int32, device=device)
        self.qd_start = wp.array(model.joint_qd_start.numpy()[:-1].astype(np.int32), dtype=wp.int32, device=device)
        places = model.joint_X_p.numpy()[None] if set_places is None else np.asarray(set_places)
        if places.shape[1:] != (len(kinds), 7):
            raise ValueError(f"set places {places.shape} are not [sets, {len(kinds)} joints, 7]")
        self.joint_x_p = wp.array(places.astype(np.float64), dtype=wp.transformd, device=device)
        if row_set is None and places.shape[0] > 1:
            raise ValueError(f"{places.shape[0]} sets of joint places and no row_set")
        self.row_set = None if row_set is None else wp.array(np.asarray(row_set, dtype=np.int32), dtype=wp.int32,
                                                                  device=device)
        self.joint_x_c = wp.array(model.joint_X_c.numpy().astype(np.float64), dtype=wp.transformd, device=device)
        self.joint_axis = wp.array(model.joint_axis.numpy().astype(np.float64), dtype=wp.vec3d, device=device)


def frames(forward, joint_q, body_q):
    """body_q [rows, bodies] transformd: every row's link frames from joint_q [rows, coords] (Newton's layout)."""
    rows = joint_q.shape[0]
    if forward.row_set is None:
        forward.row_set = wp.zeros(rows, dtype=wp.int32, device=joint_q.device)
    if forward.row_set.shape[0] != rows:
        raise ValueError(f"row_set holds {forward.row_set.shape[0]} rows, joint_q {rows}")
    wp.launch(_frames, dim=joint_q.shape[0],
              inputs=[joint_q, forward.joint_type, forward.joint_parent, forward.joint_child, forward.q_start,
                      forward.qd_start, forward.joint_x_p, forward.row_set, forward.joint_x_c, forward.joint_axis],
              outputs=[body_q], device=joint_q.device)
