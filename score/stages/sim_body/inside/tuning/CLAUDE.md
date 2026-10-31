# score/stages/sim_body/inside/tuning/

Level 1 of the fit (#70; CONTEXT.md "landmark set"; numpy and scipy, its test runs in any Python with both): ONE joint
optimisation, never rounds of pieces judged alone (owner, 2026-10-29: "its ONE SOLVER with multiple layers, they all
need eachother"). `layout` names the unknowns (each landmark's link, a joint-defining one only across its bone; its
log trust; each group end's centre on MyoFullBody, `ended`: its offset in its body's frame, each end its own, left and
right apart (owner, 2026-10-29: "isn't this exactly what the solver will find", "bodies aren't perfectly symmetric"),
within `END_REACH`; the two global weights, the markers' goal and a group end's weight; a left and right landmark share
theirs, mirrored, `paired`), `offsets` the centres' moves, `applied` turns them into a landmark table and weights, `case_residuals` is one tuning case's
follow measures (bones' depth outside SOMA's skin by region, root mean square in mm: the share outside, the judged
measure, is a step that a sub-micron pose change flips, so its differences were noise (#70, 2026-10-30); turns on the FROZEN calibration table, joints at `JOINT_SHARE`; turns and joints tuned as their root mean square over frames, m.json's "per group rms deg" / "per joint rms mm", the reported median's middle frames swapping under a step in 23 of 36 measured cases (B4g, 2026-10-30)),
`prior` pulls links to their anatomical starts and centres to the model's own, `sparsity` the Jacobian's pattern (own, parent and child groups; a
global everything), `solved` runs scipy's least_squares (trf, bounded), its Jacobian by `_differences`: ABSOLUTE
steps of `STEP` (2 mm of a link or centre, 0.1 of a log weight) over the pattern's column groups, never scipy's
`diff_step`, which is relative to |x| and at the start (every unknown 0) stepped 1.5e-8 so nothing moved (2026-10-29), every group's nudged set handed over in ONE call (`_differences.nudged`, `jacobian(many, ...)`; `solved(many=)`, `whole(evaluate_many=)`, card build step 6a: one card batch for them all; 1 + G = 138 sets, G = 137 column groups on the real table's 263 unknowns and 54 rows a case, measured 2026-10-29), with every evaluation checkpointed
(`checkpointed`, `resumed` from the best) and stops when `settled` (under 0.5 % over 3 iterations) or at its limit. `solved(exact=)` takes a Jacobian in place of the differences (`_adjoint.stacked_jacobian`, card build step 6b; test: given one, the differences never run, 2026-10-30); `solved(exact=, by_differences=)` is the hybrid: those columns (level 1's centres, as decided) by differences grouped among themselves only (`_differences.chosen_groups`), the rest exact (`_differences.hybrid`; test: the chosen column differenced, the others exact, 2026-10-30); the differences stay the default and its check; the adjoint gate on heavy_kimodo, tall_kimodo and mean_kimodo passed on 2026-10-31 with a 4 STEP reference pair (`_adjoint/CLAUDE.md`), and level 1 runs the hybrid (`level1.py --card ... --exact`, the owner's go of 2026-10-31 16:2x).
`_paired` reports each step as per-case paired changes on the fixed case set against the noise floor (same point scored twice).
`rewritten` (in `_rewriting.py`, re-exported; moved out 2026-10-30 to keep `__init__.py` under 300 lines) writes a result into `landmarks/_table.py`, `weight_rewritten` its global weights into their modules (MARKER_GOAL in `fit/_frames.py`, END_WEIGHT in `fit/__init__.py`).

- Judged only as the whole solver after level 1, against main, on the check bodies; never by the landmark distances
  the solver pulls on.
- The bone's long axis is the body's own y (`LONG_AXIS`, OpenSim's convention for MyoFullBody's long bones).
- `whole` is level 1 entire: `solved` with each evaluation's residuals from the runner (`../evaluation`: levels 2 and
  3 on every tuning body, side by side) and the held-out check scored every few iterations and at the end.
