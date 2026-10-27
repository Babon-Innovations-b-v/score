# score/stages/effects/

The effects stage (the paper's Methods, "The canonical scene": effects; experimental, PRD #6): a scene's effects made
from its design and made into its OpenUSD effects layer by `tools/usd/effects.py`, which the assembly stage takes in
place of the seed's. `__init__.py`'s docstring has the make and the gates; `from_design.py` the record made from the
design.

- **Made from the design, never a record written for a scene** (the owner, 2026-10-21: "the modules are not
  agnostic"). Every object of a scene inventory row whose kind emits (CONTEXT.md "row kind", `../row_kinds.py`,
  `data/checks/row-kinds.json`) carries each effect its kind emits from the library of measured effects
  (`data/checks/effects.json`: the emitter, where it stands on its object's own box, why it gives no light, its footage
  sources and checks), found on the stage by its name (`<row>_<n>`) over the seed with the accepted scene record
  (`../layer_base.py`). The record is written into the output (`record.json`) and the gates read it there; `designed`
  fails an emitter on no inventory row's object and a row that emits with no object on the stage. A new effect is a
  new kind in `data/checks/effects.json` measured on footage and named by a row kind, never an entry for one scene. A
  per-row parameter a rule cannot choose is one recorded model call per scene inside the batch, never typed by hand.
- **How an effect is made is one rule, never a pick** (owner, 2026-10-27: "how does the framework decide?").
  `data/checks/effects.json` `methods` maps what a kind is made of (its `matter`) to its maker, with the reason:
  grains (sand, dust piles, cuttings, snow) are Newton's implicit MPM, drawn as one surface built from every grain;
  cloth and cables would be Newton's VBD (no such kind yet: the stage refuses it until it has a maker); steam, mist,
  smoke and fog, and fire, rocket exhaust and sparks, are baked particles, since Newton 1.7.0 has no gas, flame or
  light solver; a glow is the record's keyed lights. `from_design.py` writes each emitter's `made_by` and `drawn` from
  it and `made` dispatches on it; no stage code names a place or an object. A kind's parameter that neither the
  design nor a rule gives is named in its `asked` (the drill's bore and how much it brings up) and read off the
  locked concept by one claude-code call per scene (`asked.py`, EUR 0, cached and ledgered, so the row runs only on
  the owner's PC), its numbers and reasons kept in `record.json`.
- **The old records are retired** (`data/effects/<place>.json`, written for the old concepts; owner, 2026-10-21: all
  old stuff is retired). The completion gate's contents check reads the emitters on the stage; the review's renders
  read no effects views.

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
- **Only scenes whose design shows a row that emits have the row** (the table's `designed("effects")`). The paid
  `effects-look` (the launch's stills before and after, its `shown` and `lit` gates) was retired on 2026-10-21 with
  the launch's records: the layer's `footage` and `light` gates measure each emitter of any scene on the baked
  particles, and the films' visual check (`../complete/visual`) sees them; a new render of its own would only repeat
  them.
  Today's measured kinds are steam off a kettle and a hob, a humidifier's mist and a drilling rig's cuttings (the
  first effect Newton makes: a granular pile by implicit MPM, `inside/`, drawn as a surface from all its grains, its
  flank held to the slip faces measured on Mars); the old records' pump-down fog,
  vacuum vents, Mars drift, dust devils, cigarette smoke and the launch's flame were tied to the game's cycles and
  places and wait to become kinds of their own.
- **Indoors stays indoors.** A record lists its `interiors` (upright cylinders, `[]` for none) whenever an emitter
  stands under the open sky; the bake lets no particle of such an emitter be inside one, and `outside` measures it
  off the composed stage for a minute (a devil wanders). A record where nothing rides or follows a prim says why
  (`rides_nothing`), or `attached` is unknown. A stage reading this one reads without it where it
  does not apply (`Runner.reads`).
- **The row is `effects-layer`.** The store's `effects@<place>` nodes (accepted 2026-10-11) are the unmerged local
  `effects` branch's stage (be73bb0: other checks, `timed` and `seen`), which a new output cannot be compared with. Its
  records for the airlock, garage, hangar, greenhouse and habitat are ported into this schema (2026-10-12) and the
  branch is gone.
- `test_effects_ride_their_design.py` makes a small kitchen stage itself, makes its effects from its design (the
  stove's and the kettle's steam at their measured spots), passes every gate and fails `designed` on a row with no
  object; a drilling rig on Mars lays its pile as a surface (Newton's run stood in for by a cone, the scene's ask by
  a stand-in answer) and fails `footage` on one too flat; an ask left unanswered stops the row; every kind is made
  by its matter's method.
