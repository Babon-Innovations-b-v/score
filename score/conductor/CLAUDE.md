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
- **Money**: the conductor bills in its own project (`SCORE_CONDUCTOR_PROJECT`, `score-conductor`); the stop line reads
  the batch project's bill alone, and `project_refusal` (in `compute.books_refusal`, `compute.require_books` and
  `guard.refusal`) refuses every clearance and rent point if the two names are ever the same.
- **`dry.py`**: `python -m score.conductor dry`, free, in a temp home under `SCORE_FREE_ONLY=1`, with a local
  stand-in for the size function: plan, waiting for size, resume at another boot id, the memory guard, health and
  logs, the shrink, the kill switch; one line, the detail in `$PROPS_HOME/logs/conductor-dry-<time>.json`. It never
  takes the agents' mark off: in an agent's process it checks the two refusals and walks the paths behind them.

Rules: nothing here rents, and nothing routes around `compute.require_cleared`, `books_refusal` or the stop line;
growing the machine is spend, so only a run the owner started (his Buy click's checkout) grows it. Tests:
`score/conductor/*_test.py`, each under 120 s in `make tests`' sandbox home.
