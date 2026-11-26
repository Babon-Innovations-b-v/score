# tools/props/moon_dust/

The 2099 prologue's Moon landing dust: `dust.py` bakes the footage-measured landing dust sheet (carried from score git
`f46ea0f27^:data/effects/wreck.json`, its checks read off the Apollo descent films and the papers measuring them, and
that commit's `rise` measure) with the particle effects algorithm (`tools/usd/effects.py`) into a score_lib effect
entry: `effect.usda` (default prim /dust, the emitter 0.15 m over the ground under the engine, y up), the `clip.usdc`
it plays and `settings.json`. Its cards fall at the Moon's own pull (the builder's change, in the docstring). Plain
CPU, a few seconds.

- Never widen a footage range to pass: the bake is refused when any sample of its loop misses one.
- Taken into score_lib with `score-lib take-in` as an `effect` entry; the game plays it while the engine fires near the
  ground.
- Test: `test_the_landing_dust_hugs_the_ground_as_the_apollo_films_measured.py`.
