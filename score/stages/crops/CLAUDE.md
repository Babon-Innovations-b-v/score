# score/stages/crops/

The crops stage (experimental, PRD #6, design D of 2026-10-12): the crop kinds a place's design shows, made like any
prop and grown on its plan's beds as its concept grows them, as a layer of point instancers the assembly takes
(its `LAYERS`). `__init__.py`'s docstring lists the rows; each module's docstring has its make and gates.

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json` that names the place, the prim or pattern, what it is, why it is not from the
  library, who allowed it and when. Every finish is a library surface (`data/library`, the ProcFunc recipes and
  palette tokens): never a picture's own texture, a model's baked-in colour, a default grey or anything else; a
  picture-made model keeps its geometry and gets its finish replaced. The library check
  (`score/stages/complete/library`) lists what does not trace; bible `architecture/components`.
- **Read off the design, never a record per place** (owner, 2026-10-21: every stage builds from the creator's
  design; the old per-place crop data, `data/crops/<place>.json`, was retired). `crop_data.record_of` reads the kept
  scene inventory: every row whose kind grows (`../row_kinds.py`) standing on a bed (`../design_layers.py`
  `row_layers`: a row of a bed's noun, or one that grows itself, a planter) is a kind, named by its row, asked of
  SAM 3 by its name, then its noun when no other crop row shares it; its bed row the row it stands on. The beds are
  the plan items that bed row makes (`crop_data.beds_in`, in the place's frame: `scene_record/plan.items_of`), as tall
  as the bed row's metres, on the plan level its anchor names. The plot SAM 3 finds on the concept is the bed rows'
  words. A place whose design shows no row growing on a bed has no crop rows (`crop_data.applies`).
- **Measured on the concept, never by eye.** `crops-concept` asks SAM 3 for each kind's words on the concept's 2x
  tiles, in the inventory's row order (a plant two kinds' words find is the earlier kind's); a box over `MERGED`
  widths is plants SAM 3 merged and is left out. A kind SAM 3 cannot count leaves `measured` unknown, named; never
  typed as a count. The 2026-10-12 runs (the old concept): on the whole picture the bushes merged into a few boxes;
  the 2x tiles fixed the read. The canopy kinds and dropped kinds the old crop data wrote by hand went with it.
- **Spacing, not plants a square metre.** A concept draws its plants far larger than its plan's beds hold them, so a
  kind's measure is its spacing in plant widths (nearest-neighbour distance over the plant's box width), laid as that
  spacing times the made model's width, and checked again on the laid spots (`spacing`) and on the render (`density`,
  the look).
- **Plants are models like any other** (the owner, 2026-10-20, #26). The crop kinds are rows of the place's own hand-in
  (its design's, `{home}/design/props/<place>.json`: props-inputs, closeup, pixal) and takes of its own surface data
  (the finish route to surfaces-bake), so one shared prop pipeline and one finish route make them. This package is the
  motion layer's growth module, a layer adapter: its own inputs (the concept's kinds and spacing, `crops-concept`; the
  crop rows' boxes, `crops-boxes`) and its own steps after the model (laid on the beds, `crops-layer`; seen again on a
  render, `crops-look`). Until 2026-10-20 the crops had a line of their own on the finish-map method (`line.py`,
  `renamed.py`), deleted with it.
- **The box gate first, off the design.** `crops-boxes` reads each crop row's box from the locked concept's reading
  (the kept inventory's `box`): a box SAM 3 placed there passes as it stands; only a row the reading framed by
  Gemini's region is masked again by box_check's own SAM 3 measure inside the runner (box_check.py --masks rents
  outside it and is refused). Nothing to mask rents nothing (2026-10-22: the old page-A read rented a card for none).
- **The concept decides how the beds look**: the crops grow on every bed the plan lays, as its locked concept
  draws them (its kinds' patches and spacing).
- Tests: `test_crops_grow_as_the_concept_grows_them.py` (kinds and beds read off a design, tiles, measures, the gates, the look's camera round
  trip), free.
