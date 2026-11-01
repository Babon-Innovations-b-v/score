# score/stages/sim_body/inside/calibration/

The static calibration table (#70; pure numpy, its test runs in the score venv): `TABLE`, per bone group, the fixed
turn R_cal between SOMA's segment frame and MyoFullBody's group frame (R_body = R_segment @ R_cal), read once from
the two models' rest poses (SOMA's template bind against MyoFullBody's default pose, couplings applied) by aligning
each group's anatomical axes (`aligned`, `frame`, `REFERENCES`); `turn(group)` gives it as a matrix.

- `FINGERS` (2026-11-01): the held fingers' rest turns, one per joint for both hands, so MyoFullBody's hand at rest
  is SOMA's template hand's shape (SOMA's hand is one rigid shape; MyoFullBody's published zero has the fingers straight
  and the thumb opposed, 67.6 % of the finger bones' vertices outside the template's skin, the thumb 25 to 45 mm;
  24.7 % with them, the thumb inside). `_measure.fingers_measured` reads them on the table as it stands (paste TABLE
  first): each finger bone vertex as deep in SOMA's skin as the joints' ranges let it, both hands one solve; laid in
  the person's file by `myo._rested`. The index stays out (SOMA's index stands dorsal of where MyoFullBody's metacarpal
  puts it and its knuckle does not bend back). Static like the table: never per person or per clip.
- Never fit it, never per person or per clip: it would absorb a person's posture (a curved spine) and erase it
  (owner, 2026-10-28). It is the geometry every retargeting tool uses, not fitted to reference data.
- `_measure.py` measures it again in Newton's own Python and prints `TABLE`; run it after a model or template change
  and paste the rows. Measured 2026-10-28: the same as the tables study's within 0.002 (quaternion parts).
- A right group's turn is its left one's times diag(-1, -1, 1); a middle group turns no body sideways (the test).
- A stretch's ends are always MyoFullBody's joint centres (`myo_parts`), a reference's points the landmarks' bone
  points: until 2026-10-29 the landmark `sternoclavicular_{side}` (7 mm off the clavicle's origin) shadowed the
  centre of that name, turning the shoulders' rows about 2 degrees; measured again, they are main's. Level 1's
  worker (`../evaluation/_case.py`) reads the table again at rest from each evaluation's group-end centres.
