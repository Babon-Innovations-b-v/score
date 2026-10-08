# tools/usd/

The framework's canonical scene: one OpenUSD stage per place (PRD #1, first task), which Blender and other engines
load. `export.py` is the way in (its docstring has the layout of a stage); `views.py` is the Blender adapter's check
against the place's recorded game shots; the script Blender runs is `../blender/inside/usd_views.py`.

- **Two layers, one rule.** The base layer (`layers/base.usda`) and the assets are the framework's: rewritten whole
  on every export. The edit layer (`layers/edit.usda`) is the creator's: made empty once, never written by the
  framework again. Edits survive only because objects keep their names (`<row>_<n>`, the layout's order); never
  rename an object or reorder how names are given without a migration of every edit layer.
- **A third layer for characters.** A place with a cast has `layers/characters.usda` (`../characters/cast.py`)
  between the edit layer and the base; `write_root` keeps it there when it exists. It is the characters stage's, never
  written here.
- **Converted, not referenced.** glTF geometry becomes UsdGeomMesh with UsdPreviewSurface materials and PNG maps:
  usd-core and Blender read no glTF inside USD. Parts are GeomSubsets named after their library surface.
  The parts come from `data/parts` (`../props/library/stored_parts.py`: a stored sample of each labelled take, by
  `models.json`), never from a work or tmp folder.
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
- `resting.py` is the scene check (floating, tipping, sunk below its contact points, one piece inside another; hung
  rows exempt by their inventory `anchor`, fixed rows not judged for tipping, two fixed rows may be joined). Never put a fault right by lowering a piece: settle it.
- `settle.py` is the physics settle: loose rows dropped in headless Blender (`../blender/inside/settle_stage.py`) on
  the stage's ground with their own triangles (cut down), `"fixed": true` rows static, and the rest pose written into the layout
  (inventory spot and kit piece: `x`, `z`, the lift `y` and a `rotation` quaternion [x, y, z, w] in the piece's own
  seat frame, which replaces `facing` and `tilt`). Settling only corrects: a piece that would turn more than 15° or
  drift more than 30 cm (small debris, no side over 1.4 m: any turn, 1 m) keeps its laid pose and is marked `unrested` (the check fails it as "would not rest as laid"),
  because the concept's composition is the owner's; put its layout right instead. Loose pieces collide with the
  ground and the static pieces only (convex hulls over hollows rested on debris). `--cloud` runs it on a rented
  machine. `ground.py level <place>` levels a place's yard in the plan; `ground.py dent <place> <piece>` cuts a
  shallow bowl under a piece (a thrown sphere, a section's impact) so it rests where it was laid.
- `export_test.py` checks the edit survival, the parts, the units, children and the parts lookup on places made in the
  test itself; `resting_test.py` the resting check and the planned ground; `settle_test.py` the settle's write-back
  (a pose round-trips through the layout and the export) and the levelled yard, without Blender.
- **The scene record** (`data/scene/<place>.json`, read by `scene.py`) is what the game drew in its own code and no kit
  piece covers: room shells and the building round a room, stairs and stepped floors, the gameplay objects it places
  from code (a world's own model file, `glb_asset.py`), the ground past the place and Mars's or the Moon's ball, the
  water, the far backdrop, other places seen from this one (their own stages referenced), every light (UsdLux, the
  game's numbers kept as `score:game:*`), the sky and the exposure, and the cameras the place is judged from with the
  game's shot from each. Its geometry comes only from the code builders in `builders.py` (plain numbers in, meshes
  painted with library surfaces out); add a builder there, never a mesh in a record. Every entry says where in the game
  its numbers came from (`from`), and what the game draws that the record does not carry is listed in `game_only`.
- **Light units.** The stage's lights are in Blender's USD reader's units (a sphere light's watts its intensity times
  pi, a distant light's strength its intensity times 4), from the game's energies by `scene.SUN_PER_ENERGY` and
  `OMNI_PER_ENERGY`, and a lamp's energy matched halfway out to its range for its own fall-off (`reach_matched`); change those, never a record's energies, when the brightness check against the game's shots says
  the scene is too dark or too bright.
- `export.py --world <the game's checkout>` resolves the files a record names; a walkway tube's kit is laid along the
  record's `tube_length` as the game's TubeKit lays it. `scene_test.py` checks the builders, the lights' units and
  turns, the kit lamps, the tube's laying and every real record.

