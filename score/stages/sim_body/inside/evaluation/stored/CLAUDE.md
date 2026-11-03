# score/stages/sim_body/inside/evaluation/stored/

Level 1's pieces in SCORE's store (#70; owner, 2026-11-03, after `measured`'s `rmtree(out)` wiped 501 seeds built on
a rented H100): every case's result at one point (a seed is the CPU result at level 1's start), every evaluation's
and every exact block, and every checkpoint line, kept once under the key of what made it, never overwritten and never
cleared; a run on any machine (this PC, a rented card, the conductor) finds what exists and makes only what is
missing. `__init__.py`'s docstring has the keys and the store layout; `evaluation.kept_run` is the one caller that
makes pieces.

- **One store, not a second**: score/store's public calls only (`put_tree`, `write_once`, `read`, `place_blob`,
  `read_file`), under `level1/` keys; outputs keep their blobs safe from kept.py's sweep. score/store is not edited
  here (it is in every row's key). SCORE_LEVEL1_STORE names a store folder of its own (a rented batch's slice, a
  test's), else `Store.default()` (PROPS_HOME's).
- **A key is what made the piece**: the worker's code (inside/ files it imports, docstrings out, plus `KEYED`
  constants; the runner `evaluation/__init__.py` and this package are `LEFT_OUT`: how a job runs, never what it makes),
  the case (its job.json with every named file as its bytes' hash), its body (level 2 solves a body from all its
  clips), the point (rows, weights, rest with the rig as bytes) and, on the card, the body's seeds' bytes. What it ran
  on is in the mark, never the key. Never key by a path: the same seed on another machine must be found.
- **Nothing is deleted**: whatever stands where a piece is written is set `aside` into the store first; out folders
  are views of read-only links to the blobs. A second make of a key leaves the first standing.
- `python <this folder> import <seeds root> --src <src> --cases <cases.json> [--start <table.json>]` keeps a seeds
  root made before this, keyed by --src's code; `checkpoint <run dir> --src <src>` keeps a run's checkpoint lines.
- `exported` / `merged` move pieces between the PC's store and a rented batch's slice (tools/cloud/level1/cloud.py).
- Test: `test_a_level1_piece_is_made_once_kept_and_found_by_any_machine.py` (a toy worker, a store of its own).
