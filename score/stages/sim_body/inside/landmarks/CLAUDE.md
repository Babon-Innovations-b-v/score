# score/stages/sim_body/inside/landmarks/

SCORE's landmark set (#70, CONTEXT.md "landmark set"; pure numpy, its test runs in the score venv): `LANDMARKS`
(102 from the landmark study of 2026-10-29, 84 the solver's: a SOMA face and barycentric weights, its segment, the
MyoFullBody body, the bone point, the link, the trust, whether the solver takes it),
`CENTRES` (MyoFullBody's own joint centres, the group ends' and the measure's; a group end's is level 1's to move,
`tuning.ended`), `on_skin`, `posed`, `soma_point` and
`soma_joints` (SOMA's own joints, the group ends, the measure and the masses) and `myo_parts`. The links and trusts are
level 1's (`tuning`); the old joint-centre rules (Harrington's hips, Rab's shoulders) and the per-landmark
refinement were deleted 2026-10-29 (no caller; the group ends are SOMA's rig joints).
Every point by its anatomical definition; never a licensed dataset's marker list.

- `_table.py` is generated, once, from the landmark study of 2026-10-29 (MC3_head_r's trust set to the left's, 0.098,
  the worse side's as the study's mirrored rule says; head_vertex's link turned to its outward +y and opisthocranion's
  to its outward -x, their magnitudes kept, 2026-10-29: both pointed +x, one across the crown, one into the skull, and
  level 1 drove them to its bound; `head_crown` = head_vertex plus that 7 mm scalp, the Head group's end, as SOMA's
  HeadEnd sits on the skin's top, within 0.6 mm along the head on all 12 bodies) (its scripts stay with the study, outside the
  repository); edit a row by hand only with the measurement that justifies it, noted here.
- MC5_head's SOMA face moved onto the little finger's knuckle (2026-11-01; 2631 to 2859, 7135 to 7363): the study's
  face stood between the middle and ring fingers' lines on the template (y -8.7 mm in the hand's frame, the little
  finger's line -37.4: the dorsal skin over each finger's skin centre line, carried back from its sections at 110 and
  125 mm to the knuckle's place along the hand), 28.7 mm off its bone point, and turned the Hand table 15 degrees
  about the hand's long axis. MC2, MC3 and MC5's links measured again on the template with the new table (the study's
  way: skin point less the carried bone point, body frame); MC2's face kept (13 mm radial of the index's line: the
  knuckle's radial side; moved too, the template's finger bones fit worse, 41.6 % outside against 24.7 %).
- The marker starting points embed the template's soft tissue; the solver fits where each marker sits on its bone.
- Rule centres against SOMA's joints on the template (study, 2026-10-29): knee 2.1 mm, ankle 15.9, elbow 11.0, wrist
  4.5, mtp 27.3, hip 21.4, glenohumeral 21.8; the rule's bias between the two models 2 to 8 mm but the hip's 31.6.
  They are the sizing's ends, on both models alike; SOMA's joints are only the measure.
