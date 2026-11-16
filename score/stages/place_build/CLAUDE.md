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
- **`start --split` rents a SAM 3 card** (score/review/concept_objects.py): a paid step, its spend rules apply.
- The camera `start` writes is a starting guess (`CAMERA`); the agent sets the concept's with `camera`.
- Test: `test_a_laid_scene_holds_its_library_entries_where_the_agent_put_them.py` (no Blender, no library fetch).
