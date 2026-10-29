# score/stages/sim_body/inside/fit/_card/

Level 3 on the card (#70, the card build plan's step 1; owner 2026-10-29: "the card is why we go for MuJoCo and its
ecosystem"): mink's per-frame step batched over rows on the RTX 5080, in Warp 1.18.0 beside Newton 1.7.0. The mink
path in `../_frames.py` stays the reference and the one that runs until the card path equals it within the plan's
tolerances (cost ratio |x-1| <= 1e-5, angles <= 0.01 deg, sites <= 0.01 mm, every frame); nothing here replaces it
before that.

- `_step.py` (`Reduction`, `damped_step`): mink's damped Gauss-Newton step (1e-3 |r|^2 + 1e-9 on the diagonal) in the
  reduced dofs (frozen out, each follower's Jacobian column onto its leader's through polyval's slope, three
  active-set passes after the first solve holding dofs at a bound that push out, holds only added: one pass let a
  toy row with two dofs on their bounds push a third out and back every step), solved by Warp's tile Cholesky, Newton's own
  IKOptimizerLM pattern. Reduced size on MyoFullBody measured 37 (128 dofs, 40 frozen, 51 followers, no follower
  leads another, 2026-10-29), inside sm_120's shared memory (fits up to 79); the 37 kernel equals float64 to 1.6e-7
  rad on 497-residual rows, 0.43 ms a step at 136 rows, 10.4 ms at 4,000.
- `_project.py` (`Projection`, `project`): after each step, ranges clipped, followers set to polyval of their
  leader, frozen coordinates back to the row's seed, in MuJoCo's qpos layout (Newton's quaternion order converted
  by the caller).
- `_objective.py` (`PlacePerProblem`, `TurnPerProblem`): Newton's IKObjectivePosition and IKObjectiveRotation
  (canonicalised error; the turn's Jacobian the log's exact one, mink's: SO(3)'s inverse left Jacobian times
  Newton's spin rows, which alone are off by the log's bend 0.1 rad from the target) with offset and weight per problem (rows of several bodies or
  level-1 sets in one batch), analytic; equal to the built-in ones row by row (test file, six-link chain, 1e-6).
- `_forward.py` (`Forward`, `frames`): every row's link frames in float64 (free, revolute, prismatic, fixed; Newton's
  eval_fk maths), for the residuals; `_objective.wide_residuals` gives both objectives' residuals in float64 on them.
- `_solve.py` (`solved`, `NotConverged`): the loop (Newton's analytic Jacobian in float32, the residuals and the stop
  rule's cost in float64 (`_forward`), the damped step, Newton's integrate, the projection; root quaternion order
  converted on the card), a row stopping when its reduced step is under 1e-6 or its cost moved under 1e-9 of itself
  over two steps; NotConverged at 300. Measured 2026-10-29 on the proto clip (136 frames, each row seeded as mink's
  frame was), float32 residuals: angles 0.020 deg and sites 0.029 mm max, all in elv_angle_l/r (the shoulder's
  elevation plane near the hanging arm, a flat direction); mink's answer is the float64 minimum there (scipy's least
  squares at 1e-15 from both answers lands on mink's to 4e-5 deg and 0.0002 mm), so the miss is the card's. With the
  residuals in float64 and the cost stop at 1e-7: angles 0.012 deg, sites 0.017 mm (2 frames over); at 1e-9 (the
  rule): EQUAL on every frame, angles 0.0025 deg, sites 0.0042 mm, cost ratio 2.2e-8, couplings 1.3e-7 rad, ranges
  held, 14 / 26 steps median / max (a step stop of 1e-8 never fires: 114 rows NotConverged at 300). Speed with float32 residuals (one batch, no chunking
  needed up to 12,784 rows): 1,925 rows/s at 1,088, 4,094 at 4,080, 6,889 at 12,784 (1.86 s, 2.7 GB on the card).
  Not in the test file yet; nothing replaces mink.
- The clip test (2026-10-29, in the test file): a toy MJCF (free root, three ranged hinges, a polyval follower in its
  own body since Newton merges two hinges in one body into a D6, a frozen hinge), 10 frames, mink set up as
  `_frames.Frames` (a place target turned as its site now; a target turned identity adds SE(3)'s V^-1 term and moved
  mink 0.8 deg off the plain place minimum): card equals mink to 0.0012 deg, costs equal to 5 digits, 5 to 28 steps.
- Still to come: chunking above ~30,000 rows (plan: 8,000-row chunks, one IKSolver each), the gate measure again
  with the exact turn Jacobian and three hold passes, the test file split under 300 lines.
- One test file (`test_the_card_step_and_projection_equal_the_cpu_prototype.py`): a 12-row fixture against the CPU
  prototype's float64 maths; it needs Newton's Python and a CUDA card, else prints `skipped`.
