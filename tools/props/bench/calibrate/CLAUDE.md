# tools/props/bench/calibrate/

The prop benchmark's calibration pass (#163 step 3, design on #162, PRD #159): free, no model made. Each NVIDIA truth
is measured against an exact copy of itself (its surface cut again unmoved: the known-good ceiling), a copy
decimated to half (how a sound shape meets the route's triangle cut) and the other assets of its kind laid at its size
(the wrong-object floor); the route's own checks (model gate, straight.py, shapes' sausage and lump, patchy) run on
the truth itself; each NVIDIA mass is read against the density of its volume. `__init__.py`'s docstring has the
interface; `python3 -m tools.props.bench.calibrate run` runs the set side by side (SCORE_LIB_ROOT a scratch checkout),
keeps its records and `spread.json` as one run-store object with its blobs in the store bucket, and empties its
scratch.

- **A check that fails a known-good copy judges wrongly** and is fixed at its source with a test both ways (#162);
  a bar is set strict from the spread: the known-good pass it with margin, the wrong objects' p95 fails it. Bars are
  never loosened to pass a made model.
- **Bars are set on the tune split**; the held-out split only confirms them (tools/props/bench/CLAUDE.md).
- **Records keep every measures result whole**, so `spread` judges them again at whatever measures.BARS stand.
- A twin (NVIDIA's same geometry in another colour, measures.twin) is no wrong object and is left out.
- Test: `test_a_known_good_copy_passes_and_a_wrong_object_fails.py`, a small box truth, every answer by hand.
