# tools/props/library/likeness/

The look-alike check (#155): a surface of an adopted set holds its own maps AND a ProcFunc recipe checked to look the
same, so a place can draw it either way. Bible: `architecture/components`; glossary: adopted set (`CONTEXT.md`).

- `fit.py` fits a recipe from the maps' statistics alone, no render: the family from the material name's finish word
  (`FAMILY_WORDS`, first match wins; words of a finish, never a maker's or a repository's name), else from its metal
  and roughness means; the colours from the albedo's Lab mean and darkest fifth; roughness and metal from an ORM map's
  green and blue (or their own maps); the pattern size and bump from the normal map integrated to a height field
  (Frankot-Chellappa) and high-passed. A pattern size stays within `SIZE_RANGE` of its family's default.
  `fit.described` reads a surface.json: `maps` a dict {role: file} (an adopted set's), `normal_convention`
  (a DirectX map's green turned over, here and in `../inside/likeness.py`) and `tile_metres`; a null tile size
  is fitted as a free setting (the size at which the relief's features are the family's default pattern size),
  never assumed 1 m.
- `measure.py` compares the two renders view by view (cell colour difference, lightness histogram, highlight, detail
  ratio), passes or fails at its own bounds, writes the likeness block `{measures, pass, algorithm}` and refines a
  failing recipe (colour by the Lab gap, roughness by the highlight gap, bump and contrast by the detail ratio). The
  bounds are the check's (checks are ours, never the owner's question); they are settled by the first run over the
  set, never loosened to pass.
- `check.py` is the one batch command over a list of surface addresses: fit, one Blender for all of them through this
  PC's card queue (`score/stages/place_build/render.queued`, `../inside/likeness.py`), measure, refine, at most
  `ROUNDS` renders a surface. A run over many surfaces is started detached (`tools/cloud/detached.py`). A surface that
  never passes keeps its maps only: its recipe is a written gap (step 18 of #155 writes it into the entry).
- The renders stay in the run's folder: a picture of the map side is an adaptation of the set's own material and is
  never stored in the library or the repository.
- The test (`test_a_fitted_recipe_passes_only_when_it_looks_like_its_maps.py`) covers the fit and the measures with
  64-texel maps and stand-in pictures, no Blender. The Blender side is proven by a run on this PC's card: on
  2026-11-22 two of the library's image surfaces (plastic010: pass in one render, cell colour 0.2; diamond plate
  008a: fail on detail, 0.71 and 0.42, after two) — the chequer plate recipe's lugs are a hard step in height, which
  a bump render shows only as their outline.
