"""fit: on a small model posed by hand (a free pelvis, a left leg of thigh and shin, a right leg whose ankle follows its
hip by a coupling, one thigh's calibration turned 30 degrees), with the person's constants set by hand (one pelvis
marker 1 cm off its link, the knee, a joint inside the left leg's group, 1 cm off its place), the solver gives back from
the bone groups' turns and the markers the marker's move (within its pull to its link) and the knee's (within its pull
to its place), and at those constants every frame's angles; a frame asking a hip past its range stops it at the range's
end, its coupled follower on its leader by the coupling, though the follower's own range is narrower; each marker weighs
its trust among the markers, the markers' goal (group ends included, one goal) MARKER_GOAL in all against the turns' 1;
a group end that is the middle of two bodies' centres (the hips') sits on their common holder (the pelvis) as one body's
sits on its own, one rule; the constants are the body's, sampled from every one of its recordings; SOMA's targets (its
segments' turns, its skin's landmarks and rig joints) leave both solves unchanged (#70: SOMA is never moved); a frame's
fit ends on a step that moves no task's error, though the step itself is not small. It runs in Newton's own Python (mink
pinned there; score/stages/physics/inside/newton_env.sh, built at $PROPS_HOME/envs/newton_env): with none built there,
as in `make tests`' sandbox home, it prints `skipped`.

Breaks (each applied once with the env linked into a sandbox home, seen red, reverted):
- (2026-10-28) Fitting's site `Rotation.from_matrix(calibration.T)` made `Rotation.from_matrix(calibration)`: the turned
  thigh's target is met by a wrong pose.
- (2026-10-28) limited_model's `found.jnt_limited[self.followers] = 0` dropped: the follower's own range stops its
  leader short.
- (2026-10-28) Frames' constraints `[mink.EqualityConstraintTask(...)]` made `[]`: the follower leaves its leader.
- (2026-10-29) Fitting.apply's `self.model.site_pos[self.mark_sites] += marks` dropped: the marker's move is not found.
- (2026-10-29) _frames.weights' `np.sqrt(trusts / max(trusts.sum(), 1e-12))` made `np.full(len(trusts), 1.0 /
  np.sqrt(len(trusts)))`: the low-trust marker weighs as much as the others.
- (2026-10-29) _frames.weights' `trusts.sum()` made `trusts[:-1].sum()`: a group end weighs on top of the markers' goal,
  not inside it.
- (2026-10-29) _frames.weights' `MARKER_GOAL * trusts` made `2 * trusts`: the markers' goal outweighs the turns'.
- (2026-10-29) sampled's `for turns, points in recordings` made `for turns, points in recordings[:1]`: the body's second
  recording is left out of its constants.
- (2026-10-29) Fitting.apply's `self.model.body_pos[self.inside] += joints` dropped: the knee's move is not found.
- (2026-10-29) angles' `Frames(fit).fitted(turns, points)` after `points[...] = points + 0.0`: SOMA's targets are moved
  by the solve.
- (2026-10-29) end_site's holder `next(body for body in _above(...) if all(...))` made `bodies[0]`: the hips' middle
  rides the left thigh.
- (2026-10-29) _frames.solved's `or moved < STEP_DONE` dropped: the hinge whose mass sits 1e-6 m off its axis drifts
  1e-3 rad a step and raises NotConverged.

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
      <freejoint name="root"/><geom type="box" size="0.15 0.1 0.1" mass="10"/>
      <body name="leg_l" pos="0.1 0 -0.1">
        <joint name="hip_l" type="hinge" axis="1 0 0" range="-1 1"/><geom type="capsule" fromto="0 0 0 0 0 -0.4" size="0.05" mass="5"/>
        <body name="shin_l" pos="0 0 -0.4">
          <joint name="knee_l" type="hinge" axis="1 0 0" range="-2 0"/><geom type="capsule" fromto="0 0 0 0 0 -0.4" size="0.04" mass="3"/>
        </body></body>
      <body name="leg_r" pos="-0.1 0 -0.1">
        <joint name="hip_r" type="hinge" axis="0 1 0" range="-1 1"/><geom type="capsule" fromto="0 0 0 0 0 -0.4" size="0.05" mass="5"/>
        <body name="foot_r" pos="0 0 -0.4">
          <joint name="ankle_r" type="hinge" axis="0 1 0" range="-0.4 0.4"/><geom type="box" size="0.05 0.1 0.02" mass="1"/>
        </body></body>
    </body></worldbody>
  <equality><joint joint1="ankle_r" joint2="hip_r" polycoef="0 0.5 0 0 0"/></equality>
</mujoco>
"""
MARKS = {"pelvis": [(0.15, 0.1, 0.0), (-0.15, 0.1, 0.0), (0.0, -0.1, 0.1)],
         "leg_l": [(0.05, 0.0, -0.2), (0.0, 0.05, -0.35)],
         "shin_l": [(0.04, 0.0, -0.2), (0.0, 0.04, -0.38)], "leg_r": [(-0.05, 0.0, -0.2), (0.0, 0.05, -0.35)],
         "foot_r": [(0.0, 0.1, -0.02)]}
BODIES = ("pelvis", "leg_l", "shin_l", "leg_r", "foot_r")  # each a turn site
TRUE_MOVE = ("pelvis1", (0.0, 0.01, 0.0))  # a marker 1 cm off its link, on its body
TRUE_JOINT = ("shin_l", (0.0, 0.01, 0.0))  # the knee 1 cm off its place in the thigh (a joint inside a group)
LEG_GROUPS = [{"leg_l", "shin_l"}, {"leg_r", "foot_r"}]  # the toy's two leg groups: the knee and ankle inside them
LOW_TRUST = ("pelvis2", 0.25)
# Each frame's root place, then hip_l, knee_l, hip_r (radians); the last asks hip_l past its range's end, 1.
POSES = [((0.0, 0.0, 1.0), 0.2, -0.4, 0.1), ((0.05, 0.0, 1.0), 0.4, -0.8, -0.3), ((0.1, 0.02, 0.98), 0.1, -1.2, 0.6),
         ((0.15, 0.03, 0.99), -0.3, -0.3, 0.9), ((0.2, 0.03, 1.0), -0.5, -0.1, 0.3),
         ((0.25, 0.03, 1.0), 1.3, -0.5, 0.2)]
MOST_RADIANS = 1e-4
# The marker's move is pulled to its link by one row at its own weight against the five frames' (found 2026-10-29: 7.1 mm
# of the true 10 mm, 10.0 with the pull dropped): along the true move at least MOVE_SHARE of it and no more than all of
# it, off that line by under MOST_METRES.
MOVE_SHARE = 0.5
MOST_METRES = 2e-3


def calibration(body):
    """A body's calibration turn: the left thigh's 30 degrees about its long axis, the others none."""
    from scipy.spatial.transform import Rotation
    return Rotation.from_euler("z", 30 if body == "leg_l" else 0, degrees=True).as_matrix()


def toy_fitting(folder):
    """The toy's `Fitting`: a turn site on every body (the left thigh's calibration 30 degrees about its long axis), its
    markers, one of them trusted a quarter."""
    import numpy as np
    from fit import Fitting
    path = pathlib.Path(folder) / "toy.xml"
    path.write_text(TOY)
    frames = [(body, body, calibration(body)) for body in BODIES]
    marks = [(f"{body}{number}", body, np.array(point)) for body, points in MARKS.items()
             for number, point in enumerate(points)]
    trusts = [LOW_TRUST[1] if name == LOW_TRUST[0] else 1.0 for name, _, _ in marks]
    return Fitting(path, frames, marks, (), trusts, LEG_GROUPS)


def posed_targets(fitting, truth, poses):
    """Each pose's group turns (each body's turn times its calibration's transpose, R_segment = R_body R_cal^T) and
    marker places on the toy at the constants `truth` (the model left neutral)."""
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
        points.append(data.site_xpos[fitting.mark_sites].copy())
        angles.append(qpos[7:11])
    fitting.apply(fitting.neutral())
    return np.array(turns), np.array(points), np.array(angles)


def truth_of(fitting):
    """The constants set by hand: TRUE_MOVE's marker and TRUE_JOINT's joint moved."""
    found = fitting.neutral()
    at = 3 * fitting.marks.index(TRUE_MOVE[0])
    found[at:at + 3] = TRUE_MOVE[1]
    at = 3 * (len(fitting.marks) + fitting.inside_names.index(TRUE_JOINT[0]))
    found[at:at + 3] = TRUE_JOINT[1]
    return found


def the_solver_gives_back_the_angles_and_the_constants():
    """TRUE_MOVE's marker and TRUE_JOINT's joint moved along their true moves by MOVE_SHARE to all of it, within MOST_METRES of that line; at the true constants every frame within reach (all but the last) within
    MOST_RADIANS of its angles."""
    import fit
    import numpy as np
    with tempfile.TemporaryDirectory() as folder:
        fitting = toy_fitting(folder)
        truth = truth_of(fitting)
        turns, points, angles = posed_targets(fitting, truth, POSES[:-1])
        found = fit.constants(fitting, [(turns[:2], points[:2]), (turns[2:], points[2:])])
        fitting.apply(truth)
        path = fit.angles(fitting, turns, points)
    problems = []
    off = np.abs(path[:, 7:11] - angles).max()
    if off > MOST_RADIANS:
        problems.append(f"angles off by up to {off:.6f} rad")
    for kind, (name, wanted) in (("marks", TRUE_MOVE), ("joints", TRUE_JOINT)):
        move, true = np.array(found[kind][name]), np.array(wanted)
        along = move @ true / (true @ true)
        if not MOVE_SHARE <= along <= 1.0 or np.linalg.norm(move - along * true) > MOST_METRES:
            problems.append(f"{name} moved {move}, not {wanted}")
    return problems


def every_recording_of_the_body_is_sampled():
    """The constants' frames from two recordings of the body (two frames and three): all five, in order, each posed
    from its own recording's start (at the true constants within MOST_RADIANS of its angles)."""
    import fit
    import numpy as np
    with tempfile.TemporaryDirectory() as folder:
        fitting = toy_fitting(folder)
        truth = truth_of(fitting)
        turns, points, angles = posed_targets(fitting, truth, POSES[:-1])
        fitting.apply(truth)
        found, _, path = fit.sampled(fitting, [(turns[:2], points[:2]), (turns[2:], points[2:])])
    if len(found) != len(turns) or not np.allclose(found, turns):
        return [f"{len(found)} frames sampled of the recordings' {len(turns)}"]
    off = np.abs(path[:, 7:11] - angles).max()
    return [] if off <= MOST_RADIANS else [f"the sampled frames' angles off by up to {off:.6f} rad"]


def somas_targets_leave_the_solves_unchanged():
    """The targets (SOMA's turns and points) read-only through the constants' and the angles' solves: no write to them
    (numpy refuses one) and the same values after."""
    import fit
    import numpy as np
    with tempfile.TemporaryDirectory() as folder:
        fitting = toy_fitting(folder)
        turns, points, _ = posed_targets(fitting, truth_of(fitting), POSES[:-1])
        kept = turns.copy(), points.copy()
        for target in (turns, points):
            target.setflags(write=False)
        try:
            fit.constants(fitting, [(turns[:2], points[:2]), (turns[2:], points[2:])])
            fit.angles(fitting, turns, points)
        except ValueError as refused:
            return [f"a solve wrote to SOMA's targets: {refused}"]
    return [] if np.array_equal(turns, kept[0]) and np.array_equal(points, kept[1]) else ["SOMA's targets changed"]


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


def each_marker_weighs_its_trust_and_the_markers_goal_the_turns_goal():
    """The toy's ten markers, one trusted 0.25: each place cost the square root of its trust over 9.25, each of the
    five turns one over the square root of 5; the markers' goal, every marker's (a group end's too) squared cost
    summed, is MARKER_GOAL, 1, the turns' goal's sum: the turns stay the main term."""
    import numpy as np
    from fit._frames import MARKER_GOAL, weights
    with tempfile.TemporaryDirectory() as folder:
        fitting = toy_fitting(folder)
        turn_cost, place_costs = weights(fitting)
    wanted = np.array([np.sqrt(MARKER_GOAL * (LOW_TRUST[1] if name == LOW_TRUST[0] else 1.0) / 9.25)
                       for name in fitting.marks])
    problems = [] if np.allclose(place_costs, wanted) else [f"place costs {place_costs.tolist()}"]
    problems += [] if np.isclose(turn_cost, 1 / np.sqrt(5)) else [f"turn cost {turn_cost}"]
    marker_sum, turn_sum = float(np.sum(place_costs ** 2)), turn_cost ** 2 * len(fitting.frame_sites)
    good = np.isclose(marker_sum, MARKER_GOAL) and np.isclose(marker_sum, turn_sum)
    return problems + ([] if good else [f"markers' goal {marker_sum}, turns' {turn_sum}"])


def the_place_goal_sums_to_the_marker_goal():
    """With MARKER_GOAL set to 4, the ten markers' squared costs sum to 4 and the five turns' to 1: one global
    balance for every landmark and group."""
    import numpy as np
    from fit import _frames
    kept = _frames.MARKER_GOAL
    _frames.MARKER_GOAL = 4.0
    try:
        with tempfile.TemporaryDirectory() as folder:
            turn_cost, place_costs = _frames.weights(toy_fitting(folder))
    finally:
        _frames.MARKER_GOAL = kept
    found, turns = float(np.sum(place_costs ** 2)), 5 * turn_cost ** 2
    return [] if np.isclose(found, 4.0) and np.isclose(turns, 1.0) else [f"places {found:.4f}, turns {turns:.4f}"]


def a_middle_end_sits_on_the_common_holder():
    """The toy's hips' middle (each thigh's origin, half each) lands on the pelvis between them; one body's point stays
    on that body as it is."""
    import mujoco
    import numpy as np
    from fit import end_site
    model = mujoco.MjModel.from_xml_string(TOY)
    found = [end_site(model, [("leg_l", np.zeros(3), 0.5), ("leg_r", np.zeros(3), 0.5)]),
             end_site(model, [("shin_l", np.array([0.0, 0.01, 0.0]), 1.0)])]
    wanted = [("pelvis", (0.0, 0.0, -0.1)), ("shin_l", (0.0, 0.01, 0.0))]
    return [f"{name} at {np.round(local, 4)}, not {body} {place}" for (name, local), (body, place) in zip(found, wanted)
            if name != body or not np.allclose(local, place, atol=1e-9)]


def a_step_no_task_sees_ends_the_fit():
    """A hinge whose mass sits 1e-6 m off its axis, pulled 1 m away: each step turns it 1e-3 rad and moves the mass 1e-9
    m, a direction its task barely sees (#70's arms_raise gimbal); the fit ends, its error as it was within a step."""
    import mink
    import mujoco
    import numpy as np
    from fit import _frames
    model = mujoco.MjModel.from_xml_string('<mujoco><worldbody><body><joint type="hinge" axis="0 0 1"/><inertial '
                                           'pos="1e-6 0 0" mass="1" diaginertia="1 1 1"/></body></worldbody></mujoco>')
    configuration, task = mink.Configuration(model), mink.ComTask(cost=1.0, lm_damping=_frames.LM_DAMPING)
    task.set_target(np.array([0.0, 1.0, 0.0]))
    before = task.compute_error(configuration)
    try:
        _frames.solved(configuration, [task], [], [])
    except _frames.NotConverged as error:
        return [str(error)]
    moved = np.linalg.norm(task.compute_error(configuration) - before)
    return [] if moved < 1e-6 else [f"its error moved {moved}"]


CHECKS = (a_middle_end_sits_on_the_common_holder, each_marker_weighs_its_trust_and_the_markers_goal_the_turns_goal,
          the_place_goal_sums_to_the_marker_goal, the_solver_gives_back_the_angles_and_the_constants,
          every_recording_of_the_body_is_sampled, somas_targets_leave_the_solves_unchanged, a_hip_past_its_range_stops_at_its_end_and_its_follower_follows,
          a_step_no_task_sees_ends_the_fit)


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
