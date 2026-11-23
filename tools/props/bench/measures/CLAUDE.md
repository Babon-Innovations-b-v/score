# tools/props/bench/measures/

The prop benchmark's measures (#163, design on #162, PRD #159): one step's model of the prop route held to the
NVIDIA SimReady asset it was made from. `__init__.py` is the way in (its docstring has the interface and the input
dicts); the rest is private. Pure functions over plain arrays: the truth reader, the render and the runner live
elsewhere in the bench and hand in `{vertices, faces, face_material, box, mass, colliders, friction}` per side.

- **Strict by design** (owner, 2026-11-23: our checks are "not strict enough"). The made model is measured as its
  route laid it: no rescale ever hides a size error, the silhouettes are drawn by one camera framed on the truth (not
  compare.outline's boxed masks), and the turn that stands it on the truth is its up-axis error. A tie between axis
  turns (within `_align.TIE` of the best fit) takes the least-leaning one, so a symmetric shape is not charged for a
  turn that changes nothing.
- **Reuse, never copies.** The ring is tools/usd/compare.py's (YAWS, ELEVATION, FOV), the input view the close-up's
  (tools/props/closeup/check.py TURN_DEGREES, look_down), ownership split_compare.py's rule (OWN_PURITY,
  FINISH_LEAST, finishes_owned), the flat share and swell place_build/shapes', the least wall the model gate's,
  the finish bounds tools/props/library/likeness/measure.py's `passes`. Change those at their source.
- **BARS are #162's design bars** until the calibration pass (#163 step 3) confirms or resets each with its numbers;
  a bar is never loosened to pass. A measure whose input a step lacks (a raw model's parts, mass, colliders) is left
  out, never failed.
- **The Newton drop runs in the runner** (tools/usd/drop.py on the truth's and the made model's convex colliders;
  #155: a triangle-mesh collider crashes Newton); `rested` compares the two rests. Finish likeness needs each matched
  pair drawn by tools/props/library/likeness; `finish_likeness` judges those measures.
- Not measured yet: self-intersecting faces (no free exact test at a million faces); the route's own checks
  (straight.py, the model gate's pass, sausage and lump) run in the calibration pass, not here.
- Check: `test_a_made_model_passes_only_where_it_matches_its_truth.py`, one table of made models against one small
  box truth, each row the bar a known fault must break or a known-small error must keep.
