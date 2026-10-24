# score/stages/rough_model/

The `rough-model` row (CONTEXT.md "rough model", shapes first, issue #15): a place's concept put through the prop
pipeline whole, one Pixal3D model in a cloud batch that gives its plan its proportions and shape; never shipped. One row
of the stage table, right after `plan` (the shell split, #16, comes after it): the shared loop's first row
(`../shapes_first`, #41), registered to the plan by `rough-align`. `__init__.py`'s docstring has the reads,
the output and the gates. Bible: `architecture/components`.

- **Every place with a plan, in any environment.** It applies where `plan` does (`scene_record.written`), outside
  shells and inside places alike; nothing in it names a place of environment 1.
- **The concept is the one the plan names, never chosen here** (its `concept.picture`, a declared file).
- **The existing cloud path, not a new one.** `_cloud.py` runs `tools/cloud/batch.py`'s own command (its plan,
  price, clearance at every rent point, ledger line and finish) with only its row check swapped for the approval half
  (the inventory approved; no style: Pixal3D is worded by nothing): a rough model is on no inventory row. `batch.py`
  is never edited for it: the `pixal` row declares that file, so an edit there moves a paid key.
- **Paid, priced only from measured runs.** No rough-model run is measured, so the runner prices it unknown; `EUROS`
  is its clearance estimate (four one-model Pixal3D batches, EUR 0.26 to 1.42) and is never shown as a price. Pixal's
  per-model unit is not carried over: it is measured over batches whose set-up many models share.
- **Measures, no made-up thresholds.** `made` measures the model's triangles and extent (its mesh frame, Pixal3D's
  own size: the contract claims no metres); no proportion threshold against the plan exists until one is measured on
  accepted rough models.
- **The finish runs on a rented machine, never on the PC** (2026-10-22 benchmark: the PC has no image-to-3dlab
  environment or Blender for it). The batch brings the raw take back unfinished (`--no-finish`); `_finish.py` runs
  `pixal.py --finish-only` inside Blender on a `blender_cloud.run_elsewhere` machine (a card by the minute first),
  with the lab's pinned Python built there, the raw take, its camera folder, `tools/props` and the lab's copy sent up
  at their own paths. A raw take already in WORK/pixal is only finished, never made again (the batch refuses to
  overwrite one); a finished one is only copied.
- Gaps: a place whose `rough-model@<place>` does not stand accepted has the route gap `place:rough-model` with that
  node (`score/stages/complete/gaps`: `fill.py`, `route.py`).
- Run: `python -m score run <world> --stage rough-model --detach` (it spends). Test: `rough_model_test.py` (a stand-in
  batch, no spend).
