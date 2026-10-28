# score/stages/sim_body/inside/calibration/

The static calibration table (#70; pure numpy, its test runs in the score venv): `TABLE`, per bone group, the fixed
turn R_cal between SOMA's segment frame and MyoFullBody's group frame (R_body = R_segment @ R_cal), read once from
the two models' rest poses (SOMA's template bind against MyoFullBody's default pose, couplings applied) by aligning
each group's anatomical axes (`aligned`, `frame`, `REFERENCES`); `turn(group)` gives it as a matrix.

- Never fit it, never per person or per clip: it would absorb a person's posture (a curved spine) and erase it
  (owner, 2026-10-28). It is the geometry every retargeting tool uses, not fitted to reference data.
- `_measure.py` measures it again in Newton's own Python and prints `TABLE`; run it after a model or template change
  and paste the rows. Measured 2026-10-28: the same as the tables study's within 0.002 (quaternion parts).
- A right group's turn is its left one's times diag(-1, -1, 1); a middle group turns no body sideways (the test).
