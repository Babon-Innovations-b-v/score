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
- Its test runs in Newton's own Python by subprocess and prints `skipped` where no env is built.
