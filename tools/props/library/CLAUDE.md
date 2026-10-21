# tools/props/library/

The theme's material library and the robust route's piece making (job robust-exp, 2026-10-06). Shape and material
are kept apart: models and code give shape only; every part names a library variant, a ProcFunc recipe coloured
from palette tokens, baked to the maps the game draws. Bible: `architecture/components`.

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json` that names the place, the prim or pattern, what it is, why it is not from the
  library, who allowed it and when. Every finish is a library surface (`data/library`, the ProcFunc recipes and
  palette tokens): never a picture's own texture, a model's baked-in colour, a default grey or anything else; a
  picture-made model keeps its geometry and gets its finish replaced. The library check
  (`score/stages/complete/library`) lists what does not trace; bible `architecture/components`.
- **The old models' records are retired** (owner, 2026-10-21: every old model, kit, effect, sound, layer and place
  withdrawn from score_lib, all remade fresh). `data/library/details.json`, `composites.json`, `fittings.json`,
  `pipeline_failures.json` and `data/parts` are gone and their readers answer none: `sorter.failures` and
  `sorter.fittings` are empty, so every kind goes to the prop pipeline; `route.jobs` names a kind with no turn and
  stops; no take is stored. What a scene needs is its design's (`{home}/design/inventory/<scene>.json`, its hand-in
  `{home}/design/props/<scene>.json`); the remake batch makes each model and hands it to score_lib as a draft
  (`library@<place>`). The bullets below that name those files describe the old route; its builders (`inside/pieces*.py`,
  `earth_*.py`) still stand, routed to by nothing until a pipeline failure is recorded.
- **Experimental until the surface stage proves it** (docs/bible.md, `architecture/experimental`): everything in the
  painting after round four (the two-way split fit, round five's 3D split, paint by the model's own parts with
  `--face-parts` and `finish_masks.py`, the patchy rule), the surface check's dark rule (5c66c2e: a region the
  close-up shows very dark is read as dark paint, so shadow reads as paint), and `split_spread.py` (a measure: nothing
  was repainted by it). None of it has an owner-accepted before and after on a world model: 42 environment 1 takes are
  still on the 10-08 paint and the owner sees the same painting faults (2026-10-11). Step 1 of PRD #6 settles them,
  with numbers, on the hangar and the six named models; a surface-stage trial is running in its own worktree, so this
  folder's paint code is left as it is meanwhile.

- **An outdoor place and the scene package** (moved from 2099, #129 there): `place_route.py` plans a place with no kit
  layout from its inventory rows (models, bake jobs, the model gate and straightness, `split` for a take too long for
  one piece); `package.py` writes what any engine loads, every object its glTF and `scene.json` with each copy's
  transform, and refuses a package that does not match the inventory. `route.py install` (kit rooms) writes the
  environment's files (`data/kit/<room>.json`, the made models); an engine's own scenes for a kit are its adapter's.
- **Every old material is retired** (owner, 2026-10-21: "all materials, models all"; the base theme's 373 variants,
  its printed pictures, every kind's `materials` list in `details.json` and the old game tokens as material colours
  went; score_lib's 386 surface entries and `surface_recipes@1` withdrawn). `data/library/materials.json` holds the
  method alone: the wear levels, each recipe's default settings (no token in them) and `colour_settings`, the colour
  settings a variant of each recipe names in its own tokens. A scene's surfaces are made fresh by its
  `surface-library` row (`score/stages/surfaces/scene_library.py`), a library of the same form with its families,
  `kinds`, its own palette `tokens` ({name: "#rrggbb"}) and `dirt`. `library.py` loads either (`--list` lists the
  families; the command line prints one summary line naming the file under `/tmp/score-output/`, `--verbose` prints
  it); colours come only from a library's own tokens (`token_colours(library)`), never `design/tokens/tokens.json`,
  which is the dashboard's palette alone. A surface or token a library lacks is `LibraryEmpty` ("surface library
  empty: run surface-library first"), a `FileNotFoundError`, so a gate answers unknown and a row names it; a lookup
  of every variant (`variants`, `library_specs`) of the method's library finds none, so a reader that names an
  unknown surface (the sound layer, the library check) names every old one. The kit routes' place still names variants in its own `materials` in `place.json`; with
  the library empty they name the missing input. `browser.py` writes the browser page from a swatch run.
- **Recipes are ProcFunc** (`recipes.py`, the owner, 2026-10-06): composable functions (relief, edge wear, dirt,
  layering, grids on the surface's own plane, printed pictures), every setting an argument, the seed explicit, no
  Python branch on a setting, so ProcFunc's tracer lists them (`settings_of`). Relief from `vendor/infinigen2`'s
  base materials (BSD-3); their colour noise is left out on purpose: the ink look draws flat colour by region. Wear
  reads the true geometry (the bevel test) and the noise only scales it, so a flat face never wears.
- **Earth's recipes** (the prologue build, 2026-10-07): `painted_plaster`, `tiles`, `terrazzo`, `boards`,
  `rusted_metal` and `wet_asphalt` (their families and variants retired with every old material, 2026-10-21), each
  wearing from a cause: chips on edges, scuffs where feet kick, worn floor paint where feet go, rust where rain gets
  in. Scenery seen only from afar takes a `far_` own name and `route.DISTANT` texels a metre.
- **Screens and lamp lenses glow as plates of their own** (`data/library/details.json` `screens`; their printed
  pictures in `data/library/pictures` were retired, 2026-10-21, and a scene library gives none yet), laid by
  `route.py` on a generated piece's front, or a code-built piece's own glass (make_kit splits glowing slots off).
- **The game's shared paints are retired** (`data/library/shared_paint.json`, 2026-10-21): a scene record's
  `shared_paint` object has each named surface marked `score:surface:missing` (`tools/usd/scene.py`), never drawn in
  the game's colours.
- **Big objects seen up close are code-built bodies under the take's details** (the owner, 2026-10-18, PRD #10: the
  picture model's geometry is right in its details, lumpy in its main shapes; every finish the library's).
  `inside/bodies.py` (plain Python) names each such take in `BODIES` (its builder in `inside/pieces_bodies.py`, the
  surfaces kept wherever they are, and its turn where the place's data has it wrong) and holds each body's numbers,
  read off its take in the kit frame; the bake (`make_chunky.make_bodied`) builds the body, keeps only the take's
  faces `bodies.kept` names (the console's screens, lamps and its bays' controls; nothing of the old station's first
  module), bakes both into one model and writes `<model>.parts/` (its surfaces as laid, kit frame), which the bake
  check and the assembly's export read in place of the labelled take. The registry sits in the bake's own folder, not
  in `data/surfaces/<place>.json`, which every row of a place's line reads: an edit there repaints the place.
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
  `inside/` runs through `../cloud/library_bake.py` (one class fixed at price time; a processor class only when asked for with `--classes cpu-32c-128gb`). `tune.py`
  renders there too, a machine a round. `inside/runtime.py` maps the sockets Blender 5 renamed for ProcFunc.
- **Never split a raw Pixal3D model into per-piece objects.** trimesh's `split` on a 950k-face raw model took
  43.5 GB and took WSL down (2026-10-06). Sample points (`register.py`). Every local Python step runs under
  `systemd-run --user --scope -q -p MemoryMax=16G`.
- **The prop pipeline first for every kind (the owner, 2026-10-20, #19, #41); code only on a named failure.**
  `sorter.route` sends a kind to code only when the pipeline-failure record (`data/library/pipeline_failures.json`:
  the failure, its evidence, its date) names it; every other kind, plain plates and fittings too, is the shared
  loop's (`score/stages/shapes_first`), and an inventory row is routed by `sorter.route`, never by its own `kind`
  (`code` or `generate`), so its close-up is taken and it is handed to the loop. A model-routed kind with no take yet
  is a gap that `plan.json` lists (`gaps`), never a code build and never a stop. Not built yet: no shell-section
  layer hands kit kinds to the loop, so `route.py plan` still makes a model-routed kit kind that has a labelled take
  from it (labels.py, `inside/make_chunky.py`), the old prop route, and earth-seed bakes its named fallbacks
  (`score/stages/earth_seed`'s overlay says why no kit row is handed to the loop yet). The record holds the failures
  measured on their own object (the hub's thin pieces every Pro close-up failed, `paper/evidence/compare-hub`; the
  cockpit's thrust indicator and the shiplock's outer hatch on likeness) and the owner's named exception: the hangar
  ship's hull, engines and thrusters, built in code from his plan v7 (`inside/ship_outline.py` reads
  `data/definitions/ship.json` for the kit layout and the builder alike; `inside/pieces_hull.py` builds them from the
  numbers the layout hands in), never from a picture. A kind joins it only with a failure measured on its own object.
  Big objects keep their code body (below). Purely code-built pieces look generated and copied shell pieces look like
  tiles; shell pieces come as a few pipeline-made variants per kit, laid by shell section (CONTEXT.md).
  `place_route.py plan` routes an outdoor place's rows the same way.
- **Method B's parts check holds a code fallback, never routes one** (the owner's pick 2026-10-07, demoted by #19):
  `data/library/fittings.json` lists a fitting's close-up parts and how much of each its last code build shows
  (`pieces.parts_seen`, each part seen at least 10% from in front, no print over a part); `route.py fittings <work>`
  writes a build's result back, and `sorter.fallback_parts_missing` is the one check `route.py layout` and the
  likeness row both hold a code fallback to (an unlisted fallback passes as plain). `PLAIN` stays a fact (no parts
  of its own to show). Builders, the sorter and `fittings.json` go per kind only after that kind's pipeline take
  passed (#19's clean-up map). `library_test.py` fails on a builder that is neither plain, a listed fitting nor a
  body; its check that every model a kit room lays was made on its kind's route is a strict xfail until every kit
  installed before #19 is made again through the loop.
- **Paint by parts.** `labels.py` paints a generated model by its parts (job paint, 2026-10-08, the owner: "shouldn't the painting be
  done by parts?"): PartCrafter's split (`../cloud/parts.py`) laid on the welded Pixal3D model, every face one part,
  every part ONE material from the kind's allowed list (`details.json` `materials`) by its lit colour; never per
  face. A split that does not register is reported and painted whole. `patchy.py` measures patchy paint (stray
  islands, mixed faces, soft seams; on a baked model also unbaked black) and `route.py plan` refuses patchy labels.
- **The picture's regions are the painting unit** (`labels.py --regions`, job repaint, 2026-10-08): SAM 2.1's masks of
  the clean close-up (`../cloud/segment.py`) become regions and looks (`regions.py`: the smallest mask over a pixel,
  like colours one look), carried onto the model through the corrected camera; the judge names each look's material
  (with each allowed material's colour here in words). PartCrafter's parts stay for moving pieces and bound where an
  unseen face's paint is taken from. PartCrafter's parts alone did not follow finishes (the lander's foil patches).
- **A part's material is what the part is** (job repaint, 2026-10-08): `labels.py --ask` writes each seen part
  outlined on the clean close-up with the object's name and the kind's allowed list (`part_judge.py`), the open judge
  (`../cloud/judge.py`, Qwen3.8-27B) answers, `--answers` paints by it; colour picks only where the judge gave no usable
  answer, and for finishes within a part (foil wraps, bands: `with_finishes`). The raw model faces the picture's camera
  turned half round (`labels.VIEW_TURN`); without it every colour came from the model's back.
- **Two checks, both must pass** (`route.py plan`): patchiness, and `patchy.stripped` (the close-up's main colours
  collapsed into one material), because one material can never be patchy. On a baked model a worn edge counts as wear
  of the material round it (`worn_as_around`).
- **A labelled take is stored in the repository** (`stored_parts.py`, job repaint 2026-10-08): labels.py writes the full
  labels (35 MB a take, the bake's input) under the work folder and a 40,000-point sample of them into
  `data/parts/<take>.npz`; `data/parts/models.json` says which take each place's made model was painted from. The
  OpenUSD export reads only these. A take relabelled is stored again; keep `models.json` in step when a model's take
  changes. Every sample labels.py draws is seeded (trimesh ignores numpy's global seed), so a take labels the same way
  every run.
- **A model's feet** (`feet.py`): its low points clustered across and along, each foot's lowest; `level` stretches a
  take's short legs onto the level plane through its lowest foot (the surface stage's paint, before its bake), the
  resting triage judges each foot of a laid object, the settle refuses a tip onto uneven feet.
- **A generated piece's back is baked at full density** (`bake.Atlas(backs_hidden=False)` from make_chunky): shrunk
  face by face its remeshed triangles fell under a texel and baked black (every generated piece's back, 2026-10-08).
- **One wear for the room, from a cause:** a scene's wear level (its scene palette's on the finish route; `place.json`
  on the kit routes), the bevel test on edges, and kick
  wear (`recipes.kick_mask`) within 32 cm over the floor a piece stands on (`foot`, route.py). A finish may carry its
  own wear level and seed (owner, 2026-10-20, #18): the finish route's list gives a level only with a cause the views
  show (walked paths, edges, round doors), and `recipes.arguments` takes a spec's own `wear` and `seed` over the
  place's and the job's. `sweep.py` checks a
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
- **Part splitters compared** (`split_compare.py`, `split_page.py`, `split_html.py`; job parts-test, 2026-10-09): on 22
  models GeoSAM2 seeded with the close-up's regions gave 79% of finishes parts of their own against PartCrafter's 34%
  (SegviGen 46% unguided, 68% guided but a median of 30 parts); its weakness is cuts through smooth surfaces where SAM
  cut one finish. Scores: finishes owned, needless cuts, regions whole and parts pure from the close-up's camera.
- **A splitter is judged by its spread over an environment's models, not its mean** (`split_spread.py`, job splits,
  2026-10-10, after the owner found the split better but inconsistent across models on 10-09): every environment 1 take
  split, each scored against its own close-up's finishes (its regions painting's materials when the regions match,
  else the judge per region), the spread and the worst models written to `<run>/spread.txt`. It writes no labels and
  no stored parts. On the 126 environment 1 takes (88 with two finishes or more), GeoSAM2 seeded owned a median 100% of
  finishes but a mean 75%, sd 29%, 10 models under half and 4 none; PartCrafter on its 45: mean 25%, 22 none. A rerun
  of 22 takes gave identical SAM 2.1 regions and GeoSAM2 splits 88-100% the same by area, one take's score flipping
  (rover-r1). GeoSAM2 needs only `mesh.glb` and `seed_points.npz` (12 MB a take), so a run folder for it alone keeps
  `raw.glb` (35 MB a take) out of the uploads: with it, 20 machines sat idle on the home line's uploads for 35
  minutes (EUR 36) and nothing came back.
