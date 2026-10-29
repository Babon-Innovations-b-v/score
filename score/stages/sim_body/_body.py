"""The sim body stage's body: a person's rig at its own build (`person_rig`, its clips played as the people build
plays them: `tools.characters.played`), its segments, its clips' frames and its mass by #64's rule."""
import numpy as np

from tools.characters import played

RATE = 30.0  # the rig's clips (tools/characters/skel_usd.py RATE)
# SOMA joints that carry no segment: the ground point under the body and the end sites.
NOT_SEGMENTS = ("Root", "HeadEnd", "LeftToeEnd", "RightToeEnd")
# Global age-standardised mean BMI of adults, 2016 (kg/m2): NCD-RisC, Lancet 2017;390:2627-42,
# https://doi.org/10.1016/S0140-6736(17)32129-3. Height times this is #64's rule for a body with no stated weight.
BMI = {"male": 24.5, "female": 24.8}
BODY = "people-body"  # a look's built body row: its rig.npz is the person's own build (prop_rig.py)


def segments_of(rig):
    """The rig's segment joints (indices) and, for each rig joint, the segment that carries it (its nearest kept
    joint up the tree; the root's children carry the root)."""
    names, parents = [str(name) for name in rig["names"]], rig["parents"]
    kept = [joint for joint, name in enumerate(names) if name not in NOT_SEGMENTS]

    def carrier(joint):
        while joint >= 0 and joint not in kept:
            joint = parents[joint]
        return joint

    carriers = [carrier(joint) for joint in range(len(names))]
    top = next(joint for joint in kept if carrier(parents[joint]) < 0)
    return kept, [top if found < 0 else found for found in carriers]


def body_row(single):
    """The built body row of a character's look (people-cloth's own naming)."""
    return f"{BODY}-{(single.get('look') or '').replace('/', '-')}"


def bind_offsets(rig):
    """Each joint's offset against its parent at the rig's own bind (the root's: its bind's place)."""
    bind = np.asarray(rig["bind"], dtype=float)
    return np.array([bind[joint] if parent < 0 else np.linalg.inv(bind[parent]) @ bind[joint]
                     for joint, parent in enumerate(rig["parents"])])[:, :3, 3]


def person_rig(rig, built):
    """The clips rig at a person's own build, as the people build plays its clips (`tools.characters.played`, the
    people route's one definition: prop_build.py's clip_world and floor_lift): the built body's bind and surface
    (rig.npz's moved mean surface), every clip's joint offsets the built ones and its travel (Hips) scaled by the built
    Hips' height over the rig's, every clip lifted so the standing clip's first frame puts the feet where the bind
    does; and that size. With no build, the rig's own bind is the build, size 1: its clips were posed on SOMA's
    zero-identity body, 7 cm shorter than the template its bind and surface are, and their own offsets floated its
    skin 26 to 57 mm over its ground (#70)."""
    if built is None:
        built = {"bind": rig["bind"], "offsets": bind_offsets(rig), "source_points": rig["points"]}
    names = [str(name) for name in rig["names"]]
    hips = played.TRAVELLING_JOINT
    if names[hips] != "Hips":
        raise ValueError(f"the rig's travelling joint is {names[hips]}, not Hips")
    size = float(built["bind"][hips, 1, 3] / rig["bind"][hips, 1, 3])
    bones = {"offsets": built["offsets"], "parents": rig["parents"], "bind": built["bind"]}
    lift = played.floor_lift(rig, bones, names, size)
    found = dict(rig, bind=np.asarray(built["bind"]), points=np.asarray(built["source_points"]))
    for key in [key for key in rig if key.startswith("clip_")]:
        found[key] = played.clip_local(rig, key[len("clip_"):], built["offsets"], rig["parents"], size, lift)
    return found, size


def standing_height(rig):
    """The rig's own standing height at its bind pose (metres, its surface's top over its lowest point)."""
    points = np.asarray(rig["points"])
    return float(points[:, 1].max() - points[:, 1].min())


def mass_of(single, height):
    """A character's body mass record: the stated weight, else height squared times the reference BMI of its sex
    (the mean of both when none is stated), marked estimated (#64)."""
    if single.get("weight"):
        return {"kg": float(single["weight"]), "source": "stated weight"}
    stated = single.get("height")
    tall = float(stated or height)
    sex = single.get("sex")
    bmi = BMI[sex] if sex in BMI else sum(BMI.values()) / len(BMI)
    return {"kg": round(bmi * tall ** 2, 2), "source": "estimated", "height": round(tall, 4),
            "height from": "stated" if stated else "the SOMA body's own standing height",
            "sex": sex if sex in BMI else "not stated", "bmi": bmi}


def clip_frames(rig, clip, kept):
    """The clip's segment frames in the world, frame by frame (frames x segments x 4 x 4): its joints' transforms
    against their parents chained down the tree."""
    return played.chained(np.asarray(rig[f"clip_{clip}"], dtype=float), rig["parents"])[:, kept]
