# score/stages/sim_body/

The sim body stage (experimental, #65; PRD #56; CONTEXT.md "sim body"): row `sim-body@<place>` for a place whose
design shows people, every character of its accepted cast as a body on Newton. `__init__.py`'s docstring has the
make and the gates; `inside/sim_body.py` is the run, in Newton's own Python.

- **The body is SOMA's segments, never a template resized.** It is built from `people-clips-made`'s `rig.npz`, the rig
  every clip plays: a segment a kept joint at its bind frame, its mass share and inertia from the rig's closed surface
  (voxels owned by strongest skin weight). Never give it a body file of its own or a hand-typed mass table.
- **Mass by #64's rule**: the cast's stated `weight` (kg), else `height` (m, else the body's own) squared times the
  reference BMI of `sex` (NCD-RisC 2016, the mean of both unstated), marked `estimated` in the record. Never tune a
  mass, a drive gain or a gate to pass: fix the method and measure again.
- **Ground forces come from contact**: the root has no actuator and its height is free; its helper holds only the
  horizontal path and the turn, and is recorded. Do not let a helper carry weight.
- **One Newton environment**: the run uses the physics stage's `score/stages/physics/inside/newton_env.sh` (declared as
  `sim env`), built once at `$PROPS_HOME/envs/newton_env`; never a second env or a pip install of its own. It runs on
  this machine (free), on MuJoCo's CPU backend: newton 1.7.0 with mujoco-warp 3.15.0 in deterministic mode turns every
  body over 60 dofs to NaN within 15 ms (#60; this body has 72), and the CPU backend repeats bit for bit. Euler, its
  drive damping on the joints (Euler integrates joint damping implicitly; an actuator's velocity gain explicitly blew
  the body up in 10 ms).
- **It stands on the scene's own ground**: the stage the cast is measured on (`layer_base.built` with the scene record,
  `cast/measure.solids` on the terrain row's made ground), the solids within `REACH` of each clip's path, in the body's
  own frame. Never a flat floor again. On the CPU backend MuJoCo runs its own collision and meets a mesh as its convex
  hull, so the ground goes in as a heightfield of standing heights (`inside/sim_body.py` `heightfield`), and every
  shape's contact gap is 0 (Newton's default 0.1 m made MuJoCo hold a foot 20 cm up or let a box through). Each
  person's ground sits on MuJoCo's world body, where Newton's collision groups cannot keep it from the other bodies, so
  the people stand apart in the one world (`apart_of`) and their output is in their own frame again. Heights for the
  gates are measured on the drawn triangles, never on the heightfield.
- **Only people-cloth reads its output** (and imports `segments_of`), so an edit here moves people-cloth's key too;
  wiring it into the assembly is a change of its own (it re-keys every people place's assembly).
- Tests: `test_a_body_built_from_its_segments_carries_its_weight_and_follows_its_clip.py` (a toy rig and seed, written
  runs; Newton itself is not run there: its numbers are on #65).
