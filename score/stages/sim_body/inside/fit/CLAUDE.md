# score/stages/sim_body/inside/fit/

The one solver (#70; SOMA is the truth): MyoFullBody fitted to the clip's SOMA body. `__init__.py` is the interface
(`followed`, `placed`, `targets`, `fitting`, `constants`, `angles`, `following`, `riding`, `constants_record`,
`METHOD`); `_model.py` the fitting model (`Fitting`: MuJoCo's own compile of the person's file, a calibration site per
bone group, a site per landmark marker, the constants laid on `body_pos`/`site_pos` in
place, the stretches' lengths), `_frames.py` mink per frame, `_constants.py` the constants' sparse least squares,
`_follow.py` the judgement and the segments' riding, `_skin.py` the bones outside SOMA's posed skin by region
(warp's winding number, every 10th frame), `_frozen.py` main's calibration table frozen (227b29b2).

- **Reuse, not handwritten maths** (owner, 2026-10-28): per frame mink 1.3.0 (Apache-2.0, pinned in
  `score/stages/physics/inside/newton_env.sh` with qpsolvers 4.13.0 and daqp 0.10.3), its `FrameTask`s for the
  groups' turns (orientation only, on the calibration sites) and the places (position only, each target's turn its
  site's own so the error is the plain place error), `EqualityConstraintTask` as a hard constraint (the couplings,
  OpenSim's default), `ConfigurationLimit` on the leading joints only, `DofFreezingTask` for the fingers; the
  constants by scipy's `least_squares` with bounds. No handwritten iterative solver here; never bring one back.
- **Weights are OpenSim's IK's** (InverseKinematicsSolver, Simbody's OrientationSensors and Markers goals): each goal
  normalised by its own count, here two goals (the turns, and the landmarks' markers, each weighed by its
  trust); the turns are the main term. Never tune a weight to pass a gate.
- **SOMA's group ends are a target** (#70, the owner's plan, 2026-10-29): every bone group's start that is a SOMA
  rig joint (`group_ends`: hips, knees, ankles, toes' bases, sternoclavicular, shoulders, elbows, wrists, the lumbar,
  thoracic and skull joints, the hips' and neck's middles too: one rule for every end, a middle of two bodies' centres
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
  Newton's model has them too; the record keeps each in mm (`inside joints moved mm`). No group or joint special-cased.
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
  the run (`NotConverged`), never kept silently.
- **The record states the honest measures first** (#70's audit item 2, 2026-10-29): `following` gives the bones
  outside SOMA's skin by region and the turns on main's frozen table before the joint mm (partly the ends' own pull)
  and the tree's-table turns; the frozen table is never edited to follow the tree.
- `following` and `riding` read the bone-group and landmark tables of MyoFullBody itself, so the toy test does not
  reach them; they are checked on the walkers' runs (#70's numbers).
- Its test runs in Newton's own Python by subprocess and prints `skipped` where no env is built.
