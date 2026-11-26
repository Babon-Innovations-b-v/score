# score/stages/signs/

**A sign whose words must read is built in code** (2099 #161, 2026-11-26: TRELLIS.2 draws no characters; the street's
tea restaurant sign read "未来余食厅" in a dull texture that never lit). `build(text, size, palette)` gives a lightbox:
a dark casing, a glowing face inset by `BORDER`, and the words raised `LETTER_PROUD` off the face as boxes, one a run
of a row of the words' ink, set in the library's face (`score/stages/surfaces/text_decals.FONTS`, SIL OFL) at `ROWS`
rows. Its frame: y up, the face towards +z, the foot on y 0, centred across and in depth, so it takes the place of a
sign model laid with its face out.

- **No picture, no texture.** The words are geometry in the palette's `sign_lettering_red` (glowing), the face
  `sign_lightbox_cream` (glowing), the casing `gunmetal_steel` (painted metal): every part a palette variant of its
  library recipe through `moving_parts/car.painted`, never a colour of the build's own.
- A face the library does not hold a glyph for sets an empty box: check `text_decals.missing(text, look)` first.
- **A lightbox's face is lit from behind**: it gives off `FACE_GLOW` and reflects only `FACE_BASE` of its colour, its
  letters `LETTER_GLOW` of theirs, deeper than the face (2099 #161 round 3: a whole cream face under its lamp drew a
  white slab, its red words salmon). `finishes` swaps a part's variant: a neon blade sign is a dark `gunmetal_steel`
  face with its letters glowing whole in a `neon_*` variant; `vertical` stacks the characters top to bottom.
