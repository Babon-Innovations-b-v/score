"""contact: the ground pushes a ball only where its surface comes within GAP of the drawn ground, inside a friction
pyramid when slow and sliding against its slip when fast; a foot stands in the clip's frames where it is low and
still; and a path is moved once so its lowest point stands on the ground at its median frame (all worked by hand).
It runs in Newton's own Python (MuJoCo pinned there; score/stages/physics/inside/newton_env.sh, built at
$PROPS_HOME/envs/newton_env): with none built there, as in `make tests`' sandbox home, it prints `skipped`.

Breaks (each applied once with the env linked into a sandbox home, seen red, reverted), 2026-10-28:
- pushes' `<= GAP` made `<= 1.0`: a ball 6 mm over the ground is pushed.
- pushes' `np.linalg.norm(moving) > SLIDE_MOST` made `< SLIDE_MOST`: a slow point slides and a fast one sticks.
- stances' `low & (speed < STILL)` made `low`: a foot leaving the ground at 6 m/s still stands.

Run: .venv/bin/python score/stages/sim_body/inside/contact/test_only_a_point_within_gap_is_pushed.py
"""
import os
import pathlib
import subprocess
import sys

INSIDE = pathlib.Path(__file__).resolve().parents[1]
IN_ENV = "SIM_BODY_INSIDE_TEST"
BALL = """<mujoco model="ball">
  <worldbody>
    <body name="ball" pos="0 0 1">
      <freejoint/>
      <geom name="ball" type="sphere" size="0.05" mass="1"/>
    </body>
  </worldbody>
</mujoco>
"""


def flat():
    """The ground: a 10 m square at height 0 (the person's frame, Y up), two triangles."""
    import numpy as np
    return np.array([[[-5.0, 0.0, -5.0], [5.0, 0.0, 5.0], [5.0, 0.0, -5.0]],
                     [[-5.0, 0.0, -5.0], [-5.0, 0.0, 5.0], [5.0, 0.0, 5.0]]])


def ball_at(height, speed=0.0):
    """The ball's model and its data with its centre `height` metres up (MuJoCo's frame, Z up), moving `speed` m/s
    along x."""
    import mujoco
    model = mujoco.MjModel.from_xml_string(BALL)
    data = mujoco.MjData(model)
    data.qpos[2], data.qvel[0] = height, speed
    mujoco.mj_forward(model, data)
    return model, data


def only_a_point_within_gap_is_pushed():
    """The ball (5 cm) with its bottom 4 mm over the ground: its one lowest surface point is pushed, along the four
    edges of the friction pyramid (normal up, plus or minus FRICTION across); 6 mm over it, nothing is pushed."""
    import contact
    import ground
    import numpy as np
    up = ground.normals(flat())
    near = contact.pushes(*ball_at(0.054), flat(), up, [0])
    far = contact.pushes(*ball_at(0.056), flat(), up, [0])
    problems = [] if len(near) == 1 and len(near[0][2]) == 4 else [f"4 mm over: {len(near)} points pushed"]
    if near and not np.allclose(sorted(np.round(edge, 9).tolist() for edge in near[0][2]),
                                sorted([[0.0, 0.5, 1.0], [0.0, -0.5, 1.0], [0.5, 0.0, 1.0], [-0.5, 0.0, 1.0]])):
        problems.append(f"4 mm over: edges {[edge.tolist() for edge in near[0][2]]}")
    return problems + ([] if not far else [f"6 mm over: {len(far)} points pushed"])


def a_fast_point_slides_against_its_slip():
    """The same ball moving 2 m/s along x (over SLIDE_MOST, 1.2 m/s): one edge, the normal and FRICTION of it
    against the slip, (-0.5, 0, 1)."""
    import contact
    import ground
    import numpy as np
    found = contact.pushes(*ball_at(0.054, 2.0), flat(), ground.normals(flat()), [0])
    edges = found[0][2] if found else []
    return [] if len(edges) == 1 and np.allclose(edges[0], [-0.5, 0.0, 1.0]) else [f"sliding edges {edges}"]


def a_foot_stands_where_it_is_low_and_still():
    """A foot standing 0.1 m over the ground in the calibration frame stays there for frames 0 to 4, then stands 0.5
    m up for frames 5 to 9 (30 frames a second): it stands in frames 0 to 3 (frame 4's central difference with frame
    5 is 6 m/s) and in none of the high ones; a path whose ball stands 1, 2 and 3 cm over the ground is moved 2 cm
    down (its median frame's)."""
    import contact
    import numpy as np
    worlds = np.tile(np.eye(4), (10, 1, 1, 1))
    worlds[:5, 0, 1, 3], worlds[5:, 0, 1, 3] = 0.1, 0.5
    standing = np.eye(4)[None].copy()
    standing[0, 1, 3] = 0.1
    found = contact.stances(standing, ["LeftFoot"], worlds, flat(), 30.0)
    problems = [] if [frame for frame, feet in enumerate(found) if "LeftFoot" in feet] == [0, 1, 2, 3] else [
        f"standing frames {[frame for frame, feet in enumerate(found) if feet]}"]
    model, _ = ball_at(0.0)
    path = np.tile(model.qpos0, (3, 1))
    path[:, 2] = [0.06, 0.07, 0.08]
    moved, shift = contact.grounded(model, path, [0], flat(), "ball")
    return problems + ([] if np.isclose(shift, -0.02) and np.allclose(moved[:, 2], [0.04, 0.05, 0.06]) else
                       [f"grounded by {shift}: {moved[:, 2]}"])


CHECKS = (only_a_point_within_gap_is_pushed, a_fast_point_slides_against_its_slip,
          a_foot_stands_where_it_is_low_and_still)


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
