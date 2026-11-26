# tools/props/launch_exhaust/

The 2099 prologue launch's exhaust: `exhaust.py` bakes the launch's footage-measured flame core, flame, pad fire and
plume (carried from score git `e9e8cc813:data/effects/launch.json`, its flame checks, and the climb of
`e9e8cc813:data/motion/launch.json`) with the particle effects algorithm (`tools/usd/effects.py`) into four score_lib
effect entries, each `effect.usda` (default prim /exhaust, y up), the `clip.usdc` it plays and `settings.json`; the
plume's cards draw the smoke flipbook (`score:effect:flipbook`, tools/props/smoke_card). Scaled to the pad's 48 m
rocket; the changes from the record are named in the docstring as the builder's own. Plain CPU, a few seconds.

- The flames ride the rocket's engines (the game stands them there); the pad fire stands on the pad under them; the
  plume stands at the engines' rest and its particles are let out up the climb.
- Never widen a footage range to pass: the bake is refused when a flame misses its length.
- Taken into score_lib with `score-lib take-in` as `effect` entries.
- Test: `test_the_flames_reach_as_far_under_the_pads_rocket_as_the_footage.py`.
