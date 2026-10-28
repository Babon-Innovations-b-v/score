"""fit: on a clip made by posing a small model itself (a free pelvis and a hinged leg each side, every followed
segment riding one of them, their offsets the identity), the fit gives back the joint angles that posed it, and the
pelvis where the clip's Hips stand; the calibration frame is the standing clip's, else the bind's rows. It runs in
Newton's own Python (on a model Newton builds; score/stages/physics/inside/newton_env.sh, built at
$PROPS_HOME/envs/newton_env): with none built there, as in `make tests`' sandbox home, it prints `skipped`.

Breaks (each applied once with the env linked into a sandbox home, seen red, reverted), 2026-10-28:
- _fitted's error `(Rotation.from_matrix(target) * Rotation.from_matrix(...).inv()).as_rotvec()` made
  `(Rotation.from_matrix(...) * Rotation.from_matrix(target).inv()).as_rotvec()`: each step turns away from its
  target.
- calibration's `if person.get("standing") is not None` made `if False`: the standing clip is not used.

Run: .venv/bin/python score/stages/sim_body/inside/fit/test_the_fit_follows_the_clips_turns.py
"""
import os
import pathlib
import subprocess
import sys
import tempfile

INSIDE = pathlib.Path(__file__).resolve().parents[1]
IN_ENV = "SIM_BODY_INSIDE_TEST"
TOY = """<mujoco model="toy">
  <compiler angle="radian"/>
  <worldbody>
    <body name="pelvis" pos="0 0 1">
      <freejoint name="root"/>
      <geom type="box" size="0.15 0.1 0.1" mass="10"/>
      <body name="leg_l" pos="0.1 0 -0.1">
        <joint name="hip_l" type="hinge" axis="1 0 0" range="-2 2"/>
        <geom type="capsule" fromto="0 0 0 0 0 -0.8" size="0.05" mass="5"/>
      </body>
      <body name="leg_r" pos="-0.1 0 -0.1">
        <joint name="hip_r" type="hinge" axis="0 1 0" range="-2 2"/>
        <geom type="capsule" fromto="0 0 0 0 0 -0.8" size="0.05" mass="5"/>
      </body>
    </body>
  </worldbody>
</mujoco>
"""
FRAMES = 10
MOST_DEGREES = 0.5
MOST_METRES = 0.001


def posed_clip():
    """The toy model, its couplings, the person, its bodies, the clip (frames x segments x 4 x 4) and the qpos that
    posed it: the pelvis walking 2 cm a frame along x and turning 3 degrees a frame about up, the left hip swinging
    0.4 rad and the right 0.3 rad."""
    import mujoco
    import model
    import numpy as np
    from bone_groups import TARGETS, sided
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder) / "toy.xml"
        path.write_text(TOY)
        found = model.built(path, 9.81)
    couplings = model.Couplings(found)
    segments = sided(TARGETS)
    riding = {"Left": "leg_l", "Right": "leg_r"}
    bodies = {segment: model.body_index(found, next((body for side, body in riding.items()
                                                      if segment.startswith(side)), "pelvis"))
              for segment in segments}
    data, worlds, truth = mujoco.MjData(found), [], []
    for frame in range(FRAMES):
        qpos = found.qpos0.copy()
        qpos[:3] = [0.02 * frame, 0.0, 1.0]
        mujoco.mju_axisAngle2Quat(qpos[3:7], [0.0, 0.0, 1.0], np.radians(3.0 * frame))
        qpos[7:9] = 0.4 * np.sin(frame / 3), 0.3 * np.cos(frame / 4)
        data.qpos[:] = qpos
        mujoco.mj_kinematics(found, data)
        worlds.append([model.own_pose(found, data, bodies[segment]) for segment in segments])
        truth.append(qpos)
    return found, couplings, {"segments": segments}, bodies, np.array(worlds), np.array(truth)


def the_fit_gives_back_the_angles_that_posed_the_clip():
    """Every frame's hip angles within MOST_DEGREES of the ones that posed the clip and the pelvis within
    MOST_METRES of its place."""
    import fit
    import numpy as np
    found, couplings, person, bodies, worlds, truth = posed_clip()
    fixed = ({segment: np.eye(3) for segment in person["segments"]}, {"Hips": np.zeros(3)})
    path = fit.motion(found, couplings, person, worlds, bodies, fixed)
    angles = np.degrees(np.abs(path[:, 7:9] - truth[:, 7:9])).max()
    place = np.abs(path[:, :3] - truth[:, :3]).max()
    problems = [] if angles < MOST_DEGREES else [f"hip angles off by up to {angles:.3f} degrees"]
    return problems + ([] if place < MOST_METRES else [f"pelvis off by up to {place:.4f} m"])


def the_calibration_frame_is_the_standing_clips():
    """With a standing clip given, its frame; without, the bind's rows of the segments, in the segments' order."""
    import fit
    import numpy as np
    bind = np.tile(np.eye(4), (3, 1, 1))
    bind[:, 1, 3] = [0.0, 1.0, 2.0]
    standing = np.tile(np.eye(4), (2, 1, 1))
    standing[:, 0, 3] = 5.0
    rig = {"names": ["Root", "Hips", "LeftLeg"], "bind": bind.tolist()}
    given = fit.calibration({"rig": rig, "standing": standing.tolist()}, ["LeftLeg", "Hips"])
    bound = fit.calibration({"rig": rig, "standing": None}, ["LeftLeg", "Hips"])
    problems = [] if np.array_equal(given, standing) else ["the standing clip's frame is not used"]
    return problems + ([] if np.array_equal(bound[:, 1, 3], [2.0, 1.0]) else [f"bind rows {bound[:, 1, 3]}"])


CHECKS = (the_fit_gives_back_the_angles_that_posed_the_clip, the_calibration_frame_is_the_standing_clips)


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
