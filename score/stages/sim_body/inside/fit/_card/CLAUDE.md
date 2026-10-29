# score/stages/sim_body/inside/fit/_card/

Level 3 on the card (#70, the card build plan's step 1; owner 2026-10-29: "the card is why we go for MuJoCo and its
ecosystem"): mink's per-frame step batched over rows on the RTX 5080, in Warp 1.18.0 beside Newton 1.7.0. The mink
path in `../_frames.py` stays the reference and the one that runs until the card path equals it within the plan's
tolerances (cost ratio |x-1| <= 1e-5, angles <= 0.01 deg, sites <= 0.01 mm, every frame); nothing here replaces it
before that.

- `_step.py` (`Reduction`, `damped_step`): mink's damped Gauss-Newton step (1e-2 |r|^2 + 1e-9 on every full dof's
  diagonal, so S^T S in the reduced dofs: a leader's damping times 1 plus its followers' slopes squared; damped once,
  heavy_squat's row 148 swung elv_angle_r and its slope -1 follower 1 rad a step, never stopping, 2026-10-29) in the
  reduced dofs (frozen out, each follower's Jacobian column onto its leader's through polyval's slope, three
  active-set passes after the first solve holding dofs at a bound that push out (one pass let a toy row with two
  dofs on their bounds push a third out and back every step), a held one released when its model gradient
  J^T (r + J s) points its descent back inside (2026-10-29: holds only added kept heavy_kimodo's knee on 0 in the
  chain gate, mink's 4e-4 rad inside; test rows 0 and 1)), solved by Warp's tile Cholesky, Newton's own
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
  converted on the card), a row stopping when its reduced step is under 1e-6 or its cost moved under 1e-10 of itself
  over two steps (1e-9 until 8258bcab: mean_squat's chain stopped 0.047 deg short in elv_angle_r's flat valley), or (as mink's frames, `../_frames.solved`, 2026-10-29) a step moved its float64 residuals by under
  1e-8 (arms_raise's shoulder gimbal drift; its proto-clip and toy tests unchanged, its own break test and the
  arms_raise gate not yet run); NotConverged at 300. Measured 2026-10-29 on the proto clip (136 frames, each row seeded as mink's
  frame was), float32 residuals: angles 0.020 deg and sites 0.029 mm max, all in elv_angle_l/r (the shoulder's
  elevation plane near the hanging arm, a flat direction); mink's answer is the float64 minimum there (scipy's least
  squares at 1e-15 from both answers lands on mink's to 4e-5 deg and 0.0002 mm), so the miss is the card's. With the
  residuals in float64 and the cost stop at 1e-7: angles 0.012 deg, sites 0.017 mm (2 frames over); at 1e-9 (the
  rule): EQUAL on every frame, angles 0.0025 deg, sites 0.0042 mm, cost ratio 2.2e-8, couplings 1.3e-7 rad, ranges
  held, 14 / 26 steps median / max (a step stop of 1e-8 never fires: 114 rows NotConverged at 300). Speed with float32 residuals (one batch, no chunking
  needed up to 12,784 rows): 1,925 rows/s at 1,088, 4,094 at 4,080, 6,889 at 12,784 (1.86 s, 2.7 GB on the card).
- The clip test (2026-10-29, in the test file): a toy MJCF (free root, three ranged hinges, a polyval follower in its
  own body since Newton merges two hinges in one body into a D6, a frozen hinge), 10 frames, mink set up as
  `_frames.Frames` (a place target turned as its site now; a target turned identity adds SE(3)'s V^-1 term and moved
  mink 0.8 deg off the plain place minimum): card equals mink to 0.0012 deg, costs equal to 5 digits, 5 to 28 steps.
- `solved_in_chunks`: `solved` over CHUNK_ROWS (8,000, the plan's) rows at a time, the caller's `optimizer_for(start,
  stop)` one IKSolver a chunk (its buffers are per row); equal to one batch on the toy (test).
- Gate measure (2026-10-29, exact turn Jacobian, three hold passes, one batch, proto clip tiled): EQUAL on every frame
  (angles 0.0017 deg, sites 0.0042 mm, cost ratio 2.0e-8, couplings 1.3e-7 rad, ranges held, 13 / 38 steps median /
  max); 136 rows 2.38 s (57 rows/s, the first launch's compile in it), 1,088 0.89 s (1,223/s, 244 MiB), 4,080 1.60 s
  (2,558/s, 916 MiB), 12,784 3.81 s (3,359/s, 2,740 MiB on the card). Nothing replaces mink yet.
- `_seeds.py` (`first`, `kept`, `newton_order`; plan step 2): iteration 0 starts each frame from mink's own angles
  for it (angles.npz, written by `evaluation._case` beside a clip's measures), later iterations from each frame's own
  last accepted solve; a cold seed (rest pose) is never used. Seeded from the last iteration's angles with the toy's
  places moved 0.5 or 3 mm, one row cycled for good (2,000 steps): the float32 pose's floor, not the step (the float64
  step equals the card's; its model gain 3.7e-12, the pose's rounding moves the cost 9e-9 either way). `_solve`'s cycle
  stop (cost back within 1e-2 of the change between, two steps apart, by a step under 1e-4 since 8258bcab, mean_squat's 2-cycle at mink's angle stepping 3e-5) ends it; a monotone fall
  never fires it. The seed check is in the test file (3 mm on: equals mink). On the proto clip (2026-10-29), each row
  seeded from mink's own answer for its frame (the cache) and mink re-solved from the same seed: EQUAL on every frame
  with the places as they were and moved 0.5 or 3 mm (angles 0.0018 deg, sites 0.0036 mm, cost ratio 2.1e-8 at most,
  steps median / max 3 / 12 to 9 / 24). Speed shares the card with env1: 4,080 rows took 1.5 to 1.7 s with the card
  idle and 3.7 s with env1 holding it at 99%; quote rows/s only with nvidia-smi's utilisation beside it.
- One test file (`tests/test_the_card_step_and_projection_equal_the_cpu_prototype.py`): a 12-row fixture against the
  CPU prototype's float64 maths, the objectives on a six-link chain (`tests/card_chain.py`), the loop and the seeds on
  the toy clip (`tests/card_toy.py`: the MJCF, mink's answer set up as `_frames.Frames`, the card's setup, the
  errors); it needs Newton's Python and a CUDA card, else prints `skipped`. About 15 s.
