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
- Still to come (plan step 1, second half): Newton's IKSolver ANALYTIC residuals and Jacobian with per-problem
  targets, the integrate, the float32 stop rule fixed against mink, NotConverged at 300 steps, the clip test against
  mink frame by frame.
- One test file (`test_the_card_step_and_projection_equal_the_cpu_prototype.py`): a 12-row fixture against the CPU
  prototype's float64 maths; it needs Newton's Python and a CUDA card, else prints `skipped`.
