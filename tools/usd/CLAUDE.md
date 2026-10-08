# tools/usd/

The framework's canonical scene: one OpenUSD stage per place (PRD #1, first task), which Blender and other engines
load. `export.py` is the way in (its docstring has the layout of a stage); `views.py` is the Blender adapter's check
against the place's recorded game shots; the script Blender runs is `../blender/inside/usd_views.py`.

- **Two layers, one rule.** The base layer (`layers/base.usda`) and the assets are the framework's: rewritten whole
  on every export. The edit layer (`layers/edit.usda`) is the creator's: made empty once, never written by the
  framework again. Edits survive only because objects keep their names (`<row>_<n>`, the layout's order); never
  rename an object or reorder how names are given without a migration of every edit layer.
- **Converted, not referenced.** glTF geometry becomes UsdGeomMesh with UsdPreviewSurface materials and PNG maps:
  usd-core and Blender read no glTF inside USD. Parts are GeomSubsets named after their library surface.
- **No fake data.** What is not known is not written: mass and friction are absent until the framework records
  them; a model without labelled parts gets one baked material and no surfaces.
- Stages are written outside the repo (`~/.farm-factory-props/work/usd/<place>/`); nothing generated is committed.
- usd-core (Pixar's OpenUSD) is under the Tomorrow Open Source Technology License 1.0: Apache 2.0 with a different
  trademark clause; commercial use allowed.
- Blender only through `../blender/session.py batch` (no window, the machine's lock, the memory floor). A heavy local
  step runs under `systemd-run --user --scope -q -p MemoryMax=16G`.
- **The ground is the game's arithmetic, repeated.** `ground.py` stands each object as 2099's MadePlace does (a seat
  of its own under its spot on the 220 m ball, lifted by its `at` y off the planned ground there) and makes the
  `/<place>/Ground` mesh; the plan and each place's seat are `data/ground/<ground>.json` (the heights and skin copied
  from the game). Change it only with the game's Seat, Ground and MadePlace, or the stage and the game stop agreeing.
- **Children are child prims.** An object standing on another (the layout's `children`) is `<parent>/<row>_<n>`, its
  transform where the parent's composite (`data/library/composites.json`) puts it, so moving the parent moves it.
- **Parts by the run's records.** `--work` reads the take `plan-route.json` names; `--parts` takes each model's newest
  take of any name (`-r1`, `-s1`). Never guess a take name.
- `resting.py` is the scene check (floating, tipping, sunk; hung rows exempt by their inventory `anchor`); its
  `--settle` is the ground snap, writing the settled lifts into the layout (inventory and kit), never into a stage.
- `export_test.py` checks the edit survival, the parts, the units, children and the parts lookup on places made in the
  test itself; `resting_test.py` checks the resting check and the planned ground the same way.
