# score/stages/concept_view/

The concept-views row (experimental, 2026-10-14): a concept view drawn by Nano Banana Pro from a creator's reference
picture and a written request, one environment node, paid and cleared by the runner like any paid row. `__init__.py`'s
docstring has the record, the output and the gate.

- **Requests are environment data** (`data/definitions/concept_views.json`): each view's reference (a picture under the
  seeds folder), its wording, the shape it promises and why. A new view re-keys the node; the views already drawn
  come back from google_spend's cache at no cost.
- **The creator's pictures are inputs, not outputs.** A view is drawn from his reference; it is never his picture
  copied, and nothing is painted from it (paint is the library's).
- **The gate measures, it does not judge looks.** `drawn` holds each picture to its promised size and shape and fails a
  blank one; whether the drawing is right is the creator's call on his page.
- Run: `python -m score run world1 --stage concept-views --detach`. Test: `concept_view_test.py` (a stand-in Pro, no
  spend).
