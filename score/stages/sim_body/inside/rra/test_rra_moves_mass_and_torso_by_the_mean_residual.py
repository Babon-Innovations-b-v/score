"""rra: RRA's model step changes the body's mass by the mean upward residual over its weight, at most MASS_MOST from
the mass it was made with over every round together (the unbounded change recorded as recommended), and moves the
torso's centre of mass under the mean residual moment, at most COM_MOST from where it was made, as worked out by hand (to
1e-6: Newton keeps gravity in float32); and a segment's turn between two posed paths is measured in degrees. It runs
in Newton's own Python (on a model Newton builds; score/stages/physics/inside/newton_env.sh, built at
$PROPS_HOME/envs/newton_env): with none built there, as in `make tests`' sandbox home, it prints `skipped`.

Breaks (each applied once with the env linked into a sandbox home, seen red, reverted), 2026-10-28:
- reweighed's `share = -float(np.mean(residuals[:, 2]))` made `share = float(...)`: the body gets lighter when the
  ground must carry more.
- reweighed's `np.clip(recommended, -MASS_MOST, MASS_MOST)` made `recommended`: a floating body loses all its mass
  (2026-10-29).
- reweighed's `model.body_mass[:] = made[0] * (1 + share)` made `model.body_mass[:] *= 1 + share`: the bound
  compounds round after round, three rounds take the body to 0.98 ** 3 (2026-10-29).
- reweighed's `np.clip(model.body_ipos[torso] + shift - home, -COM_MOST, COM_MOST)` made `model.body_ipos[torso] +
  shift - home`: the torso's centre of mass moves past RRA's 0.1 m.

Run: .venv/bin/python score/stages/sim_body/inside/rra/test_rra_moves_mass_and_torso_by_the_mean_residual.py
"""
import os
import pathlib
import subprocess
import sys
import tempfile

INSIDE = pathlib.Path(__file__).resolve().parents[1]
IN_ENV = "SIM_BODY_INSIDE_TEST"
GRAVITY = 9.81
TORSO_KG = 2.0
TOY = """<mujoco model="toy">
  <compiler angle="radian"/>
  <worldbody>
    <body name="pelvis" pos="0 0 1">
      <freejoint name="root"/>
      <geom type="box" size="0.15 0.1 0.1" mass="8"/>
      <body name="torso" pos="0 0 0.2">
        <joint name="flex_extension" type="hinge" axis="1 0 0" range="-1 1"/>
        <geom type="box" size="0.1 0.1 0.1" mass="2"/>
      </body>
    </body>
  </worldbody>
</mujoco>
"""


def toy_physics():
    import model
    import muscles
    import numpy as np
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder) / "toy.xml"
        path.write_text(TOY)
        found = model.built(path, GRAVITY)
    ground = np.array([[[-5.0, 0.0, -5.0], [5.0, 0.0, 5.0], [5.0, 0.0, -5.0]]])
    return muscles.Physics(found, ground, [])


def made_of(found):
    """The toy's masses and inertias as made."""
    return found.body_mass.copy(), found.body_inertia.copy()


def the_mass_follows_the_mean_upward_residual():
    """A residual of 1% of the weight down at the pelvis on every frame: every body 1% heavier (the share 0.01),
    and with no residual moment the torso's centre of mass where it was."""
    import model
    import numpy as np
    import rra
    physics = toy_physics()
    found = physics.model
    torso = model.body_index(found, "torso")
    mass, home = found.body_mass.copy(), found.body_ipos[torso].copy()
    residuals = np.zeros((3, 6))
    residuals[:, 2] = -0.01 * mass.sum() * GRAVITY
    share, _ = rra.reweighed(physics, np.tile(found.qpos0, (3, 1)), residuals, home, made_of(found))
    problems = [] if abs(share - 0.01) < 1e-6 and np.allclose(found.body_mass, 1.01 * mass, rtol=1e-6) else [
        f"share {share}, masses {found.body_mass.tolist()} from {mass.tolist()}"]
    return problems + ([] if np.allclose(found.body_ipos[torso], home) else ["the torso's centre of mass moved"])


def a_floating_body_keeps_its_mass_within_the_bound():
    """A body the ground carries nothing of (the residual holds its whole weight up) three rounds over: RRA recommends
    taking all its mass (-1 from the made mass), and the change made stays at -MASS_MOST, never compounding."""
    import numpy as np
    import rra
    physics = toy_physics()
    found = physics.model
    mass, made = found.body_mass.copy(), made_of(found)
    found_shares = []
    for _ in range(3):
        residuals = np.zeros((3, 6))
        residuals[:, 2] = found.body_mass.sum() * GRAVITY
        found_shares.append(rra.reweighed(physics, np.tile(found.qpos0, (3, 1)), residuals, np.zeros(3), made))
    share, recommended = found_shares[-1]
    problems = [] if abs(share + rra.MASS_MOST) < 1e-6 and abs(recommended + 1) < 1e-6 else [
        f"share {share}, recommended {recommended}"]
    return problems + ([] if np.allclose(found.body_mass, (1 - rra.MASS_MOST) * mass, rtol=1e-6) else
                       [f"masses {found.body_mass.sum()} from {mass.sum()}"])


def the_torso_moves_under_the_mean_moment_within_its_cap():
    """A residual moment about x of the torso's weight times 2 cm (the torso upright): its centre of mass moves 2 cm
    along y; of its weight times 50 cm, it stops at COM_MOST (10 cm)."""
    import model
    import numpy as np
    import rra
    moved = []
    for lever in (0.02, 0.5):
        physics = toy_physics()
        found = physics.model
        torso = model.body_index(found, "torso")
        home = found.body_ipos[torso].copy()
        residuals = np.zeros((3, 6))
        residuals[:, 3] = -TORSO_KG * GRAVITY * lever
        rra.reweighed(physics, np.tile(found.qpos0, (3, 1)), residuals, home, made_of(found))
        moved.append(found.body_ipos[torso] - home)
    problems = [] if np.allclose(moved[0], [0.0, 0.02, 0.0], atol=1e-6) else [f"2 cm lever: moved {moved[0]}"]
    return problems + ([] if np.allclose(moved[1], [0.0, rra.COM_MOST, 0.0], atol=1e-6) else
                       [f"50 cm lever: moved {moved[1]}"])


def a_turn_between_two_paths_is_its_angle():
    """One segment turned 10 degrees about up between two posed paths, the other not: 10 and 0 degrees."""
    import numpy as np
    import rra
    from scipy.spatial.transform import Rotation
    before = np.tile(np.eye(4), (1, 2, 1, 1))
    after = before.copy()
    after[0, 0, :3, :3] = Rotation.from_euler("y", 10, degrees=True).as_matrix()
    found = rra.turned_off(before, after)
    return [] if np.allclose(found, [[10.0, 0.0]]) else [f"turns {found}"]


CHECKS = (the_mass_follows_the_mean_upward_residual, a_floating_body_keeps_its_mass_within_the_bound,
          the_torso_moves_under_the_mean_moment_within_its_cap,
          a_turn_between_two_paths_is_its_angle)


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
