# tools/props/library/

The theme's material library and the robust route's piece making (job robust-exp, 2026-10-06). Shape and material
are kept apart: models and code give shape only; every part names a library variant, a ProcFunc recipe coloured
from palette tokens, baked to the maps the game draws. Bible: `workflow/bootstrap` item 11.

- **The library is data and only grows.** `data/library/materials.json` holds families of variants (each a recipe
  name, a token, its settings over the recipe's defaults, and the reference patch it was tuned to), the wear
  levels and the printed pictures; a place takes variants by name in its own `materials` in `place.json`, with its
  own token and wear. `library.py` resolves them (`--list` prints the families); nothing else holds a colour. Add a
  variant for a new surface; never change one a room already uses. `browser.py` writes the browser page from a
  swatch run.
- **Recipes are ProcFunc** (`recipes.py`, the owner, 2026-10-06): composable functions (relief, edge wear, dirt,
  layering, grids on the surface's own plane, printed pictures), every setting an argument, the seed explicit, no
  Python branch on a setting, so ProcFunc's tracer lists them (`settings_of`). Relief from `vendor/infinigen2`'s
  base materials (BSD-3); their colour noise is left out on purpose: the ink look draws flat colour by region. Wear
  reads the true geometry (the bevel test) and the noise only scales it, so a flat face never wears.
- **Labels, keypads and screens are printed pictures on code-built parts** (`printed.py` draws them into
  `data/library/pictures`; `inside/pieces.py` `label`, `screen_part`, `keypad`), never baked into a surface's own
  material. A screen is dark glass with its content lit; laid as its own piece, its kind glows.
- **Generated pieces get their detail back in code** (`data/library/details.json`): `inside/make_chunky.py` turns a
  labelled Pixal3D model into the kit frame at its laid size, closes a copy into a solid (thickened 5 mm inward,
  rebuilt on a voxel grid: a raw Pixal3D model is a shell under 1 mm thick, which the model check fails), cuts it to
  20k triangles, bakes the library from the full model onto it (its shape relief kept in the normal map), and seats
  labels, screws and keypads on its front by ray.
- **`route.py` runs the route for a whole room** (round three, 2026-10-06): `plan` (one model per kind and size, the
  cloud jobs), `layout` (the game's layout over the made models, a failing generated model left out), `install`
  (models, BC7 picture imports, kinds' scenes, data/kit). A piece's glowing parts (screen content, lamp lenses) are
  split into a `part` piece of their own, so only they glow.
- **Texture memory:** a job's pieces share one picture set (`inside/bake.py` `Atlas`), every face at one texel
  density except those the room never sees (backs against a wall or roof, a twentieth), colour and metal-roughness
  at half the normal map's side. Pieces export as .gltf beside the shared pictures.
- **No bake or render on this PC.** A local bake took every core and WSL crashed (2026-10-06). Everything under
  `inside/` runs through `../cloud/library_bake.py` (a card, or `--processor` when no card is in stock). `tune.py`
  renders there too, a machine a round. `inside/runtime.py` maps the sockets Blender 5 renamed for ProcFunc.
- **Never split a raw Pixal3D model into per-piece objects.** trimesh's `split` on a 950k-face raw model took
  43.5 GB and took WSL down (2026-10-06). Sample points (`register.py`). Every local Python step runs under
  `systemd-run --user --scope -q -p MemoryMax=16G`.
- `sorter.py` routes every kit kind before a picture is drawn: flat, slender, opening and repeat to code
  (`inside/pieces.py`), solid ones to Pixal3D, labels and signs to printed parts. `labels.py` gives a generated
  model's faces library variants from its clean picture, or per part from a splitter's parts (`../cloud/parts.py`).
- `tune.py`: relief stays within the ink look's bounds (>= 1 cm, <= 0.6 mm high); matched freely, it crinkles every
  paint into photo grain.
- Checks: `library_test.py` (system python).
