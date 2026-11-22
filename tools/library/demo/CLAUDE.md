# tools/library/demo/

`pictures.py` makes score_lib's README pictures, one of each kind, from the library's own entries (owner,
2026-11-22: "these samples are so shit"). The 3D ones render in the cloud (`tools/blender/inside/library_demo.py`
through `blender_cloud.run_elsewhere`), never Blender on this PC; the concept, place and sound come from the pictures
their entries hold. Its docstring says how each kind is read so a plain USD reader shows it as a place does.

- **Every picture is made from library entries only**: models, kit pieces, surfaces, lamps and effects come from
  score_lib by `library_files.resolve`; the studio (backdrop, studio lights, a swatch sphere) is the only thing made
  here, and a finish is always a library surface laid at its own tile size.
- **Change a pick in `PICKS`** and say why on score #156; the README's captions in score_lib name the
  same entries.
- Its test, `test_an_entry_is_drawn_where_it_stands.py`, covers the preparation that needs no Blender.
