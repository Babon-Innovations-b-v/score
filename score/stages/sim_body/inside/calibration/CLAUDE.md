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
- `INSIDE_GROUPS` (2026-11-01, #70; the owner and the coordinator: the Head's row by its skull and jaw in SOMA's
  head, then every group where it helps): their rows are read by `_measure.inside_measured`, the group's bone vertices
  laid at rest with their start centre (`myo_parts`, scaled) at SOMA's start joint, then turned and shifted rigidly to
  their least depth outside SOMA's skin (the head's pockets closed); a middle group turns about its body's z alone, a
  side's pair shares one mirrored turn (`turned`); the shift is dropped. Level 1's re-read keeps them (`remeasured`).
  Anchored at the frame body's origin instead (before), the neck's bones stood 48 cm above SOMA's neck (its body's
  origin is at the torso's) and the shoulders' and chest's far off too, so the solve fell into 61.7, 32.5 and 7.2
  degree turns. Kept where the bones outside fell at rest and no group's turn error rose on the mean body's 15 clips:
  Head (the decided one: 6.6 degrees, 30.0 to 3.1 % outside at rest; head 25.1 to 19.5 % on the clips, its turn
  error 4.81 to 5.01 degrees), Shins (5.5 degrees, 12 to 2 %; shin 20.0 to 17.4 %, thigh 28.4 to 24.3 %, their
  error 5.35/6.35 to 4.23/5.05), Feet (1.5, 10 to 2 %; 8.43/8.34 to 7.93/7.76), Hips (0.2) and ForeArms (0.1). Left
  on their lines: Toes (7.0 degrees, 48 to 16 % at rest, but foot 28.3 to 32.3 % on the clips and their error up),
  Hands (2.1 degrees, 14.7 to 13.8 %, the left's error 0.15 to 0.17), Legs (0.3 degrees, their error up 0.02), Chest
  and Neck1 (more outside at rest). All together: bones outside 15.12 to 13.84 %, turns 4.99 to 4.66 degrees, joints
  10.78 to 12.07 mm (the shins' turn moves the knee and ankle centres).
- A stretch's ends are always MyoFullBody's joint centres (`myo_parts`), a reference's points the landmarks' bone
  points: until 2026-10-29 the landmark `sternoclavicular_{side}` (7 mm off the clavicle's origin) shadowed the
  centre of that name, turning the shoulders' rows about 2 degrees; measured again, they are main's. Level 1's
  worker (`../evaluation/_case.py`) reads the table again at rest from each evaluation's group-end centres.
