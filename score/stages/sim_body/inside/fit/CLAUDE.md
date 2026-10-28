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
  normalised by its own count, here three goals (the turns, the landmarks, SOMA's joints), so 1 degree of turn costs
  as much as 1.75 cm of marker error; the turns are the main term. Never tune a weight to pass a gate.
- **SOMA's joints are a goal of their own** (`placed`, 2026-10-28; #70 named two place goals, the landmarks only):
  #70 judges the fit on SOMA's joints, and with the landmarks alone they stood 17 mm off on the median (the landmark
  joint centres are 4 to 24 mm off SOMA's); with SOMA's joints as a third goal 12.7 mm while the lengths were free to
  drift, 18.7 (Kimodo walker) and 19.5 (rig walk) with every stretch held to SOMA's length. An owner's decision to
  keep or drop (#70).
- **The group sizes are solved** (`_constants`, within `SIZE_MOST` of the sizing's): until 2026-10-29 each stretch was
  held to SOMA's length (LENGTH_WEIGHT 100, every group within 1.1 mm); #70's review asked them solved, and the model
  record's `lengths` says how far they move from SOMA's (numbers on #70).
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
- What stays (measured 2026-10-28 on both test walkers, median over the frames): the ankles 37 mm off SOMA's, the
  arms' joints 15 to 24 mm, the head 28 to 30 mm (rigid on the thorax); the groups' turns 5 to 6 degrees on the
  median, the feet and toes 8 to 9 (hinges), the head 23 (rigid). A frame that does not converge in `MOST_STEPS` fails
  the run (`NotConverged`), never kept silently.
- `following` and `riding` read the bone-group and landmark tables of MyoFullBody itself, so the toy test does not
  reach them; they are checked on the walkers' runs (#70's numbers).
- Its test runs in Newton's own Python by subprocess and prints `skipped` where no env is built.
