# score/stages/sim_body/inside/tuning/

Level 1 of the fit (#70; CONTEXT.md "landmark set"; numpy and scipy, its test runs in any Python with both): ONE joint
optimisation, never rounds of pieces judged alone (owner, 2026-10-29: "its ONE SOLVER with multiple layers, they all
need eachother"). `layout` names the unknowns (each landmark's link, a joint-defining one only across its bone; its
log trust; the two global weights, the markers' goal and a group end's weight; a left and right landmark share theirs,
mirrored, `paired`), `applied` turns them into a landmark table and weights, `case_residuals` is one tuning case's
follow measures (bones outside SOMA's skin by region, turns on the FROZEN calibration table, joints at `JOINT_SHARE`),
`prior` pulls links to their anatomical starts, `sparsity` the Jacobian's pattern (own, parent and child groups; a
global everything), `solved` runs scipy's least_squares (trf, 2-point, bounded) with every evaluation checkpointed
(`checkpointed`, `resumed` from the best) and stops when `settled` (under 0.5 % over 3 iterations) or at its limit.
`rewritten` writes a result into `landmarks/_table.py`, `weight_rewritten` its global weights into their modules (MARKER_GOAL in `fit/_frames.py`, END_WEIGHT in `fit/__init__.py`).

- Judged only as the whole solver after level 1, against main, on the check bodies; never by the landmark distances
  the solver pulls on.
- The bone's long axis is the body's own y (`LONG_AXIS`, OpenSim's convention for MyoFullBody's long bones).
- The runner (levels 2 and 3 per evaluation on the tuning bodies, side by side) lives outside the repository with the
  #70 workflow.
