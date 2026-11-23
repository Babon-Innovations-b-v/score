# tools/library/part_looks/

The October 2026 code-built library models (provenance `framework_models`, score 4547b8c54) remade part by part in
library surfaces, their shared atlas off (2026-11-23: bake.py's shrink_hidden gave every face toward the kit's back a
twentieth of the texel density, so 1,137 models drew a median 37% of their surface in the atlas's unpainted black).
`part_looks.py`'s docstring has the method and the command line.

- **Geometry is kept exactly**; only the finish changes. Which part a face is comes from its old builder built again
  at the models' commit (`rebuild.py`, in Blender) and its triangles taken in the old join's order, each within
  TOLERANCE of the model's. An entry that does not match is refused and named in the report, never guessed and never
  matched looser.
- **The part-to-surface map is data** (`map/parts.json`), recovered from every builder at 4547b8c54 by `recover`; a
  remake refuses a part the map does not list. Rerun `recover` only if OLD_COMMIT changes.
- **Every finish is a library surface**: each part's look names the library's recipe entry (`score:surface`) and
  carries the old variant's spec in its place (`score:recipe:spec`), as place_build's palette looks do. A variant that
  prints an old picture the library does not hold refuses the entry.
- `make` only writes files; the take-in (`score-lib take-in <listing.json> --save`) and the withdrawals
  (`score-lib withdraw <old> --replaced-by <new>`, from `replaced.json`) are the library's own commands.
