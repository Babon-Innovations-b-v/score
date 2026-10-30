"""Level 3 across sets: Newton's batched forward kinematics with each row's own joint places (joint_X_p), so one card
batch holds every set's frames (rows = set x frame) though each set's inside-joint moves change its body places.
The kernel is Newton's _eval_fk_articulation_batched (ik_common) with joint_X_p read as the row's set's row of a
[sets, joints] array; the arithmetic is Newton's own eval_single_articulation_fk, so all rows on one set equal
Newton's bit for bit."""
import warp as wp
from newton._src.sim.articulation import eval_single_articulation_fk
from newton._src.sim.enums import BodyFlags


@wp.kernel
def _per_row_fk(
    articulation_start: wp.array[wp.int32],
    articulation_end: wp.array[wp.int32],
    joint_articulation: wp.array[int],
    joint_q: wp.array2d[wp.float32],
    joint_qd: wp.array2d[wp.float32],
    joint_q_start: wp.array[wp.int32],
    joint_qd_start: wp.array[wp.int32],
    joint_type: wp.array[wp.int32],
    joint_parent: wp.array[wp.int32],
    joint_child: wp.array[wp.int32],
    set_places: wp.array2d[wp.transform],
    row_set: wp.array[wp.int32],
    joint_X_c: wp.array[wp.transform],
    joint_axis: wp.array[wp.vec3],
    joint_dof_dim: wp.array2d[wp.int32],
    body_com: wp.array[wp.vec3],
    body_flags: wp.array[wp.int32],
    body_q: wp.array2d[wp.transform],
    body_qd: wp.array2d[wp.spatial_vector],
):
    problem_idx, articulation_idx = wp.tid()
    eval_single_articulation_fk(
        articulation_start[articulation_idx], articulation_end[articulation_idx], joint_articulation,
        joint_q[problem_idx], joint_qd[problem_idx], joint_q_start, joint_qd_start, joint_type, joint_parent,
        joint_child, set_places[row_set[problem_idx]], joint_X_c, joint_axis, joint_dof_dim, body_com, body_flags,
        int(BodyFlags.ALL), body_q[problem_idx], body_qd[problem_idx])


def per_row_fk(model, set_places, row_set, joint_q, joint_qd, body_q, body_qd):
    """Body frames of every row, row r with joint places set_places[row_set[r]] ([sets, joints] transforms)."""
    wp.launch(
        kernel=_per_row_fk, dim=[joint_q.shape[0], model.articulation_count],
        inputs=[model.articulation_start, model.articulation_end, model.joint_articulation, joint_q, joint_qd,
                model.joint_q_start, model.joint_qd_start, model.joint_type, model.joint_parent, model.joint_child,
                set_places, row_set, model.joint_X_c, model.joint_axis, model.joint_dof_dim, model.body_com,
                model.body_flags],
        outputs=[body_q, body_qd], device=model.device)
