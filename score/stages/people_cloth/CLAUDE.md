# score/stages/people_cloth/

The people cloth stage (experimental; owner 2026-10-27, "bring back"; PRD #56): row `people-cloth@<place>` for a
place whose design shows people, each character's loose garment parts as cloth on Newton's VBD against its sim body
(`../sim_body`). `__init__.py`'s docstring has the make and the gates; `inside/cloth.py` is the run, in Newton's own
Python.

- **Not the retired drapes.** The owner rejected Newton's drapes on 2026-10-10 (GarmentCode patterns sewn and settled
  on a still body, then baked) and the SOMA shell replaced them on 2026-10-13. Here the built, dressed garment keeps
  its shape; only its loose points are simulated, every other point rides the skin. Never sew, re-pattern or settle a
  whole garment here.
- **Loose is measured, never marked by hand**: a point whose rig point stands off the fitted SOMA shell over
  `people_bodies.bodies.OFFSET_MOST`, the shell gate's own loose cloth. No look marks a garment loose, and no design
  today wears a skirt, coat or cape: the astronaut has 6 loose points of 9,504 (its chest front).
- **Cloth values come from the part's library surface**: its recipe (the people line's surface library, read beside)
  and that recipe's row in `data/physics/cloth.json`, each value with its source. A recipe with no row leaves the
  part baked and named. Never type a stiffness, density or damping here, and never tune one or a gate to pass.
- **No cloth damping of its own**: Newton's default (10 N s/m) against cotton's 5 N/m shear held loose points 5 cm
  behind a walking body within 8 frames (2026-10-27). The implicit step's loss is the only damping.
- **One Newton world a person**: each sim-body run stands in the person's own frame, so in one world they overlap
  and one person's body pushed another's cloth 11 cm (2026-10-27).
- **One Newton environment**: the physics stage's `newton_env.sh` (declared as `sim env`), on this machine's card
  (`DEVICE`), VBD run-to-run deterministic (two runs gave identical points).
- **Nothing reads its output yet**, so it moves no other row's key; the assembly taking `layers/people_cloth.usdc` is a
  change of its own (it re-keys every people place's assembly), as is matching the characters layer's clip cut and
  start (the layer's samples are the sim body's own frames from 0).
- Tests: `test_loose_cloth_rides_its_sim_body_and_is_judged_by_measure.py` (toys and written runs; Newton is not run
  there).
