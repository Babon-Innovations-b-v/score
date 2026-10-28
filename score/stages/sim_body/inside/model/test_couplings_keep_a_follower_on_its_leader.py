"""model: on a small model Newton builds (a free root, a leading hinge and a hinge MuJoCo couples to it by a known
polynomial), the couplings set the follower and its derivative as worked out by hand (to 1e-6: Newton keeps the
polynomial in float32), a body is found by its own name, and the low-pass keeps a still path still, its root turn's
sign kept continuous, and a path of MuJoCo's own compile is carried onto Newton's joint by joint.
It runs in Newton's own Python (score/stages/physics/inside/newton_env.sh, built at $PROPS_HOME/envs/newton_env): with
none built there, as in `make tests`' sandbox home, it prints `skipped` and passes nothing.

Breaks (each applied once with the env linked into a sandbox home, seen red, reverted), 2026-10-28:
- Couplings.apply's `sum(poly[power] * moved ** power for power in range(5))` made `poly[0]`: the follower stays at
  the polynomial's constant.
- filtered's sign loop `if turn[frame] @ turn[frame - 1] < 0: turn[frame] *= -1` made `pass`: q and -q averaged.
- carried's `{...: 7, ...: 4}.get(int(source.jnt_type[joint]), 1)` made `1`: the root's place is carried, its turn
  not.

Not tested: `limited` never clamps a joint today (its `model.jnt_type[joint] in (mujoco.mjtJoint.mjJNT_HINGE, ...)`
is False for numpy's int32 against MuJoCo's enum, measured 2026-10-28 in the env: `==` is True, `in` False); the
move to this module kept it as it was (#70: behaviour unchanged first).

Run: .venv/bin/python score/stages/sim_body/inside/model/test_couplings_keep_a_follower_on_its_leader.py
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
    <body name="root" pos="0 0 1">
      <freejoint name="root"/>
      <geom type="sphere" size="0.1" mass="5"/>
      <body name="leader" pos="0 0 -0.2">
        <joint name="lead" type="hinge" axis="1 0 0" limited="true" range="-1 1"/>
        <geom type="capsule" fromto="0 0 0 0 0 -0.3" size="0.04" mass="2"/>
        <body name="follower" pos="0 0 -0.3">
          <joint name="follow" type="hinge" axis="1 0 0"/>
          <geom type="capsule" fromto="0 0 0 0 0 -0.3" size="0.04" mass="1"/>
        </body>
      </body>
    </body>
  </worldbody>
  <equality>
    <joint joint1="follow" joint2="lead" polycoef="0.1 0.5 0.2 0 0"/>
  </equality>
</mujoco>
"""


def built_toy(folder):
    import model
    path = pathlib.Path(folder) / "toy.xml"
    path.write_text(TOY)
    return model.built(path, 9.81)


def the_follower_follows_its_leader():
    """follow = 0.1 + 0.5 lead + 0.2 lead^2: at lead 0.5 the follower is 0.4 and d(follow)/d(lead) 0.7; the leading
    dofs are the root's six and the leader."""
    import model
    with tempfile.TemporaryDirectory() as folder:
        found = built_toy(folder)
    couplings = model.Couplings(found)
    lead, follow = (found.jnt_qposadr[joint] for joint in _joint_ids(found))
    qpos = found.qpos0.copy()
    qpos[lead] = 0.5
    qpos = couplings.apply(qpos)
    problems = [] if abs(qpos[follow] - 0.4) < 1e-6 else [f"follower at {qpos[follow]}, not 0.4"]
    slope = couplings.map(qpos)[found.jnt_dofadr[_joint_ids(found)[1]], 6]
    problems += [] if abs(slope - 0.7) < 1e-6 else [f"d follow / d lead {slope}, not 0.7"]
    return problems + ([] if len(couplings.leads) == 7 else [f"{len(couplings.leads)} leading dofs, not 7"])


def the_low_pass_keeps_a_still_turn_still():
    """The leader's body is found by its own name; a still path stays still through the low-pass, also when its root
    turn is written as q on even frames and -q on odd ones (one turn: the low-pass keeps its sign continuous)."""
    import model
    import numpy as np
    with tempfile.TemporaryDirectory() as folder:
        found = built_toy(folder)
    couplings = model.Couplings(found)
    problems = [] if found.body_parentid[model.body_index(found, "leader")] > 0 else ["the leader is not found"]
    still = np.tile(couplings.apply(found.qpos0.copy()), (20, 1))
    still[:, 3:7] = [0.6, 0.0, 0.0, 0.8]
    flipped = still.copy()
    flipped[1::2, 3:7] *= -1
    for name, path in (("still", still), ("flipped", flipped)):
        filtered = model.filtered(found, couplings, path, 30.0)
        if np.abs(filtered - still).max() > 1e-9:
            problems.append(f"the {name} path moved in the low-pass by {np.abs(filtered - still).max():.3g}")
    return problems


def _joint_ids(found):
    import mujoco
    names = [mujoco.mj_id2name(found, mujoco.mjtObj.mjOBJ_JOINT, joint) or "" for joint in range(found.njnt)]
    return [next(joint for joint, name in enumerate(names) if name.endswith(wanted)) for wanted in ("lead", "follow")]


def a_path_is_carried_joint_by_joint():
    """Two frames of MuJoCo's own compile of the toy (the root at (1, 2, 3) and turned 90 degrees about x, the leader
    at 0.3 and 0.6, the follower at -0.2) carried onto Newton's: every joint's coordinates as they were."""
    import mujoco
    import model
    import numpy as np
    with tempfile.TemporaryDirectory() as folder:
        found = built_toy(folder)
        own = mujoco.MjModel.from_xml_path(str(pathlib.Path(folder) / "toy.xml"))
    path = np.array([[1.0, 2.0, 3.0, np.sqrt(0.5), np.sqrt(0.5), 0.0, 0.0, lead, -0.2] for lead in (0.3, 0.6)])
    carried = model.carried(own, found, path)
    names = [mujoco.mj_id2name(found, mujoco.mjtObj.mjOBJ_JOINT, joint) or "" for joint in range(found.njnt)]
    problems = []
    for joint in range(own.njnt):
        name = mujoco.mj_id2name(own, mujoco.mjtObj.mjOBJ_JOINT, joint)
        width = 7 if own.jnt_type[joint] == mujoco.mjtJoint.mjJNT_FREE else 1
        target = next(index for index, full in enumerate(names) if full.endswith(name))
        start, at = own.jnt_qposadr[joint], found.jnt_qposadr[target]
        if not np.array_equal(carried[:, at:at + width], path[:, start:start + width]):
            problems.append(f"{name} carried as {carried[:, at:at + width]}")
    return problems


CHECKS = (the_follower_follows_its_leader, the_low_pass_keeps_a_still_turn_still, a_path_is_carried_joint_by_joint)


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
