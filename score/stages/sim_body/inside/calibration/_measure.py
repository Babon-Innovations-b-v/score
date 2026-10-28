"""Measures the static calibration table again and prints it as `TABLE` (Newton's own Python: MuJoCo and Newton):

    <env>/bin/python score/stages/sim_body/inside/calibration/_measure.py <model folder> <SOMA template rig.npz>

<model folder>: the fetched MyoFullBody ($PROPS_HOME/models/<sha>); <rig.npz>: people-clips-make's template rig. Each
bone group's stretch on SOMA's bind (`landmarks.soma_point`) and on MyoFullBody at its default pose
(`landmarks.myo_parts`), each reference axis (`REFERENCES`), then `aligned`. The MyoFullBody reference is turned to
agree in sign with SOMA's."""
import pathlib
import sys

import mujoco
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bone_groups import groups, sided_map  # noqa: E402
from calibration import REFERENCES, aligned  # noqa: E402
from landmarks import MARKS, myo_parts, soma_point  # noqa: E402
from model import TO_OWN, Couplings, default_pose  # noqa: E402
from myo import SOURCE  # noqa: E402

OWN = {"own x": np.array([1.0, 0.0, 0.0]), "own y": np.array([0.0, 1.0, 0.0])}


def myo_point(model, data, name):
    """A MyoFullBody centre or landmark bone point in the person's frame at the default pose."""
    parts = myo_parts(name) if name not in MARKS else [(MARKS[name][3], MARKS[name][4], 1.0)]
    found = np.zeros(3)
    for body, local, weight in parts:
        index = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body)
        found += weight * (data.xpos[index] + data.xmat[index].reshape(3, 3) @ np.asarray(local))
    return TO_OWN @ found


def soma_reference(name, segment, rig):
    names = [str(joint) for joint in rig["names"]]
    if name in OWN:
        return OWN[name]
    if name == "radial":
        side = segment[:-len("Hand")]
        return rig["bind"][names.index(segment), :3, 1] * (1.0 if side == "Left" else -1.0)
    return rig["bind"][names.index(name[len("z of "):]), :3, 2]


def myo_reference(name, segment, model, data):
    if name in OWN:
        return OWN[name]
    if name == "radial":
        letter = segment[0].lower()
        return myo_point(model, data, f"MC2_head_{letter}") - myo_point(model, data, f"MC5_head_{letter}")
    return TO_OWN @ data.xaxis[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name[len("axis of "):])]


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
        soma_axis = soma_reference(soma_ref, segment, rig)
        myo_axis = myo_reference(myo_ref, segment, model, data)
        myo_axis = myo_axis * (1.0 if myo_axis @ soma_axis >= 0 else -1.0)
        segment_turn = rig["bind"][names.index(segment), :3, :3]
        body = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, frame_body)
        body_turn = TO_OWN @ data.xmat[body].reshape(3, 3)
        found[segment] = aligned(
            (segment_turn, soma_point(end, rig) - soma_point(start, rig), soma_axis),
            (body_turn, myo_point(model, data, myo_end) - myo_point(model, data, myo_start), myo_axis))
    from scipy.spatial.transform import Rotation
    return {segment: Rotation.from_matrix(turn).as_quat() for segment, turn in found.items()}


if __name__ == "__main__":
    for group, quaternion in measured(*sys.argv[1:3]).items():
        print(f'    "{group}": ({", ".join(f"{value:.6g}" for value in quaternion)}),')
