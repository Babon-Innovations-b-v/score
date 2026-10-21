# score/stages/crops/

The crops stage (experimental, PRD #6, design D of 2026-10-12): the crop kinds a place's concept shows, made like any
prop and grown on its beds as the concept grows them, as a layer of point instancers the assembly takes
(its `LAYERS`). `__init__.py`'s docstring lists the rows; each module's docstring has its make and gates.

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json` that names the place, the prim or pattern, what it is, why it is not from the
  library, who allowed it and when. Every finish is a library surface (`data/library`, the ProcFunc recipes and
  palette tokens): never a picture's own texture, a model's baked-in colour, a default grey or anything else; a
  picture-made model keeps its geometry and gets its finish replaced. The library check
  (`score/stages/complete/library`) lists what does not trace; bible `architecture/components`.
- **Measured on the concept, never by eye.** `crops-concept` asks SAM 3 for each kind's nouns on the concept's 2x
  tiles; the kinds and their nouns are environment data (`data/crops/<place>.json`), in precedence order (a plant two
  kinds' nouns find is the earlier kind's). A kind SAM 3 cannot count is changed in the data with a written reason
  (`dropped`, `canopy`), never typed as a count. The 2026-10-12 runs: on the whole picture the bushes merged into a
  few boxes and the seedling and herb nouns fell to earlier kinds; the 2x tiles and the precedence order fixed the
  read; parsley and kale stay one canopy kind, `greens`.
- **Spacing, not plants a square metre.** The concept draws its plants far larger than the plan's 12 m plot holds
  them, so a kind's measure is its spacing in plant widths (nearest-neighbour distance over the plant's box width),
  laid as that spacing times the made model's width, and checked again on the laid spots (`spacing`) and on the
  render (`density`, the look).
- **Plants are models like any other** (the owner, 2026-10-20, #26). The crop kinds are rows of the place's own
  prop data (`data/props/<place>.json`: props-inputs, closeup, pixal) and takes of its own surface data
  (`data/surfaces/<place>.json`: the finish route to surfaces-bake), so one shared prop pipeline and one finish route
  make them. This package is the motion layer's growth module, a layer adapter: its own inputs (the concept's kinds
  and spacing, `crops-concept`; the crop rows' boxes, `crops-boxes`) and its own steps after the model (laid on the
  beds, `crops-layer`; seen again on a render, `crops-look`). Until 2026-10-20 the crops had a line of their own on
  the finish-map method (`line.py`, `renamed.py`), deleted with it.
- **The box gate first.** `crops-boxes` runs box_check's own SAM 3 measure on the crop rows' boxes inside the runner
  (box_check.py --masks rents outside it and is refused); each crop row's box is its partition proposal's.
- **What the owner decides.** The crop state (the concept's mid-season beds, not the game's bare start) is his open
  decision, said in the crop data's `state`. Crops grow on the scene's 25 start beds only; the tarped stages stay.
- **Crop data is its design's.** A place's crop data names the view `design` (its locked concept); the old
  concepts' (the greenhouse's K09) was retired with them (owner, 2026-10-21: all old stuff is retired), so a place
  whose design shows crops waits on its crop data by name until it is written from the design.
- Tests: `crops_test.py` (tiles, measures, the gates, the look's camera round trip), free.
