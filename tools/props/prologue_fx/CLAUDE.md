# tools/props/prologue_fx/

The 2099 prologue's water effects the lay plans miss (2099 #161): `fx.py` bakes the drips off a street awning's front
edge in heavy rain and the white water behind the pad's speedboat with the particle effects algorithm
(`tools/usd/effects.py`) into two score_lib effect entries, each `effect.usda` (default prim /effect, the emitter at its
root, y up), the `clip.usdc` it plays and `settings.json` (the record, its sources, each check's measure). Every
number is a published measurement (the drop's pinch-off volume filmed, its end speed, the wake angles off airborne
images) or a builder's own choice named in the docstring. Plain CPU, a few seconds.

- Never widen a footage range to pass: the bake is refused when any sample of a loop misses one.
- Taken into score_lib with `score-lib take-in` as `effect` entries; a place lays them with `put` under Effects.
- Test: `test_the_water_effects_meet_their_footage.py`.
