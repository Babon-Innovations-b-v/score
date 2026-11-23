# tools/library/part_looks/

The October 2026 code-built library models (provenance `framework_models`, score 4547b8c54) remade part by part in
library surfaces, their shared atlas off (2026-11-23: bake.py's shrink_hidden gave every face toward the kit's back a
twentieth of the texel density, so 1,137 models drew a median 37% of their surface in the atlas's unpainted black).
`part_looks.py`'s docstring has the method and the command line.

- **Geometry is kept exactly**; only the finish changes. Which part a face is comes from its old builder built again
  at the models' commit (`rebuild.py`, in Blender) and its triangles taken in the old join's order, each of the
  model's lying on the corners of the face built in its place and covering it, within TOLERANCE (an n-gon's cut into
  triangles is Blender's choice, so the face is compared, not the triangle). An entry that does not match is refused and named in the report, never guessed and never
  matched looser.
- **The part-to-surface map is data** (`map/parts.json`), recovered from every builder at 4547b8c54 by `recover`; a
  remake refuses a part the map does not list. Rerun `recover` only if OLD_COMMIT changes.
- **Every finish is a library surface**: each part's look names the library's recipe entry (`score:surface`) and
  carries the old variant's spec in its place (`score:recipe:spec`), as place_build's palette looks do.
- **Built as its room laid it**: model.json keeps no `laid`, so a remake reads what the model's room showed at
  4547b8c54 (`laid_of`: the kit room's piece of that model, route.shows' keys: a street face's weather, a dome gore's
  arc, a sign's openings), and the rebuild is moved onto the model's box (a model laid off its builder's origin).
- **A printed picture is a library decal**: a variant that printed an old picture prints the library decal of it
  (surface/<picture>, family decal) through the builder's own `content` map, composited as the old recipe printed it;
  a picture the library holds no decal of refuses the entry (NoDecal) until `decals` lists it for the take-in.
- **The fallback, from the atlas regions**: an entry whose old build cannot be recovered (Unrecovered: no code build,
  a builder that fails, parts the map lacks, triangles that do not match) wears, per UV island of its old atlas, its
  room's library surface nearest the island's painted colour (an island on the unpainted black: the nearest painted
  face's); its record's step says so. Its previews are looked at before the take-in like any other.
- `make` only writes files; the take-in (`score-lib take-in <listing.json> --save`) and the withdrawals
  (`score-lib withdraw <old> --replaced-by <new>`, from `replaced.json`) are the library's own commands.
