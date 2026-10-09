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
- **The effects layer** (`effects.py`, `layers/effects.usda`, between the edit layer and the base with the other stage
  layers): a place's particle effects from its record (`data/effects/<place>.json`, every entry with its game `from`),
  each emitter written twice. The schema is an Xform `/<place>/Effects/<emitter>` in the emitter's own frame carrying
  `score:effect:*` (kind; look `speck` or `puff`; emitter shape and size; count, rate, lifetime, explosiveness and a
  burst's period; direction, spread, flatness, speed; gravity in the emitter's frame; damping, radial push,
  turbulence; size, scale and size over life; linear colour, opacity and opacity over life; a puff's near fade; the
  wind it follows in the place's frame; spin; world or local space; seed; the bake's loop; `from`), which an engine
  adapter makes again with its own particles. Under it a UsdGeomPoints `<emitter>_points` is baked over the loop
  (points, widths, displayOpacity, a displayColor) as a value clip in `assets/effects/<emitter>.usdc`, looped over the
  stage's time, so any USD reader shows the particles without the schema. The bake repeats Godot's
  ParticleProcessMaterial with its own seeded draws: the same record is always the same particles. A record's
  `replaces` makes a base prim inactive that the layer draws moving (the camp's still drift), and a `variant` puts an
  entry in that variant of `/<place>/Effects` (the camp's `weather`: calm, storm). Blender's reader leaves
  displayOpacity out, so `../blender/inside/usd_views.py` draws the effects itself, frame by frame. Effects are
  fine and many (the owner's rule: real footage first; big or sparse particles read as dots): never thin a record to
  make it cheaper to draw.
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
- `placeholders.py` is the placeholder check: nothing visible stands in for a made piece. A scene record's box,
  quad, disc, round wall, lathe, sphere or torus says which plain thing it is (`plain`: plate, pipe, trim, shell,
  ground, soil, water or sky) or fails; a kit piece built in code must be a kind the sorter sends to code; a mesh
  with no material or in the default grey, and a proxy, fail. Never mark a thing with detail plain to pass it: make it.
- `complete.py` is the completion gate: `check <place>` runs the checks and keeps each result beside the stage
  (`checks/<check>.json`, tied to the stage's fingerprint), `done <place>` writes `manifest.json` and passes only when
  every requirement passes (rows made or dropped with a written reason, made-only, placeholders, resting, every result
  current, the review page built and rendered from this stage). Unknown blocks like fail. The Stop hook
  (`.claude/hooks/completion_guard.py`) refuses a session's "done" for a place it worked on unless the gate passes.
  Export writes `inputs.json` (what the stage was made from, each model by hash); keep it, the gate reads it.
- `triage.py` is the resting triage over `resting.py`: each object judged by its support from data (row `support`,
  `fixed`, kit shell groups and kit kinds `hangs`/`floors`, `on:` held, hanging words, wall, ceiling, floor;
  `data/checks/resting.json`), SceneEval's guards (4 contacts and the weight inside them; one contact for wall, ceiling
  and hanging; an overlap counts only if it survives a 5 mm nudge), bedding classes as data, SAGE's drop rule from a
  settle run (`settle.py --dry-run`: over 0.2 m or 8 degrees is unstable), and real faults grouped by cause with a
  close-up each (`--closeups`). False alarms are kept, marked, never deleted. The gate's resting requirement is its real
  faults.
- `collide.py` is the collision queries (python-fcl and trimesh; one tree per model and scale): collision set,
  intersection test with an offset, distance, touches, raycast. ProcFunc's interface; its release has no such code yet.
- `snap.py` is placement by snapping, for agents laying a place instead of hand coordinates (ProcFunc's idea, not in
  its release): `down` drops an object onto the first surface under its footprint (ground, objects, the scene
  record's Structure and Fixtures) to rest 2 mm over it; `to x,z ...` slides it along each way in turn until it
  stops 2 mm short of a wall or neighbour; `free xmin,zmin,xmax,zmax --seed N` tries seeded spots, drops each, and
  keeps the first that collides with nothing (collide.py) and passes triage's floor support rule. It prints the
  proposed pose; `--write` writes it into the layout with settle.py's pose helpers (no settle limits: a snap is a new
  laid pose, and a stale `unrested` mark goes). Export again and run the checks after. `snap_test.py` checks it.
- `camera_paths.py` is a review walkthrough camera's path: RRT* at eye height (1.6 m over the ground or Structure floor
  under each point) from a start to a goal or round a loop of waypoints, an edge valid only when its ray and four rays
  offset by the clearance (0.25 m) meet nothing, seeded, cut short where straight edges are clear, and laid out as
  the review walk's views (renders.py's format: `walk-NNN`, eye, aim, up, fov, look_only). renders.py does not read
  it; a caller hands the views to `renders.render_stage` and `walk_video`. `camera_paths_test.py` checks a path
  between two rooms goes through the doorway only.
- **Openings in code builders.** When a builder needs a hole in a wall (a door, a window, a hatch), cut it as a cutout
  of the surface itself in its UV layout (ProcFunc's way: the hole is part of the surface, no boolean of two meshes),
  not a boolean. A note for new builders; the builders in `builders.py` are not changed by it.
- `annotate.py` (Blender side `../blender/inside/annotate_stage.py`) is the one annotate step: from any camera the look,
  per-pixel object ids, depth and normals, and from them masks and occlusion boundaries. Checks call it; never write a
  second renderer for a check.
- `picks.py` is the pick lock: a row's `pick` (model, hash, the decision in words; `models` {name: hash} for a row
  drawn by several models) is written on its objects at export (`score:pick_sha256` beside `score:model_sha256`);
  export refuses a picked row showing another model or none unless the row has `pick_replaced` (the owner's written
  decision). A scene record object that stands for a row names it (`row`) and is locked the same way (the launch's
  rocket). Never write a pick or a replacement the owner did not make; each `decided` names its source (the owner's
  message and date, the page, the log line). An inventory's `concept_pick` records the concept the owner approved
  (picture, hash, source); the lock does not read it. The hash covers a model's .gltf and buffers, not its texture
  files, so a repaint that keeps the file names is not caught.
- `compare.py` is the render-and-compare: each object with a close-up rendered alone from 8 ways round it, the best
  outline standing for the close-up's camera, scored by outline overlap and DINOv2 likeness (`../props/cloud/similar.py`).
- `made_only.py` is the made-only check on the stage: every drawn mesh says what made it (score:model, score:builder,
  score:kind) and every object's model loaded.
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
- A record names a file by its name in the world's release (`models/...`, tools/assets/world.py) or by its path in
  git (`data/...`); `export.py` resolves both (`--assets <folder>` reads another copy of the release), never a file of
  the game's checkout. A walkway tube's kit is laid along the
  record's `tube_length` as the game's TubeKit lays it. `scene_test.py` checks the builders, the lights' units and
  turns, the kit lamps, the tube's laying and every real record.

- `far_city_stage.py` stands the far city up as a place of its own (`<stages>/far_city/far_city.usda`): far_city.py's
  seeded plan with each tower an instance of its kind's made model, the land, the mountains and the harbour out to its
  shore. The flat, the street, the square and the launch view reference it through a `places` entry; it refuses to
  write while a tower kind has no made model, so no stand-in tower is ever shown.
- **The sound stage** (`sound.py`) writes `layers/sound.usda` only (UsdMedia.SpatialAudio: room tones from
  `data/sound/places.json`, objects' own sounds from their inventory rows, motions' sounds from `data/motion`, and
  a bank of surface sounds each library surface points at) and copies the files into `assets/sound/`. Levels come
  from `data/sound/catalogue.json` with `sounds.json` over it. It never writes the base. `soundtrack` mixes what a
  camera hears; the review's walk and the demo's videos use it.
- **The motion stage** (`motion.py`) writes `layers/motion.usda` only: time samples on prims the base already has (a
  door's translate, a light's intensity), as overs, from `data/motion/<place>.json` (each motion's prim, its cycle:
  start, length, loop, its game numbers with a `from`, and the sounds the game plays with it for `sound.py`). A thing
  the game moves but the base does not draw while it rests (the airlock's sunk inner door, a dark warning light) is
  the motion's `adds`, the layer's only defs. Animate only what the game moves, at its own speeds and lengths; a rest
  the player's pace decides is the record's and says so. `motion_test.py` checks it without Blender.
- **Framework shaders** (`shaders.py`): a surface the library's flat colour cannot carry gets a UsdPreviewSurface
  over a picture the framework bakes (`earth_face`: `earth.py`, the game's ink_earth shader in numpy), bound under
  `/<place>/Looks/` when the stage's folder is known; the sun's disc is a ball along each unnamed sun light. Add a
  shader to `LOOKS`, never a picture by hand.
