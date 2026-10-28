"""Which MyoFullBody body each SOMA segment rides, which segments the fit follows, the hips that place the pelvis, the
feet, the trunk's lumbar leaders and what MyoFullBody lacks (pure: no MuJoCo, no Newton); `sided` and `sided_map`
write a `{Side}`/`{side}` name out for both sides."""
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


def sided(names):
    """Each {Side}/{side} name made for both sides, other names as they are."""
    found = []
    for name in names:
        found += [name.format(Side=side, side=side[0].lower()) for side in ("Left", "Right")] if "{" in name else [name]
    return found


def sided_map(table):
    return {key.format(Side=side, side=side[0].lower()): (value.format(Side=side, side=side[0].lower())
                                                          if isinstance(value, str) else
                                                          tuple(part.format(Side=side, side=side[0].lower())
                                                                for part in value))
            for key, value in table.items() for side in (("Left", "Right") if "{" in key else ("Left",))}
