"""The honest measures level 1 scores on, on the card (#70, the card build plan's step 3): each SOMA joint's position
error (mm), each bone group's rotation error on the frozen table (deg) and the share of bone vertices outside SOMA's
posed skin by region, as `evaluation._measure.measures` gives them ("joints mm", "per joint mm", "turns deg",
"per group deg", "bones outside skin %", "bones outside all %"); its other readings (tips, lengths, floor, depths)
stay on the CPU. The frames' poses by MuJoCo's float64 kinematics (`Posed`), the joint and turn errors one Warp
kernel each in float64, the winding test Warp's mesh query on the card over every EVERY-th frame against the skin posed once per case
(`Skins`: identical each evaluation); medians on the host from the per-frame arrays, as the CPU's `summary`.
Newton's Python (mujoco, warp) and a CUDA card."""
import mujoco
import numpy as np
import warp

from evaluation import _measure as cpu
from fit._frozen import frozen_turn
from fit._skin import EVERY, HAND, bone_meshes, bone_points, region, skin as skinned
from model import TO_OWN

DEVICE = "cuda:0"


@warp.kernel
def _joint_errors(xpos: warp.array2d(dtype=warp.vec3d), xmat: warp.array2d(dtype=warp.mat33d),
                  bodies: warp.array2d(dtype=int), locals_: warp.array2d(dtype=warp.vec3d),
                  wanted: warp.array2d(dtype=warp.vec3d), out: warp.array2d(dtype=warp.float64)):
    frame, joint = warp.tid()
    first, second = bodies[joint, 0], bodies[joint, 1]
    placed = warp.float64(0.5) * (xpos[frame, first] + xmat[frame, first] @ locals_[joint, 0]
                    + xpos[frame, second] + xmat[frame, second] @ locals_[joint, 1])
    out[frame, joint] = warp.float64(1000.0) * warp.length(placed - wanted[frame, joint])


@warp.kernel
def _turn_errors(xmat: warp.array2d(dtype=warp.mat33d), bodies: warp.array(dtype=int),
                 wanted: warp.array2d(dtype=warp.mat33d), out: warp.array2d(dtype=warp.float64)):
    frame, group = warp.tid()
    rel = warp.transpose(xmat[frame, bodies[group]]) @ wanted[frame, group]
    cosine = warp.clamp(warp.float64(0.5) * (warp.trace(rel) - warp.float64(1.0)), warp.float64(-1.0), warp.float64(1.0))
    out[frame, group] = warp.degrees(warp.acos(cosine))


@warp.kernel
def _outside(meshes: warp.array(dtype=warp.uint64), points: warp.array2d(dtype=warp.vec3),
             out: warp.array2d(dtype=float)):
    shot, point = warp.tid()
    out[shot, point] = warp.mesh_query_point_sign_winding_number(meshes[shot], points[shot, point], 1.0e6, 2.0,
                                                                 0.5).sign


class Skins:
    """SOMA's skin posed on every EVERY-th frame of one case, each a Warp mesh on the card (posed once per case)."""

    def __init__(self, rig, segments, worlds):
        self.frames = np.arange(0, len(worlds), EVERY)
        faces = warp.array(np.asarray(rig["faces"], dtype=np.int32).ravel(), dtype=int, device=DEVICE)
        self.meshes = [warp.Mesh(points=warp.array(skinned(rig, segments, worlds[frame]).astype(np.float32),
                                                   dtype=warp.vec3, device=DEVICE), indices=faces)
                       for frame in self.frames]
        self.ids = warp.array(np.array([mesh.id for mesh in self.meshes], dtype=np.uint64), dtype=warp.uint64,
                              device=DEVICE)


class Posed:
    """Every frame's body and geom poses by MuJoCo's own float64 kinematics on the host (the CPU measure's; MuJoCo
    Warp's float32 moved a deep group's turn 0.001 deg and a bone vertex across the skin, 2026-10-29), the body poses
    on the card in float64, and the kept bone vertices of the skin frames as `fit._skin.bone_points` places them."""

    def __init__(self, model, angles, frames):
        data, meshes = mujoco.MjData(model), bone_meshes(model)
        xpos, xmat, points = [], [], []
        for frame, qpos in enumerate(angles):
            data.qpos[:] = qpos
            mujoco.mj_kinematics(model, data)
            xpos.append(data.xpos.copy())
            xmat.append(data.xmat.reshape(-1, 3, 3).copy())
            if frame in frames:
                own, self.bones = bone_points(model, data, meshes)
                points.append(own)
        self.xpos = warp.array(np.array(xpos), dtype=warp.vec3d, device=DEVICE)
        self.xmat = warp.array(np.array(xmat), dtype=warp.mat33d, device=DEVICE)
        self.points = warp.array(np.array(points, dtype=np.float32), dtype=warp.vec3, device=DEVICE)


def joint_table(model, joints, scales):
    """Each measured joint's two (body, local offset) parts in MuJoCo's frame (a single centre twice, a middle its
    two ends), as `evaluation._measure.centre` reads them."""
    def part(name):
        bone, local = cpu.CENTRES[name]
        return cpu.body(model, bone), np.asarray(local, dtype=float) * scales[bone]
    pairs = [[part(name) for name in cpu.MIDDLE.get(cpu.JOINTS[segment], (cpu.JOINTS[segment],) * 2)]
             for segment in joints]
    return (np.array([[body for body, _ in pair] for pair in pairs], dtype=np.int32),
            np.array([[local for _, local in pair] for pair in pairs], dtype=float))


def joint_errors(model, data, worlds, segments, scales):
    """{segment: [mm per frame]}: each SOMA joint's miss, MyoFullBody's centre against SOMA's joint."""
    joints = [segment for segment in cpu.JOINTS if segment in segments]
    bodies, locals_ = joint_table(model, joints, scales)
    wanted = np.asarray(worlds)[:, [segments.index(segment) for segment in joints]][..., :3, 3] @ TO_OWN
    out = warp.zeros((len(worlds), len(joints)), dtype=warp.float64, device=DEVICE)
    warp.launch(_joint_errors, dim=out.shape, device=DEVICE,
                inputs=[data.xpos, data.xmat, warp.array(bodies, dtype=int, device=DEVICE),
                        warp.array(locals_, dtype=warp.vec3d, device=DEVICE),
                        warp.array(wanted, dtype=warp.vec3d, device=DEVICE), out])
    return dict(zip(joints, out.numpy().T.astype(float)))


def turn_errors(model, data, worlds, segments):
    """{segment: [deg per frame]}: each bone group's rotation off SOMA's segment on the frozen table."""
    groups = [segment for segment in segments if segment in cpu.FRAME_BODY]
    bodies = np.array([cpu.body(model, cpu.FRAME_BODY[segment]) for segment in groups], dtype=np.int32)
    turned = np.stack([TO_OWN.T @ np.asarray(worlds)[:, segments.index(segment), :3, :3] @ frozen_turn(segment)
                       for segment in groups], axis=1)
    out = warp.zeros((len(worlds), len(groups)), dtype=warp.float64, device=DEVICE)
    warp.launch(_turn_errors, dim=out.shape, device=DEVICE,
                inputs=[data.xmat, warp.array(bodies, dtype=int, device=DEVICE),
                        warp.array(turned, dtype=warp.mat33d, device=DEVICE), out])
    return dict(zip(groups, out.numpy().T.astype(float)))


def outside_marks(data, skins):
    """[skin frames x points] whether each kept bone vertex is outside the skin posed on that frame."""
    out = warp.zeros(data.points.shape, dtype=float, device=DEVICE)
    warp.launch(_outside, dim=out.shape, device=DEVICE, inputs=[skins.ids, data.points, out])
    return out.numpy() >= 0


def skin_shares(marks, bones):
    """{label: [share per skin frame]} of the bone vertices outside, the hand's parts as one ("hand")."""
    parts = np.array([region(bone) for bone in bones])
    labels = np.where(np.isin(parts, HAND), "hand", parts)
    return {label: [float(shot[labels == label].mean()) for shot in marks] for label in set(labels)}


def measures(model, angles, rig, segments, worlds, scales, skins=None):
    """The score's measures of one fitted clip, keyed and summarised as `evaluation._measure.measures`."""
    skins = skins or Skins(rig, segments, worlds)
    data = Posed(model, angles, set(skins.frames.tolist()))
    joints = joint_errors(model, data, worlds, segments, scales)
    turns = turn_errors(model, data, worlds, segments)
    outside = skin_shares(outside_marks(data, skins), data.bones)
    return {"joints mm": cpu.summary(np.concatenate(list(joints.values()))),
            "per joint mm": {key: cpu.summary(value)[:2] for key, value in joints.items()},
            "turns deg": cpu.summary(np.concatenate(list(turns.values()))),
            "per group deg": {key: cpu.summary(value)[:2] for key, value in turns.items()},
            "bones outside skin %": {key: 100 * float(np.mean(value)) for key, value in outside.items()},
            "bones outside all %": 100 * float(np.mean(sum(outside.values(), [])))}

