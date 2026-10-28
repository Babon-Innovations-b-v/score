"""What the run writes for one person (out.json's entry and <out>.npz's arrays, the contract the stage reads): each
frame's record (`frames`: the body's and the clip's segment turns, the joints' moments, the ground's push, the feet,
the residual and reserve, the muscles' activations and forces; the poses the skin plays are SOMA's own, the stage's)
with the arrays drawn beside
(each body's and segment's pose, the muscles' paths), the bone meshes (`bones_of`), the arrays by name (`arrays`),
the person's entry (`entry`) and RRA's `adjusted` record (`adjustment_record`)."""
import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

from bone_groups import LACKS
from contact import lowest_over
from ground import heights_over
from model import TO_OWN, own_pose
from rra import RRA_ROUNDS, turned_off

BONE_CELL = 0.005  # metres: the drawn bones' vertices merged within this


def segment_pose(world):
    """A 4 x 4 as [x, y, z, qx, qy, qz, qw]."""
    return [*world[:3, 3], *Rotation.from_matrix(world[:3, :3]).as_quat()]


def local_turns(worlds, parents):
    """Each segment but the first against its parent, as rotation vectors in degrees."""
    return [Rotation.from_matrix(worlds[parent][:3, :3].T @ worlds[index][:3, :3]).as_rotvec(degrees=True)
            for index, parent in enumerate(parents) if parent >= 0]


def rounded(value):
    return None if value is None else round(value, 5)


def _path_of(data, tendon):
    """A tendon's path points now (MuJoCo's frame): its wrap points, a pulley's (a break between branches, at the
    origin) left out."""
    span = slice(data.ten_wrapadr[tendon], data.ten_wrapadr[tendon] + data.ten_wrapnum[tendon])
    return data.wrap_xpos.reshape(-1, 3)[span][data.wrap_obj.reshape(-1)[span] != -2]


def merged(points, faces):
    """A mesh with its vertices merged within BONE_CELL (vertex clustering) and the faces that fell flat dropped."""
    cells = np.round(points / BONE_CELL).astype(np.int64)
    _, first, inverse = np.unique(cells, axis=0, return_index=True, return_inverse=True)
    faces = inverse.reshape(-1)[faces]
    faces = faces[(faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 0] != faces[:, 2])]
    return points[first], faces


def bones_of(model):
    """The bone meshes of the person's model in their bodies' frames ({body name: (points, faces)}), from MuJoCo's own
    compile of its file (`model`), each mesh's vertices merged within BONE_CELL."""
    found = {}
    for geom in np.flatnonzero(model.geom_type == mujoco.mjtGeom.mjGEOM_MESH):
        mesh = model.geom_dataid[geom]
        points = model.mesh_vert[model.mesh_vertadr[mesh]:model.mesh_vertadr[mesh] + model.mesh_vertnum[mesh]]
        faces = model.mesh_face[model.mesh_faceadr[mesh]:model.mesh_faceadr[mesh] + model.mesh_facenum[mesh]]
        turn = np.zeros(9)
        mujoco.mju_quat2Mat(turn, model.geom_quat[geom])
        points = points @ turn.reshape(3, 3).T + model.geom_pos[geom]
        points, faces = merged(points, faces)
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, model.geom_bodyid[geom])
        if name in found:
            before = found[name]
            points, faces = np.concatenate([before[0], points]), np.concatenate([before[1], faces + len(before[0])])
        found[name] = (points, faces)
    return found


def com_height(model, qpos, ground):
    """The centre of mass' height over its ground at a pose (m)."""
    data = mujoco.MjData(model)
    data.qpos[:] = qpos
    mujoco.mj_kinematics(model, data)
    mujoco.mj_comPos(model, data)
    return float(heights_over((data.subtree_com[model.jnt_bodyid[0]] @ TO_OWN.T)[None], ground)[0])


def adjustment_record(moved_by, kept, shares, step, before, after, segments, follows):
    """How far RRA moved the body (a quality measure, sim_bodies.json `adjusted`): the pelvis (cm) and its turn and
    each segment's turn (degrees) against the fitted path, median and largest over the frames, and the largest of any
    segment on any frame (the `follows` gate's per-frame cap), every body's mass change (made, within MASS_MOST, and RRA's
    recommended one each round, OpenSim's report) and the torso's centre of mass
    move (cm, its own frame), the share of the move kept under the follows cap, the least share a frame kept under the
    per-frame cap (`within_frames`), and the follows measure before and after."""
    turns = turned_off(before, after)
    turned = {segment: turns[:, index] for index, segment in enumerate(segments)}
    pelvis = 100 * np.linalg.norm(moved_by, axis=1)
    return {"method": "OpenSim's residual reduction (RRA; Delp et al. 2007, opensim-core RRATool): the pelvis' and "
                      "trunk's path and the body's masses and torso centre of mass adjusted, capped by follows",
            "rounds": RRA_ROUNDS, "kept share": kept, "least frame share": round(float(shares.min()), 3),
            "pelvis cm": [round(float(np.median(pelvis)), 2), round(float(pelvis.max()), 2)],
            "largest turn deg": round(float(turns.max()), 2),
            "segments deg": {segment: [round(float(np.median(found)), 2), round(float(found.max()), 2)]
                             for segment, found in turned.items()},
            "mass %": round(100 * float(step["mass"]), 3),
            "mass % recommended": [round(100 * float(share), 3) for share in step["mass recommended"]],
            "torso centre of mass cm": np.round(100 * step["torso"], 2).tolist(),
            "follows deg": [round(follows[0], 3), round(follows[1], 3)]}


def frames(physics, path, velocities, accelerations, worlds, ground, riders, feet, drawn_ids):
    """Every frame's record and the drawn arrays beside it: its physics shared out (`Physics.shared`), its segments
    riding their bones (`riders`: segments, bodies, riding, parents), the feet (`feet`: {segment: geoms}); returns
    the records, each drawn body's poses, each segment's, the muscles' paths and their point counts. The poses the
    skin plays are SOMA's own, written by the stage (#70: SOMA is the truth, never moved)."""
    model = physics.model
    segment_names, bodies, riding, parents = riders
    found, bones, segments, paths, counts = [], [], [], [], []
    for frame in range(len(path)):
        share = physics.shared(physics.needed(path[frame], velocities[frame], accelerations[frame]))
        data = physics.data
        posed = [own_pose(model, data, bodies[segment]) @ riding[segment] for segment in segment_names]
        pushes = share["pushes"] @ TO_OWN.T
        found.append({
            "angles": np.round(local_turns(posed, parents), 3).tolist(),  # the body's segments' turns
            "targets": np.round(local_turns(worlds[frame], parents), 3).tolist(),
            "torques": np.round(share["moments"], 3).tolist(),
            "ground": np.round(pushes.sum(axis=0), 3).tolist(),
            "lowest": rounded(lowest_over(model, data, physics.colliders, ground)),
            "feet": {segment: [rounded(lowest_over(model, data, geoms, ground)) if geoms else None,
                               round(float(pushes[bodies[segment], 1]), 3)] for segment, geoms in feet.items()},
            "residual": np.round(np.concatenate([TO_OWN @ share["residual"][:3], TO_OWN @ share["residual"][3:]]),
                                 3).tolist(),
            "reserve": round(float(np.abs(share["reserves"]).max(initial=0.0)), 3),
            "activations": np.round(share["activations"], 4).tolist(),
            "forces": np.round(share["forces"], 2).tolist()})
        segments.append([segment_pose(world) for world in posed])
        bones.append([segment_pose(own_pose(model, data, body)) for body in drawn_ids])
        mine = [_path_of(data, tendon) for tendon in model.actuator_trnid[physics.muscles, 0]]
        counts.append([len(points) for points in mine])
        paths.append(np.concatenate(mine) @ TO_OWN.T)
    return found, bones, segments, paths, counts


def arrays(name, bones, segments, paths, counts, meshes):
    """One person's arrays in <out>.npz, by name: `<name>/bones`, `/segments`, `/paths`, `/counts` and each bone's
    `/mesh/<body>/points|faces`."""
    found = {f"{name}/bones": np.asarray(bones, dtype=np.float32),
             f"{name}/segments": np.asarray(segments, dtype=np.float32),
             f"{name}/paths": np.concatenate(paths).astype(np.float32),
             f"{name}/counts": np.asarray(counts, dtype=np.int32)}
    for body, (points, faces) in meshes.items():
        found[f"{name}/mesh/{body}/points"] = points.astype(np.float32)
        found[f"{name}/mesh/{body}/faces"] = faces.astype(np.int32)
    return found


def entry(model, record, names, rides, qpos, ground, gravity, adjustment, records):
    """One person's out.json entry: its model record with what MyoFullBody lacks, its muscles, joints, drawn bones
    and the body each segment rides (`names`: those four), the centre of mass' height at `qpos` over the ground, its
    mass and weight, RRA's `adjusted` record and every frame's record."""
    muscles, joints, drawn = names
    weight = sum(model.body_mass) * gravity
    return {"model": {**record, "lacks": {key: value for key, value in LACKS.items()}},
            "muscles": muscles, "joints": joints, "bones": drawn, "rides": rides,
            "com height": round(com_height(model, qpos, ground), 4),
            "kg": round(float(sum(model.body_mass)), 3),
            "weight N": round(float(weight), 2), "adjusted": adjustment, "frames": records}
