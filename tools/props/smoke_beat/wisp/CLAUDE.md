# tools/props/smoke_beat/wisp/

The cigarette's smoke (#152): `wisp.py` bakes the flat's footage-measured wisp (carried from score git
`c3ef49db0^:data/effects/flat.json`) with the particle effects algorithm (`tools/usd/effects.py`) into a score_lib
effect entry: `effect.usda` (default prim /smoke, the emitter standing at the lit end, y up), the `clip.usdc` it plays
and `settings.json` (the record, its footage, each check's measure). Plain CPU, under a second.

- Never widen a footage range to pass: the bake is refused when any sample of its loop misses one; a number changed to
  meet them is named in the docstring as the builder's own (the 16 degree launch cone).
- Taken into score_lib with `score-lib take-in` as an `effect` entry; place_build's `put` lays it under Effects.
- Test: `test_the_wisp_rises_off_its_lit_end_as_its_footage_measured_it.py`.
