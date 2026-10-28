"""myo: the person's file written from a small body laid out as MyoFullBody's wheel has it (a floor, a body with two
joints, a muscle whose class gives its parameters, names with '-'), sized to a toy SOMA (each thigh and shin a box),
compiles in MuJoCo and builds in Newton with the
same joints, one joint a body, no '-' in a name, no floor, the person's mass, and every muscle's gain and bias in
Newton's model the published model's (#60's import fixes). It runs in Newton's own Python
(score/stages/physics/inside/newton_env.sh, built at $PROPS_HOME/envs/newton_env): with none built there, as in `make
tests`' sandbox home, it prints `skipped`.

Breaks (each applied once with the env linked into a sandbox home, seen red, reverted), 2026-10-28:
- person_file's `split(full_muscles(renamed(xml), final))` made `full_muscles(renamed(xml), final)`: a body keeps two
  joints.
- person_file's `split(full_muscles(renamed(xml), final))` made `split(full_muscles(xml, final))`: names keep '-'.
- person_file's `split(full_muscles(renamed(xml), final))` made `split(renamed(xml))`: the muscle's partial
  gainprm loses its class's range and Newton refuses it ("lmin<1<lmax required in muscle").
- person_file's `spec.delete(geom)` made `pass`: the floor stays.

Run: .venv/bin/python score/stages/sim_body/inside/myo/test_the_persons_file_builds_in_newton_as_mujoco_compiles_it.py
"""
import os
import pathlib
import re
import subprocess
import sys
import tempfile

INSIDE = pathlib.Path(__file__).resolve().parents[1]
IN_ENV = "SIM_BODY_INSIDE_TEST"
# Each side's chain: (body, its place in its parent's frame, its parent); x is mirrored for the right side.
CHAIN = (("femur", "0.1 0 -0.1", "pelvis"), ("tibia", "0 0 -0.4", "femur"), ("talus", "0 0 -0.4", "tibia"),
         ("toes", "0 0.1 -0.05", "talus"), ("humerus", "0.2 0 0.4", "torso"), ("ulna", "0 0 -0.3", "humerus"),
         ("lunate", "0 0 -0.25", "ulna"))
KG = 50.0
# The toy's bone groups: each side's thigh and shin (bone_groups.GROUPS' shape); the rest take their parent's scale.
TABLE = {f"{side}{segment}": ((f"{side}{segment}", f"{side}{end}"), (f"{start}_{letter}", f"{finish}_{letter}"),
                              f"{body}_{letter}", (f"{body}_{letter}",))
         for side, letter in (("Left", "l"), ("Right", "r"))
         for segment, end, start, finish, body in (("Leg", "Shin", "hip", "knee", "femur"),
                                                   ("Shin", "Foot", "knee", "ankle", "tibia"))}
# The toy SOMA's joints (own frame, +x left; the right side mirrored): thigh and shin 0.44 m.
JOINTS = {"LeftLeg": (0.1, 1.0, 0.0), "LeftShin": (0.1, 0.56, 0.0), "LeftFoot": (0.1, 0.12, 0.0),
          "LeftArm": (0.2, 1.4, 0.0)}


def toy_size():
    """The toy SOMA (its joints and a 0.04 m box along each stretch) as a `sizing.Size`."""
    import numpy as np
    import sizing
    places = {**JOINTS, **{"Right" + name[4:]: (-x, y, z) for name, (x, y, z) in JOINTS.items()}}
    names = list(places)
    bind = np.tile(np.eye(4), (len(names), 1, 1))
    bind[:, :3, 3] = [places[name] for name in names]
    unit = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], dtype=float)
    faces = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6],
                      [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    points = [unit * [0.02, 0.15, 0.02] + (np.asarray(places[start]) + places[end]) / 2
              for (start, end), _, _, _ in TABLE.values()]
    rig = {"names": names, "bind": bind, "points": np.concatenate(points),
           "faces": np.concatenate([faces + 8 * index for index in range(len(points))]),
           "weights": np.zeros((8 * len(points), len(names)))}
    return sizing.Size(rig, TABLE)


def toy_body():
    """The toy body's MJCF as MyoFullBody's wheel has it: a floor, every body a sphere of 1 kg (a moving body needs a
    mass), the torso with two joints and carrying a mesh up to 1.6 m, each toes body a mesh down to 0 m, one muscle
    of a class with partial parameters from the pelvis to the left tibia, names with '-'."""
    sides = []
    for side, mirror in (("l", 1.0), ("r", -1.0)):
        for body, place, parent in CHAIN:
            x, y, z = (float(part) for part in place.split())
            mesh = '<geom type="mesh" mesh="sole" mass="0.1"/>' if body == "toes" else ""
            mesh += '<site name="rect-fem-insertion" pos="0 0.05 -0.1"/>' if (body, side) == ("tibia", "l") else ""
            sides.append((f"{body}_{side}", f"{mirror * x:g} {y:g} {z:g}",
                          parent if parent in ("pelvis", "torso") else f"{parent}_{side}", mesh))

    def children(parent):
        return "".join(f'<body name="{name}" pos="{place}"><joint type="hinge" axis="1 0 0"/>'
                       f'<geom type="sphere" size="0.03" mass="1"/>{mesh}{children(name)}</body>'
                       for name, place, mine, mesh in sides if mine == parent)
    return f"""<mujoco model="toybody">
  <compiler angle="radian"/>
  <default>
    <default class="muscle">
      <muscle ctrllimited="true" ctrlrange="0 1" scale="200"/>
    </default>
  </default>
  <asset>
    <mesh name="head" vertex="-0.1 -0.1 0  0.1 -0.1 0  0 0.1 0  0 0 0.5"/>
    <mesh name="sole" vertex="-0.03 -0.03 0  0.03 -0.03 0  0 0.03 0  0 0 -0.05"/>
  </asset>
  <worldbody>
    <geom name="floor" type="plane" size="5 5 0.1"/>
    <body name="pelvis" pos="0 0 1">
      <freejoint name="root"/>
      <geom type="sphere" size="0.1" mass="1"/>
      <site name="rect-fem-origin" pos="0.1 0.1 -0.05"/>
      {children("pelvis")}
      <body name="torso" pos="0 0 0.1">
        <joint name="lumbar-flex" type="hinge" axis="1 0 0"/>
        <joint name="lumbar-bend" type="hinge" axis="0 1 0"/>
        <geom type="sphere" size="0.1" mass="1"/>
        <geom type="mesh" mesh="head" mass="0.1"/>
        {children("torso")}
      </body>
    </body>
  </worldbody>
  <tendon>
    <spatial name="rect_fem">
      <site site="rect-fem-origin"/>
      <site site="rect-fem-insertion"/>
    </spatial>
  </tendon>
  <actuator>
    <muscle name="rect_fem" class="muscle" tendon="rect_fem" force="500"/>
  </actuator>
</mujoco>
"""




def written(folder):
    """The person's file written from the toy wheel in `folder`, its text, its record and its two compiles: MuJoCo's
    and Newton's."""
    import mujoco
    import model
    import myo
    source = pathlib.Path(folder) / myo.SOURCE
    source.parent.mkdir(parents=True)
    source.write_text(toy_body())
    path = pathlib.Path(folder) / "person.xml"
    record = myo.person_file(folder, toy_size(), KG, path)
    return path.read_text(), record, mujoco.MjModel.from_xml_path(str(path)), model.built(path, 9.81)


def the_written_file_builds_as_it_compiles():
    """MuJoCo's compile and Newton's build of the written file have the same joints; every body one joint at most; no
    name with '-'; nothing in the world body (the floor gone); the record's mass the person's."""
    import numpy as np
    with tempfile.TemporaryDirectory() as folder:
        text, record, compiled, built = written(folder)
    problems = [] if (compiled.nq, compiled.nv) == (built.nq, built.nv) else [
        f"MuJoCo nq {compiled.nq} nv {compiled.nv}, Newton nq {built.nq} nv {built.nv}"]
    joints = np.bincount(compiled.jnt_bodyid, minlength=compiled.nbody)
    problems += [] if joints.max() <= 1 else [f"{int((joints > 1).sum())} bodies with several joints"]
    named = [name for name in re.findall(r'\bname="([^"]*)"', text) if "-" in name]
    problems += [] if not named else [f"names with '-': {named}"]
    problems += [] if not (compiled.geom_bodyid == 0).any() else ["a geom in the world body (the floor)"]
    return problems + ([] if abs(record["kg"] - KG) < 1e-3 else [f"record kg {record['kg']}"])


def every_muscle_keeps_its_published_parameters_in_newton():
    """The muscle's gain and bias parameters in Newton's model are the published model's compile (to 1e-6)."""
    import mujoco
    import myo
    import numpy as np
    with tempfile.TemporaryDirectory() as folder:
        _, _, _, built = written(folder)
        source = mujoco.MjModel.from_xml_path(str(pathlib.Path(folder) / myo.SOURCE))
    problems = []
    for field in ("gainprm", "biasprm"):
        theirs, ours = getattr(source, "actuator_" + field)[:, :9], getattr(built, "actuator_" + field)[:, :9]
        if theirs.shape != ours.shape or not np.allclose(theirs, ours, rtol=1e-6, atol=1e-6):
            problems.append(f"{field}: Newton {ours.round(4).tolist()}, published {theirs.round(4).tolist()}")
    return problems


CHECKS = (the_written_file_builds_as_it_compiles, every_muscle_keeps_its_published_parameters_in_newton)


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
