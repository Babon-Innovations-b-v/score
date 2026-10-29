"""The measure check's toy body: the MyoFullBody body names the measures read (the toes, head, lunates, finger tips,
the limbs' lengths),
each on a hinge with a small cube bone mesh set partly out of its skin box, one sphere collider; a five-segment SOMA
rig whose skin is a box per segment weighted wholly to it, its tips (toe ends, head end) beside; 16 frames of turns.
Newton's Python (mujoco)."""
import mujoco
import numpy as np

BODIES = {"toes_l": (0.1, 0.0, 0.0), "toes_r": (-0.1, 0.0, 0.0), "head": (0.0, 0.0, 1.6),
          "lunate_l": (0.4, 0.0, 1.0), "lunate_r": (-0.4, 0.0, 1.0), "3distph_l": (0.5, 0.0, 0.9),
          "3distph_r": (-0.5, 0.0, 0.9)}
LIMBS = {"LeftLeg": "femur_l", "LeftShin": "tibia_l", "LeftFoot": "talus_l", "LeftArm": "humerus_l",
         "LeftForeArm": "ulna_l"}  # read by the measure's lengths only: no skin, no turn target
LIMBS.update({key.replace("Left", "Right"): body[:-1] + "r" for key, body in list(LIMBS.items())})
BODIES.update({body: (0.1 * (index % 5) * (1 if body.endswith("l") else -1), 0.2, 0.2 * (index % 5))
               for index, body in enumerate(LIMBS.values())})
SEGMENTS = ("LeftToeBase", "RightToeBase", "Head", "LeftHand", "RightHand")
RIDES = {"LeftToeBase": "toes_l", "RightToeBase": "toes_r", "Head": "head", "LeftHand": "lunate_l",
         "RightHand": "lunate_r"}
TIPS = {"LeftToeEnd": "LeftToeBase", "RightToeEnd": "RightToeBase", "HeadEnd": "Head"}
CUBE = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], dtype=float)
FACES = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6],
                  [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
FRAMES = 16


def model():
    """The toy MJCF compiled: a hinge and a cube bone mesh a body, the bone (4 cm) shifted 1.5 cm off its body."""
    verts = " ".join(f"{value:g}" for value in (0.02 * CUBE).ravel())
    bodies = "".join(
        f'<body name="{name}" pos="{x} {y} {z}"><joint name="{name}_turn" axis="{index % 3 == 0:d} '
        f'{index % 3 == 1:d} {index % 3 == 2:d}"/><geom type="mesh" mesh="cube" pos="0.015 0.01 0" contype="0" '
        f'conaffinity="0" mass="0.1"/>' + ('<geom type="sphere" size="0.02" contype="1"/>' if index == 0 else "")
        + "</body>" for index, (name, (x, y, z)) in enumerate(BODIES.items()))
    return mujoco.MjModel.from_xml_string(
        f'<mujoco><asset><mesh name="cube" vertex="{verts}"/></asset><worldbody>{bodies}</worldbody></mujoco>')


def turn(axis, angle):
    """A rotation of `angle` rad about unit `axis`."""
    axis = np.asarray(axis, dtype=float) / np.linalg.norm(axis)
    skew = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(angle) * skew + (1 - np.cos(angle)) * skew @ skew


def rig(own):
    """The toy SOMA rig (own frame): a joint per segment at its body's place, a tip 5 cm on, an 8 cm skin box each."""
    names = list(SEGMENTS) + list(TIPS) + list(LIMBS)
    places = ([own[RIDES[segment]] for segment in SEGMENTS] + [own[RIDES[tip]] + [0.05, 0, 0] for tip in TIPS.values()]
              + [own[body] for body in LIMBS.values()])
    bind = np.tile(np.eye(4), (len(names), 1, 1))
    bind[:, :3, 3] = places
    points = np.concatenate([own[RIDES[segment]] + 0.04 * CUBE for segment in SEGMENTS])
    weights = np.zeros((len(points), len(names)))
    for index in range(len(SEGMENTS)):
        weights[8 * index:8 * index + 8, index] = 1.0
    faces = np.concatenate([FACES + 8 * index for index in range(len(SEGMENTS))])
    return {"names": names, "bind": bind, "points": points, "faces": faces, "weights": weights}


def clip(seed=3):
    """(model, angles [FRAMES x nq], rig, segments, worlds [FRAMES x segments x 4 x 4], scales {body: [3]})."""
    from model import TO_OWN
    toy, generator = model(), np.random.default_rng(seed)
    own = {name: TO_OWN @ np.asarray(place) for name, place in BODIES.items()}
    angles = generator.uniform(-0.6, 0.6, (FRAMES, toy.nq))
    worlds = np.tile(np.eye(4), (FRAMES, len(SEGMENTS), 1, 1))
    for frame in range(FRAMES):
        for index, segment in enumerate(SEGMENTS):
            worlds[frame, index, :3, :3] = turn(generator.normal(size=3), generator.uniform(0, 0.5))
            worlds[frame, index, :3, 3] = own[RIDES[segment]] + generator.normal(scale=0.01, size=3)
    scales = {name: np.full(3, 1.1) for name in BODIES}
    return toy, angles, rig(own), list(SEGMENTS), worlds, scales
