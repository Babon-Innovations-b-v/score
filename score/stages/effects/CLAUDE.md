# score/stages/effects/

The effects stage (the paper's Methods, "The canonical scene": effects; experimental, PRD #6): a place's effects record
(`data/effects/<place>.json`) made into its OpenUSD effects layer by `tools/usd/effects.py`, which the assembly stage
takes in place of the seed's. `__init__.py`'s docstring has the make and the gates; `look.py` the paid look.

- **Real footage first** (the owner's rule). An effect the game never drew is modelled on real footage: its record's
  `footage` block lists the sources (photographs, what was measured on each) and the checks, each a measure of the
  baked particles at a moment after lift-off with the range read off the footage, in the rocket's heights. Never
  widen a range to pass a gate: measure more footage, or put the record right. Many fine particles, never thinned to
  draw cheaper; big sparse ones read as dots.
- **Tied to the world.** What burns on a moving thing rides it (`on`: the emitter is the prim's child), what it leaves
  behind follows its motion (`follows`: each particle let out where the prim stood at its birth), and an event plays
  once at its own seconds (`once`). The `attached` gate reads this off the composed stage, never off the record.
- **The light is part of the effect.** A record's `lights` ride their prim like an emitter; `light` measures what the
  flame gives the pad against the place's own lamps, and the look's `lit` measures it in the pictures.
- **Only `STAGED` places have the row** (the proof place, launch), and `look.LOOKED` the paid look, until the owner
  has seen the launch's stills. Other places keep their seed's effects layer. A stage reading this one reads without
  it where it does not apply (`Runner.reads`).
- **Stills, not films**: the look renders the place's review cameras at a few moments (`look.MOMENTS`); films wait for
  the owner's go. Run it with `python -m score run world1 --place launch --stage effects-look --detach` in the
  background, which drives terrain, effects, assembly and the look.
- **The row is `effects-layer`.** The store's `effects@<place>` nodes (accepted 2026-10-11) are the unmerged local
  `effects` branch's stage (be73bb0: other checks, `timed` and `seen`), which a new output cannot be compared with; that
  branch also holds records for the airlock, garage, hangar, habitat and greenhouse in its own schema, the starting
  point for the next places.
- `effects_test.py` runs the make and the gates on the launch's own record and seed, and breaks each gate once.
