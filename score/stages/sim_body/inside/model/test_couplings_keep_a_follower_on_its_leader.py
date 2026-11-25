"""model: on a small model Newton builds (a free root, a leading hinge and a hinge MuJoCo couples to it by a known
polynomial), one path of MuJoCo's own compile (the root at (1, 2, 3) turned about z, its turn written as q or as -q on
odd frames, the leader still at 0.5, the follower wrong and different each frame) is carried onto Newton's joint by
joint, its followers set by the couplings as worked out by hand (follow = 0.1 + 0.5 lead + 0.2 lead^2: 0.4, and
d(follow)/d(lead) 0.7, to 1e-6: Newton keeps the polynomial in float32; the leading dofs the root's six and the
leader), and the low-pass keeps that still path still, its root turn's sign kept continuous; a body is found by its
own name; and Newton's build with its spec's bodies listed once (`listed_once`) is the build without it, field for
field, its excluded pairs too, a body added inside it is listed, and MuJoCo's own listing is back after it.
It runs in Newton's own Python (score/stages/physics/inside/newton_env.sh, built at $PROPS_HOME/envs/newton_env): with
none built there, as in `make tests`' sandbox home, it prints `skipped` and passes nothing.

Breaks (each applied once with the env linked into a sandbox home, seen red, reverted), 2026-10-28:
- Couplings.apply's `sum(poly[power] * moved ** power for power in range(5))` made `poly[0]`: the follower stays at
  the polynomial's constant.
- filtered's sign loop `if turn[frame] @ turn[frame - 1] < 0: turn[frame] *= -1` made `pass`: q and -q averaged.
- carried's `{...: 7, ...: 4}.get(int(source.jnt_type[joint]), 1)` made `1`: the root's place is carried, its turn
  not.
- (2026-11-06) listed_once's `kept.clear()` made `pass`: a body added inside it is not listed.
- (2026-11-06) listed_once's `mujoco.MjSpec.bodies = listing` made `pass`: the kept listing stays after it.
(2026-11-13: all five applied again to the one merged test, each seen red, reverted.)

Not tested: `limited` never clamps a joint today (its `model.jnt_type[joint] in (mujoco.mjtJoint.mjJNT_HINGE, ...)`
is False for numpy's int32 against MuJoCo's enum, measured 2026-10-28 in the env: `==` is True, `in` False); the
move to this module kept it as it was (#70: behaviour unchanged first).

Run: make tests TESTS=score/stages/sim_body/inside/model/test_couplings_keep_a_follower_on_its_leader.py
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
FRAMES = 20
# The root turn's sign on each frame of the path: one turn either way, so the low-pass must keep it as written.
SIGNS = (("still", [1.0] * FRAMES), ("flipped", [1.0 if frame % 2 == 0 else -1.0 for frame in range(FRAMES)]))


def toy_worlds():
    """The toy as Newton builds it (its bodies listed once), as Newton builds it with `listed_once` a no-op, and as
    MuJoCo compiles it itself."""
    import contextlib
    import mujoco
    import model
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder) / "toy.xml"
        path.write_text(TOY)
        once = model.built(path, 9.81)
        kept, model.listed_once = model.listed_once, contextlib.nullcontext
        try:
            plain = model.built(path, 9.81)
        finally:
            model.listed_once = kept
        return once, plain, mujoco.MjModel.from_xml_path(str(path))


def joint_columns(source, target):
    """Each of `source`'s joints: its name, its qpos columns in `source` and in `target` (found by its own name)."""
    import mujoco
    names = [mujoco.mj_id2name(target, mujoco.mjtObj.mjOBJ_JOINT, joint) or "" for joint in range(target.njnt)]
    for joint in range(source.njnt):
        name = mujoco.mj_id2name(source, mujoco.mjtObj.mjOBJ_JOINT, joint)
        width = 7 if source.jnt_type[joint] == mujoco.mjtJoint.mjJNT_FREE else 1
        target_joint = next(index for index, full in enumerate(names) if full.endswith(name))
        start, at = source.jnt_qposadr[joint], target.jnt_qposadr[target_joint]
        yield name, slice(start, start + width), slice(at, at + width), target_joint


def own_path(signs):
    """A still path in MuJoCo's own layout: the root at (1, 2, 3) turned (0.6, 0, 0, 0.8) times each frame's sign,
    the leader at 0.5, the follower at -0.2 - 0.01 frame (wrong, and different each frame)."""
    import numpy as np
    return np.array([[1.0, 2.0, 3.0, 0.6 * sign, 0.0, 0.0, 0.8 * sign, 0.5, -0.2 - 0.01 * frame]
                     for frame, sign in enumerate(signs)])


def couplings_faults():
    """Every fault of the toy's worlds: a path carried, coupled and low-passed, the leader found, the two builds."""
    import mujoco
    import model
    import numpy as np
    found, plain, own = toy_worlds()
    couplings = model.Couplings(found)
    columns = {name: (start, at, joint) for name, start, at, joint in joint_columns(own, found)}
    lead, follow = columns["lead"][1].start, columns["follow"][1].start
    faults = [] if len(couplings.leads) == 7 else [f"{len(couplings.leads)} leading dofs, not 7"]
    faults += [] if found.body_parentid[model.body_index(found, "leader")] > 0 else ["the leader is not found"]
    coupled_by_sign = {}
    for label, signs in SIGNS:
        path = own_path(signs)
        carried = model.carried(own, found, path)
        faults += [f"{label}: {name} carried as {carried[:, at]}" for name, (start, at, _) in columns.items()
                   if not np.array_equal(carried[:, at], path[:, start])]
        coupled = np.array([couplings.apply(qpos) for qpos in carried.copy()])
        faults += [f"{label}: follower at {coupled[frame, follow]} on frame {frame}, not 0.4"
                   for frame in range(FRAMES) if abs(coupled[frame, follow] - 0.4) >= 1e-6]
        slope = couplings.map(coupled[0])[found.jnt_dofadr[columns["follow"][2]], 6]
        faults += [] if abs(slope - 0.7) < 1e-6 else [f"{label}: d follow / d lead {slope}, not 0.7"]
        coupled_by_sign[label] = coupled
    still = coupled_by_sign["still"]
    for label, _ in SIGNS:
        moved = np.abs(model.filtered(found, couplings, coupled_by_sign[label], 30.0) - still).max()
        faults += [] if moved <= 1e-9 else [f"the {label} path moved in the low-pass by {moved:.3g}"]
    arrays = [name for name in dir(plain) if not name.startswith("_") and isinstance(getattr(plain, name), np.ndarray)]
    faults += [f"{name} differs listed once" for name in arrays
               if not np.array_equal(getattr(plain, name), getattr(found, name), equal_nan=True)]
    faults += [] if plain.nexclude > 0 else ["the toy has no excluded pair to compare"]
    listing, adding = mujoco.MjSpec.__dict__["bodies"], mujoco.MjsBody.__dict__["add_body"]
    with model.listed_once():
        spec = mujoco.MjSpec.from_string(TOY)
        before = len(spec.bodies)
        spec.worldbody.add_body(name="added")
        faults += [] if len(spec.bodies) == before + 1 else [f"{len(spec.bodies)} bodies listed after one added"]
    faults += [] if mujoco.MjSpec.__dict__["bodies"] is listing else ["MjSpec's own listing not back"]
    return faults + ([] if mujoco.MjsBody.__dict__["add_body"] is adding else ["MjsBody's own add_body not back"])


def in_newton():
    """The check, in Newton's own Python."""
    sys.path.insert(0, str(INSIDE))
    faults = couplings_faults()
    for fault in faults:
        print(fault)
    print("ok" if not faults else f"{len(faults)} failed")
    return 1 if faults else 0


def test_couplings_keep_a_follower_on_its_leader():
    env = pathlib.Path(os.environ["PROPS_HOME"]) / "envs/newton_env"
    if not list(env.glob(".built-*")):
        print(f"skipped: no Newton env built at {env} (score/stages/physics/inside/newton_env.sh)")
        return
    ran = subprocess.run([str(env / "bin/python"), "-B", __file__], env={**os.environ, IN_ENV: "1"},
                         capture_output=True, text=True)
    assert ran.returncode == 0 and ran.stdout.strip().endswith("ok"), ran.stdout[-4000:] + ran.stderr[-4000:]


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[5] / "conftest.py"))["refuse_outside_sandbox"]()
    if os.environ.get(IN_ENV):
        sys.exit(in_newton())
    test_couplings_keep_a_follower_on_its_leader()
