# score/stages/physics/

The physics stage (experimental, F11: the paper's "responsive"). `__init__.py`'s docstring has the two rows and their
gates; `tools/usd/physics.py` writes the layers; `inside/physics_trial.py` is the trial, run in Newton (its MuJoCo solver on
Newton's own contacts) in its own pinned Python (`inside/newton_env.sh`) on a rented card, or on this PC.

- **The stage's own schema is the source.** Collision, mass, material, joints, drives and hands are UsdPhysics in the
  stage's layers; Newton's `add_usd` reads them as written. Never give the trial script a number the stage does not
  hold: write it into the layer, so any UsdPhysics reader (PhysX, Newton) runs the same trial. What Newton needs said
  outright is written there too: a hull bound to its body's physics material, the hinge an ArticulationRootAPI (an
  orphan FixedJoint is refused), the leaf filtered against its frame's colliders (a static frame is no body, so the
  joint's no-collision default does not reach it), and `newton:limitStiffness` +inf (UsdPhysics limits are hard,
  Newton's default is a soft spring: the toy's leaf swung to 148.6 degrees through its 100).
- **The engine is Newton with `SolverMuJoCo(use_mujoco_contacts=False, integrator="euler")`** (owner, 2026-10-27; it
  replaced Blender's Bullet outright, PRD #55). MuJoCo's own contacts treat a hollow static as convex; XPBD explodes
  on overlaps; the implicit integrator takes a capped velocity drive's damping as if uncapped (the toy's door crept
  4.9 degrees). The script drives what the importer leaves to its caller every substep: each kinematic hand from its
  time samples, each drive's torque cap from its time-sampled maxForce. Newton has no renderer: the views stay
  Blender's (`tools/blender/inside/usd_views.py`) on the same held card. A falling body differs a little run to run
  on the card (MuJoCo Warp's solver has no deterministic mode with sensors; the contacts are sorted).
- **Mass is the model's surface area times its material's sheet and density** (props are hollow shells); friction and
  restitution are per material (`data/physics/materials.json`, textbook values with their source). A model with no
  labelled parts takes its trial record's `material`. Never tune a mass or a friction to pass a gate.
- **A door opens by its hinge's motor** (a DriveAPI with a timed torque cap), not by a kinematic hand: on the toy place
  a kinematic box striking a hinged leaf kicked it 50 degrees the wrong way. Hands push free objects (the stool).
- **The trial comes from the design, never a record written for a scene** (the owner, 2026-10-21: "the modules are
  not agnostic"). `design.py` makes it: every laid object of a loose row (the row-kind classification,
  `../row_kinds.py`, `data/checks/row-kinds.json`) dropped `DROP_OVER` straight up over where it stands and let fall
  back onto it, one with something in its fall left out by name; the gravity is the body under the scene's top site
  in the environment's physics (`data/physics/setting.json`, up `data/places/within.json`'s holders). The record is
  written into the output (`record.json`) and the trial reads it there; the gate `designed` fails a body that is no
  object of an inventory row. Doors move in the motion layer, so the trial hangs no hinge and says why (`no_hinges`).
  A per-row parameter a rule cannot choose is one recorded model call per scene inside the batch, never typed by hand.
- Only scenes whose design shows a loose row have the rows (the table's `designed("physics")`, `../design_layers.py`). The rows read the place's
  accepted assembly on its current key (its neighbours output where it shows other places: the places its plan's
  leads open onto stand in it under places/, so the trial renders them; never a seed or a retired data/scene
  record): they wait until the place's line has landed it. Run with
  `python -m score run world1 --place habitat --stage physics-trial --detach`, only when `python -m score.stages status
  habitat` shows `assembly@habitat` accepted (else `--stage` drives the place's surface line).
- Tests: `test_the_trial_comes_from_the_design_and_each_gate_fails_its_break.py` here (the trial from a design on
  the toy place, the trial sent to the held card in its own Python, and measures and gates on a written run),
  tools/usd's physics test (the layers on a toy place; run with a `<folder>` it keeps the toy for a trial of about
  20 s on this PC's card: `bash score/stages/physics/inside/newton_env.sh ~/.farm-factory-props/envs/newton_env &&
  ~/.farm-factory-props/envs/newton_env/bin/python score/stages/physics/inside/physics_trial.py <folder>/toy/toy.usda
  out.json`; the first run on a card compiles its kernels, about 100 s).
