# tools/usd/

The framework's canonical scene: one OpenUSD stage per place (PRD #1, first task), which Blender and other engines
load. `export.py` is the way in (its docstring has the layout of a stage); `views.py` is the Blender adapter's check
against the place's recorded game shots; the script Blender runs is `../blender/inside/usd_views.py`.

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json` that names the place, the prim or pattern, what it is, why it is not from the
  library, who allowed it and when. Every finish is a library surface (`data/library`, the ProcFunc recipes and
  palette tokens): never a picture's own texture, a model's baked-in colour, a default grey or anything else; a
  picture-made model keeps its geometry and gets its finish replaced. The library check
  (`score/stages/complete/library`) lists what does not trace; bible `architecture/components`.
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
  `score:effect:*` (kind; look `speck` or `puff`; a puff's card, dust or plain for steam, fog and mist; emitter shape and size; count, rate, lifetime, explosiveness and a
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
  make it cheaper to draw. An emitter can ride a prim of the base (`on`: written as its child), fill a room
  (`room`: a box over the scene record's floor to its ceiling), follow a motion's
  climb (`follows`), play once at its own seconds (`once`, its own `samples` a second) or light at a second
  (`starts`); a record's `interiors` (the camp's domes) hold no particle of an emitter under the open sky; a record's `lights` ride a prim with keyed intensity (usd_views keys a light on a moving prim where it
  stands). An entry the game never drew names the real footage it was measured on (`footage: <source id>`, listed
  in its record's `footage` block). The effects stage (`score/stages/effects`) is the way in for the places it
  covers.
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
- **The sky is the game's arithmetic, repeated.** `orbits.py` is 2099's Orbits (the Moon's and Earth's middles, the
  Moon's facing at a base minute); a record's stars `turn` (a minute, and the `site` or the place's `seat` axes) turns
  the field as sky.gd's `_stars_turn` does. The minute is measured on the game's own shots (`star_turn.py`: the field
  identified on each and its turn fitted to the facing), never typed by eye: on the Moon the stars wheel round once in
  under seven real minutes, so each shot holds its own moment. `orbits_test.py` checks the orbits against the game's
  measured Earth heights, `star_turn_test.py` the measure on a shot made in the test.
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
  Its ground is the stage's `Ground`, or the made ground's fine patch (`MADE_GROUND`, `/<place>/Outside/near`) where
  the terrain stage's layer turns the old Ground off; the drop stands on the same (`settle_stage.py` GROUND_NAMES).
  Before 2026-10-12 both read y = 0 there.
- `placeholders.py` is the placeholder check: nothing visible stands in for a made piece. Every mesh a scene record's
  code builder drew says which plain thing it is (`plain`: plate, pipe, trim, shell, ground, soil, water or sky; the
  ground's and water's groups by their kind) or fails, whatever the builder, a primitive or one that puts a thing
  together (the hangar's ship_hull, passed by default until 2026-10-11); only the shell builders (`SHELL_BUILDERS`)
  pass without saying, and a new builder is judged until it is put on that list; a kit piece built in code must be
  a kind the sorter sends to code; a mesh with no material or in the default grey, and a proxy, fail. Never mark a thing with detail plain to pass it: make it.
- `complete.py` is the completion gate: `check <place>` runs the checks and keeps each result beside the stage
  (`checks/<check>.json`, tied to the stage's fingerprint), `done <place>` writes `manifest.json` and passes only when
  every requirement passes (rows made or dropped with a written reason, made-only, placeholders, resting, picks, boxes,
  every result current, the review page built and rendered from this stage, and the contents checks). Unknown blocks
  like fail. It reads the place's named gaps (`data/checks/gaps/<place>.json`) as the runner's complete row does,
  with `score/stages/gaps.py`'s own code: a check's faults a gap names pass that check, said by name, and the
  `named gaps` requirement fails each gap by name; a fault no gap names still fails. Reach runs and shows on the manifest but is experimental (`EXPERIMENTAL`): its faults are not counted (it
  fails backdrop rows nobody walks to), only that it was recorded on this stage. The runner's complete stage
  (`score/stages/complete`) runs these same checks on the place's assembled stage: one gate, two ways in. The Stop
  and SubagentStop hooks (`.claude/hooks/completion_guard.py`) refuse a session's or sub-agent's "done" for a place it
  worked on unless the gate passes.
  Export writes `inputs.json` (what the stage was made from, each model by hash); keep it, the gate reads it.
- `contents.py` is the gate's contents checks (its docstring has each): people against the cast (every look a made
  model of the people prop route, never SOMA's mesh in drapes), effects and motions against the needs in
  `data/checks/contents.json` (from the world 1 checklist), crop density where crops apply, every generated row held
  to its close-up (likeness@<place>) and repainted (surfaces-check@<place>), the light and sound layers, the shown
  places, and no record citing the game. A place `contents.json` does not list is unknown; one listed `part_of`
  another (the garage's and hangar's door leaves, gdoor and hdoor) is judged on people, light, sound and neighbours
  on its host's stage, which shows it. `contents_test.py` checks each both ways.
- `triage.py` is the resting triage over `resting.py`: each object judged by its support from data (row `support`,
  `fixed`, kit shell groups and kit kinds `hangs`/`floors`, `on:` held, hanging words, wall, ceiling, floor;
  `data/checks/resting.json`), SceneEval's guards (4 contacts and the weight inside them; one contact for wall, ceiling
  and hanging; an overlap counts only if it survives a 5 mm nudge), bedding classes as data, SAGE's drop rule from a
  settle run (`settle.py --dry-run`: over 0.2 m or 8 degrees is unstable), and real faults grouped by cause with a
  close-up each (`--closeups`). False alarms are kept, marked, never deleted. The gate's resting requirement is its real
  faults. A floor or held object (not of a bedding class) is also judged foot by foot (`../props/library/feet.py`: its
  surface within 10 cm of its lowest point sampled densely and clustered, `foot_clusters`; a foot over 3 cm off while
  another touches is real, since four contact points can lie on three feet; on 600 sparse points a side wall fell
  apart into "feet" up to 10 cm off, 2026-10-12; a foot is down when any of its sole touches) and by its lean. An
  object whose lowest points touch nothing is read again by the points nearest what is under them
  (`nearest_points`: a hull lying across a crater's rim touches 15 cm over its lowest point) (its own up over 3 degrees from the plane under what it touches); a row that says `leans`
  (laid tilted on purpose: the wreck's debris, captain 2026-10-12) is asked neither:
  the greenhouse's water tank stood 7.5 degrees tipped, a foot 7 cm up, and passed before (2026-10-12).
  On ground sloping over 1 degree under an object standing on it (`ground_plane`) its footing and feet are read by
  height over the ground's plane, not straight up (read straight up, the campgrounds' reactor flush on a 6.6 degree
  slope touched along its downhill edge and tipped by 0.8 m, 2026-10-15); level ground and decks read as before.
- `collide.py` is the collision queries (python-fcl and trimesh; one tree per model and scale): collision set,
  intersection test with an offset, distance, touches, raycast. ProcFunc's interface; its release has no such code yet.
- `snap.py` is placement by snapping, for agents laying a place instead of hand coordinates (ProcFunc's idea, not in
  its release): `down` drops an object onto the first surface under its footprint (ground, objects, the scene
  record's Structure and Fixtures) to rest 2 mm over it; `to x,z ...` slides it along each way in turn until it
  stops 2 mm short of a wall or neighbour; `free xmin,zmin,xmax,zmax --seed N` tries seeded spots, drops each, and
  keeps the first that collides with nothing (collide.py) and passes triage's floor support rule. It prints the
  proposed pose; `--write` writes it into the layout with settle.py's pose helpers (no settle limits: a snap is a new
  laid pose, and a stale `unrested` mark goes). Export again and run the checks after. `snap_test.py` checks it.
- `camera_paths.py` is a review walkthrough camera's path: RRT* at eye height (1.6 m over the first surface under each
  point: ground, Structure, Fixtures or an object such as a kit room's floor plate, never a person; a step rising or
  dropping more than a stair's 0.6 m is not taken) from a start to a goal or round a loop of waypoints, an edge valid
  only when every point of it, its ends too, keeps the clearance (0.25 m) from the meshes, the place's people and its
  movers (a ball swept along it in FCL; the people and what the motion layer moves, a rover or a hatch's leaf, as
  solid boxes where they stand at the moments asked for, so one who walks or drives is followed: the garage's rover
  drove through a film's camera planned on the stage at rest, 2026-10-18), seeded, cut short where straight edges are clear, and laid out as the review walk's views (renders.py's
  format: `walk-NNN`, eye, aim, up, fov, look_only). FCL drops a triangle with no area from its tree: it takes any
  eye to touch one. `clearances` measures an eye's distance from the meshes and the people; the demo's film checks
  use it on every frame. renders.py does not read it; a caller hands the views to `renders.render_stage` and
  `walk_video`. The demo's place films (`../review/demo.py`) walk every shot with its `leg` (a clear straight edge,
  else RRT*). `camera_paths_test.py` checks a path between two rooms goes through the doorway only, a walking person
  and a moving thing are followed, and the clearance is measured on every side.
- `reach.py` is the gate's reach check, the automatic playtest (owner, 2026-10-05; the interact press waits for
  interactable assets): the cast check's walker (body radius, knee, head) on a Recast-style heightfield of the stage
  (spans from upward faces, cleared overhead, eroded by the body, joined by climbable steps), its floor the part the
  scene record's views stand on; a row passes when a standing spot lies within body plus arm of one of its objects.
  Experimental: a row it cannot reach shows as a fault but does not fail the place until the owner sets the scenery
  rule and it has caught a real unreachable row that was then fixed; a row with no object is unknown. Measure a fault with it, never move a
  piece by eye to pass it. `reach_test.py` checks a doorway, a shut pen, a stair and the gate.
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
  (picture, hash, source); the lock does not read it. An object the surface stage repainted carries the baked file's
  hash and `score:repaint_of` (the seed's, the model its bake repainted: the assembly's `stamp_baked_hash`); the lock
  reads `repaint_of` first, since a pick chooses the model, never its old paint. The rule itself is `pick_lock.py`
  (what export imports) and the inputs record and hashes `stage_inputs.py`, apart from `picks.py`'s stage check and
  `complete.py`'s checks, so editing a check moves no export's, terrain's or effects' code version (`stages_test.py`);
  the assembly, triage, settle and compare.py read those helpers from `stage_inputs.py` too, so a gate edit moves
  only the runner's complete row. The hash covers a model's .gltf and buffers, not its texture
  files, so a repaint that keeps the file names is not caught.
- `compare.py` is the render-and-compare: each object with a close-up rendered alone from 8 ways round it, the best
  outline standing for the close-up's camera, scored by outline overlap and DINOv2 likeness (`../props/cloud/similar.py`).
  Experimental, a candidate check: no gate reads it and it has not yet failed a known-bad model; it is proven when it
  ranks a model from the fault corpus worst.
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
  shallow bowl under a piece (a thrown sphere, a section's impact) so it rests where it was laid. A tip over 3 degrees
  onto feet that do not lie in one plane in the model's own frame (`uneven_feet`) is never written either: it is the
  model's fault (the surface stage's paint levels a take's feet), marked `unrested` with the feet's spread.
  A loose piece standing on its feet on sloping ground rests flush on the slope (`flush_on_slope`: its up along the
  ground's normal, heading kept, let down to touch), whatever the drop of the seed's model did: the paint levels the
  bake's feet, so on the slope's plane every one touches (the campgrounds' crane, 17 degrees on its seed's feet).
  A drop that finds rest poses (`drop_job(upright=True)`: settle.py's write, the settle stage) starts each loose piece
  stood upright in its seat (`upright_starts`: an old settle's tip of up to 15 degrees is no pose to drop from; a row
  that `leans` or may bed in starts as laid), and a piece stacked on another loose one meets it (`stacked_under`: a
  crate on a crate fell through it to the floor), starting wholly over the one support it overlaps most
  (`onto_one_support`: a crate laid across two rested with a skid 99 cm in the air). A drop that judges the laid pose (`--dry-run`, the assembly's
  resting evidence) starts as laid. `rest_poses` is the settle stage's write: the same limits, the rest as matrices;
  `score/stages/settling/held.py`'s `held_rests` snaps held ones onto their holders (a level spot within 30 cm when the straight snap leaves one
  leaning), `fixed_let_down` lets a floating fixed one down. A cloud drop of the very same job, drop script and stage
  is read back from a cache (`simulate(cache=...)`, `drop_key`), never bought twice.
- `export_test.py` checks the edit survival, the parts, the units, children and the parts lookup on places made in the
  test itself; `resting_test.py` the resting check and the planned ground; `settle_test.py` the settle's write-back
  (a pose round-trips through the layout and the export) and the levelled yard, without Blender.
- **The scene record** (`data/scene/<place>.json`, read by `scene.py`) is what the game drew in its own code and no kit
  piece covers: room shells and the building round a room, stairs and stepped floors, the gameplay objects it places
  from code (a world's own model file, `glb_asset.py`), the ground past the place and Mars's or the Moon's ball, the
  water, the far backdrop, other places seen from this one (their own stages referenced), every light (UsdLux, the
  game's numbers kept as `score:game:*`), the sky and the exposure, and the cameras the place is judged from with the
  game's shot from each. Its geometry comes only from the code builders in `builders.py` (plain numbers in, meshes
  painted with library surfaces out); add a builder there, never a mesh in a record. A record entry that is an
  inventory row's piece names it (`row`: a structure's code-built piece, an object's made model), so the rows check
  and the pick lock find it. Every entry says where in the game its numbers came from (`from`), and what the game
  draws that the record does not carry is listed in `game_only`.
  What the owner took out for good is `owner_rejected` ({what, names, date, why}); `scene.refuse_rejected` keeps
  those names out of the record, the kit's rows and the effects record, so a later port from the game cannot bring
  them back. Never take a name off that list without the owner's word, and never put on it what the owner did not
  reject: what the coordinator takes out with it (it stood on a rejected thing) is `coordinator_removed`, not refused.
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
  shore, laid out as every place's stage (`layers/base.usda` rewritten, `layers/edit.usda` kept, `inputs.json`); each
  kind's prototype names its launch inventory row (`score:row`), so the launch view's rows check finds the made kinds.
  The flat, the street, the square and the launch view reference it through a `places` entry; it refuses to write
  while a tower kind has no made model, so no stand-in tower is ever shown.
- **The sound stage** (`sound.py`) writes `layers/sound.usda` only (UsdMedia.SpatialAudio: room tones from
  `data/sound/places.json`, objects' own sounds from their inventory rows, motions' sounds from `data/motion`, and
  a bank of surface sounds each library surface points at) and copies the files into `assets/sound/`. Levels come
  from `data/sound/catalogue.json` with `sounds.json` over it. It never writes the base. `soundtrack` mixes what a
  camera hears; nothing calls it since 2026-10-18 (`hearing.py` replaced it; it goes the next time sound.py changes
  for its own sake, since sound.py is in the assembly's, settle's and motion's code and an edit runs them again).
- **What a camera hears** (`hearing.py`, the review's walk and the demo's films): **every track is mixed at one gain**
  (MIX_GAIN_DB, a soft limit under the ceiling), never brought to a loudness of its own (until 2026-10-18 each shot was
  pressed to -24 dBFS, so the lift-off played as loud as a cabin). A placed sound plays at its level within Godot's
  10 m unit size (its `near` in sounds.json where it names one), a shown place's room tone is not heard from the place
  showing it, outside only what the boots feel carries, and the walker's footsteps come from the floor under the eye.
  `bed` is what the camera hears standing before a shot: the film's title card and the showcase's cards carry it, so
  no card is silent. Keep the mix out of sound.py for the reason above.
- **The motion stage** (`motion.py`) writes `layers/motion.usda` only: time samples on prims the base already has (a
  door's translate, a light's intensity, a turntable's rotateY; a kit piece keeps its own transform under the slide's
  outermost translate), as overs, from `data/motion/<place>.json` (each motion's prim, its cycle:
  start, length, loop, its game numbers with a `from`, and the sounds the game plays with it for `sound.py`). A thing
  the game moves but the base does not draw while it rests (the airlock's sunk inner door, a dark warning light) is
  the motion's `adds`, the layer's only defs. A game motion keeps the game's own speeds and lengths; a rest
  the player's pace decides is the record's and says so. `motion_test.py` checks it without Blender.
- **Movers** (`movers.py`, experimental): what the game left standing set moving in its place from
  `data/movers/<place>.json` (a closed path, a swing on a hinge, a spin, or a motion record's slide), written into the
  same `layers/motion.usda` with the game's motions over a stage folder's own layers. Every number has a source (its
  `from`; the kind's speed range in `data/checks/motion.json`); the motion stage (`score/stages/motion`) gates it.
- **Framework shaders** (`shaders.py`): a surface the library's flat colour cannot carry gets a UsdPreviewSurface
  over a picture the framework bakes (`earth_face`: `earth.py`, NASA's Blue Marble and cloud cover, the real
  planet; a record's Earth turned by `placed_turn` so its equator and Africa face the place, as photographs from the
  Moon show it), bound under `/<place>/Looks/` when the stage's folder is known (in the ground group too); the sun's
  disc is a ball along each unnamed sun light. Add a shader to `LOOKS`, never a picture by hand.
- **Lamps' shafts and the day sky** (2026-10-11, experimental until `score/stages/light` passes): a spot light with a
  `shaft` fills its own cone, its `length` out from the lamp, with haze only the lamps light (`write_shafts`,
  `/<place>/Shafts`, kept when another place shows this one); a record's environment `sky_dome` is the air past the
  place's thin haze, `mars_sky.py`'s single scattering of a dust layer for the place's sun, on a ball between the
  sun's disc and the stars that the eye and mirrors see and nothing is lit by. Their strengths are measured against
  the concept on rendered views (the light stage's sweep), never set by eye.
