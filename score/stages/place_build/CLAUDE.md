# score/stages/place_build/

The placing agent's tool (#128, owner 2026-11-16): a place laid by hand from score_lib entries, step by step, until
its render reads as its locked concept (same room, layout, main objects, mood). The agent (a vision model) drives it
one command at a time and reads `compare.png` and the measures to choose the next correction; nothing here judges.

- **Everything laid comes from the library.** `put` lays only an entry with a USD file (kit pieces, models, the
  sky domes), copied whole under the place's `assets/`; `surface` binds a library surface over everything inside the
  object (a variant's own material, or a recipe in a palette colour), so a model's baked colour never shows; `light`
  lays the library's lamp. No geometry, colour or light is made here outside a library entry.
- **The scene is a plain USD** (y up, metres, `/<place>/Objects|Looks|Lights`) that tools/usd (snap.py, resting.py)
  and sim body read as they read a place: keep that layout, never a Blender file.
- **Render through the card queue only** (`render.py`: usd_views.py, Cycles review samples, a memory-capped scope,
  more than 12 GB free); a long one is started with tools/cloud/detached.py, never waited on in the foreground. Set
  `SCORE_BLENDER_LIBS` to the X/GL libraries this PC's Blender needs.
- **`start --split` runs SAM 3 free on this PC's card** (score/review/concept_objects.py under SCORE_CLOUD=local and
  SCORE_FREE_ONLY=1, tools/cloud/backends/local.py's segment claim); never a rented card.
- **Parts.** A kit piece's or model's colour regions are GeomSubsets; `surface --part` binds a surface on one, and the
  object's whole look then goes on every shape and every other part, so no baked colour shows anywhere.
- **glTF-only entries** (our picture-made models and takes) are converted once at `put` (gltf.py): a part a material,
  each wearing its own bake and paint (base colour, metal-roughness and normal maps), a take's `-final` model first;
  `surface` puts a library surface over a part or the whole when a bake is wrong.
- **Characters** are laid as their own SkelRoot (never an Xform over it), dressed in one body group (WORN) and held
  still in a clip with tools/characters/cast.py's own steps.
- **The dome shell** (dome_shell.py, `dome`) is code-made: its shell, ribs and deck are parts for their surfaces;
  `ground` lays the same flat disc alone as the place's ground.
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
- **Named views** (`view`, `render --views a,b`): inside and low views beside the concept's, their look only.
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
  side and a glazed front. Panes are one face each (a closed pane's two thin-glass skins ring with light).
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
  aims one), against the physics check's own solids (ready.Place, its lights left out). Its speed and look are eased,
  never jump; a frame carries the stage's time code, so walkers laid as time samples move with it. A glazed or closed
  place is filmed from free air outside its glass, never through a closed door.
- Test: `test_a_laid_scene_holds_its_library_entries_where_the_agent_put_them.py` (no Blender, no library fetch;
  blender_views.py is checked by a render of the fixture scene, never in the test).
