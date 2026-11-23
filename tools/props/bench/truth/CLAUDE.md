# tools/props/bench/truth/

The benchmark's set and truth (#163 steps 1 and 2). The interface and the truth's data shape are `__init__.py`'s
docstring; callers import `from tools.props.bench import truth`, never `_pick` or `_read`.

- **The set is the rule's output, never hand-edited.** `python3 -m tools.props.bench.truth pick` runs #162's rule
  (`_pick.py`) on SCORE_LIB_ROOT and writes `data/checks/prop-bench-set.json` with the rule's words and the score_lib
  commit. A changed rule or kind table is a change to `_pick.KINDS` and a new pick, recorded on #163.
- **The truth is in the measures' frame** (`../measures`): metres, Z up as NVIDIA authors it (a stage not Z up is
  `Unread`), instances flattened (`Usd.TraverseInstanceProxies`), each payload's variant enabled alone in the session
  layer (never the cached file). Its `box`, `colliders` and `friction` are the keys the measures read. Only the entry's USD files are
  fetched (library_files, the library cache), not its maps.
- **Colliders as the simulator collides**: MuJoCo hulls every mesh geom whatever its approximation; Newton's
  `convexDecomposition` is cut by the simulator at load, so its payload holds only the mesh (`convex` False). A drop
  trial uses the MuJoCo colliders (#155: Newton crashes on a triangle mesh collider; 71 of the 83 author none).
- An approximation or collider type this reader does not know raises `Unread`, never a guess.
- Test: `test_the_truth_is_the_model_as_laid_and_the_set_is_the_rule.py`, a tiny library in tmp (SCORE_LIB_ROOT,
  SCORE_LIB_FILES), every answer worked by hand in its docstring.
