"""sizing: a small body built like MyoFullBody's legs and lower trunk (a pelvis, lumbar5 and lumbar3, each side's
femur, tibia, talus and toes), sized to a SOMA made of one thin box along each bone group's stretch, has every
group's stretch SOMA's length, every group's mass its box's volume at Dempster's density (all brought to the person's
mass with the bodies of no group kept), each group's centre of mass on its stretch's middle and each one-body group's
inertia its box's (all worked out by hand from the boxes). It runs in Newton's own Python (MuJoCo pinned there;
score/stages/physics/inside/newton_env.sh, built at $PROPS_HOME/envs/newton_env): with none built there, as in `make
tests`' sandbox home, it prints `skipped`.

Breaks (each applied once with the env linked into a sandbox home, seen red, reverted), 2026-10-28:
- sized's `np.asarray(body.pos) * (scale if body.name in OWN_PLACED else above)` made `np.asarray(body.pos)`: no
  group grows.
- weigh's `shift = target - masses @ data.xipos[index] / mass` made `shift = np.zeros(3)`: the centres stay the
  model's.
- volumes.weighed's `density(group) * 1000.0 * volume` made `1000.0 * volume`: every density one.
- weigh's `max((trace - spread) / max(own, 1e-12), INERTIA_FLOOR)` made `1.0`: the inertias stay the model's.

Run: .venv/bin/python score/stages/sim_body/inside/sizing/test_a_sized_group_is_somas_length_and_weight.py
"""
import os
import pathlib
import subprocess
import sys

INSIDE = pathlib.Path(__file__).resolve().parents[1]
IN_ENV = "SIM_BODY_INSIDE_TEST"
KG = 60.0
# The toy's bone groups, as bone_groups.GROUPS writes them (lumbar3 and toes in no group: their parent's scale).
TABLE = {"Hips": (("hipmid", "Spine1"), ("hipmid", "L5_S1"), "pelvis", ("pelvis",)),
         "Spine1": (("Spine1", "Spine2"), ("L5_S1", "L3_L4"), "lumbar5", ("lumbar5",)),
         **{f"{side}{segment}": ((f"{side}{segment}", f"{side}{end}"), (f"{start}_{letter}", f"{finish}_{letter}"),
                                 f"{body}_{letter}", (f"{body}_{letter}",))
            for side, letter in (("Left", "l"), ("Right", "r"))
            for segment, end, start, finish, body in (("Leg", "Shin", "hip", "knee", "femur"),
                                                      ("Shin", "Foot", "knee", "ankle", "tibia"),
                                                      ("Foot", "ToeBase", "ankle", "mtp", "talus"))}}
# SOMA's joints (own frame: Y up, +x left; the right side mirrored), and so its stretches: Hips 0.15, Spine1 0.1, Leg
# and Shin 0.45, Foot 0.15 m.
JOINTS = {"Hips": (0, 1.0, 0), "Spine1": (0, 1.15, 0), "Spine2": (0, 1.25, 0), "LeftLeg": (0.1, 1.0, 0),
          "LeftShin": (0.1, 0.55, 0), "LeftFoot": (0.1, 0.1, 0), "LeftToeBase": (0.1, 0.1, 0.15)}
LENGTHS = {"Hips": 0.15, "Spine1": 0.1, "Leg": 0.45, "Shin": 0.45, "Foot": 0.15}
DENSITY = {"Hips": 1.01, "Spine1": 1.01, "Leg": 1.05, "Shin": 1.09, "Foot": 1.10}  # Winter 2009 Table 4.1
# Each group's box: 0.04 x 0.04 m across, along the middle 60% of its stretch, so its centre is the stretch's middle.
SIDE, SHARE = 0.04, 0.6


def joints():
    found = dict(JOINTS)
    for name, (x, y, z) in JOINTS.items():
        if name.startswith("Left"):
            found["Right" + name[4:]] = (-x, y, z)
    return found


def box(start, end):
    """A closed box (8 points, 12 faces) along the middle SHARE of start to end (an axis line), SIDE across."""
    import numpy as np
    start, end = np.asarray(start, float), np.asarray(end, float)
    middle, along = (start + end) / 2, np.abs(end - start) * SHARE / 2
    half = np.where(along > 0, along, SIDE / 2)
    corners = np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]) * half + middle
    faces = [[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6],
             [0, 6, 4], [1, 5, 7], [1, 7, 3]]
    return corners, np.array(faces), half * 2


def toy_rig():
    """The toy SOMA: its joints, and one box a group (the Hips' from the hip joints' middle)."""
    import numpy as np
    places = joints()
    names = list(places)
    bind = np.tile(np.eye(4), (len(names), 1, 1))
    for index, name in enumerate(names):
        bind[index, :3, 3] = places[name]
    points, faces, sizes = [], [], {}
    for group, ((start, end), _, _, _) in TABLE.items():
        first = (np.asarray(places["LeftLeg"]) + places["RightLeg"]) / 2 if start == "hipmid" else places[start]
        corners, mine, size = box(first, places[end])
        faces.append(mine + 8 * len(points))
        points.append(corners)
        sizes[group] = size
    return {"names": names, "bind": bind, "points": np.concatenate(points), "faces": np.concatenate(faces),
            "weights": np.zeros((8 * len(points), len(names)))}, sizes


def toy_body():
    """The toy MJCF (MuJoCo's frame, Z up, the model's left +x): every body a 1 kg sphere; the hips 0.1 m down and
    0.1 m to each side of the pelvis, lumbar5 0.1 m up, lumbar3 0.08 m over it; femur and tibia 0.4 m, the toes 0.1 m
    forward (MuJoCo's -y) of the talus. Its stretches: Hips 0.2, Spine1 0.08, Leg and Shin 0.4, Foot 0.1 m."""
    sides = ""
    for letter, mirror in (("l", 1), ("r", -1)):
        sides += (f'<body name="femur_{letter}" pos="{0.1 * mirror} 0 -0.1"><joint type="hinge" axis="1 0 0"/>'
                  f'<geom type="sphere" size="0.03" mass="1"/><body name="tibia_{letter}" pos="0 0 -0.4">'
                  f'<joint type="hinge" axis="1 0 0"/><geom type="sphere" size="0.03" mass="1"/>'
                  f'<body name="talus_{letter}" pos="0 0 -0.4"><joint type="hinge" axis="1 0 0"/>'
                  f'<geom type="sphere" size="0.03" mass="1"/><body name="toes_{letter}" pos="0 -0.1 0">'
                  f'<joint type="hinge" axis="1 0 0"/><geom type="sphere" size="0.02" mass="1"/>'
                  f'</body></body></body></body>')
    return f"""<mujoco model="toybody"><worldbody><body name="pelvis" pos="0 0 1"><freejoint name="root"/>
      <geom type="sphere" size="0.05" mass="1"/>{sides}
      <body name="lumbar5" pos="0 0 0.1"><joint type="hinge" axis="1 0 0"/><geom type="sphere" size="0.03" mass="1"/>
        <body name="lumbar3" pos="0 0 0.08"><joint type="hinge" axis="1 0 0"/>
          <geom type="sphere" size="0.03" mass="1"/></body></body></body></worldbody></mujoco>"""


def sized_toy():
    """The toy sized and weighed to the toy SOMA: (final model, its body scales, the boxes' sizes)."""
    import mujoco
    import sizing
    from model import TO_OWN
    rig, sizes = toy_rig()
    size = sizing.Size(rig, TABLE, turns={group: TO_OWN for group in TABLE})
    source = mujoco.MjModel.from_xml_string(toy_body())
    scales = size.scales(source)
    spec = mujoco.MjSpec.from_string(toy_body())
    sizing.sized(spec, source, scales, KG, 0)
    grown = spec.compile()
    size.weigh(spec, grown, scales, KG - sizing.ungrouped_kg(grown, TABLE))
    return spec.compile(), scales, sizes


def every_group_is_somas_length_mass_and_centre():
    """Each stretch SOMA's length within 1 mm; each group's mass KG less the bodies of no group (lumbar3, the toes)
    shared by box volume times density within 0.1%; the whole body KG; each group's centre of mass on its stretch's
    middle within 1 mm; each group's inertia's trace its box's, m (a2 + b2 + c2) / 6, within 0.5%."""
    import mujoco
    import numpy as np
    import sizing
    from model import Couplings, default_pose
    final, scales, sizes = sized_toy()
    problems = []
    found = sizing.myo_lengths(final, scales, TABLE)
    for group, length in found.items():
        if abs(length - LENGTHS[group.removeprefix("Left").removeprefix("Right")]) > 0.001:
            problems.append(f"{group} {length:.4f} m")
    loose = sum(final.body_mass[mujoco.mj_name2id(final, mujoco.mjtObj.mjOBJ_BODY, name)]
                for name in ("lumbar3", "toes_l", "toes_r"))
    weighted = {group: DENSITY[group.removeprefix("Left").removeprefix("Right")] * np.prod(sizes[group])
                for group in TABLE}
    data = default_pose(final, Couplings(final))
    for group, (_, (start, end), frame, _) in TABLE.items():
        body = mujoco.mj_name2id(final, mujoco.mjtObj.mjOBJ_BODY, frame)
        wanted = (KG - loose) * weighted[group] / sum(weighted.values())
        if abs(final.body_mass[body] - wanted) > 0.001 * wanted:
            problems.append(f"{group} {final.body_mass[body]:.4f} kg, not {wanted:.4f}")
        middle = (sizing.myo_point(final, data, start, scales) + sizing.myo_point(final, data, end, scales)) / 2
        if np.linalg.norm(data.xipos[body] - middle) > 0.001:
            problems.append(f"{group}'s centre {np.round(data.xipos[body], 4)}, not {np.round(middle, 4)}")
        trace = final.body_mass[body] * float(np.sum(sizes[group] ** 2)) / 6
        if abs(final.body_inertia[body].sum() - trace) > 0.005 * trace:
            problems.append(f"{group}'s inertia trace {final.body_inertia[body].sum():.6f}, not {trace:.6f}")
    return problems + ([] if abs(final.body_mass.sum() - KG) < 1e-6 else [f"mass {final.body_mass.sum()} kg"])


CHECKS = (every_group_is_somas_length_mass_and_centre,)


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
