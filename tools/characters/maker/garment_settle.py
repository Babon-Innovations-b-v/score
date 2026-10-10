"""The prop route's garment settle (plan step 5; owner, 2026-10-10: "for the clothing parts some drape shaping to fully
seal it"): the garment parts only, settled through every frame of every clip against the person's own posed Pixal3D
surface, so cloth stops going through cloth and through the skin and hard parts. No SOMA surface takes part.

    ~/.farm-factory-props/env/bin/python tools/characters/maker/garment_settle.py inputs <body.glb> <settle_in.npz>
    /root/envs/newton/bin/python tools/characters/maker/garment_settle.py run <settle_in.npz> <settle_out.npz>

`inputs` (here, CPU) reads the built person as the engine skins it (people/joins.py's reader): its garment surfaces
welded into one cloth, every other surface (skin, hair, hard parts, and the tucks under the cloth, so the cloth is
held over them: the tucks showed through where the posed surface crossed itself, review 2026-10-10) welded into the
collider, a cloth
point on a border with the collider held as part of it, and every clip's skinning matrices frame by frame, each clip
led in from the bind pose over LEAD_IN frames (each joint's turn against its parent eased from the bind's to the clip's
first frame's), so the settle starts from the welded surface Pixal3D made, which crosses nothing a clip makes.

`run` (on a card, the newton environment; Newton's SolverVBD on NVIDIA Warp, both Apache-2.0, as newton_drape.py):
one model of every point, the collider's points with no mass (moved to their skinned places each substep), the
cloth's with mass, each triangle resting at its bind shape (weak), the cloth bending (weak), contact between every
pair of triangles on (the cloth against the collider and against itself). Each substep every cloth point's speed is set
to reach its skinned place by the substep's end, so with nothing in the way it lands exactly there, and where it would
go into another surface the contact holds it out. Gravity is off: this is not a new drape but the posed one kept from
crossing (the aim of the plan's step 5). Writes each clip's settled cloth minus its skinned cloth, frame by frame, in
metres in the world (`offset_<clip>`), the cloth's point numbers into the glb's garment surfaces, and the record.
"""
import json
import pathlib
import sys
import time

import numpy as np

MAKER = pathlib.Path(__file__).resolve().parent
LEAD_IN = 30
SETTINGS = {
    "fps": 30,              # the clips' frame rate (people/clips.py)
    "substeps": 16,
    "iterations": 8,
    "mass": 1.0e-3,         # every cloth point's mass, kg: heavy enough that its skinned place leads
    "tri_ke": 30.0,         # membrane stiffness: weak, the cloth bends and dents where it is pushed
    "tri_ka": 30.0,
    "edge_ke": 0.05,        # bending
    "contact_ke": 2.0e4,    # contact stiffness (cloth and collider alike)
    "contact_kd": 1.0e-4,
    "radius": 0.0015,       # each point's half thickness
    "self_margin": 0.003,   # contact distance between triangles
    "self_gap": 0.006,      # detection beyond the margin: VBD's step bound grows with it
    "rest_exclusion": 0.002,  # pairs this close in the bind pose never push (Pixal3D's surface touches itself there)
    "lost": 0.08,           # a cloth point this far from its skinned place is put back on it (caught, not settled)
}


# --- inputs (here) --------------------------------------------------------------------------------------------------

def welded_surface(parts, posed=None, keep=None):
    """Parts welded where their copies coincide: (places, faces, joints, weights, each part's point numbers)."""
    sys.path.insert(0, str(MAKER))
    import pokes
    points = np.concatenate([part.points[:keep(part)] for part in parts])
    welded = pokes.weld_map(points)
    count = int(welded.max()) + 1
    places, joints, weights = np.zeros((count, 3)), np.zeros((count, 4), int), np.zeros((count, 4))
    places[welded] = points
    joints[welded] = np.concatenate([part.joints[:keep(part)] for part in parts])
    weights[welded] = np.concatenate([part.weights[:keep(part)] for part in parts])
    faces, numbers, offset = [], [], 0
    for part in parts:
        own = keep(part)
        mine = welded[offset:offset + own]
        faces.append(mine[part.faces[(part.faces < own).all(1)]])
        numbers.append(mine)
        offset += own
    return places, np.concatenate(faces), joints, weights, numbers


def bind_locals(document, inverse_bind, joint_nodes, parent):
    """Each node's own 4x4 at the bind pose: the skin's joints where their inverse bind matrices put them under the
    file's fixed root, every other node at rest."""
    sys.path.insert(0, str(MAKER.parent / "people"))
    import joins
    rotations, translations, scales = joins.node_rest(document)
    rest = joins.world_matrices(rotations, translations, scales, parent)
    world = rest.copy()
    root = [node for node in range(len(parent)) if parent[node] < 0 and node not in joint_nodes][0]
    for slot, node in enumerate(joint_nodes):
        world[node] = rest[root] @ np.linalg.inv(inverse_bind[slot])
    return np.array([world[node] if parent[node] < 0 else np.linalg.inv(world[parent[node]]) @ world[node]
                     for node in range(len(parent))])


def eased(start, end, share):
    """Node 4x4s eased from `start` to `end`: each rotation slerped, each translation and scale moved straight."""
    from scipy.spatial.transform import Rotation, Slerp
    found = end.copy()
    for node in range(len(start)):
        scale_start = np.linalg.norm(start[node, :3, :3], axis=0)
        scale_end = np.linalg.norm(end[node, :3, :3], axis=0)
        turns = Rotation.from_matrix(np.stack([start[node, :3, :3] / scale_start, end[node, :3, :3] / scale_end]))
        scale = scale_start + share * (scale_end - scale_start)
        found[node, :3, :3] = Slerp([0, 1], turns)(share).as_matrix() * scale
        found[node, :3, 3] = start[node, :3, 3] + share * (end[node, :3, 3] - start[node, :3, 3])
    return found


def worlds_of(locals_, parent):
    world = np.zeros_like(locals_)
    for node in np.argsort([depth(parent, node) for node in range(len(parent))], kind="stable"):
        world[node] = locals_[node] if parent[node] < 0 else world[parent[node]] @ locals_[node]
    return world


def depth(parent, node):
    found = 0
    while parent[node] >= 0:
        node, found = parent[node], found + 1
    return found


def clip_moves(document, blob, animation, inverse_bind, joint_nodes, parent, start):
    """A clip's skinning matrices (frames, joints, 4, 4), led in from `start` (the bind's node 4x4s) over LEAD_IN
    frames; the lead-in's frame count."""
    sys.path.insert(0, str(MAKER.parent / "people"))
    import joins
    rotations, translations = joins.clip_frames(document, blob, animation)
    _, _, scales = joins.node_rest(document)
    frames = [joins.world_matrices(rotations[frame], translations[frame], scales, parent)
              for frame in range(len(rotations))]
    first = np.array([np.linalg.inv(frames[0][parent[node]]) @ frames[0][node] if parent[node] >= 0 else frames[0][node]
                      for node in range(len(parent))])
    lead = [worlds_of(eased(start, first, (step + 1) / (LEAD_IN + 1)), parent) for step in range(LEAD_IN)]
    worlds = np.array([world[joint_nodes] for world in lead + frames])
    return worlds @ inverse_bind[None], LEAD_IN


def inputs(body_path, out):
    """The settle's input file from the built person (the module's header)."""
    sys.path.insert(0, str(MAKER))
    sys.path.insert(0, str(MAKER.parent / "people"))
    import joins
    import pokes
    document, blob = joins.read_glb(body_path)
    skin = document["skins"][0]
    inverse_bind = joins.accessor(document, blob, skin["inverseBindMatrices"]).reshape(-1, 4, 4).transpose(0, 2, 1)
    parent = joins.parents_of(document)
    found = pokes.surfaces(document, blob)
    cloth_parts = [part for part, role, _ in found if role == pokes.GARMENT]
    other = [(part, tuck_from) for part, role, tuck_from in found if role != pokes.GARMENT]
    cloth = welded_surface(cloth_parts, keep=lambda part: len(part.points))
    collider = welded_surface([part for part, _ in other], keep=lambda part: len(part.points))
    welded = pokes.weld_map(np.concatenate([cloth[0], collider[0]]))
    first_collider = {number: index for index, number in reversed(list(enumerate(welded[len(cloth[0]):])))}
    held_collider = np.array([first_collider.get(number, -1) for number in welded[:len(cloth[0])]])
    held = held_collider >= 0
    start = bind_locals(document, inverse_bind, skin["joints"], parent)
    arrays = {"cloth_points": cloth[0], "cloth_faces": cloth[1], "cloth_joints": cloth[2], "cloth_weights": cloth[3],
              "held": held, "held_collider": held_collider, "collider_points": collider[0],
              "collider_faces": collider[1],
              "collider_joints": collider[2], "collider_weights": collider[3],
              "cloth_names": np.array([part.name for part in cloth_parts])}
    for number, numbers in enumerate(cloth[4]):
        arrays[f"cloth_numbers_{number}"] = numbers
    clips = []
    for animation in document.get("animations", []):
        moves, lead = clip_moves(document, blob, animation, inverse_bind, skin["joints"], parent, start)
        arrays[f"moves_{animation['name']}"] = moves.astype(np.float32)
        clips.append(animation["name"])
    arrays["clips"], arrays["lead_in"] = np.array(clips), lead
    hips = [document["nodes"][node].get("name") for node in skin["joints"]].index("Hips")
    arrays["anchor_slot"], arrays["anchor_place"] = hips, np.linalg.inv(inverse_bind[hips])[:3, 3]
    np.savez_compressed(out, **arrays)
    return {"cloth_points": len(cloth[0]), "held": int(held.sum()), "collider_points": len(collider[0]),
            "clips": len(clips), "frames": int(sum(len(arrays[f"moves_{clip}"]) for clip in clips))}


# --- run (on the card) ----------------------------------------------------------------------------------------------

def skin_points(points, joints, weights, moves):
    """Linear blend skinning of points by four joints each under one frame's matrices."""
    homogeneous = np.concatenate([points, np.ones((len(points), 1))], axis=1)
    out = np.zeros((len(points), 3))
    for slot in range(joints.shape[1]):
        out += weights[:, slot, None] * np.einsum("pij,pj->pi", moves[joints[:, slot]], homogeneous)[:, :3]
    return out


class Settle:
    """The model and solver: the cloth's free points first, then the collider's, massless (a held cloth point is the
    collider's point it lies on, so the seam is one point and contact never pushes across it)."""

    def __init__(self, data, settings):
        import newton
        import warp as wp
        self.wp, self.settings = wp, settings
        free = np.flatnonzero(~data["held"])
        held = np.flatnonzero(data["held"])
        self.free = free
        self.order_points = np.concatenate([data["cloth_points"][free], data["collider_points"]])
        number = np.empty(len(data["cloth_points"]), int)
        number[free] = np.arange(len(free))
        number[held] = len(free) + data["held_collider"][held]
        self.cloth_number = number
        offset = len(free)
        builder = newton.ModelBuilder(up_axis=newton.Axis.Y, gravity=0.0)
        masses = [settings["mass"]] * len(free) + [0.0] * (len(self.order_points) - len(free))
        builder.add_particles([tuple(point) for point in self.order_points], [(0.0, 0.0, 0.0)] * len(masses), masses,
                              radius=[settings["radius"]] * len(masses))
        cloth_faces = number[data["cloth_faces"]]
        collider_faces = data["collider_faces"] + offset
        faces = np.concatenate([cloth_faces, collider_faces])
        builder.add_triangles(faces[:, 0], faces[:, 1], faces[:, 2], tri_ke=[settings["tri_ke"]] * len(faces),
                              tri_ka=[settings["tri_ka"]] * len(faces), tri_kd=[0.0] * len(faces),
                              tri_drag=[0.0] * len(faces), tri_lift=[0.0] * len(faces))
        edges = bending_edges(cloth_faces)
        if len(edges):
            builder.add_edges(edges[:, 0].tolist(), edges[:, 1].tolist(), edges[:, 2].tolist(), edges[:, 3].tolist(),
                              edge_ke=[settings["edge_ke"]] * len(edges), edge_kd=[0.0] * len(edges))
        builder.color(include_bending=True)
        self.model = builder.finalize()
        self.model.soft_contact_ke = settings["contact_ke"]
        self.model.soft_contact_kd = settings["contact_kd"]
        self.model.soft_contact_mu = 0.0
        self.solver = newton.solvers.SolverVBD(
            self.model, iterations=settings["iterations"], particle_enable_self_contact=True,
            particle_self_contact_margin=settings["self_margin"], particle_self_contact_gap=settings["self_gap"],
            particle_rest_shape_contact_exclusion_radius=settings["rest_exclusion"])
        self.states = [self.model.state(), self.model.state()]
        self.control = self.model.control()
        self.step_seconds = 1.0 / settings["fps"] / settings["substeps"]

    def reset(self, places):
        for state in self.states:
            state.particle_q.assign(places.astype(np.float32))
            state.particle_qd.zero_()

    def frame(self, before, after):
        """One frame: every point led from its place towards `after` (the frame's skinned places, in the model's
        order) through the substeps; the massless ones put exactly on the way."""
        wp = self.wp
        count = len(self.free)
        for step in range(self.settings["substeps"]):
            share = (step + 1) / self.settings["substeps"]
            target = before + share * (after - before)
            now = self.states[0].particle_q.numpy()
            speeds = np.zeros_like(now)
            speeds[:count] = (target[:count] - now[:count]) / self.step_seconds
            now[count:] = target[count:]
            self.states[0].particle_q.assign(now)
            self.states[0].particle_qd.assign(speeds.astype(np.float32))
            self.states[0].clear_forces()
            self.solver.step(self.states[0], self.states[1], self.control, None, self.step_seconds)
            self.states = [self.states[1], self.states[0]]
        wp.synchronize()
        got = self.states[0].particle_q.numpy().astype(float)
        lost = ~np.isfinite(got).all(1) | (np.linalg.norm(got - after, axis=1) > self.settings["lost"])
        lost[count:] = False
        if lost.any():
            got[lost] = after[lost]
            self.states[0].particle_q.assign(got.astype(np.float32))
            self.states[0].particle_qd.zero_()
        return got, int(lost.sum())


def bending_edges(faces):
    """Each inner edge of the triangles with its two opposite corners, as (opposite, opposite, edge, edge) rows."""
    found = {}
    for face in faces:
        for corner in range(3):
            first, second, third = face[corner], face[(corner + 1) % 3], face[(corner + 2) % 3]
            found.setdefault((min(first, second), max(first, second)), []).append(third)
    return np.array([(opposite[0], opposite[1], edge[0], edge[1]) for edge, opposite in found.items()
                     if len(opposite) == 2], int).reshape(-1, 4)


def placed(data, moves, order):
    """Every model point's skinned place under one frame's matrices, in the model's order, less where the hips go (the
    settle runs in the hips' frame: VBD keeps each step within its contact bound, a few millimetres, and the walk's
    travel outran it)."""
    cloth = skin_points(data["cloth_points"], data["cloth_joints"], data["cloth_weights"], moves)
    collider = skin_points(data["collider_points"], data["collider_joints"], data["collider_weights"], moves)
    places = np.zeros((len(order.order_points), 3))
    places[len(order.free):] = collider
    places[order.cloth_number[order.free]] = cloth[order.free]
    anchor = moves[int(data["anchor_slot"])] @ np.append(data["anchor_place"], 1.0)
    return places - anchor[:3]


def run(in_path, out_path):
    import newton
    import warp as wp
    wp.init()
    data = dict(np.load(in_path))
    settle = Settle(data, SETTINGS)
    lead = int(data["lead_in"])
    arrays, record = {}, {"simulator": {"name": "Newton SolverVBD", "version": newton.__version__,
                                        "warp": wp.__version__, "device": str(wp.get_device()),
                                        "licence": "Apache-2.0 (Newton and NVIDIA Warp)"},
                          "settings": SETTINGS, "lead_in": lead, "clips": {}}
    for clip in [str(name) for name in data["clips"]]:
        began = time.time()
        moves = data[f"moves_{clip}"].astype(float)
        before = placed(data, moves[0], settle)
        settle.reset(before)
        offsets, lost = [], 0
        for frame in range(1, len(moves)):
            after = placed(data, moves[frame], settle)
            got, caught = settle.frame(before, after)
            before = after
            if frame >= lead:
                offsets.append(np.where(data["held"][:, None], 0.0, (got - after)[settle.cloth_number]))
                lost += caught
        offsets = np.array(offsets, np.float32)
        size = np.linalg.norm(offsets, axis=2)
        arrays[f"offset_{clip}"] = offsets
        record["clips"][clip] = {"frames": len(offsets), "seconds": round(time.time() - began, 1),
                                 "points_put_back": lost,
                                 "moved_mm_p99": round(float(np.percentile(size, 99)) * 1000, 2),
                                 "moved_mm_max": round(float(size.max()) * 1000, 2),
                                 "points_moved_over_2mm": int((size > 0.002).any(0).sum())}
        print(clip, record["clips"][clip], flush=True)
    np.savez_compressed(out_path, **arrays)
    pathlib.Path(out_path).with_suffix(".json").write_text(json.dumps(record, indent=1))


def main():
    what, *rest = sys.argv[1:]
    if what == "inputs":
        print(json.dumps(inputs(pathlib.Path(rest[0]), pathlib.Path(rest[1]))), flush=True)
    elif what == "run":
        run(pathlib.Path(rest[0]), pathlib.Path(rest[1]))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
