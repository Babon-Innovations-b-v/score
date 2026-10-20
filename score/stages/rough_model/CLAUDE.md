# score/stages/rough_model/

The `rough-model` row (CONTEXT.md "rough model", shapes first, issue #15): a place's concept put through the prop
pipeline whole, one Pixal3D model in a cloud batch that gives its plan its proportions and shape; never shipped. One row
of the stage table, right after `plan` (the shell split, #16, comes after it). `__init__.py`'s docstring has the reads,
the output and the gates. Bible: `architecture/components`.

- **Every place with a plan, in any environment.** It applies where `plan` does (`scene_record.written`), outside
  shells and inside places alike; nothing in it names a place of environment 1.
- **The concept is the one the plan names, never chosen here** (its `concept.picture`, a declared file). The
  concept views are not read: no view's request says which place it is the concept of (the cockpit's are
  `cockpit_seat`, `cockpit_stick` and `ship46_cockpit`; `hangar_thrusters` is a close-up), so matching by id picks the
  wrong picture. Once a request names its place, the row reads `concept-views` there.
- **The existing cloud path, not a new one.** `_cloud.py` runs `tools/props/cloud/batch.py`'s own command (its plan,
  price, clearance at every rent point, ledger line and finish) with only its row check swapped for the approval half
  (the inventory approved, the place's style text written): a rough model is on no inventory row. `batch.py` is never
  edited for it: the `pixal` row declares that file, so an edit there moves a paid key.
- **Paid, priced only from measured runs.** No rough-model run is measured, so the runner prices it unknown; `EUROS`
  is its clearance estimate (four one-model Pixal3D batches, EUR 0.26 to 1.42) and is never shown as a price. Pixal's
  per-model unit is not carried over: it is measured over batches whose set-up many models share.
- **Measures, no made-up thresholds.** `made` measures the model's triangles and extent (its mesh frame, Pixal3D's
  own size: the contract claims no metres); no proportion threshold against the plan exists until one is measured on
  accepted rough models.
- **A take is never stuck.** One the cloud brought back raw whose finish failed is finished here with `pixal.py
  --finish-only`, as the batch finishes every take; the batch refuses to make a raw take again.
- Holes: a place whose `rough-model@<place>` does not stand accepted has the route hole `place:rough-model` with that
  node (`score/stages/complete/holes`: `fill.py`, `route.py`).
- Run: `python -m score run <world> --stage rough-model --detach` (it spends). Test: `rough_model_test.py` (a stand-in
  batch, no spend).
