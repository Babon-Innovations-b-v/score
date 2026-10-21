# score/stages/complete/prepare/

Prepare a batch (CONTEXT.md "batch", #21): the free risk work before a paid batch, so it runs once and right, and
the one figure the creator says yes to. Today it prepares the environment's remake through the prop pipeline (#19).
`__init__.py`'s docstring has the modules and the record's shape. Bible: `architecture/components`.

- **Free, local, never a row.** Reads the scene inventory readings, the library's index (read only: score never imports the
  library), `data/costs/per-unit.json`, the cloud ledgers and the store; nothing in the stage table imports it, so no
  key moves. No Blender, no model, nothing judged or bought. `--stock` is the provider's free listing; `--moved` is
  `score moved`'s dry run (minutes).
- **The rows are the scene inventory readings** (owner, 2026-10-21; `groups.current`): each place's and outside
  shell's current reading (`score/review/reading.reading_of`: read from its picked draw by today's method), never
  `data/inventory/` (still read for the library models' sizes and the hub's measured rates only). A place with none
  waits on inventory, no euros (`inventory.waiting`). A reading gives each row its size in metres (Gemini, from
  what it is and the picture, against the place's outline; SAM 3 gives only where, #10): a row's size is its place's
  current plan's item (`groups.plan_sizes`, `score/review/plans.current`, laid at the reading's metres, his edits
  counted: wide and deep as laid, tall the reading's), else its reading's own metres (on a wall, the ceiling or
  another row); a row the reading gave none has none. A row's box is SAM 3's, else Gemini's region from the same
  reading (`groups.boxed_by`, marked so in the hand-in). A model take with no box, a box that is the whole picture or
  no size is an **input gap** (`contract.faults`, `__main__.status_of`): not bought, priced apart
  (`input_gaps_if_bought`), never handed to the loop, so the runner neither buys nor counts it. Rows of
  one model (kind, size ratio, kit) share a take. Each row's route is its noun's (`groups.ROUTES`, owner's rules,
  CONTEXT.md "layer adapter", "motion"): a code row of a shell noun (`groups.SHELL_NOUNS`), a window, stairs or
  building shell is a shell piece (route `shell`); the ground itself is the terrain node's (route `ground`, status
  `terrain node`: no take, never a close-up of the whole picture); people are models of the prop pipeline with the motion
  layer's steps after (`estimate.OWN_ROUTES`); the sky, the effects (water, rain, smoke, mist) and the far city
  are their own routes, priced only by their own measured per unit (unpriced until then), their inputs their
  route's own (not checked here); every other row, terrain too, is a model through the prop pipeline. Each layer
  names the routes it runs (`runs`). Plans may refine positions later, never the count.
- **Every job once.** The figure prices each take's layers one run each (`estimate.one_shot`: one Pro wording a row,
  one draw a map, no finish asked again); no retry share, no second take, no fallback class. A shell piece runs the
  whole route like any model (CONTEXT.md "prop pipeline": the finish route lists its library surface, no maps, so the
  bake, which bakes the listed takes, bakes it, #10). likeness-calibration is no layer of a design's take
  (`__main__.design_route`: it applies only to prop data naming accepted models). Card and processor layers carry the bill share
  (`gaps/price.py` `BILL_SHARE`); Google calls do not.
- **A prediction comes from a measured failure mode, never a guess.** `predict.py` counts the hub's prop-route table
  against the hub's sizes every run: a shape every one of at least `MIN_MEASURED` measured rows failed is a predicted
  gap, not bought, and priced apart (`predicted_gaps_if_bought`); fewer measured rows is `at risk`, still bought.
  The crop's upscale is said, never a prediction (no failure was measured against it).
- **Unmeasured stays unknown.** A layer with no per unit is unpriced and named; one with no measured minutes is
  untimed, and the ETA is then only `at_least_minutes` (`gaps/schedule.py`). The preview clips' layer
  (`estimate.clip_layer`, one clip a bought take) is priced and timed from library-clips' measured run, its minutes
  the places' clips spread over warm cards as the row spreads them (`clips.shares`, `estimate.clip_minutes`).
- **One class and zone a layer** (`machines.py`): the runner's first class in its kind's order, the zone with the
  best boot record in the ledgers, in stock when `--stock` read it; no class in stock is the layer's jobs as gaps.
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
  (missing, drawn, picked), inventory (None before the pick, made when `data/inventory/<place>.json` was read from the
  picked draw, else to read; CONTEXT.md "scene inventory") and plan (remake while the inventory is not made, else
  approved), read from the store (the concept review's draws and picks, `score/review/concepts.py`, first) and `data/places/concepts.json`,
  never judged. The pick is the approval (owner, 2026-10-21): its inventory and then its plan are made from it
  automatically (`score/review/plans.py`; the plan page is for inspecting and fixing, his edits redoing what follows). The cockpit's batch buys only approved places' steps. The old plans'
  `concept.pick` is a hint for drawing, not a constraint.
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
