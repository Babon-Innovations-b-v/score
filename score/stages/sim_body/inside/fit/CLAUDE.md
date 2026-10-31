# score/stages/sim_body/inside/fit/

The one solver (#70; SOMA is the truth): MyoFullBody fitted to the clip's SOMA body. `__init__.py` is the interface
(`followed`, `placed`, `targets`, `fitting`, `constants`, `angles`, `following`, `riding`, `constants_record`,
`METHOD`); `_model.py` the fitting model (`Fitting`: MuJoCo's own compile of the person's file, a calibration site per
bone group, a site per landmark marker, the constants laid on `body_pos`/`site_pos` in
place, the stretches' lengths), `_frames.py` mink per frame, `_constants.py` the constants' sparse least squares,
`_follow.py` the judgement and the segments' riding, `_skin.py` the bones outside SOMA's posed skin by region
(warp's winding number, every 10th frame; `marks_kernel` beside it each point's depth outside, its distance to the
skin's closest point, 0 inside, `depth_mm` a region's root mean square: level 1's smooth skin residual, the share
staying the judged measure; one kernel for the CPU and the card), `_frozen.py` main's calibration table frozen (227b29b2), `_card/` level 3's step and projection on the card (plan step 1, being proved equal to mink; mink stays the reference); level 2's exact Jacobian too, and level 2's residuals and Jacobian in float64 with the frames' kinematics on the card (`_card._level2_wide`), which `constants` has `staged` use (`wide=True`; scipy's 2-point differences stay `staged`'s default and the reference, `told` reads the host's).

- **Reuse, not handwritten maths** (owner, 2026-10-28): per frame mink 1.3.0 (Apache-2.0, pinned in
  `score/stages/physics/inside/newton_env.sh` with qpsolvers 4.13.0 and daqp 0.10.3), its `FrameTask`s for the
  groups' turns (orientation only, on the calibration sites) and the places (position only, each target's turn its
  site's own so the error is the plain place error), `EqualityConstraintTask` as a hard constraint (the couplings,
  OpenSim's default), `ConfigurationLimit` on the leading joints only, `DofFreezingTask` for the fingers; the
  constants by scipy's `least_squares` with bounds. No handwritten iterative solver here; never bring one back.
- **Weights are OpenSim's IK's** (InverseKinematicsSolver, Simbody's OrientationSensors and Markers goals): each goal
  normalised by its own count, here two goals (the turns, and the landmarks' markers, each weighed by its
  trust); the turns are the main term. Never tune a weight to pass a gate. The markers' goal's sum is each
  `Fitting`'s own `marker_goal` (taken from `_frames.MARKER_GOAL` when `fitting` builds it): it is a level 1 unknown,
  so sets solved across one another each keep their own, never the module's last value.
- **SOMA's group ends are a target** (#70, the owner's plan, 2026-10-29): every bone group's start that is a SOMA
  rig joint (`group_ends`: hips, knees, ankles, toes' bases, sternoclavicular, shoulders, elbows, wrists, the lumbar,
  thoracic and skull joints, the neck's middle too (the hips' middle left out: its two hip ends already hold both its rig joints, never counted twice): one rule for every end, a middle of two bodies' centres
  put on their nearest common holder at rest by `end_site`, the pelvis and the thorax, SOMA's side the mean of its two
  rig joints, `landmarks.soma_joints`) is a marker at MyoFullBody's centre there, never moved, weighed END_WEIGHT times the landmarks' mean trust, the same for
  every end, in the markers' goal beside the landmarks (whose weights keep their own sum, `Fitting.goal`); joints inside
  a group come from the landmarks and couplings. Before (2026-10-29 upstream fit) SOMA's joints were only the measure,
  and before that a SOMA rule centre as target pulled the ankle 16 mm up the shank. Since the ends are a target, the
  joint measure partly measures what the solver pulls on: judge with the bones inside SOMA's skin and the turns on a
  frozen calibration table beside it.
- **No size unknowns** (#70 level 2: lengths straight from SOMA): the lengths are the sizing's (`inside/sizing`),
  never solved here. The size-factor stage (14 mirrored size groups pulled to 1) never ran and was deleted
  (2026-10-29, the audit's item 9) with its record fields. The constants are each free marker's move off its link,
  pulled to it at its own weight, and the joints inside groups (below); the plantar pads (`landmarks.HELD`) never
  move, so a foot cannot sink through SOMA's sole.
- **The joints inside groups are person constants** (#70 level 2, 2026-10-29): every body whose parent is another
  body of its own bone group (the lumbar levels, clavicle to scapula, the wrist bones, talus to calcaneus, the radius)
  and that a marker rides, it or a body below it (`Fitting.inside`), moves in its parent, solved in the markers' stage
  with the markers' moves and the sampled frames' angles, once per body, within `MARK_MOST`, pulled to its place at
  the markers' mean weight; never per frame. The moves are written in the person's file (`myo.inside_moved`), so
  Newton's model has them too; the record keeps each in mm (`inside joints moved mm`). No group or joint special-cased. Only the axes the data can tell are solved (`_constants.told`, 2026-10-29: level 2's optimum was
  flat, card and 2-point ending 1.1-1.55 mm apart): an inside joint axis whose column of level 2's exact Jacobian at
  the start (the host's double kinematics, never the card's floats) lies within `TOLD` of the span of every other
  column (the markers' moves, the frames' coordinates, root place included) and of the inside axes kept before it
  in the model's order (QR without pivoting; column-pivoted until 2026-10-31, when tall's c3, a landmark's trust,
  showed the pivot flipping between humphant_l's y and humphant1_l's at a 5 % trust change: level 2's constants
  jumped ~1 cm between level 1's nudged sets, their STEP and STEP/2 central differences 99.9 % apart; in the model's
  order the kept set is the same in every set and they are 0.1 % apart, night/gpu2/c3) stays at its file's place. On the tall walker 38 of 96 axes: the pelvis (its common shift with
  the sacrum is the root's place), the welded root, thorax and cervical spine (the bimanual attachment above takes
  them), the capitate and metacarpals (their markers' own moves take them), each humphant1's y; every other axis,
  the clavicle phantoms and scapulae too, is told (least: a scapula's y, 4e-3).
  The other columns' span is taken by their Gram matrix (`_constants.off_span`, sparse Cholesky) when their smallest
  singular value is over `WELL_TOLD` of their largest (then the pivoted QR keeps their whole span), else by that QR
  (`qr_off_span`); heavy_kimodo: 0.15 s against 2.5-5.6 s, the same axes kept.
- **Level 2 ends settled to float64** (#70, 2026-10-30): after scipy's `least_squares` (trf/lsmr, which stalled
  2.5 to 3 mm short of settled on heavy_kimodo) `_constants.polished` takes Gauss-Newton steps (the host-exact
  Jacobian, a sparse direct solve, halved until the cost falls) on the told unknowns more than `BOUND_HELD` inside
  their bounds until their gradient is under `POLISHED` (1e-10), else raises. When no halving lowers the cost, the
  whole step is judged by the free gradient instead (`steadied`: taken when it lowers it): on mean_kimodo the step's
  predicted fall at 1.59e-10 was 4.4e-17 on a cost of 0.867, under the residuals' own float64 noise (reading the fall
  off the residuals' differences instead of two summed costs did not help), so the cost test refused every halving. A halving is taken only on a strict fall (2026-10-30): with `<=` heavy_kimodo's polish took halvings 1e-13 long at an equal cost round after round and stood at 1.48e-10 for its last 10 of 30 rounds, `steadied` never asked; strict, b4/steps' run (13 sets, three bodies) ended with no polish refused, the 36 it logged under 1e-10 in 14 to 23 rounds. `Problem.path` is float64: the card's
  float32 angles rounded every qpos the residuals read (a 1e-6 step on root z moved it 9.5e-7), so the polish
  stalled at 6.5e-8 and the "exact Jacobian is off" reading was the residuals'. Toy: 2.0e-7 without the polish,
  under 1e-10 with it, 0.028 s; heavy_kimodo's polish 2.4 s. `least_squares` runs at scipy's own tolerances: the
  polish does the settling (at ftol=xtol 1e-12, gtol 1e-10 the whole real solve took 405 s; toy without the polish
  at the loose tolerances 9.8e-7; heavy_kimodo at them: 22 s, polish 5.0 s, free gradient 9.7e-11).
- **The calibration is the static table** (`calibration`), a site's quaternion R_cal^T on the group's frame body:
  never fitted, never per person.
- **The followers' own ranges are not held** (`Fitting.limited_model`): 35 of MyoFullBody's 51 couplings have a
  follower range narrower than its polynomial over its leader's range (the published model's); held, they stopped a
  leader 50 degrees short of a reachable pose (solver study, 2026-10-28). OpenSim's assembler and the old fit did not
  hold them either.
- **Every group SOMA has is a turn target** (`followed`): leaving out the groups with no joint of their own (thorax,
  neck, head) or only followers (lumbar above L5, shoulder girdle) measured worse on the Kimodo walker (joints 24 mm
  median against 17, 2026-10-28, before SOMA's joints were a goal).
- **The constants are one sparse problem** with the angles of `SAMPLE` frames (`_constants.Problem`): alternating
  mink and the constants gave the same answer on the walker (joints 16.9 against 16.7 mm median) but converged
  linearly and did not give back the toy's constants (test); the sparse solve takes about a minute on 30 frames.
- What stays (measured 2026-10-29 on both test walkers, median over the frames, SOMA's joints no goal): the joints
  16 mm off SOMA's, the shoulders 44 to 50, the head 20 to 25 (rigid on the thorax); the groups' turns 5.2 to 5.9
  degrees on the median of those not at a limit, the head 23 (rigid). A frame that does not converge in `MOST_STEPS` fails
  the run (`NotConverged`), never kept silently. A frame's fit ends on a step under `STEP_DONE`, its own norm or its change to the
  tasks' and couplings' weighted errors (2026-10-29: at zero shoulder elevation elv_angle and its follower cancel, a
  direction no task sees; mink drifted along it 1e-4 rad a step for ever on every body's arms_raise; with the rule
  mean, heavy and short converge on all 7 clips, the other clips' angles moved at most 7e-6 rad).
- **Mink stops on its joint bounds where the card does not** (#70, 2026-10-30): on heavy_short_legged frame 16 mink
  ends at its ConfigurationLimit bounds (cost 0.307) while the card's solve ends at 0.0094 inside every range; that
  frame held two right-arm constants on their 0.03 m bound (level 2 cost 0.900 against 0.602 with card frames). So
  level 2's sampled frames are posed on the card, across sets (`card_paths`, `constants_across`: one launch a frame for every set; `evaluation/_card_sets`
  solves each body's constants that way); the bar is no worse than the CPU per body, better where mink is stuck. Why (measured 2026-10-30): not
  an early stop. From frame 15's seed mink's first full step is 2.0 rad (tangent norm) and lands in a second basin;
  its next 66 steps shrink geometrically, the cost flat at 0.30691 to 1e-15, and `moved < STEP_DONE` fires at a true
  local minimum. Seeded at the card's frame 16, mink stays there (cost 0.00929). So a toy for the card's edge needs a
  first step that overshoots into another basin, not a hinge driven past its range (that one mink slides along).
  Across sets against one set after another (measured 2026-10-30, card frames on both): 32 sets of heavy_arms_raise
  8.9 s a set against 17.8 s a nudged set alone; gate6a on heavy_kimodo + tall_kimodo, step cosine at least 0.99975
  on all 6 columns, relative under 1 % but ASIS_l trust 2.26 %, whose card-against-CPU gap (6.3e-5 a step) is the size
  of the start set's own gap (7.7e-5): float noise on a column that barely moves tall_kimodo, not a wiring error.
  The gate's rule (coordinator, 2026-10-30): a column passes at a relative gap of at most 2 %, or, above that,
  when its absolute gap is no larger than the start set's own card-against-CPU gap; on that rule all 6 pass.
  Card frames against mink frames on heavy_arms_raise (2026-10-30): the earlier gap (joints mm max 64.5 against
  59.6, shin bones outside 2.1 % against 0.65 %) came from fitting level 2 on that one recording against the body's
  seven, not from the card. Like with like (seven recordings, set s00000) card frames read joints mm max 59.4 against
  59.6, bones outside 13.9 % against 14.7 %, foot 17.6 against 19.2 %, hand 49.4 against 54.2 %; worse by a hair on
  shin (0.82 against 0.65 %, depth 0.19 against 0.17 mm) and thigh (18.0 against 17.7 %). That hair is the solvers'
  tolerance, not a fault: level 3's leg and spine angles differ at most 0.0005 rad, the root at most 0.9 mm, the leg
  constants are equal, so bone points within 0.2 mm of the skin flip side; only the shoulder chain moves (at most
  0.022 rad, its constants traded within their box), which is where the hand and forearm gain.
  On the body's seven clips (heavy, 4 real sets, measured 2026-10-30 with the card and CPU shared): across sets 70.8 s
  against 112.1 s one after another, measures within 0.0033; about 5.7 s against 22 s a nudged set after the first.
  Tall's seven clips the same way (4 sets): 73.5 s against 110.5 s, measures within 0.033 mm; about 4.7 s against
  23.2 s a nudged set. Every tuning body has seven clips, so a Jacobian's ~4.5 h would be ~0.9 to 1.15 h, one
  process a body, if a process holding 138 sets keeps a set's card memory (measured on 4 sets only).
- **The skin's side is the exact winding number's** (2026-10-31): every skin mesh is built with Warp's
  `support_winding_number=True` (`_skin.marks`, `_card/_measure.Skins`, `tuning/_adjoint/_measures`). Without it
  Warp's sign query misjudged points of a posed skin that crosses itself: a forearm point 5.7 mm off mean_running's
  skin read outside, then inside after a 0.003 mm move (exact winding number 1 both times), and the jump of its depth
  made the trust and end weight columns' differences scale as 1/step on running, squat and sit_stand (night/gpu2/c3);
  on frame 12's skin 1 of 3,000 random points within a centimetre sat on the wrong side, none with it; the test's
  four overlapping spheres 169 of 4,000.
- **The record states the honest measures first** (#70's audit item 2, 2026-10-29): `following` gives the bones
  outside SOMA's skin by region and the turns on main's frozen table before the joint mm (partly the ends' own pull)
  and the tree's-table turns; the frozen table is never edited to follow the tree.
- `following` and `riding` read the bone-group and landmark tables of MyoFullBody itself, so the toy test does not
  reach them; they are checked on the walkers' runs (#70's numbers).
- Its test runs in Newton's own Python by subprocess and prints `skipped` where no env is built.
