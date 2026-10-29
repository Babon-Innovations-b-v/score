# score/stages/sim_body/inside/fit/_card/

Level 3 on the card (#70, the card build plan's step 1; owner 2026-10-29: "the card is why we go for MuJoCo and its
ecosystem"): mink's per-frame step batched over rows on the RTX 5080, in Warp 1.18.0 beside Newton 1.7.0. The mink
path in `../_frames.py` stays the reference and the one that runs until the card path equals it within the plan's
tolerances (cost ratio |x-1| <= 1e-5, angles <= 0.01 deg, sites <= 0.01 mm, every frame); nothing here replaces it
before that.

- `_step.py` (`Reduction`, `damped_step`): mink's damped Gauss-Newton step (1e-3 |r|^2 + 1e-9 on the diagonal) in the
  reduced dofs (frozen out, each follower's Jacobian column onto its leader's through polyval's slope, one
  active-set pass holding dofs at a bound that push out), solved by Warp's tile Cholesky, Newton's own
  IKOptimizerLM pattern. Reduced size on MyoFullBody measured 37 (128 dofs, 40 frozen, 51 followers, no follower
  leads another, 2026-10-29), inside sm_120's shared memory (fits up to 79); the 37 kernel equals float64 to 1.6e-7
  rad on 497-residual rows, 0.43 ms a step at 136 rows, 10.4 ms at 4,000.
- `_project.py` (`Projection`, `project`): after each step, ranges clipped, followers set to polyval of their
  leader, frozen coordinates back to the row's seed, in MuJoCo's qpos layout (Newton's quaternion order converted
  by the caller).
- `_objective.py` (`PlacePerProblem`, `TurnPerProblem`): Newton's IKObjectivePosition and IKObjectiveRotation
  (canonicalised error, its analytic omega Jacobian) with offset and weight per problem (rows of several bodies or
  level-1 sets in one batch), analytic; equal to the built-in ones row by row (test file, six-link chain, 1e-6).
- `_solve.py` (`solved`, `NotConverged`): the loop (Newton's analytic residuals and Jacobian, the damped step, Newton's
  integrate, the projection; root quaternion order converted on the card), a row stopping when its reduced step is
  under 1e-6 or its cost moved under 1e-7 of itself over two steps; NotConverged at 300. Measured 2026-10-29 on the
  proto clip (136 frames, each row seeded as mink's frame was): cost ratio |x-1| 2.2e-8 max, couplings 1.4e-7 rad,
  ranges held, 12 / 25 steps median / max; NOT yet equal: angles 0.020 deg and sites 0.029 mm max (3 frames over the
  plan's 0.01), all in elv_angle_l/r (the shoulder's elevation plane near the hanging arm, a flat direction), not
  moved by a tighter stop or float64 sums in the normal equations: a float32 floor of Newton's FK/Jacobian. Speed
  (one batch, no chunking needed up to 12,784 rows): 1,925 rows/s at 1,088, 4,094 at 4,080, 6,889 at 12,784 (1.86 s,
  2.7 GB on the card). Not in the test file yet; nothing replaces mink.
- Still to come: the equality decision on the flat shoulder dof, chunking above ~30,000 rows, the clip test against
  mink in the test file.
- One test file (`test_the_card_step_and_projection_equal_the_cpu_prototype.py`): a 12-row fixture against the CPU
  prototype's float64 maths; it needs Newton's Python and a CUDA card, else prints `skipped`.
