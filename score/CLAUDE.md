# score/

The layered framework's core (PRD #6, the design of 2026-10-11): stages run by one runner, every output kept in one
store by its content's hash, gates that block on unknown, a review page per output, and accepts and paid runs the
runner gives by the gates' answers (the owner's answers of 2026-10-11: his picks are made, from concept and style on
everything runs automatically, no spend limit, spend logically). Today's tools in `tools/` move in here stage by
stage as each stage is built; nothing moves before.

- **`checks/`** the gate rules every stage shares: `Verdict` (pass, fail or unknown, a reason, measures, findings),
  `Check` (a judge and the evidence it needs), `judge` (missing evidence is unknown without asking), `overall`
  (fail, else unknown, else pass; nothing judged is unknown), `regressions` (what got worse than the accepted one);
  `grain.py` (a shipping render's specks on its flat area; the table adds it to the rows of `stages.GRAIN_PICTURES`).
- **`contracts/`** every output's schema, version and units, checked both ways: `Contract` (a schema, its version,
  the house units it uses, its faults check; other units than metres, seconds, degrees and Y up are refused),
  `stamp` (the runner checks an output and writes `contract.json` into it before storing; one off its contract is
  not stored), `expect` (a reader refuses an input of another schema or version, or with no stamp). The schemas in
  use: `OPENUSD_STAGE` (one root stage, metres, Y up, a default prim) and `PLACE_MANIFEST`.
- **`store/`** the store over `tools/cloud/runtime/store.py`'s interface (a folder at `$PROPS_HOME/store` by
  default; nothing in the cloud): outputs as content-hashed files and listings, finish records, judgements per
  evidence state, evidence per check and output, accepts (the runner's automatic ones and the owner's), the owner's
  rejects, waivers and spend yeses, the runner's clearances, the environment's finish registry (append-only). Written
  once, never overwritten, and safe for lines side by side (each write lands whole through a `.partial` file of its
  own process; a write-once key is linked into place, so a second writer is refused); `store/durable.py`, installed by the runner and `score.review` only so it is in no row's key, syncs every write to disk before and after it lands, so a reboot leaves it whole or absent, and moves an empty or unparsable object to `quarantine/` beside the store, read as absent, except in the owner areas: an unreadable accept, reject, waiver or spend yes stops the run and stays put (a trade-off kept on purpose: a cut runner's automatic accept then stops every run until it is fixed by hand, since reading it as absent could buy a paid row again); checkouts are read-only copies (never links to the stored bytes), made again
  when changed; an agent's process cannot write the framework
  store's owner areas (the runner's automatic accept excepted). Its docstring has the key layout. `store/restore/`
  (its overlay) rebuilds a lost store by today's keys and gates with a runner that spends nothing (#13).
- **`python -m score run <world> [--place P ...] [--stage S ...] [--jobs N] [--detach]`** and **`python -m score
  status [<world>]`** (`__main__.py`; `--stage` keeps only those stages and the nodes they read, place by place, an environment stage named with `--place` kept with the place nodes it reads, so `--place people --stage people-look` is the people line and its bodies in one run; `--object <name>` (repeat it) narrows a stage that selects (`Stage.selects`) to those objects of its place, the names in its params as `objects`, so a filtered output has its own key, and `graph.selected()` gives them to its files function, so another object's files neither key nor block it; any other stage runs whole): the runner drives every line (the environment's own nodes, then each place's) to its end with no agent
  in the loop (`Runner.drive`, `Runner.lines`), the lines side by side: each node in a forked process of its own, at
  most `--jobs` at once (default 8), so a line waiting on a cloud step holds up no other, and an environment node every line
  reads is made once. Each node's process sets `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and
  `NUMBA_NUM_THREADS` to this PC's cores divided by `--jobs` (at least 1; a smaller value already set stands, an empty one counts as unset, and
  one that is not a whole number above 0 is refused before the run) before its make starts, inside its log (a failed cap
  shows in its fault report), so its children inherit them, and resizes the OpenBLAS pools the drive loaded before it forked; a
  lone node gets only that share too (3 cores at the default 8 on 24), so `--jobs 1` gives a lone heavy node every
  core; more jobs than cores is refused unless given `--oversubscribe`. It starts each node the moment the nodes it reads stand accepted,
  gathers a gate's missing evidence itself (`Stage.gatherers`; a paid one cleared like a paid stage, and only when
  nothing else blocks the output) and waits on every cloud step itself. A node that does not end accepted stops its
  own line only and leaves a plain fault report, `faults/<node>.txt` beside the store (`$PROPS_HOME/store/`): the
  cause, every blocking check's reason, measures and findings, its log's tail (`logs/<node>.log`). A free node
  that errors on a transient fault (HTTP 5xx, a timeout, a dropped connection: `graph.transient`) runs again up to
  `RETRIES` times, the waits doubling from `RETRY_WAIT`, before it stops its line; a paid node never runs again
  inside the batch, its failure is a gap (ADR-0005). Once a node stops its line,
  nothing later on that line starts (a node already running may finish). Runs side by side on one store (every
  agent's `score run`) make a node's key one at a time: a file lock per node and key (`locks/` beside the store; a
  dead holder lets go at once) makes a second run wait and then reuse the first's record, so nothing is paid twice;
  held past `LOCK_WAIT` the waiter is blocked, never made again. A record or judgement another run stored first is
  taken as made, never an error; a make that writes into its read-only input's checkout fails and stores nothing.
  One commit per store (`graph/runs.py`'s claims): `run` registers its commit, worktree, pid (with its start time) and the
  nodes it would make in `$PROPS_HOME/runs/active.json` under a lock, and is refused while a live run from another
  commit holds the store (named with its commit and worktree), or one at the same commit would make some of the same
  nodes (a node standing accepted is not made, so one run per place goes side by side once the world nodes stand); an
  entry whose pid is gone or now another process's is dropped. A worktree with tracked changes not committed is
  refused when the run would buy a paid row, unless given `--uncommitted`. A detached run registers itself: refused
  there, its result line is `detached: refused: ...`. Every `run` drives from its own frozen copy of the code
  (`graph/frozen.py`, #45): a git worktree under `$PROPS_HOME/frozen` at one commit (HEAD when clean, else one commit
  of the whole working tree; the run still registers as uncommitted), the running venv linked in as `.venv`, made
  as it starts (the command starts itself again inside it) and removed once it ends, after the machines it parked
  are gone (`park.outlive`); a pull or push in the checkout it came from never reaches it. Never point a run at a
  checkout to "pick up" a fix mid-run: start a new run.
- **`python -m score resume [--dry]`** starts again, each from its own worktree and detached, every `score run` in
  the run registry (`graph/runs.py`, `$PROPS_HOME/runs/<id>.json`) an earlier boot cut off (one the owner stopped is marked `stopped` and never resumed), one resume at a time, and clears an earlier boot's `.partial` files. It starts a run only at the commit that registered it with nothing uncommitted, and only one alive (its entry touched every minute while it drives) within 12 h before the boot; any other, or one whose restart fails, is marked `unresumable` with why and listed by `score status`; a
  detached run's log is under `$PROPS_HOME/logs`. `.claude/scripts/score-resume.service` runs it at boot once the
  owner installs it (needs systemd in WSL).
- **`graph/`** the runner: `Stage` (the stage table's row; a paid one names its estimate, `euros`; `applies`
  leaves out the places its environment data says it has nothing to do for; `upward`: its beside reads go up to the
  outside shell holding this place, an inside place's plan reading its outside shell's split, so the table's loop check leaves
  them out), `Environment` (`World` its old name, kept for the images stage, whose keyed module names it, until that stage is next made),
  `Runner.run/drive/status/lines/why/ticket/stale`. `run` accepts an output by itself when every gate passed
  (waivers counted), nothing got worse than the accepted output and the owner never rejected it, and makes a paid
  stage inside its clearance's ticket; `stale` (shown in status) names the earlier nodes whose accepted output moved
  since. A node's key hashes its computed code version (`_code.py`: its make's and checks' files and every repository module they
  import, inside functions and through `sys.path` folders too (read from the files, in the folders the path held at the process's first code version, so a folder a make adds later moves nothing); never the framework's own runner, review, clearance,
  stage table and renting code (`batch`, `capacity`, `park`, `blender_cloud`), `_code.FRAMEWORK`, so one line's edits there re-make no other line's nodes), parameters, seed,
  pinned models and every input, a declared folder's bytecode left out (`graph.source_hash`: each checkout writes its
  own __pycache__, #67; an accepted output whose key moved only by it is kept under the new key when its record is
  of a committed tree and the folder's sources at that commit, from git, hash as now: `Runner.kept_over_bytecode`,
  "same sources, bytecode left out of the key", the proof in its record; one whose key only got narrower, a module
  moved into FRAMEWORK unedited say, is kept too: `Runner.kept_by_narrowing`, its record's code version rebuilt
  from git at its commit and every file read today read as then, or a Python file of it reworded only (comments,
  blank lines, layout, docstrings unless something reads `__doc__`: `_code.words_only`, "same meaning", the files
  named in its record; type hints and names still count), a rewired stage, another Python or a dropped file edited
  or deleted made again). `python -m score moved` lists the paid rows a tree would buy again;
  `.githooks/pre-push-moved` refuses a push that moves one without a `Moved-rows:` reason (off until the owner
  sets `git config score.movedCheck true` and calls it from his pre-push). Before `run` starts, `rebuy.py` lists every paid row it would buy with its
  estimate (a Google ask google_spend's cache answers at EUR 0) and refuses, over EUR 5 of rows that already have an
  accepted output, unless given `--rebuy-reason "<why>"`, which goes into the run's log and the cloud ledger.
- **`review/`** the review page of one output from its own record (who accepted it, and how the owner rejects it);
  `accept_automatically` (the runner's; "worse than accepted" is `review.regressions`: a measure is worse only by its
  `TOLERANCES` step, the smallest change a viewer could see, one more for a count; a failing check still fails; his
  worse accept records each measure's `allowed` from and to, and a later passing output no worse than the output he
  took is accepted "within the owner's accept of <date> (<output>)", one beyond it waits for him); and the owner's `reject` (the accepted output moves back to the one accepted
  before, later nodes that read it go stale, the runner never takes it again), `accept` (his own, a worse one with his
  reason), `waive` (one check passes for one key, with his reason; it ends when the key changes and shows on the page
  and in status) `spend` (his override, a yes for a run outside the runner, node `override`) and `stop` (his money yes for an environment: it
  writes the environment's stop line itself, so no yes waits on someone to copy it into a guard). `python -m
  score.review ...` refuses those without a terminal, the store refuses their writes in an agent's process, and
  `.claude/hooks/accept_guard.py` blocks the other routes: a barrier, not a lock. `concepts.py` is the concept
  review's (CONTEXT.md): a place's concept draws, each one direct Nano Banana Pro call inside the owner's yes his cockpit
  click wrote (`web.concept_draw`), and his picks, kept in the store under `concepts/` (written only in the owner's process);
  `environment_concept.py` is the environment concept's (CONTEXT.md): its versions (style line, physics, references,
  places with what each may hold) and the set interview's asks, written only in the owner's process; environment 1's
  is today's data until he keeps one; the locked one is what every draw reads, and a draw or pick made under another
  version is out of date, and its places with what each may hold start within.json's proposal (`places_in_force`);
  each draw is copied to the private bucket as it is made (`concept-draws/<sha>.png` and `.json`; a failed copy is
  named in its record), and each pick or unlock is handed to score_lib through its own `score-lib concept` command.
  `reading.py` reads a picked concept into its scene inventory, started on its own by the pick (`web.reading_started`):
  Gemini 3.1 Pro's rows, each with its size in metres judged against the place's outline (`plans.outline_from_holder`:
  the layer above's box, its own plan, else round its inside places), then SAM 3's boxes of each row on one rented
  card (where, never size; its own words first, then its noun); only what both agree on is a row, its count SAM 3's
  instances (owner, 2026-10-21), the structure, ground and rows holding an inside place or standing in one kept as read, duplicates
  merged, the rest kept apart as `skipped` (never a row or a gap); a kept row with no metres or anchor its gaps; a
  reading by an older method is read again from its own rows, SAM 3 only; each
  reading and its cost kept under `inventory-readings/<place>/`; refused for a place with no pick of its own.
  `reading.row_boxes(store, place, row)` is the one read of a row's instance boxes in pixels of the picked concept.
  `plans.py` is the plan review's (CONTEXT.md): a place's plan made free from its pick, inventory and the layer
  above's plan, his edits and named inside places kept under `plans/` (his process only), a Correct with notes one
  direct Gemini call inside his click's yes (`web.plan_revise`), `made` and `holder_of` (the row and SAM box holding an
  inside place) for `concepts.step_refusal`, `shape_sent` an inside place's shape on it, `keep` the plans where the
  plan stage reads them (`stages.creator_plan`) and the plan row made again for those that changed; the plan shown is
  the newer of his edit and the plan made without him (`made_plan`: written, else the rough one laid from the
  inventory, its SAM boxes only ordering it). `plan_writing.py` writes a place's plan, measured off a drawing (owner, 2026-10-21):
  first `plan_drawing.py`'s top-down drawing (one Nano Banana Pro call redrawing the pick from directly above on its
  outline on the layer above's plan, kept under `plan-drawings/<place>/`, once per pick and outline), then one Gemini
  3.1 Pro call reading positions and footprints off it in its units, which part is which from the pick, the
  inventory's metres, the layer above's plan and its inside places (the stage table's schema plus outline, walls,
  openings, levels, stairs, roofs, terrain, shapes, section), turned into metres by the holder's box or the rows'
  metres, kept under `plan-writings/<place>/`, then `plan_checks.py`'s free checks (the arrangement against the
  concept's SAM boxes, left of, behind, what a tube joins, among them), each failure a plain gap with where it is; run on its own after a reading
  (`reading.planned`, `AUTOMATIC`: the owner's standing allowance, `compute.reading_clearance(node=PLAN_WRITING)`), else
  on his Make plan click as his spend yes (`web.plan_write`).
  `blockout.py` builds a place's blockout (CONTEXT.md "blockout", owner 2026-10-21) from its parent's plan: a top
  place's site on the environment's plan (each part with a plan of its own, else its own plan, at full detail: walls
  with thickness and openings, domes, vaults, tubes, levels, stairs, items by shape; on ground at its body's true
  curve), else its own room shell alone at full detail in its box on the holder's plan shown (no hull, no rooms
  beside it); rendered free (a numpy z-buffer at twice the size, a shadow map from the site's sun, no
  card, no Blender) from the fixed concept view, framed so the place fills it, a person for scale, and, when a world
  in its sky falls outside that view, a overhead view from the site at eye height. `scene_key` keys each render by what
  it is built from and the module's code, so the cockpit never serves an older code's render.
  `concepts.structure_pictures` sends both first with every first draw, the draw record keeps the blockout's
  sha (`blockout`), and a draw without one that can be built now is out of date (`current_draw`); `without_blockout`
  names the picked places drawn before. `concepts.step_refusal` waits only for the place's outline on the layer
  above's plan (`outlined`: held by a row or by the holder's own walls). `setting.py` is an environment's setting
  (CONTEXT.md "setting", owner 2026-10-21), part of its environment concept: its bodies (a real one takes the cited
  reference table's values, `data/physics/bodies.json`; an invented one is given by its own: radius, mass and so
  gravity, orbit, spin, and its light when it shines: kelvin, lux at lux_at_km), its lights (a far source of light
  with no body, on its day path: a house's sun), its backdrops (too far to move: a dome round everything, the stars,
  or a skyline), its plots (flat ground with a gravity, no body) and each top place's site (latitude, longitude and
  height on a body, metres on a plot); no fixed sky (owner 2026-10-21); environment 1's starts from
  `data/physics/setting.json` (the Sun, Earth, Moon and Mars as bodies, the stars a backdrop).
  No branch names a world. `environment_plan.py` is the environment's plan (CONTEXT.md "environment plan"): a map a
  ground of the concept's setting, each top place's site where the setting puts it at true size (the ground's fall
  from its true radius; the game's ground plans read only for the layout of a site's parts in metres), written by the
  plan writer's call (`plan_writing.asked`, cleared like a plan writing), the fixed facts kept over the answer, the
  true distances and what each site sees overhead worked out (`settled`, again on every read); kept under
  `environment-plans/<world>/` (writings; his edits in his process only), each with the concept version it was made
  under, one under another out of date. `overhead.py` runs the setting to a moment at a site (`seen`): every other
  body's direction, true angular size and phase, every light (a shining body's by its distance, a far light's from its
  path), brightest first, and every backdrop; the data the engine runs live.
- **`adapters/`** `models` (pinned images and models from `tools/cloud/images`), `compute` (`clearance`: the runner's
  ticket for a node whose inputs passed and stand accepted, when the month's books are known and the stop line (or a
  benchmark grant) has room for its forecast with every open reservation (no month's ceiling: owner, 2026-10-20),
  cleared under one lock so two lines never both spend the last euros; kept
  in the store; then `tools/cloud/runtime/submit.write_job`; `require_cleared` at every rent point; the forecast a
  node is cleared at is its stage's measured runs, else its stage's measured per-unit high times the units its
  accepted output made (`unit_price`, `data/costs/per-unit.json` from `tools/costs/per_unit.py`), else that high
  times the units its forecast rule counts (`gaps/price.planned_units`, as the run's plan priced it), else its
  estimate; `run_price` (`score price`, the cockpit's): when its caller counted a node's units before the make by its
  stage's forecast rule (`forecast_price`, PER_UNIT's `forecast`; the gaps' price, whose node is made again with what
  the gap adds; `score plan` and `score price` through `planned_units`, so the plan's stop line rests on the same
  measured per unit prepare uses, #10) "per unit × forecast" first, else the same as the forecast (basis "measured
  runs", then "per unit × counted"; a per-unit price at `bill_share`, the provider's bill over the ledger, 1 for
  Google calls, as prepare's figure), and a node with none of these has no price: its estimate is kept apart as
  `guess_euros`, with `guess_from` (`Stage.euros_from`, the line of the row that names it), never shown as a price
  (owner, 2026-10-18); `guard.py`: the environment's stop line, the owner's
  money figure, refuses a paid job before it starts when its forecast with the environment's spend since its first line and
  every run in flight would pass it (one outbox line, free work goes on; in the framework's store an environment with no
  line is refused), and never stops a started job except a runaway past twice its forecast minutes;
  `grant_benchmark(answer, question, euros)`: the owner's yes in a Claude Code session to one benchmark batch of at
  most EUR 20 (his standing rule of 2026-10-20; benchmark only, both quoted, single use, 24 h, `grants/` in the store),
  written by the session that asked him and never by hand; a `score run` tagged `SCORE_BENCHMARK_GRANT=<grant id>` is
  cleared against the grant instead of the stop line, one run per grant, within its euros; `reading_clearance`: a
  scene inventory reading run (`review/reading.py`, node `inventory-read`) cleared under the owner's standing
  allowance of 2026-10-21, no yes and no stop line, the books asked, at most `READING_EUROS` a place, against a grant
  when tagged), `engines`
  (Blender: the blender image's job, or `tools/props/cloud/blender_cloud.run_elsewhere` after clearance). Wrapped, not rewritten.
  `vendored` (the table of every tool in `vendor/`: where it is called, or why it is left out; its test fails on a
  tool vendored and forgotten).
- **`library/`** the one reader of the creator's library files (score_lib's `entries/` and `index/`), checked against
  their schema version (ADR-0007, its overlay); nothing else in score parses them.
- **`stages/`** the stage table (`python -m score.stages status|run|why <place> ...`). Step 0 holds the worked
  example: `assembly` on environment 1's round-three stages as unverified seeds (placeholder and resting gates) and
  `complete`. `earth-kit` (paid) and `earth-seed` (free, `stages/earth_seed`, its overlay) make each kit-laid earth
  place's base stage again from git and the rows' outputs, and every row that read the lost round-three seed reads it
  (`stages.earth_seeded`). `terrain` (one environment node, free, the code fallback under its prop-pipeline adapter, `ground-join`) makes
  every ground from its plan in `data/ground/plan/`, gated on scale and slope; `ground-fit@<place>` (free) judges each
  seated place's stage on it: ground under objects, nothing floating, no hole, openings (its overlay). `surfaces` (step 1) is each place's own line of
  rows, the finish route to checked bake (its overlay; per-place data in
  `data/surfaces/`). `effects-layer` (experimental: the launch, airlock, garage, hangar, greenhouse, habitat, flat, camp and campgrounds) makes a place's effects layer from its record in
  `data/effects/`, gated on attached, footage, light and outside, and the assembly takes it; `effects-look` (paid) renders it
  before and after (its overlay). `neighbours` (experimental, `stages/assembly/neighbours.py`) stands each place's
  neighbours (its scene record's `places`) in its assembly, each read beside (`Stage.beside`, `Stage.neighbours`:
  another place's accepted output, versioned and waited on like `after`) as its own accepted assembly, gated on
  `neighbours` (every shown place stands, resolves and has children). `complete` is the completion gate on what
  the place holds: `tools/usd/complete.py`'s own checks (all but resting, the assembly's gate) on the place's
  neighbours output (else its assembly), reading its surfaces-check and likeness; one gate, two ways in
  (`stages/complete/complete_test.py` holds them equal). The library check (`stages/complete/library`, its overlay) is
  not one of its gates: a standalone check of the accepted assembly against the library, its findings the cockpit's
  problems. Nor is the visual check (`stages/complete/visual`, its overlay): it reads the films, made only once
  complete passes, and writes its findings, with their pictures, the same way. A ship place's assembly lays its made
  pieces on its kit-built base (`stages/assembly/ship_made.py`, in the table). `complete-boxes` (paid, the ship's
  places) measures the boxes no other row measures (code rows, rows taken from another place's take), so complete's
  box check has a verdict for each. The materials checks (`stages/complete/materials`, its overlay: texture detail
  near cameras, finish-border raggedness, kit bakes older than their bake code) are not gates either: standalone and
  free, their findings reach the cockpit as problems with their pictures. `surface-tiles` (paid, its overlay) bakes
  each library surface a place's room shell names as a repeating tile, and the assembly draws the shell with them.
  `settle` (experimental, paid, its overlay; only the places in `stages.SETTLED`) drops a place's loose objects
  on its made ground, snaps its held ones onto their holders and lays where each rests as a layer the assembly
  takes, gated on `rested` and `resting`. `props-inputs`, `closeup`, `pixal` and `likeness` (`stages/props`, its overlay)
  are the prop route first (owner, 2026-10-12): close-up, Pixal3D, the surface line, then the likeness gate; they
  apply only to a place with a hand-in: its approved design's (`{home}/design/props/<place>.json`, written by
  prepare from the takes it priced, `stages/complete/prepare/handin.py`; with it its surface data,
  `{home}/design/surfaces/<place>.json`, and rough-model reads its picked concept), else `data/props/<place>.json`
  (the ship rooms', the people's line). A place with neither has no rows: it waits on its design.
  `rough-model` (paid, `stages/rough_model`, its overlay) puts each place's concept through the prop pipeline whole,
  after its plan: one Pixal3D model, its rough model, never shipped. The shared loop (`stages/shapes_first`, its
  overlay, #41) is every model layer's one way to a model: rough model, `rough-align` (its registration to the plan,
  free), the parts split, close-up, Pixal3D, the finish route, likeness, then each layer adapter's after-steps. `cast`
  (experimental, its overlay) places each place's people from its picked design (`data/people/rows.json`,
  `stages/people_rows.py`, #26: each inventory people row a look of the shared people line, a crowd one far look)
  and measures them on the seed's geometry (counted, standing, clear, made);
  `characters-layer` (`stages/cast/layer.py`) lays each person of the accepted cast in its own look's accepted dressed
  body (`people-dress-<look>`), unknown while one is missing, and the assembly takes its layer. `motion-models` (experimental, `stages/motion/models`, its overlay) lays each place's
  rigid moving models (`data/motion/models/<place>.json`: the garage's rover) on what holds them up, gated on outline,
  parts present and resting, and the assembly takes its layer. `physics-layer` and `physics-trial` (experimental, `stages/physics`, its
  overlay) write a place's UsdPhysics and run a trial of it on Bullet, for a place with `data/physics/<place>.json`
  (the habitat). `motion` (experimental, places with a rigid record) writes a place's motion layer from its game
  motions and its rigid moves in `data/motion/rigid/`, gated on clear, speeds, loops, grounded, covered and the motion
  check (its overlay). These rows, settle, physics, the cast and people rows and the crops rows are the one motion
  layer (CONTEXT.md "motion"; `stages.MOTION_LAYER` names them by module).
  `light-layer`, `light-passes` (paid) and `light` (experimental, `stages/light`, its overlay) make each place's
  light layer: today's sky and lamps over the seed, one render with a light group a lamp, the lamps' strengths
  swept on it against the concept; the assembly takes the accepted layer (`assembly.LAYERS`). A
  stage reads without an earlier place stage that does not apply to its place
  (`Runner.reads`). Environment 1's record is `data/definitions/world.json`. The `images` environment (`stages/images`, its own table in `stages.TABLES`, no places) rebuilds and proves the job images: `image-pins-<kind>` free, `image-proof-<kind>` paid and cleared like any row, `python -m score images publish <kind>` writes an accepted proof into images.json.
  `library@<place>` and `library-world` (free, the table's last rows, `stages/library`, its overlay) hand every
  accepted output of the place's line and of the environment to the creator's library through its own command
  (`SCORE_LIB_*`, else the score_lib checkout beside score and the cloud's object store, its key from the secret store, in the command's environment only) and gate on the report it writes (`handover.json`): a place is
  complete when its library node stands accepted, the environment when every one does (`status` prints it).
  `library-clips` (paid, after `library@<place>`, `stages/library/clips`, its overlay) renders a preview clip of
  each item the handover made new, a place's spread over warm cards (7 a card) in cloud Blender with the films' renderer, and puts
  each into its entry through the library's own command (CONTEXT.md "preview clip").

Rules:

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json` that names the place, the prim or pattern, what it is, why it is not from the
  library, who allowed it and when. Every finish is a library surface (`data/library`, the ProcFunc recipes and
  palette tokens): never a picture's own texture, a model's baked-in colour, a default grey or anything else; a
  picture-made model keeps its geometry and gets its finish replaced. The library check
  (`score/stages/complete/library`) lists what does not trace; bible `architecture/components`.
- **Agents never walk a line by hand.** Start it with `python -m score run <world> [--place P] --detach`: it
  returns at once with its log's path, and the run goes on in a session of its own until every line is done or
  stopped, then writes one result line (`detached: ok|failed exit=N ...`) as the log's last line. Wait for that line
  with the Monitor tool (or end the turn and read the log's last line later), never a poll loop. Never start its
  steps one by one, never poll a cloud step. Step in only on a fault report (the result line says `exit=1` and
  `python -m score status` names it): read that file, put the cause right, run the line again.
- **Never write a reject, a waiver, a spend yes, a clearance or an accept by hand**, by any route, and never ask the
  owner to accept or to say yes to a spend: run the stages, and the runner accepts what passed and got no worse and
  clears what may spend. The runner and every stage read the accepted output only; a new output that failed, is
  unknown or got worse lands beside it and waits on its page for the owner.
- **Every stage names its output's contract** (`Stage.contract`) and, in `after`, the (schema, version) it was
  written for of each stage it reads. A schema change is a new version, never an edit of the old one.
- **An accepted gap moves a fault, never loosens a gate** (`stages/gaps.py`): an owner's dated decision in
  `data/checks/gaps/<place>.json` names the objects whose faults in one gate (`stages.GAP_GATES`: assembly's
  placeholders and resting, surfaces-check's stands level, the paint's colour against the close-up) go down the
  line, and complete's `accepted gaps` fails each
  by name with its measured faults; any other fault still stops the line. The wrappers live in the table and unwrap
  to each gate's own judge, so moving a verdict re-keys no paid row. Write one only on the owner's decision.
  A **batch gap** (`stages/batch_gaps.py`, CONTEXT.md "gap") moves the same way without a written decision: the
  owner's yes to the batch decided it. A paid step that sorts a take into a named failure (no close-up passed,
  Pixal3D brought no model back, no usable list or one off the library, a split fault, a bake job that failed, a
  recheck that did not pass) writes it into its output's `batch-gaps.json` with its check and faults; the finish
  route leaves the take out and carries the gap on, the likeness carries every gap of the line (with its hand-in rows)
  to complete, and the table moves only those objects' faults (`stages.BATCH_GATES`); complete's `accepted gaps` lists
  each with the batch run and output that decided it, and the cockpit shows it as a gap its step's node fixes
  (`complete/gaps/marks.batched`). A step that brings nothing back at all (a set-up fault) still stops its row.
- **A gate never passes on missing evidence.** A check that needs evidence names it (`Check.evidence`); a judge that
  cannot tell answers unknown. Unknown blocks like fail.
- **Method choices live in the stage's code or in accepted environment data**; a stage's parameters are its true inputs.
  Every file a stage or its checks read is a declared input (`Stage.files`), or its node will not rerun when it
  changes. Over-declare rather than miss one (assembly declares the whole inventory folder for this reason).
- **Old outputs come in as unverified seeds** (`origin.json` in the output, a banner on the page), judged by the
  stage's own gates before anyone may accept them. A seed's references to other places (`/<place>/Places`) do not
  resolve in the assembly's output, where each place is its own node; the neighbours stage points them at copies of
  the neighbours' accepted assemblies, and its gate fails one that still resolves to nothing.
- **No `/tmp`, no hand-named folders** for outputs: a stage writes into the folder the runner gives it, and the
  store keeps the result. Tests use their own store (`Store.in_folder`); the worked example's test keeps it under
  `$PROPS_HOME/store-tests` and removes it.
- Tests are plain scripts beside each module (`make tests` runs `score/**/*_test.py`), driving the public interface.
