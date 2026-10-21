# score/stages/motion/

**The motion layer** (CONTEXT.md "motion", the owner 2026-10-20, #26): one layer for everything in a place that
moves, as connected modules. Every model comes from the prop pipeline (CONTEXT.md "layer adapter"); a module only
adds what moves it. `stages.MOTION_LAYER` names each module's rows in the stage table:

| module | rows | what it adds | source of the movement |
|---|---|---|---|
| models | `motion-models`, `motion-models-boxes` (`models/`, its overlay) | the prop pipeline's models of rigid moving things, laid on what holds them up | none: layout |
| rigid | `motion` (this folder) | joints and paths: hinge (swing), rail (slide), lane (path), spin | the design's moving rows by their kind's rule (`from_design.py`, `data/checks/row-kinds.json`) |
| physics | `settle` (`../settling`), `physics-layer`, `physics-trial` (`../physics`) | settling, falling, cloth | simulation (`tools/usd/settle.py`, Bullet) |
| bodies | `cast`, `characters-layer` (`../cast`), `people-body-*`, `people-dress-*`, `people-clips` (`../people_bodies`, `tools/characters`) | rigging (UniRig), body reading (SAM 3D Body), generated body motion (Kimodo), drapes (GarmentCode) | generated motion |
| growth | `crops-layer` (`../crops`) | growth stages and sway of plants | formula |

Every paid job of the layer is one shot in a batch: no paid retry, no fallback chain, no tweak loop; a job that fails
is a gap. The free motion check (`check.py`, #23) judges every rigid move against its intended motion; the films'
gate (`../demo_film`, `seen_faults`) holds a place whose cast record stands people to showing one. What the layer
needs at a place is worked out free in `needs.py` (a row of a moving kind nothing moves, a motion need no record
names), the gaps check's `motion` source (`../complete/gaps/layers.py`), each a line of code work, never a guess.

The motion stage (the paper's Methods, "The canonical scene": motion; experimental, PRD #6): a scene's motion layer,
its rigid moves made from its design (`from_design.py`), written by `tools/usd/motion_layer.py` over the scene's
stage (`../layer_base.py`). `__init__.py`'s docstring has the make and the gates; `space.py` the measures of space
(hulls, still surfaces, heights under a spot); `check.py` the motion check.

- **Made from the design, never a record written for a scene** (the owner, 2026-10-21: "the modules are not
  agnostic"). Every object of a scene inventory row whose kind moves (CONTEXT.md "row kind", `../row_kinds.py`)
  moves by its kind's rule in `data/checks/row-kinds.json`: a door swings a right angle on its own left edge and
  shuts again, a crane slews about its middle, a fan spins a whole number of turns a round, each at the middle of its
  motion kind's cited speeds (`data/checks/motion.json`); a vehicle or a lift stands with the rule's reason; a rule
  with `needs` moves only where the scene holds what it serves (a door swings only where somebody passes: a row that
  `walks`), else it stands with `still_without`. The record is written into the output (`moves.json`) and the gates
  read it there; `designed` fails a moving thing on no inventory row's object and a moving row with no object on
  the stage. A per-row parameter a rule cannot choose is one recorded model call per scene inside the batch, never
  typed by hand.
- **The old records** (`data/motion/<place>.json`, the game's timed motions, and `data/motion/rigid/<place>.json`,
  written for the old concepts) are no input of this stage; the sound stage and the completion gate's contents check
  still read them until their owners move.

- **Motion that fits the place.** A moving thing's numbers are measured, not typed by eye: its path stays in its free space
  (`clear`), its speed in the cited range of its kind (`data/checks/motion.json`, every range with its source), its
  loop joins (`loops`), and it stays on what it moves on (`grounded`). Never widen a kind's range to pass a gate: find
  a better source, or put the path right.
- **Every moving row moves, or says why not.** `covered` fails an object of a row whose kind moves that the layer
  leaves standing unless the record's `still` gives the reason; a prim merely named like an old record's moving kind
  (`data/checks/motion.json`'s `prims`) on no moving row is not asked for.
- **Designed pass-throughs are written, never assumed.** A motion that passes through a still thing by its design (a
  door's edges in its wall's track) is the record's `through` ({motion: {prim pattern: why}}), shown in `clear`'s
  findings; a rule that needs one says so in `data/checks/row-kinds.json`, never in a record for one scene. A thing standing in a
  track by layout (the garage's pressure gauge in the big door's way) is a fault of the place, not a pass-through.
- **Swings are fitted by the gate** (`fitted`, in the make): a swing that strikes is tried the other way, then
  `FIT_STEP` degrees less either way down to `FIT_LEAST` (60), the first that `clear` passes kept and said in its
  `from`; one that strikes every way stands with the strike as its `still` reason, so a door against a wall or a
  crane over a neighbour never stops the line. A thing lying lower than it is wide both ways (a floor hatch, a crane
  spanning a hall) never swings: a swing turns about an upright line (`from_design.LYING`).
- **A thing it starts inside is its mount** (a boom's rail, a hatch's frame), named in `clear`'s findings and not
  judged; a moving thing on a `rail` must keep touching one of them.
- **Over the place's accepted scene record, the place alone.** Where the place has a scene-record row the layer is
  written over its accepted record as the assembly writes it (`../layer_base.py`), else over the seed; the places it
  shows are left out (but their prims that move), since neighbours show each other.
- **Models move where the models step lays them.** A place with a motion models record (the garage's rover) has its
  accepted `motion-models` layer in the stage, as the assembly takes it; its motion waits on that row. A moving thing on the
  `ground` drives on every still thing under its footprint up to CLIMB_MOST over its underside (floor, sill, yard),
  rising and falling with it; an open path (`closed`: false) ends where it stops, and `relative` points are offsets
  from where the moving thing rests.
- **Only scenes whose design shows a row that moves have the row** (the table's `designed("motion")`). The assembly takes the
  accepted layer (`assembly.LAYERS`) in place of the seed's `layers/motion.usda`.
- Effects tied to motion (dust, exhaust) are the effects stage's (`follows`, `on`).
- `motion_test.py` makes a small scene itself and its moves from its design (a door swung on its own edge, a fan's
  whole turns, a rover parked), passes every gate, keeps the door shut with nobody in the scene and fails `designed`
  on a row with no object; `check_test.py` makes a small place of its own, writes a path, a swing and a slide as the
  output's record, and breaks the motion check's rules and `clear` once each.
