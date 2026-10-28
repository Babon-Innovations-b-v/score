"""muscles: a body standing still on a flat ground under gravity is carried by the ground: the static optimisation
gives the ground's push its weight and leaves almost no residual on the pelvis, and the movement's needed force is
its weight up. It runs in Newton's own Python (on a model Newton builds; score/stages/physics/inside/newton_env.sh,
built at $PROPS_HOME/envs/newton_env): with none built there, as in `make tests`' sandbox home, it prints `skipped`.

Breaks (each applied once with the env linked into a sandbox home, seen red, reverted), 2026-10-28:
- shared's `rows[:6] = BALANCE` made `rows[:6] = 0.0`: the pelvis' balance costs nothing, so the ground pushes
  nothing and the weight is left as residual.
- needed's `found + model.dof_armature * qacc - data.qfrc_passive` made `-found + ...`: the movement asks for its
  weight down.

Run: .venv/bin/python score/stages/sim_body/inside/muscles/test_a_standing_body_is_carried_by_the_ground.py
"""
import os
import pathlib
import subprocess
import sys
import tempfile

INSIDE = pathlib.Path(__file__).resolve().parents[1]
IN_ENV = "SIM_BODY_INSIDE_TEST"
KG = 10.0
GRAVITY = 9.81
BODY = """<mujoco model="block">
  <compiler angle="radian"/>
  <worldbody>
    <body name="pelvis" pos="0 0 0.101">
      <freejoint name="root"/>
      <geom type="sphere" size="0.1" mass="10"/>
    </body>
  </worldbody>
</mujoco>
"""


def the_ground_carries_a_still_body():
    """A 10 kg ball standing 1 mm over a flat ground, still: the movement needs 98.1 N up at the pelvis, the ground's
    push sums to it within 1% and the pelvis' residual force is under 1% of it."""
    import model as built_model
    import muscles
    import numpy as np
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder) / "block.xml"
        path.write_text(BODY)
        found = built_model.built(path, GRAVITY)
    ground = np.array([[[-5.0, 0.0, -5.0], [5.0, 0.0, 5.0], [5.0, 0.0, -5.0]],
                       [[-5.0, 0.0, -5.0], [-5.0, 0.0, 5.0], [5.0, 0.0, 5.0]]])
    physics = muscles.Physics(found, ground, [0])
    still = np.zeros(found.nv)
    needed = physics.needed(found.qpos0.copy(), still, still)
    weight = KG * GRAVITY
    problems = [] if np.allclose(needed[:3], [0.0, 0.0, weight], rtol=1e-6) else [f"needed {needed[:3]}"]
    share = physics.shared(needed)
    pushed = share["pushes"].sum(axis=0)
    if abs(pushed[2] - weight) > 0.01 * weight:
        problems.append(f"the ground pushes {pushed.round(3).tolist()} N, not {weight} N up")
    residual = float(np.linalg.norm(share["residual"][:3]))
    return problems + ([] if residual < 0.01 * weight else [f"residual force {residual:.3f} N"])


CHECKS = (the_ground_carries_a_still_body,)


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
