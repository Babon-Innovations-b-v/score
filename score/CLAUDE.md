# score/

The layered framework's core (PRD #6, the design of 2026-10-11): stages run by one runner, every output kept in one
store by its content's hash, gates that block on unknown, a review page per output, and accepts and paid runs the
runner gives by the gates' answers (the owner's answers of 2026-10-11: his locks are made, from concept and style on
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
  own process; a write-once key is linked into place, so a second writer is refused); `store/durable.py`, installed by the runner and `score.review` only so it is in no row's key, syncs every write to disk before and after it lands, so a reboot leaves it whole or absent, and moves an empty or unparsable object to `quarantine/` beside the store, read as absent, except in the owner areas: an unreadable accept, reject, waiver or spend yes stops the run and stays put (a trade-off kept on purpose: a cut runner's automatic accept then stops every run until it is fixed by hand, since reading it as absent could buy a paid row again); checkouts are hard links to the stored bytes (copies until 2026-10-27, when they grew the
  conductor's cache 16 GB in an hour beside a 22 GB store), made again when changed: a stored blob's inode is read-only
  (0444) and a writable one is copied, never linked, so a write through a checkout is refused and a save that
  replaces or adds a file changes the checkout's entries only (the make then fails, nothing stored); only a
  chmod of an input file before a write would reach the store, and no code here raises an input's mode (every
  `chmod`/`u+w` acts on a copy); `clean-cache` makes an earlier commit's copies links, safe with a run live; an agent's process cannot write the framework
  store's owner areas (the runner's automatic accept excepted). Its docstring has the key layout. `store/restore/`
  (its overlay) rebuilds a lost store by today's keys and gates with a runner that spends nothing (#13).
  `store/backup/` (its overlay) backs the home up with restic every 30 minutes on the store's machine and makes the
  one-time move of the store from the PC to the conductor, checked by manifest.
- **`python -m score run <world> [--place P ...] [--stage S ...] [--jobs N] [--detach]`** and **`python -m score
  status [<world>]`** (`__main__.py`; `--stage` keeps only those stages and the nodes they read, place by place, an environment stage named with `--place` kept with the place nodes it reads, so `--place people --stage people-look-<look>` is the people line and that look's body in one run (with `--object <look>-s1` the line narrowed to its take: the prop route, finish route, bake and likeness select); `--object <name>` (repeat it) narrows a stage that selects (`Stage.selects`) to those objects of its place, the names in its params as `objects`, so a filtered output has its own key, and `graph.selected()` gives them to its files function, so another object's files neither key nor block it; any other stage runs whole): the runner drives every line (the environment's own nodes, then each place's) to its end with no agent
  in the loop (`Runner.drive`, `Runner.lines`), the lines side by side: each node in a forked process of its own, at
  most `--jobs` at once (default 8; the cockpit's Buy launches 16, `checkout/pricing.DEFAULT_JOBS`; on this PC a node only waiting for a turn of the container, its claim marked by `local.take` in `this-pc.waiting/`, holds no job slot while it waits, at most `WAITERS_EXCUSED` such, and a stage with a node so waiting starts no other until it got its turn, then one a pass, so other stages' ready nodes take the slots: 2026-10-29, all 8 slots held by bake rows, 5 of them waiting on the container's 3 Blender turns, about 60 ready rows of other stages kept out, then the freed slots went to more waiting bake rows), so a line waiting on a cloud step holds up no other, and an environment node every line
  reads is made once. It starts a node only while this PC's available memory (`/proc/meminfo`), less what each running
  node is still expected to take (its stage's peak less what its process tree holds now, `/proc`; one that ended holds none) and
  less the new node's own stage peak, stays at `MEMORY_FLOOR` (6 GB; `SCORE_MIN_FREE_GB` names another) or above. A stage's peak is
  the most memory one of its nodes' process trees held, by proportional share (each process's `Pss` of
  `/proc/<pid>/smaps_rollup` summed over the tree, its RSS only where that file cannot be read: a node forked from the drive
  and its Blender and pool children share pages, which an RSS sum counted once per process, 15.8 GB kept for
  finish-route-views nodes holding 2.5 GB, 2026-10-28), read every `MEMORY_SAMPLE` seconds by the node itself and by the drive,
  whichever is more; the same measure is what a running node is taken to hold now. Kept per stage in `memory/peaks-made.json`
  beside the store and only ever raised (the RSS sums of `memory/peaks.json` and the readings of `memory/peaks-pss.json`, kept before the rule below, are no longer read); a stage never measured is given `MEMORY_FLOOR`, and a node that made nothing (its output found made) is kept only above that, so a quick one never lowers the default (2026-10-28: such nodes kept finish-route-views low and seven real ones started on 38.9 GB, the PC at 7 GB free)
  (2026-10-28: five finish-route-views nodes grew to 4.8-6.4 GB each minutes after their start, past the old one-minute reserve,
  and took this PC to 7 GB free). A node whose tree ran a container client (`CONTAINER_CLIENTS`: `blender_cloud.py`) held its real
  memory in the container, outside its tree, so its stage keeps no peak below the default; on this PC (`on_this_pc`) such a node, holding the container's one claim or waiting on it, reserves its own tree's kept peak (`client_peak`: the most one of its stage's nodes' trees held, kept at every reading while it runs, its share or its processes' VmHWM summed, whichever is more, else its stage peak or the floor) less what its tree holds now, from its start to its end (round 26, 2026-10-30: two settle nodes each grew to 12-13 GB in their own trees side by side), and the container is counted once, by what its running jobs may still grow to (`container_reserve`), never more than its cgroup's `memory.max` less its `anon` (`container_room`; unread, each keeps its stage's peak; 2026-10-28: three surfaces-bake nodes, one claim, were given 8 GB each and held about 121 ready nodes with 32 GB available): each job (`container_jobs`: a session under the container's sshd whose tree runs a script, its kind that script) its kind's take peak less what its tree holds now, never below 0, and each slot seen busy but idle now a whole take peak; the whole room until a job was ever seen. A kind's take peak is the p90 (`TAKE_RANK`) of its last `TAKES_KEPT` takes, each the most its tree's `VmHWM` summed to, kept with the most jobs seen at once in `memory/container-peaks.json`; a kind never measured is given `TAKE_PEAK` (8.5 GB, the container's own per slot assumption). The container's cgroup cap stays the hard limit for a tail take, the outside guard the backstop (2026-10-29: the cap's whole 16.5 GiB was reserved beside three takes holding 1.2 to 3.2 GB, 108 ready nodes waiting with 24.6 GB available). A ready node that does not fit waits
  and the ones after it that fit start, however long it has waited; each pass reads the waiting nodes in order, so the room a node's end leaves goes to the first one waiting (2026-10-28: one 6 GB node at the head held 122 small ready nodes, five of eight slots empty for 29 min; 2026-10-29: once it had waited ten turns it held every node behind it again). Otherwise it
  says so once and reads again every `MEMORY_POLL` seconds; each turn first reaps the nodes that ended (an ended process
  holds nothing) and concludes them inside that turn's one `still` pass with the waiting nodes (each key, and each plan by
  `plans.one_moment`, worked out once, the nodes it starts forked after it: Batch 1 of 2026-10-25 spent 12 min and then
  over an hour in one pass, its pool billing); what each waiting node reads is kept across turns (`kept`, `forget`) until a
  node of its place, one it reads or an environment node ends, and all of it again every `HEARTBEAT` seconds, and `score run`'s watchdog stops a drive whose last pass is `DRIVE_STALL_SECONDS` old (the PC has run out of memory before; local nodes measured 0.2-0.3 GB, 2026-10-22). Each node's process sets `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and
  `NUMBA_NUM_THREADS` to this PC's cores divided by `--jobs` (at least 1; a smaller value already set stands, an empty one counts as unset, and
  one that is not a whole number above 0 is refused before the run) before its make starts, inside its log (a failed cap
  shows in its fault report), so its children inherit them, and resizes the OpenBLAS pools the drive loaded before it forked; a
  lone node gets only that share too (3 cores at the default 8 on 24), so `--jobs 1` gives a lone heavy node every
  core; more jobs than cores is refused unless given `--oversubscribe`. It starts each node the moment the nodes it reads stand accepted,
  gathers a gate's missing evidence itself (`Stage.gatherers`; a paid one cleared like a paid stage, and only when
  nothing else blocks the output) and waits on every cloud step itself. A node that does not end accepted stops its
  own line only and leaves a plain fault report, `faults/<node>.txt` beside the store (`$PROPS_HOME/store/`): the
  cause (an earlier node that "has not run on its current inputs" with what moved its key since its last record),
  every blocking check's reason, measures and findings, its log's tail (`logs/<node>.log`). A free node
  that errors on a transient fault (HTTP 5xx, a timeout, a dropped connection: `graph.transient`) runs again up to
  `RETRIES` times, the waits doubling from `RETRY_WAIT`, before it stops its line; a paid node never runs again
  inside the batch, its failure is a gap (ADR-0005). Once a node stops its line,
  every node that reads it, directly or through another, is not run; a node on that line that reads nothing of it
  still runs (a node already running may finish). Runs side by side on one store (every
  agent's `score run`) make a node's key one at a time: a file lock per node and key (`locks/` beside the store; a
  dead holder lets go at once) makes a second run wait and then reuse the first's record, so nothing is paid twice;
  held past `LOCK_WAIT` the waiter is blocked, never made again. A record or judgement another run stored first is
  taken as made, never an error; a make that writes into its read-only input's checkout fails and stores nothing.
  One commit per store (`graph/runs.py`'s claims): `run` registers its commit, worktree, pid (with its start time) and the
  nodes it would make in `$PROPS_HOME/runs/active.json` under a lock, and is refused while a live run from another
  commit holds the store (named with its commit and worktree), or one at the same commit would make some of the same
  nodes (a node standing accepted is not made, so one run per place goes side by side once the world nodes stand); an
  entry whose pid is gone or now another process's is dropped. The claim lists the run's line nodes once, inside the one
  still pass in which it works out which it would make, and hands that list to the heartbeat's gauges. A worktree with tracked changes not committed is
  refused when the run would buy a paid row, unless given `--uncommitted`. A detached run registers itself: refused
  there, its result line is `detached: refused: ...`. Every `run` drives from its own frozen copy of the code
  (`graph/frozen.py`, #45): a git worktree under `$PROPS_HOME/frozen` at one commit (HEAD when clean, else one commit
  of the whole working tree; the run still registers as uncommitted), the running venv linked in as `.venv`, made
  as it starts (the command starts itself again inside it) and removed once it ends, after the machines it parked
  are gone (`park.outlive`), or kept for resume when a shutdown's SIGTERM leaves it `running`; one git cannot remove is
  deleted, and the copies a run never removed (a SIGKILL, a refused resume) go at boot and every sync pass
  (`score/conductor/disk.py` clean-frozen); a run is refused while PROPS_HOME's disk has under 10 GB free; a pull or
  push in the checkout it came from never reaches it. Never point a run at a
  checkout to "pick up" a fix mid-run: start a new run.
  `run --free` (every run under `SCORE_FREE_ONLY=1` by default: the agents' door, the kill latch) is a free-only run, said in its log's first line: every free node whose inputs stand runs for real, a
  paid node not standing accepted is `not run: paid, left for the Buy` (its line waits there, no fault report) and
  the nodes reading it wait on it; no warm pool, nothing cleared (`Runner.cleared` refuses), no re-buy check; it ends
  with the list of free rows that stand, failed (with causes) and paid rows left, `exit: ok, free-only, ...` unless a
  free row failed.
- **`python -m score resume [--dry]`** starts again, each from its own worktree and detached, every `score run` in
  the run registry (`graph/runs.py`, `$PROPS_HOME/runs/<id>.json`) an earlier boot cut off (one the owner stopped is marked `stopped` and never resumed), one resume at a time, and clears an earlier boot's `.partial` files. It starts a run only at the commit that registered it with nothing uncommitted, and only one alive (its entry touched every minute while it drives) within 12 h before the boot; any other, or one whose restart fails, is marked `unresumable` with why and listed by `score status`; a
  detached run's log is under `$PROPS_HOME/logs`. `tools/cloud/conductor/units/score-resume.service` runs it at boot
  (the conductor's boot installs it; on the PC the owner installs it, which needs systemd in WSL). It also starts a
  `waiting-for-size` run once the machine has its cores.
- **`conductor/`** (its overlay) the conductor's operations, on the always-on cloud machine that holds the store (off
  one, nothing changes): `--jobs` defaults to its cores; a run with more jobs than cores registers `waiting-for-size`
  and the size function grows the machine (`size.py`, score-size.timer, which shrinks it after 30 idle minutes); a
  detached run is its own scope in `score-runs.slice` (memory less 6 GB), the drive's memory floor per node
  `SCORE_MIN_FREE_GB` when set; `health.json`, the log tails and the owner's kill switch (`kill.stop_all`, its
  free-only latch read by every `score` command); `python -m score.conductor dry` is its free end-to-end check.
- **`graph/`** the runner: `Stage` (the stage table's row; a paid one names its estimate, `euros`; `applies`
  leaves out the places its environment data says it has nothing to do for; `upward`: its beside reads go up to the
  outside shell holding this place, an inside place's plan reading its outside shell's split, so the table's loop check leaves
  them out), `Environment` (`World` its old name, kept for the images stage, whose keyed module names it, until that stage is next made),
  `Runner.run/drive/status/lines/why/ticket/stale`. `run` accepts an output by itself when every gate passed
  (waivers counted), nothing got worse than the accepted output and the owner never rejected it, and makes a paid
  stage inside its clearance's ticket. A new output that fails its gates (fail, the owner's waivers counted; never
  unknown, never only its accepted gaps) is made once more, without asking, when that is free here (a free row with
  no paid gatherer, or any row on this PC's card, `on_this_pc()`; owner, 2026-10-28: "the goal was getting to the
  film"): `Runner.after_failure` notes it once in the store (`remakes/<node>/<key>.json`, the count, so never twice
  across runs and restarts), which gives the node's key a `remake` part with a fresh seed, attempt 2, its record
  saying "automatic free remake, attempt 2, after <checks>". A second failure, or a paid row off this PC, stops the
  line and goes on the owner's list, priced (its forecast, else its estimate). A row of cached model asks
  (`asks_cached`: its own files are or import `CACHED_ASKS`, the Google batch route or the claude-code adapter) is
  never remade, since a fresh seed asks the same question: its note says "same question, same answer: needs a source
  fix (prompt or inputs)", not on his list; it runs again only once its key moves (owner, 2026-10-28). So is a row
  that only checks what other rows made (`Stage.seeded` False, set by `UNSEEDED` in `score/stages/__init__.py`:
  likeness, surfaces-check, complete, ground-fit): its note says "a check of inputs: same inputs, same answer; needs a
  source fix upstream: <findings>" (likeness@airlock, 2026-10-29, was remade and listed twice for nothing). Each note (failed checks, reasons,
  measures, findings, what came next, attempt 2's outcome) is a line of `remakes/notes.jsonl` beside the store, an
  owner's one also of `remakes/owner-list.jsonl`, and the fault report names both attempts; the noted checks are
  where the cause gets fixed (a builder, a route, a check judging wrongly), the remake is no fix. One object's take
  is remade by his reject naming it (`decide-yes reject <node> --output <o> --takes <take,...>`, then `decide`;
  review.reject `takes`): a row that retakes (`Stage.retakes`: pixal) is keyed anew with a `retake` param {takes,
  attempt, after} while its key's output stands so rejected, and its make remakes those takes alone, the rest kept
  (pixal, wired in the table's `retaking`: the take's files set aside under `work/pixal/retaken/`, made again at its
  seed plus the attempt). No gate loosens,
  no accept the gates did not give, his rejects, waivers and accepts stay his; `stale` (shown in status) names the earlier nodes whose accepted output moved
  since. A node's key hashes its computed code version (`_code.py`: its make's and checks' files and every repository module they
  import, inside functions and through `sys.path` folders too (read from the files, in the folders the path held at the process's first code version, so a folder a make adds later moves nothing); never the framework's own runner, review, clearance,
  stage table and run machinery (code that only decides where and how a job runs: renting, the warm pool, spreading, provider and backends, ledgers, forecasts, money guards, the cockpit; files or whole folders in `_code.FRAMEWORK`, so one line's edits there re-make no other line's nodes; a maker, its scripts sent up and their images stay in), parameters, seed,
  pinned models and every input, a declared folder's bytecode left out (`graph.source_hash`: each checkout writes its
  own __pycache__, #67; an accepted output whose key moved only by it is kept under the new key when its record is
  of a committed tree and the folder's sources at that commit, from git, hash as now: `Runner.kept_over_bytecode`,
  "same sources, bytecode left out of the key", the proof in its record; one whose key only got narrower, a module
  moved into FRAMEWORK unedited say, is kept too: `Runner.kept_by_narrowing`, its record's code version rebuilt
  from git at its commit and every file read today read as then, or a Python file of it reworded only (comments,
  blank lines, layout, docstrings unless something reads `__doc__`: `_code.words_only`, "same meaning", the files
  named in its record; type hints and names still count), a rewired stage, another Python or a dropped file edited
  or deleted made again). `python -m score moved` lists the paid rows a tree would buy again;
  `.claude/hooks/local/pre-push-moved` refuses a push that moves one without a `Moved-rows:` reason (off until the owner
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
  `.claude/hooks/local/accept_guard.py` blocks the other routes: a barrier, not a lock. `concepts.py` is the concept
  review's (CONTEXT.md): a place's concept draws, each one direct Nano Banana Pro call inside the owner's yes his cockpit
  click wrote (`web.concept_draw`), and his locks, kept in the store under `concepts/` (written only in the owner's process);
  `discuss.py` his Discuss of a shown draw (CONTEXT.md "discussion"): one Gemini 3.1 Pro call inside his click's yes
  (`web.concept_discuss`) sent what a redraw would with the discussion so far, its measured cost kept with the answer
  under `concepts/<place>/discussions/`; `concepts.redrawn` sends the open discussion to the prompt rewrite;
  `environment_concept.py` is the environment concept's (CONTEXT.md): its versions (style line, physics, references,
  places with what each may hold) and the set interview's asks, written only in the owner's process; environment 1's
  is today's data until he keeps one; the locked one is what every draw reads, and a draw or lock made under another
  version is out of date, and its places with what each may hold start within.json's proposal (`places_in_force`);
  each draw is copied to the private bucket as it is made (`concept-draws/<sha>.png` and `.json`; a failed copy is
  named in its record), and each lock or unlock is handed to score_lib through its own `score-lib concept` command.
  `reading.py` reads a locked concept into its scene inventory, started on its own by the lock (`web.reading_started`):
  Gemini 3.1 Pro's rows, each with its size in metres judged against the place's outline (`plans.outline_from_holder`:
  the layer above's box, its own plan, else round its inside places), then SAM 3's boxes of each row on one rented
  card (where, never size; its own words first, then its noun); only what both agree on is a row, its count SAM 3's
  instances (owner, 2026-10-21), the structure, ground and rows holding an inside place or standing in one kept as read, duplicates
  merged, a single object Gemini counted once over `LARGE` of the picture that SAM 3 found under no word kept with
  Gemini's region as its box (`boxed_by` "gemini", the engine room's core), the rest kept apart as `skipped` (never a
  row or a gap); `--again` reads a place already read again from its own rows, SAM 3 only; a kept row with no metres or anchor its gaps; a
  reading by an older method is read again from its own rows, SAM 3 only; a kept reading holding a row both readers
  put inside another row's thing (camp's "door" that is its fridge's glass door) has it merged into that thing by
  `reading_fixes.py` (free, a new reading; the sync pass runs it before parts, light and plans: not in reading.py,
  which is in the code version of 74 paid rows); each
  reading and its cost kept under `inventory-readings/<place>/`; refused for a place with no lock of its own.
  `reading.row_boxes(store, place, row)` is the one read of a row's instance boxes in pixels of the locked concept.
  `plans.py` is the plan review's (CONTEXT.md): a place's plan made free from its lock, inventory and the layer
  above's plan, his edits and named inside places kept under `plans/` (his process only), a Correct with notes one
  direct Gemini call inside his click's yes (`web.plan_revise`), `made` and `holder_of` (the row and SAM box holding an
  inside place) for `concepts.step_refusal`, `shape_sent` an inside place's shape on it, `keep` the plans where the
  plan stage reads them (`stages.creator_plan`) and the plan row made again for those that changed; the plan shown is
  his edit, always (a plan written after it is named as a gap, never shown over it), else the plan made without him
  (`made_plan`: written, else the rough one laid from the inventory, its SAM boxes only ordering it), each locked
  inside scene kept in the room its locked draw was drawn on (`locked_rooms_kept`): only his edit moves a locked
  scene's room (owner, 2026-10-21). `plan_writing.py` writes a place's plan, measured off a drawing (owner, 2026-10-21):
  first `plan_drawing.py`'s top-down drawing (one Nano Banana Pro call redrawing the locked concept from directly above on its
  outline on the layer above's plan, kept under `plan-drawings/<place>/`, once per lock and outline), then one Gemini
  3.1 Pro call reading positions and footprints off it in its units, which part is which from the locked concept, the
  inventory's metres, the layer above's plan and its inside places (the stage table's schema plus outline, walls,
  openings, levels, stairs, roofs, terrain, shapes, section), turned into metres by the holder's box or the rows'
  metres, kept under `plan-writings/<place>/`; a thing the creator already planned (`creator_plans.py`: the ship's
  floor plan, its hull outline and rooms, held by the hangar's row holding its rooms) is laid from his plan at its own
  size, its middle where drawn and its nose the way drawn, and the drawing is asked for it at that size in its box's
  frame; then `plan_checks.py`'s free checks (the arrangement against the
  concept's SAM boxes, left of, behind, place across the view, the way a thing faces, what a tube joins, among them; a
  run of crates one item with its `count`, only things drawn touching: a counted box far larger than its things side
  by side is a gap, `run_gaps`; a people row is never a thing: it stands on person spots, `plan["people"]` entries
  [x, y, facing, row], the cast's spots), each failure a plain gap with where it is, fixed before it is shown
  (`plan_fixes.py`, owner 2026-10-21: "gaps should only show things that cant be fixed auto"): the free fixes (people
  stood where their SAM boxes project, a box of things drawn apart split, the missing placed where their boxes
  project, facings turned the concept's way, overlaps parted inside the walls), then at most two automatic Corrects
  by the gaps left, each kept only when it leaves fewer, their cost kept with the writing; what is left says why; his
  edits and the rooms are never touched; `python -m score.review.plan_fixes <place> ...` fixes plans written before, and the sync pass's `plans keep` fixes again on its own every written plan never fixed or that today's free fixes place more of (`plans_pass.unsettled`), and parts the things the free fixes left in each other with IsaacLab-Arena's relation solver ported to numpy (`review/relation_solver`, its overlay: free, seeded, plan spots soft, walls and other things box obstacles, kept only when the checks find fewer overlaps and nothing new; never on a plan whose plan row stands accepted, and a free part made before the keep so the plan row is made once from it);
  run on its own after a reading
  (`reading.planned`, `AUTOMATIC`: the owner's standing allowance, `compute.reading_clearance(node=PLAN_WRITING)`), else
  on his Make plan click as his spend yes (`web.plan_write`).
  No grey model is built before a concept (the blockout, retired by the owner 2026-10-23: a scene's rough
  shapes are its rough model); `plan_drawing.from_south_east` reads the old locks' `blockout` field for their view.
  `concepts.step_refusal` waits only for the place's outline on the layer
  above's plan (`outlined`: held by a row or by the holder's own walls). `setting.py` is an environment's setting
  (CONTEXT.md "setting", owner 2026-10-21), part of its environment concept: its bodies (a real one takes the cited
  reference table's values, `data/physics/bodies.json`; an invented one is given by its own: radius, mass and so
  gravity, orbit, spin, and its light when it shines: kelvin, lux at lux_at_km), its lights (a far source of light
  with no body, on its day path: a house's sun), its backdrops (too far to move: a dome round everything, the stars,
  or a skyline), its plots (flat ground with a gravity, no body) and each top place's site (latitude, longitude and
  height on a body, metres on a plot); no fixed sky (owner 2026-10-21); environment 1's starts from
  `data/physics/setting.json` (the Sun, Earth, Moon and Mars as bodies, the stars a backdrop).
  No branch names a world. `environment_plan.py` is the environment's plan (CONTEXT.md "environment plan"): a map a
  ground of the concept's setting, each top place's site where the setting puts it (the ground's fall from its true
  radius), its footprint, size and blocks its top scene's own plan (`plans.current`, read again on every settle,
  `from_plan`: never written or edited apart, owner 2026-10-23), its scene times and terrain spots written by the
  plan writer's call (`plan_writing.asked`, cleared like a plan writing), the fixed facts kept over the answer, the
  true distances, sites that would overlap parted (`cleared`: the smaller out along its bearing to `CLEAR_M` apart;
  one the creator placed himself never moves, two of his overlapping a gap) and what each site sees overhead worked out (`settled`, again on every
  read); kept under
  `environment-plans/<world>/` (writings; his edits in his process only), each with the concept version it was made
  under, one under another out of date. `overhead.py` runs the setting to a moment at a site (`seen`): every other
  body's direction, true angular size and phase, every light (a shining body's by its distance, a far light's from its
  path), brightest first, and every backdrop; the data the engine runs live. `scene_sky.py` keeps each scene's sky
  inputs where its light layer reads them (`{home}/design/sky/<scene>.json`: the physics, and the site and scene time
  of the top scene it stands in), on `python -m score.review.plans keep`.
- **`adapters/`** `models` (pinned images and models from `tools/cloud/images`; `claude_code.py`, a Gemini-shaped ask answered by a headless `claude -p` on the owner's subscription, pinned to claude-opus-5-5, cached and ledgered at EUR 0; the finish route's palette, library, list and recheck ask through it since 2026-10-27, env1 running on the owner's PC (`tools/cloud/this_pc.py`), and on a machine without Claude Code, the conductor, they stop with "runs on this PC", never asking Gemini instead), `compute` (`clearance`: the runner's
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
  `grant_benchmark(answer, question, euros)`: the owner's yes in a Claude Code session to benchmark batches of at
  most EUR 20 in all (his standing rule of 2026-10-20; benchmark only, both quoted, 24 h, `grants/` in the store),
  written by the session that asked him and never by hand; a `score run` tagged `SCORE_BENCHMARK_GRANT=<grant id>` is
  cleared against the grant's balance instead of the stop line (owner, 2026-10-22): each clearance holds its high
  plus 10% (`grants/holds/`) and, when its run ends, finished or failed, draws what it really spent from it
  (`grants/draws/`, the balance after each), so runs share one grant until its balance or its 24 h run out;
  `restore_grant` applies that yes to a grant used up under the old single-use rule; `reading_clearance`: a
  scene inventory reading run (`review/reading.py`, node `inventory-read`) cleared under the owner's standing
  allowance of 2026-10-21, no yes and no stop line, the books asked, at most `READING_EUROS` a place, against a grant
  when tagged), `engines`
  (Blender: the blender image's job, or `tools/cloud/blender_cloud.run_elsewhere` after clearance). Wrapped, not rewritten.
  `vendored` (the table of every tool in `vendor/`: where it is called, or why it is left out; its test fails on a
  tool vendored and forgotten).
- **`library/`** the one reader of the creator's library files (score_lib's `entries/` and `index/`), checked against
  their schema version (ADR-0007, its overlay); nothing else in score parses them.
- **`stages/`** the stage table (`python -m score.stages status|run|why <place> ...`). Step 0 holds the worked
  example: `assembly` on environment 1's round-three stages as unverified seeds (placeholder and resting gates) and
  `complete`. `earth-seed` (free, `stages/earth_seed`, its overlay) makes every designed scene's base stage from its
  design and the rows' outputs (`design_shell.py`: a room whose kit holds its walls gets its deck, walls and roof, an
  open place its raised levels, each painted from the scene's surface library; every other shell and every stair is
  the scene record's, from the same plan), the ship's rooms and a scene added in the app too; every row that read the
  lost round-three or ship seed, or an old kit (data/kit, retired with the old concepts on 2026-10-21, and earth-kit,
  kit-sections and the ship kits with it), reads it (`stages.earth_seeded`: the seed's stage folder, the design's kit
  `kit.json`). `terrain` (one environment node, free, the code fallback under its prop-pipeline adapter, `ground-join`) makes
  every ground from the design (a body or plot of the setting, each top scene at its site and what its plan holds,
  the plans' terrain spots), gated on spots and curve; `ground-fit@<place>` (free) judges each place standing on it:
  ground level under objects, nothing floating, no hole, openings (its overlay). `surfaces` (step 1) is each place's own line of
  rows, the finish route to checked bake (its overlay; per-place data its design's, `{home}/design/surfaces/`, the people line's in
  `data/surfaces/`). Which layer rows a place has (people, crops, effects, motion, physics, light, sound) is read off its design alone, `stages/design_layers.py` (its locked concept's scene inventory, each row's
  row kind): the table's `designed(kind)` and the assembly's layers gate (`assembly.needed_layers`, reading the same
  kept inventory as its `design` input) give one answer, so the gate never waits on a layer the table has no row for
  and no row's places are a hand-written list. `effects-layer` (experimental: a place whose design shows a row that
  emits) makes its effects layer from its design (`stages/effects/from_design.py`: each object of an emitting row
  carries its kind's measured effects, `data/checks/effects.json`), gated on attached, footage, light, outside and
  designed, and the assembly takes it (its overlay; the paid `effects-look`, the old launch's stills, was retired
  2026-10-21). `neighbours` (experimental, `stages/assembly/neighbours.py`) stands each place's
  neighbours (its scene record's `places`) in its assembly, each read beside (`Stage.beside`, `Stage.neighbours`:
  another place's accepted output, versioned and waited on like `after`) as its own accepted assembly, gated on
  `neighbours` (every shown place stands, resolves and has children). `scene-tree` (free, `stages/assembly/scene_tree.py`)
  is a scene's assembly with each child scene its plan lays out referenced at its hold from the child's own tree (read
  beside, `Stage.downward`: a child's tree before its parent's), gated on `child scenes`; a parent scene with no data of
  its own (the Moon base) is a place once its design is done, and `stages.places` lists each parent scene before its
  children; a scene merged into another and a part of another scene's outside (`data/places/within.json` `parts`,
  the launch) are no place of the build: no stage line, nothing waits on one, and the scene a part belongs to builds
  it, its inventory rows and plan area that scene's design (the owner, 2026-10-21, to "Shall Launch stop being a
  place the batch builds, so the Square's build covers it?": "yes"). `complete` is the completion gate on what
  the place holds: `tools/usd/complete.py`'s own checks (all but resting, the assembly's gate) on the place's
  neighbours output (else its assembly), reading its surfaces-check and likeness; one gate, two ways in
  (`stages/complete/test_the_completion_gate_passes_only_a_place_that_holds_what_it_should.py` holds them equal). The library check (`stages/complete/library`, its overlay) is
  not one of its gates: a standalone check of the accepted assembly against the library, its findings the cockpit's
  problems. Nor is the visual check (`stages/complete/visual`, its overlay): it reads the films, made only once
  complete passes, and writes its findings, with their pictures, the same way. Nor is the USD check
  (`stages/complete/usd`, its overlay): SCORE's curated usd-validation-nvidia rules on each place's composed stage,
  its errors the cockpit's problems, run by the sync pass. (The old ship kit's made pieces laid on
  its base, `ship_made.py`, and `complete-boxes`, which measured the old inventories' boxes, were retired with the old
  kits and inventories on 2026-10-21: a design's every box is its reading's.) The materials checks (`stages/complete/materials`, its overlay: texture detail
  near cameras, finish-border raggedness) are not gates either: standalone and
  free, their findings reach the cockpit as problems with their pictures. `surface-tiles` (paid, its overlay) bakes
  each library surface a place's room shell takes as a repeating tile, and the assembly draws the shell with them.
  `settle` (experimental, paid, its overlay; a place whose design shows a loose row) drops a place's loose objects
  on its made ground, snaps its held ones onto their holders and lays where each rests as a layer the assembly
  takes, gated on `rested` and `resting`. `props-inputs`, `closeup`, `pixal` and `likeness` (`stages/props`, its overlay)
  are the prop route first (owner, 2026-10-12): close-up, Pixal3D, the surface line, then the likeness gate; they
  apply only to a place with a hand-in: its approved design's (`{home}/design/props/<place>.json`, written by
  prepare from the takes it priced, `stages/complete/prepare/handin.py`; with it its surface data,
  `{home}/design/surfaces/<place>.json`, and rough-model reads its locked concept), else `data/props/<place>.json`
  (the people's line; the old hand-ins were retired, 2026-10-21). A place with neither has no rows: it waits on its design.
  `rough-model` (paid, `stages/rough_model`, its overlay) puts each place's concept through the prop pipeline whole,
  after its plan: one Pixal3D model, its rough model, never shipped. The shared loop (`stages/shapes_first`, its
  overlay, #41) is every model layer's one way to a model: rough model, `rough-align` (its registration to the plan,
  free), the parts split, close-up, Pixal3D, the finish route, likeness, then each layer adapter's after-steps. `cast`
  (experimental, its overlay; a place whose design shows a row that acts) places each place's people from its locked design (`data/people/rows.json`,
  `stages/people_rows.py`, #26: each inventory people row a look of the shared people line, a crowd one far look)
  and measures them on the seed's geometry (counted, standing, clear, made);
  `characters-layer` (`stages/cast/layer.py`) lays each person of the accepted cast in its own look's accepted dressed
  body (`people-dress-<look>`), unknown while one is missing, and the assembly takes its layer (a moving row's
  models are the prop pipeline's, laid by the assembly like any other: the `motion-models` rows, which laid a record
  per place, were retired 2026-10-21). `physics-layer` and `physics-trial` (experimental, `stages/physics`, its
  overlay) write a place's UsdPhysics and run a trial of it in Newton, for a place whose design shows a loose row,
  the trial made from its design (`stages/physics/design.py`: its loose objects dropped where they stand, its body's
  gravity). `motion` (experimental, a place whose design shows a row that moves) writes its motion layer
  from its design (`stages/motion/from_design.py`: each object of a moving row swings, spins or stands by its kind's
  rule), gated on clear, speeds, loops, grounded, covered, designed and the motion check (its overlay). The three
  take their work from one row-kind classification (`stages/row_kinds.py`, `data/checks/row-kinds.json`, CONTEXT.md
  "row kind"), never from a record written per scene. These rows, settle, physics, the cast and people rows and the crops rows are the one motion
  layer (CONTEXT.md "motion"; `stages.MOTION_LAYER` names them by module).
  `light-layer`, `light-passes` (paid) and `light` (experimental, `stages/light`, its overlay) make each place's
  light layer: today's lamps over the seed and its sky from the environment concept's physics overhead at its site
  (`sky.py`, gated on `sky bodies`), one render with a light group a lamp, the lamps' strengths
  swept on it against the concept; the assembly takes the accepted layer (`assembly.LAYERS`). A
  stage reads without an earlier place stage that does not apply to its place
  (`Runner.reads`). Environment 1's record is `data/definitions/world.json`. The `images` environment (`stages/images`, its own table in `stages.TABLES`, no places) rebuilds and proves the job images: `image-pins-<kind>` free, `image-proof-<kind>` paid and cleared like any row, `python -m score images publish <kind>` writes an accepted proof into images.json.
  `library@<place>` and `library-world` (free, the table's last rows, `stages/library`, its overlay) hand every
  accepted output of the place's line and of the environment to the creator's library through its own command
  (`SCORE_LIB_*`, else the score_lib checkout beside score and the cloud's object store, its key from the secret store, in the command's environment only) and gate on the report it writes (`handover.json`): a place is
  complete when its library node stands accepted, the environment when every one does (`status` prints it). No row
  renders a library item: the cockpit shows each live and free (CONTEXT.md "item preview"; `library-clips` retired,
  owner 2026-10-22).

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
  clears what may spend. The runner and every stage read the accepted output only; a new output that failed (after its
  one free remake, `graph/`), is
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
- Tests sit beside each module, one file a module named for its invariant (`make tests` runs `score/**/test_*.py` and the older `score/**/*_test.py`), driving the public interface.
