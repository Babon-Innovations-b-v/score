"""The exact projection after each step (plan step 1): ranges clipped, every coupling's follower set to
polyval of its (clipped) leader, the frozen coordinates set back to the row's seed; MuJoCo's qpos layout."""
import warp as wp

COUPLING_TERMS = 5


@wp.kernel(enable_backward=False)
def _projected(qpos: wp.array2d[wp.float32], lower: wp.array[wp.float32], upper: wp.array[wp.float32],
               follower_coord: wp.array[wp.int32], leader_coord: wp.array[wp.int32],
               follower_rest: wp.array[wp.float32], leader_rest: wp.array[wp.float32], poly: wp.array2d[wp.float32],
               frozen_coord: wp.array[wp.int32], seeds: wp.array2d[wp.float32]):
    """One row projected in place, in the CPU prototype's order: ranges, couplings, frozen."""
    row = wp.tid()
    for coord in range(qpos.shape[1]):
        qpos[row, coord] = wp.clamp(qpos[row, coord], lower[coord], upper[coord])
    for coupling in range(follower_coord.shape[0]):
        lead = float(0.0)
        if leader_coord[coupling] >= 0:
            lead = qpos[row, leader_coord[coupling]] - leader_rest[coupling]
        value = float(0.0)
        power = float(1.0)
        for term in range(COUPLING_TERMS):
            value += poly[coupling, term] * power
            power *= lead
        qpos[row, follower_coord[coupling]] = follower_rest[coupling] + value
    for frozen in range(frozen_coord.shape[0]):
        qpos[row, frozen_coord[frozen]] = seeds[row, frozen_coord[frozen]]


class Projection:
    """Ranges (an unlimited coordinate +-UNBOUNDED), couplings and frozen coordinates on the card."""

    UNBOUNDED = 1e30

    def __init__(self, lower, upper, follower_coord, leader_coord, follower_rest, leader_rest, poly, frozen_coord,
                 device):
        self.lower = wp.array(lower, dtype=wp.float32, device=device)
        self.upper = wp.array(upper, dtype=wp.float32, device=device)
        self.follower_coord = wp.array(follower_coord, dtype=wp.int32, device=device)
        self.leader_coord = wp.array(leader_coord, dtype=wp.int32, device=device)
        self.follower_rest = wp.array(follower_rest, dtype=wp.float32, device=device)
        self.leader_rest = wp.array(leader_rest, dtype=wp.float32, device=device)
        self.poly = wp.array(poly, dtype=wp.float32, device=device)
        self.frozen_coord = wp.array(frozen_coord, dtype=wp.int32, device=device)


def project(projection, qpos, seeds):
    """qpos [rows, coords] projected in place onto the ranges, couplings and the seeds' frozen coordinates."""
    wp.launch(_projected, dim=qpos.shape[0],
              inputs=[qpos, projection.lower, projection.upper, projection.follower_coord, projection.leader_coord,
                      projection.follower_rest, projection.leader_rest, projection.poly, projection.frozen_coord,
                      seeds], device=qpos.device)
