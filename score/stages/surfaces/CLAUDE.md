# score/stages/surfaces/

The surface stage (R4, the paper's core contribution: shape and surface apart, every part one surface of the shared
library), step 1 of PRD #6, as rows of world 1's stage table (`__init__.py`, `ROWS`). Bible: `architecture/components`
and `architecture/experimental`; method: the paper's Methods, "Shape and surface apart".

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
  the close-up; Nano Banana Pro's finish map of the close-up, drawn up to three times, the last more strictly, then
  of each turntable view against it; `finish_ask.py`, `finish_maps.py`), `segvigen_row.py` (SegviGen guided by the
  close-up's map). Each paid row has a module of its own, so a free change never pays again; every Google ask is
  cached by its input's hash. The six-model re-test rows are `../finishmap/trial.py`.
- **A library change re-keys only the rows that read the library** (lists, names, parts, paint, bake, check:
  `surface_data.line_files`); inputs, turntable, maps and SegviGen declare none (`shape_files`), the inputs'
  output names no folder of its run, and the turntable renders on the processor with a fixed seed
  (`inside/turntable.py` `cycles_fixed`), its PNGs kept without Blender's date and render-time text
  (`turntable_row.without_text`: the same pixels are the same file). On 2026-10-12 the making folder in `job.json` and card renders that
  differed run to run made one library change re-render every place and re-draw every view map (about EUR 50).
  Before pushing a change that moves a paid row's key, list what it re-buys (`_code.source_files` and the
  row's files); `score run` lists it again before it starts and refuses over EUR 5 without `--rebuy-reason`.
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
  asked to paint one colour, the picture model tinted the photo); a close-up whose draws all fail is split by its own
  colours and each region named by the draws' labelled pixels (`finish_maps.colour_split`, owner-approved fallback
  2026-10-12, old_station's lab module: colours only split, the paint stays the library's); one that still loses a
  finish counts as not settled. A model with no settled close-up map is named in `surfaces-maps`' fail and
  stops its place's line (once the owner waives it, later rows leave it out). A part whose voted faces mix two
  finishes fails `surfaces-parts` the same way.
- **Each finish's surface is checked against the close-up's colour** (`finish_parts.checked_finishes`,
  `COLOUR_DELTA_E` 32 CIE76, set on round 4's six models): the colour only chooses among library surfaces (the
  nearest of the listed one's family); a finish none fits gets a tinted proposal in the registry and fails the paint
  row's gate "colour against the close-up" by name. A finish is measured on its label's brighter half, a
  dark one (library L* under `DARK_L` 35) on all its pixels: the light lifts blacks' brighter half to L* 40 to 45.
  A Gemini 3.1 Pro ask that times out is asked again with its thinking held low (`finish_ask.low_thinking`).
  Glass, screen glow, lamp light and print off the lit colour keep their surface (owner, #8: judged by their own
  colour), and so does a see-through finish of another family (`coloured_cover`: the garage beacon's red transparent
  dome, its pixels its highlights and what lies behind it). A finish the close-up shows over 10 L* lighter than another whose surface lies over 3 L* lighter in the
  library takes the nearest surface of its family that keeps the order, else the darker finish does, else fails the
  gate by its order (`in_close_up_order`); a finish out of that order is also named again (`out_of_order`). Lighter
  by 3 or less, the pair is reordered only by a surface nearer its finish's close-up colour (`reordered`): the bake
  moves L* on its own (the hangar's parts shelving: plastic_grey 1.5 under galvanized_steel baked 4.5 under it). A finish's close-up pixels
  whose first face from the camera is a see-through part (glass, light, screen, transparent or translucent words) are
  left out of its measure (`behind_left_out`). A finish drawn within one see-through finish (its outline at least
  90% that cover, `seen_within`) is laid as the cover, in every map: the model is the cover's shell with nothing
  inside, so the maps drew what lies behind it on the cover's own faces (the garage beacon's reflector on its red
  dome). Paint-row gate changes go here, in the parts row: a paint check's file is in the paint
  row's key, so an edit there repaints and rebakes every place. A strongly coloured finish named again (chroma over
  40) is also asked whether it is lamp light (`finish_ask.GLOW_QUESTION`); other naming requests stay word for word.
- **A finish is named again when its words or colour contradict its surface** (`surfaces-names`, paid, cached): its
  words name a material its surface's family is not (`finish_parts.contradicts`: black rubber as bare_steel), or its
  surface lies over `COLOUR_DELTA_E` from its close-up colour; Gemini is asked once with the close-up, the finish map
  and every surface the take's library places allow. New library surfaces are made the library's own way (a variant
  in `data/library/materials.json` on a palette token, the place taking it in `place.json`), never a picture's colour.
- **The bake takes today's library and the method's paint only**: every spec the library knows (painted, and the job's
  decals and screens) from the library, an old job's `regions` boxes dropped; a spec left naming a missing picture
  stops the bake before anything is rented. The job files still give each model's entry (size, decals, cuts).
- **The paint runs on rented processor machines, a job a take** (`make_paint`, `inside/paint_take.py` through
  `blender_cloud.py`; paid, cleared like the bake): heavy steps run in the cloud (owner, 2026-10-12); measured up there,
  campgrounds' takes peak at 1.5 to 3.4 GB and crane-r1 at 34.8 GB (the PC's cap is 14 GB). Up there Blender's own
  Python runs `place_line.py paint-take` with the prop environment's pinned packages and says its peak memory and any
  signal; the registry proposals are written here first. `tools/props/heavy.py` refuses the step anywhere the
  cloud runner's mark (FARM_LOCAL_MODELS=1) is not set. prop_env.py is left alone: the method's rows import it, and an
  edit there re-keys every place's inputs.
- **The check holds a bake against its surface dirtied as its place dirties it** (`bake_check.on_surface`: the
  stretch from the library colour toward the place's dirt colour, as far as its dirt amount; the wreck's whites
  bake to L* 69 in regolith at 0.6 and pass, a wrong surface still fails).
- **A standing model stands level** (`bake_check.judge_stance`, gate "stands level"): each footprint quadrant of its
  lowest quarter ends within 3 cm of its lowest point (the hangar's rack stood on a middle part, its legs 22 cm up;
  the paint's feet check, in shares of size, let it pass). A model its paint did not level (no floor or held row) or
  whose inventory row names a lying class (`data/checks/stance.json`: torn wreckage) is left out. Glass, glow, lamp
  light and print skip the close-up comparison (#8), and so does a coloured see-through cover the paint judged by its
  own colour (`cover`: the garage beacon's red_plastic dome), left out of `close_up_colours`; other finishes judged
  by their own colour stay in it for the order and one-look checks.
- **The check is its own module** (`bake_check.py`, so its edits move the check row alone; wired in
  `score/stages/__init__.py` until the 2026-10-12 fan-out ends). The turntable and SegviGen rows take their world
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
  kit's spots and the scene record's eyes; owner, 2026-10-13: a fixed 12 failed the wreck's access cover on a step he
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
  through the middle (the square's guard hut, 2026-10-14: 14 cm across, it stood on a strip and tipped). Wear and dirt stay
  the room's one setting, applied where they have a cause (owner): a per-model amount read off the close-up is a
  picture-derived look (tried 2026-10-13, reverted).
- **The paint levels a take's feet before its bake** (`place_line.levelled_feet`, `tools/props/library/feet.py`):
  a take a row lays loose on the floor or held (`stands_on_feet`, from the inventory and the resting rules, declared
  in the table) has its short legs stretched onto the level plane through its lowest foot, in its own frame; a foot
  over a tenth of its size up is a missing leg and fails the gate "feet in one plane" by name. Never level by
  tipping the model: its own up is the reference (the water tank's top lay level within 0.25 degrees).
- **Painting is 3D parts plus the shared library, only.** A picture's colours never reach a model: a map's label
  colours only name finishes, each part is painted from its finish's library surface.
- **The finish registry is a store item** (`registry.py`; `registry/surfaces/` in the store): append-only, the new
  library surfaces a method proposed, each standing as first proposed for the owner to accept into the library or
  not; until then the part keeps the nearest library surface the method named (`stands_in`). The paint writes it
  outside its key.
- **Per-place data is world data** (`surface_data.py`, `data/surfaces/<place>.json`): the takes a place paints, the
  library name, the bake (the route's make_chunky job, model per take, entries the job lacks), and `elsewhere`: the
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
