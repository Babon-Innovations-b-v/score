# score/

The layered framework's core (PRD #6, the design of 2026-10-11): stages run by one runner, every output kept in one
store by its content's hash, gates that block on unknown, a review page per output, and accepts and paid runs the
runner gives by the gates' answers (the owner's answers of 2026-10-11: his picks are made, from concept and style on
everything runs automatically, no spend limit, spend logically). Today's tools in `tools/` move in here stage by
stage as each stage is built; nothing moves before.

- **`checks/`** the gate rules every stage shares: `Verdict` (pass, fail or unknown, a reason, measures, findings),
  `Check` (a judge and the evidence it needs), `judge` (missing evidence is unknown without asking), `overall`
  (fail, else unknown, else pass; nothing judged is unknown), `regressions` (what got worse than the accepted one).
- **`contracts/`** every output's schema, version and units, checked both ways: `Contract` (a schema, its version,
  the house units it uses, its faults check; other units than metres, seconds, degrees and Y up are refused),
  `stamp` (the runner checks an output and writes `contract.json` into it before storing; one off its contract is
  not stored), `expect` (a reader refuses an input of another schema or version, or with no stamp). The schemas in
  use: `OPENUSD_STAGE` (one root stage, metres, Y up, a default prim) and `PLACE_MANIFEST`.
- **`store/`** the store over `tools/cloud/runtime/store.py`'s interface (a folder at `$PROPS_HOME/store` by
  default; nothing in the cloud): outputs as content-hashed files and listings, finish records, judgements per
  evidence state, evidence per check and output, accepts (the runner's automatic ones and the owner's), the owner's
  rejects, waivers and spend yeses, the runner's clearances, the world's finish registry (append-only). Written
  once, never overwritten, and safe for lines side by side (each write lands whole through a `.partial` file of its
  own process; a write-once key is linked into place, so a second writer is refused); checkouts are read-only copies (never links to the stored bytes), made again
  when changed; an agent's process cannot write the framework
  store's owner areas (the runner's automatic accept excepted). Its docstring has the key layout.
- **`python -m score run <world> [--place P ...] [--stage S ...] [--jobs N] [--detach]`** and **`python -m score
  status [<world>]`** (`__main__.py`; `--stage` keeps only those stages and the nodes they read, place by place): the runner drives every line (the world's own nodes, then each place's) to its end with no agent
  in the loop (`Runner.drive`, `Runner.lines`), the lines side by side: each node in a forked process of its own, at
  most `--jobs` at once (default 8), so a line waiting on a cloud step holds up no other, and a world node every line
  reads is made once. It starts each node the moment the nodes it reads stand accepted,
  gathers a gate's missing evidence itself (`Stage.gatherers`; a paid one cleared like a paid stage, and only when
  nothing else blocks the output) and waits on every cloud step itself. A node that does not end accepted stops its
  own line only and leaves a plain fault report, `faults/<node>.txt` beside the store (`$PROPS_HOME/store/`): the
  cause, every blocking check's reason, measures and findings, its log's tail (`logs/<node>.log`). A node that
  errors on a transient fault (HTTP 5xx, a timeout, a dropped connection: `graph.transient`) runs again up to
  `RETRIES` times, the waits doubling from `RETRY_WAIT`, before it stops its line. Once a node stops its line,
  nothing later on that line starts (a node already running may finish). Runs side by side on one store (every
  agent's `score run`) make a node's key one at a time: a file lock per node and key (`locks/` beside the store; a
  dead holder lets go at once) makes a second run wait and then reuse the first's record, so nothing is paid twice;
  held past `LOCK_WAIT` the waiter is blocked, never made again. A record or judgement another run stored first is
  taken as made, never an error; a make that writes into its read-only input's checkout fails and stores nothing.
- **`graph/`** the runner: `Stage` (the stage table's row; a paid one names its estimate, `euros`; `applies`
  leaves out the places its world data says it has nothing to do for), `World`,
  `Runner.run/drive/status/lines/why/ticket/stale`. `run` accepts an output by itself when every gate passed
  (waivers counted), nothing got worse than the accepted output and the owner never rejected it, and makes a paid
  stage inside its clearance's ticket; `stale` (shown in status) names the earlier nodes whose accepted output moved
  since. A node's key hashes its computed code version (`_code.py`: its make's and checks' files and every repository module they
  import, inside functions and through `sys.path` folders too (read from the files, in the folders the path held at the process's first code version, so a folder a make adds later moves nothing); never the framework's own runner, review, clearance,
  stage table and renting code (`batch`, `capacity`, `park`, `blender_cloud`), `_code.FRAMEWORK`, so one line's edits there re-make no other line's nodes), parameters, seed,
  pinned models and every input, a declared folder's bytecode left out (`graph.source_hash`: each checkout writes its
  own __pycache__, #67; an accepted output whose key moved only by it is kept under the new key when its record is
  of a committed tree and the folder's sources at that commit, from git, hash as now: `Runner.kept_over_bytecode`,
  "same sources, bytecode left out of the key", the proof in its record). Before `run` starts, `rebuy.py` lists every paid row it would buy with its
  estimate (a Google ask google_spend's cache answers at EUR 0) and refuses, over EUR 5 of rows that already have an
  accepted output, unless given `--rebuy-reason "<why>"`, which goes into the run's log and the cloud ledger.
- **`review/`** the review page of one output from its own record (who accepted it, and how the owner rejects it);
  `accept_automatically` (the runner's; "worse than accepted" is `review.regressions`: a measure is worse only by its
  `TOLERANCES` step, the smallest change a viewer could see, one more for a count; a failing check still fails; his
  worse accept records each measure's `allowed` from and to, and a later passing output no worse than the output he
  took is accepted "within the owner's accept of <date> (<output>)", one beyond it waits for him); and the owner's `reject` (the accepted output moves back to the one accepted
  before, later nodes that read it go stale, the runner never takes it again), `accept` (his own, a worse one with his
  reason), `waive` (one check passes for one key, with his reason; it ends when the key changes and shows on the page
  and in status) `spend` (his override, a yes for a run outside the runner, node `override`) and `stop` (his money yes for a world: it
  writes the world's stop line itself, so no yes waits on someone to copy it into a guard). `python -m
  score.review ...` refuses those without a terminal, the store refuses their writes in an agent's process, and
  `.claude/hooks/accept_guard.py` blocks the other routes: a barrier, not a lock.
- **`adapters/`** `models` (pinned images and models from `tools/cloud/images`), `compute` (`clearance`: the runner's
  ticket for a node whose inputs passed and stand accepted, when the month's ceiling has room for the estimate over
  the ledger and every open reservation, cleared under one lock so two lines never both spend the last euros; kept
  in the store; then `tools/cloud/runtime/submit.write_job`; `require_cleared` at every rent point; the forecast a
  node is cleared at is its stage's measured runs, else its estimate; `guard.py`: the world's stop line, the owner's
  money figure, refuses a paid job before it starts when its forecast with the world's spend since its first line and
  every run in flight would pass it (one outbox line, free work goes on; in the framework's store a world with no
  line is refused), and never stops a started job except a runaway past twice its forecast minutes), `engines`
  (Blender: the blender image's job, or `tools/props/cloud/blender_cloud.run_elsewhere` after clearance). Wrapped, not rewritten.
  `vendored` (the table of every tool in `vendor/`: where it is called, or why it is left out; its test fails on a
  tool vendored and forgotten).
- **`stages/`** the stage table (`python -m score.stages status|run|why <place> ...`). Step 0 holds the worked
  example: `assembly` on world 1's round-three stages as unverified seeds (placeholder and resting gates) and
  `complete`. `terrain` (one world node, paid) makes every ground from its plan in `data/ground/plan/`, gated on
  scale, slope, ground under objects and openings (its overlay). `surfaces` (step 1) is each place's own line of
  rows, the finish-map method to checked bake (its overlay; per-place data in
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
  problems. A ship place's assembly lays its made
  pieces on its kit-built base (`stages/assembly/ship_made.py`, in the table). `complete-boxes` (paid, the ship's
  places) measures the boxes no other row measures (code rows, rows taken from another place's take), so complete's
  box check has a verdict for each. The materials checks (`stages/complete/materials`, its overlay: texture detail
  near cameras, finish-border raggedness, kit bakes older than their bake code) are not gates either: standalone and
  free, their findings reach the cockpit as problems with their pictures.
  `settle` (experimental, paid, its overlay; only the places in `stages.SETTLED`) drops a place's loose objects
  on its made ground, snaps its held ones onto their holders and lays where each rests as a layer the assembly
  takes, gated on `rested` and `resting`. `props-inputs`, `closeup`, `pixal` and `likeness` (`stages/props`, its overlay)
  are the prop route first (owner, 2026-10-12): close-up, Pixal3D, the surface line, then the likeness gate; they
  apply only to a place with `data/props/<place>.json`, which only the camp grounds have (their cairn). `cast`
  (experimental, its overlay) places each place's people from its cast record, read against `concept_people` (a
  world node of the table) and measured on the seed's geometry (counted, standing, clear, made, drapes);
  `characters-layer` (`stages/cast/layer.py`) lays each person of the accepted cast in its own look's accepted dressed
  body (`people-dress-<look>`), unknown while one is missing, and the assembly takes its layer. `machines-layer` (experimental, `stages/machines`, its overlay) lays each place's machines
  (`data/machines/<place>.json`: the garage's rover) on what holds them up, gated on outline, parts present and
  resting, and the assembly takes its layer. `physics-layer` and `physics-trial` (experimental, `stages/physics`, its
  overlay) write a place's UsdPhysics and run a trial of it on Bullet, for a place with `data/physics/<place>.json`
  (the habitat). `motion` (experimental, places with a movers record) writes a place's motion layer from its game
  motions and its movers in `data/movers/`, gated on clear, speeds, loops, grounded and covered (its overlay).
  `light-layer`, `light-passes` (paid) and `light` (experimental, `stages/light`, its overlay) make each place's
  light layer: today's sky and lamps over the seed, one render with a light group a lamp, the lamps' strengths
  swept on it against the concept; the assembly takes the accepted layer (`assembly.LAYERS`). A
  stage reads without an earlier place stage that does not apply to its place
  (`Runner.reads`). World 1's record is `data/definitions/world.json`. The `images` world (`stages/images`, its own table in `stages.TABLES`, no places) rebuilds and proves the job images: `image-pins-<kind>` free, `image-proof-<kind>` paid and cleared like any row, `python -m score images publish <kind>` writes an accepted proof into images.json.
  `library@<place>` and `library-world` (free, the table's last rows, `stages/library`, its overlay) hand every
  accepted output of the place's line and of the world to the creator's library through its own command
  (`SCORE_LIB_*`, else `$PROPS_HOME/library.env`) and gate on the report it writes (`handover.json`): a place is
  complete when its library node stands accepted, the world when every one does (`status` prints it).

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
- **A named gap moves a fault, never loosens a gate** (`stages/gaps.py`): an owner's dated decision in
  `data/checks/gaps/<place>.json` names the objects whose faults in one gate (`stages.GAP_GATES`: assembly's
  placeholders and resting, surfaces-check's stands level, the paint's colour against the close-up) go down the
  line, and complete's `named gaps` fails each
  by name with its measured faults; any other fault still stops the line. The wrappers live in the table and unwrap
  to each gate's own judge, so moving a verdict re-keys no paid row. Write one only on the owner's decision.
- **A gate never passes on missing evidence.** A check that needs evidence names it (`Check.evidence`); a judge that
  cannot tell answers unknown. Unknown blocks like fail.
- **Method choices live in the stage's code or in accepted world data**; a stage's parameters are its true inputs.
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
