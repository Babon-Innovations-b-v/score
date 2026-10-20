# score/stages/complete/prepare/

Prepare a batch (CONTEXT.md "batch", #21): the free risk work before a paid batch, so it runs once and right, and
the one figure the creator says yes to. Today it prepares the environment's remake through the prop pipeline (#19).
`__init__.py`'s docstring has the modules and the record's shape. Bible: `architecture/components`.

- **Free, local, never a row.** Reads the scene inventories, the library's index (read only: score never imports the
  library), `data/costs/per-unit.json`, the cloud ledgers and the store; nothing in the stage table imports it, so no
  key moves. No Blender, no model, nothing judged or bought. `--stock` is the provider's free listing; `--moved` is
  `score moved`'s dry run (minutes).
- **Every job once.** The figure prices each take's layers one run each (`estimate.one_shot`: one Pro wording a row,
  one draw a map, no finish asked again); no retry share, no second take, no fallback class. A shell piece takes its
  library surface with no maps (`estimate.SHELL_ROUTE`). Card and processor layers carry the bill share
  (`holes/price.py` `BILL_SHARE`); Google calls do not.
- **A prediction comes from a measured failure mode, never a guess.** `predict.py` counts the hub's prop-route table
  against the hub's sizes every run: a shape every one of at least `MIN_MEASURED` measured rows failed is a predicted
  hole, not bought, and priced apart (`predicted_holes_if_bought`); fewer measured rows is `at risk`, still bought.
  The crop's upscale is said, never a prediction (no failure was measured against it).
- **Unmeasured stays unknown.** A layer with no per unit is unpriced and named; one with no measured minutes is
  untimed, and the ETA is then only `at_least_minutes` (`holes/schedule.py`).
- **One class and zone a layer** (`machines.py`): the runner's first class in its kind's order, the zone with the
  best boot record in the ledgers, in stock when `--stock` read it; no class in stock is the layer's jobs as holes.
- **Sharing a take across places is the owner's call** (a place's style may differ): `across_places` prices it
  beside the figure, never in it.
- **Quality is never a cost lever** (owner, 2026-10-20): never lower a setting that ships (Pixal3D's steps, held at
  the #55 lock in `tools/props/pixal.py`; film samples; resolutions), and never list a benchmark that would.
- **Benchmarks are listed, never launched here** (`benchmarks.py`, EUR 20 cap in all, counted on their highs): each
  through `score run --detach` once its track has landed, after `benchmarks.guard()` (the month's guard) has room.
- Run: `.venv/bin/python -m score.stages.complete.prepare [--library DIR] [--stock] [--moved]`, writes
  `WORK/checks/prepare/remake.json`. Test: `PROPS_HOME=$(mktemp -d) .venv/bin/python
  score/stages/complete/prepare/prepare_test.py`.
