# score/stages/motion/

**The motion layer** (CONTEXT.md "motion", the owner 2026-10-20, #26): one layer for everything in a place that
moves, as connected modules. Every model comes from the prop pipeline (CONTEXT.md "layer adapter"); a module only
adds what moves it. `stages.MOTION_LAYER` names each module's rows in the stage table:

| module | rows | what it adds | source of the movement |
|---|---|---|---|
| models | `motion-models`, `motion-models-boxes` (`models/`, its overlay) | the prop pipeline's models of rigid moving things, laid on what holds them up | none: layout |
| rigid | `motion` (this folder) | joints and paths: hinge (swing), rail (slide), lane (path), spin | formula-driven paths from `data/motion/rigid/` and the game's `data/motion/` |
| physics | `settle` (`../settling`), `physics-layer`, `physics-trial` (`../physics`) | settling, falling, cloth | simulation (`tools/usd/settle.py`, Bullet) |
| bodies | `cast`, `characters-layer` (`../cast`), `people-body-*`, `people-dress-*`, `people-clips` (`../people_bodies`, `tools/characters`) | rigging (UniRig), body reading (SAM 3D Body), generated body motion (Kimodo), drapes (GarmentCode) | generated motion |
| growth | `crops-layer` (`../crops`) | growth stages and sway of plants | formula |

Every paid job of the layer is one shot in a batch: no paid retry, no fallback chain, no tweak loop; a job that fails
is a gap. The free motion check (`check.py`, #23) judges every rigid move against its intended motion; the films'
gate (`../demo_film`, `seen_faults`) holds a place whose cast record stands people to showing one. What the layer
needs at a place is worked out free in `needs.py` (a row of a moving kind nothing moves, a motion need no record
names), the gaps check's `motion` source (`../complete/gaps/layers.py`), each a line of code work, never a guess.

The motion stage (the paper's Methods, "The canonical scene": motion; experimental, PRD #6): a place's motion layer,
the game's own timed motions (`data/motion/<place>.json`) and the rigid moves SCORE gives the things that move there
(`data/motion/rigid/<place>.json`), written by `tools/usd/motion_layer.py` over the place's seed stage.
`__init__.py`'s docstring has the make and the gates; `space.py` the measures of space (hulls, still surfaces,
heights under a spot); `check.py` the motion check.

- **Motion that fits the place.** A moving thing's numbers are measured, not typed by eye: its path stays in its free space
  (`clear`), its speed in the cited range of its kind (`data/checks/motion.json`, every range with its source), its
  loop joins (`loops`), and it stays on what it moves on (`grounded`). Never widen a kind's range to pass a gate: find
  a better source, or put the path right.
- **Every moving kind moves, or says why not.** `covered` fails a prim of a moving kind the layer leaves standing
  unless the rigid record's `still` gives the reason (the street's car parked with its driver waiting).
- **The game's timed motions stay the game's.** Their records (`data/motion`) are read as they are; the effects stage
  reads them too, so editing one moves the effects rows' keys. A place's rigid record may set the layer's
  `seconds` so the game's loops also fit it whole.
- **Designed pass-throughs are written, never assumed.** A motion that passes through a still thing by its design (the
  airlock's doors sinking through a floor whose slot the stage does not cut, a door's edges in its wall's track) is
  the rigid record's `through` ({motion: {prim pattern: why}}), shown in `clear`'s findings. A thing standing in a
  track by layout (the garage's pressure gauge in the big door's way) is a fault of the place, not a pass-through.
- **Hatches are fitted by the gate.** A hatch opens into its room as far as `clear` allows (100 degrees down to 60);
  one that strikes at every angle stays shut with the strike as its `still` reason.
- **A thing it starts inside is its mount** (a boom's rail, a hatch's frame), named in `clear`'s findings and not
  judged; a moving thing on a `rail` must keep touching one of them.
- **Over the place's accepted scene record, the place alone.** Where the place has a scene-record row the layer is
  written over its accepted record as the assembly writes it, else over the seed; the places it shows are left out
  (but their prims that move), since neighbours show each other. A game prim the new record names otherwise is the
  rigid record's `renamed`; one the record dropped fails `covered`, never written to nothing, unless the rigid
  record's `removed` gives the concept's reason (the workshop's robot turntable: concept K10 shows no robot).
- **Models move where the models step lays them.** A place with a motion models record (the garage's rover) has its
  accepted `motion-models` layer in the stage, as the assembly takes it; its motion waits on that row. A moving thing on the
  `ground` drives on every still thing under its footprint up to CLIMB_MOST over its underside (floor, sill, yard),
  rising and falling with it; an open path (`closed`: false) ends where it stops, and `relative` points are offsets
  from where the moving thing rests.
- **The made ground stands in the stage only where the rigid record asks** (`ground`: the garage, whose rover drives
  out onto its yard), sublayered from the terrain stage's place layer as the assembly does.
- **Only places with a rigid record have the row.** The assembly takes the accepted layer (`assembly.LAYERS`) in
  place of the seed's `layers/motion.usda`.
- Effects tied to motion (dust, exhaust) are the effects stage's (`follows`, `on`).
- `motion_test.py` runs the gates on the launch's and hub's seeds (absent since the work folder was lost, 2026-10-19); `check_test.py` makes a small place of its own, writes a path, a swing and a slide, and breaks the motion check's rules and `clear` once each.
