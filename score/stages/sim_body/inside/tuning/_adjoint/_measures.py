"""Level 1's per-frame measures on Warp's tape through Newton's eval_fk, as rows of the inner pose (#70, card plan step
6b): each joint's model centre in SOMA's frame minus SOMA's joint (`evaluation/_measure`: TO_OWN @ centre(...) minus
world[:3, 3], a MIDDLE centre the mean of its parts) and each group's turn error in degrees (the frozen table's link-frame
turn against SOMA's, the card's own `_turn_error`). A body batched per frame: every frame a copy in one model, its
links named per frame. Feeds `_adjoint.case_rows`. Newton's Python only. Skin depths are not taped here yet."""
import numpy as np
import warp as wp

from _taped import _turn_error


@wp.kernel
def _joint_centres(body_q: wp.array[wp.transform], part_link: wp.array[wp.int32], part_local: wp.array[wp.vec3],
                   part_slot: wp.array[wp.int32], part_share: wp.array[wp.float32], to_own: wp.mat33,
                   centres: wp.array[wp.vec3]):
    part = wp.tid()
    placed = to_own * wp.transform_point(body_q[part_link[part]], part_local[part])
    wp.atomic_add(centres, part_slot[part], part_share[part] * placed)


@wp.kernel
def _joint_differences(centres: wp.array[wp.vec3], targets: wp.array[wp.vec3], differences: wp.array[wp.vec3]):
    slot = wp.tid()
    differences[slot] = centres[slot] - targets[slot]


@wp.kernel
def _turn_degrees(body_q: wp.array[wp.transform], links: wp.array[wp.int32], offsets: wp.array[wp.quat],
                  targets: wp.array[wp.vec4], degrees: wp.array[wp.float32]):
    row = wp.tid()
    degrees[row] = wp.length(_turn_error(body_q[links[row]], targets[row], offsets[row])) * 57.29577951308232


class TapedMeasures:
    """Joints and turn groups measured off `sites`' (a `TapedSites`) forward kinematics. `joints` {name: (parts per
    frame [[(link, local point in the link frame scaled, share)]], SOMA's joint per frame (frames, 3))}, `to_own` the
    3 x 3 turn into SOMA's frame; `turns` {group: (link per frame, frozen offset quat x y z w, SOMA's turn per frame
    (frames, 4) x y z w, both folded into the link's frame and SOMA's)}."""

    def __init__(self, sites, joints, to_own, turns):
        device = sites.model.device
        self.sites, self.joint_names, self.turn_names = sites, sorted(joints), sorted(turns)
        self.frames = len(next(iter(joints.values()))[1]) if joints else len(next(iter(turns.values()))[0])
        parts = [(link, local, share, slot) for slot, (name, frame) in enumerate(
            (name, frame) for name in self.joint_names for frame in range(self.frames))
            for link, local, share in joints[name][0][frame]]
        self.part_link = wp.array([part[0] for part in parts], dtype=wp.int32, device=device)
        self.part_local = wp.array(np.array([part[1] for part in parts], dtype=np.float32), dtype=wp.vec3, device=device)
        self.part_share = wp.array([part[2] for part in parts], dtype=wp.float32, device=device)
        self.part_slot = wp.array([part[3] for part in parts], dtype=wp.int32, device=device)
        targets = np.concatenate([np.asarray(joints[name][1], dtype=np.float32) for name in self.joint_names])
        self.targets = wp.array(targets, dtype=wp.vec3, device=device)
        self.to_own = wp.mat33(*np.asarray(to_own, dtype=np.float32).ravel())
        self.centres = wp.zeros(len(targets), dtype=wp.vec3, device=device, requires_grad=True)
        self.differences = wp.zeros(len(targets), dtype=wp.vec3, device=device, requires_grad=True)
        self.turn_links = wp.array(np.concatenate([turns[name][0] for name in self.turn_names]).astype(np.int32),
                                   dtype=wp.int32, device=device)
        offsets = np.concatenate([np.tile(turns[name][1], (self.frames, 1)) for name in self.turn_names])
        self.turn_offsets = wp.array(offsets.astype(np.float32), dtype=wp.quat, device=device)
        wanted = np.concatenate([np.asarray(turns[name][2]) for name in self.turn_names]).astype(np.float32)
        self.turn_targets = wp.array(wanted, dtype=wp.vec4, device=device)
        self.degrees = wp.zeros(len(wanted), dtype=wp.float32, device=device, requires_grad=True)

    def _evaluate(self, inner, outer):
        """Forward kinematics at `inner`, then every joint difference and turn degree."""
        self.sites._evaluate(inner, outer)
        body_q, device = self.sites.state.body_q, self.sites.model.device
        self.centres.zero_()
        wp.launch(_joint_centres, dim=self.part_link.shape[0],
                  inputs=[body_q, self.part_link, self.part_local, self.part_slot, self.part_share, self.to_own],
                  outputs=[self.centres], device=device)
        wp.launch(_joint_differences, dim=self.targets.shape[0], inputs=[self.centres, self.targets],
                  outputs=[self.differences], device=device)
        wp.launch(_turn_degrees, dim=self.turn_links.shape[0],
                  inputs=[body_q, self.turn_links, self.turn_offsets, self.turn_targets], outputs=[self.degrees],
                  device=device)

    def _row(self, inner, outer, output, entry):
        """d output[entry] / d inner (the pose's part) by one backward pass seeded on that entry alone."""
        tape = wp.Tape()
        with tape:
            self._evaluate(inner, outer)
        seed = np.zeros(output.numpy().shape, dtype=np.float32)
        seed.reshape(-1)[entry] = 1.0
        tape.backward(grads={output: wp.array(seed, dtype=output.dtype, device=output.device)})
        pose = self.sites.model.joint_q if self.sites.couplings is None else self.sites.couplings.pose
        found = pose.grad.numpy().astype(np.float64)
        tape.zero()
        return found

    def measured(self, inner, outer):
        """`case_rows`' joints {name: (differences (frames, 3) m, rows (frames, 3, pose))} and turns {group: (degrees
        (frames,), rows (frames, pose))} at (`inner`, `outer`)."""
        self._evaluate(inner, outer)
        differences = self.differences.numpy().astype(np.float64).reshape(len(self.joint_names), self.frames, 3)
        degrees = self.degrees.numpy().astype(np.float64).reshape(len(self.turn_names), self.frames)
        joint_rows = np.array([self._row(inner, outer, self.differences, entry) for entry in range(differences.size)])
        turn_rows = np.array([self._row(inner, outer, self.degrees, entry) for entry in range(degrees.size)])
        joint_rows = joint_rows.reshape(len(self.joint_names), self.frames, 3, -1)
        turn_rows = turn_rows.reshape(len(self.turn_names), self.frames, -1)
        return ({name: (differences[index], joint_rows[index]) for index, name in enumerate(self.joint_names)},
                {name: (degrees[index], turn_rows[index]) for index, name in enumerate(self.turn_names)})
