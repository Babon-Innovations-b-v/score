# tools/props/smoke_beat/

The 2099 prologue's smoke beat's library pieces built in code (#152): `cigarette.py`, the cigarette as a score_lib
model at a king size cigarette's measures (its docstring names their source), its parts the filter, the paper, the
ember (the glowing burn line) and the ash, each finished by a library surface (`FINISHES`: a score_lib recipe in a
colour, the recipe's roughness and glow from `data/library/materials.json`), written as USD (a look a part) and as a
GLB (a mesh and material a part, named after it) for the game. Plain CPU, no card.

- Measures come from a cited source in the docstring; a measure no source gives is named there as the builder's own.
- Taken into score_lib with `score-lib take-in` (a model entry, its `.usdc`, `.glb` and its `.json` record).
- Test: `test_a_cigarette_stands_at_its_measures_in_its_parts.py`.
- Its smoke (`wisp/`) and the hand holding it (`hold/`) are modules of their own, each with its overlay.
