# tools/props/launch_cloud/

The 2099 prologue launch's cloud at ignition: `cloud.py` bakes the launch's footage-measured ground cloud, its billows
and the deluge's steam (carried from score git `e9e8cc813:data/effects/launch.json`, with its footage checks) with the
particle effects algorithm (`tools/usd/effects.py`) into three score_lib effect entries, each `effect.usda` (default
prim /cloud, the emitter at its height over the rocket's foot, y up), the `clip.usdc` it plays, `settings.json` (the
record, its footage, each check's measure) and the smoke flipbook's atlases its cards draw (`score:effect:flipbook`,
tools/props/smoke_card). Scaled to the pad's 48 m rocket; the changes from the record are named in the docstring as the
builder's own. Plain CPU, about 20 s.

- The three are measured together (the footage's cloud is all three); never widen a footage range to pass: the bake
  is refused when any check misses.
- Taken into score_lib with `score-lib take-in` as `effect` entries; the game plays them once from the engines' light.
- Test: `test_the_launch_cloud_meets_its_footage_at_the_pads_rocket.py`.
