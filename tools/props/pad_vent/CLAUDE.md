# tools/props/pad_vent/

The 2099 prologue pad's cryogenic venting before launch (2099 #161): `vent.py` bakes the launch's footage-measured
venting (carried from score git `e9e8cc813:data/effects/launch.json`, `lox_vent` and `foot_vapour`) with the particle
effects algorithm (`tools/usd/effects.py`) into two score_lib effect entries, each `effect.usda` (default prim /vent,
the emitter at its root, y up), the `clip.usdc` it plays and `settings.json` (the record, its footage, each check's
measure). Scaled to place/pad@10's 48 m rocket; the changes from the record are named in the docstring as the
builder's own. Plain CPU, about 15 s.

- Never widen a footage range to pass: the bake is refused when any sample of a loop misses one.
- Taken into score_lib with `score-lib take-in` as `effect` entries; the game stands them on the rocket (2099
  game/effects).
- Test: `test_the_venting_meets_its_footage_at_the_pads_rocket.py`.
