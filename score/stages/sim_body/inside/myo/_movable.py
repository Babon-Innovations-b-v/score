"""MyoFullBody made movable above the lower back (#70, the owner: "MyoFullBody should be fully movable"), on the spec
of the pinned source, the download untouched: the neck's two joints the source leaves commented out (`NECK`), one
three-axis thoracic joint where the torso meets lumbar1 (`THORACIC`), and the shoulder girdle's couplings to the
arm's elevation dropped, its clavicle and scapula joints given their own two-sided ranges (`GIRDLE`) and each phantom
tied to the joint it undoes (`PHANTOMS`); its feet given the twist on the shin their hinges lack and the ankle's
and subtalar joint's human ranges (`FEET`, 2026-11-01); its fingers' knuckles let bend back as a person's do
(`KNUCKLES`, 2026-11-01); and its shin's turn on the femur let free of the knee's flexion (`KNEE`, 2026-11-04). A
body or coupling the source does not have is left alone (a toy wheel in the tests)."""
import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

# MyoHead's own lines (head/assets/myohead_rigid_chain.xml, commented out there), as written: {body: joint}.
NECK = {"neck": {"name": "neck_rotation", "pos": [-0.02, 0.4, 0.0], "axis": [0.2, 1.0, 0.0], "range": [-1.4, 1.4]},
        "head": {"name": "neck_flexion", "pos": [0.0, 0.0, 0.0], "axis": [0.0, 0.0, 1.0], "range": [-0.87, 1.05]}}
# The thoracic spine's motion lumped at T12/L1 (landmarks' T12_L1 on the torso), the lumbar levels' axes and order
# (FE about z, flexion negative; LB about x; AR about y). Ranges: the thoracic spine's normal active range of motion,
# the upper end of Magee's (Orthopedic Physical Assessment, 6th ed. 2014, ch. 8: forward flexion 20-45 deg, extension
# 25-45 deg, side flexion 20-40 deg, rotation 35-50 deg), in line with White and Panjabi's summed T1-T12 segment
# ranges (Clinical Biomechanics of the Spine, 2nd ed. 1990, table 2-4). Names never end like bone_groups.TRUNK's.
THORACIC = ("torso", "myotorso", [-0.01368, 0.11893, 0.00045],
            [("thoracic_FE", [0.0, 0.0, 1.0], [-np.radians(45), np.radians(45)]),
             ("thoracic_LB", [1.0, 0.0, 0.0], [-np.radians(40), np.radians(40)]),
             ("thoracic_AR", [0.0, 1.0, 0.0], [-np.radians(50), np.radians(50)])])
# The girdle's couplings to shoulder_elv dropped (myoarm_bimanual_assets.xml: the clavicle's two turns, the scapula's
# three, and the phantom that undoes each), so the clavicle and the scapula lead, each on its own range; each phantom
# (unrotscap, unrothum: MoBL-ARMS' undo of the girdle's turn, Holzbaur et al. 2005) is tied at -1 to the joint it
# undoes, so the scapula turns on the thorax by the acromioclavicular joints alone and the humerus' joints stay
# thoracohumeral, as MoBL's rhythm had them (a phantom left free shares its joint's axis: the clavicle's own turn then
# has no target, and the card's level 3 swung the pair bound to bound, 2026-10-31). Each range by the sign the arm's
# lift drives the joint, the model's own end kept where it is wider (the published rhythm stays reachable):
# sternoclavicular r2 (lift negative: retraction) to the model's 43 deg (Ludewig et al. 2009, JBJS 91(2):378: 15-30
# deg in elevation), protraction 20 deg; r3 (lift positive: elevation) to 45 deg, depression 10 deg (Moore, Dalley and
# Agur, Clinically Oriented Anatomy, 7th ed. 2014, table 6.4). Acromioclavicular r3 (lift positive: upward rotation)
# to the model's 70 deg, downward rotation 10 deg; r1 (posterior tilt) to the model's 32 deg, anterior tilt 20 deg;
# r2 (lift negative: external rotation) 25 deg each way (the scapula on the thorax in elevation and at rest: Ludewig
# 2009; McClure et al. 2001, JSES 10(3):269).
GIRDLE = {"sternoclavicular_r2": [-0.75, np.radians(20)], "sternoclavicular_r3": [-np.radians(10), np.radians(45)],
          "acromioclavicular_r1": [-np.radians(20), 0.552], "acromioclavicular_r2": [-np.radians(25), np.radians(25)],
          "acromioclavicular_r3": [-np.radians(10), 1.228]}
PHANTOMS = {"unrotscap_r2": "sternoclavicular_r2", "unrotscap_r3": "sternoclavicular_r3",
            "unrothum_r1": "acromioclavicular_r1", "unrothum_r2": "acromioclavicular_r2",
            "unrothum_r3": "acromioclavicular_r3"}
# The foot's twist on the shin (#70, the owner, 2026-11-01: SOMA's foot turns about the shin's long axis, MyoFullBody's
# hinges cannot): one hinge `ankle_rotation_{side}` on the talus at the ankle's centre, about the tibia's long axis
# (knee to ankle centre), before the ankle's flexion, positive turning the toes in (adduction) on both sides. At the
# ankle: the ankle complex's transverse-plane axis is the tibia's long axis (Brockett and Chapman 2016, Orthop Trauma
# 30(3):232, doi:10.1016/j.mporth.2016.04.015), and under full body load the talus turns about the vertical axis in the
# talocrural joint as the leg turns, the talonavicular joint beyond it (Lundberg 1989, Acta Orthop Scand Suppl 233,
# p. 15: 5.0 and 12 degrees within a 20-degree internal to 10-degree external leg rotation, not end ranges), joints
# MyoFullBody's rigid foot lumps into this one. Range: the ankle joint complex's abduction 20 and adduction 25 degrees
# (Gunaratne and Tamura 2024, Sensors 24(24), PMC11679897, a review of active ankle orthoses beside Grimston et al.
# 1993, Foot Ankle 14:215, who measured the complex's abduction and adduction; the review's sentence names no source).
# Ranges widened to human ones, never to what a clip asks:
# plantar flexion to 55 degrees (the ankle complex's "10 to 20 of dorsiflexion through to 40-55 of plantarflexion",
# Brockett and Chapman 2016, after Grimston et al. 1993 and Stauffer et al. 1977), dorsiflexion to 33 (averages 13 to
# 33 across studies: Roaas and Andersson 1982, Boone and Azen 1979, Lundberg et al. 1989, Stauffer et al. 1977, as
# OrthopaedicsOne's foot-and-ankle biomechanics review gathers them), subtalar inversion to 23 (the frontal plane's
# "23 inversion, 12 eversion", Brockett and Chapman 2016 after Stauffer et al. 1977); eversion keeps the model's 20
# (wider than 12: the published model stays reachable).
FEET = {"twist": ("ankle_rotation", [-np.radians(20), np.radians(25)]),
        "ranges": {"ankle_angle": [-np.radians(55), np.radians(33)], "subtalar_angle": [-0.349066, np.radians(23)]}}
# The fingers' knuckles bend back (#70, 2026-11-01): MyoFullBody's metacarpophalangeal flexion of the index to the
# little finger (mcp2 to mcp5) stops at 0 (the finger straight on its metacarpal), so SOMA's flatter hand, which asks
# them 20 to 30 degrees back, leaves the index and little distal phalanges outside its skin. A person's finger MCP
# joint hyperextends: extension 0 to 45 degrees beside flexion 0 to 90 (the AAOS average ranges, Greene and Heckman,
# The Clinical Measurement of Joint Motion, AAOS 1994, as Norkin and White, Measurement of Joint Motion, 5th ed. 2016,
# reproduce them; Eaton's hand reference table: "(0-45H)/90"). Extension widened to 45 degrees; flexion keeps the
# model's 90; the thumb's MCP (mp_flexion) and every other joint keep theirs.
# The shin turns on the femur of its own (#70, 2026-11-04): MyoFullBody's knee sets the tibia's turn about its long axis
# (knee_angle_rotation3) from the flexion alone (polycoef 0, 0.3695, -0.1695, 0.0252: 0.26 rad at 90 degrees, its
# range end), so seated the fitted shin stood 6 to 10 degrees from SOMA's Shin turn and the lateral malleolus swung
# out of SOMA's skin. A person's flexed knee turns the tibia of its own: at 90 degrees of flexion 30 degrees medially
# and 40 laterally (Kapandji, The Physiology of the Joints, vol. 2, the lower limb: the knee's active axial rotation),
# none at full extension. The coupling is dropped and the joint leads on the published model's own range (15 degrees
# each way, inside the flexed knee's), never widened; the knee's other couplings stay.
KNEE = ("knee_angle_rotation3", "knee_angle")
KNUCKLES = {"stems": tuple(f"mcp{finger}_flexion" for finger in "2345"), "extension": np.radians(45)}


def movable(spec):
    """The spec's neck, thorax, shoulder girdle, feet, knuckles and knees made movable in place (the module's six
    changes)."""
    _neck(spec)
    _thoracic(spec)
    _girdle(spec)
    _feet(spec)
    _knuckles(spec)
    _knee(spec)


def _neck(spec):
    """MyoHead's two neck joints added as the source's commented lines give them (its class's defaults)."""
    for body, joint in NECK.items():
        found = spec.body(body)
        if found is not None:
            found.add_joint(default=spec.find_default("myohead"), limited=True, **joint)


def _thoracic(spec):
    """The thoracic joint's three hinges added on the torso at T12/L1."""
    body, kind, place, axes = THORACIC
    found = spec.body(body)
    if found is None:
        return
    for name, axis, span in axes:
        found.add_joint(default=spec.find_default(kind), name=name, pos=place, axis=axis, range=span, limited=True)


def _girdle(spec):
    """The girdle's couplings to shoulder_elv deleted, each of its joints given GIRDLE's range; each phantom's tied at
    -1 to the joint it undoes, on that joint's range turned round."""
    for equality in list(spec.equalities):
        stem, side = equality.name1[:-2], equality.name1[-2:]  # the side's '_l'/'_r' off
        if not equality.name2.startswith("shoulder_elv"):
            continue
        if stem in GIRDLE:
            spec.delete(equality)
            spec.joint(equality.name1).range = GIRDLE[stem]
        elif stem in PHANTOMS:
            equality.name2 = PHANTOMS[stem] + side
            equality.data[:5] = [0.0, -1.0, 0.0, 0.0, 0.0]
            low, high = GIRDLE[PHANTOMS[stem]]
            spec.joint(equality.name1).range = [-high, -low]


def _feet(spec):
    """Each foot's twist hinge added on its talus before the ankle's flexion (`FEET`), the ankle's and subtalar
    joint's ranges widened."""
    name, span = FEET["twist"]
    for side in "lr":
        talus = spec.body(f"talus_{side}")
        if talus is None or spec.joint(f"ankle_angle_{side}") is None:
            continue
        shin_axis = -np.asarray(talus.pos, dtype=float) / np.linalg.norm(talus.pos)  # tibia origin (knee) from the ankle
        turned = Rotation.from_quat(np.roll(np.asarray(talus.quat, dtype=float), -1)).as_matrix()
        axis = turned.T @ shin_axis * (-1.0 if side == "l" else 1.0)  # +: toes in on both sides
        later = [_kept(joint) for joint in talus.joints]
        for joint in list(talus.joints):
            spec.delete(joint)
        talus.add_joint(default=spec.find_default("myolegs"), name=f"{name}_{side}", type=mujoco.mjtJoint.mjJNT_HINGE,
                        pos=[0.0, 0.0, 0.0], axis=axis, range=span, limited=True)
        for kept in later:
            talus.add_joint(**kept)
        for stem, wide in FEET["ranges"].items():
            spec.joint(f"{stem}_{side}").range = wide


def _knuckles(spec):
    """Each finger MCP flexion joint's (`KNUCKLES`) lower end moved to the knuckle's extension, its flexion kept."""
    for stem in KNUCKLES["stems"]:
        for side in "lr":
            joint = spec.joint(f"{stem}_{side}")
            if joint is not None:
                joint.range = [-KNUCKLES["extension"], float(joint.range[1])]


def _knee(spec):
    """Each knee's coupling of the shin's turn to its flexion (`KNEE`) deleted, the joint kept on its own range."""
    follower, leader = KNEE
    for equality in list(spec.equalities):
        if equality.name1[:-2] == follower and equality.name2[:-2] == leader:
            spec.delete(equality)


def _kept(joint):
    """A joint's settings, to add it again after another (MjSpec adds joints last only)."""
    return {field: getattr(joint, field) for field in
            ("name", "type", "pos", "axis", "range", "limited", "ref", "springref", "stiffness", "damping",
             "armature", "frictionloss", "margin", "group", "solref_limit", "solimp_limit", "solref_friction",
             "solimp_friction", "actfrclimited", "actfrcrange", "actgravcomp", "align", "springdamper")}
