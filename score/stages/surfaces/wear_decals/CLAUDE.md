# score/stages/surfaces/wear_decals/

Weather marks a place shows (grime, scorch, wet and damp stains, hairline cracks, rain and rust streaks) drawn in
code as score_lib decals, and the one carrier plate (`model/decal_plate`) a decal is laid on (2099 ADR-0008 lay
plans, 2026-11-26). The package docstring has the method and the command line.

- **A mark is a token's ink through a transparency**: each pixel the palette token's colour, its strength the alpha;
  never a photograph, a model's texture or a colour of the code's own. The place's lay names the token's place.
- **Same kind, size, ink and seed, same picture**: a mark is remade only by a new seed or size, as the next version.
- **Moon footprints are not drawn here**: they are pressed relief, `algorithm/ground_tracks` (place_build `tracks`).
- **One carrier for every mark**: the plate is laid scaled to its mark (`[wide, tall, deep / PLATE_DEEP]`), its
  `face` bound to the decal, its `edge` to the finish under it. A new kind goes in `KINDS` and a row of the test.
