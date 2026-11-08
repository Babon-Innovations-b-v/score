# score/stages/motion/

**The motion layer** (CONTEXT.md "motion", the owner 2026-10-20, #26): one layer for everything in a place that
moves, as connected modules. Every model comes from the prop pipeline (CONTEXT.md "layer adapter"); a module only
adds what moves it. `stages.MOTION_LAYER` names each module's rows in the stage table:

| module | rows | what it adds | source of the movement |
|---|---|---|---|
| rigid | `motion` (this folder) | joints and paths: hinge (swing), rail (slide), lane (path), spin | the design's moving rows by their kind's rule (`from_design.py`, `data/checks/row-kinds.json`) |
| physics | `settle` (`../settling`), `physics-layer`, `physics-trial` (`../physics`) | settling, falling, cloth | simulation (settle and physics trial: Newton, one pinned Python) |
| bodies | `cast`, `characters-layer` (`../cast`), `people-body-*`, `people-dress-*`, `people-clips` (`../people_bodies`, `tools/characters`) | rigging (UniRig), body reading (SAM 3D Body), generated body motion (Kimodo) | generated motion |
| growth | `crops-layer` (`../crops`) | growth stages and sway of plants | formula |

Every paid job of the layer is one shot in a batch: no paid retry, no fallback chain, no tweak loop; a job that fails
is a gap. The free motion check (`check.py`, #23) judges every rigid move against its intended motion; the films'
gate (`../demo_film`, `seen_faults`) holds a place whose cast record stands people to showing one. The rigid
module moves every moving row of the design by its kind's rule, so it leaves no motion gap of its own (its old
`needs.py`, which named rows the old records left unmoved, went with them, 2026-10-21).

The motion stage (the paper's Methods, "The canonical scene": motion; experimental, PRD #6): a scene's motion layer,
its rigid moves made from its design (`from_design.py`), written by `tools/usd/motion_layer.py` over the scene's
stage (`../layer_base.py`). `__init__.py`'s docstring has the make and the gates; `space.py` the measures of space
(hulls, still surfaces, heights under a spot); `check.py` the motion check.

- **Made from the design, never a record written for a scene** (the owner, 2026-10-21: "the modules are not
  agnostic"). Every object of a scene inventory row whose kind moves (CONTEXT.md "row kind", `../row_kinds.py`)
  moves by its kind's rule in `data/checks/row-kinds.json`: a door swings a right angle on its own left edge and
  shuts again, a crane slews about its middle, a fan spins a whole number of turns a round, each at the middle of its
  motion kind's cited speeds (`data/checks/motion.json`); a vehicle or a lift stands with the rule's reason. The
  row's own words choose its rule (`from_design.rule_of`): a sliding door slides, a garage or roller door rises, a
  double door splits, an open one stands posed open. A door (`needs` "passes") moves only for a walker of the
  accepted cast (the cast row's `cast.json`, an `after`) whose route comes within a metre of it, opened by its
  arrival and shut once it is past, played once; with nobody passing it stands with `still_without` (the audit of
  2026-11-04: 22 doors swung on a 2 s / 10 s clock with nobody there; `passed` and `rests` fail that now). A rocket
  launches (`launch`): from the layer's start it climbs straight up (`climb`) at the middle of its kind's cited push
  (thrust over liftoff mass, Saturn V to Falcon 9) less the pull of the body its site stands on (the scene's sky
  inputs, `{home}/design/sky/<place>.json`), and `speeds` reads its acceleration off the stage plus that body's pull
  against the push; its exhaust stays `unmade` until an effect kind makes it. A flag on a body with no air (under
  `natural_grounds.WIND_KPA`: the Moon) hangs still with that reason. A move no
  writer makes (a rocket's exhaust, a flag's cloth in the air, a body of water, a double door's leaves) is `unmade` and fails
  `covered`, as does every row no stage makes (`row_kinds.uncovered`: a moving word in its noun; a screen's picture is
  the screens stage's, `data/checks/screens.json` `read_by`, #88),
  never a still. The record is written into the output (`moves.json`) and the gates
  read it there; `designed` fails a moving thing on no inventory row's object and a moving row with no object on
  the stage. A moving row a carried batch gap names (by its id or its take, the row's `thing`: the bake's gap
  names the take only) is still failed by name, recorded in `left_out` and given a gap of its own in the output's
  `batch-gaps.json` beside the carried ones, so the table moves that fault (`stages.BATCH_GATES`, motion@garage
  2026-10-28: the lift's bake job failed in the batch). The accepted plan's `placed` gap on a row counts as such a
  gap (`from_design.plan_gaps`: hangar's floor hatch, placed none of, 2026-10-29), its name pointing at where the
  source fix waits; a take the surface line left out is named by the table's `leaving_out` from the hand-in
  (hangar's overhead crane). A row with no object and no gap still stops the line. A per-row parameter a rule cannot choose is one recorded model call per scene inside the batch, never
  typed by hand.
- **The old records are retired** (`data/motion/<place>.json`, the game's timed motions, `data/motion/rigid/` and
  `data/motion/models/`, written for the old concepts; owner, 2026-10-21: all old stuff is retired). The sound row
  reads this row's `moves.json` for its moving things.

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
- **A parted build moves its parts on their pivots** (#19, `score/stages/props/moving_parts`): an object whose parts
  are named with a joint (`<part>__hinge_<axis>[n]`, `from_design.parts_of`) swings each hinged part about its own
  origin and axis instead of the whole: a double door's two leaves (so `split` is made, not unmade), a hatch's lid on
  its level hinge (so a lying hatch opens, never LYING), posed open where its words say open, timed by the walkers
  passing that part. `covered`, `passed`, `rests` and `designed` read a part's move as its object's
  (`under`, `from_design.object_path`); `follows` holds a turn to its own `axis`. A parked vehicle's wheels (`spin`
  parts) stand with it until a vehicle drives.
- **Swings are fitted by the gate** (`fitted`, in the make): a swing that strikes is tried the other way, then
  `FIT_STEP` degrees less either way down to `FIT_LEAST` (60), the first that `clear` passes kept and said in its
  `from`; one that strikes every way stands with the strike as its `still` reason, so a door against a wall or a
  crane over a neighbour never stops the line. A thing lying lower than it is wide both ways (a floor hatch, a crane
  spanning a hall) never swings: a swing turns about an upright line (`from_design.LYING`). One in one piece whose words say open
  (wreck's open hatch, 2026-11-08) stands open as its model is built (`LYING_OPEN`), and `rests` passes it standing
  still, never asking a swing to pose it.
- **A thing it starts inside is its mount** (a boom's rail, a hatch's frame), named in `clear`'s findings and not
  judged; a moving thing on a `rail` must keep touching one of them.
- **Over the place's accepted scene record, the place alone.** Where the place has a scene-record row the layer is
  written over its accepted record as the assembly writes it (`../layer_base.py`), else over the seed; the places it
  shows are left out (but their prims that move), since neighbours show each other.
- **A moving row's models are the prop pipeline's**, laid by the assembly like any other object; the motion layer only
  moves them (the `motion-models` rows, which laid a record of models per place, were retired with the records,
  2026-10-21). A moving thing on the `ground` drives on every still thing under its footprint up to CLIMB_MOST over its
  underside (floor, sill, yard), rising and falling with it; an open path (`closed`: false) ends where it stops, and
  `relative` points are offsets from where the moving thing rests.
- **Only scenes whose design shows a row that moves have the row** (the table's `designed("motion")`). The assembly takes the
  accepted layer (`assembly.LAYERS`) in place of the seed's `layers/motion.usda`.
- Effects tied to motion (dust, exhaust) are the effects stage's (`follows`, `on`).
- `test_a_thing_moves_as_its_design_says.py` makes a small scene itself and its moves from its design (a door swung
  on its own edge, a fan's whole turns, a rover parked), passes every gate, keeps the door shut with nobody in the
  scene and fails `designed` on a row with no object; then a small place of its own with a path, a swing and a slide
  written as the output's record, breaking the motion check's rules and `clear` once each.
