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
- `_measure.py` (`measures`, `Skins`, `Posed`; plan step 3): the measures level 1 scores on ("joints mm", "per joint
  mm", "turns deg", "per group deg", "bones outside skin %", "bones outside depth mm", "bones outside all %"), keyed as
  `evaluation._measure`; the winding sign and the depth outside by `fit._skin.marks_kernel`, the CPU's own kernel (the
  depths within 4.6e-6 mm of the CPU's on the toy, float32 closest points, 2026-10-30);
  its other readings stay on the CPU. The skin posed every EVERY-th frame once per case (`Skins`, a Warp mesh each);
  the poses by MuJoCo's own float64 kinematics on the host (with MuJoCo Warp's float32 poses one hand vertex fell
  across the skin on heavy_kimodo, 2026-10-29); joint and turn errors float64 Warp kernels (the turn by
  arccos of the trace as the CPU: atan2 differed 0.001 deg on targets not quite orthonormal); the winding test on the
  card. Gate 2026-10-29 (heavy_kimodo, heavy_rigwalk from the seed cache): every measure equal to 4e-13, the skin
  shares exact, no rounded value differs; 0.05 / 0.09 s against the CPU's 2.8 / 2.5 s, the skins cached apart.
- `_level2.py` (`jacobian`; plan step 4, first piece): level 2's exact Jacobian of `../_constants.Problem.residuals`
  in its own sparse pattern, for `least_squares(jac=...)`: per frame the unknowns reach the dofs by `dof_map` (root
  place one for one, its rotation vector by SO(3)'s right Jacobian, MuJoCo's free joint turning in its body frame, a
  leader its dof, a follower by polyval's slope), place rows the site's place Jacobian, turn rows -J_l^-1(log)
  R_site^T times the site's turn Jacobian, a marker's move its body's turn, an inside joint's move its parent's turn
  on every site it carries, the priors diagonal. The frames' kinematics are MuJoCo's float64 on the host for now
  (`Kinematics`, the reference) or the card's (`_level2_card.CardKinematics`: every sampled frame a MuJoCo Warp
  world, `kinematics`, then MuJoCo Warp's own `_cdof` about each root body's origin (not `com_pos`: its float32 atomic
  sums over sibling bodies ran in no fixed order, so two runs of one set ended 1.2e-4 mm apart in joints, 2026-10-29;
  `jac_dof` adds the same point back, the same Jacobian), then one launch of MuJoCo Warp's own `jac_dof` per world,
  site and dof; the
  constants assigned to its `body_pos`/`site_pos` each call, float32, equal to the host's to 3.3e-7; MuJoCo Warp
  reads both per world, `body_pos[worldid % body_pos.shape[0]]` in `smooth.py`'s kinematics and site kernels, so
  level 2 across sets needs no per-world models: one model whose `body_pos`/`site_pos` hold a row per set x frame
  world, checked in the installed mujoco_warp 2026-10-30, not yet built). On fit's toy
  (test, `tests/card_level2.py`) the host's equals central differences to 1.8e-10 of a column, the card's to 1e-5.
  Gate on heavy (host kinematics, 2026-10-29, build/4/gate.py): 12,333 rows x 1,483 unknowns, 283,149 nonzeros; the
  exact Jacobian equals scipy's 2-point to 8.0e-7 of a column (plan 1 %); level 2 with jac=exact against today's:
  constants 0.0011 mm, coordinates 3.2e-4 deg, cost 6.5e-10 relative, both 24 evaluations, status 2; 6.4 s against
  36.7 s (a Jacobian 0.20 s on the host, 1.7 s by differences). With the card's kinematics: 5.2e-6 of a column;
  constants 0.019 mm, coordinates 5.8e-4 deg, cost 8.7e-9 relative, 6.2 s against 35.5 s. `frame_rows` gives COO
  triplets (the frame's own block's nonzeros, the move blocks vectorised, `moved_blocks` and the model's `couplings` made once per Jacobian, not
  per frame, 809dd8a2; a dense block over every
  unknown then csr took the Jacobian to 0.20 s): heavy's Jacobian 0.066 s with the card's kinematics, level 2 3.0 s
  against 32.3 s (constants 0.015 mm, coordinates 0.0020 deg, cost 6.4e-9 relative, 25 evaluations against 24). Wired as an
  option: `../_constants.staged(jacobian=...)` (2-point differences the default and the reference; `constants` does
  not pass it until the 10 tuning bodies' gate is equal); the toy solved both ways in the test file.
- `_clip.py` (`Clip`; plan step 5, first piece): the card loop's parts made from a fitted MuJoCo model as
  `../_frames.Frames` sets mink up (the turn and marker sites with `_frames.weights`' costs, the active joint
  couplings, the followers-free model's slide and hinge ranges, the frozen dofs) beside a Newton model of the same
  file; `angles(turns, points, seeds)` every frame from its own seed. The toy's fixture is set up by it (equal to the
  hand setup bit for bit, 2026-10-29); joint types compared as ints (MuJoCo's enums never equal the model's ints).
  `for_fitting(fitting, path)` builds it for a `Fitting` from the person's file (constants written there), refused
  when Newton's sites at rest miss MuJoCo's by over `MAPPED` (1e-5 m). Its ranges are `followers_free_ranges` (the joint
  arrays `coordinate_bounds` reads, the followers' limits off), not `Fitting.limited_model`'s deep copy of the whole
  model: 2.5 s of tall_kimodo's 14 s card process went to copying the meshes (2026-10-29, cProfile); angles bit for
  bit the same, the toy's setup checks the two bounds equal. On heavy_kimodo's gate dump (2026-10-29,
  build/5/clip_real.py, each frame seeded from mink's cached answer): sites 0.0073 mm apart at rest; 136 rows 1.55 s,
  3 / 32 steps; angles 0.00035 deg, sites 0.0013 mm off mink's.
- `_per_row.py` (`per_row_fk`; level 3 across sets, first piece): Newton's batched FK with each row's joint places
  (`joint_X_p`) read from a [sets, joints] array by the row's set, so one batch can hold every set's frames (rows = set
  x frame) though each set's inside-joint moves change its body places (Newton's IK has no worlds: one model, so the
  places go per row). Newton's own `eval_single_articulation_fk`, so equal to `eval_fk_batched` on each set alone bit
  for bit (2026-10-30, the chain, 3 sets x 4 frames). `rowwise(optimizer, set_places, row_set)` overrides an
  IKOptimizerLM instance's `_fk_two_pass` and `_compute_motion_subspace` with the same per-row read (Newton's own
  kernels, the place read by the row's set; an instance override, not a subclass, since Newton specialises the class
  per size): its analytic residuals and Jacobian equal each set's own model bit for bit (2026-10-30, the chain, a
  position objective). `_forward.Forward(model, set_places, row_set)` does the same in float64 (rows read their set's
  places; several sets with no row_set refused): equal to Forward on each set alone bit for bit (2026-10-30).
  `_solve.solved` / `solved_in_chunks(..., set_places=, row_set=)` (host arrays; chunks slice row_set) wire both: the
  toy's clip as 3 sets (inside joints moved ~2 mm, targets 1 mm apart) in one batch equals each set alone within
  0.01 deg / 0.01 mm (`tests/card_across.py`, 2026-10-30; at ~1 cm moves from mink's base seeds 3 rows did not
  converge in 300 steps, not looked into). `_sets.Sets(clips)` (one `Clip` per set, set 0 the base) builds the set x
  frame rows from several sets, each row its own set's marker offsets, weights and targets on set 0's model, the
  places per row; refused when a set's reduction or projection (frozen, limited, couplings) or its sites or bodies
  differ from set 0's. `Sets.angles(turns, points, seeds)` (one array per set) equals each set's `Clip.angles` alone
  within 0.01 deg / 0.01 mm on the toy (`tests/card_sets.py`: 3 sets, inside joints, offsets, weights and targets
  apart, 2026-10-30). The couplings' polys go per set too (`Reduction.poly` / `Projection.poly` [sets, couplings, 5],
  read by the row's set in `_step._slopes` and `_project._projected`; one set [1, ...] is shared by every row;
  `Sets` stacks each set's and `refusal` leaves `poly` out): a real body's nudged set's file rounds its polys (7e-7
  max, 1.5e-5 relative, 2026-10-30), so equal-poly sets alone would refuse it; on the toy with each set's follower
  slope 0.05 apart, equal to each Clip alone, reading set 0's for every row 4.2 / 10.2 deg off. Toy timing, 4 sets x 10 frames warm: one batch 186 ms against 384 ms alone (2.07x, equal
  exactly). Still to come: the body run calling `Sets`, and the 4-set timing on a real body's short clip.
- One test file (`tests/test_the_card_step_and_projection_equal_the_cpu_prototype.py`): a 12-row fixture against the
  CPU prototype's float64 maths, the objectives on a six-link chain (`tests/card_chain.py`), the loop and the seeds on
  the toy clip (`tests/card_toy.py`: the MJCF, mink's answer set up as `_frames.Frames`, the card's setup, the
  errors), the measures on a toy body (`tests/card_body.py`, its check there too), level 2's two checks in `tests/card_level2.py`; it needs Newton's Python and a CUDA card, else prints `skipped`. About 20 s.
- `_level2_card.CardKinematics.lay` / `frames(qpos, body_pos, site_pos)` (2026-10-30): each world its own row of
  constants (worlds x n x 3), so one card model holds every set's sampled frames (level 2 across sets' first
  piece); on the toy, 3 sets equal each set alone bit for bit (test). Not used: a lockstep driver (one card `frames`
  call a round for every running set, 3acb8b02) was built and deleted 2026-10-30: on tall's first case the card
  `frames` calls are 0.40 s of a 2.42 s level 2 solve (host assembly 1.04 s, residuals 0.34 s, scipy ~0.64 s), so
  batching them across sets saves at most 17 % of level 2. Level 3 across sets (`_sets.Sets`) measured no gain either
  (heavy, 7 clips x 4 sets: 68.1 s alone, 72.3 s together), so its driver went too.
