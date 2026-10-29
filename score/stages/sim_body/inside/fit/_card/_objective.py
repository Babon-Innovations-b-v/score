"""A site's place on the card with its own offset and weight per problem (rows from several bodies or level-1 sets in
one batch): Newton's IKObjectivePosition with the offset and weight read per problem instead of one for all."""
import warp as wp
from newton import ik


@wp.kernel(enable_backward=False)
def _place_residuals(body_q: wp.array2d[wp.transform], target: wp.array[wp.vec3], link_index: int,
                     offset: wp.array[wp.vec3], weight: wp.array[wp.float32], start_idx: int,
                     problem_of: wp.array[wp.int32], residuals: wp.array2d[wp.float32]):
    row = wp.tid()
    problem = problem_of[row]
    error = target[problem] - wp.transform_point(body_q[row, link_index], offset[problem])
    for axis in range(3):
        residuals[row, start_idx + axis] = weight[problem] * error[axis]


@wp.kernel(enable_backward=False)
def _place_jacobian(link_index: int, offset: wp.array[wp.vec3], weight: wp.array[wp.float32],
                    affects_dof: wp.array[wp.uint8], body_q: wp.array2d[wp.transform],
                    joint_s: wp.array2d[wp.spatial_vector], start_idx: int, jacobian: wp.array3d[wp.float32]):
    problem, dof = wp.tid()
    if affects_dof[dof] == 0:
        return
    site = wp.transform_point(body_q[problem, link_index], offset[problem])
    motion = joint_s[problem, dof]
    velocity = wp.vec3(motion[0], motion[1], motion[2]) + wp.cross(wp.vec3(motion[3], motion[4], motion[5]), site)
    for axis in range(3):
        jacobian[problem, start_idx + axis, dof] = -weight[problem] * velocity[axis]


class PlacePerProblem(ik.IKObjectivePosition):
    """target [problems] vec3, offset [problems] vec3 in the link's frame, weight [problems] float32; analytic only."""

    def __init__(self, link_index, offsets, targets, weights):
        super().__init__(link_index, wp.vec3(0.0, 0.0, 0.0), targets, weight=1.0)
        self.offsets = offsets
        self.weights = weights

    def supports_analytic(self):
        return True

    def compute_residuals(self, body_q, joint_q, model, residuals, start_idx, problem_idx):
        wp.launch(_place_residuals, dim=body_q.shape[0],
                  inputs=[body_q, self.target_positions, self.link_index, self.offsets, self.weights, start_idx,
                          problem_idx], outputs=[residuals], device=self.device)

    def compute_jacobian_analytic(self, body_q, joint_q, model, jacobian, joint_S_s, start_idx):
        wp.launch(_place_jacobian, dim=[body_q.shape[0], model.joint_dof_count],
                  inputs=[self.link_index, self.offsets, self.weights, self.affects_dof, body_q, joint_S_s,
                          start_idx], outputs=[jacobian], device=self.device)
