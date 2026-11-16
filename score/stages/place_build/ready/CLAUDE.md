# score/stages/place_build/ready/

Physics ready (#128, owner 2026-11-16: "this is alll very much not physics ready env's"): the placing agent's check of
a place_build scene for the walkers (sim body) and pushed objects, and its `on` helper. The CLI is place_build's
(`check`, `on`); this module tells, it never moves anything but what `on` is asked to lay.

- **Roles come from the scene**: `score:role` when set, else the object's marks, kind, name and library address
  (`role_of`). A role word list is not a judgement of quality: when a role reads wrong, set `score:role`, never widen
  a tolerance.
- **Reuse, no new physics**: resting.py's tolerances, weight and footprint; reach.py's Recast-style walker floor
  (spans, steps, pieces) with the walkway's own erosion; MuJoCo (settle_mujoco.py) for the settle. The settle runs in
  the physics trial's own Python (score/stages/physics/inside/newton_env.sh, MuJoCo as pinned there, the one sim
  body's walkers use), one small mjSpec model an object, free on this PC's CPU.
- **The walkers' ground and routes** (#128, 2026-11-16): `solids` is what a walker stands on and runs into (every
  object the check reads, doors open, no characters), the ground sim body and scene clips read for a place_build
  scene (their input `place-build`, INPUT); `route` (`place_build route --through`) is a walker's way through spots on
  the check's own walkers' floor (WALKWAY wide): the shortest way over standing spans, its corners kept by line of
  sight and rounded over ROUND, so a walk path never leaves the floor the check judged.
- **The ground is read near the place**: a ground's faces more than GROUND_REACH past the laid objects' box are left
  out (`near_ground`), so a terrain to the horizon (800 000 faces) fits the 8 GB check; walkers' ground included.
- **A planted fault per measure** is in the test fixture; a new measure gets its fault there, seen caught.
- Test: `test_every_planted_physics_fault_is_told_by_name.py` (its MuJoCo part prints skipped in a sandbox home with
  no newton_env; link `$PROPS_HOME/envs/newton_env` to run it whole).
