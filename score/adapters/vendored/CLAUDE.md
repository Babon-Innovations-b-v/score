# score/adapters/vendored/

The table of every vendored tool in `vendor/` and where the framework calls it (`__init__.py`'s docstring has the
fields): wired (its callers, its cloud image, the stages it reaches), an agent tool, or left out with why.

- **A tool is never vendored and forgotten.** `vendored_test.py` fails on a `vendor/` folder with no row, a caller
  that is gone or never names its tool, an image kind with no folder in `tools/cloud/images` and a stage package that
  is not there. Add the row in the same commit as the tool.
- **Wire a new tool the house way**, before its row says wired: a cloud runner in `tools/props/cloud` with its image
  and pinned models (`tools/cloud/images/<kind>/models.json`, read by `score.adapters.models`), a stage-table entry
  only where a stage needs it (a new row or a new file in a paid row re-keys it: check `python -m score.stages.moved
  origin/main` shows 0 paid rows moved), a test with a stand-in, a rule in its caller's overlay. No model runs here.
- **Left out is a written reason**, never a silence: an owner's decision or what replaced it. Re-wiring a tool left
  out by the owner's decision is his call.
- Nothing imports this package at run time; it is the table and its check, so editing it re-keys no row.
