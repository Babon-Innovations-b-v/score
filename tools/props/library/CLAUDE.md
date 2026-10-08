# tools/props/library/

The theme's material library and the robust route's piece making (job robust-exp, 2026-10-06). Shape and material
are kept apart: models and code give shape only; every part names a library variant, a ProcFunc recipe coloured
from palette tokens, baked to the maps the game draws. Bible: `workflow/bootstrap` item 11.

- **An outdoor place and the scene package** (moved from 2099, #129 there): `place_route.py` plans a place with no kit
  layout from its inventory rows (models, bake jobs, the model gate and straightness, `split` for a take too long for
  one piece); `package.py` writes what any engine loads, every object its glTF and `scene.json` with each copy's
  transform, and refuses a package that does not match the inventory. `route.py install` (kit rooms) still writes the
  game 2099's Godot files: that is its adapter, to move out when 2099 consumes the package.
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
- **Earth's surfaces** (the prologue build, 2026-10-07): `painted_plaster`, `tiles`, `terrazzo`, `boards`,
  `rusted_metal` and `wet_asphalt`, in the families `plaster`, `tile`, `ground` and `rusted` (plus wood, fabric,
  plastic and light variants), each wearing from a cause: chips on edges, scuffs where feet kick, worn floor paint
  where feet go, rust where rain gets in. Scenery seen only from afar takes a `far_` own name and `route.DISTANT`
  texels a metre.
- **Screens and lamp lenses glow as plates of their own** (`data/library/details.json` `screens`, pictures drawn by
  `printed.py` into `data/library/pictures`), laid by `route.py` on a generated piece's front, or a code-built
  piece's own glass (make_kit splits glowing slots off).
- **Generated pieces** (`data/library/details.json`: each kind's `turn`, `screens`, `cuts`, `decals` and whether it is
  `square`): `inside/make_chunky.py` turns a labelled Pixal3D model into the kit frame at its laid size, closes a copy
  into a solid (thickened 5 mm inward, rebuilt on a voxel grid: a raw Pixal3D model is a shell under 1 mm thick, which
  the model check fails), cuts it to 20k triangles, cuts its openings, lays its decals on clear flat spots
  (`clear_spot`) and bakes the library from the full model onto it (its shape relief kept in the normal map). The
  picture's colours never reach it (method B; round four's picture layer gave every piece its own rust and stains,
  "inconsistent with the rest of the room", and is gone). `straight.py` fails a `square` kind that comes out tilted or
  warped (round four's locker leant 13 degrees).
- **Print is decals placed by rule** (round six): labels, sheets, notes and stickers are printed plates (print
  family) placed on purpose, a few a piece, never over a vent, a handle or a tool: `pieces.prints_off` probes the
  face under every print on a code-built piece, `make_chunky.clear_spot` finds a clear flat spot on a generated one.
- **Composites are split, one model per real-world object** (round six): `data/library/composites.json` lists a
  parent kind's children (each its own kind: a tool, a radio, a monitor) and where each stands on the parent; the
  inventory has a row per child (`anchor: on:<parent>`). `route.py` plans each child like any kind and writes it
  into the parent's prop scene, their glowing parts under one `Glow` node.
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
- **Code or pipeline, by the parts check (method B, the owner's pick 2026-10-07).** `sorter.py`: plain plates,
  pipes and trims (`PLAIN`) go to `inside/pieces.py`; so does every kind listed in `data/library/fittings.json` (the
  room's shell and fittings, furniture holders, plain manufactured objects) whose last code build shows every part
  its clean close-up shows (`pieces.parts_seen`, each part seen at least 10% from in front) with no print over a part;
  every other kind goes to the prop pipeline. A box's proportions never decide it. `route.py fittings <work>` writes a
  build's result back; `route.py layout` stops on a code build that failed. `library_test.py` fails on a builder
  that is neither plain nor a listed fitting, and on any model the hub lays that was not made on its kind's route.
  `labels.py` paints a generated model by its parts (job paint, 2026-10-08, the owner: "shouldn't the painting be
  done by parts?"): PartCrafter's split (`../cloud/parts.py`) laid on the welded Pixal3D model, every face one part,
  every part ONE material from the kind's allowed list (`details.json` `materials`) by its lit colour; never per
  face. A split that does not register is reported and painted whole. `patchy.py` measures patchy paint (stray
  islands, mixed faces, soft seams; on a baked model also unbaked black) and `route.py plan` refuses patchy labels.
- **A labelled take is stored in the repository** (`stored_parts.py`, job repaint 2026-10-08): labels.py writes the full
  labels (35 MB a take, the bake's input) under the work folder and a 40,000-point sample of them into
  `data/parts/<take>.npz`; `data/parts/models.json` says which take each place's made model was painted from. The
  OpenUSD export reads only these. A take relabelled is stored again; keep `models.json` in step when a model's take
  changes. Every sample labels.py draws is seeded (trimesh ignores numpy's global seed), so a take labels the same way
  every run.
- **A generated piece's back is baked at full density** (`bake.Atlas(backs_hidden=False)` from make_chunky): shrunk
  face by face its remeshed triangles fell under a texel and baked black (every generated piece's back, 2026-10-08).
- **One wear for the room, from a cause:** a place's wear level (`place.json`), the bevel test on edges, and kick
  wear (`recipes.kick_mask`) within 32 cm over the floor a piece stands on (`foot`, route.py). `sweep.py` checks a
  room's made models against its own library palette.
- **Storage:** `stored.py` keeps a room's pictures as WebP and stops an install past the room budget (modules batch
  one).
- **A piece of thin rails and open shelves may close thicker** (`details.json` `wall`, `make_chunky.solid_copy`): the
  solid step's 5 mm left berths, shelves and an alcove's rails under the model check's 3 mm (modules batch one).
- **The model check before the bake** (`route.py precheck <work>`, modules round): every code model of a plan is built
  here as geometry alone (`inside/build_only.py`, headless Blender, no bake, no render) and given the model check;
  run it after `plan` and before any bake (five builds failed on 2 mm walls only after their bake: a band laid 2 mm
  proud of what it wraps reads as a 2 mm wall, so a band, tape or stripe stands 4 mm proud or sits on its face).
- **Pipe runs** (step 0 of the modules round, 2026-10-07): a wall pipe run's axis stands `pieces.PIPE_AXIS` (8 cm) off
  the wall, its bracket and valve on the wall behind it; the layout cuts a straight pipe at every inline valve
  (`hub_kit.split_at_fittings`), never through it.
- **A shared picture set never silently loses density**: `bake.Atlas` stops past the 4096 side, and `route.py`
  splits a set by its boxes' seen area before the bake.
- `tune.py`: relief stays within the ink look's bounds (>= 1 cm, <= 0.6 mm high); matched freely, it crinkles every
  paint into photo grain.
- Checks: `library_test.py` (system python), `straight_test.py` and `paint_test.py` (hand themselves to the prop
  environment).
