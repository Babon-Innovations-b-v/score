# score/stages/props/

The prop route as rows of the stage table (`__init__.py`): every object goes the prop route first, and only one whose
measured checks fail is built in code and checked again (owner, 2026-10-12, flipping the parts check's order). Rows:
`props-inputs` (free, the box gate), `closeup` (paid, Nano Banana Pro through `tools/props/closeup/pro.py`), `pixal`
(paid, `tools/cloud/batch.py`), then the surface line (its first row waits on `pixal`), then `likeness` (free;
DINOv2 evidence gathered, paid). These rows are the shared loop's (`../shapes_first`, #41): the table takes them from
`shapes_first.rows()`, and `props-inputs` waits on `rough-align` and holds every row to the registered floor.
Environment data (`prop_data.py`): a designed place's hand-in, `{home}/design/props/<place>.json` (`prop_data.DESIGN`,
written by prepare from the takes it priced: `../complete/prepare/handin.py`; it is also the scene inventory its rows
are drawn and built from, each box of its reading `grounded`: SAM 3's, else Gemini's region, said which; the box
gate passes it), else
`data/props/<place>.json` (the ship rooms', the people's line).

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json` that names the place, the prim or pattern, what it is, why it is not from the
  library, who allowed it and when. Every finish is a library surface (`data/library`, the ProcFunc recipes and
  palette tokens): never a picture's own texture, a model's baked-in colour, a default grey or anything else; a
  picture-made model keeps its geometry and gets its finish replaced. The library check
  (`score/stages/complete/library`) lists what does not trace; bible `architecture/components`.
- **No existing key may move.** The rows apply only to a place with prop data, so environment 1's nodes read without them
  (`Runner.reads`). Never put a tool folder on `sys.path` at import: `_code` hashes a bare name's file in every folder
  on the path, so one more folder adds files to other stages' code versions. Import the prop tools inside functions
  under `prop_data.tools(...)`, which takes the folders off again, and declare the tool files a row runs in its
  `files` (`prop_data.*_TOOLS`). Import this package's modules by their full name (`import
  score.stages.props.prop_data as prop_data`), never `from score.stages.props import ...`: that hashes `__init__.py`,
  and a table or check edit would re-buy every close-up and model. `props_test.py` holds both.
- **The likeness gate** (`likeness.py`, `likeness_row.py`) is `tools/usd/compare.py`'s candidate check on the model
  alone: silhouettes from eight ways round, no renderer. `OUTLINE_LEAST` was set on the hub's twelve accepted
  round-six generated models with a 0.05 margin (`likeness.py measure`). DINOv2's least is set the same way by the
  paid row `likeness-calibration@<place>` (`calibration_row.py`, about EUR 0.43) on the accepted models the prop data
  names (`accepted`); without it the `likeness` check answers unknown and blocks. A designed place's hand-in names
  none, so it has no calibration row: its DINOv2 scores are measured and shown, never judged (`measured_only`), and
  `outline` holds its likeness (#10). Change a threshold only by measuring the accepted set again.
- **A take a paid step failed is a batch gap, never a stop** (`../batch_gaps.py`, score's overlay): `closeup` names
  each object no Pro take passed, `pixal` each take its batch brought no model back for (carrying the close-up's), in
  `batch-gaps.json`; their gates still fail them by name and the table moves those faults. `likeness` reads the rows
  that write such gaps and carries them all to complete, each with its hand-in object and inventory rows; it declares
  a take's Pixal3D input only where it is there. A batch whose command fails as a whole still stops `pixal`.
- **The comparison** (`compare.py`) runs one place prop-first and code-first, each in its own data copy and store
  under `$PROPS_HOME/compare/<place>/`, and writes the table and review page there. Run it with `--detach`; it spends,
  every ledger line tagged `compare-<place>-<order>` (`ledger_tag/`).
