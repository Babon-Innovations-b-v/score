# score/stages/surface_tiles/

The surface-tiles stage: each place's room shell (its scene record's code-built `structure`) drawn with its library
surfaces instead of a flat colour, one paid row `surface-tiles@<place>` in world 1's table, read by the assembly.

- **One tile a surface, baked flat on a card** (`tools/props/library/inside/make_tiles.py` through
  `tools/props/cloud/library_bake.py`), in the place's own tokens, wear and dirt, `TILE_METRES` a side at the kit's
  density, made to repeat without a seam. The assembly's record step writes the shell with it
  (`tools/usd/shaders.py` `tile_look`, a UsdTransform2d over the mesh's uvs in metres); the web viewer carries the
  repeat as KHR_texture_transform.
- **Glass, glow, light and print keep the flat surface**: a tile carries no opacity or glow (`UNTILED_FAMILIES`).
- **Its surfaces come from the seed scene record** (`data/scene/<place>.json`); a surface the tiles lack is drawn
  flat, as before. A place with no scene record or no tiled surface has no row.
- **No bake on this PC.** A local preview of `make_tiles.py` is small, low-resolution and under the gate's lock.
