"""rra: RRA's model step changes the body's mass by the mean upward residual over its weight, at most MASS_MOST from the
mass it was made with over every round together (the unbounded change recorded as recommended), and moves the torso's
centre of mass under the mean residual moment, at most COM_MOST from where it was made; the feet stay where they stood
when the pelvis moves (`Footing`, mink), a leg's direction no foot task sees held where the frame stood
(`FreeHold`), and a frame that does not converge fails loudly; as worked out by hand (to 1e-6: Newton keeps gravity
in float32); a segment's turn between two posed paths is measured in degrees; RRA's frame shares are held smooth
and never above what the frame check lowered them to, a move putting bones out of SOMA's skin is seen region by region
against the fitted path, and only the move off the fitted path is low-passed (#70, 2026-11-05); the caps' rows of
every nudge landed as one stacked path, and the card's sensitivities with a frame's couplings' map kept where its
leaders stand, are each nudge's own bits (2026-11-06). It runs in Newton's
own Python (on a model Newton builds; score/stages/physics/inside/newton_env.sh, built at $PROPS_HOME/envs/newton_env): with none
built there, as in `make tests`' sandbox home, it prints `skipped`.

Breaks (each applied once with the env linked into a sandbox home, seen red, reverted), 2026-10-28:
- reweighed's `share = -float(np.mean(residuals[:, 2]))` made `share = float(...)`: the body gets lighter when the
  ground must carry more.
- reweighed's `np.clip(recommended, -MASS_MOST, MASS_MOST)` made `recommended`: a floating body loses all its mass
  (2026-10-29).
- reweighed's `model.body_mass[:] = made[0] * (1 + share)` made `model.body_mass[:] *= 1 + share`: the bound
  compounds round after round, three rounds take the body to 0.98 ** 3 (2026-10-29).
- Footing.footed's `self.tasks + [self.height]` made `[self.height]`: the feet ride the moved pelvis, 2 cm off
  (2026-10-29).
- fit._frames.solved's `raise NotConverged(...)` made `return configuration.q.copy()`: a frame cut off at its
  last step is kept silently (2026-10-29).
- reweighed's `np.clip(model.body_ipos[torso] + shift - home, -COM_MOST, COM_MOST)` made `model.body_ipos[torso] +
  shift - home`: the torso's centre of mass moves past RRA's 0.1 m.
- Footing.footed's `limit.lower, limit.upper = np.minimum(lower, still), np.maximum(upper, still)` dropped: a knee
  the fitted path carries past its stop is pulled in with no move (camp, 2026-11-03).
- Footing.footed's `self.hold.set_target(qpos)` made `self.hold.set_target(still)`: the shin's turn and the ankle's
  twist go back to where `before` stood them, a direction no foot sees moved (2026-11-04).
- Footing.footed's `found[unstopped] = self._mink(...)` dropped: a frame the card did not stop is kept half solved
  (2026-11-05).
- FreeHold._free's `turns[rank:]` made `turns[:rank]` (the directions the feet see held instead): the feet 15 mm off
  (2026-11-04).

- rra._cap.held_share's `np.convolve(padded, ...)` made `smoothed(lowered, rate)` with `np.minimum(lowered, ...)`
  (the rule before): the dip's whole 0.7 kept as one step; its erosion's `2 * radius + 1` made `1`: the average
  rises above the lowered share beside the dip (2026-11-05).
- rra._cap.skin_excess' `- fitted[...]` dropped: a region already out on the fitted path counts as put out; its
  `labels == label` made all vertices: region b's half read as a quarter (2026-11-05).
- rra._cap.smoothed_off's `smoothed(offsets, rate)` dropped: the shake kept; its offsets taken off the zero pose
  instead of `before`: the walk itself low-passed (2026-11-05).
- rra._linear.wrenches' `places - summed[:, None] * origin` made `places - origin`, and its `summed[:, None, None] *
  edges` made `edges`: the blended point's columns off its Jacobian's; residuals_kept's key without the masses: moved
  masses read the kept residuals (2026-11-06).
- rra._linear.sensitivities' `mapped if same else couplings.map(placed)` made `mapped`: a lumbar nudge's trunk rows
  read the frame's map, not its own; rra._cap.cap_rows' `found[1 + column]` made `found[column]`: a stacked nudge read
  as its neighbour's (2026-11-06).

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
LEGS = """<mujoco model="legs">
  <compiler angle="radian"/>
  <worldbody>
    <body name="pelvis" pos="0 0 0.9">
      <freejoint name="root"/>
      <geom type="box" size="0.1 0.15 0.05" mass="8"/>
      <body name="thigh_l" pos="0 0.1 0">
        <joint name="hip_l" type="hinge" axis="0 1 0" range="-1.5 1.5"/>
        <geom type="capsule" fromto="0 0 0 0 0 -0.4" size="0.05" mass="5"/>
        <body name="shin_l" pos="0 0 -0.4">
          <joint name="knee_l" type="hinge" axis="0 1 0" range="0 2.5"/>
          <geom type="capsule" fromto="0 0 0 0 0 -0.4" size="0.04" mass="3"/>
          <body name="foot_l" pos="0 0 -0.4">
            <joint name="ankle_l" type="hinge" axis="0 1 0" range="-1 1"/>
            <geom type="box" pos="0.05 0 -0.03" size="0.1 0.04 0.03" mass="1"/>
          </body>
        </body>
      </body>
      <body name="thigh_r" pos="0 -0.1 0">
        <joint name="hip_r" type="hinge" axis="0 1 0" range="-1.5 1.5"/>
        <geom type="capsule" fromto="0 0 0 0 0 -0.4" size="0.05" mass="5"/>
        <body name="shin_r" pos="0 0 -0.4">
          <joint name="knee_r" type="hinge" axis="0 1 0" range="0 2.5"/>
          <geom type="capsule" fromto="0 0 0 0 0 -0.4" size="0.04" mass="3"/>
          <body name="foot_r" pos="0 0 -0.4">
            <joint name="ankle_r" type="hinge" axis="0 1 0" range="-1 1"/>
            <geom type="box" pos="0.05 0 -0.03" size="0.1 0.04 0.03" mass="1"/>
          </body>
        </body>
      </body>
    </body>
  </worldbody>
</mujoco>
"""


def legs_footing():
    """The legs toy, knees a little bent, its Footing on both feet, and its standing qpos."""
    import mujoco
    import model
    import rra
    found = mujoco.MjModel.from_xml_string(LEGS)
    standing = found.qpos0.copy()
    for side in "lr":
        standing[found.jnt_qposadr[found.joint(f"hip_{side}").id]] = -0.3
        standing[found.jnt_qposadr[found.joint(f"knee_{side}").id]] = 0.6
        standing[found.jnt_qposadr[found.joint(f"ankle_{side}").id]] = -0.3
    feet = [model.body_index(found, f"foot_{side}") for side in "lr"]
    return rra.Footing(found, model.Couplings(found), feet), standing


def the_feet_stay_where_they_stood_when_the_pelvis_moves():
    """The pelvis moved 2 cm forward and 1 cm down on two frames: the feet back within 0.01 mm and 0.001 degrees of
    where they stood, the pelvis kept where it was moved."""
    import numpy as np
    footing, standing = legs_footing()
    moved = np.tile(standing, (2, 1))
    moved[:, 0] += 0.02
    moved[:, 2] -= 0.01
    found = footing.footed(moved, np.tile(standing, (2, 1)))
    off = footing.off(found, np.tile(standing, (2, 1)))
    problems = [] if off[:, 0].max() < 1e-5 and np.degrees(off[:, 1].max()) < 1e-3 else [f"feet off {off.tolist()}"]
    return problems + ([] if np.allclose(found[:, :3], moved[:, :3], atol=1e-6) else
                       [f"pelvis at {found[:, :3].tolist()}, moved to {moved[:, :3].tolist()}"])


def a_leg_past_its_stop_is_left_where_it_stood():
    """A knee the fitted path carries 0.05 rad past its 0 stop: unmoved, the frame comes back as it was (to 1e-9); with
    the pelvis 1 cm down, the knee bends no further past its stop than it stood."""
    import numpy as np
    footing, standing = legs_footing()
    knee = footing.model.jnt_qposadr[footing.model.joint("knee_l").id]
    standing[knee] = -0.05
    still = footing.footed(standing[None], standing[None])[0]
    lowered = standing.copy()
    lowered[2] -= 0.01
    moved = footing.footed(lowered[None], standing[None])[0]
    changed = np.abs(still - standing).max()
    problems = [] if changed < 1e-9 else [f"an unmoved frame changed by {changed}"]
    return problems + ([] if moved[knee] >= -0.05 - 1e-9 else [f"knee {moved[knee]} past where it stood (-0.05)"])


def a_legs_free_direction_is_held_where_the_frame_stood():
    """The legs toy with the left shin turning on the knee and the foot twisting on the shin, both about the shin's
    long axis (`knee_angle_rotation3_l` and `ankle_rotation_l`, as MyoFullBody's): one direction, the turn against the
    twist, moves no foot. A frame turned 0.1 rad and twisted back 0.1, its pelvis 1 cm down, comes back with its feet
    where they stood and the turn and the twist where the frame had them."""
    import mujoco
    import numpy as np
    import model
    import rra
    legs = LEGS.replace('<joint name="knee_l" type="hinge" axis="0 1 0" range="0 2.5"/>',
                        '<joint name="knee_l" type="hinge" axis="0 1 0" range="0 2.5"/>'
                        '<joint name="knee_angle_rotation3_l" type="hinge" axis="0 0 1" range="-0.26 0.26"/>')
    legs = legs.replace('<joint name="ankle_l" type="hinge" axis="0 1 0" range="-1 1"/>',
                        '<joint name="ankle_rotation_l" type="hinge" axis="0 0 1" range="-0.35 0.44"/>'
                        '<joint name="ankle_l" type="hinge" axis="0 1 0" range="-1 1"/>')
    found = mujoco.MjModel.from_xml_string(legs)
    standing = found.qpos0.copy()
    for name, angle in (("hip", -0.3), ("knee", 0.6), ("ankle", -0.3)):
        for side in "lr":
            standing[found.jnt_qposadr[found.joint(f"{name}_{side}").id]] = angle
    footing = rra.Footing(found, model.Couplings(found), [model.body_index(found, f"foot_{side}") for side in "lr"])
    pair = [found.jnt_qposadr[found.joint(name).id] for name in ("knee_angle_rotation3_l", "ankle_rotation_l")]
    frame = standing.copy()
    frame[pair] = 0.1, -0.1
    frame[2] -= 0.01
    put = footing.footed(frame[None], standing[None])
    off = footing.off(put, standing[None])[0]
    problems = [] if off[0] < 1e-5 and np.degrees(off[1]) < 1e-3 else [f"feet off {off.tolist()}"]
    return problems + ([] if np.allclose(put[0][pair], [0.1, -0.1], atol=1e-6) else
                       [f"the turn and the twist moved to {put[0][pair].tolist()}"])


def the_cards_footing_equals_minks():
    """On a CUDA card, `Footing` given the person's file solves every frame at once on the card
    (`_footed_card.CardFooting`): on the legs toy with the shin's turn and the foot's twist (a free direction), Newton's
    build of it, three frames (the pelvis 2 cm forward and 1 cm down; 1 cm down with the knee 0.05 rad past its stop;
    the turn and twist at 0.1 and -0.1 rad, 1 cm down), its feet within 0.01 mm and 0.001 degrees of where mink's
    put them (the knee held at its stop leaves both 0.1 mm off on the second), every coordinate within 1e-4 rad (or
    m) of mink's, the knee no further past its stop than it stood, and the frozen
    pelvis bit for bit the frame's; frames the card does not stop (one step allowed) are mink's.
    Without a card it prints that it was not run."""
    import numpy as np
    import fit
    import model
    import rra
    if not fit.on_card():
        print("the card's footing: no CUDA card, not run")
        return []
    wrapper = '<inertial pos="0 0 0" mass="0.001" diaginertia="1e-6 1e-6 1e-6"/>'  # one joint a body, as Newton needs
    shin = ('          <geom type="capsule" fromto="0 0 0 0 0 -0.4" size="0.04" mass="3"/>\n'
            '          <body name="foot_l" pos="0 0 -0.4">\n'
            '            <joint name="ankle_l" type="hinge" axis="0 1 0" range="-1 1"/>\n'
            '            <geom type="box" pos="0.05 0 -0.03" size="0.1 0.04 0.03" mass="1"/>\n'
            '          </body>\n')
    free = (f'          {wrapper}\n'
            '          <body name="shin_turn_l">\n'
            '          <joint name="knee_angle_rotation3_l" type="hinge" axis="0 0 1" range="-0.26 0.26"/>\n'
            '          <geom type="capsule" fromto="0 0 0 0 0 -0.4" size="0.04" mass="3"/>\n'
            '          <body name="foot_twist_l" pos="0 0 -0.4">\n'
            '            <joint name="ankle_rotation_l" type="hinge" axis="0 0 1" range="-0.35 0.44"/>\n'
            f'            {wrapper}\n'
            '          <body name="foot_l">\n'
            '            <joint name="ankle_l" type="hinge" axis="0 1 0" range="-1 1"/>\n'
            '            <geom type="box" pos="0.05 0 -0.03" size="0.1 0.04 0.03" mass="1"/>\n'
            '          </body>\n          </body>\n          </body>\n')
    if shin not in LEGS:
        return ["the legs toy's left shin is not as this check splits it"]
    legs = LEGS.replace(shin, free)
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder) / "legs.xml"
        path.write_text(legs)
        found = model.built(path, GRAVITY)
        feet = [model.body_index(found, f"foot_{side}") for side in "lr"]
        card = rra.Footing(found, model.Couplings(found), feet, path)
        mink = rra.Footing(found, model.Couplings(found), feet)
        if card.card is None:
            return ["a card and a file, but Footing did not take the card"]
        def coordinate(name):  # Newton names a joint by its path
            joints = [joint for joint in range(found.njnt) if (found.joint(joint).name or "").endswith(name)]
            return found.jnt_qposadr[joints[0]]

        standing = found.qpos0.copy()
        for name, angle in (("hip", -0.3), ("knee", 0.6), ("ankle", -0.3)):
            for side in "lr":
                standing[coordinate(f"{name}_{side}")] = angle
        before = np.tile(standing, (3, 1))
        knee = coordinate("knee_l")
        before[1, knee] = -0.05
        moved = before.copy()
        moved[0, 0] += 0.02
        moved[:, 2] -= 0.01
        pair = [coordinate("knee_angle_rotation3_l"), coordinate("ankle_rotation_l")]
        moved[2, pair] = 0.1, -0.1
        put, reference = card.footed(moved, before), mink.footed(moved, before)
        card.card.most_steps = 1  # no row stops: every frame handed to mink, the reference
        handed = card.footed(moved, before)
    off = card.off(put, before) - card.off(reference, before)
    problems = [] if off[:, 0].max() < 1e-5 and np.degrees(off[:, 1].max()) < 1e-3 else [f"feet off {off.tolist()}"]
    apart = np.abs(put - reference).max()
    problems += [] if apart < 1e-4 else [f"the card's frames {apart} off mink's"]
    problems += [] if put[1, knee] >= -0.05 - 1e-6 else [f"knee {put[1, knee]} past where it stood (-0.05)"]
    problems += [] if np.array_equal(handed, reference) else ["frames the card did not stop not mink's"]
    return problems + ([] if np.array_equal(put[:, [0, 1, 3, 4, 5, 6]], moved[:, [0, 1, 3, 4, 5, 6]]) else
                       ["the frozen pelvis moved"])


def a_foot_frame_that_does_not_converge_fails():
    """With one step allowed, the same move raises NotConverged instead of keeping a frame half solved."""
    import fit
    from fit import _frames
    footing, standing = legs_footing()
    moved = standing.copy()
    moved[0] += 0.02
    kept, _frames.MOST_STEPS = _frames.MOST_STEPS, 1
    try:
        footing.footed(moved[None], standing[None])
    except fit.NotConverged:
        return []
    finally:
        _frames.MOST_STEPS = kept
    return ["a frame cut off after one step was kept"]


def toy_physics():
    import contact
    import model
    import muscles
    import numpy as np
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder) / "toy.xml"
        path.write_text(TOY)
        found = model.built(path, GRAVITY)
    ground = np.array([[[-5.0, 0.0, -5.0], [5.0, 0.0, 5.0], [5.0, 0.0, -5.0]]])
    nothing = contact.Skin(np.zeros((0, 3)), np.zeros((0, 1)), [np.eye(4)], [0], [np.eye(4)])  # no skin: no contact
    return muscles.Physics(found, ground, nothing)


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


def the_frame_shares_are_smooth_and_never_above_the_lowered():
    """At 30 frames a second, a share of 1 lowered to 0.3 on one frame and to 0.6 on another (as the frame check
    lowers it): held, it is nowhere above the lowered share and its largest step between frames is under a third of the
    lowered share's 0.7 (the min of the lowered share and its low-pass kept that step whole)."""
    import numpy as np
    import rra
    lowered = np.ones(90)
    lowered[30], lowered[60] = 0.3, 0.6
    held = rra.held_share(lowered, 30.0)
    problems = [] if np.all(held <= lowered + 1e-12) else [f"held above lowered by {float((held - lowered).max())}"]
    step = float(np.abs(np.diff(held)).max())
    return problems + ([] if step < 0.7 / 3 else [f"a step of {step} between frames"])


def a_move_that_puts_bones_out_of_the_skin_is_seen_by_region():
    """Two regions of two bone vertices each, one of region a's out on the fitted path and kept out; the found path
    puts one of region b's out on its second frame: no rise on the first, half of b on the second (a's none)."""
    import numpy as np
    import rra
    labels = np.array(["a", "a", "b", "b"])
    fitted = np.zeros((2, 4), dtype=bool)
    fitted[:, 0] = True
    found = fitted.copy()
    found[1, 3] = True
    rises = rra.skin_excess(found, fitted, labels)
    return [] if np.allclose(rises, [0.0, 0.5]) else [f"rises {rises.tolist()}"]


def only_the_move_off_the_fitted_path_is_low_passed():
    """The legs toy's fitted path walking 1 m/s along x for 60 frames at 30 a second, a found path 1 cm further along
    with a 1 mm shake every other frame: the smoothed path keeps the walk and the centimetre (within 0.2 mm mid-clip)
    and its shake is under a tenth of a millimetre; a found path equal to the fitted one comes back unchanged."""
    import types
    import numpy as np
    import model
    import rra
    footing, standing = legs_footing()
    physics = types.SimpleNamespace(model=footing.model, couplings=model.Couplings(footing.model))
    path = np.tile(standing, (60, 1))
    path[:, 0] += np.arange(60) / 30.0
    found = path.copy()
    found[:, 0] += 0.01 + 0.001 * (-1) ** np.arange(60)
    smooth = rra.smoothed_off(physics, path, found, 30.0)
    off = smooth[:, 0] - path[:, 0]
    problems = [] if np.abs(off[10:50] - 0.01).max() < 2e-4 else [f"the move kept as {off[10:50].tolist()}"]
    shake = float(np.abs(np.diff(off[10:50], n=2)).max())
    problems += [] if shake < 1e-4 else [f"a shake of {shake} m left"]
    same = rra.smoothed_off(physics, path, path, 30.0)
    return problems + ([] if np.allclose(same, path, atol=1e-12) else ["an unmoved path changed"])


TRUNK_LEGS = LEGS.replace("""      <body name="thigh_l\"""", """      <body name="torso" pos="0 0 0.1">
        <joint name="flex_extension" type="hinge" axis="0 1 0" range="-1 1"/>
        <joint name="lat_bending" type="hinge" axis="1 0 0" range="-1 1"/>
        <joint name="axial_rotation" type="hinge" axis="0 0 1" range="-1 1"/>
        <geom type="box" pos="0 0 0.15" size="0.1 0.12 0.15" mass="10"/>
        <body name="chest" pos="0 0 0.3">
          <joint name="follower" type="hinge" axis="0 1 0" range="-1 1"/>
          <geom type="box" pos="0 0 0.1" size="0.1 0.12 0.1" mass="6"/>
        </body>
      </body>
      <body name="thigh_l\"""", 1).replace("</worldbody>", """</worldbody>
  <equality><joint joint1="follower" joint2="flex_extension" polycoef="0 0.5 0.3 0 0"/></equality>""")


class CpuCard:
    """A stand-in for `batched.Card` on MuJoCo's C: `evaluate`'s needed forces (mj_inverse) and root poses, the states
    it was given kept."""

    def __init__(self, found):
        import mujoco
        self.model, self.data = found, mujoco.MjData(found)

    def evaluate(self, qpos, qvel, qacc, names):
        import mujoco
        import numpy as np
        found = {"needed": [], "xpos": [], "xmat": []}
        for state in zip(qpos, qvel, qacc):
            self.data.qpos[:], self.data.qvel[:], self.data.qacc[:] = state
            mujoco.mj_inverse(self.model, self.data)
            found["needed"].append(self.data.qfrc_inverse.copy())
            found["xpos"].append(self.data.xpos.copy())
            found["xmat"].append(self.data.xmat.copy())
        self.given, self.needed = np.array(qpos), np.array(found["needed"])
        return {name: np.array(values) for name, values in found.items()}


def the_linearisation_is_each_nudge_measured_alone():
    """On a toy with a trunk, a chest following its flexion and two legs (four frames, a small move), mink's Footing:
    `cap_rows` with every nudged path moved, landed and posed as one stacked path gives the rows and values, bit for
    bit, that one path a nudge gives; and on a card (MuJoCo's C standing in) `sensitivities`' trunk rows are, bit for
    bit, each nudged state's own couplings' map: the frame's kept only where the leaders stand as the frame's."""
    import types
    import mujoco
    import numpy as np
    import model
    import rra
    from rra import _cap, _linear
    found = mujoco.MjModel.from_xml_string(TRUNK_LEGS)
    couplings = model.Couplings(found)
    physics = types.SimpleNamespace(model=found, data=mujoco.MjData(found), couplings=couplings, card=None)
    standing = found.qpos0.copy()
    for side in "lr":
        for joint, angle in (("hip", -0.3), ("knee", 0.6), ("ankle", -0.3)):
            standing[found.jnt_qposadr[found.joint(f"{joint}_{side}").id]] = angle
    path = np.tile(standing, (4, 1))
    path[:, found.jnt_qposadr[found.joint("flex_extension").id]] = [0.1, 0.12, 0.15, 0.17]
    path[:, 0] += np.arange(4) * 0.01
    path = np.array([couplings.apply(qpos) for qpos in path])
    feet = [model.body_index(found, f"foot_{side}") for side in "lr"]
    footing = rra.Footing(found, couplings, feet)

    def land(moved):
        return footing.footed(moved, np.concatenate([path] * (len(moved) // len(path))))

    segments = ["pelvis", "torso", "chest", "thigh_l", "shin_l", "thigh_r", "shin_r"]
    riders = (segments, {name: model.body_index(found, name) for name in segments},
              {name: np.eye(4) for name in segments})
    fitted = model.posed_path(found, path, *riders)
    most = (0.02, np.radians(5.0))
    adjusted = _linear.adjusted_leads(physics)
    total = 0.004 * np.sin(np.arange(4 * len(adjusted)) + 1.0).reshape(4, len(adjusted))
    rows, values = rra.cap_rows(physics, path, total, land, fitted, riders, most)
    now = _cap.turns_off(found, land(_linear.moved(physics, path, total, adjusted)), fitted, riders)
    turning = np.zeros((4, now.shape[1], 3, len(adjusted)))
    for column in range(len(adjusted)):
        nudge = np.zeros(len(adjusted))
        nudge[column] = _cap.CAP_STEP
        ahead = _cap.turns_off(found, land(_linear.moved(physics, path, total + nudge, adjusted)), fitted, riders)
        turning[..., column] = (ahead - now) / (_cap.CAP_STEP * most[1])
    kept = []
    for ball in range(now.shape[1]):
        mine = np.concatenate([turning[:, ball].reshape(4, -1), now[:, ball] / most[1]], axis=1)
        if np.abs(mine).max() > _cap.CAP_STEP and not any(np.allclose(mine, other, atol=_cap.CAP_STEP)
                                                          for other in kept):
            kept.append(mine)
    width = len(adjusted)
    alone = (np.stack([mine[:, :3 * width].reshape(4, 3, width) for mine in kept], axis=1),
             np.stack([mine[:, 3 * width:] for mine in kept], axis=1))
    problems = [] if len(kept) > 1 and np.array_equal(rows[:, :-2], alone[0]) and np.array_equal(
        values[:, :-2], alone[1]) else [f"the stacked nudges' {rows.shape[1] - 2} balls not one path's bits each"]
    physics.card = CpuCard(found)
    states = _linear.frame_states(physics, path, 30.0)
    sensitive = rra.sensitivities(physics, states, adjusted)
    asked = np.array([(couplings.map(qpos).T @ needed)[adjusted[6:]] for qpos, needed in
                      zip(physics.card.given, physics.card.needed)]).reshape(4, len(adjusted), 2, 3, -1)
    wanted = (asked[:, :, 0] - asked[:, :, 1]) / (2 * np.array(_linear.CARD_STEPS)[:, None])
    off = [frame for frame in range(4) for kind in range(3)
           if not np.array_equal(sensitive[frame][kind][6:], wanted[frame, :, kind].T)]
    return problems + ([f"the trunk's rows on frames {sorted(set(off))} not their states' own maps"] if off else [])


def the_balance_is_the_pushes_wrenches_kept_per_path():
    """On the toy, its skin's points 2 mm over the ground under its pelvis (one blended 0.5 on the pelvis and 0.3 on
    the torso), three states (still, turned and moving, sliding at 2 m/s) on MuJoCo's C: `residuals`' columns (each
    push e at a point p of weights summing to s as (s e, (p - s origin) x e)) are `about` of the push's generalised
    force through its point's Jacobian (`pushes`) to 1e-12, and its residuals the least squares of those columns to
    1e-6 N (the least squares stops at SOLVE_TOLERANCE: 4e-9 N apart here); `residuals_kept` gives a path's residuals once at the same masses, and at moved masses works them out
    again, bit for bit `residuals`'."""
    import mujoco
    import numpy as np
    import contact
    import model
    import rra
    import solvers
    from muscles import BALANCE, CONTACT_COST
    from rra import _linear
    physics = toy_physics()
    physics.card = None  # MuJoCo's C, the reference; on a card the same code reads the card's states
    found, data = physics.model, physics.data
    data.qpos[:] = found.qpos0
    mujoco.mj_kinematics(found, data)
    pelvis, torso = model.body_index(found, "pelvis"), model.body_index(found, "torso")
    under = np.array([[x, 0.902, z] for x in (-0.14, 0.0, 0.14) for z in (-0.09, 0.09)] + [[0.05, 0.903, 0.0]])
    weights = np.zeros((len(under), 2))
    weights[:, 0] = 1.0
    weights[-1] = [0.5, 0.3]
    physics.skin = contact.Skin(under, weights, [model.own_pose(found, data, body) for body in (pelvis, torso)],
                                [pelvis, torso], [np.eye(4)] * 2)
    physics.ground = np.array([[[-5.0, 0.9, -5.0], [5.0, 0.9, 5.0], [5.0, 0.9, -5.0]],
                               [[-5.0, 0.9, -5.0], [-5.0, 0.9, 5.0], [5.0, 0.9, 5.0]]])
    physics.up = __import__("ground").normals(physics.ground)
    states = []
    for turn, speed in ((0.0, 0.0), (0.05, 0.3), (0.0, 2.0)):
        qpos = found.qpos0.copy()
        mujoco.mju_axisAngle2Quat(qpos[3:7], np.array([1.0, 0.0, 0.0]), turn)
        qpos[7] = 0.2
        qvel, qacc = np.zeros(found.nv), np.zeros(found.nv)
        qvel[[0, 3, 6]], qacc[[0, 2, 6]] = [speed, 0.4, -0.5], [0.5, 1.0, 2.0]
        data.qpos[:] = qpos
        mujoco.mj_kinematics(found, data)
        states.append((qpos, qvel, qacc, data.xpos[pelvis].copy()))
    problems, wanted = [], []
    touching = contact.touching_all(found, _linear.posed(physics, *[np.array(values) for values in
                                                                     list(zip(*states))[:3]]), physics.ground,
                                    physics.up, physics.skin)
    for (qpos, qvel, qacc, origin), mine in zip(states, touching):
        needed = _linear.about(found, data, physics.needed(qpos, qvel, qacc), origin)
        columns = np.array([_linear.about(found, data, along.T @ edge, origin)
                            for _, along, edges, _ in physics.contacts() for edge in edges]).T
        new = _linear.wrenches(*mine, origin)
        if columns.shape != new.shape or not np.allclose(new, columns, rtol=0.0, atol=1e-12):
            problems.append(f"columns {new.shape} off the Jacobians' {columns.shape}")
            continue
        pushed = solvers.least(BALANCE * columns, BALANCE * needed, np.full(columns.shape[1], CONTACT_COST),
                               np.full(columns.shape[1], np.inf))
        wanted.append(needed - columns @ pushed)
    if any(sum(counts) == 0 for *_, counts in touching) or touching[2][3].min() != 1:
        problems.append("a state with nothing pushed, or the sliding one not sliding")
    got = rra.residuals(physics, states)
    if not problems and not np.allclose(got, wanted, rtol=0.0, atol=1e-6):
        problems.append(f"residuals {np.abs(got - np.array(wanted)).max()} N off the Jacobians'")
    kept = {}
    first = rra.residuals_kept(physics, states, kept)
    problems += [] if rra.residuals_kept(physics, states, kept) is first and len(kept) == 1 else [
        "a path's residuals worked out twice at the same masses"]
    found.body_mass[:] *= 1.01
    moved = rra.residuals_kept(physics, states, kept)
    problems += [] if len(kept) == 2 and np.array_equal(moved, rra.residuals(physics, states)) and not np.array_equal(
        moved, first) else ["moved masses read the kept residuals"]
    return problems


CHECKS = (the_mass_follows_the_mean_upward_residual, a_floating_body_keeps_its_mass_within_the_bound,
          the_torso_moves_under_the_mean_moment_within_its_cap, the_feet_stay_where_they_stood_when_the_pelvis_moves,
          a_leg_past_its_stop_is_left_where_it_stood, a_legs_free_direction_is_held_where_the_frame_stood,
          a_foot_frame_that_does_not_converge_fails, the_cards_footing_equals_minks,
          a_turn_between_two_paths_is_its_angle, the_frame_shares_are_smooth_and_never_above_the_lowered,
          a_move_that_puts_bones_out_of_the_skin_is_seen_by_region, only_the_move_off_the_fitted_path_is_low_passed,
          the_balance_is_the_pushes_wrenches_kept_per_path, the_linearisation_is_each_nudge_measured_alone)


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
