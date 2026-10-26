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
- **Thin straight things are built in code** (`thin_straight.py`; owner, 2026-10-25: "Yes, code-build thin straight
  things"): `pixal` sweeps a row slender by `gates/model.py`'s rule and named for a straight kind (a railing its posts at
  most `POST_GAP` apart under a top and a mid rail) or of a kind that glows (a stem lamp's post, a light
  bar, a strip or string of lights: its light the library's lamp, laid by the light layer), whose every Pro take
  failed, as its take's files (raw, slimmed, final stood by the finish's own turn, `input.png` its concept crop cut by the row's own SAM 3 mask, never its box,
  `code.json`), so the finish route paints it and `likeness` holds it to that crop, turned upright or level first by its mask's long axis (`likeness_row.straight_cut`: the crop is the concept's slanted view, and a thin line's outline fell to 0.02 at 30 degrees; an upright one turned at most 45). The direction is the picture's, the metres the box's: a box the reading stood upright over a run its mask shows lying is built lying (`thin_straight.stands`). A mask that is not one straight run (`one_run`: a bent pipe network, a sag, a railing's ladder, a bundle of parallel lines) is followed instead (`path_build`, owner's ask 2026-10-26): skeletonised, traced (forks kept), seen back from the close-up's look-down in a wall's plane (a ground's for a row whose height is its thinnest side), its longest reach the row's longest side, one closed tube surface (marching cubes over the runs' distance) the line's thickness, at most the box's middle side; its cut is the mask as it is, turned only by the finish stand's small in-plane turn of it (`stand_tilt`, at most `STAND_EXCUSE`: the stand finds up from a model's box and walls, every pose alike, and leaves a planar network a little turned; a larger turn stays and fails). One route a kind in a place (`thin_straight.kin`; owner, 2026-10-26: mixed pipes "will prob look bad"): once one thin straight row's close-up fails, every thin straight row sharing a kind word with it is built too, its close-up passed or not, and prepare predicts it so. `pixal` drops its close-up
  gap (the finish route skips a gapped take); `likeness` carries it again only while a free check fails the build. A
  close-up that passes later removes the build and Pixal3D makes the take, unless a row of its kind still fails. Keep `likeness_row` out of its imports:
  the paid rows' code must not hash the checks (`props_test.py`), so the shared cut-out (`cut_out`) lives there.
- **A thin straight row's mask can be made before its close-ups fail** (`masks_row.py`, row `straight-masks`, paid,
  one SAM 3 card a place, `--object` narrows it): thin_straight's own masks and cuts of every thin straight object, read
  only by prepare's prediction (`predict.straight_outcome`), which builds each in code and holds it free to the
  likeness rules. The table adds it in score/stages/__init__.py after the library rows: in this package's table or
  shapes_first it would re-key most rows (their code versions hash those modules).
- **Flat sheets are built in code when their take made no model** (`flat_sheet.py`): a row lying flat (its close-up
  drawn from straight above) under `SHEET_SHARE` of its longest side tall (a poster, rug, note, paper, mat) whose
  Pixal3D take or its finish made no model is laid as its own close-up's outline (convex hull, cut out by
  `flat_sheet.cut_out`: off the border-fitted backdrop by an RGB distance, so a cream note on a grey backdrop is
  the note, not its drop shadow) at the row's size, its take's files thin_straight's with `code.json` naming the rule,
  so the finish route paints it with a library surface and `likeness` holds it to that close-up. The prop route first: only a failed take is built, and the build is
  kept (no close-up removes it). The finish's own fault for such sheets was `glb_file.upright_turn --flat` giving a
  side square to up no sign (a NaN turn); fixed 2026-10-26, so this route is the net, not the way. A sheet laid
  thinner than the model gate's 3 mm wall is held to being solid through its thickness (`gates/model.py least_wall`).
- **A take a paid step failed is a batch gap, never a stop** (`../batch_gaps.py`, score's overlay): `closeup` names
  each object no Pro take passed, `pixal` each take its batch brought no model back for (carrying the close-up's), in
  `batch-gaps.json`; their gates still fail them by name and the table moves those faults. `likeness` reads the rows
  that write such gaps and carries them all to complete, each with its hand-in object and inventory rows; it declares
  a take's Pixal3D input only where it is there. A batch whose command fails as a whole still stops `pixal`.
- **The comparison** (`compare.py`) runs one place prop-first and code-first, each in its own data copy and store
  under `$PROPS_HOME/compare/<place>/`, and writes the table and review page there. Run it with `--detach`; it spends,
  every ledger line tagged `compare-<place>-<order>` (`ledger_tag/`).
