"""The honest measures of following SOMA (#70), from one fitted clip: each SOMA joint's position error (MyoFullBody's
joint centre against SOMA's joint, mm), each bone group's rotation error on the FROZEN calibration copy (fit._frozen,
deg), the share of bone vertices outside SOMA's posed skin by region (every EVERY-th frame), and beside them tip,
length and floor readings. Never a landmark distance the solver pulls on. The skin, the winding test, the regions and
the frozen table are the stage's own (fit._skin, fit._frozen), so the record and level 1's score are one code. Every
value is unrounded (the solver's); `evaluation.rounded` makes the copy people read (m.json).
Newton's Python (mujoco, warp)."""
import mujoco
import numpy as np
from scipy.spatial import cKDTree

from contact import surface
from fit._frozen import frozen_turn
from fit._skin import EVERY, HAND, bone_meshes, bone_points, outside as outside_skin, region, skin as skinned
from landmarks import soma_point
from model import TO_OWN


# frozen from origin/main 5a46a96e landmarks._table.CENTRES and bone_groups: SOMA joint -> MyoFullBody centre parts;
# level 1's worker moves each group end's by the evaluation's offset (`_case.load_centres`), as the fit's own
CENTRES = {
    "hip_l": ("femur_l", (0, 0, 0)), "knee_l": ("tibia_l", (0, 0, 0)), "ankle_l": ("talus_l", (0, 0, 0)),
    "mtp_l": ("toes_l", (0, 0, 0)), "sternoclavicular_l": ("clavicle_l", (0, 0, 0)),
    "glenohumeral_l": ("humerus_l", (0, 0, 0)), "elbow_l": ("ulna_l", (0, 0, 0)), "wrist_l": ("lunate_l", (0, 0, 0)),
    "hip_r": ("femur_r", (0, 0, 0)), "knee_r": ("tibia_r", (0, 0, 0)), "ankle_r": ("talus_r", (0, 0, 0)),
    "mtp_r": ("toes_r", (0, 0, 0)), "sternoclavicular_r": ("clavicle_r", (0, 0, 0)),
    "glenohumeral_r": ("humerus_r", (0, 0, 0)), "elbow_r": ("ulna_r", (0, 0, 0)), "wrist_r": ("lunate_r", (0, 0, 0)),
    "L5_S1": ("lumbar5", (0, 0, 0)), "L3_L4": ("lumbar3", (0, 0, 0)),
    "C7_T1": ("torso", (-0.03192, 0.39675, 0.00031)), "C0_C1": ("head", (-0.00763, 0.00738, 0.00005)),
    "T12_L1": ("torso", (-0.01368, 0.11893, 0.00045)),
    "finger_tip_l": ("3distph_l", (0.00112, -0.01854, -0.00137)),
    "finger_tip_r": ("3distph_r", (0.00112, -0.01854, 0.00137)),
    "toe_tip_l": ("toes_l", (0.07692, -0.003, 0.0155)), "toe_tip_r": ("toes_r", (0.07692, -0.003, -0.0155)),
    "head_vertex": ("head", (-0.00767, 0.15057, 0)),
}
MIDDLE = {"mid_cervical": ("C7_T1", "C0_C1")}
JOINTS = {"Spine1": "L5_S1", "Spine2": "L3_L4", "Chest": "T12_L1", "Neck1": "C7_T1", "Neck2": "mid_cervical",
          "Head": "C0_C1"}
for side, letter in (("Left", "l"), ("Right", "r")):
    JOINTS.update({f"{side}Shoulder": f"sternoclavicular_{letter}", f"{side}Arm": f"glenohumeral_{letter}",
                   f"{side}ForeArm": f"elbow_{letter}", f"{side}Hand": f"wrist_{letter}",
                   f"{side}Leg": f"hip_{letter}", f"{side}Shin": f"knee_{letter}", f"{side}Foot": f"ankle_{letter}",
                   f"{side}ToeBase": f"mtp_{letter}"})
# tips: SOMA end joint carried rigidly by its segment, MyoFullBody point
TIPS = {"LeftToeEnd": ("LeftToeBase", "toe_tip_l"), "RightToeEnd": ("RightToeBase", "toe_tip_r"),
        "HeadEnd": ("Head", "head_vertex")}
FRAME_BODY = {"Hips": "pelvis", "Spine1": "lumbar4", "Spine2": "lumbar1", "Chest": "torso", "Neck1": "neck",
              "Neck2": "neck", "Head": "head"}
for side, letter in (("Left", "l"), ("Right", "r")):
    FRAME_BODY.update({f"{side}Shoulder": f"scapula_{letter}", f"{side}Arm": f"humerus_{letter}",
                       f"{side}ForeArm": f"ulna_{letter}", f"{side}Hand": f"lunate_{letter}",
                       f"{side}Leg": f"femur_{letter}", f"{side}Shin": f"tibia_{letter}",
                       f"{side}Foot": f"calcn_{letter}", f"{side}ToeBase": f"toes_{letter}"})


def body(model, name):
    return mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name.replace("-", "_").replace(" ", "_"))


def centre(model, data, name, scales):
    if name in MIDDLE:
        return sum(centre(model, data, part, scales) for part in MIDDLE[name]) / 2
    bone, local = CENTRES[name]
    index = body(model, bone)
    return data.xpos[index] + data.xmat[index].reshape(3, 3) @ (np.asarray(local) * scales[bone])


def summary(values):
    values = np.asarray(values, dtype=float)
    return [float(np.median(values)), float(np.percentile(values, 95)), float(values.max())]


def measures(model, angles, rig, segments, worlds, scales):
    data = mujoco.MjData(model)
    names = [str(joint) for joint in rig["names"]]
    bind = np.asarray(rig["bind"], dtype=float)
    colliders = [geom for geom in range(model.ngeom) if model.geom_contype[geom] or model.geom_conaffinity[geom]]
    joints = {segment: [] for segment in JOINTS if segment in segments}
    tips = {tip: [] for tip in TIPS}
    hand = {side: [] for side in ("Left", "Right")}
    turns = {segment: [] for segment in segments if segment in FRAME_BODY}
    lowest, skin_lowest, outside, depth, by_bone, hand_parts, no_fingers = [], [], {}, {}, {}, {}, {}
    faces, meshes = np.asarray(rig["faces"]), bone_meshes(model)
    hand_tips = {side: soma_point(f"{side}Hand tip", rig) for side in hand}
    for frame, (qpos, world) in enumerate(zip(angles, worlds)):
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        for segment in joints:
            placed = TO_OWN @ centre(model, data, JOINTS[segment], scales)
            joints[segment].append(1000 * np.linalg.norm(placed - world[segments.index(segment)][:3, 3]))
        for tip, (segment, myo) in TIPS.items():
            seg = world[segments.index(segment)] @ np.linalg.inv(bind[names.index(segment)])
            soma = seg[:3, :3] @ bind[names.index(tip), :3, 3] + seg[:3, 3]
            tips[tip].append(1000 * np.linalg.norm(TO_OWN @ centre(model, data, myo, scales) - soma))
        for side in hand:
            seg = world[segments.index(f"{side}Hand")] @ np.linalg.inv(bind[names.index(f"{side}Hand")])
            soma = seg[:3, :3] @ hand_tips[side] + seg[:3, 3]
            hand[side].append(1000 * np.linalg.norm(
                TO_OWN @ centre(model, data, f"finger_tip_{side[0].lower()}", scales) - soma))
        for segment in turns:
            seen = TO_OWN @ data.xmat[body(model, FRAME_BODY[segment])].reshape(3, 3) @ frozen_turn(segment).T
            wanted = world[segments.index(segment)][:3, :3]
            turns[segment].append(np.degrees(np.arccos(np.clip((np.trace(seen.T @ wanted) - 1) / 2, -1, 1))))
        low = float((surface(model, data, colliders) @ TO_OWN.T)[:, 1].min())
        skin = skinned(rig, segments, world)
        lowest.append(1000 * low)
        skin_lowest.append(1000 * float(skin[:, 1].min()))
        if frame % EVERY == 0:
            own, bones = bone_points(model, data, meshes)
            parts = np.array([region(bone) for bone in bones])
            labels = np.where(np.isin(parts, HAND), "hand", parts)  # the score's regions: the hand as one
            unbent = labels != "hand"
            unbent |= np.isin(parts, ("carpals", "metacarpals"))
            out = outside_skin(own, skin, faces)
            tree = cKDTree(skin)
            far, _ = tree.query(own[out]) if out.any() else (np.zeros(0), None)
            for label in set(labels):
                mine = labels == label
                outside.setdefault(label, []).append(float(out[mine].mean()))
                depth.setdefault(label, []).extend((1000 * far[labels[out] == label]).tolist())
            for part in HAND:
                hand_parts.setdefault(part, []).append(float(out[parts == part].mean()))
            for label in set(labels):
                mine = (labels == label) & unbent
                no_fingers.setdefault(label, []).append(float(out[mine].mean()))
            for bone in set(bones):
                by_bone.setdefault(bone, []).append(float(out[bones == bone].mean()))
    segs = {"LeftLeg": ("hip_l", "knee_l", "LeftShin"), "LeftShin": ("knee_l", "ankle_l", "LeftFoot"),
            "LeftArm": ("glenohumeral_l", "elbow_l", "LeftForeArm"), "LeftForeArm": ("elbow_l", "wrist_l", "LeftHand"),
            "LeftFoot": ("ankle_l", "mtp_l", "LeftToeBase")}
    segs.update({key.replace("Left", "Right"): (a[:-1] + "r", b[:-1] + "r", c.replace("Left", "Right"))
                 for key, (a, b, c) in list(segs.items())})
    data.qpos[:] = angles[0]
    mujoco.mj_kinematics(model, data)
    long = {key: 1000 * float(np.linalg.norm(centre(model, data, b, scales) - centre(model, data, a, scales))
                              - np.linalg.norm(bind[names.index(c), :3, 3] - bind[names.index(key), :3, 3]))
            for key, (a, b, c) in segs.items()}
    free = sum(joints.values(), [])
    return {"joints mm": summary(free), "per joint mm": {key: summary(value)[:2] for key, value in joints.items()},
            "turns deg": summary(sum(turns.values(), [])),
            "per group deg": {key: summary(value)[:2] for key, value in turns.items()},
            "joint length over SOMA mm": long, "tips mm": {key: summary(value)[:2] for key, value in tips.items()},
            "hand tips mm": {key: summary(value)[:2] for key, value in hand.items()},
            "lowest collider mm": [float(np.median(lowest)), float(np.min(lowest))],
            "skin lowest mm": [float(np.median(skin_lowest)), float(np.min(skin_lowest))],
            "collider under skin mm": float(np.median(np.array(skin_lowest) - np.array(lowest))),
            "bones outside skin %": {key: 100 * float(np.mean(value)) for key, value in outside.items()},
            "outside depth p95 mm": {key: float(np.percentile(value, 95)) if value else 0.0
                                     for key, value in depth.items()},
            "bones outside all %": 100 * float(np.mean(sum(outside.values(), []))),
            "hand parts outside %": {key: 100 * float(np.mean(value)) for key, value in hand_parts.items()},
            "bones outside no fingers %": 100 * float(np.mean(sum(no_fingers.values(), []))),
            "bones outside by bone %": {key: 100 * float(np.mean(value)) for key, value in by_bone.items()}}


