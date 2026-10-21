# score/stages/surface_tiles/

The surface-tiles stage: each place's shell (the walls, decks, roofs and stairs its scene record lays from its locked
plan) drawn with its scene library's surfaces instead of a flat colour, one paid row `surface-tiles@<place>` in world
1's table, read by the assembly.

- **One tile a surface, baked flat on a card** (`tools/props/library/inside/make_tiles.py` through
  `tools/props/cloud/library_bake.py`), in the scene palette's tokens, wear and dirt, `TILE_METRES` a side at the
  shell's density, made to repeat without a seam. The assembly's record step writes the shell with it
  (`tools/usd/shaders.py` `tile_look`, a UsdTransform2d over the mesh's uvs in metres); the web viewer carries the
  repeat as KHR_texture_transform.
- **Glass, glow, light and print keep the flat surface**: a tile carries no opacity or glow (`UNTILED_FAMILIES`).
- **From the design and the batch alone** (owner, 2026-10-21): which parts the shell has is the locked plan's
  (`{home}/design/plans/<place>.json`, `shell_kinds`: what scene_record.writer `structure` lays), which surface each
  takes is the scene's surface library's (`surface-library@<place>`, `palette_library.shell_surface`), its specs,
  wear and dirt the scene palette's (`finish-route-palette@<place>`). A place whose plan lays no such shell, or whose
  finish line makes no library, has no row; a part the library gives no surface is drawn flat.
- **No bake on this PC.** A local preview of `make_tiles.py` is small, low-resolution and under the gate's lock.
