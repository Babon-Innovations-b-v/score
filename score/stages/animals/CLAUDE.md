# score/stages/animals/

The animal rows (experimental, #52; `__init__.py`'s docstring has the rows, gates and prices). This is part of the
motion layer's bodies module (CONTEXT.md "motion"). Every scene inventory row whose kind roams (an animal,
`data/checks/row-kinds.json`) gets `animal-body-<row>` and `animal-clips-<row>` at each place whose design shows it.
They are made by `tools/characters/animals/route.py`'s steps (its overlay): Pixal3D, UniRig for a four-legged
animal, then Blender on one held cloud machine.

- **From the design alone.** The rows, the body (fish or four-legged, by the kind's `fish` nouns), the length (the
  row's metres) and the picture (the row's box of the locked concept, widened by `MARGIN`) come from the place's kept
  inventory and its locked concept. Nothing is written per scene, and no environment or scene is named.
- **No measured price.** No stage has made an animal yet. `BODY_EUROS` and `CLIPS_EUROS` are guesses that the runner
  keeps apart. Replace them with `data/costs/per-unit.json` entries once a run is measured.
- **Not yet laid into a place.** The assembly takes no animal layer (`assembly.NEEDS` has none) and
  `stages.MOTION_LAYER` does not list these rows, because its test refuses a pattern that matches no row and no
  design shows an animal today. Both wait for the first animal row a design shows.
- **Look at the frames.** The clips gate only checks that every clip has review frames. Whether a clip works is
  decided by looking at those frames (the route's overlay).
- Tests: `animals_test.py` covers a toy design and a toy table only. Nothing paid runs.
