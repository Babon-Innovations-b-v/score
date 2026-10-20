# score/stages/rough_model/

The `rough-model` row (CONTEXT.md "rough model", shapes first, issue #15): a place's concept put through the prop
pipeline whole, one Pixal3D model in a cloud batch that gives its plan its proportions and shape; never shipped. One row
of the stage table, right after `plan` (the shell split, #16, comes after it). `__init__.py`'s docstring has the reads,
the output and the gates. Bible: `architecture/components`.

- **Every place with a plan, in any environment.** It applies where `plan` does (`scene_record.written`), outside
  shells and inside places alike; nothing in it names a place of environment 1.
- **The concept is read, never chosen here.** A place a concept view is drawn for (`drawn_for`: a view's id names it)
  reads `concept-views` (that row's `applies` is `drawn_for`, so no other place waits on it or re-keys with it); any
  other reads the picture its plan names. A new view re-keys the rough model of every place a view is drawn for.
- **The existing cloud path, not a new one.** `_cloud.py` runs `tools/props/cloud/batch.py`'s own command (its plan,
  price, clearance at every rent point, ledger line and finish) with only its row check swapped for the approval half
  (the inventory approved, the place's style text written): a rough model is on no inventory row. `batch.py` is never
  edited for it: the `pixal` row declares that file, so an edit there moves a paid key.
- **Paid, priced only from measured runs.** No rough-model run is measured, so the runner prices it unknown; `EUROS`
  is its clearance estimate (four one-model Pixal3D batches, EUR 0.26 to 1.42) and is never shown as a price. Pixal's
  per-model unit is not carried over: it is measured over batches whose set-up many models share.
- **Measures, no made-up thresholds.** `made` measures the model's triangles and extent; no proportion threshold
  against the plan exists until one is measured on accepted rough models.
- Holes: a place whose `rough-model@<place>` does not stand accepted has the route hole `place:rough-model` with that
  node (`score/stages/complete/holes`: `fill.py`, `route.py`).
- Run: `python -m score run <world> --stage rough-model --detach` (it spends). Test: `rough_model_test.py` (a stand-in
  batch, no spend).
