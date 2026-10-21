# score/stages/demo_turntable/

The demo-turntables row (experimental, 2026-10-14): models that already exist turned round for the paper's demos, one
environment node, paid and cleared by the runner like any paid row (one Blender job on the cheapest card through
`tools/props/cloud/blender_cloud.py`, drawn by the review page's `tools/blender/inside/review_models.py`).
`__init__.py`'s docstring has the record, the output and the gate.

- **What is turned is environment data** (`data/definitions/demo_turntables.json`): each object's models (the model file
  first, then its buffers and textures, all declared inputs) and the headings. A new model re-keys the node.
- **It shows, it accepts nothing into a place.** Its pictures feed the paper's demos only; no stage reads its output.
- **Never edit `tools/blender/inside/` for this row.** Crops and physics declare that whole folder, so an edit there
  moves their keys (2026-10-14: a margin edit to review_models.py did, and was put back). `turntable_models.py` runs
  review_models.py with its frame widened instead.
- **The gate measures, it does not judge looks.** `drawn` fails a model missing or blank at any heading.
- Run: `python -m score run world1 --stage demo-turntables --detach`. Test: `demo_turntable_test.py` (no Blender, no
  spend).
