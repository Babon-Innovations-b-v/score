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


@wp.kernel
def _link_frames(body_q: wp.array[wp.transform], links: wp.array[wp.int32], frames: wp.array[wp.vec3]):
    """Each used link's place and its turn's three columns, side by side (4 vec3 a link)."""
    used = wp.tid()
    placed = body_q[links[used]]
    turn = wp.transform_get_rotation(placed)
    frames[4 * used] = wp.transform_get_translation(placed)
    frames[4 * used + 1] = wp.quat_rotate(turn, wp.vec3(1.0, 0.0, 0.0))
    frames[4 * used + 2] = wp.quat_rotate(turn, wp.vec3(0.0, 1.0, 0.0))
    frames[4 * used + 3] = wp.quat_rotate(turn, wp.vec3(0.0, 0.0, 1.0))


@wp.kernel
def _seeded(entries: wp.array2d[wp.int32], slot: wp.array[wp.int32], grad: wp.array[wp.float32]):
    """The output's incoming gradient: 1 at each frame's entry of the current slot (-1: the frame has none left)."""
    frame = wp.tid()
    entry = entries[slot[0], frame]
    if entry >= 0:
        grad[entry] = 1.0


@wp.kernel
def _pose_gathered(entries: wp.array2d[wp.int32], slot: wp.array[wp.int32], pose_grad: wp.array[wp.float32],
                   width: wp.int32, rows: wp.array2d[wp.float32]):
    """Each seeded entry's row: its own frame's block of the pose's gradient."""
    frame, column = wp.tid()
    entry = entries[slot[0], frame]
    if entry >= 0:
        rows[entry, column] = pose_grad[frame * width + column]


@wp.kernel
def _constants_gathered(entries: wp.array2d[wp.int32], slot: wp.array[wp.int32], joint_grad: wp.array[wp.transform],
                        inside: wp.array2d[wp.int32], start: wp.int32, rows: wp.array2d[wp.float32]):
    """Each seeded entry's row over level 2's inside joints from `start`: its frame's copy's joint_X_p place grads."""
    frame, joint, axis = wp.tid()
    entry = entries[slot[0], frame]
    if entry >= 0:
        rows[entry, start + 3 * joint + axis] = wp.transform_get_translation(joint_grad[inside[frame, joint]])[axis]


@wp.kernel
def _advanced(slot: wp.array[wp.int32]):
    slot[0] = slot[0] + 1


class _Skins:
    """Every region's bone points on every skin frame against that frame's posed SOMA skin; each point's frame
    (`frame_of`) is its link's copy (`per_copy` bodies a copy), not its skin frame's index: the skins are on every
    EVERY-th frame only."""

    def __init__(self, skins, device, per_copy):
        self.names = sorted(skins)
        frames = len(next(iter(skins.values()))[0]) if skins else 0
        self.meshes = [wp.Mesh(points=wp.array(np.asarray(verts, dtype=np.float32), dtype=wp.vec3, device=device),
                               indices=wp.array(np.asarray(faces, dtype=np.int32).ravel(), dtype=wp.int32, device=device),
                               support_winding_number=True)
                       for verts, faces in (skins[self.names[0]][1] if skins else [])]
        rows = [(name, frame, link, local) for name in self.names for frame in range(frames)
                for link, local in skins[name][0][frame]]
        self.counts = [sum(1 for row in rows if row[0] == name) for name in self.names]
        self.frame_of = np.array([row[2] // per_copy for row in rows], dtype=np.int64)
        self.link = wp.array([row[2] for row in rows], dtype=wp.int32, device=device)
        self.local = wp.array(np.array([row[3] for row in rows], dtype=np.float32).reshape(-1, 3), dtype=wp.vec3,
                              device=device)
        self.mesh_ids = wp.array([self.meshes[row[1]].id for row in rows], dtype=wp.uint64, device=device)
        self.points = wp.zeros(len(rows), dtype=wp.vec3, device=device, requires_grad=True)
        self.closest = wp.zeros(len(rows), dtype=wp.vec3, device=device)
        self.outside = wp.zeros(len(rows), dtype=wp.float32, device=device)
        self.depths = wp.zeros(len(rows), dtype=wp.float32, device=device, requires_grad=True)
        links = np.array([row[2] for row in rows], dtype=np.int64)
        used, self.used_of = np.unique(links, return_inverse=True)
        self.locals = np.array([row[3] for row in rows], dtype=np.float32).reshape(-1, 3).astype(np.float64)
        self.used = wp.array(used.astype(np.int32), dtype=wp.int32, device=device)
        self.link_frames = wp.zeros(4 * len(used), dtype=wp.vec3, device=device, requires_grad=True)
        self.link_entry_frames = np.repeat(used // per_copy, 12)

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
        wp.launch(_link_frames, dim=self.used.shape[0], inputs=[body_q, self.used], outputs=[self.link_frames],
                  device=device)

    def point_weights(self, to_own):
        """Each bone point's depth gradient over its link's frame entries ((points, 12), as `_link_frames` lays them):
        the depth's gradient in the point (outside times the unit from its closest skin point, SOMA's frame) turned
        back to the world, times d(place + turn @ local)."""
        points, closest = self.points.numpy().astype(np.float64), self.closest.numpy().astype(np.float64)
        apart = points - closest
        lengths = np.linalg.norm(apart, axis=1)
        unit = np.divide(apart, lengths[:, None], out=np.zeros_like(apart), where=lengths[:, None] > 0)
        world = (self.outside.numpy().astype(np.float64)[:, None] * unit) @ np.asarray(to_own, dtype=np.float64)
        return np.concatenate([world[:, None, :], self.locals[:, :, None] * world[:, None, :]], axis=1).reshape(-1, 12)

    def rows_of(self, link_rows, to_own):
        """Every bone point's depth row from its link's frame rows (`link_rows` (used links x 12, width): d of the
        link's place and turn columns, as `_link_frames` lays them), through `point_weights`. One backward pass a
        link frame entry, not a bone point (2026-10-31: tall_kimodo's 8,233 passes, each the whole tape run back, were
        a block's largest step)."""
        weights = self.point_weights(to_own)[:, None, :]
        per_link = link_rows.reshape(-1, 12, link_rows.shape[1])
        found = np.empty((len(weights), link_rows.shape[1]))
        for start in range(0, len(weights), 2048):
            stop = start + 2048
            found[start:stop] = (weights[start:stop] @ per_link[self.used_of[start:stop]])[:, 0]
        return found

    def seed(self, coefficients, part, to_own, weights=None):
        """The link frames' incoming gradient (4 x used links vec3) of sum(coefficients * depth) over the points
        `part` (a slice): each point's `point_weights` row summed onto its link."""
        weights = self.point_weights(to_own) if weights is None else weights
        seeded = np.zeros((self.used.shape[0], 12))
        np.add.at(seeded, self.used_of[part], coefficients[:, None] * weights[part])
        return seeded.reshape(-1, 3)


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
        self.own = np.asarray(to_own, dtype=np.float64).reshape(3, 3)
        self.centres = wp.zeros(len(targets), dtype=wp.vec3, device=device, requires_grad=True)
        self.differences = wp.zeros(len(targets), dtype=wp.vec3, device=device, requires_grad=True)
        self.turn_links = wp.array(np.concatenate([turns[name][0] for name in self.turn_names]).astype(np.int32),
                                   dtype=wp.int32, device=device)
        offsets = np.concatenate([np.tile(turns[name][1], (self.frames, 1)) for name in self.turn_names])
        self.turn_offsets = wp.array(offsets.astype(np.float32), dtype=wp.quat, device=device)
        wanted = np.concatenate([np.asarray(turns[name][2]) for name in self.turn_names]).astype(np.float32)
        self.turn_targets = wp.array(wanted, dtype=wp.vec4, device=device)
        self.degrees = wp.zeros(len(wanted), dtype=wp.float32, device=device, requires_grad=True)
        self.skins = _Skins(skins or {}, device, sites.model.body_count // self.frames)

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

    def part_turns(self):
        """After an evaluation: each joint part's d (its joint and frame's difference) / d (its local point), its share
        times to_own @ its link's rotation (parts, 3, 3), in `joints`' order (sorted names, then frames, then parts)."""
        from scipy.spatial.transform import Rotation
        placed = self.sites.state.body_q.numpy()[self.part_link.numpy()]
        turned = np.asarray(self.to_own, dtype=np.float64).reshape(3, 3) @ Rotation.from_quat(placed[:, 3:7]).as_matrix()
        return self.part_share.numpy().astype(np.float64)[:, None, None] * turned

    def _pose_grad(self):
        """The pose's gradient array (the free coordinates' under couplings, else joint_q)."""
        return self.sites.model.joint_q if self.sites.couplings is None else self.sites.couplings.pose

    def _gathers(self, pose, constants, rows, entries, slot):
        """The launches that copy each seeded entry's row into `rows` on the card after a backward pass: its frame's
        pose block (`pose`), then level 2's moves (`constants`: the free sites' columns zero, then each inside joint's
        joint_X_p place grad off its frame's copy); the row width they fill."""
        device, launches, width = self.sites.model.device, [], 0
        if pose:
            size = self._pose_grad().shape[0]
            if size % self.frames:
                raise ValueError(f"pose of {size} does not split into {self.frames} equal frame blocks")
            block = size // self.frames
            launches.append(lambda: wp.launch(_pose_gathered, dim=(self.frames, block), inputs=[
                entries, slot, self._pose_grad().grad, block], outputs=[rows()], device=device))
            width = block
        if constants:
            held = self.sites.constants
            if held is None or held.inside_joints.shape[0] != self.frames:
                raise ValueError("constant rows need `sites` with constants given per frame (frames, count)")
            start, count = width + 3 * held.free_count, held.inside_joints.shape[1]
            inside = wp.array(np.asarray(held.inside_joints, dtype=np.int32).reshape(self.frames, count), dtype=wp.int32,
                              device=device)
            launches.append(lambda: wp.launch(_constants_gathered, dim=(self.frames, count, 3), inputs=[
                entries, slot, self.sites.model.joint_X_p.grad, inside, start], outputs=[rows()],
                device=device))
            width = start + 3 * count
        return launches, width

    def _rows(self, tape, output, entry_frames, pose, constants):
        """d output[entry] / d (the pose's frame blocks when `pose`, level 2's moves when `constants`, side by side)
        for every entry as its own frame's row only (entries, width). A frame's entries move only its own copy, so one
        backward pass seeds one entry of every frame at once (its k-th): as many passes as a frame's most entries,
        never one per entry. All on the card: each pass seeds, runs the tape back, gathers its rows and zeroes the
        grads by launches alone, the first eagerly and the rest one CUDA graph replayed (2026-10-31: a real block's
        8,233 passes, each read back to the host, took 21 s alone and 83 s beside l1d's other blocks)."""
        device = output.device
        slots = [np.flatnonzero(entry_frames == frame) for frame in range(self.frames)]
        count = max((len(found) for found in slots), default=0)
        table = np.full((max(count, 1), self.frames), -1, dtype=np.int32)
        for frame, found in enumerate(slots):
            table[:len(found), frame] = found
        entries, slot = wp.array(table, dtype=wp.int32, device=device), wp.zeros(1, dtype=wp.int32, device=device)
        made = {}
        launches, width = self._gathers(pose, constants, lambda: made["rows"], entries, slot)
        made["rows"] = wp.zeros((len(entry_frames), width), dtype=wp.float32, device=device)
        if not count:
            return made["rows"].numpy().astype(np.float64)
        if output.grad is None:
            output.grad = wp.zeros_like(output)
        incoming = output.grad.view(wp.float32).flatten()

        def passed():
            """One backward pass: seeded, run back, its rows gathered, every grad zeroed, the slot moved on."""
            wp.launch(_seeded, dim=self.frames, inputs=[entries, slot], outputs=[incoming], device=device)
            tape.backward()
            for launch in launches:
                launch()
            tape.zero()
            wp.launch(_advanced, dim=1, inputs=[slot], device=device)
        tape.zero()
        passed()  # the first eagerly: every kernel loaded and every grad the tape keeps made before the capture
        if count > 1:
            with wp.ScopedCapture(device=device, force_module_load=False) as capture:
                passed()
            for _ in range(count - 1):
                wp.capture_launch(capture.graph)
        self.passes += count
        return made["rows"].numpy().astype(np.float64)

    def measured(self, inner, outer):
        """Joints {name: (differences (frames, 3) m, None)}, turns {group: (degrees (frames,), None)} and skins
        {region: (depths m, rows (points, block), each point's frame)} at (`inner`, `outer`), each skin row its own
        frame's pose block (`case_rows(skins, frames=)`), off one recorded tape (`passes` counts its backward passes).
        Only the skins are taped: level 1's rows are the bones inside the skin since 2026-11-01 (turns its check,
        joints reported; their rows were about 89 of a frame's backward passes)."""
        return self._measured(inner, outer, pose=True, constants=False)

    def constant_measured(self, inner, outer):
        """`measured`'s values with the skins' rows over level 2's moves (the inner unknowns after the pose, `sites`'
        constants) in place of the pose, (points, constants): whole rows for `case_rows` without `frames` (its
        derivative is R_c)."""
        return self._measured(inner, outer, pose=False, constants=True)

    def joined_measured(self, inner, outer):
        """(`measured`, `constant_measured`) off one tape and one set of backward passes: each pass reads both the
        pose's and level 2's moves' gradient, so R_q and R_c cost one taping, not two."""
        width = self._pose_grad().shape[0] // self.frames
        both = self._measured(inner, outer, pose=True, constants=True)
        return _split(both, slice(None, width)), _split(both, slice(width, None))

    def region_rows(self, inner, outer):
        """{("skin", region): (its bones' depth outside, root mean square in mm; its row over the whole pose, every
        frame's block; its row over level 2's moves), ("turn", group): (its turn error, root mean square over frames
        in degrees; the same two rows)} at (`inner`, `outer`): `case_rows`' raw rows, each by ONE backward pass seeded
        with the root mean square's own gradient (a vector-Jacobian product: a skin's over its depths, `_Skins.seed`;
        a turn's over its frames' degrees), not one a link frame entry (2026-11-01: a frame's ~600 passes each ran the
        whole tape back, most of a block's time). `passes` counts them. The turns are level 1's second term (owner,
        2026-11-03)."""
        tape = wp.Tape()
        with tape:
            self._evaluate(inner, outer)
        depths = self.skins.depths.numpy().astype(np.float64)
        degrees = self.degrees.numpy().astype(np.float64)
        weights = self.skins.point_weights(self.own)
        bounds = np.cumsum([0] + self.skins.counts)
        pose_size = self._pose_grad().shape[0]
        constant_size = self.sites.constants.size if self.sites.constants is not None else 0
        found, self.passes = {}, 0

        def passed(grads):
            """The pose's and level 2's moves' rows of one backward pass seeded by `grads`."""
            tape.backward(grads=grads)
            pose_row = self._pose_grad().grad.numpy().astype(np.float64)
            constant_row = (self.sites.constants.gradient(self.sites.offsets, self.sites.model.joint_X_p)
                            if constant_size else np.zeros(0))
            tape.zero()
            self.passes += 1
            return pose_row, constant_row
        for index, name in enumerate(self.skins.names):
            part = slice(bounds[index], bounds[index + 1])
            root = float(np.sqrt(np.mean(np.square(depths[part]))))
            if root == 0.0:
                found[("skin", name)] = (0.0, np.zeros(pose_size), np.zeros(constant_size))
                continue
            coefficients = 1000.0 * depths[part] / (len(depths[part]) * root)
            seeded = self.skins.seed(coefficients, part, self.own, weights)
            found[("skin", name)] = (1000.0 * root, *passed({self.skins.link_frames: wp.array(
                seeded.astype(np.float32), dtype=wp.vec3, device=self.skins.link_frames.device)}))
        for index, name in enumerate(self.turn_names):
            part = slice(index * self.frames, (index + 1) * self.frames)
            root = float(np.sqrt(np.mean(np.square(degrees[part]))))
            if root == 0.0:
                found[("turn", name)] = (0.0, np.zeros(pose_size), np.zeros(constant_size))
                continue
            seed = np.zeros(len(degrees), dtype=np.float32)
            seed[part] = degrees[part] / (self.frames * root)
            found[("turn", name)] = (root, *passed({self.degrees: wp.array(seed, dtype=wp.float32,
                                                                           device=self.degrees.device)}))
        return found

    def _measured(self, inner, outer, pose, constants):
        """Every measure at (`inner`, `outer`) with its rows over the pose and/or level 2's moves, off one recorded
        tape."""
        tape = wp.Tape()
        with tape:
            self._evaluate(inner, outer)
        self.passes = 0
        differences = self.differences.numpy().astype(np.float64).reshape(len(self.joint_names), self.frames, 3)
        degrees = self.degrees.numpy().astype(np.float64).reshape(len(self.turn_names), self.frames)
        depths = self.skins.depths.numpy().astype(np.float64)
        skin_rows = self.skins.rows_of(self._rows(tape, self.skins.link_frames, self.skins.link_entry_frames, pose,
                                                  constants), self.own) if depths.size else np.zeros((0, 0))
        bounds = np.cumsum([0] + self.skins.counts)
        return ({name: (differences[index], None) for index, name in enumerate(self.joint_names)},
                {name: (degrees[index], None) for index, name in enumerate(self.turn_names)},
                {name: (depths[bounds[index]:bounds[index + 1]], skin_rows[bounds[index]:bounds[index + 1]],
                        self.skins.frame_of[bounds[index]:bounds[index + 1]])
                 for index, name in enumerate(self.skins.names)})


def _split(found, columns):
    """`_measured`'s (joints, turns, skins) with each skin row cut to `columns` (the values and frames kept)."""
    joints, turns, skins = found
    return (joints, turns,
            {name: (values, rows[..., columns], frames) for name, (values, rows, frames) in skins.items()})
