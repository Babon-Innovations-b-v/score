"""fit: on a small model posed by hand (a free pelvis, a left leg of thigh and shin, a right leg whose ankle follows its
hip by a coupling, one thigh's calibration turned 30 degrees), with the person's constants set by hand (the left
group 8% longer, the left hip moved 2 cm), the solver gives back from the bone groups' turns, the markers and one
SOMA joint on its centre (the left ankle) every frame's angles, the size factor and the hip's move; a frame asking a
hip past its range stops it at the range's end, its coupled follower on its leader by the coupling, though the
follower's own range is narrower. The size is solved, not held (#70, 2026-10-29). It runs in Newton's own Python (mink pinned there; score/stages/physics/inside/newton_env.sh, built at
$PROPS_HOME/envs/newton_env): with none built there, as in `make tests`' sandbox home, it prints `skipped`.

Breaks (each applied once with the env linked into a sandbox home, seen red, reverted), 2026-10-28:
- Fitting's site `Rotation.from_matrix(calibration.T)` made `Rotation.from_matrix(calibration)`: the turned
  thigh's target is met by a wrong pose.
- Fitting.apply's `self.model.body_pos[self.joint_bodies] += joints` dropped: the hip's move is not found.
- Fitting's `for site in self.place_sites])` (the sites a group's size carries) made `for site in self.mark_sites])`:
  the sizes no longer reach the centre sites (the ankle's), and the solve fails.
- limited_model's `found.jnt_limited[self.followers] = 0` dropped: the follower's own range stops its leader short.
- Frames' constraints `[mink.EqualityConstraintTask(...)]` made `[]`: the follower leaves its leader.
- _frames.weights' `np.full(marks, 1.0 / np.sqrt(max(marks, 1)))` made `np.full(marks, 0.0)`: no marker sees a
  length.
- (2026-10-29) a row holding the left group to its start length (`(factors[0] - 1.0) * 100`, the old LENGTH_WEIGHT
  hold) added to Problem.residuals: the factor stays near 1, not TRUE_LEFT.

Run: .venv/bin/python score/stages/sim_body/inside/fit/test_the_solver_gives_back_the_pose_and_constants_that_made_its_targets.py
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
        <joint name="hip_l" type="hinge" axis="1 0 0" range="-1 1"/>
        <geom type="capsule" fromto="0 0 0 0 0 -0.4" size="0.05" mass="5"/>
        <body name="shin_l" pos="0 0 -0.4">
          <joint name="knee_l" type="hinge" axis="1 0 0" range="-2 0"/>
          <geom type="capsule" fromto="0 0 0 0 0 -0.4" size="0.04" mass="3"/>
        </body>
      </body>
      <body name="leg_r" pos="-0.1 0 -0.1">
        <joint name="hip_r" type="hinge" axis="0 1 0" range="-1 1"/>
        <geom type="capsule" fromto="0 0 0 0 0 -0.4" size="0.05" mass="5"/>
        <body name="foot_r" pos="0 0 -0.4">
          <joint name="ankle_r" type="hinge" axis="0 1 0" range="-0.4 0.4"/>
          <geom type="box" size="0.05 0.1 0.02" mass="1"/>
        </body>
      </body>
    </body>
  </worldbody>
  <equality>
    <joint joint1="ankle_r" joint2="hip_r" polycoef="0 0.5 0 0 0"/>
  </equality>
</mujoco>
"""
MARKS = {"pelvis": [(0.15, 0.1, 0.0), (-0.15, 0.1, 0.0), (0.0, -0.1, 0.1)],
         "leg_l": [(0.05, 0.0, -0.2), (0.0, 0.05, -0.35)],
         "shin_l": [(0.04, 0.0, -0.2), (0.0, 0.04, -0.38)], "leg_r": [(-0.05, 0.0, -0.2), (0.0, 0.05, -0.35)],
         "foot_r": [(0.0, 0.1, -0.02)]}
OWNERS = {"pelvis": "trunk", "leg_l": "left", "shin_l": "left", "leg_r": "right", "foot_r": "right"}
TRUE_LEFT = 1.08
ANKLE = (0.0, 0.0, -0.4)  # SOMA's left ankle on the shin: a joint centre site, sized with the left group
TRUE_HIP = (0.0, 0.02, 0.0)
# Each frame's root place, then hip_l, knee_l, hip_r (radians); the last asks hip_l past its range's end, 1.
POSES = [((0.0, 0.0, 1.0), 0.2, -0.4, 0.1), ((0.05, 0.0, 1.0), 0.4, -0.8, -0.3), ((0.1, 0.02, 0.98), 0.1, -1.2, 0.6),
         ((0.15, 0.03, 0.99), -0.3, -0.3, 0.9), ((0.2, 0.03, 1.0), -0.5, -0.1, 0.3),
         ((0.25, 0.03, 1.0), 1.3, -0.5, 0.2)]
MOST_RADIANS = 1e-4
MOST_FACTOR = 1e-4
MOST_METRES = 1e-4


def calibration(body):
    """A body's calibration turn: the left thigh's 30 degrees about its long axis, the others none."""
    from scipy.spatial.transform import Rotation
    return Rotation.from_euler("z", 30 if body == "leg_l" else 0, degrees=True).as_matrix()


def toy_fitting(folder):
    """The toy's `Fitting`: a turn site on every body (the left thigh's calibration 30 degrees about its long axis), its
    markers, the left hip's centre free to move."""
    import numpy as np
    from fit import Fitting
    path = pathlib.Path(folder) / "toy.xml"
    path.write_text(TOY)
    frames = [(body, body, calibration(body)) for body in OWNERS]
    marks = [(f"{body}{number}", body, np.array(point)) for body, points in MARKS.items()
             for number, point in enumerate(points)]
    return Fitting(path, frames, marks, OWNERS, (), [("hip_l", "leg_l")], (), [("ankle_l", "shin_l", ANKLE)])


def posed_targets(fitting, truth, poses):
    """Each pose's group turns (each body's turn times its calibration's transpose, R_segment = R_body R_cal^T) and
    places (the markers', then the left ankle's: ANKLE on the shin, TRUE_LEFT longer) on the toy at the constants
    `truth` (the model left neutral)."""
    import mujoco
    import numpy as np
    model, data = fitting.model, mujoco.MjData(fitting.model)
    fitting.apply(truth)
    turns, points, angles = [], [], []
    for place, hip_l, knee_l, hip_r in poses:
        qpos = model.qpos0.copy()
        qpos[:3] = place
        qpos[7:11] = hip_l, knee_l, hip_r, 0.5 * hip_r
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        turns.append([data.xmat[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body)].reshape(3, 3)
                      @ calibration(body).T for body in fitting.groups])
        shin = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "shin_l")
        ankle = data.xpos[shin] + data.xmat[shin].reshape(3, 3) @ (TRUE_LEFT * np.array(ANKLE))
        points.append(np.concatenate([data.site_xpos[fitting.mark_sites], [ankle]]))
        angles.append(qpos[7:11])
    fitting.apply(fitting.neutral())
    return np.array(turns), np.array(points), np.array(angles)


def truth_of(fitting):
    """The constants set by hand: the left group TRUE_LEFT long, the left hip moved TRUE_HIP, no marker moved."""
    found = fitting.neutral()
    found[fitting.sizes.index("left")] = TRUE_LEFT
    found[len(fitting.sizes):len(fitting.sizes) + 3] = TRUE_HIP
    return found


def the_solver_gives_back_the_angles_and_the_constants():
    """Every frame within reach (all but the last) within MOST_RADIANS of its angles; the size factor within
    MOST_FACTOR of TRUE_LEFT and the hip's move within MOST_METRES of TRUE_HIP."""
    import fit
    import numpy as np
    with tempfile.TemporaryDirectory() as folder:
        fitting = toy_fitting(folder)
        turns, points, angles = posed_targets(fitting, truth_of(fitting), POSES[:-1])
        found = fit.constants(fitting, turns, points)
        path = fit.angles(fitting, turns, points)
    problems = []
    off = np.abs(path[:, 7:11] - angles).max()
    if off > MOST_RADIANS:
        problems.append(f"angles off by up to {off:.6f} rad")
    if abs(found["sizes"]["left"] - TRUE_LEFT) > MOST_FACTOR:
        problems.append(f"the left group's factor {found['sizes']['left']:.6f}, not {TRUE_LEFT}")
    hip = np.array(found["joints"]["leg_l"])
    if np.abs(hip - TRUE_HIP).max() > MOST_METRES:
        problems.append(f"the left hip moved {hip}, not {TRUE_HIP}")
    return problems


def a_hip_past_its_range_stops_at_its_end_and_its_follower_follows():
    """The last frame's left hip at its range's end (1 rad) within MOST_RADIANS; on every frame the right ankle 0.5
    times the right hip within MOST_RADIANS (its own range, 0.4, narrower than 0.5 times the hip's 0.9)."""
    import fit
    import numpy as np
    with tempfile.TemporaryDirectory() as folder:
        fitting = toy_fitting(folder)
        turns, points, _ = posed_targets(fitting, truth_of(fitting), POSES)
        fitting.apply(truth_of(fitting))
        path = fit.angles(fitting, turns, points)
    problems = [] if abs(path[-1, 7] - 1.0) < MOST_RADIANS else [f"the hip past its range stands at {path[-1, 7]}"]
    follower = np.abs(path[:, 10] - 0.5 * path[:, 9]).max()
    if follower > MOST_RADIANS:
        problems.append(f"the ankle leaves its coupling by up to {follower:.6f} rad")
    reached = np.abs(path[3, 9] - POSES[3][3])
    return problems + ([] if reached < MOST_RADIANS else [f"the right hip stopped {reached:.4f} rad short of 0.9"])


CHECKS = (the_solver_gives_back_the_angles_and_the_constants,
          a_hip_past_its_range_stops_at_its_end_and_its_follower_follows)


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
