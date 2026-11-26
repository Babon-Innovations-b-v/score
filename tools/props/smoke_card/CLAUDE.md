# tools/props/smoke_card/

The billowing smoke flipbook (the 2099 prologue's launch smoke; the owner: "this smoke ... is shit"): `billow.py` (run inside Blender)
simulates one puff of smoke with Mantaflow (Blender's gas solver) and renders it six-way lit with Cycles on the
processor; `card.py` packs the frames into two 4 x 4 atlases and the score_lib surface `smoke_billow` (family
`flipbook`, its `surface.json` the layout and the solver's settings). An effect's puff cards draw it instead of a soft
round card (`score:effect:flipbook` on the effect's root, tools/props/launch_cloud).

- Blender only through `tools/blender/session.py batch` (`card.py render`), on the processor (`cycles.device` CPU):
  the graphics card stays free. About 4 minutes at the full settings (2026-11-26, this PC).
- A made flipbook is a simulation, not footage; the effects that draw it keep their own footage checks.
- Taken into score_lib with `score-lib take-in` as a `surface` entry (atlases, material.usda, preview.png,
  surface.json).
- Test: `test_each_side_lights_its_own_channel_of_the_atlas.py` (the pack; the render is not run in a test).
