# score/stages/effects/

The effects stage (the paper's Methods, "The canonical scene": effects; experimental, PRD #6): a place's effects record
(`data/effects/<place>.json`) made into its OpenUSD effects layer by `tools/usd/effects.py`, which the assembly stage
takes in place of the seed's. `__init__.py`'s docstring has the make and the gates; `look.py` the paid look.

- **Real footage first** (the owner's rule). An effect the game never drew is modelled on real footage: its record's
  `footage` block lists the sources (photographs, what was measured on each) and the checks, each a measure of the
  baked particles at a moment with the range read off the footage: the launch's after lift-off in the rocket's
  heights, every other place's at its own `at` second in metres from an `anchor` emitter. Never
  widen a range to pass a gate: measure more footage, or put the record right. Many fine particles, never thinned to
  draw cheaper; big sparse ones read as dots.
- **Tied to the world.** What burns on a moving thing rides it (`on`: the emitter is the prim's child), what it leaves
  behind follows its motion (`follows`: each particle let out where the prim stood at its birth), and an event plays
  once at its own seconds (`once`). The `attached` gate reads this off the composed stage, never off the record.
- **The light is part of the effect.** A record's `lights` ride their prim like an emitter; `light` measures what the
  flame gives the pad against the place's own lamps, and the look's `lit` measures it in the pictures. A record whose
  effects light nothing (steam, fog, ice) says so in `no_light`, or `light` is unknown.
- **Only `STAGED` places have the row** (the launch, its accepted smoke without venting, the owner's call of 2026-10-14; the pump-downs, mist and
  steam of the airlock, garage, hangar, greenhouse and habitat; the flat's cigarette smoke;
  the camp's and its grounds' Mars drift and dust devils), and `look.LOOKED` the paid look (the launch only) until the
  owner has seen the launch's stills. Other places keep their seed's effects layer; a place gets the row only when
  its record passes every gate, so a record waiting on a mover (wheel dust, a ship's exhaust) is not staged.
- **Indoors stays indoors.** A record lists its `interiors` (upright cylinders, `[]` for none) whenever an emitter
  stands under the open sky; the bake lets no particle of such an emitter be inside one, and `outside` measures it
  off the composed stage for a minute (a devil wanders). A record where nothing rides or follows a prim says why
  (`rides_nothing`), or `attached` is unknown. A stage reading this one reads without it where it
  does not apply (`Runner.reads`).
- **Stills, not films**: the look renders the place's review cameras at a few moments (`look.MOMENTS`); films wait for
  the owner's go. Run it with `python -m score run world1 --place launch --stage effects-look --detach` in the
  background, which drives terrain, effects, assembly and the look.
- **The row is `effects-layer`.** The store's `effects@<place>` nodes (accepted 2026-10-11) are the unmerged local
  `effects` branch's stage (be73bb0: other checks, `timed` and `seen`), which a new output cannot be compared with. Its
  records for the airlock, garage, hangar, greenhouse and habitat are ported into this schema (2026-10-12) and the
  branch is gone.
- `effects_test.py` runs the make and the gates on the launch's own record and seed, and breaks each gate once.
