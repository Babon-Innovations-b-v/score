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
- **glTF-only entries** are converted once at `put` (gltf.py: geometry, a part a material, no finish).
- **Characters** are laid as their own SkelRoot (never an Xform over it), dressed in one body group (WORN) and held
  still in a clip with tools/characters/cast.py's own steps.
- **The dome shell** (dome_shell.py, `dome`) is code-made: its shell and ribs are parts for their surfaces.
- **The preview's Blender script is blender_views.py**, usd_views.py with a laid ground as the ground and see-through
  looks as thin glass, patched in there so the films' and physics' renders (which key usd_views.py) never move.
- **`batch`** runs many steps in one process on one open stage: a full relayout in seconds, never one call a step.
- The camera `start` writes is a starting guess (`CAMERA`); the agent sets the concept's with `camera`.
- Test: `test_a_laid_scene_holds_its_library_entries_where_the_agent_put_them.py` (no Blender, no library fetch;
  blender_views.py is checked by a render of the fixture scene, never in the test).
