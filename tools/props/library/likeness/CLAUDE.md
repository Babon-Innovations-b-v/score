# tools/props/library/likeness/

The look-alike check (#155): a surface of an adopted set holds its own maps AND a ProcFunc recipe checked to look the
same, so a place can draw it either way. Bible: `architecture/components`; glossary: adopted set (`CONTEXT.md`).

- `fit.py` fits a recipe from the maps' statistics alone, no render: the family from the material name's finish word
  (`FAMILY_WORDS`, first match wins; words of a finish, never a maker's or a repository's name), else from its metal
  and roughness means; the colours from the albedo's Lab mean and darkest fifth (a surface with no albedo map: its
  surface.json `constants` diffuseColor, linear, drawn as the map material's constant base colour too); roughness and metal from an ORM map's
  green and blue (or their own maps), else the constants' roughness and metallic, else USD's 0.5 and 0, and the map
  side draws the same (never Blender's default: 41 glass and 8 metal fails, 2026-11-23, and their passes compared a
  recipe against a 0.5 the surface never said); a constant opacity into glass's; the pattern size and bump from the normal map integrated to a height field
  (Frankot-Chellappa) and high-passed. A pattern size stays within `SIZE_RANGE` of its family's default, and a clamped size scales the bump with it so
  the relief keeps its slope (a 30 cm swell drawn as 8 mm grain at full height scattered two black plastics'
  highlights 60 L away).
  `fit.described` reads a surface.json: `maps` a dict {role: file} (an adopted set's), `normal_convention`
  (a DirectX map's green turned over, here and in `../inside/likeness.py`) and `tile_metres`; a null tile size
  is fitted as a free setting (the size at which the relief's features are the family's default pattern size),
  never assumed 1 m.
- The fit's sources of a wrong family or setting, fixed at their source on 2026-11-23 after the first run over 783
  adopted surfaces (621 pass): a surface that gives off light is glowing at its own strength; a measured metal
  overrules a glass name, "mirror" is polished metal, a name saying only "metal" takes its finish from its maps,
  material words come before colour metals, stone is rock and a tiled floor tiles; a packed `albedo_roughness` map
  is read as its two roles; a normal map's z is rebuilt from its x and y (a map whose blue is not its z) on both
  sides; slopes finer than the read widen the roughness (Toksvig), and a large tile's relief is read down to the
  close view's pixel; no normal map draws no relief; a grid family's pitch is its relief's period; polished metal's
  scratches come from its roughness map's spread; rusted metal's own wear from its albedo's worn share; plastic,
  rubber, cloth and paint mottle by contrast and roughness spread, a darker second shade past contrast 1.
- **Transparency is compared** (2026-11-23; until then both sides were drawn opaque and no glass's see-through was
  checked). A surface whose source lets light through (`fit.see_through_of`: a constant opacity or cutout under 1, an
  opacity map cut at its threshold, a glass's transmission, whose colour and roughness are its look as score_lib's
  take-in writes it) or whose recipe has an opacity under 1 is also drawn as a pane before a checker that gives off
  its own light (`inside/likeness.py`): the map side by its alpha and the principled surface's transmission, the
  recipe by its opacity as the look's alpha. `measure.through_measures` reads how much of the checker's contrast each
  pane shows; the gap is held to 0.08 of it (the lightness bound's 8 L over the checker's 100), and the refinement
  moves the opacity by it, by a secant once an earlier round shows how the gap moves (`measure.opacity_step`: a
  pane's share is far from linear in its alpha, and the plain step swung 59 glasses between two opacities for six
  rounds). The fitted opacity is the share the source stops, its glass's light tinted by its colour
  (`fit.opacity_of`: a black glass starts near opaque, not clear). A surface that lets light through by a glass's transmission or a constant opacity under 1
  (no map, no threshold) is fitted glass whatever its name (glass is the one family drawn see-through), so a
  see-through plastic fails only where its tint or frost differs. A cutout (`fit.cutout_of`: an opacity map or a
  threshold, as a perforated metal, a leaf or a fence) keeps its own family, and its cut is drawn on both panes, so
  only its finish is compared; an opacity map is cut texel by texel before it is counted (holes finer than a read
  block are never averaged away).
- **The adopted set's missing families** (2026-11-23, from the first run's diagnosis): `mat` (studs or ribs on a
  grid: whole words, `fit.says`: matsurface, mat with surface, fluted, antislip, a rubber lined or line, never a
  place mat, a blood line or a lined leather; or a rubber whose relief is a grid,
  `PERIODIC_SHARE`), `strand_board` (OSB and HDF flakes), `knit` (a blanket's loops), `hammered` (by its name alone:
  a relief's half width read 39 plastics' slow swells as dents, so the grainy black plastic stays plastic) and a printed check on `cloth` (its albedo's print a grid). A mat's ribs or
  studs and their width come from its relief's anisotropy and raised share, a check's pitch, line and colour from its
  albedo's period, off-median area and colour.
- `measure.py` compares the two renders view by view (cell colour difference, lightness histogram, highlight, detail
  ratio), passes or fails at its own bounds, writes the likeness block `{measures, pass, algorithm}` and refines a
  failing recipe (colour by the Lab gap, roughness by the highlight gap, a secant step once an earlier round shows
  which way the gap moves, bump and contrast by the detail ratio). `check.py` keeps the best round (`measure.ranking`:
  the fewest bounds broken, then the least far), not the last, and every round's settings and measures in the
  result's `history`. The
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
  a bump render shows only as their outline. Later that day, NVIDIA SimReady's 10 tiling surfaces with maps: 9 pass in
  one render each; the emissive white failed on detail (0.36), its map material drawing no emissiveColor. Now
  `fit.described` carries a surface's glow (`emission_colour`, its constant emissiveColor, linear, its intensity in
  its size; none beside an emission map, which the map side draws itself, as USD draws a connected input) and the map
  side draws it: rerun the same day, the emissive white (55f5469a, emissiveColor 5) passes in one render, both sides
  a flat glowing white (cell colour 0, detail 1.0 in both views).
