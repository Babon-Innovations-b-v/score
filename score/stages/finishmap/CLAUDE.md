# score/stages/finishmap/

The re-test of the surface stage's finish-map method (its code is `../surfaces/`, its overlay there) on round 4's six
models, as world-grain rows (`trial.py`, `python -m score.stages.finishmap.trial status|run|why`): the stage's own
method rows run on the six takes, round 4's paid turntable read back instead of rendered again. First run 2026-10-11
with the owner's approval (EUR 15); the owner then made the method the surface stage's (2026-10-12).

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json` that names the place, the prim or pattern, what it is, why it is not from the
  library, who allowed it and when. Every finish is a library surface (`data/library`, the ProcFunc recipes and
  palette tokens): never a picture's own texture, a model's baked-in colour, a default grey or anything else; a
  picture-made model keeps its geometry and gets its finish replaced. The library check
  (`score/stages/complete/library`) lists what does not trace; bible `architecture/components`.
- **Rows, not scripts**: fm-lists, fm-maps and fm-segvigen are paid and cleared by the runner; fm-inputs,
  fm-turntable and fm-parts are free. Nothing spends outside the runner.
- **Measured, never judged by eye**: fm-parts' `parts.json` holds each take's agreement with every map on the faces
  its view sees, the parts mixing two finishes and the part count; its front and back pictures are part maps. The old
  texture-made reference (round 4's `measure.py`) is circular for a texture method and is no verdict here.
- Checks: `finishmap_test.py`.
