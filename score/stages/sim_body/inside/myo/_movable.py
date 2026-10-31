"""MyoFullBody made movable above the lower back (#70, the owner: "MyoFullBody should be fully movable"), on the spec
of the pinned source, the download untouched: the neck's two joints the source leaves commented out (`NECK`), one
three-axis thoracic joint where the torso meets lumbar1 (`THORACIC`), and the shoulder girdle's couplings to the
arm's elevation dropped, its clavicle and scapula joints given their own two-sided ranges (`GIRDLE`) and each phantom
tied to the joint it undoes (`PHANTOMS`). A body or coupling the source does not
have is left alone (a toy wheel in the tests)."""
import numpy as np

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


def movable(spec):
    """The spec's neck, thorax and shoulder girdle made movable in place (the module's three changes)."""
    _neck(spec)
    _thoracic(spec)
    _girdle(spec)


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
