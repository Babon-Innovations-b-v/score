# score/stages/place_build/

The placing agent's tool (#128, owner 2026-11-16): a place laid by hand from score_lib entries, step by step, until
its render reads as its locked concept (same room, layout, main objects, mood). The agent (a vision model) drives it
one command at a time and reads `compare.png` and the measures to choose the next correction; nothing here judges.

- **A concept's cut is the camera's, never the building's** (owner and the 2099 session, 2026-11-19). Every inside
  place is built closed: walls, roof, floor, and a door shut in each doorway (glass and windows in their openings).
  A concept drawn as a cut-away or section (a front wall missing, a roof lifted off) is a camera's look: build the
  wall, then list it with `cut <folder> <object>` (place.json `cut`), and the preview and the film leave it out of
  the camera's rays alone (blender_views.camera_cut; it still shades), the film's camera path passes it. The walkers,
  the physics check and every game engine (the scene package) get the building whole. The check (ready/) fails an
  inside that sees the sky or the outside through a gap no door, window or glass closes. A cut object is found at render by its prim's path (Blender 5's
  reader names a single-mesh Xform for its mesh), and `remove` drops it from the cut. An outside place is marked
  `kind <folder> outside` (place.json `kind`): the check then judges only its structures' rooms.
- **Everything laid comes from the library.** A withdrawn entry is refused (the owner retired every old model,
  kit, character and surface on 2026-10-21), and the finish check fails one already laid. `put` lays only an entry
  with a USD file (kit pieces, models, the
  sky domes), copied whole under the place's `assets/`; `surface` binds a library surface over everything inside the
  object (a variant's own material, or a recipe in a palette colour), so a model's baked colour never shows; `light`
  lays the library's lamp. No geometry, colour or light is made here outside a library entry.
- **The scene is a plain USD** (y up, metres, `/<place>/Objects|Looks|Lights`) that tools/usd (snap.py, resting.py)
  and sim body read as they read a place: keep that layout, never a Blender file.
- **Render through the card queue only** (`render.py`: usd_views.py, Cycles review samples, a memory-capped scope,
  more than 12 GB free), from render/still.usda: the scene without its walkers' layer (render.still_stage; the films
  draw the people); a long one is started with tools/cloud/detached.py, never waited on in the foreground. The
  X/GL libraries a box's Blender lacks come from `bash tools/blender/setup.sh` (into `blender-mcp/libs`, the default;
  `SCORE_BLENDER_LIBS` overrides it), and an exit 127 names that fix.
- **`start --split` runs SAM 3 free on this PC's card** (score/review/concept_objects.py under SCORE_CLOUD=local and
  SCORE_FREE_ONLY=1, tools/cloud/backends/local.py's segment claim); never a rented card.
- **Every shown part wears a library finish** (finished/, its own overlay): `surface` is refused over the whole of a
  model whose own paint has parts, `refinish` lays it per part from the palette, `put` does so for a model in a paint
  no library surface made, and the check (`check`, ready.json's `finishes`) tells every object that does not.
- **A made shape that reads wrong is remade** (shapes/, its own overlay): a pipe whose section swells along its run
  (a sausage) or a hard made thing with too few flat faces (a lump) is told in ready.json's `shapes`, never kept.
- **Parts.** A kit piece's or model's colour regions are GeomSubsets; `surface --part` binds a surface on one, and the
  object's whole look then goes on every shape and every other part, so no baked colour shows anywhere.
- **glTF-only entries** (our picture-made models and takes) are converted once at `put` (gltf.py): a part a material,
  each wearing its own bake and paint (base colour, metal-roughness and normal maps), a take's `-final` model first;
  `surface` puts a library surface over a part or the whole when a bake is wrong.
- **Characters** are laid as their own SkelRoot (never an Xform over it), dressed in one body group (WORN) and held
  still in a clip with tools/characters/cast.py's own steps.
- **A held prop** (`hold`, #152): a character entry's `pose.json` (tools/props/smoke_beat/hold/) sets a laid,
  held-still character's joints and marks its Held pose `score:pose`; `--prop` lays that object at the pose's hold
  frame of the posed joint (the cigarette in the hand). An `effect` entry (the cigarette's wisp) is `put` under
  Effects, role effect, its record's `usd` root laid, never the clip it plays.
- **The dome shell** (dome_shell.py, `dome`) is code-made: its shell, ribs and deck are parts for their surfaces;
  `ground` lays the same flat disc alone as the place's ground.
  In a batch, a dome's `base` [high, wide] deepens its plinth ring, `oculus` crowns it with a ring where the meridians end, `strips`
  hangs thin lamp bands inside the glass at those heights (part `strip`, for a glowing palette variant).
- **A real ground** (relief.py, `terrain`): a terrain entry is a heightfield model read from a public-domain HiRISE
  DTM (range requests, never the whole file), its own posts near the centre and wider out to the horizon, bent with
  the planet; `terrain --pad x,z,r` levels a building's site to the laid height and eases it into the ground.
- **A tinted image surface**: `surface --colour` over an image surface multiplies its colour map (the texture's
  scale; Blender's reader brings it in as a multiply), so a scanned ground takes Mars' tint and keeps its grain; the
  preview displaces a laid ground by its surface's height map when surface.json names `displacement_metres`.
- **The sky and its sun** (`sky`): a light entry's sky dome laid as the place's own `/<place>/Environment` (the
  renderer's ambient light and exposure) and a distant sun from an elevation and heading, the dome turned (`--turn`)
  so its picture's glow stands where the sun is; never a far sphere lamp.
- **The tunnel** (`tube`): the dome shell algorithm's ribbed glass tube between two domes (parts shell, ribs, deck);
  an end wall's rim is drawn in to the tube's circle, never stepped. A tube's file is cached under the place's
  `assets/algorithm/` by its sizes: delete it there after changing dome_shell.py, or the old one is laid.
- **Standing on things**: `put --rest` lays a piece's lowest point at the given height (a floor, a table top);
  `--on-ground` reads that height over the laid ground there (a rock on a terrain's relief).
- **Doors are marked, never guessed** (`door`, #148): `--opens` the walkers open it, `--slide` it slides aside along
  its face (score:move; a sliding balcony door, a lock's plug door) instead of swinging, `--lock <chamber> --side
  inner|outer` it is a pressure door of an airlock chamber, any laid object closing the chamber's air (a blocks-built
  airlock's shell too: its walls are no dome shell, so no chamber is found without the marks). A pressure door opens
  to its high-pressure side (scene_package.locks_of: the outer one into the chamber, the inner one out of it to the
  base); ready.opening is the one answer to how a door opens, read alike by the walkers' floor, walker_route's door
  times, the film and the scene package's `door` block.
- **Named views** (`view`, `render --views a,b`): inside and low views beside the concept's, their look only. A
  named view sees the building closed; `view --cut` makes it see through place.json `cut` as the concept's does
  (render.views gives each view its own `cut`, blender_views.view_cut applies it per view).
- **Image surfaces** (`surface/ambientcg_*`, CC0 PBR sets taken in with their source in each entry's provenance and
  surface.json) tile at their own `tile_metres` in the preview, box-projected in the object's own frame
  (blender_views.py); a model's bake keeps its own texture coordinates.
- **The preview's Blender script is blender_views.py**, usd_views.py with a laid ground as the ground and see-through
  looks as thin glass, patched in there so the films' and physics' renders (which key usd_views.py) never move.
- **One palette a place** (owner, 2026-11-16: "if u take a bunch of random scans, everything will look very
  inconsistent"): `palette` takes in the place's scene surface library (its surface-library output: ProcFunc recipe
  variants in its palette tokens, the ones its props were baked from) with its wear and dirt; `surface ... palette/<v>`
  lays a variant (its recipe's score_lib entry, the spec on the look) and the preview draws it as its recipe
  (tools/props/library/recipes.py: edge wear, dirt, relief) on the mesh set upright, so shells, floors and repainted
  parts share the props' finishes. The recipes need pandas beside Blender (`$PROPS_HOME/blender-mcp/pf-site`).
- **Physics-ready structure**: `dome --opening around,radius,centre` cuts glass, ribs and plinth where a tube joins
  (a collar rib round it); `tube --cap w,h` closes its far end with a wall holding a doorway (an airlock's door sits
  in it; `--cap-door <door>` cuts that doorway to the laid door's own outline, so a round hatch gets a round one, its
  hinges and latch left on the jamb; lay the door first), `trims` end its skin on the domes' glass, and its skin is solid to WALL_HIGH over its deck (part `wall`).
- **A model's own layers** (`<file>_glow.usdc`, a monitor's screen) are laid with it as children, each a part a
  surface can take (`surface --part glow palette/screen_glow`).
- **`render --final`** renders at the films' samples at 1920x1080; the views take AgX's medium high contrast look.
- **The stair core** (stair_core.py, `stairs`, owner 2026-11-16: "real walkable stairs with landings"): a switchback
  stairwell of real size (0.167 m risers, 0.28 m treads, 1.2 m flights, a waist under each so the flight below keeps
  its head height), every piece a closed solid of real thickness, its faces turned out (the walkers' floor reads a top
  by its normal), the ground slab laid in pieces (MuJoCo let a mat fall through one face across the whole place); its
  doorways cut in its walls with a hall behind each flat's door, railings on every open edge, flats' blocks either
  side and a glazed front. Panes are one face each (a closed pane's two thin-glass skins ring with light). `--one-block` keeps only the
  flats' block the entrance opens into, so a cut-away's far wall stands free to the street and the sky beyond.
  `stairs --curtain` glazes the front as a storey-high curtain wall (only the slab edges and corner piers left), so
  the concept's cut-away look into the shaft is a look through real glass; `stairs --cut` lays the front wall as its
  own object `<name>_front` (stair_core.front_alone) and lists it in place.json `cut`: the shaft stays closed and
  the camera alone sees through its front (the section the concept draws). Every doorway is recorded in place.json
  `doorways` (`<name>_door<k>`, the scene's frame); `stairs --joined <k>` leaves out the hall stub behind storey k's
  flat door, for a place of its own joined there (the flat). `stairs --street-door` cuts a street door in the
  entrance block's facade (`<name>_street`, in place of its ground window nearest the shaft): that ground floor is
  the lobby the entrance opens off, so the stairwell meets the street (#154).
- **A neighbour's part of the concept** (`backdrop <folder> <name>`, place.json `backdrop`; 2099's prologue,
  2026-11-22: the flat carried its own square, crowd, stage and far blocks through the street's walls): an object or
  lamp of the concept's surroundings that another place of the area is (place/square). The place's own renders draw
  it; its package leaves it out once the area seats it, and the area's shells check reads it as none of the place's.
- **A block giving way** (`hollow <folder> <name> --region x0,y0,z0,x1,y1,z1`): a blocks object re-laid without what
  stands in each region (the scene's frame), its boxes read back from its laid mesh and cut, its parts, pose and role
  kept; what stands in a region (a shop's tables, its lamps) and fittings left with no wall within FITTING_REACH go
  with it, a door leaf never. The street's wall_l1 round the seated stairwell and flat: the walker began inside it.
- **Places of one area** (area/, its own overlay): `join` marks the doorway leading to a neighbour place, `area` seats
  the places at the plans' storey heights with their joined doors meeting and checks every join (seats.json).
- **A physical sky from where and when** (`sky-at`, #154; every library sky dome is withdrawn): an airless body's
  sky (the Moon's) from a kept scene's sky (`--scene`, `{home}/design/sky/<scene>.json`) or a given site and time,
  written by the light stage's own `light/sky.py write` on overhead.py's answer, never a second sky model: the risen
  lights at true direction, kelvin and lux, the Sun's disc, every other body a ball at its true size and phase, black
  behind them, the backdrops' domes as the Environment's light, the exposure a white face square to the Sun at 1;
  `--turn` turns the azimuths onto the place's frame. Each body wears its library face (`surface/<body>_face`'s
  face.json, as its body-face row made it); one the library lacks or withdrew is laid named missing. A body with air
  is refused (its day dome is not laid here). The light stage's gate (`sky.faults`) holds it in the test.
- **`sky --background`** sets the sky the camera sees (a palette token's night blue where the entry's is black).
- **Blocks** (`blocks`, batch only; the street, owner 2026-11-16: "no paper-thin walls, bevels on edges"): a
  straight-sided structure is solid chamfered boxes from the shell algorithm (dome_shell.blocks_file), one object of
  parts: a road and kerbed pavements of slabs laid as ground, a building's walls with its window openings, reveals and
  a shop's room as a structure (`score:role`). A window, sign or air conditioner flush on a wall is `put` with
  `role` "mount" and `support` "wall:<building>", so the check (ready/) judges it against that wall.
- **A night** (`night`, batch only): no sky picture; the night's physics (score/stages/light/night.py worked out for
  the place: the moonlit and city-lit air, the moon) passed in as the Environment's light, background and exposure
  and a moon light; `haze` a box of haze (tools/usd/scene.py's haze body) the renderer fills.
- **`batch`** runs many steps in one process on one open stage: a full relayout in seconds, never one call a step.
- **`review`** (review.py, review_views.py; owner 2026-11-16: "were missing a tool that allow for quick ways to review
  a scene"): a region (the scene, `--box x0,z0,x1,z1` or `--prefix`) as one contact sheet from one Blender call on the
  card at 8 samples denoised, the ground's displacement as bump (a review never ships): a plan cut 2.4 m over the floor
  with a 1 m grid and names, four corners, eye height from each door and the middle, a close-up per compartment
  (place.json `compartments`, else each dome shell structure), the concept in the corner, review.json listing the
  views; a physics check's faults (`check.json` {"faults": [{"object", "kind"}]}) boxed in red. A crowd of one entry
  (the stones) never frames the region. `viewer` writes the scene as one Draco GLB (viewer_glb.py, no card), its
  textures halved until it fits 15 MB, for the owner to orbit.
- **`make`** (maker/, its own overlay): a prop's model made with TRELLIS.2 on this PC's card from its picture (a take's
  close-up, a concept crop by its SAM 3 mask), set over the model it replaces, graded to the palette, CoACD hulls and
  mass, taken into score_lib as a draft entry that `put` lays like any made model.
- The camera `start` writes is a starting guess (`CAMERA`); the agent sets the concept's with `camera`.
- **The film** (film.py, `film`, `film-render`; owner 2026-11-16: "get me my demo"): a camera path that holds on the
  concept's view, glides down clear of everything and moves through the place's stops (named views with their aims,
  `x,z` at eye height over the floor walked by tools/usd/camera_paths.py's legs, or `x,y,z` in free air; `>x,y,z`
  aims one), against the physics check's own solids (ready.Place, its lights left out, each door as it stands for
  the walkers: one marked `score:opens` swung open). Its speed and look are eased,
  never jump; a frame carries the stage's time code, so walkers laid as time samples move with it. A glazed or closed
  place is filmed from free air outside its glass, never through a closed door.
- Test: `test_a_laid_scene_holds_its_library_entries_where_the_agent_put_them.py` (no Blender, no library fetch;
  blender_views.py is checked by a render of the fixture scene, never in the test).
- **The scene package** (scene_package.py, `package <folder> <out>`): the laid place for a game engine (2099's Unity,
  glTFast) in tools/props/library/package.py's one format (score.scene v1, checked by its own check, never forked):
  every object converted from the laid USD with usd-core and trimesh's writer (a door a walker swings over time laid
  as it rests, with its `door` block; any other moving object left out), laid at place.json `seat` when the area
  gave one (area/), its bound looks as glTF PBR (exact
  factors, maps, an image surface box-projected over its tile, glass as transmission), an unchanged glTF model its
  entry's own glTF; colliders from ready.json's roles. A palette recipe is baked as the preview draws it (wear, dirt,
  relief; bake_looks.py, headless Blender through the card queue) at 512 texels a metre on xatlas maps, each map as
  big as its charts and at most 4096 (written at most 2048 and every side a multiple of BLOCK_TEXELS, 4, so an engine compresses it in its 4 x 4 blocks;
HELD_TEXELS: the game's PlaceTextures.MostTexels, a
  bigger picture halved as its mip is made, so the game decodes what it shows; 2099 #161) (a face wider than half a map cut first, blocks of a map's worth packed alone, a
  map under 512 refused: #146, #151; the base's hangar sat 11.5 h packing 44 big faces as one 33,000 px map), a laid
  ground's as one seamless 8 m tile, in Blender runs of a few maps of one object each (scene_package.BATCH; one run
  over the street's 225 maps grew past the 8 GB cap), SIDE_BY_SIDE runs at once on measured card shares (a run's
  card mostly waits on its Blender's processor work: 29% busy one run at a time, 2026-11-22), each finished map marked under <out>/bake/maps so `package`
  again resumes a stopped bake and rebakes only a changed object's maps; every step runs under its time
  (scene_package.STEP_SECONDS: an object's conversion and the scene's rest stop the process with its stack, a Blender
  run is stopped by `timeout`, its card wait not counted), each named in <out>/bake/steps.log first; a mesh with no
  normals goes smooth, as Blender imports it; scene.json's
  `environment` carries the sky picture, sun, exposure, the ground's baked albedo (an engine's bounce from below) and
  the AgX grade drawn by Blender's own OpenColorIO as a lattice picture (grade_lut.py), so the engine grades exactly.
  **`package --draft`** (2099 #161) is a preview that never ships: the same scene.json and glTF objects with no bake
  and no walkers' eyes read, each palette recipe its plain colour, metal and roughness (an image surface keeps its
  own pictures), scene.json `draft` (scene_package.DRAFT); score-lib take-in --place refuses a folder carrying it.
  **`package --pieces`** (pieces.py, 2099 #245) writes the piece list beside it, score.scene version 2 in package.py's
  format and check: no Blender and no bake, in seconds. A laid library entry (model, take, kit, effect, ground) is a
  piece by its address and its index's digest, never written; everything made for the place (an algorithm's blocks,
  stair core, dome, terrain) a made/<name>.glb of one mesh a part, positions and normals only; each copy its whole
  matrix and a look id a part (a recipe's spec word for word, a surface's factors and library maps, or `own`).
  **Characters go in it skinned** (skinned.py, 2099's prologue, 2026-11-20): every SkelRoot laid (a `put` player
  model, the cast's characters layer, a sim body's own SkelAnimation) and every crowd PointInstancer copy is a skinned
  glTF converted from the laid USD (its skeleton, shown meshes with their weights and morph targets, every clip cut to
  one round and the animation it plays, a walker's route as node 0's moves), its copy's `plays` saying from when; its
  check skins the glTF at the played animation's first, middle and last keys against UsdSkel's own skin (within
  1e-4 m) and fails the package otherwise. The people's correctives key negative weights: an engine must not clamp
  them (Blender's importer does until a key's slider_min is lowered). Prims under a SkelRoot must be typed (a Scope,
  an Xform): UsdSkel skips a skinned mesh under a typeless prim, as tools/characters/skel_usd.py's assets never have.
