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
- **The tunnel** (`tube`): the dome shell algorithm's ribbed glass tube between two domes (parts shell, ribs, deck).
- **Standing on things**: `put --rest` lays a piece's lowest point at the given height (a floor, a table top);
  `--on-ground` reads that height over the laid ground there (a rock on a terrain's relief).
- **Named views** (`view`, `render --views a,b`): inside and low views beside the concept's, their look only.
- **Image surfaces** (`surface/ambientcg_*`, CC0 PBR sets taken in with their source in each entry's provenance and
  surface.json) tile at their own `tile_metres` in the preview, box-projected in the object's own frame
  (blender_views.py); a model's bake keeps its own texture coordinates.
- **The preview's Blender script is blender_views.py**, usd_views.py with a laid ground as the ground and see-through
  looks as thin glass, patched in there so the films' and physics' renders (which key usd_views.py) never move.
- **`batch`** runs many steps in one process on one open stage: a full relayout in seconds, never one call a step.
- The camera `start` writes is a starting guess (`CAMERA`); the agent sets the concept's with `camera`.
- Test: `test_a_laid_scene_holds_its_library_entries_where_the_agent_put_them.py` (no Blender, no library fetch;
  blender_views.py is checked by a render of the fixture scene, never in the test).
