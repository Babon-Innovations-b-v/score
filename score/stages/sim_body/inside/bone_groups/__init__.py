"""Which MyoFullBody body each SOMA segment rides, which segments the fit follows, the hips that place the pelvis, the
feet, the trunk's lumbar leaders and what MyoFullBody lacks, and the bone groups (`GROUPS`: each SOMA segment's
MyoFullBody bodies between the same start and end joint; pure: no MuJoCo, no Newton); `sided` and `sided_map` write
a `{Side}`/`{side}` name out for both sides."""
FEET = ("Foot", "ToeBase")
# Each SOMA segment and the MyoFullBody body it rides ({side} its side's letter); the first carries the pelvis.
RIDES = {"Hips": "pelvis", "Spine1": "lumbar4", "Spine2": "lumbar2", "Chest": "torso", "Neck1": "head",
         "Neck2": "head", "Head": "head", "{Side}Shoulder": "clavicle_{side}", "{Side}Arm": "humerus_{side}",
         "{Side}ForeArm": "ulna_{side}", "{Side}Hand": "lunate_{side}", "{Side}Leg": "femur_{side}",
         "{Side}Shin": "tibia_{side}", "{Side}Foot": "calcn_{side}", "{Side}ToeBase": "toes_{side}"}
# The segments the fit follows, each a virtual orientation sensor on the body it rides (OpenSense's IMUs, weight 1
# each); the rest ride their bodies: MyoFullBody has no joint of its own for them.
TARGETS = ("Hips", "Chest", "{Side}Arm", "{Side}ForeArm", "{Side}Hand", "{Side}Leg", "{Side}Shin", "{Side}Foot",
           "{Side}ToeBase")
LACKS = {"Spine1, Spine2": "one lumbar joint spread over its five levels by the model's couplings",
         "Neck1, Neck2, Head": "MyoFullBody's head and neck are rigid on its thorax",
         "{Side}Shoulder": "the clavicle and scapula follow the arm's elevation (the model's shoulder rhythm)",
         "{Side}Shin, {Side}Foot, {Side}ToeBase": "the knee, ankle, subtalar and toe joints are hinges"}
# The hip joints, whose middle places the pelvis on SOMA's at calibration: each SOMA leg segment and its femur.
HIPS = {"LeftLeg": "femur_l", "RightLeg": "femur_r"}
# The lumbar leaders the residual reduction moves with the pelvis (the owner's: "adjust the pelvis and trunk path
# slightly"), by the ends of their joint names.
TRUNK = ("flex_extension", "lat_bending", "axial_rotation")


# The bone groups (#70; CONTEXT.md "bone group"): each SOMA segment, its stretch on SOMA (start and end: a rig joint,
# `hipmid` the hip joints' middle, `<Side>Hand tip` the hand mesh's far end) and on MyoFullBody (the same two joint
# centres: landmarks.CENTRES), the body whose frame stands for the group (the one holding the end joint; the forearm
# the ulna, as SOMA's forearm does not pronate) and the MyoFullBody bodies of its stretch (source model names). Spine levels
# paired by each joint's share of the height from the hip joints' middle to C7/T1 (SOMA Spine1 0.247 ~ L5/S1 0.255,
# Spine2 0.380 ~ L3/L4 0.366, Chest 0.514 ~ T12/L1 0.526; measured 2026-10-28 on the source model and SOMA's template
# rig). Neck2 has no body of its own: MyoFullBody's neck is one rigid body, so Neck1's carries both.
_HAND = ("lunate", "scaphoid", "pisiform", "triquetrum", "capitate", "trapezium", "trapezoid", "hamate", "firstmc",
         "secondmc", "thirdmc", "fourthmc", "fifthmc", "proximal_thumb", "distal_thumb", "2proxph", "2midph",
         "2distph", "3proxph", "3midph", "3distph", "4proxph", "4midph", "4distph", "5proxph", "5midph", "5distph")
GROUPS = {
    "Hips": (("hipmid", "Spine1"), ("hipmid", "L5_S1"), "pelvis", ("Full Body", "pelvis", "sacrum")),
    "Spine1": (("Spine1", "Spine2"), ("L5_S1", "L3_L4"), "lumbar4", ("lumbar5", "lumbar4")),
    "Spine2": (("Spine2", "Chest"), ("L3_L4", "T12_L1"), "lumbar1", ("lumbar3", "lumbar2", "lumbar1")),
    "Chest": (("Chest", "Neck1"), ("T12_L1", "C7_T1"), "torso",
              ("torso", "bimanual_attachment", "root", "thorax", "cervical_spine", "head_attach")),
    "Neck1": (("Neck1", "Neck2"), ("C7_T1", "mid_cervical"), "neck", ("neck",)),
    "Neck2": (("Neck2", "Head"), ("mid_cervical", "C0_C1"), "neck", ()),
    "Head": (("Head", "HeadEnd"), ("C0_C1", "head_vertex"), "head", ("head",)),
    "{Side}Shoulder": (("{Side}Shoulder", "{Side}Arm"), ("sternoclavicular_{side}", "glenohumeral_{side}"),
                       "scapula_{side}", ("clavicle_{side}", "clavphant_{side}", "scapula_{side}")),
    "{Side}Arm": (("{Side}Arm", "{Side}ForeArm"), ("glenohumeral_{side}", "elbow_{side}"), "humerus_{side}",
                  ("scapphant_{side}", "humphant_{side}", "humphant1_{side}", "humerus_{side}")),
    "{Side}ForeArm": (("{Side}ForeArm", "{Side}Hand"), ("elbow_{side}", "wrist_{side}"), "ulna_{side}",
                      ("ulna_{side}", "radius_{side}")),
    "{Side}Hand": (("{Side}Hand", "{Side}Hand tip"), ("wrist_{side}", "finger_tip_{side}"), "lunate_{side}",
                   tuple(f"{bone}_{{side}}" for bone in _HAND)),
    "{Side}Leg": (("{Side}Leg", "{Side}Shin"), ("hip_{side}", "knee_{side}"), "femur_{side}", ("femur_{side}",)),
    "{Side}Shin": (("{Side}Shin", "{Side}Foot"), ("knee_{side}", "ankle_{side}"), "tibia_{side}", ("tibia_{side}",)),
    "{Side}Foot": (("{Side}Foot", "{Side}ToeBase"), ("ankle_{side}", "mtp_{side}"), "calcn_{side}",
                   ("talus_{side}", "calcn_{side}")),
    "{Side}ToeBase": (("{Side}ToeBase", "{Side}ToeEnd"), ("mtp_{side}", "toe_tip_{side}"), "toes_{side}",
                      ("toes_{side}",)),
}
# MyoFullBody bodies with no SOMA segment: each follows its couplings or its parent (sized with its parent).
NO_COUNTERPART = {"patella_{side}": "kneecap: its slides and turn follow knee_angle_{side} (couplings)",
                  "Abdomen": "abdominal wall wrapper: Abs_t1 and Abs_t2 locked, Abs_r3 follows flex_extension"}
# Bodies on a group's stretch with no target of their own.
NO_TARGET = {"clavicle_{side}": "its two dofs follow shoulder_elv_{side}",
             "scapula_{side}": "every shoulder-girdle dof follows shoulder_elv_{side}",
             "talus_{side}": "ankle_angle_{side}; the foot group's frame is the calcaneus (subtalar)",
             "radius_{side}": "its pro_sup_{side} turn is SOMA's {Side}Hand twist",
             "lumbar5": "its flex_extension, lat_bending and axial_rotation lead every lumbar level",
             "sacrum": "rigid on the pelvis"}


def groups():
    """GROUPS written out for both sides: {segment: ((SOMA start, end), (MyoFullBody start, end), frame body,
    bodies)}."""
    return sided_map(GROUPS)


def sided(names):
    """Each {Side}/{side} name made for both sides, other names as they are."""
    found = []
    for name in names:
        found += [name.format(Side=side, side=side[0].lower()) for side in ("Left", "Right")] if "{" in name else [name]
    return found


def sided_map(table):
    """The table with each `{Side}` key written for both sides, its value's names (in nested tuples too) its side's."""
    return {key.format(Side=side, side=side[0].lower()): _written(value, side)
            for key, value in table.items() for side in (("Left", "Right") if "{" in key else ("Left",))}


def _written(value, side):
    if isinstance(value, str):
        return value.format(Side=side, side=side[0].lower())
    return tuple(_written(part, side) for part in value)
