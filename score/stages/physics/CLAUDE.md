# score/stages/physics/

The physics stage (experimental, F11: the paper's "responsive"). `__init__.py`'s docstring has the two rows and their
gates; `tools/usd/physics.py` writes the layers; `inside/physics_trial.py` is the Blender script the trial runs on a
rented machine.

- **The stage's own schema is the source.** Collision, mass, material, joints, drives and hands are UsdPhysics in the
  stage's layers; the Blender script reads them through pxr and maps them onto Bullet. Never give the Blender script
  a number the stage does not hold: write it into the layer, so any UsdPhysics reader (PhysX, Newton) runs the same
  trial.
- **Mass is the model's surface area times its material's sheet and density** (props are hollow shells); friction and
  restitution are per material (`data/physics/materials.json`, textbook values with their source). A model with no
  labelled parts takes its trial record's `material`. Never tune a mass or a friction to pass a gate.
- **A door opens by its hinge's motor** (a DriveAPI with a timed torque cap), not by a kinematic hand: on the toy place
  a kinematic box striking a hinged leaf kicked it 50 degrees the wrong way. Hands push free objects (the stool).
- **Bullet's hinge turns its first object against its second**: the constraint takes the joint's body1 first, as
  UsdPhysics measures the angle (checked on the toy place). A motor turns about its own x.
- **Blender 5.0.1's USD reader may leave a y-up stage unturned** (a stage with no root object, the toy's): the script
  checks a body against its stage pose and turns the roots itself.
- Only places with `data/physics/<place>.json` have the rows (the habitat). The rows read the place's accepted
  assembly on its current key: they wait until the place's line has landed it. Run with
  `python -m score run world1 --place habitat --stage physics-trial --detach`, only when `python -m score.stages status
  habitat` shows `assembly@habitat` accepted (else `--stage` drives the place's surface line).
- Tests: `physics_test.py` here (measures and gates on a written run), `tools/usd/physics_test.py` (the layers on a toy
  place; `physics_test.py <folder>` keeps the toy for a Blender run of seconds:
  `python3 tools/blender/session.py batch score/stages/physics/inside/physics_trial.py -- <folder>/toy/toy.usda out.json`).
