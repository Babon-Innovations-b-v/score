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
- `export_test.py` checks the edit survival, the parts and the units on a place made in the test itself.
