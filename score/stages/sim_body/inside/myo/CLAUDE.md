# score/stages/sim_body/inside/myo/

MyoFullBody made ready for Newton and sized to one person: `person_file` writes the person's file from the pinned
wheel (`SOURCE`) and returns its record (scales, muscle length scale, kg). Its sizing is `sizing`'s; #60's import
fixes are `_fixes.py` (names without '-' or spaces, every muscle's full gain, bias and dynamics parameters, a body with
several joints split into 1 g wrappers, Euler written out, the floor gone).

- A fix here exists because Newton builds the file differently from MuJoCo's compile (#60): its test builds a small
  wheel-shaped body in both and holds them equal. A muscle whose name holds '-' is not written in full
  (`full_muscles` looks the renamed name up in the compile of the old names); MyoFullBody's muscle names have none.
- Its test runs in Newton's own Python by subprocess and prints `skipped` where no env is built.
