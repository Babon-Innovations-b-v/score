# score/stages/complete/prepare/

Prepare a batch (CONTEXT.md "batch", #21): the free risk work before a paid batch, so it runs once and right, and
the one figure the creator says yes to. Today it prepares the environment's remake through the prop pipeline (#19).
`__init__.py`'s docstring has the modules and the record's shape. Bible: `architecture/components`.

- **Free, local, never a row.** Reads the scene inventory readings, the library's index (read only: score never imports the
  library), `data/costs/per-unit.json`, the cloud ledgers and the store; nothing in the stage table imports it, so no
  key moves. No Blender, no model, nothing judged or bought. `--stock` is the provider's free listing; `--moved` is
  `score moved`'s dry run (minutes).
- **The rows are the scene inventory readings** (owner, 2026-10-21; `groups.current`): each place's and outside
  shell's current reading (`score/review/reading.reading_of`: read from its locked draw by today's method), never
  `data/inventory/` (retired with the old concepts on 2026-10-21; the library models' sizes are read from the design's
  kept inventories, the hub's measured rates from the evidence's own sizes, `paper/evidence/compare-hub/sizes.json`). A place with none
  waits on inventory, no euros (`inventory.waiting`). A reading gives each row its size in metres (Gemini, from
  what it is and the picture, against the place's outline; SAM 3 gives only where, #10): a row's size is its reading's own
  metres, unless his plan edit sized its item (`groups.row_size`: his edits counted, wide and deep as he laid them,
  tall the reading's), else its plan item's (`groups.plan_sizes`) where the reading gave none; a plan's item is the
  footprint the object is laid in, so it places the object and never sizes its model (coordinator, 2026-10-25: the
  airlock's 0.1 m porch post was baked 0.48 by 1.7 m); a row the plan lays as a run or path (`groups.run_pieces`: several pieces counted or laid, a polygon round an edge; never several items each laying one of it within their lengths end to end, `groups.one_each`: the reading's metres are one of it, 2026-10-26: habitat's 2 m rugs were cut to 0.2 m strips) whose own metres are a line overrunning its item by one of its pieces (`groups.overruns`: never four doors on a door's item, 2026-10-26) measured the whole run, so it is made as one repeating piece, the run over its pieces, each side held to its item (`groups.run_piece`; 2026-10-25: the stairwell's 12 m conduit, the greenhouse's 50 m railing), and its close-up is drawn and checked at that piece (`groups.own_size`, its `read_size`); a row neither sizes has none. A row's box is SAM 3's, else Gemini's region from the same
  reading (`groups.boxed_by`, marked so in the hand-in). A model take with no box, a box that is the whole picture or
  no size is an **input gap** (`contract.faults`, `__main__.status_of`): not bought, priced apart
  (`input_gaps_if_bought`), never handed to the loop, so the runner neither buys nor counts it. Rows of
  one model (kind, size ratio, kit) share a take. Each row's route is its part's (`groups.route_of`, `ROUTES`: the
  part of the place its reading says it is, score/review/reading.py `PARTS`, never a list of nouns; owner, 2026-10-25:
  "no hax tho ... framework remember"; CONTEXT.md "layer adapter", "motion"): a floor, wall, roof, opening or other
  structure is a shell piece (route `shell`); one whose part the place's plan lays itself (`groups.plan_parts`, by
  score/stages/earth_seed/design_shell: an enclosed place's decks, walls, roofs and the openings it writes, an open
  place's raised levels), or that a plan laying its walls names its own shell (`groups.plan_structure`: the stairwell's building shell, its box the whole picture), or arched structure the shell lays at its plan items (`groups.plan_arches`, design_shell.arches: the tube's ribs), is the plan's own (route `plan`, status `laid from the plan`: the earth seed and the scene
  record lay it, no take, no close-up), never by its size; a model row its plan shows beyond the place (the plan's `beyond`: through a window, past its edge, far off, never placed here) or its reading names far off (`groups.beyond_of`: plan_checks.afar, the rows the plan checks leave outside on purpose; 2026-10-26, the street's distant floodlights, flags and palms in the square past its end, which its plan laid in the street) is the backdrop's (route `skyline`, `groups.routed`: no take, no close-up of a far speck), unless it stands on a row laid here (its anchor `on:<id>`, `groups.stood_beyond`: the stairwell's man and woman on its own stairs, listed beyond, are its people), or reaches the picture's foot (`plan_checks.at_foot`: a SAM 3 box within `FOOT_SHARE` of its bottom edge stands before the viewer: the airlock's sandbags; the plan check counts it unplaced and the plan fixes place it where its boxes project, `plan_fixes.brought_in`); a backdrop row a place of its scene makes as a model (`groups.shown_from`: the scene holding it or a place it holds beside, `scene_places`; that place's row of the same object kind, else the nearest whose kind's words hold the row's or are held in them, `source_of`; for a part of a structure, anchored on a wall (a window, door, sign, balcony, facade light) or a shell's part (a building's wall seen beyond: the tube's exterior wall), the nearest shell row standing on the ground taller than it, a building or facade whose finish gives it its look, `structure_of`) is `shown` from there (status `shown from its place`: bought and priced there, no euros here; the scene record stands that place in this one's stage, writer.places_of, and the rows check counts the row made once that place's object stands under its Places); one no place makes is an ordinary model made here and laid far off (`groups.far_made`, route `prop`, marked `far`: the owner, 2026-10-26, "the skyline is world1's own scenes at their real distance, plus ordinary objects for anything that isn't a scene"; a top scene's own are made there, so a place it holds shows them from it: the stairwell's city skyline is the square's), one whose footprint is a line FAR_RUN times its depth and height a run of repeating pieces each as long as it is tall (the square's 1000 m skyline: ten 100 m pieces, its close-up one piece), the scene record standing it where its concept box is seen at its true distance (score/stages/scene_record/far.py); no row is left without a maker; the ground itself is the terrain node's (route `ground`,
  status `terrain node`: no take, never a close-up of the whole picture), and so is a body of water (`terrain.design.water_row`: a terrain row whose words name the ocean recipe, the square's sea, the stairwell's water), laid as water over the ground lowered under it; a row whose part is not read (a reading
  answered before parts were asked) has no route and its take is an input gap (`contract.PART_UNREAD`) until
  `python -m score.review.reading <place>` asks them (`reading.parted`: one call, its rows, boxes and plan kept; a reading parted under an older `reading.PARTS_VERSION` is asked again the same way: since version 2 the hull, dome or tube enclosing the room is its wall, so an enclosed place's plan lays it); people are models of the prop pipeline with the motion
  layer's steps after (`estimate.OWN_ROUTES`); the sky and the effects (rain, smoke, mist) are their own routes, priced only by their own measured per unit (unpriced until then), their inputs their
  route's own (not checked here); every other row, terrain too, is a model through the prop pipeline. Each layer
  names the routes it runs (`runs`). Plans may refine positions later, never the count.
- **Every job once.** The figure prices each take's layers one run each (`estimate.one_shot`: one draw a map, no
  finish asked again); no retry share, no second take, no fallback class. The one exception is the close-up: a
  picture the shape check rejects gets up to three retries (owner, 2026-10-24, 2026-10-25), priced at the per unit
  file's measured pictures a row (`per_model`, the runner's count too). A shell piece runs the whole route like any model (CONTEXT.md "prop pipeline": the finish route lists its library surface, no maps, so the
  bake, which bakes the listed takes, bakes it, #10). likeness-calibration is no layer of a design's take
  (`__main__.design_route`: it applies only to prop data naming accepted models). Card and processor layers carry the bill share
  (`gaps/price.py` `BILL_SHARE`); Google calls do not.
- **A prediction comes from a measured failure mode, never a guess.** `predict.py` counts the hub's prop-route table
  against the hub's sizes every run: a shape every one of at least `MIN_MEASURED` measured rows failed is a predicted
  gap, unless a route builds it after the close-up fails (a thin straight row, built in code:
  `predict.code_built`, score/stages/props/thin_straight.py), which is `at risk`; fewer measured rows is `at risk`. Both are bought and judged by the real gates: a prediction never drops a
  row from the Buy (2026-10-24: street's palms, 0.4 x 1.16 x 8 m, were "rods" by size alone and left out).
  A take this environment already measured is predicted by that, not by its shape (`predict.own_outcome`, from each
  place's accepted close-up, Pixal3D and likeness outputs, `environment_measures`; only at today's object size and
  request, 2026-10-26; one that passed at an older request, a flat row's view or a far row's whole painting, is at risk,
  never its shape's hub rate: the square's 60 m rocket): its close-up passed is a pass (at risk when Pixal3D made no model), every take failed is a
  predicted gap unless a code build passed the likeness (not judged yet: at risk), or its close-up was accepted before
  `LATER_TAKES_SINCE` (its next takes a new request: from the crop alone, upright; measured by shape again).
  The crop's upscale is said, never a prediction (no failure was measured against it).
- **Once-a-scene rows** (`estimate.once_a_scene`: the scene palette and the surface-library row, which makes every
  scene's surfaces fresh, owner 2026-10-21, and every route row whose per unit's forecast rule is one a place, as the
  runner counts it: the rough model): one unit a scene with a bought take, not one a take; each priced at its
  own measured per unit, else at the measured Gemini 3.1 Pro batch answer (`estimate.ASK_PRICED_AS`, the finish
  list's), marked `estimated_from` and counted in `totals.estimated`.
- **Unmeasured stays unknown.** A layer with no per unit is unpriced and named; one with no measured minutes is
  untimed, and the ETA is then only `at_least_minutes` (`gaps/schedule.py`).
- **One class and zone a layer** (`machines.py`): the runner's first class in its kind's order, the zone with the
  best boot record in the ledgers, in stock when `--stock` read it; with no class in stock the first still, its
  jobs waiting for a card of the run's warm pool (no stock never makes a gap: owner, 2026-10-23).
- **Library reuse only under today's route** (owner, 2026-10-20, #21/#41: "wouldn't lock anything"): a matching
  library model is reused only when the owner locked it, or when its provenance names today's route
  (`library.todays_route()`, the route stages' code and gates hashed as the library rows' key hashes them; their
  handover stamps it) and the runner took it there; every other match is remade and priced (`library_old`,
  `library_code_only`). Never a hand-named route.
- **Sharing a take across places is the owner's call** (a place's style may differ): `across_places` prices it
  beside the figure, never in it.
- **Quality is never a cost lever** (owner, 2026-10-20): never lower a setting that ships (Pixal3D's steps, held at
  the #55 lock in `tools/props/pixal.py`; film samples; resolutions; the finish list's thinking), and never list a
  benchmark that would.
- **The benchmarks are one basket item, bought only by the owner's Buy** (`benchmarks.py`, #21; EUR 20 cap in all,
  counted on their highs with the row estimates of the unmeasured ones): prepare lists each with its estimate and
  minutes, the cockpit shows them as the item "Benchmarks" (`score/dashboard/proposals/benchmarks.py`), and his
  checkout starts `python -m score.stages.complete.prepare.benchmarks run --detach`, one batch under the stop his yes
  wrote: each benchmark planned free first, one whose inputs do not stand (or that would buy another paid row) a gap,
  never substituted; the rest each one `score run`, one after another. A benchmark with no paid path is listed as a
  gap. Never start the batch from an agent.
- **Design before the batch** (owner, 2026-10-20, CONTEXT.md "design"; `design.py`): each place's concept
  (missing, drawn, picked: the stored state of a lock), inventory (None before the lock, made when its reading, else the design's kept inventory, was read from the
  locked draw, else to read; CONTEXT.md "scene inventory") and plan (approved only once the design stands whole on
  its lock, `design.waits`: its draw not on a room the plan above has since moved, `concepts.plan_changed`; its
  reading current, `reading.reading_of`; its plan written by today's method or edited after that reading,
  `plans.design_done`; else remake with `waits`
  saying why, so the Buy lists it as waiting; a `parts` place of within.json is no place of the build and never
  listed: the scene it is part of builds it, owner 2026-10-21, `stages.places`), read from the store (the concept review's draws and locks, `score/review/concepts.py`), never judged. The lock is the approval (owner, 2026-10-21): its inventory and then its plan are made from it
  automatically (`score/review/plans.py`; the plan page is for inspecting and fixing, his edits redoing what follows). The cockpit's batch buys only approved places' steps.
- **The runner runs what the figure prices** (`handin.py`, #10): for each designed place (its plan kept where the plan
  stage reads it, `score/review/plans.KEPT`) prepare writes its takes as the shared loop's hand-in
  (`{home}/design/props/<place>.json`: objects, the sized rows, each take's `stages` by `estimate.take_stages`) and
  its surface data (`{home}/design/surfaces/<place>.json`), each only when its bytes change; the stage table reads
  them in place of `data/props` and `data/surfaces`, and the runner counts a designed node's units from its takes'
  `stages` (`gaps/price.design_takes`), so `score plan` lists and prices the same takes at the same per unit and bill
  share (`compute.bill_share`). `prepare_test.py` holds the two equal.
- Run: `.venv/bin/python -m score.stages.complete.prepare [--library DIR] [--stock] [--moved]`, writes
  `WORK/checks/prepare/remake.json`. Test: `PROPS_HOME=$(mktemp -d) .venv/bin/python
  score/stages/complete/prepare/prepare_test.py`.
