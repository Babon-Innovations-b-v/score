"""What each robot part is asked for, and the room it fills on the robot.

One entry per model the game draws: the greenhouse frame and every part that fits it, which the
bench draws, and the digger frame and its own parts, which are drawn at the dig site (#62 S14).
The three controller links are one generated mast, fitted into three
rooms of different heights. A part is made
alone, in the locked Moon look, then fitted into its room, so parts made on
different days still sit on one robot the same way.

**The model** each part is drawn from is built in code by `tools/kit` (2026-09-27), fitted into
the room below; the sentence and the form are kept to make a part on the locked route
(`run.sh --part <id>`) when one is to be laid beside its kit part.

**The room** is the box the part fills, in metres, in the robot's own space with the origin on the
mount it sits on and front at -z: `low` and `high` corners. It is the box the part's old blocks
filled, which the bench's picking was tuned around, so a real part lands exactly where the block
stood and nothing about fitting changes.

**How it fills it.** `within` scales the part evenly until it touches the box, then stands it on
the box's floor at the middle, so a part keeps its own proportions. `exact` stretches it to the box
on every side, for the frame, whose mounts are fixed points on it.

**The form** is `machine` unless a brief names another. A wheel asked for in the machine form
comes back as a whole little rover, because the form names a machine; `space` gives the same
materials without asking for one.

**A wheel set** is one wheel. The bench draws it at both ends of its axle, turned so its axle runs
along x; `room` is the box of the left wheel, and reaches outward rather than into the frame when
a made wheel is chunkier than its old block.
"""

# The mast every controller link draws. The three levels differ by height only, so one mesh is
# made and fitted into each level's room.
MAST_SENTENCE = ("a slim upright antenna mast with a small round sensor dome on its top, joined at "
                 "its foot to a small square base plate")

BRIEFS = {
    "greenhouse": {
        "sentence": ("a low flat rectangular robot chassis, one thick solid deck slab longer than it "
                     "is wide, with a squat axle housing joined under its front end and another "
                     "under its rear end, its top surface flat and empty"),
        "room": {"low": [-0.55, 0.22, -0.7], "high": [0.55, 0.52, 0.7]},
        "fill": "exact",
    },
    "rover_wheels": {
        "sentence": ("a single loose wheel on its own and attached to nothing, a thick treaded tyre on a solid "
                     "metal disc hub"),
        "room": {"low": [-0.76, -0.22, -0.22], "high": [-0.54, 0.22, 0.22]},
        "fill": "within",
        "wheel": True,
        "form": "space",
    },
    "wide_wheels": {
        "sentence": ("a single loose very wide heavy wheel on its own and attached to nothing, a deep treaded "
                     "tyre on a solid metal disc hub"),
        "room": {"low": [-0.75, -0.24, -0.24], "high": [-0.49, 0.24, 0.24]},
        "fill": "within",
        "wheel": True,
        "form": "space",
    },
    "light_wheels": {
        "sentence": ("a single loose thin light wheel on its own and attached to nothing, a slim smooth tyre on a "
                     "flat metal disc hub"),
        "room": {"low": [-0.725, -0.2, -0.2], "high": [-0.585, 0.2, 0.2]},
        "fill": "within",
        "wheel": True,
        "form": "space",
    },
    "battery_pack": {
        "sentence": ("a heavy rectangular battery pack, a sealed box with two thick power terminals "
                     "and a carry handle joined to its top"),
        "room": {"low": [-0.36, -0.11, -0.225], "high": [0.36, 0.11, 0.225]},
        "fill": "within",
    },
    "battery_2": {
        "sentence": ("a heavy rectangular battery pack, a sealed box with two thick power terminals "
                     "and a carry handle joined to its top"),
        "room": {"low": [-0.36, -0.11, -0.225], "high": [0.36, 0.11, 0.225]},
        "fill": "within",
    },
    "link_basic": {
        "sentence": MAST_SENTENCE,
        "room": {"low": [-0.1, 0.0, -0.1], "high": [0.1, 0.77, 0.1]},
        "fill": "within",
    },
    "link_2": {
        "sentence": MAST_SENTENCE,
        "room": {"low": [-0.12, 0.0, -0.12], "high": [0.12, 0.97, 0.12]},
        "fill": "within",
    },
    "link_3": {
        "sentence": MAST_SENTENCE,
        "room": {"low": [-0.14, 0.0, -0.14], "high": [0.14, 1.15, 0.14]},
        "fill": "within",
    },
    "seed_drill": {
        "sentence": ("three short straight planting tubes pointing straight down, joined in a row "
                     "under a square seed hopper with sloped sides and an open top"),
        "room": {"low": [-0.45, -0.26, -0.25], "high": [0.45, 0.485, 0.25]},
        "fill": "within",
    },
    "picker": {
        "sentence": ("two long slim curved gripper fingers reaching forward side by side, joined at "
                     "their rear to a compact square actuator housing"),
        "room": {"low": [-0.25, -0.17, -0.45], "high": [0.25, 0.2, 0.15]},
        "fill": "within",
    },
    "soil_feeder": {
        "sentence": ("a short feed spout pointing down, joined under a round sealed feed tank with a "
                     "domed lid"),
        "room": {"low": [-0.25, 0.0, -0.25], "high": [0.25, 0.6, 0.25]},
        "fill": "within",
    },
    "bumper": {
        "sentence": "a long straight padded bumper bar, thick and rigid, with two short mounting brackets joined to its back",
        # Deep enough behind the bar for its brackets to reach back to the frame's nose.
        "room": {"low": [-0.5, -0.1, -0.05], "high": [0.5, 0.1, 0.2]},
        "fill": "within",
    },
    "row_guide": {
        "sentence": "a small camera pod with one large round lens on its front, joined to a short square bracket",
        # Deeper than its old block: a camera is long along its lens.
        "room": {"low": [-0.1, -0.075, -0.15], "high": [0.1, 0.075, 0.15]},
        "fill": "within",
    },
    # The field eye (#119) sits on the row guide's mount and shares its brief until it has its own.
    "field_eye": {
        "sentence": "a small camera pod with one large round lens on its front, joined to a short square bracket",
        "room": {"low": [-0.1, -0.075, -0.15], "high": [0.1, 0.075, 0.15]},
        "fill": "within",
    },
    "crop_basket": {
        "sentence": "an open topped rectangular crop basket with thick solid walls and a flat floor",
        "room": {"low": [-0.415, -0.02, -0.215], "high": [0.415, 0.255, 0.215]},
        "fill": "within",
    },
    "extension_plate": {
        "sentence": "a thick flat rectangular mounting plate with bolt holes along its edges and a raised rim",
        # Taller than its old slab, so the rim and the bolts along it survive at full width.
        "room": {"low": [-0.55, -0.05, -0.3], "high": [0.55, 0.15, 0.3]},
        "fill": "within",
    },
    "top_rack": {
        "sentence": ("a small rack frame of four thick upright posts joined by a solid crossbar along "
                     "their tops"),
        "room": {"low": [-0.32, 0.0, -0.24], "high": [0.32, 0.43, 0.24]},
        "fill": "within",
    },
    # The digger's frame and parts, made under the outside workstream's prefix (#62 S3) and fitted
    # here once the simulation named them. The rooms are the digger's own: a 1.2 m by 1.8 m deck
    # 0.3 m thick at axle height, wheels 0.6 m across outboard of it, the scoop resting on the
    # ground ahead of the deck and the bin standing on its rear half. Game figures, the owner's to
    # retune.
    "digger": {
        "sentence": ("a long flat rectangular robot chassis box for a digging machine, a thick solid "
                     "deck longer than it is wide, a sensor block across its front end"),
        "room": {"low": [-0.6, 0.3, -0.9], "high": [0.6, 0.6, 0.9]},
        "fill": "exact",
    },
    "digger_wheels": {
        "sentence": ("a single loose big heavy wheel on its own with a small motor block beside its "
                     "hub, a deep treaded tyre on a solid metal disc hub"),
        "room": {"low": [-0.9, -0.3, -0.3], "high": [-0.62, 0.3, 0.3]},
        "fill": "within",
        "wheel": True,
        "form": "space",
    },
    "dig_scoop": {
        "sentence": ("a digging scoop bucket with an open front lip on the end of a short straight "
                     "arm"),
        "room": {"low": [-0.3, -0.35, -0.8], "high": [0.3, 0.1, 0.1]},
        "fill": "within",
    },
    "regolith_bin": {
        "sentence": ("an open topped hopper bin with sloping sides, wider at its top than at its "
                     "square base"),
        "room": {"low": [-0.45, 0.0, -0.4], "high": [0.45, 0.8, 0.4]},
        "fill": "within",
    },
}
