"""Level 1's per-frame measures on Warp's tape through Newton's eval_fk, as rows of the inner pose (#70, card plan step
6b): each joint's model centre in SOMA's frame minus SOMA's joint (`evaluation/_measure`: TO_OWN @ centre(...) minus
world[:3, 3], a MIDDLE centre the mean of its parts) and each group's turn error in degrees (the frozen table's link-frame
turn against SOMA's, the card's own `_turn_error`). A body batched per frame: every frame a copy in one model, its
links named per frame. Feeds `_adjoint.case_rows`. Newton's Python only. Each region's bone points' depth outside
SOMA's posed skin (`fit/_skin.marks_kernel`'s measure: the distance to the skin's closest point when outside by the
winding number, 0 inside): the closest point and the side are found off the tape (SOMA never moves with the pose), the
distance to that point taped, so its row is the unit normal's (the envelope rule of a closest point)."""
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


@wp.kernel
def _bone_points(body_q: wp.array[wp.transform], point_link: wp.array[wp.int32], point_local: wp.array[wp.vec3],
                 to_own: wp.mat33, points: wp.array[wp.vec3]):
    point = wp.tid()
    points[point] = to_own * wp.transform_point(body_q[point_link[point]], point_local[point])


@wp.kernel
def _closest(meshes: wp.array[wp.uint64], points: wp.array[wp.vec3], closest: wp.array[wp.vec3],
             outside: wp.array[wp.float32]):
    point = wp.tid()
    found = wp.mesh_query_point_sign_winding_number(meshes[point], points[point], 1.0e6, 2.0, 0.5)
    closest[point] = wp.mesh_eval_position(meshes[point], found.face, found.u, found.v)
    outside[point] = wp.where(found.sign >= 0.0, 1.0, 0.0)


@wp.kernel
def _skin_depths(points: wp.array[wp.vec3], closest: wp.array[wp.vec3], outside: wp.array[wp.float32],
                 depths: wp.array[wp.float32]):
    point = wp.tid()
    depths[point] = outside[point] * wp.length(points[point] - closest[point])


class _Skins:
    """Every region's bone points on every frame against that frame's posed SOMA skin."""

    def __init__(self, skins, device):
        self.names = sorted(skins)
        frames = len(next(iter(skins.values()))[0]) if skins else 0
        self.meshes = [wp.Mesh(points=wp.array(np.asarray(verts, dtype=np.float32), dtype=wp.vec3, device=device),
                               indices=wp.array(np.asarray(faces, dtype=np.int32).ravel(), dtype=wp.int32, device=device))
                       for verts, faces in (skins[self.names[0]][1] if skins else [])]
        rows = [(name, frame, link, local) for name in self.names for frame in range(frames)
                for link, local in skins[name][0][frame]]
        self.counts = [sum(1 for row in rows if row[0] == name) for name in self.names]
        self.frame_of = np.array([row[1] for row in rows], dtype=np.int64)
        self.link = wp.array([row[2] for row in rows], dtype=wp.int32, device=device)
        self.local = wp.array(np.array([row[3] for row in rows], dtype=np.float32).reshape(-1, 3), dtype=wp.vec3,
                              device=device)
        self.mesh_ids = wp.array([self.meshes[row[1]].id for row in rows], dtype=wp.uint64, device=device)
        self.points = wp.zeros(len(rows), dtype=wp.vec3, device=device, requires_grad=True)
        self.closest = wp.zeros(len(rows), dtype=wp.vec3, device=device)
        self.outside = wp.zeros(len(rows), dtype=wp.float32, device=device)
        self.depths = wp.zeros(len(rows), dtype=wp.float32, device=device, requires_grad=True)

    def evaluate(self, body_q, to_own, device):
        """The bone points placed, their closest skin points found off the tape, then their depths outside."""
        count = self.link.shape[0]
        if not count:
            return
        wp.launch(_bone_points, dim=count, inputs=[body_q, self.link, self.local, to_own], outputs=[self.points],
                  device=device)
        wp.launch(_closest, dim=count, inputs=[self.mesh_ids, self.points], outputs=[self.closest, self.outside],
                  device=device, record_tape=False)
        wp.launch(_skin_depths, dim=count, inputs=[self.points, self.closest, self.outside], outputs=[self.depths],
                  device=device)


class TapedMeasures:
    """Joints and turn groups measured off `sites`' (a `TapedSites`) forward kinematics. `joints` {name: (parts per
    frame [[(link, local point in the link frame scaled, share)]], SOMA's joint per frame (frames, 3))}, `to_own` the
    3 x 3 turn into SOMA's frame; `turns` {group: (link per frame, frozen offset quat x y z w, SOMA's turn per frame
    (frames, 4) x y z w, both folded into the link's frame and SOMA's)}; `skins` {region: (bone points per frame
    [[(link, local point in the link frame scaled)]], SOMA's posed skin per frame [(verts (n, 3), faces (m, 3))]), the
    same skin for every region}."""

    def __init__(self, sites, joints, to_own, turns, skins=None):
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
        self.skins = _Skins(skins or {}, device)

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
        self.skins.evaluate(body_q, self.to_own, device)

    def _pose_grad(self):
        """The pose's gradient array (the free coordinates' under couplings, else joint_q)."""
        return self.sites.model.joint_q if self.sites.couplings is None else self.sites.couplings.pose

    def _pose_blocks(self):
        """After a backward pass: each frame's own pose block of the pose's gradient (frames, block)."""
        size = self._pose_grad().shape[0]
        if size % self.frames:
            raise ValueError(f"pose of {size} does not split into {self.frames} equal frame blocks")
        return self._pose_grad().grad.numpy().astype(np.float64).reshape(self.frames, size // self.frames)

    def _constant_blocks(self):
        """After a backward pass: each frame's gradient over level 2's moves (frames, constants), off its own copy's
        inside joints' joint_X_p grads; the free sites' columns zero (no measure reads a site)."""
        constants = self.sites.constants
        if constants is None or constants.inside_joints.shape[0] != self.frames:
            raise ValueError("constant rows need `sites` with constants given per frame (frames, count)")
        joints = self.sites.model.joint_X_p.grad.numpy()[constants.inside_joints, :3].reshape(self.frames, -1)
        return np.concatenate([np.zeros((self.frames, 3 * constants.free_count)), joints], axis=1).astype(np.float64)

    def _rows(self, tape, output, entry_frames, blocks):
        """d output[entry] / d (what `blocks` reads) for every entry as its own frame's row only (entries, width),
        `entry_frames` each entry's frame, `blocks` reading every frame's row after a backward pass. A frame's entries
        move only its own copy, so one backward pass seeds one entry of every frame at once (its k-th): as many passes
        as a frame's most entries, never one per entry."""
        rows = None
        slots = [np.flatnonzero(entry_frames == frame) for frame in range(self.frames)]
        for slot in range(max((len(entries) for entries in slots), default=0)):
            seeded = np.array([entries[slot] for entries in slots if slot < len(entries)], dtype=np.int64)
            seed = np.zeros(output.numpy().shape, dtype=np.float32)
            seed.reshape(-1)[seeded] = 1.0
            tape.backward(grads={output: wp.array(seed, dtype=output.dtype, device=output.device)})
            found = blocks()
            tape.zero()
            self.passes += 1
            rows = np.zeros((len(entry_frames), found.shape[1])) if rows is None else rows
            rows[seeded] = found[entry_frames[seeded]]
        return rows

    def measured(self, inner, outer):
        """`case_rows`' joints {name: (differences (frames, 3) m, rows (frames, 3, block))}, turns {group: (degrees
        (frames,), rows (frames, block))} and skins {region: (depths m, rows (points, block), each point's frame)} at
        (`inner`, `outer`), each row its own frame's pose block (`case_rows(..., frames=)`), off one recorded tape
        (`passes` counts its backward passes)."""
        return self._measured(inner, outer, self._pose_blocks)

    def constant_measured(self, inner, outer):
        """`measured`'s values with rows over level 2's moves (the inner unknowns after the pose, `sites`' constants)
        in place of the pose: joints' (frames, 3, constants), turns' (frames, constants), skins' (points, constants),
        whole rows for `case_rows` without `frames` (its derivative is R_c)."""
        return self._measured(inner, outer, self._constant_blocks)

    def _measured(self, inner, outer, blocks):
        """Every measure at (`inner`, `outer`) with its rows over what `blocks` reads, off one recorded tape."""
        tape = wp.Tape()
        with tape:
            self._evaluate(inner, outer)
        self.passes = 0
        differences = self.differences.numpy().astype(np.float64).reshape(len(self.joint_names), self.frames, 3)
        degrees = self.degrees.numpy().astype(np.float64).reshape(len(self.turn_names), self.frames)
        joint_frames = np.repeat(np.tile(np.arange(self.frames), len(self.joint_names)), 3)
        joint_rows = self._rows(tape, self.differences, joint_frames, blocks).reshape(len(self.joint_names), self.frames, 3, -1)
        turn_frames = np.tile(np.arange(self.frames), len(self.turn_names))
        turn_rows = self._rows(tape, self.degrees, turn_frames, blocks).reshape(len(self.turn_names), self.frames, -1)
        depths = self.skins.depths.numpy().astype(np.float64)
        skin_rows = self._rows(tape, self.skins.depths, self.skins.frame_of, blocks) if depths.size else np.zeros((0, 0))
        bounds = np.cumsum([0] + self.skins.counts)
        return ({name: (differences[index], joint_rows[index]) for index, name in enumerate(self.joint_names)},
                {name: (degrees[index], turn_rows[index]) for index, name in enumerate(self.turn_names)},
                {name: (depths[bounds[index]:bounds[index + 1]], skin_rows[bounds[index]:bounds[index + 1]],
                        self.skins.frame_of[bounds[index]:bounds[index + 1]])
                 for index, name in enumerate(self.skins.names)})
