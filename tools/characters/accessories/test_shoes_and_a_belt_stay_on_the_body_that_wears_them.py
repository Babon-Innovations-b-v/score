"""Shoes and a belt stay on the body that wears them: a shoe made on a toy foot covers the foot under its collar and
nothing over it, its sole lies under the foot, it moves with the foot, and the foot stays inside it; a belt goes round
the toy skirt's waistband top, round all of it; and `faults` names a sole through the floor, a sole that never
reaches it, a foot out through its shoe, a belt off its waistband, a belt held off the skin by cloth it does not
hold in (a loose tee under it) and a belt out through the coat worn over it (a coat pulled in between the belt's
inside and its outside). Each row is the toy body walking forward one way.

Breaks that turn it red (each applied once, seen red, reverted): the shoe's offset along the last's normals taken
inward (`- normals` in `shoe`: the foot out through the shoe); the collar's cut keeping the faces over it (`~inside`:
the shoe over the ankle); a shoe carried by the bind's joints alone (`worlds[:1]` in `carried`: the shoe left behind as
the foot walks); the lift left out of the sole's lowest in `measured` (every worn row below the floor); the belt's
radius taken from the waistband's ring alone rather than from all round it (`around` the ring in `belt`: the belt
inside the skirt's flare); the belt's top measured off its inside bottom row (`belted["belt"][:, BINS + 1:2 * (BINS +
1)]` in `measured`: the belt read off its waistband); the belt's distance off the skin read off the skin alone
(`skin_radius` in `held_in` taken as the belt's own radius: no belt ever holds anything out); the belt's outside
taken as its inside (`+ BELT_THICK_M` left out in `under_cover`: the coat pulled in through the belt's strap)."""
import numpy as np
import pytest
import trimesh

from tools.characters import accessories

NAMES = ["Hips", "LeftShin", "LeftFoot", "LeftToeBase", "LeftToeEnd",
         "RightShin", "RightFoot", "RightToeBase", "RightToeEnd"]
FRAMES = 5
STEP_M = 0.1  # the toy body's walk forward a frame


def toy_body():
    """Two feet (ellipsoids on the floor, toes forward at +z) on two leg tubes, and a hip tube; skinned rigidly to
    their joints, walking STEP_M forward a frame."""
    pieces, joints = [], []
    for side, sign in (("Left", 1.0), ("Right", -1.0)):
        foot = trimesh.creation.icosphere(subdivisions=3)
        foot.apply_scale([0.045, 0.04, 0.13])
        foot.apply_translation([sign * 0.1, 0.04, 0.07])
        leg = trimesh.creation.cylinder(radius=0.035, height=0.45, sections=24)
        leg.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2.0, [1, 0, 0]))
        leg.apply_translation([sign * 0.1, 0.3, 0.0])
        pieces += [foot, leg]
        joints += [np.where(foot.vertices[:, 2] > 0.12, NAMES.index(f"{side}ToeBase"), NAMES.index(f"{side}Foot")),
                   np.full(len(leg.vertices), NAMES.index(f"{side}Shin"))]
    hips = trimesh.creation.cylinder(radius=0.14, height=0.3, sections=48)
    hips.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2.0, [1, 0, 0]))
    hips.apply_translation([0.0, 0.95, 0.0])
    hips = hips.subdivide_to_size(0.01)  # skin points all down its side, as a body has, for the belt's band
    pieces.append(hips)
    joints.append(np.full(len(hips.vertices), NAMES.index("Hips")))
    joined = trimesh.util.concatenate(pieces)
    joints = np.concatenate(joints)
    weights = np.zeros((len(joints), len(NAMES)))
    weights[np.arange(len(joints)), joints] = 1.0
    bind = np.tile(np.eye(4), (len(NAMES), 1, 1))
    for side, sign in (("Left", 1.0), ("Right", -1.0)):
        for part, place in (("Shin", (0.0, 0.45, 0.0)), ("Foot", (0.0, 0.06, 0.0)), ("ToeBase", (0.0, 0.03, 0.13)),
                            ("ToeEnd", (0.0, 0.02, 0.2))):
            bind[NAMES.index(f"{side}{part}"), :3, 3] = np.array(place) + [sign * 0.1, 0.0, 0.0]
    bind[0, :3, 3] = [0.0, 0.95, 0.0]
    worlds = np.repeat(bind[None], FRAMES + 1, axis=0)
    worlds[:, :, 2, 3] += STEP_M * np.arange(FRAMES + 1)[:, None]
    points = np.asarray(joined.vertices)
    frames = points[None] + np.array([0.0, 0.0, STEP_M])[None, None] * np.arange(FRAMES + 1)[:, None, None]
    return {"bind": points, "faces": np.asarray(joined.faces), "weights": weights, "names": np.asarray(NAMES),
            "joints": bind, "worlds": worlds, "frames": frames, "clip_start": np.array(1)}


def toy_skirt():
    """A flared skirt over the hips, its top ring (the waistband's top) 2 mm out of the hip tube, every clip frame."""
    heights = np.linspace(0.6, 1.0, 21)
    radii = 0.142 + (1.0 - heights) * 0.15
    angles = np.linspace(0.0, 2.0 * np.pi, 64, endpoint=False)
    points = np.concatenate([np.stack([radius * np.cos(angles), np.full(64, height), radius * np.sin(angles)], axis=1)
                             for height, radius in zip(heights, radii)])
    walked = points[None] + np.array([0.0, 0.0, STEP_M])[None, None] * np.arange(1, FRAMES + 1)[:, None, None]
    return walked, np.arange(20 * 64, 21 * 64)


def toy_coat(radius):
    """A coat's cloth over the belt's band: a tube of `radius` round the hip tube's axis, every clip frame."""
    angles = np.linspace(0.0, 2.0 * np.pi, 64, endpoint=False)
    points = np.concatenate([np.stack([radius * np.cos(angles), np.full(64, height), radius * np.sin(angles)], axis=1)
                             for height in np.linspace(0.95, 1.0, 11)])
    return points[None] + np.array([0.0, 0.0, STEP_M])[None, None] * np.arange(1, FRAMES + 1)[:, None, None]


@pytest.mark.parametrize("wear, failed", [
    ("worn", []),
    ("lifted short", ["left shoe below the floor", "right shoe below the floor"]),
    ("lifted too far", ["left shoe never on the floor", "right shoe never on the floor"]),
    ("left shoe shrunk on the foot", ["left foot out through its shoe"]),
    ("belt slid down the skirt", ["belt off the waistband"]),
    ("loose tee under the belt", ["belt not holding the cloth in"]),
    ("coat over the belt", []),
    ("coat pulled in to the belt", ["belt out through the cloth over it"]),
])
def test_shoes_and_a_belt_stay_on_the_body_that_wears_them(wear, failed):
    body = toy_body()
    start = int(body["clip_start"])
    shoes = {side: accessories.shoe(body, side) for side in ("Left", "Right")}
    worn = {side: accessories.carried(made["points"], made["weights"], body)[start:] for side, made in shoes.items()}
    for side, made in shoes.items():
        foot = np.asarray(body["bind"])[made["covered"]]
        assert len(made["covered"]) > 100
        assert made["points"][:, 1].max() < accessories.collar_height(body, side, made["points"]).max() + 0.01
        assert made["points"][made["faces"][made["sole"]]][..., 1].mean() < foot[:, 1].min()
        assert made["foot length m"] == pytest.approx(0.26, abs=0.01)
        assert np.allclose(worn[side][-1] - worn[side][0], [0.0, 0.0, STEP_M * (FRAMES - 1)], atol=1e-9)
    lift = max(-float(frames[..., 1].min()) for frames in worn.values())
    if wear == "lifted short":
        lift -= 0.005
    if wear == "lifted too far":
        lift += 0.01
    if wear == "left shoe shrunk on the foot":
        middle = worn["Left"].mean(axis=1, keepdims=True)
        worn["Left"] = middle + (worn["Left"] - middle) * np.array([0.85, 1.0, 0.85])  # narrower and shorter
    skirt, ring = toy_skirt()
    worn_round = [skirt]
    if wear == "loose tee under the belt":  # a tee hanging 3 cm off the hips all round the belt's band
        loose = skirt.copy()
        loose[..., 0] *= 0.17 / 0.142
        loose[..., 2] = (loose[..., 2] - STEP_M * np.arange(1, FRAMES + 1)[:, None]) * 0.17 / 0.142 + STEP_M * \
            np.arange(1, FRAMES + 1)[:, None]
        worn_round.append(loose)
    belted = accessories.belt(body, start, worn_round, ring)
    if wear == "belt slid down the skirt":
        belted["belt"] = belted["belt"] - np.array([0.0, 0.04, 0.0])
    radii = np.hypot(belted["belt"][..., 0], belted["belt"][..., 2] - STEP_M * np.arange(1, FRAMES + 1)[:, None])
    assert radii.min() > 0.1465  # round the flare under the top (its 0.98 m ring, 0.145 m), not the top (0.142 m)
    assert belted["off the skin"].min() > 0.0
    if wear.startswith("coat"):  # its cloth 10 mm out past the belt's inside, or 2 mm: inside its 4 mm strap
        inside = radii[:, :2 * (accessories.BINS + 1)].max()
        coat = toy_coat(inside + (0.01 if wear == "coat over the belt" else 0.002))
        belted = accessories.belt(body, start, worn_round, ring, [coat])
    found = accessories.measured(shoes, worn, np.asarray(body["frames"])[start:], np.asarray(body["faces"]), belted,
                                 lift)
    lines = accessories.faults(found)
    kinds = ["left shoe below the floor", "right shoe below the floor", "left shoe never on the floor",
             "right shoe never on the floor", "left foot out through its shoe", "right foot out through its shoe",
             "belt off the waistband", "belt not holding the cloth in", "belt out through the cloth over it"]
    assert [kind for kind in kinds if any(line.startswith(kind) for line in lines)] == failed, lines
