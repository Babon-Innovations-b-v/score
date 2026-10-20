# score/stages/surfaces/

The surface stage (R4, the paper's core contribution: shape and surface apart, every part one surface of the shared
library), step 1 of PRD #6, as rows of environment 1's stage table (`__init__.py`, `ROWS`). Bible: `architecture/components`
and `architecture/experimental`; method: the paper's Methods, "Shape and surface apart".

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json` that names the place, the prim or pattern, what it is, why it is not from the
  library, who allowed it and when. Every finish is a library surface (`data/library`, the ProcFunc recipes and
  palette tokens): never a picture's own texture, a model's baked-in colour, a default grey or anything else; a
  picture-made model keeps its geometry and gets its finish replaced. The library check
  (`score/stages/complete/library`) lists what does not trace; bible `architecture/components`.
- **One line per place, run by the runner**: `python -m score run world1 --place <place> --detach` (score's overlay:
  never walk the rows by hand). Every row is place grain (`surfaces-inputs@greenhouse` ... `surfaces-check@greenhouse`);
  no place waits on another.
- **The method sits behind one interface**: its rows end in the contract `surfaces-parts` v1 (`parts.json`: per model
  its parts, each with the library surface the method named (`judge`), its words, a proposed new surface or null;
  `finish` null when nothing is measured; `<take>/parts.npy` one part per welded face; `<take>/colours.npy` each
  face's seen colour, NaN when none is measured). Another method replaces the method's rows and writes it; the
  framework's rows (`place_line.py`: paint, bake, check) do not change.
- **The method is the finish-map method** (owner, 2026-10-12: "finish map seed 1 looks great"; it replaced g-texture,
  whose record is branch `surface-first` and main before this change): `finish_parts.py` (inputs, parts),
  `turntable_row.py` (the raw model's texture unlit from the close-up's camera and the sides and back, with the face
  under each pixel; `inside/turntable.py`, `turntable_views.py`), `finish_rows.py` (Gemini 3.1 Pro's finish list of
  the close-up; Nano Banana Pro's finish map of the close-up, drawn once and asked strictly (`finish_ask.STRICT`), then
  of each turntable view against it, once; `finish_ask.py`, `finish_maps.py`), `segvigen_row.py` (SegviGen guided by the
  close-up's map). Each paid row has a module of its own, so a free change never pays again; every Google ask is
  cached by its input's hash. The six-model re-test rows are `../finishmap/trial.py`.
- **The finish route** (owner, 2026-10-20, #18; library first): rows `finish-route-views`, `-split`, `-list`, `-fill`,
  `-recheck` (`route_*.py`, `ROUTE` in `__init__.py`; experimental, bible `architecture/experimental`), beside the
  method until its test passes and the owner moves the line onto it; no other row reads them, and they write no
  `surfaces-parts` yet. **Off by default**: a route row has a node only when the command asks for one by name
  (`score run|plan|status --stage finish-route-*`; `route_applies`, `graph.asked_for`), so no place's line, plan,
  hole or price has them otherwise. **The trial's cap is enforced** (`route_cap.py`): the list and recheck refuse to
  run without `--object <take>`, and refuse each ask not asked before once the route's asks on the Google ledger
  (callers `finish-route-list`, `-recheck`, every month) and its estimate would pass `TRIAL_EUROS` (EUR 5 in total,
  owner 2026-10-20). Run it: `python -m score run world1 --place <place> --stage finish-route-recheck --object
  <take> --detach`. Generic for any take of any place:
  a take's model is its raw take while it is there, else the release's made model its place's bake names
  (`route_data.py`), else the views gate names it; its close-up is its own, else a **stand-in close-up** (the model's
  own texture from the front, `route_data.STAND_IN`), named so in every output, question and verdict that reads it.
  Views (free, this PC's processor, no Blender): trimesh and Embree ray cast, orthographic, 384 px, seven sides with the
  close-up's front (`route_cast.py`); pictures are flat colour shaded by angle only (no wear, bump or pattern).
  Split (free): the labels are the model's own texture colours under each pixel in k-means groups (at most eight),
  voted across views (`finish_parts.voted`, `walked`, `cleaned`, `merged_islands`); the texture is measured, never
  painted. Paid maps (Nano Banana, about EUR 3 a model) are not drawn by the route; they stay the method's for a model
  whose free labels fail. List (paid, Gemini 3.1 Pro, about EUR 0.05 an ask, EUR 0.5 a place as the row's guess): all
  views, the groups and the close-up; each finish matched FIRST to a library surface with settings (a library token,
  roughness, metal, the node's seed), a new surface only when none fits with any settings; wear stays the place's
  level, a finish's wear wish goes to `questions.json` for the owner. Fill (free): each part its surface's token
  colour, and the free colour check (CIE76 within `COLOUR_DELTA_E`, glass, glow, light and print by their own
  colour). Recheck (paid, Gemini 3.1 Pro, up to three asks a take, EUR 1 a place as the row's guess): Gemini on the
  filled views against the close-up plus the colour check; a failing finish's settings are tweaked (Gemini's, else
  the token nearest its seen colour) and checked again, at most three tries, then the gate "library surface fits"
  fails it by name, "no library surface fits", the holes' `gate:finish-route-recheck/library surface fits:<take>`.
  Settings and tweaks are row output, never a materials.json edit. Each row selects (`score run --object <take>`).
  Its rows run in the framework's Python (trimesh and Embree are in `.venv`), not through `prop_env.py`.
- **Every paid ask runs once: the finishes layer is a batch** (CONTEXT.md, the owner, 2026-10-20; #21). One finish
  list a take, one draw of each map (`SEEDS`, `VIEW_SEEDS` one seed each), no paid naming, no ask again after a
  timeout or a dropped connection (`finish_ask.generated`): Google may bill a call cut off mid-way, and
  `google_spend` counts it at its estimate. Only a refusal that did no work (HTTP 429 or 503) is asked again, at most
  `REFUSED_ASKS` times. An ask with no usable answer (`finish_rows.UNANSWERED`) makes its take or draw a hole, named
  in its row's gate (`judge_lists`, `judge_maps`); new spend on it is a new batch and a new ask. The risk work is free
  and comes before: the close-up's measured colours (`close_up_regions`: k-means of its Lab colours, each region's
  share and median and the library surfaces within `COLOUR_DELTA_E`) go into the list ask (`finish_ask.REGIONS`),
  asked with thinking held low from the start and on the flex tier (`LIST_TIER`, half price, a 900 s timeout: the
  request's own `serviceTier`, never set in `google_spend`, which is in the close-up, crops and boxes rows' code
  versions; Nano Banana Pro has no flex tier on Google's page, 2026-10-20, so the maps stay standard). A kit or shell piece
  whose surfaces data names its `surface` (its shell section's or kit's finish) is asked nothing: that one finish
  (`declared_list`, a hole when the take may not take it), its map the close-up's mask.
- **A library change re-keys only the rows that read the library** (lists, names, parts, paint, bake, check:
  `surface_data.line_files`); inputs, turntable, maps and SegviGen declare none (`shape_files`), the inputs'
  output names no folder of its run, and the turntable renders on the processor with a fixed seed
  (`inside/turntable.py` `cycles_fixed`), its PNGs kept without Blender's date and render-time text
  (`turntable_row.without_text`: the same pixels are the same file). On 2026-10-12 the making folder in `job.json` and card renders that
  differed run to run made one library change re-render every place and re-draw every view map (about EUR 50).
  Before pushing a change, list the rows it moves with `python -m score.stages.moved <base> [<head>]` (code versions
  and every declared file: a code-only check missed the turntables' declared `blender_cloud.py`, 2026-10-14);
  `score run` lists the re-buys again before it starts and refuses over EUR 5 without `--rebuy-reason`.
- **The paint and bake rows (and their crops and people twins) key only what they read of the library**
  (`library_reads.py`, set in the table by `score/stages/__init__.py` `library_narrowed`): their library places'
  materials and wear in place.json, the variants those name and the bake job's specs, with their recipes, families,
  pictures and the kinds' details. A surface added for one place re-keys no other place's paint (2026-10-13: the
  hub's assembly wanted about EUR 60 of re-buys). Before making one, the runner keeps its accepted output under the
  new key when nothing it reads changed (`carry.py`: the library parts rebuilt from git at the record's commit, a
  committed record only); a row whose own code changed carries only with a proof stored as evidence on the output
  (`carry.proof_fault`: every changed file named with why, the free rows before it remade to their accepted outputs).
  `python -m score.stages.surfaces.carry` lists what carries and why not.
- **A map that does not settle blocks its model, never passes**: measured (`finish_maps.check`: overlap, share near
  a label colour, every finish used), filled from labelled neighbours only when its sole fault is a labelled share
  between `FILL_LEAST` and `NEAR_LEAST`; a one-finish model is not drawn (its map is the close-up's object mask:
  asked to paint one colour, the picture model tinted the photo); a close-up whose one draw fails is split by its own
  colours and each region named by the draw's labelled pixels (`finish_maps.colour_split`, owner-approved fallback
  2026-10-12, old_station's lab module: colours only split, the paint stays the library's); one that still loses a
  finish counts as not settled. A model with no settled close-up map is named in `surfaces-maps`' fail and
  stops its place's line (once the owner waives it, later rows leave it out). A part whose voted faces mix two
  finishes fails `surfaces-parts` the same way.
- **Each finish's surface is checked against the close-up's colour** (`finish_parts.checked_finishes`,
  `COLOUR_DELTA_E` 32 CIE76, set on round 4's six models): the colour only chooses among library surfaces (the
  nearest of the listed one's family); a finish none fits gets a tinted proposal in the registry and fails the paint
  row's gate "colour against the close-up" by name. A finish is measured on its label's brighter half, a
  dark one (library L* under `DARK_L` 35) on all its pixels: the light lifts blacks' brighter half to L* 40 to 45.
  Glass, screen glow, lamp light and print off the lit colour keep their surface (owner, #8: judged by their own
  colour), and so does a see-through finish of another family (`coloured_cover`: the garage beacon's red transparent
  dome, its pixels its highlights and what lies behind it). A finish the close-up shows over 10 L* lighter than another whose surface lies over 3 L* lighter in the
  library takes the nearest surface of its family that keeps the order, else the darker finish does, else fails the
  gate by its order (`in_close_up_order`). Lighter
  by 3 or less, the pair is reordered only by a surface nearer its finish's close-up colour (`reordered`): the bake
  moves L* on its own (the hangar's parts shelving: plastic_grey 1.5 under galvanized_steel baked 4.5 under it). A finish's close-up pixels
  whose first face from the camera is a see-through part (glass, light, screen, transparent or translucent words) are
  left out of its measure (`behind_left_out`). A finish drawn within one see-through finish (its outline at least
  90% that cover, `seen_within`) is laid as the cover, in every map: the model is the cover's shell with nothing
  inside, so the maps drew what lies behind it on the cover's own faces (the garage beacon's reflector on its red
  dome). Paint-row gate changes go here, in the parts row: a paint check's file is in the paint
  row's key, so an edit there repaints and rebakes every place.
- **The names are decided by rule, free** (`surfaces-names`, `finish_rows.named_by_rule`; it asked Gemini again
  until #21): a finish whose words say it gives off light (`GLOW_WORDS`) and whose close-up colour lies over
  `GLOW_CHROMA` 40 takes the nearest light or screen surface by colour (the garage beacon's red light, chroma 57); a
  finish whose words name a material its surface's family is not (`finish_parts.contradicts`: black rubber as
  bare_steel) takes the nearest surface of a family its words allow within `COLOUR_DELTA_E`, else it is a hole and
  fails the names gate by name. The paint's colour and order check (`finish_parts.checked_finishes`) runs ahead as a
  prediction (`predicted_off`, a measure); the paint's gate still names those, where a named gap can move them. The
  stage tables still declare the row paid at `LIST_EUROS` (`__init__.py`, `../crops/line.py`, `../people/line.py`,
  `../finishmap/trial.py`): it spends nothing now. New library surfaces are made the library's own way (a variant
  in `data/library/materials.json` on a palette token, the place taking it in `place.json`), never a picture's colour.
- **The bake takes today's library and the method's paint only**: every spec the library knows (painted, and the job's
  decals and screens) from the library, an old job's `regions` boxes dropped; a spec left naming a missing picture
  stops the bake before anything is rented. The job is written from git inside the bake (`bake_job.py`, 2026-10-19:
  the job files lived in the work folder and went with the old disk): each model's entry is the one its data writes
  out, else its route's own (`place_route.chunky_entry` sized over its labelled take for an outside place, whose kit
  says `on_seat`; `route.jobs`' fields at its laid size in `data/kit/<place>.json` for a kit room), the specs every
  library variant (`library.by_library` and `resolved`, as both routes write a job), so a variant added anywhere
  re-keys every bake; details.json and composites.json are keyed on only the entries the place's models read
  (`bake_job.reads`, through `library_reads.narrowed`), and the routes' code is in the bake's code version, not its
  files. A model neither gives (`bake_job.refusal`, entry_of's own checks run without the take: the launch's far
  rocket) is declared as a file that is never there, naming it, so the run refuses before anything is cleared; the
  crops bake too.
- **The paint runs on rented processor machines, a job a take** (`make_paint`, `inside/paint_take.py` through
  `blender_cloud.py`; paid, cleared like the bake): heavy steps run in the cloud (owner, 2026-10-12); measured up there,
  campgrounds' takes peak at 1.5 to 3.4 GB and crane-r1 at 34.8 GB (the PC's cap is 14 GB). Up there Blender's own
  Python runs `place_line.py paint-take` with the prop environment's pinned packages and says its peak memory and any
  signal; the registry proposals are written here first. `tools/props/heavy.py` refuses the step anywhere the
  cloud runner's mark (FARM_LOCAL_MODELS=1) is not set. prop_env.py is left alone: the method's rows import it, and an
  edit there re-keys every place's inputs.
- **The check holds a bake against its surface worn and dirtied as its place wears and dirties it**
  (`bake_check.on_surface`: the library colour worn toward its recipe's `bare` as far as the place's wear, then
  toward the place's dirt colour as far as its dirt; the wreck's whites bake to L* 69 in regolith at 0.6 and pass,
  the engine room's thin hazard trim, worn 0.8, baked a third bare steel and passes, a wrong surface still fails). A part's baked colour is its triangles'
  area-weighted median on each of L*, a*, b* (`bake_check.area_median`), never the triangle at the median L*: lab's
  junction_box_1 (2026-10-14) baked its crane yellow right on 56% of its area, and the grey panel triangle at the
  same L* that L* alone picked failed it at dE 37.
- **A standing model stands level** (`bake_check.judge_stance`, gate "stands level"): each footprint quadrant of its
  lowest quarter ends within 3 cm of its lowest point (the hangar's rack stood on a middle part, its legs 22 cm up;
  the paint's feet check, in shares of size, let it pass). A model its paint did not level (no floor or held row) or
  whose inventory row names a lying class (`data/checks/stance.json`: torn wreckage) is left out. Glass, glow, lamp
  light and print skip the close-up comparison (#8), and so does a coloured see-through cover the paint judged by its
  own colour (`cover`: the garage beacon's red_plastic dome), left out of `close_up_colours`; other finishes judged
  by their own colour stay in it for the order and one-look checks.
- **The check is its own module** (`bake_check.py`, so its edits move the check row alone; wired in
  `score/stages/__init__.py` until the 2026-10-12 fan-out ends). The turntable and SegviGen rows take their environment
  files from `row_files.py`, so neither this folder's `__init__.py` nor `place_line.py` is in their code
  version (`../stages_test.py` holds it). Each baked triangle is named by the bake's own ray (`bake_check.ray_surfaces`:
  from its middle make_chunky's reach out along its normal, inward, the first labelled face hit), never the nearest
  part: the cut-down copy stands a wall proud, and beside a thin post the post lay nearer than the facade the bake
  met (far_city's pencil tower, 2026-10-13: post_dark failed at dE 45, baked right); the ray starts where the bake
  wrote the texel the check samples (`sampled_points`: its centre's point, often on a neighbour of a triangle under a
  texel; the flat's bowl stack's glass rims failed at dE 66.6, baked right). A near-black triangle is a blotch only when its colour lies over
  `BLOTCH_DELTA_E` from every surface within its reach: on a border it may bake its neighbour (the seed tray's paper
  label on black plastic passes), a black smudge along the border still fails. It also fails a model whose surfaces
  bake to one grey look its close-up does not have (`one_look_faults`: no two told apart at the place's view distance,
  by Stone, Szafir and Setlur's measured ND(50) for their size in degrees from the nearest view (`seen_degrees`, the
  kit's spots, the scene record's objects, the machines record's machines and the scene record's eyes; owner, 2026-10-13: a fixed 12 failed the wreck's access cover on a step he
  sees), each near neutral, the close-up's over 24 apart; a model with no view distance is named; the greenhouse's water tank and crop crate, 2026-10-12: the check of bake against
  library alone passed them at dE 0), two opaque surfaces whose lightness order the bake reverses (`order_faults`:
  seen over 10 L* lighter, baked over 3 darker; the light moves L* but keeps the order), and a part baked over 32
  from its close-up colour (kept at 32: the close-up's light lifts right surfaces 15 to 30 L*, so a tighter number
  fails right blacks; compare a model's surfaces with each other instead).
- **A base that slopes as one piece is brought down level** in the paint (`place_line.flattened_base`, after the legs):
  each footprint quadrant of the bottom quarter over 1% of the size up comes down its whole gap at its lowest point,
  spread by inverse squared distance and faded over the band; over 15% is a model fault, refused. Then an underside
  that is one sloping plane (`sloped_base`: 80% of its cells within 1% of the plane fitted to them, rising over 1%)
  comes down by the plane's height, never past the lowest point: the quadrants miss a ramp whose low strip runs
  through the middle (the square's guard hut, 2026-10-14: 14 cm across, it stood on a strip and tipped). Last, the face
  it rests on (`resting_base`: its convex hull's face under its weight) comes down level when it rises over 1% of its
  footprint's diagonal: the quadrants and cells miss a plinth rim under a level floor (the garage's control cabinet,
  2026-10-15: 2.1 degrees over). Wear and dirt stay
  the room's one setting, applied where they have a cause (owner): a per-model amount read off the close-up is a
  picture-derived look (tried 2026-10-13, reverted).
- **The paint levels a take's feet before its bake** (`place_line.levelled_feet`, `tools/props/library/feet.py`):
  a take a row stands on the floor or ground (`stands_on_feet`, from the inventory and the resting rules, declared
  in the table: never mounted on another object, fixed, hung, laid tilted on purpose (`leans`) or a pile of ground
  debris; a word of a description, such as a cabinet's "cables", is no class) has its short legs stretched onto the level plane through its lowest foot, in its own frame; a foot
  over a tenth of its size up is a missing leg and fails the gate "feet in one plane" by name. Never level by
  tipping the model: its own up is the reference (the water tank's top lay level within 0.25 degrees). The bake
  levels such a take's cut-down copy again (`make_chunky.levelled_feet`, the take's `stands` from its labels through
  `library_bake.stands`): the remesh's voxels and the cut move feet apart (the hangar's 31 m ship, level in its
  paint, baked a front foot 22.2 cm up at 10 cm voxels), and the paint's 1% of size lets a 4 m piece keep 3.4 cm
  (the campgrounds' ice drill); each quadrant over the check's 3 cm comes down as `flattened_base` brings it.
- **Painting is 3D parts plus the shared library, only.** A picture's colours never reach a model: a map's label
  colours only name finishes, each part is painted from its finish's library surface.
- **The finish registry is a store item** (`registry.py`; `registry/surfaces/` in the store): append-only, the new
  library surfaces a method proposed, each standing as first proposed for the owner to accept into the library or
  not; until then the part keeps the nearest library surface the method named (`stands_in`). The paint writes it
  outside its key.
- **Per-place data is environment data** (`surface_data.py`, `data/surfaces/<place>.json`): the takes a place paints, the
  library name, the bake (model per take, the entries the route's own would not give written out), and `elsewhere`: the
  models it lays that another place claims. Everything is repainted, the owner's picks included (a pick chooses the
  model, never its old paint: owner, 2026-10-12); each take is painted by one place only, and a place reads a claimed
  model from the claiming place's bake (`elsewhere.json` in its bake output; the bake gate fails a claim the other
  place does not bake). A place with no file blocks at `surfaces-inputs`; one with no `bake` blocks at
  `surfaces-bake` before anything is cleared. A place with nothing to paint (code-built pieces only: gdoor, hdoor,
  tube) has a file with no takes and a `nothing` line; its line has no surface rows (`Stage.applies`).
- **Gates never crash or pass on what is missing** (`surface_gates.guarded`: unknown with the missing file named).
- Steps needing trimesh run in the prop environment through their module's command line (`prop_env.py`), each make
  defined in its step's own module so that module is its code version. Tests: `surfaces_test.py` (the framework
  side) and `finish_test.py` (the method's steps), both on the framework's Python.
