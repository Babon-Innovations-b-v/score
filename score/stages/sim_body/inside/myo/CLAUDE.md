# score/stages/sim_body/inside/myo/

MyoFullBody made ready for Newton and sized to one person: `person_file` writes the person's file from the pinned
wheel (`SOURCE`), with the fit's constants when given (each joint inside a bone group moved, `inside_moved`; the markers'
moves stay in the fit; the lengths are the sizing's: the run
writes the file twice, sized, then fitted), and returns its record (scales, muscle length scale, kg) and each body's
scale. Its sizing is `sizing`'s; #60's import
fixes are `_fixes.py` (names without '-' or spaces, every muscle's full gain, bias and dynamics parameters, a body with
several joints split into 1 g wrappers, Euler written out, the floor gone).

- A fix here exists because Newton builds the file differently from MuJoCo's compile (#60): its test builds a small
  wheel-shaped body in both and holds them equal. A muscle whose name holds '-' is not written in full
  (`full_muscles` looks the renamed name up in the compile of the old names); MyoFullBody's muscle names have none.
- **MyoFullBody is made movable above the lower back** (#70, the owner: "MyoFullBody should be fully movable";
  `_movable.py`, on the spec of the pinned source, never the download): MyoHead's two neck joints the source leaves
  commented out, one three-axis thoracic joint at T12/L1, and the shoulder girdle's couplings to shoulder_elv dropped
  (the clavicle and the scapula lead), each with its literature range cited beside it; each MoBL phantom (unrotscap,
  unrothum) stays tied at -1 to the joint it undoes: left free, it shares that joint's axis and the clavicle's own
  turn has no target (the card's level 3 swung the pair bound to bound, 2026-10-31). A range is the anatomy's, never
  widened to pass a check.
- **Its feet turn as SOMA's do, within human ranges** (`_movable.FEET`, the owner, 2026-11-01): a twist hinge on the
  talus about the tibia's long axis (`ankle_rotation_{side}`, before the ankle's flexion, +: toes in), 25 degrees in
  and 20 out (the ankle complex's adduction and abduction; Lundberg 1989's 5 and 12 degrees under a 30-degree leg
  turn put the foot at that range's end on 57 % of mean's frames, standing ones too); the ankle to 55 degrees plantar flexion and 33
  dorsiflexion, the subtalar joint to 23 inversion (eversion the model's 20), each cited beside it. A clip that asks
  more (the seated clip's ~61 degrees pointed foot) is the clip's fault: never widened to follow it. Seed caches made
  before have two coordinates fewer and are refused by the card (`fit/_card/_solve`): make them again.
- **Its finger knuckles bend back as a person's do** (`_movable.KNUCKLES`, 2026-11-01): each finger's MCP flexion
  (mcp2 to mcp5) from 45 degrees of extension (the AAOS average range, cited beside it) to the model's 90 of flexion;
  the published 0 left the index and little distal phalanges outside SOMA's flatter hand. The thumb and every other
  joint keep their ranges.
- **Its held fingers rest in SOMA's hand** (`_rested.py`, 2026-11-01): each finger and thumb body turned by its
  joints' rest turns (`calibration.FINGERS`), so the file's zero pose, where `fit` holds the fingers, is SOMA's
  template hand's shape; each joint's axis and anchor carried so every pose is reached as before, its range moved by
  its turn. On the source's spec before sizing (one bone group, one scale); the muscles' length scale is read against
  the same rested source (`_fresh(source).compile()`), so a finger muscle's range does not scale by its rest turn.
- Its test runs in Newton's own Python by subprocess and prints `skipped` where no env is built.
