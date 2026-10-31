# score/conductor/

The conductor's operations (owner, 2026-10-22): the one always-on Scaleway machine of our own that holds the store,
the design, the ledgers and the cockpit's home, and runs the runner, every free step, the sync, the listener and
resume. The machine itself (cloud-init, volumes, the size function, backups) is `tools/cloud/conductor/`; this package
is what the code does differently on it. A machine is a conductor when `$PROPS_HOME/machine.json` is there and
`SCORE_CONDUCTOR_SIZE_URL` is set; off one, every function here says so and the runner behaves as on the PC.

- **`size.py`**: two sizes of one machine (machine.json: `idle_type`/`idle_cores`, `batch_type`/`batch_cores`). A
  `score run` asking for more jobs than cores, at most the batch size's, outside an agent's process and without
  `--oversubscribe`, registers `waiting-for-size` (graph/runs.py) and waits up to `GROW_WAIT`; the size timer
  (`python -m score.conductor size`, `tools/cloud/conductor/units/score-size.*`, every 5 min, started at once by the
  waiting run) asks the size function to grow once no run is live and no free-only latch holds; `score resume` at the
  boot on the batch size starts the run. It shrinks after `IDLE_MINUTES` with no claim, no running or waiting run, no
  parked machine and no frozen copy a process uses. The ask: POST `{"action": "grow"|"shrink"}` to
  `SCORE_CONDUCTOR_SIZE_URL`, the token `score-conductor-size-token` in `X-Score-Size-Token` (the handler in
  `tools/cloud/conductor/size_function`), read by name through `SCORE_SECRET_READER` at the call. Before it asks,
  it writes `conductor/resizing.json`: a SIGTERM within `RESIZE_WINDOW` to a run registered before the ask is the
  resize's, so the run stays as it was for resume (`runs.stopped_by`); one registered after it is the owner's stop.
  The function itself refuses a shrink by its own health record (`health_push.py`).
- **`slices.py`** and **`bin/systemd-run`**: a detached run starts as its own scope in `score-runs.slice`, its cap the
  machine's memory less 6 GB set at each detach; inside the slice the shim adds `--slice-inherit` to a step's own
  `systemd-run --user --scope`, so its 14-16 GB scope stays under the cap. An OOM then ends a run, never the listener
  or the sync. The drive's own guard is `graph.memory_room` (a floor per node starting); `SCORE_MIN_FREE_GB` in the
  env file gives the conductor its own floor (the idle size has 16 GB).
- **`health.py`**: `$PROPS_HOME/health.json` for the Machine card (`python -m score.conductor health --write`, AREA 1's
  minute timer). Its `code` is the checkout's commit beside the cockpit's pin score-update last read
  (`conductor/pin.json`), red on the card when they differ. **`logs.py`**: `tails(limit_lines)`, newest run logs, fault reports and unit journals; a line naming
  or holding a secret, or showing a secret's own shape, is left out whole. A running entry counts as live only
  while its own process is (`size.entry_alive`: a reused pid is not the run).
- **`kill.py`**: `stop_all(asked_by, words)` and `allow_paid(asked_by, words)`, the cockpit's owner-only kill
  switch, and `stop_batch` (the run monitor's Stop this batch: the same stop, no latch), refused in an agent's process; the latch is `conductor/free-only` (`SCORE_FREE_ONLY=1`, an env file), read
  by every `score` command at its start (`conductor.apply_free_only`). It closes every open warm pool and ends its
  collector (`pool.close_all`) before it releases the parked machines, so no collector orders cards in their place.
  Then it ends every process still working in the frozen copy of a run no longer live (`frozen.users`/`frozen.end`,
  the report's `leftovers` with each command line; 2026-10-26: six processes of a stopped run held the checkout for an
  hour), and a stopped run ends its own copy's processes as it removes the copy (`frozen.remove_owned`).
- **`disk.py`** (2026-10-26: the data disk filled to 0.24 GB free and Batch 1 died with ENOSPC, the copies of the
  day's ended runs still on it): `FLOOR_GB` (10): `score run` is refused before it makes its copy while PROPS_HOME's
  disk has less free (`launch_refusal`), and health's `disk.floor_gb` and a note on the Machine card say it.
  `python -m score.conductor disk` (the door's `disk`) prints one summary line and the biggest folders, every folder in
  `conductor/disk.json`. `clean-frozen` (the door's, `score resume` at boot and every sync pass) removes each frozen
  copy and its home that no registered run needs (waiting, running and alive, or of an earlier boot resume may take; a
  live claim), no process works in (folder, `SCORE_FROZEN`, command line) and is over 15 minutes old, through
  `frozen.remove` (the checkout's `git worktree remove --force`, else deleted and pruned); it refuses everything while
  a run entry does not parse or a process's command line cannot be read. Never the store or the design: a home holds
  links only once closed, and only links are unlinked.
  `disk` also lists store/cache and work/pixal three levels down (2026-10-27: 37.5 and 20.5 GB). `clean-cache` (the
  door's; the sync pass runs it `--making-only`) removes, only with no run live (none `needed`, no process in a frozen
  copy or in a folder it clears, making/ untouched 15 min; else refused with why), the store cache's folders made
  again free (`CLEARED`: making, checkouts, evidence, pages, tmp*); it keeps paid drops, convex-parts (a paid drop's
  key hashes them), the review areas and anything unknown, and never touches store/objects or work/pixal (the paid
  Pixal3D takes the surface line reads as declared inputs, kept nowhere else). The runner removes each make's
  making/ folder however the make ends (`graph.gone`).
  `relink-pixal` (the door's, 2026-10-28: 16 GB free, work/pixal 20.5 GB), safe with a run live: each work/pixal
  file whose bytes the store holds as a blob (the store's sha256) and untouched for 15 min is made a hard link to that
  read-only blob, renamed over it; it removes nothing, so a take kept nowhere else stays whole. A take so linked is
  read-only: a re-finish that writes it in place is refused, never reaching the store.
  `clean-kept` (2026-10-29; the sync pass runs it), only with no run live (clean-cache's refusal): each kept job and
  per-take call (`tools/cloud/kept.py`, kept past its output so a re-keyed row makes only what changed) that no
  current key could ask for is dropped: its node gone from the table, its row code (`Runner.making_code`) moved, its
  system not this Python's or `blender_cloud.system`'s (worked out in a process of its own, so tools/cloud never
  joins the import path), or an input no longer current (a checkout of an output its node no longer reads, a file with
  other bytes). A node whose key is Blocked keeps its entries. Its blobs go only when no stored output and no other
  entry holds them. Never by age.
- **`library_checkout.py`** (`score-lib status | pull`, the door's, 2026-10-28): boot.sh clones score_lib once and
  nothing pulls it, while its handover, concept and the cockpit's lock push from it. Status fetches first; no push
  attempt is logged on score's side (each command's words go to its caller), so the newest push is the upstream
  ref's reflog line "update by push", and a failed push shows only as commits ahead; status also names origin's URL (no credential) and
  whether a dry push of HEAD is accepted (the deploy key's write right, nothing written). Pull fast-forwards only and is
  refused, listing them, on any local change or local commit.
  `offload-pixal` (the door's), only with no run live (clean-cache's refusal): each take a place's surface data paints,
  whole (raw and final models), untouched 15 min and not all store links, goes into score_lib as a `take` entry
  (`tools/library/pixal_takes.py`, `score-lib take-in --save`, the library's checkout pulled forward first) and its
  files leave work/pixal only once its entry is in the library's pushed history and the blob store hands every file
  back at its size and sha256. The stage table puts a freed take back (`graph.PLACE_READS`, `stages.takes_back`)
  before any row of its place works out its files, so no reader and no key changes.
  `disk` also accounts for the whole data disk (2026-10-30: 0.01 GB free of 91, about 25 GB in no folder under
  PROPS_HOME): folders from its mount point when the home is not its top, deleted files still held open (by process),
  blocks kept for root, what du cannot read or see. `store-gc [--dry]` (the door's), only with no run live: each blob no
  file, link or (followed) listing blob names is removed, `collectable_why` the one guard; a blob linked elsewhere or
  under a day old stays; refused when a file cannot be read. `sweep` (the door's; the sync pass's first step, so a
  refused pass still sweeps; owner 2026-10-30: "this should be routine"): every pass clean-frozen, clean-cache
  making/, clean-kept; on a conductor under `WARN_GB` (20) every step, clean-cache whole, relink-pixal, logs past 30
  days and tmp/ past a day, store-gc, offload-pixal, a line each with what it freed; still under the floor it names what
  fills the disk and prices the bigger volume (`conductor/sweep.json`, read by the Machine card's note): only then the
  owner. Never named blobs, paid caches (cloud/google-cache, drops), the design or a take kept nowhere else.
  Its own timer too (`score-sweep.timer`, every 10 min; 2026-10-31: at 0 GB free the update before each sync pass
  failed writing pin.json, so no pass and no sweep ran until a rescue boot by hand). One sweep and one offload-pixal at
  a time (`alone`, a lock under conductor/; a second is refused, said): the door's offload beside a pass's removed a
  take's files under the other's stat. A take with a file gone or a link to nothing is kept and named, never a crash.
- **Money**: the conductor bills in its own project (`SCORE_CONDUCTOR_PROJECT`, `score-conductor`); the stop line reads
  the batch project's bill alone, and `project_refusal` (in `compute.books_refusal`, `compute.require_books` and
  `guard.refusal`) refuses every clearance and rent point if the two names are ever the same.
- **`dry.py`**: `python -m score.conductor dry`, free, in a temp home under `SCORE_FREE_ONLY=1`, with a local
  stand-in for the size function: plan, waiting for size, resume at another boot id, the memory guard, health and
  logs, the shrink, the kill switch; one line, the detail in `$PROPS_HOME/logs/conductor-dry-<time>.json`. It never
  takes the agents' mark off: in an agent's process it checks the two refusals and walks the paths behind them.

Rules: nothing here rents, and nothing routes around `compute.require_cleared`, `books_refusal` or the stop line;
growing the machine is spend, so only a run the owner started (his Buy click's checkout) grows it. Tests:
`score/conductor/test_the_conductor_spends_and_stops_only_as_its_owner_says.py`, under 120 s in `make tests`' sandbox home.
