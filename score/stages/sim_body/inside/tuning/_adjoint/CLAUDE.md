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
  `tuning.case_residuals` (gap 2); its reducers are in `__init__` (2026-10-30): `distance_rows` (per-frame |d| and
  d|d|), `median_row` (the middle frame as a fixed mask, the two middles' mean when even, as np.median), `rms_row`
  (mean(v dv) / rms, the skin's `depth_mm`), checked against differences on a toy. `case_rows` (2026-10-30) assembles one case's rows
  and derivative rows in `tuning.case_residuals`' order and scale (JOINT_SHARE, SCALES, sqrt(share / count), mm) from
  per-frame joint differences, turn errors and skin depths with their rows; equals central differences of
  `case_residuals` on a toy case. `_measures.py` (`TapedMeasures`, Newton's Python only, 2026-10-30) tapes the
  per-frame joint differences (TO_OWN @ the joint centre, a MIDDLE one the mean of its parts, minus SOMA's joint) and
  each group's turn degrees (`_turn_error`'s length, the frozen offset in the link frame) off a `TapedSites`' eval_fk,
  one backward pass per entry, as rows of the pose; on three copies of the toy chain, fed through `case_rows`, they
  equal central differences of `case_residuals` to 1 % of the largest entry. Skin depths (`skins=`, 2026-10-30): each
  region's bone points (link, local point) per frame against that frame's posed SOMA skin, `fit/_skin.marks_kernel`'s
  measure; the closest point and side found off the tape (`record_tape=False`: SOMA does not move with the pose), the
  distance to it taped, so a row is the unit normal's; checked the same way on a box skin per frame. The Newton runs are
  `_check_taped.py` and `_check_measures.py` (run by path from the test). Still to tape: rows over level 2's constants
  (only the pose's today). `_outer.py` (numpy, 2026-10-30): `site_unknowns` maps level 1's
  unknowns onto one frame's `TapedSites(trusted=True, ends=...)` outer unknowns (`tuning.applied`'s links and
  e^(LOG_UNIT*u) trusts and globals, each group end's centre move turned into its end site's link frame) and
  `site_derivative` is its derivative, the chain rule from taped rows to level 1's; checked against `applied`,
  `offsets` and central differences on a toy table. A batched body's copies (sites copy by copy, ends inside each
  copy) are not yet laid by it: `_weighed` takes the ends as the LAST k sites.
- Built and checked on a toy only (2026-10-30, five tests, 1.2 s); `../__init__.solved(exact=)` takes `stacked_jacobian` (its test, 2026-10-30). Not yet wired: the card gradient (Newton eval_fk on
  a wp.Tape for level 3, level 2's constants) as each `Body`'s callables, `solved`'s Jacobian switch to it, the gate on heavy_kimodo, tall_kimodo and
  a third tuning body against `_differences`, and the 70-case timing.
