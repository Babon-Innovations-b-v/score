# score/stages/sim_body/inside/motor/

MOTOR (#98): the whole trial as one solve on the card, built step by step from the design on #98 (comment
6721156999): 0 feasibility, 1 whole-trial movement, 2 inverse dynamics, contact and the pelvis residual (here now),
3 tuning, 4 muscles, 5 batching, 6 into the stage. `__init__.py` is the interface (`solved`, `solved_on`, `METHOD`);
`_spline.py` the uniform cubic B-spline and its banded normal equations (pure numpy and scipy); `_rows.py` every
frame's Gauss-Newton block of the fit's own cost from level 3's card pieces (`fit._card`), all frames as rows at once;
`_dynamics.py` step 2's rows (the nodes' states, the card's inverse dynamics, the smooth contact, the torques and their
Jacobians); `_stage_a.py` step 2's solve (`dynamics_solved`).

- **Step 1 is the fit's cost over the whole trial, nothing new in it**: the groups' turns, the landmarks' markers and
  the bones inside SOMA's posed skin, exactly as level 3 weighs them, plus the spline's jerk; the leading joints
  inside their ranges by box bounds on their control points. Its jerk weight is not tuned: each coordinate's is the
  one that puts the solve's smoothing at the chain's own CUTOFF (`jerk_weights`). No weight or offset is ever fitted
  against the lab's angles (the owner's patented method; tuning is step 3's, on subjects 2-5 against plates and EMG).
- **The root**: its place a spline like a joint's; its turn the fit's turn low-passed (`smooth_turns`, the chain's
  filter) times exp of a body-frame rotation-vector spline. Newton's root columns are carried onto these unknowns
  through Newton's own world twists (`Layout.carried`: S^-1 U J_r), checked against central differences.
- **On in a job by `"motor": true`** (`sim_body.fitted_person`): the path is MOTOR's in place of the fit's low-passed
  one (`run_person` skips `filtered`); RRA and the rest of the chain run on it as before. Off, the run is the chain's.
- **Step 2, stage A** (`_stage_a`, job `"motor": "dynamics"`, `sim_body.run_person` after the skin's stance credit):
  the same spline's unknowns take every node's inverse dynamics (MuJoCo Warp on the card, `batched.Card`), a smooth
  Hunt-Crossley contact with smoothed Coulomb friction of every skin point within `BAND` of its floor (measured from
  the seen floor: the stance credit), its force the motion's alone, and tau = G^T (needed - J_c^T f_c) on the leading
  coordinates: the root's six rows (the pelvis' residual over the weight and weight x the centre's height) by an
  augmented Lagrangian to the stage's limits, the joints' as an effort. Levenberg-Marquardt on the banded normal
  equations (the optimiser the design left to this step: a kept step's Jacobians only; each node's rows touch its three
  control points, so the band is step 1's). Jacobians: the needed forces' on the place by one-sided card differences,
  on the acceleration MuJoCo's mass matrix (exact), on the speed the joints' damping (the velocity product terms left
  out, a Gauss-Newton model; the cost is always exact); the contact's through each point's Jacobian. The contact's
  settings are physical and untuned (step 3 tunes them on subjects 2-5 against the plates); the penalty and the
  effort start as scales of the fit's cost at the warm start. The chain (RRA, the static optimisation) then runs on
  stage A's path and measures it as any path; stage A's own residual, contact force a side and rounds are its record
  under "motor"/"dynamics".
- **Measured 2026-11-08** (8 LabValidation training trials, subjects 2-5, one L4 each; chain / step 1 / stage A, the
  stage's own chain measuring each): stage A's own residual within 2 %BW and 1 %BW*ht on every frame of 5 trials (the
  walks and squats; worst 1.8 %BW, 0.9 %BW*ht), not on the drop jump, walkingTS1 (both diverged, 17 degrees off step
  1) or the sit-to-stand (no progress at its seat). On the paper's measures it is not yet a gain: over the 5 that
  held, angles MAE 7.61 / 7.59 / 7.91 deg, vertical GRF 16.0 / 15.9 / 15.1 %BW (stage A's own contact 17.0),
  anterior 5.7 / 5.8 / 5.9 (own 8.7), joint moments 1.29 / 1.34 / 1.76 %BW*ht; its path 3.6-7 degrees off step 1,
  the fit's cost 2 to 5 times step 1's. 70-130 s a walk, 6-13 min a squat or sit-to-stand (the place Jacobian's
  card differences). The contact's settings and the weights are untuned (step 3).
- Card only: `solved` raises where Warp sees no CUDA card. The banded solve runs on the host (scipy's
  `solveh_banded`, 5,000-25,000 unknowns, three control points either side).
- Test: `test_one_spline_solve_lowers_the_trials_cost_and_jerk_within_its_ranges.py` (the card's toy, 40 frames;
  step 2 on the same toy built as a person is, a skin grid under its root on a flat floor).
