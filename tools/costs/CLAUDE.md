# tools/costs/

The cloud's cost and time as the paper's cost tables give them (Appendix G), from the spend ledger and the provider's
bill. `costs.py` is the way in (its docstring has the commands); `costs_test.py` checks its sums on a ledger written
in the test.

- **`per_unit.py` writes the runner's per-unit prices** (`data/costs/per-unit.json`, owner 2026-10-18: prices only
  from measured per-unit numbers, at full cost): per paid stage in its `SPECS`, the unit, which ledger lines did that
  work (a batch kind and `who`, or a Google caller), likely the median and high the 90% quantile of each line's euros
  over its units, the lines it rests on, and the rule the runner counts a node's units by in its accepted output.
  Rerun it with every ledger that holds those lines (the local cloud ledger lost its rows of 10-12 to 10-17; the
  backup, the reconstruction and the paper's copy hold the rest) and commit the file; a stage with no lines stays
  unmeasured, priced nowhere (never a flat guess: owner, 2026-10-20). A stage whose ledger lines went with the old
  disk but whose runs' euros and units are written in git (`RECORDED`: an evidence file and line, or a commit) is
  priced from those runs, each named in `sources`; add a run there only from a figure written when it ran, with its
  units. Each entry also carries its `forecast` rule (`FORECASTS`: what a make's units are forecast from before it
  runs, a source in git, with `per_model` where a model makes more than one unit: recorded units over models, or a
  bound from the code said so, as the finish maps' `MAP_DRAWS` under #21 until runs under it are measured; a
  `price_note` where the measured price was asked otherwise than today, as the lists' standard tier), which
  `score price --gaps` counts; `--add --ledger <live ledger>` writes in place the stages that ledger holds lines
  of (a line whose ticket names its node is that stage's alone; sound, over the takes its line names (`SOUND_TAKES` for the two lines written before it named them); a WARM stage priced on its
  own timed jobs, kept so by every later mode), every other stage kept;
  `--rules-only` writes the rules and the RECORDED stages into the file in place, its ledger-measured numbers
  kept, as the old disk took the live ledgers (2026-10-19). Never edit the rules in the JSON by hand.
- **Each entry's `time` comes from the same lines as its euros** (#14): a unit's seconds (median and p90: the
  machines' own `unit_seconds`, else wall minutes over units), a fresh card's set-up (median and p90: its start
  wait and its working minutes before its jobs; `{why}` where no line timed one, never a 0), `slots` (jobs a machine
  ran at once) and the failed-start share; a Google stage's from its calls' started and finished times. `node_minutes` holds
  every stage's makes as the store's finish records time them (`--store`, `score/graph/runs.py` `node_times`). A stage
  with no timed lines keeps `time` null with its `why`, never a figure from elsewhere; a `RECORDED` stage may carry
  its run's own `time`, read from that run's ledger line (library-clips: its machine's `unit_seconds` over its clips). `--times-only` writes only
  these into the file, every euro byte-identical (`per_unit_test.py` checks it on the repository's own file); the
  runner turns them into a row's minutes (`compute.unit_minutes`) and a plan's ETA (`gaps/schedule.py`).
- **The remake is priced warm** (owner, 2026-10-20, #21): `WARM` stages (Pixal3D, the bake) at their jobs' measured
  work seconds on the type in the paper's ledger copy (no set-up, no idle) over `capacity.runs_at_once`, at the saved
  bill's price for the type by the minute, plus `OVERHEAD` (10%, the owner's target: replace it with the measured
  share once runs record time outside jobs); `BATCH` stages (the close-up, the finish route's list and recheck) at
  `google_spend.TIER_PRICE["batch"]` of measured standard-tier calls. Each entry names its `basis` and sources; a
  stage with no timed job stays unpriced. Every mode writes them (`with_warm`), the other stages byte for byte.
- **The ledger is never rewritten.** What a row lacks (a kind, a machine type) is added beside it: the reconciliation
  file tags rows by batch, and an engine run's type is read from its price. A fix to the runners goes in
  `tools/props/cloud/`, not here.
- **The paper reads the public copies** in `paper/evidence/cloud/`: `scrub` writes the ledger's first rows with every
  local root replaced (`$PROPS`, `$MOTION`, `$HOME`, repository-relative), `reconcile` and `tables` read only those
  copies and the saved bill, so anyone reruns them from the repository. The bill file carries no account or project
  id; check a new one before copying it.
- **"Per stage" is per kind of batch.** The ledger names batches, not environments, places or the route's stages, so the
  tables group kinds of batch; an environment's or a place's cost comes from Appendix B's attribution by work folder.
- **R&D against production is a rule on the row**, kept in `RND_GROUPS`, `RND_KINDS` and `RND_WHO`: work on the
  framework (engine runs, images and proofs, method experiments, benchmarks and comparisons named in `who`) is R&D,
  the rest production. The route's own batches carry no mark when they were reruns while the method changed, so
  production is an upper bound.
- **`reconcile-day` is the alarm, `reconcile` the paper's.** `reconcile-day <day>` builds Scaleway's day from the
  reads `today` saves and exits 1 when a line the ledgers hold (machines; disks and addresses) is more than 5% of the
  ledgered bill off, naming the provider; storage and the rest are reported apart, never in the gap. A provider with
  no bill fails unless `--skip` names it (Google needs its day in a bill file: no bill reader yet), and so does one
  whose ledger file is missing ("no ledger at <path>", never read as an empty ledger). Nothing runs it on
  a schedule yet. Two known lines it alarms on that no ledger row holds yet: block snapshots (`/storage/block/snapshot`
  files under disks and addresses) and machines kept running for good (as dev1_m and play2_pico in the saved reads)
  count under machines; until they are ledgered or split out, its gap includes spend the owner already knows about.
  The default ledger (`~/.farm-factory-props/cloud/ledger.jsonl`) is not on every box, so any figure quoted from it
  names its `--ledger`. A gap means spend outside the ledgers, fixed in the client that made it (`paid_calls_test.py`
  lists the allowed ones), never by editing a row. The paper's commands (`reconcile`, `tables`, `types`) leave the
  order lines (`ledger.ORDER_LINES`: started, refused, cluster orders) out; they are not batches.
