# score/stages/shapes_first/

The shared loop (#41; CONTEXT.md "shapes first", "layer adapter", "prop pipeline"): the one way every model layer
gets its models, as rows of the stage table, the same for a prop, a shell piece, a ground detail area or a plant.
`__init__.py`'s docstring has the order; `align.py` the registration; `made.py` what an after-step gets back.

    plan -> rough-model -> rough-align -> props-inputs (parts split) -> closeup -> pixal
         -> finish route (surfaces.ROWS) -> likeness -> each adapter's after-steps

## The interface (for a layer adapter)

- **Hand in rows.** A layer hands the loop its rows in the place's hand-in record, `data/props/<place>.json`
  (`prop_data.py` has the form; a designed place's is its design's, `{home}/design/props/<place>.json`, which prepare
  writes from the takes it priced, each row's layer by its route: `../complete/prepare/handin.py`): one `objects` entry per inventory row, with `"layer": "<your layer>"` (no `layer`:
  `objects`; read by `props/closeup_row.layer_of`, kept out of `prop_data.py`, which half the table's paid rows
  hash). The concept and the plan are the place's (the plan names its concept); the loop reads them itself. Nothing
  else makes a model: a row on the code route only with its pipeline failure named in its record.
- **Register.** Add `Adapter("<layer>", after=(<Stage>, ...))` to `ADAPTERS` in `__init__.py`. `rows(adapters)` gives
  the table the loop's rows and then each after-step, which applies only where the place handed rows of that layer
  (and where its own `applies` says). Two adapters on one layer are refused.
- **After-steps.** Each is a place row whose `after` holds every key of `made.ENDS` (`props-inputs`, `surfaces-bake`,
  `surfaces-parts`, `likeness`); one that does not is refused at import. Its make calls
  `made.made(inputs, "<layer>")` and gets `{row: {"route": "prop", "model": <baked .gltf>, "take", "finishes":
  [<surfaces-parts part rows>], "failures": {<step>: <the record's named failure>}}}`, `{"route": "code", "model":
  <code build>, "finishes": []}` or `{"gap": <why>}`. A step made outside the loop is named in the row's record
  entry (`"failures"`, carried through `props-inputs`' rows.json), never left to prose.
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
- **The kit** is the adapter `KIT` (layer `kit`, nothing after the model, `../earth_seed`'s overlay): a scene's shell
  pieces and fittings as rows. The old kits' rows (`earth-kit`, `kit-sections`) went with the old kits (2026-10-21);
  a scene's own shell is its earth seed's, laid from its locked plan.
- **A line no place owns** (`align.NO_PLACE`, the people's): a layer whose models are no place's runs the loop on a
  line of its own name, with its hand-in record, rows and surface data under that name (`data/props/people.json`,
  `data/inventory/people.json`, `data/surfaces/people.json`). It has no plan, so no rough model or registration, and
  `fits the plan` holds its rows to none; a place's own rows (assembly, complete, the library hand-over:
  `stages.PLACE_ONLY`) do not apply there (`no_place`). It is no place of the environment's (`stages.places`), so a
  whole run leaves it out: run it by name (`--place people`). Its after-steps are place rows on that line; a world row
  reads one beside, `neighbours` naming the line (`people_bodies/bodies.the_line`).
- **Not moved yet** (#41's other agents): the motion rows. Each joins as an adapter here; its side route goes. The
  people's adapter (`PEOPLE`) is in, its one after-step the hand-on (`people-made`).
- **Named exception: the people's motion steps stay world rows.** Each look's parts, body (build, the people route,
  checks) and dress, and the clips, are world rows of their own (`../people_bodies`, `../people`) so the looks run
  side by side, each a node of its own; they read the hand-on beside (`neighbours`), so `after_step`'s check does not
  reach them. Each look's record (`data/props/people.json`, `failures`) names what is still made outside the loop:
  its second split (`people-look-parts-<look>`) and its body built from the raw take, not the baked model handed on.
  Its take is the loop's (closeup and pixal on the line, each row drawn from the design's person that maps it, #26;
  the take rows were deleted 2026-10-21).
- **No model around the loop** (`shapes_first_test.py`): a row of the table that reads a loop row and is no
  adapter's after-step reading `made.ENDS` fails, unless `READS_THE_LOOP` names it with why (the judges, the object
  layer's assembly, the scene's base painting its shell, the motion rows not on an adapter yet); a paid row outside the loop says
  what it makes (`MAKES_NO_MODEL`) or is a named exception (`MADE_OUTSIDE`) its own record names (`failures`). A row
  joins either list only with its reason; one that stops reading the loop leaves `READS_THE_LOOP`.
- Test: `shapes_first_test.py` (`.venv/bin/python -m pytest score/stages/shapes_first`), no spend.
