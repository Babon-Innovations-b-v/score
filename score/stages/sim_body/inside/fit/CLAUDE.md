# score/stages/sim_body/inside/fit/

The one solver (#70; SOMA is the truth): MyoFullBody fitted to the clip's SOMA body. `__init__.py` is the interface
(`followed`, `placed`, `targets`, `fitting`, `constants`, `angles`, `following`, `riding`, `constants_record`,
`METHOD`); `_model.py` the fitting model (`Fitting`: MuJoCo's own compile of the person's file, a calibration site per
bone group, a site per landmark marker and per SOMA joint's centre, the constants laid on `body_pos`/`site_pos` in
place, the stretches' lengths), `_frames.py` mink per frame, `_constants.py` the constants' sparse least squares,
`_follow.py` the judgement and the segments' riding.

- **Reuse, not handwritten maths** (owner, 2026-10-28): per frame mink 1.3.0 (Apache-2.0, pinned in
  `score/stages/physics/inside/newton_env.sh` with qpsolvers 4.13.0 and daqp 0.10.3), its `FrameTask`s for the
  groups' turns (orientation only, on the calibration sites) and the places (position only, each target's turn its
  site's own so the error is the plain place error), `EqualityConstraintTask` as a hard constraint (the couplings,
  OpenSim's default), `ConfigurationLimit` on the leading joints only, `DofFreezingTask` for the fingers; the
  constants by scipy's `least_squares` with bounds. No handwritten iterative solver here; never bring one back.
- **Weights are OpenSim's IK's** (InverseKinematicsSolver, Simbody's OrientationSensors and Markers goals): each goal
  normalised by its own count, here two goals (the turns, and the markers: the landmarks and the joint centres they
  give); the turns are the main term. Never tune a weight to pass a gate.
- **SOMA's joints are no target, only the measure** (#70, 2026-10-29; before, from 2026-10-28, a third goal, which
  made the joint measure partly circular): the markers hold the joint centres the landmarks give (`centred`,
  `CENTRE_JOINTS`: ISB midpoints and Harrington's hips, `landmarks.soma_centres`) on MyoFullBody's centres of the
  same name, OpenSim's practice; `following` judges against SOMA's own joints: 16.1 (Kimodo walker) and 15.9 mm
  (rig walk) on the median of the joints not at a range limit, against 9.5 and 9.7 while they were a goal, the
  shoulders (SOMA's Arm joints) the furthest, 44 to 50 mm, having no landmark centre of their own (2026-10-29).
- **The group sizes are solved** (`_constants`, within `SIZE_MOST` of the sizing's): until 2026-10-29 each stretch was
  held to SOMA's length (LENGTH_WEIGHT 100, every group within 1.1 mm); #70's review asked them solved, and the model
  record's `lengths` says how far they move from SOMA's: with SOMA's joints a goal, up to 12 to 13 mm (the pelvis,
  shoulders, head), the joints 1 mm nearer on the median; with the landmarks alone, up to 20 to 22 mm (the shoulder
  girdle and upper arms longer, the shins 6 to 9 mm shorter; 2026-10-29, both test walkers).
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
- `following` and `riding` read the bone-group and landmark tables of MyoFullBody itself, so the toy test does not
  reach them; they are checked on the walkers' runs (#70's numbers).
- Its test runs in Newton's own Python by subprocess and prints `skipped` where no env is built.
