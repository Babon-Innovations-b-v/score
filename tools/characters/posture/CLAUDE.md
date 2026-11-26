# tools/characters/posture/

A person of the people line standing or walking at ease (#223): `relaxed` brings a relaxed clip's (`RELAXED`) feet
under the hips, its upper arms in to hang against the body that plays it and its gaze level; `measured` and `faults`
fail a clip with an arm held out or a gaze up into the sky. `../garments` `built_body` runs both on every relaxed clip
it plays (the clothes are draped and the whole person drawn on that), so the run stops on a posture fault. The
`__init__.py` docstring has the measures that led here and how each move is made.

- **One fixed turn a clip.** Every correction is one turn for the whole clip (the feet's move, each arm's, the head's),
  so the clip's own sway, swing and nods stay; never a pose per frame.
- **The body decides how close an arm hangs.** An arm comes in only as far as the skin that plays it lets it
  (`clearance`, the garments' `shaped.sunk` against the torso and thighs); its forearm turns out at the elbow first
  (a carrying angle) to keep the hand off the thigh, and where that is not enough its shoulder comes a few degrees
  forward (woman_stair's walking right arm, against the side of her chest). A wide build's arms hang further out; that is the build, not the
  clip.
- **The gaze is the face's.** `rest_gaze` reads the face's own look at rest (its corneas off its eyeballs), so a face
  that sits looking up on SOMA's head is levelled with the head, not by the face fit.
- **Hands at rest** (owner, 2026-11-25: "stiff splayed fingers", a thumb out): `finger_joints` reads each hand's
  five fingers off its own skin (SOMA's finger joint places in body_face.py's npz are the template's, 8 cm off her
  hand), `hand_rested` lays the fingers in a resting cascade, together, the thumb along the index finger, and
  `hand_faults` fails a thumb out, spread fingers or a straight (or bent-back) finger. `../whole` `relaxed_hands`
  runs both on the skin the clothes are draped on and the picture shows.
- **Wrists, reach and walk.** `clip_faults` (run by `../garments` `relaxed_clip`) adds a wrist hooked to the side or
  bent, elbows or wrists higher or lower than people's for the height, and a walk whose arms do not swing against
  their legs, whose feet land flat or whose knees hardly bend.
- **Look at the pictures.** The measures say the angles are in range; only a front, side and three-quarter picture
  says the person stands like a person.
- Tests: `test_a_relaxed_clip_hangs_its_arms_and_looks_ahead.py` (a toy rig; no SOMA, Newton or Blender).
