# tools/props/library/

The theme's material library and the robust route's piece making (job robust-exp, 2026-10-06). Shape and material
are kept apart: models and code give shape only; every part names a library material, a ProcFunc recipe coloured
from palette tokens, baked to the maps the game draws. Bible: `workflow/bootstrap` (the runtime) and the robust
route in `architecture/components`.

- **The library is data.** `data/definitions/place.json` `shared.theme.library` holds every material (recipe,
  token, settings, the reference patch it is tuned to) and the wear levels; a place takes them by name in its own
  `materials`, with its own token, and its own `wear`. `library.py` resolves them; nothing else holds a colour.
- **Recipes are ProcFunc** (`recipes.py`, the owner, 2026-10-06): composable functions (relief, edge wear, dirt,
  layering), every setting an argument, the seed explicit, no Python branch on a setting, so ProcFunc's tracer
  lists them (`settings_of`). Relief comes from `vendor/infinigen2`'s base materials (BSD-3); colour noise from
  them is left out on purpose: the ink look draws flat colour by region. Wear reads the true geometry (the bevel
  test) and the noise only scales it, so a flat face never wears.
- **No bake or render on this PC.** A local bake took every core and WSL crashed (2026-10-06). Everything under
  `inside/` runs in Blender on a rented card through `../cloud/library_bake.py` (swatches, code pieces, chunky
  pieces). `inside/runtime.py` puts ProcFunc on Blender 5's path and maps the sockets Blender 5 renamed; the
  vendored copies stay as released.
- **Never split a raw Pixal3D model into per-piece objects.** trimesh's `split` on a 950k-face raw model took
  43.5 GB and took WSL down (2026-10-06). Sample points (`register.py`). Every local Python step runs under
  `systemd-run --user --scope -q -p MemoryMax=16G`.
- `sorter.py` routes every kit kind before a picture is drawn: flat, slender, opening and repeat to code
  (`inside/pieces.py`), solid ones to Pixal3D, labels and signs to decals. `labels.py` gives a generated model's
  faces library materials from its clean picture, or per part from a splitter's parts (`../cloud/parts.py`).
- `tune.py` turns a material's settings to match its reference patch (render, compare, adjust); it renders in
  Blender, so it too goes to the cloud. Relief stays within the ink look's bounds (>= 1 cm, <= 0.6 mm high):
  matched freely, it crinkles every paint into photo grain.
- Checks: `library_test.py` (system python).
