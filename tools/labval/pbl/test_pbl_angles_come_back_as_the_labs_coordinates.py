"""labval.pbl: a synthetic PBL result built from known lab angles, seen by a camera tilted 12 degrees down and rolled 4
(its pelvis turned into the camera's OpenCV axes as PBL's static-camera world holds it, its knees with gait2392's
negative flexion), comes back as those lab angles: every mapped coordinate to 1e-9 degrees, the pelvis' tilt, list
and rotation too once levelled on the camera's true up and put on the lab's heading; on the camera's own -y instead,
the pelvis' list (the lab's forward is the camera's right) is off by about the camera's pitch. A cluster job gives on_pbl.py the video's camera as GEM-X's K.
Synthetic inputs only: no number here is a result.

Breaks, each applied once, seen red, reverted (2026-11-08):
- score.MAPPED's knee sign made 1.0: the knees come back negated, far over 1e-9.
- score.coordinates' `least_turn(up, +y)` made `least_turn(+y, up)`: the pelvis comes back over 1e-9 off.
- cluster.job's fx and fy swapped for cx and cy: the job's --video carries 360 where it should carry 931.5."""
import pathlib

import numpy as np
from scipy.spatial.transform import Rotation

from tools.labval import _run
from tools.labval.pbl import cluster, score


def test_pbl_angles_come_back_as_the_labs_coordinates():
    frames = 30
    phase = np.linspace(0.0, 2.0 * np.pi, frames)
    lab = {name: 20.0 * np.sin(phase + index) + index for index, name in enumerate(score.MAPPED)}
    pelvis_angles = np.stack([10.0 * np.sin(phase), 4.0 * np.cos(phase), 30.0 + 5.0 * np.sin(2 * phase)], axis=1)
    lab_turns = Rotation.from_euler("ZXY", pelvis_angles, degrees=True).as_matrix()
    # The lab (y up) seen by an OpenCV camera (y down, z forward) pitched 12 degrees down and rolled 4.
    camera_of_lab = Rotation.from_euler("xz", [-12.0, 4.0], degrees=True).as_matrix() @ np.diag([1.0, -1.0, -1.0])
    joints = [name for name in ("pelvis_tx", "pelvis_tz", "pelvis_ty", "pelvis_tilt", "pelvis_list",
                                "pelvis_rotation")] + [joint for joint, _ in score.MAPPED.values()] + ["wrist_flex_r"]
    qpos = np.zeros((frames, len(joints)))
    for name, (joint, _) in score.MAPPED.items():  # PBL's knee flexion is negative (gait2392's), the lab's positive
        qpos[:, joints.index(joint)] = np.radians(lab[name]) * (-1.0 if name.startswith("knee") else 1.0)
    saved = {"joint_names": np.array(joints), "qpos": qpos,
             "pelvis_turns": np.einsum("ab,fbc->fac", camera_of_lab, lab_turns)}
    true_up = camera_of_lab @ np.array([0.0, 1.0, 0.0])
    found = score.coordinates(saved, true_up, _run.heading(lab_turns))
    assert set(found) == {*score.MAPPED, *_run.PELVIS}
    worst = max(np.abs(found[name] - lab[name]).max() for name in score.MAPPED)
    pelvis = np.abs(np.stack([found[name] for name in _run.PELVIS], axis=1) - pelvis_angles).max()
    level = score.coordinates(saved, score.CAMERA_UP, _run.heading(lab_turns))
    pitch_off = np.median(np.abs(level["pelvis_list"] - pelvis_angles[:, 1]))  # the lab's x is the camera's
    spec = cluster.job([(("subject2", "walking1", "Cam1", "labvalidation/subject2/Cam1/walking1.mp4"),
                         pathlib.Path("/out/subject2_walking1_Cam1"),
                         np.array([[931.5, 0.0, 360.0], [0.0, 931.5, 640.0], [0.0, 0.0, 1.0]]))])
    given = spec["command"][2]
    assert (worst < 1e-9, pelvis < 1e-9, 8.0 < pitch_off < 16.0,
            "/work/labvalidation/subject2/Cam1/walking1.mp4=931.5000=931.5000=360.0000=640.0000" in given,
            spec["inputs"][0]["key"]) == (True, True, True, True, "labvalidation/subject2/Cam1/walking1.mp4"), (
        worst, pelvis, pitch_off, given)
