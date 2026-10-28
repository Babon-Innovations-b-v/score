"""sizing: a small body built like MyoFullBody (a pelvis, a torso, each side's femur, tibia, talus and toes, humerus,
ulna and lunate) sized to limbs 1.1 times its own and its own standing height has every limb 1.1 times as long, the
rest as it was, and the person's mass; the person's limb lengths are its rig's joint distances (all worked out by
hand). It runs in Newton's own Python (MuJoCo pinned there; score/stages/physics/inside/newton_env.sh, built at
$PROPS_HOME/envs/newton_env): with none built there, as in `make tests`' sandbox home, it prints `skipped`.

Breaks (each applied once with the env linked into a sandbox home, seen red, reverted), 2026-10-28:
- sized's `body.pos = np.asarray(body.pos) * above` made `body.pos = np.asarray(body.pos)`: no limb grows.
- sized's `share = (kg - wrappers * WRAPPER_KG) / grown` made `share = 1.0`: the model's own mass is kept.
- limb_lengths' `side + far` made `side + near`: every length is 0.

Run: .venv/bin/python score/stages/sim_body/inside/sizing/test_a_sized_limb_is_the_persons_length.py
"""
import os
import pathlib
import subprocess
import sys

INSIDE = pathlib.Path(__file__).resolve().parents[1]
IN_ENV = "SIM_BODY_INSIDE_TEST"
# Each side's chain: (body, its place in its parent's frame, its parent); x is mirrored for the right side.
CHAIN = (("femur", "0.1 0 -0.1", "pelvis"), ("tibia", "0 0 -0.4", "femur"), ("talus", "0 0 -0.4", "tibia"),
         ("toes", "0 0.1 -0.05", "talus"), ("humerus", "0.2 0 0.4", "torso"), ("ulna", "0 0 -0.3", "humerus"),
         ("lunate", "0 0 -0.25", "ulna"))
# The toy's own lengths, by hand: thigh and shin 0.4, foot |(0, 0.1, -0.05)|, upper arm 0.3, forearm 0.25; standing
# height from the sole mesh's lowest point (0 m) to the head mesh's highest (1.6 m).
OWN = {"thigh": 0.4, "shin": 0.4, "foot": float(0.1 ** 2 + 0.05 ** 2) ** 0.5, "upper arm": 0.3, "forearm": 0.25}
HEIGHT = 1.6
KG = 50.0


def toy_body():
    """The toy body's MJCF: every body a sphere of 1 kg (a moving body needs a mass), the torso carrying a mesh up to
    1.6 m and each toes body a mesh down to 0 m."""
    sides = []
    for side, mirror in (("l", 1.0), ("r", -1.0)):
        for body, place, parent in CHAIN:
            x, y, z = (float(part) for part in place.split())
            mesh = '<geom type="mesh" mesh="sole" mass="0.1"/>' if body == "toes" else ""
            sides.append((f"{body}_{side}", f"{mirror * x:g} {y:g} {z:g}",
                          parent if parent in ("pelvis", "torso") else f"{parent}_{side}", mesh))

    def children(parent):
        return "".join(f'<body name="{name}" pos="{place}"><joint type="hinge" axis="1 0 0"/>'
                       f'<geom type="sphere" size="0.03" mass="1"/>{mesh}{children(name)}</body>'
                       for name, place, mine, mesh in sides if mine == parent)
    return f"""<mujoco model="toybody">
  <compiler angle="radian"/>
  <asset>
    <mesh name="head" vertex="-0.1 -0.1 0  0.1 -0.1 0  0 0.1 0  0 0 0.5"/>
    <mesh name="sole" vertex="-0.03 -0.03 0  0.03 -0.03 0  0 0.03 0  0 0 -0.05"/>
  </asset>
  <worldbody>
    <body name="pelvis" pos="0 0 1">
      <freejoint name="root"/>
      <geom type="sphere" size="0.1" mass="1"/>
      {children("pelvis")}
      <body name="torso" pos="0 0 0.1">
        <joint type="hinge" axis="1 0 0"/>
        <geom type="sphere" size="0.1" mass="1"/>
        <geom type="mesh" mesh="head" mass="0.1"/>
        {children("torso")}
      </body>
    </body>
  </worldbody>
</mujoco>
"""


def distance(model, data, first, second):
    import mujoco
    import numpy as np
    return float(np.linalg.norm(data.xpos[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, second)]
                                - data.xpos[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, first)]))


def a_sized_body_has_the_persons_limbs_and_mass():
    """Sized to limbs 1.1 times its own and its own height: every limb 1.1 times its own (within 1 mm), the pelvis
    and torso at scale 1, the torso where it was, the whole body KG."""
    import mujoco
    import sizing
    model = mujoco.MjModel.from_xml_string(toy_body())
    lengths = {f"{limb} {side}": 1.1 * length for limb, length in OWN.items() for side in sizing.SIDES}
    scales = sizing.scales_of(model, {**lengths, "height": HEIGHT})
    spec = mujoco.MjSpec.from_string(toy_body())
    sizing.sized(spec, model, scales, KG, 0)
    grown = spec.compile()
    data = mujoco.MjData(grown)
    mujoco.mj_forward(grown, data)
    problems = [f"{body} scale {scales[body]}, not 1" for body in ("pelvis", "torso") if abs(scales[body] - 1) > 1e-6]
    for limb, (start, end) in sizing.LIMBS.items():
        for side in sizing.SIDES:
            found = distance(grown, data, f"{start}_{side}", f"{end}_{side}")
            if abs(found - 1.1 * OWN[limb]) > 0.001:
                problems.append(f"{limb} {side}: {found:.4f} m, not {1.1 * OWN[limb]:.4f}")
    if abs(distance(grown, data, "pelvis", "torso") - 0.1) > 0.001:
        problems.append(f"the torso moved: {distance(grown, data, 'pelvis', 'torso'):.4f} m off the pelvis")
    return problems + ([] if abs(grown.body_mass.sum() - KG) < 1e-6 else [f"mass {grown.body_mass.sum()} kg"])


def the_persons_limbs_are_its_joint_distances():
    """A rig whose left leg's joints stand at heights 1, 0.55, 0.1 and toes 0.15 m forward of the foot, and whose
    arm's at 1.4, 1.1, 0.85 m (the right side the same mirrored): thigh 0.45, shin 0.45, foot 0.15, upper arm 0.3,
    forearm 0.25 m."""
    import numpy as np
    import sizing
    places = {"Leg": (0.1, 1.0, 0.0), "Shin": (0.1, 0.55, 0.0), "Foot": (0.1, 0.1, 0.0), "ToeBase": (0.1, 0.1, 0.15),
              "Arm": (0.2, 1.4, 0.0), "ForeArm": (0.2, 1.1, 0.0), "Hand": (0.2, 0.85, 0.0)}
    names, bind = [], []
    for side, mirror in (("Left", 1.0), ("Right", -1.0)):
        for joint, (x, y, z) in places.items():
            names.append(side + joint)
            pose = np.eye(4)
            pose[:3, 3] = mirror * x, y, z
            bind.append(pose.tolist())
    found = sizing.limb_lengths({"rig": {"names": names, "bind": bind}})
    wanted = {"thigh": 0.45, "shin": 0.45, "foot": 0.15, "upper arm": 0.3, "forearm": 0.25}
    return [f"{key}: {value}" for key, value in found.items() if abs(value - wanted[key.rsplit(" ", 1)[0]]) > 1e-9]


CHECKS = (a_sized_body_has_the_persons_limbs_and_mass, the_persons_limbs_are_its_joint_distances)


def in_newton():
    """The checks, in Newton's own Python."""
    sys.path.insert(0, str(INSIDE))
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    if os.environ.get(IN_ENV):
        sys.exit(in_newton())
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[5] / "conftest.py"))["refuse_outside_sandbox"]()
    env = pathlib.Path(os.environ["PROPS_HOME"]) / "envs/newton_env"
    if not list(env.glob(".built-*")):
        print(f"skipped: no Newton env built at {env} (score/stages/physics/inside/newton_env.sh)")
        sys.exit(0)
    sys.exit(subprocess.run([str(env / "bin/python"), "-B", __file__], env={**os.environ, IN_ENV: "1"}).returncode)
