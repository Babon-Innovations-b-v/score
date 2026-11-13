# score/stages/sim_body/inside/eased/

A clip's start eased before the sim body follows it (2026-11-13; numpy and scipy, its test runs in the score venv).
Kimodo's standing clip starts with a jolt (its segments' mean acceleration 0.5 to 0.7 m/s2 on frames 1 to 3, at most
0.4 after); on frame 2 its right foot carried 0 N and every standing body under Moon gravity held 1.5 to 3.2 N m of
residual moment, over its 1 N m (base, greenhouse, hangar). `eased` steadies the clip's first frames (one steady
acceleration from its first pose to the clip's own place and speed) over the fewest frames, at most `MOST`, that keep
its start within the clip's own largest acceleration after them; a calm start is followed as it came.

- **Never from rest.** A start held at its first pose and blended in (smootherstep) made the body catch up with the
  clip's own drift (its hips already moving 5 cm/s on frame 0): 6 N m and 6 N of residual on base's frames 5 to 23,
  2026-11-13. Keep the clip's place and speed where the ease ends.
- **Only the path the sim body follows is eased.** The stage's `poses` (the drawn person, the peels, people-cloth)
  stay the clip's own.
- **Never loosen the residual limit for a clip's start**: a start the ease leaves over it fails `residual`.
- **A measured trial is never eased**: LabValidation's job sets `"eased start": false` (`tools/labval/_job.py`); its
  first frame is a measurement, not a jolt to smooth.
