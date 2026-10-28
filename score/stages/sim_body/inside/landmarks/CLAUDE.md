# score/stages/sim_body/inside/landmarks/

The SOMA mesh landmarks and the MyoFullBody points that match them (#70; pure numpy, its test runs in the score
venv): `MARKS` (72: a SOMA face and barycentric weights, its segment, the MyoFullBody body, the bone point and the
marker's starting point, the template's soft tissue, the confidence, whether the solver takes it), `CENTRES`
(MyoFullBody's joint centres, body-local, source model), `on_skin` (each landmark on a person's mesh: every person's
mesh shares the template's topology), `soma_centres` (ISB midpoints, Harrington 2007's hips), `soma_point` (a bone
group's stretch end on SOMA) and `myo_parts`.

- `_table.py` is generated, once, from the tables study of 2026-10-28 (its scripts stay with the study, outside the
  repository); edit a row by hand only with the measurement that justifies it, noted here.
- The marker starting points embed the template's soft tissue; the solver fits where each marker sits on its bone.
- Landmark joint centres against SOMA's joints on the template: elbow 4.2 mm, wrist 4.5, knee 8.1, ankle 20.6, hip
  23.5 mm. They are not the sizing's (the sim body's joints sit on SOMA's), only the solver's start.
