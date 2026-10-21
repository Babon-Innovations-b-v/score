# score/stages/effects/

The effects stage (the paper's Methods, "The canonical scene": effects; experimental, PRD #6): a scene's effects made
from its design and made into its OpenUSD effects layer by `tools/usd/effects.py`, which the assembly stage takes in
place of the seed's. `__init__.py`'s docstring has the make and the gates; `from_design.py` the record made from the
design; `look.py` the paid look.

- **Made from the design, never a record written for a scene** (the owner, 2026-10-21: "the modules are not
  agnostic"). Every object of a scene inventory row whose kind emits (CONTEXT.md "row kind", `../row_kinds.py`,
  `data/checks/row-kinds.json`) carries each effect its kind emits from the library of measured effects
  (`data/checks/effects.json`: the emitter, where it stands on its object's own box, why it gives no light, its footage
  sources and checks), found on the stage by its name (`<row>_<n>`) over the seed with the accepted scene record
  (`../layer_base.py`). The record is written into the output (`record.json`) and the gates read it there; `designed`
  fails an emitter on no inventory row's object and a row that emits with no object on the stage. A new effect is a
  new kind in `data/checks/effects.json` measured on footage and named by a row kind, never an entry for one scene. A
  per-row parameter a rule cannot choose is one recorded model call per scene inside the batch, never typed by hand.
- **The old records are retired** (`data/effects/<place>.json`, written for the old concepts; owner, 2026-10-21: all
  old stuff is retired). The completion gate's contents check reads the emitters on the stage; the review's renders
  read no effects views; the look waits (below).

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json` that names the place, the prim or pattern, what it is, why it is not from the
  library, who allowed it and when. Every finish is a library surface (`data/library`, the ProcFunc recipes and
  palette tokens): never a picture's own texture, a model's baked-in colour, a default grey or anything else; a
  picture-made model keeps its geometry and gets its finish replaced. The library check
  (`score/stages/complete/library`) lists what does not trace; bible `architecture/components`.
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
- **Only scenes whose design shows a row that emits have the row** (the table's `designed("effects")`), and `look.LOOKED` the paid
  look: none since its launch records were retired and the launch became part of the square's outside (2026-10-21);
  the look is made again only over a design's own effects record, which names no rocket yet.
  Today's measured kinds are steam off a kettle and a hob and a humidifier's mist; the old records' pump-down fog,
  vacuum vents, Mars drift, dust devils, cigarette smoke and the launch's flame were tied to the game's cycles and
  places and wait to become kinds of their own.
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
- `effects_test.py` makes a small kitchen stage itself, makes its effects from its design (the stove's and the
  kettle's steam at their measured spots), passes every gate, fails `designed` on a row with no object and leaves a
  scene with nothing that emits out.
