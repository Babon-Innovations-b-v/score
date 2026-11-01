"""Measures the static calibration table again and prints it as `TABLE` (Newton's own Python: MuJoCo and Newton):

    <env>/bin/python score/stages/sim_body/inside/calibration/_measure.py <model folder> <SOMA template rig.npz>

<model folder>: the fetched MyoFullBody ($PROPS_HOME/models/<sha>); <rig.npz>: people-clips-make's template rig. Each
bone group's stretch on SOMA's bind (`landmarks.soma_point`) and on MyoFullBody at its default pose
(`landmarks.myo_parts`), each reference axis (`REFERENCES`: a landmark line on SOMA's template skin and between
MyoFullBody's bone points), then `aligned`. The MyoFullBody reference is turned to agree in sign with SOMA's. Then `FINGERS` (`fingers_measured`, on
the table as it stands in `TABLE`: paste the turns first, then measure again)."""
import pathlib
import sys

import mujoco
import numpy as np
import warp

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bone_groups import groups, sided_map  # noqa: E402
import calibration  # noqa: E402
from calibration import REFERENCES, aligned  # noqa: E402
from landmarks import LANDMARKS, myo_parts, on_skin, soma_point  # noqa: E402
from model import TO_OWN, Couplings, default_pose  # noqa: E402
from myo import SOURCE  # noqa: E402

OWN = {"own x": np.array([1.0, 0.0, 0.0]), "own y": np.array([0.0, 1.0, 0.0])}


def myo_point(model, data, parts):
    """Weighted MyoFullBody body points (`myo_parts`' form) in the person's frame at the default pose."""
    found = np.zeros(3)
    for body, local, weight in parts:
        index = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body)
        found += weight * (data.xpos[index] + data.xmat[index].reshape(3, 3) @ np.asarray(local))
    return TO_OWN @ found


def bone_point(landmark):
    """A landmark's bone point in `myo_parts`' form (its MyoFullBody body, the body-local point, weight 1)."""
    return [(LANDMARKS[landmark][3], LANDMARKS[landmark][4], 1.0)]


def soma_reference(name, rig):
    """A reference axis on SOMA's bind: an own axis, or a landmark line on the template's skin."""
    if name in OWN:
        return OWN[name]
    start, end = name.split()[1:]
    skin = on_skin(rig["points"], rig["faces"])
    return skin[end] - skin[start]


def myo_reference(name, model, data):
    """A reference axis on MyoFullBody at its default pose: an own axis, or a landmark line between bone points."""
    if name in OWN:
        return OWN[name]
    start, end = name.split()[1:]
    return myo_point(model, data, bone_point(end)) - myo_point(model, data, bone_point(start))


def measured(folder, rig_path):
    """{group: R_cal quaternion (x, y, z, w)}."""
    model = mujoco.MjModel.from_xml_path(f"{folder}/{SOURCE}")
    data = default_pose(model, Couplings(model))
    rig = dict(np.load(rig_path))
    names = [str(joint) for joint in rig["names"]]
    references = sided_map(REFERENCES)
    found = {}
    for segment, ((start, end), (myo_start, myo_end), frame_body, _) in groups().items():
        soma_ref, myo_ref = references[segment]
        soma_axis = soma_reference(soma_ref, rig)
        myo_axis = myo_reference(myo_ref, model, data)
        myo_axis = myo_axis * (1.0 if myo_axis @ soma_axis >= 0 else -1.0)
        segment_turn = rig["bind"][names.index(segment), :3, :3]
        body = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, frame_body)
        body_turn = TO_OWN @ data.xmat[body].reshape(3, 3)
        found[segment] = aligned(
            (segment_turn, soma_point(end, rig) - soma_point(start, rig), soma_axis),
            (body_turn, myo_point(model, data, myo_parts(myo_end)) - myo_point(model, data, myo_parts(myo_start)), myo_axis))
    from scipy.spatial.transform import Rotation
    return {segment: Rotation.from_matrix(turn).as_quat() for segment, turn in found.items()}


DEEP = 0.010  # metres: deeper than any finger's flesh holds its bone, so every finger bone vertex pulls (centred)


def fingers_measured(folder, rig_path, kg=70.0):
    """{joint stem: rest turn}: MyoFullBody sized to SOMA's template (its file at FINGERS as they stand), each hand laid
    on the template's bind by `calibration.turn` at its Hand joint, and the finger and thumb joints of both hands (one
    turn a stem, both sides alike) solved by scipy's bounded `least_squares` within their ranges so each finger bone
    vertex (`_skin.bone_meshes`' kept ones) stands DEEP inside SOMA's skin (the shortfall its residual: the bones as
    deep in the flesh as they go); the found turns added to FINGERS'."""
    import tempfile

    from scipy.optimize import least_squares

    import myo
    from fit import _skin
    from sizing import Size
    rig = dict(np.load(rig_path))
    path = pathlib.Path(tempfile.mkdtemp()) / "template.xml"
    myo.person_file(folder, Size(rig), kg, path)
    model = mujoco.MjModel.from_xml_path(str(path))
    hands = [_hand(model, rig, side) for side in ("Left", "Right")]
    stems = sorted({stem for hand in hands for stem in hand["stems"]})
    lower = np.max([[hand["range"][stem][0] for stem in stems] for hand in hands], axis=0)
    upper = np.min([[hand["range"][stem][1] for stem in stems] for hand in hands], axis=0)
    mesh = warp.Mesh(points=warp.array(rig["points"].astype(np.float32), dtype=warp.vec3, device="cpu"),
                     indices=warp.array(rig["faces"].astype(np.int32).ravel(), dtype=int, device="cpu"),
                     support_winding_number=True)
    data, meshes = mujoco.MjData(model), _skin.bone_meshes(model)
    rest = default_pose(model, Couplings(model)).qpos.copy()

    def shortfall(turns):
        found = []
        for hand in hands:
            data.qpos[:] = rest
            data.qpos[[hand["address"][stem] for stem in stems]] = turns
            mujoco.mj_kinematics(model, data)
            points, bones = _skin.bone_points(model, data, meshes)
            kept = np.isin(bones, hand["fingers"])
            found.append(DEEP - _depth_inside(mesh, _laid(points[kept], data, hand)))
        return np.maximum(0.0, np.concatenate(found))
    start = np.clip(np.zeros(len(stems)), lower + 0.02, upper - 0.02)
    solved = least_squares(shortfall, start, bounds=(lower, upper), diff_step=1e-3, x_scale=0.1)
    return {stem: round(calibration.FINGERS.get(stem, 0.0) + float(turn), 4) for stem, turn in zip(stems, solved.x)}


def _hand(model, rig, side):
    """One hand's finger bodies (the Hand group's bodies but its frame body and the carpals), their hinges by stem
    (address, range), its frame body and its lay on SOMA's bind (turn, SOMA's Hand joint)."""
    segment = f"{side}Hand"
    (start, _), _, frame_body, bodies = groups()[segment]
    fingers = [body for body in bodies if "ph" in body or "thumb" in body or body.startswith("firstmc")]
    stems, address, ranges = [], {}, {}
    for joint in range(model.njnt):
        name = model.joint(joint).name
        if model.jnt_type[joint] == mujoco.mjtJoint.mjJNT_HINGE and any(
                model.body(model.jnt_bodyid[joint]).name.startswith(body) for body in fingers):
            stem = name[:-2]
            stems.append(stem)
            address[stem], ranges[stem] = model.jnt_qposadr[joint], model.jnt_range[joint]
    names = [str(joint) for joint in rig["names"]]
    return {"stems": stems, "address": address, "range": ranges, "fingers": fingers,
            "frame": mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, frame_body),
            "turn": rig["bind"][names.index(segment), :3, :3] @ calibration.turn(segment),
            "start": soma_point(start, rig)}


def _laid(points, data, hand):
    """Bone points (the person's frame) laid on SOMA's bind: the hand's frame body at SOMA's Hand joint, turned by the
    table."""
    body_turn = TO_OWN @ data.xmat[hand["frame"]].reshape(3, 3)
    return hand["start"] + (points - TO_OWN @ data.xpos[hand["frame"]]) @ body_turn @ hand["turn"].T


@warp.kernel
def _inside_kernel(mesh: warp.uint64, points: warp.array(dtype=warp.vec3), depths: warp.array(dtype=float)):
    """Each point's distance to the mesh's closest point, inside positive (the exact winding number's side)."""
    index = warp.tid()
    found = warp.mesh_query_point_sign_winding_number(mesh, points[index], 1.0e6, 2.0, 0.5)
    closest = warp.mesh_eval_position(mesh, found.face, found.u, found.v)
    depths[index] = -found.sign * warp.length(points[index] - closest)


def _depth_inside(mesh, points):
    """Each point's depth inside the closed mesh (m, outside negative)."""
    depths = warp.zeros(len(points), dtype=float, device="cpu")
    warp.launch(_inside_kernel, dim=len(points), device="cpu",
                inputs=[mesh.id, warp.array(np.asarray(points, dtype=np.float32), dtype=warp.vec3, device="cpu"), depths])
    return depths.numpy().astype(float)


if __name__ == "__main__":
    for group, quaternion in measured(*sys.argv[1:3]).items():
        print(f'    "{group}": ({", ".join(f"{value:.6g}" for value in quaternion)}),')
    for stem, turn in fingers_measured(*sys.argv[1:3]).items():
        print(f'    "{stem}": {turn},')
