# score/stages/shapes_first/

The shared loop (#41; CONTEXT.md "shapes first", "layer adapter", "prop pipeline"): the one way every model layer
gets its models, as rows of the stage table, the same for a prop, a shell piece, a ground detail area or a plant.
`__init__.py`'s docstring has the order; `align.py` the registration; `made.py` what an after-step gets back.

    plan -> rough-model -> rough-align -> props-inputs (parts split) -> closeup -> pixal
         -> finish route (surfaces.ROWS) -> likeness -> each adapter's after-steps

## The interface (for a layer adapter)

- **Hand in rows.** A layer hands the loop its rows in the place's hand-in record, `data/props/<place>.json`
  (`prop_data.py` has the form): one `objects` entry per inventory row, with `"layer": "<your layer>"` (no `layer`:
  `objects`; read by `props/closeup_row.layer_of`, kept out of `prop_data.py`, which half the table's paid rows
  hash). The concept and the plan are the place's (the plan names its concept); the loop reads them itself. Nothing
  else makes a model: a row on the code route only with its pipeline failure named in its record.
- **Register.** Add `Adapter("<layer>", after=(<Stage>, ...))` to `ADAPTERS` in `__init__.py`. `rows(adapters)` gives
  the table the loop's rows and then each after-step, which applies only where the place handed rows of that layer
  (and where its own `applies` says). Two adapters on one layer are refused.
- **After-steps.** Each is a place row whose `after` holds every key of `made.ENDS` (`props-inputs`, `surfaces-bake`,
  `surfaces-parts`, `likeness`); one that does not is refused at import. Its make calls
  `made.made(inputs, "<layer>")` and gets `{row: {"route": "prop", "model": <baked .gltf>, "take", "finishes":
  [<surfaces-parts part rows>]}}`, `{"route": "code", "model": <code build>, "finishes": []}` or `{"gap": <why>}`.
  Import `score.stages.shapes_first.made` by its full name, never the package (the package is table wiring; its
  imports would move the after-step's key).
- **The registration.** `rough-align@<place>` (free) reads `rough-model` and `plan` and writes `align.json` (turn,
  one scale, a 4x4 row-major matrix mesh frame to place frame in metres, the plan's floor and walls' height, the
  aligned extent and the misfits) and `aligned.glb` (the rough model under one root node carrying the matrix). A
  model whose nodes carry their own transform is not registered and its gate, `registered`, names it. The parts split
  (`props-inputs`) waits on it, and its gate `fits the plan` fails a row that fits the registered floor no way round
  (unknown with no registration), measuring how many rows fit no footprint of the aligned rough model.

## Rules

- **No made-up thresholds.** The misfits are measures only until one is measured on accepted rough models (as
  `rough_model`'s overlay). The turn is 0 or 90 degrees: a box alone cannot tell 180 from 0.
- **The package is wiring only**: no make, judge or file map of its own, so it is in no row's code version; the
  loop's code is `align.py` and `made.py`.
- **Adapters in**: `OBJECTS` (nothing after the model) and `TERRAIN` (terrain/areas.py hands in the detail areas,
  split over the registered rough model; `ground-join` its one after-step; the plan's code ground the named
  fallback). A terrain row lies round the floor, not on it: `fits the plan` counts it (`align.ROUND`).
- **The Earth kit** is the adapter `KIT` (layer `kit`, after-step `kit-sections`, `../earth_seed`'s overlay); its
  `earth-kit` row bakes only the named code fallbacks, the rows not handed. No kit row is handed in yet: the loop
  lacks a per-take turn into the kit frame for the bake, and a model-less row stops the line at `likeness` instead of
  leaving a gap. Neither is the adapter's to close.
- **Not moved yet** (#41's other agents): people, the motion rows. Each joins as an adapter here; its side route goes.
- Test: `shapes_first_test.py` (`.venv/bin/python -m pytest score/stages/shapes_first`), no spend.
