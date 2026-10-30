# score/stages/sim_body/inside/tuning/_adjoint/

Level 1's Jacobian by implicit differentiation at the inner optimum (#70, card plan step 6b). Numpy only in `__init__.py`, callables in:
the inner gradient g(z, theta) over z = (every frame's pose, then the body's constants) and the residual rows R(z, theta).

- dR/dtheta = R_theta - R_z H^-1 dg/dtheta. H is the FULL Hessian by central differences of g, never Gauss-Newton
  (the card study measured Gauss-Newton alone 22.4 % off, the full one 0.19 % from a re-solve).
- H is read block-arrow: one pose coordinate of every frame stepped together, then each constant alone
  (2 x (pose size + constants) gradients, not 2 x inner size); solved by the Schur step over the constants.
- An inner fit whose gradient exceeds the tolerance raises `Unconverged`: the caller reports that body, never uses it.
- `Body` is one tuning body's inner problem at its optimum; `stacked_jacobian` is level 1's whole Jacobian in
  `tuning`'s row order (every body's rows, then the prior's), every body checked first (`refused`) and each one stopped
  unconverged named in one `Unconverged`, never used.
- `_taped.py` (`TapedSites`, Newton's Python only, never imported by `__init__.py`): one frame's level 3 sites cost on
  the card, its pose gradient by Warp's tape through Newton's eval_fk, in `Body`'s callable shape (`gradient`,
  `residuals`, site offsets the outer unknowns). Toy chain (4 hinges, 3 weighted sites): equals central differences of
  its cost to 9.2e-5 of the largest entry (2026-10-30, float32). Turn rows (level 3's link-frame turns, the card's own
  `_turn_error` loaded by path) are in its cost and checked the same way (2026-10-30). MyoFullBody's couplings (`couplings=`:
  the pose is the free coordinates, each follower its rest plus polyval of its leader's move, as `fit/_card/_project.py`)
  are on the tape, checked the same way and against the uncoupled cost at the hand-expanded pose (2026-10-30). Level 2's
  constants (`constants=`: free sites' moves off their landmarks, inside joints' place moves in joint_X_p) are inner
  unknowns after the pose, their gradient off the offsets' and joint_X_p's tape grads, checked the same way on the toy
  (2026-10-30). A body batched per frame is one model holding a copy of the body per frame (one eval_fk and one
  launch for every frame): the pose is every copy's in turn, the sites every copy's, and level 2's constants given as
  rows (frames, count) of each copy's free sites and inside joints, every copy taking the same moves, their gradients
  summed; checked on two copies of the toy chain the same way (2026-10-30). `trusted=True`: each site's trust (level 1's landmark
  weight) is an outer unknown after the offsets, replacing `weights` at every evaluation; checked on the toy (same rows
  as fixed weights, doubled trust doubles its rows, pose gradient equals central differences) (2026-10-30). `ends=k`
  (with `trusted`): the last k sites are the group ends, their offsets the group-end centres' moves (left and right each
  its own site), and the outer unknowns after the offsets are the landmarks' trusts, "end weight", "marker goal": each
  site weighs sqrt(goal * trust / sum), an end's trust end weight times the landmarks' mean (`fit.fitting`); checked on
  the toy against hand-computed weights and a doubled goal (2026-10-30). The outer rows are still the sites', not
  `tuning.case_residuals` (gap 2).
- Built and checked on a toy only (2026-10-30, five tests, 1.2 s); `../__init__.solved(exact=)` takes `stacked_jacobian` (its test, 2026-10-30). Not yet wired: the card gradient (Newton eval_fk on
  a wp.Tape for level 3, level 2's constants) as each `Body`'s callables, `solved`'s Jacobian switch to it, the gate on heavy_kimodo, tall_kimodo and
  a third tuning body against `_differences`, and the 70-case timing.
