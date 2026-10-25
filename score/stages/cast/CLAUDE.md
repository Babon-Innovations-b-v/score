# score/stages/cast/

The cast stage (experimental, design 5 of 2026-10-12): row `cast@<place>` for the places whose locked design shows
people, read from `data/people/rows.json` (`score/stages/people_rows.py`, #26: its scene inventory's people rows,
each person a look of the shared people line, a crowd one far look in palettes), never the old game records
(`data/characters/`). `__init__.py`'s docstring has the make and
the gates; `measure.py` the geometry, `spread.py` how a group and a crowd are stood on the place.

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json` that names the place, the prim or pattern, what it is, why it is not from the
  library, who allowed it and when. Every finish is a library surface (`data/library`, the ProcFunc recipes and
  palette tokens): never a picture's own texture, a model's baked-in colour, a default grey or anything else; a
  picture-made model keeps its geometry and gets its finish replaced. The library check
  (`score/stages/complete/library`) lists what does not trace; bible `architecture/components`.
- **The design says who, the stage says where they fit.** Each person is dealt to the plan's people spots in turn and
  stood on the seed's measured ground round it, clear of every solid and of each other, or left out and named; a
  design's crowd stands on the plan items its row makes (rows.json's `ground`, taken from the plan on every refresh),
  as many as SAM 3 counted, else as many as fit packed (one mass SAM 3 could not part: it asks the copies that fit, and fails only when none do); a crowd row with no plan item
  has no ground, and `counted` names it short. Never hand-place a person to pass a gate:
  put the design right (`python -m score.stages.people_rows` refreshes rows.json from the store and keeps each row's
  looks while its concept stands).
- **A crowd keeps clear of its plan's views** (`plan_views`: the plan row's output, an `after`, its views as the
  scene record writes them), never a hand-written record's (data/scene's game shots) or kit: the cast reads only
  the design, the seed, the environment's eye height and the rules (2026-10-21). They are read only for a crowd with
  ground; a plan spot looking at no plan item (the camp's, at its kit's objects) is refused by name.
- **Measured on the geometry, never on a box.** Bodies are cast_check's cylinders tested against the triangles of
  the seed's base layer (FCL); a point instancer's prototypes are left out (they stand only where it copies them).
- **Do not import tools/characters at load.** Its `cast_check` on the path or in `sys.modules` joins the assembly's
  code version through `tools/usd/reach.py` and moves every place's assembly key: `measure.characters()` imports
  `cast` and `cast_check` inside the make and the gates, and the stage declares both files as inputs. Constants
  copied from them (body sizes) are checked in `cast_test.py`.
- **`made` reads the SOMA-shell route's dress rows.** A look is made when its dress row (`people-dress-<look>`,
  `-in-<surface>` where the person's design row wears a fabric of its own: `../people_clothes.py`) stands usable; the cast reads them as optional
  inputs (`Stage.optional`), so a look with none stays not made, named: `made` passes with it as a finding (an accepted gap carried
  down, never a stop: the owner's rule, 2026-10-13), and complete's people check fails it by name.
  `drapes` is retired (2026-10-13): the SOMA-shell rig replaced the drapes route (owner, 2026-10-12 21:40), and the
  people rows' per-clip, shell and outline gates judge the cloth now.
- **The characters layer** (`layer.py`, row `characters-layer@<place>`) lays each person of the accepted cast in
  their own look's accepted dressed body (`people-dress-<look>`); a person whose cast names no look, or whose look has
  no usable body (its dress rows are optional reads, `Stage.optional`), is left out, named in `characters.json`,
  and the row passes with the gaps as findings, so the place assembles and complete's people check fails each gap
  by name (overseer, 2026-10-13). Never lay a stand-in body. `layer_test.py` holds it.
- `cast_test.py` runs the make and gates on a one-person design on the hub's seed (skipped without it).
