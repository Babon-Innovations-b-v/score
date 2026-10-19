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
  unmeasured, priced nowhere. Each entry also carries its `forecast` rule (`FORECASTS`: what a make's units are
  forecast from before it runs, a source in git; or none and `forecast_why`), which `score price --holes` counts;
  `--rules-only` writes the rules into the file in place, its measured numbers kept, as the old disk took the live
  ledgers (2026-10-19). Never edit the rules in the JSON by hand.
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
