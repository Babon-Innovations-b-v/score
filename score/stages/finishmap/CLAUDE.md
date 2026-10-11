# score/stages/finishmap/

The re-test of the surface stage's finish-map method (its code is `../surfaces/`, its overlay there) on round 4's six
models, as world-grain rows (`trial.py`, `python -m score.stages.finishmap.trial status|run|why`): the stage's own
method rows run on the six takes, round 4's paid turntable read back instead of rendered again. First run 2026-10-11
with the owner's approval (EUR 15); the owner then made the method the surface stage's (2026-10-12).

- **Rows, not scripts**: fm-lists, fm-maps and fm-segvigen are paid and cleared by the runner; fm-inputs,
  fm-turntable and fm-parts are free. Nothing spends outside the runner.
- **Measured, never judged by eye**: fm-parts' `parts.json` holds each take's agreement with every map on the faces
  its view sees, the parts mixing two finishes and the part count; its front and back pictures are part maps. The old
  texture-made reference (round 4's `measure.py`) is circular for a texture method and is no verdict here.
- Checks: `finishmap_test.py`.
