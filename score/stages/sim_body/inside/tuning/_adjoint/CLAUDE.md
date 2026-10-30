# score/stages/sim_body/inside/tuning/_adjoint/

Level 1's Jacobian by implicit differentiation at the inner optimum (#70, card plan step 6b). Numpy only, callables in:
the inner gradient g(z, theta) over z = (every frame's pose, then the body's constants) and the residual rows R(z, theta).

- dR/dtheta = R_theta - R_z H^-1 dg/dtheta. H is the FULL Hessian by central differences of g, never Gauss-Newton
  (the card study measured Gauss-Newton alone 22.4 % off, the full one 0.19 % from a re-solve).
- H is read block-arrow: one pose coordinate of every frame stepped together, then each constant alone
  (2 x (pose size + constants) gradients, not 2 x inner size); solved by the Schur step over the constants.
- An inner fit whose gradient exceeds the tolerance raises `Unconverged`: the caller reports that body, never uses it.
- `Body` is one tuning body's inner problem at its optimum; `stacked_jacobian` is level 1's whole Jacobian in
  `tuning`'s row order (every body's rows, then the prior's), every body checked first (`refused`) and each one stopped
  unconverged named in one `Unconverged`, never used.
- Built and checked on a toy only (2026-10-30, five tests, 1.2 s); `../__init__.solved(exact=)` takes `stacked_jacobian` (its test, 2026-10-30). Not yet wired: the card gradient (Newton eval_fk on
  a wp.Tape for level 3, level 2's constants) as each `Body`'s callables, `solved`'s Jacobian switch to it, the gate on heavy_kimodo, tall_kimodo and
  a third tuning body against `_differences`, and the 70-case timing.
