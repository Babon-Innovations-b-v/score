# score/stages/cast/

The cast stage (experimental, design 5 of 2026-10-12): row `cast@<place>` for the places whose locked design shows
people, read from `data/people/rows.json` (`score/stages/people_rows.py`, #26: its scene inventory's people rows,
each person a look of the shared people line, a crowd one far look in a few variants of its body), never the old game records
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
  put the design right (`python -m score.stages.people_refresh` refreshes rows.json from the store and keeps each row's
  looks while its concept stands).
- **A seated person sits on its seat** (`on_support`, 2026-11-04: 8 seated people sat on the floor in a ground-sit).
  rows.json carries each row's reading `anchor`; a sitting row anchored `on:<seat>` (its id's words name one,
  `people_rows.seat_of`) plays the `seated` clip and is put on the nearest seat of that row not taken, measured on the
  laid objects (the cast and sim-body read the surface line's bakes, so `layer_base.built` lays them): its feet on the
  seat's floor under its middle, `seat` its height (`measure.seat_top`), measured from the seat's top and clear of
  all but its own seat; one whose row lays no free seat (none laid, all taken, or no surface `SEAT_LOW` to
  `SEAT_REACH` over its floor) stands on clear floor by its spot instead (`unseated`, nudged like a group member),
  named as a finding of `standing` (2026-11-10: camp's office chairs never laid, airlock's bench top 0.19 m); the
  seat's fault is its row's to fix. Any other anchored person is raised
  onto the top of its anchor's item under it, never lowered.
- **A crowd keeps clear of its plan's views** (`plan_views`: the plan row's output, an `after`, its views as the
  scene record writes them), never a hand-written record's (data/scene's game shots) or kit: the cast reads only
  the design, the seed, the environment's eye height and the rules (2026-10-21). They are read only for a crowd with
  ground; a plan spot looking at no plan item (the camp's, at its kit's objects) is refused by name.
- **A person its design stands on stairs walks its flight** (`stairs_of`, `on_stairs`, 2026-11-04): put
  on the plan's flight nearest its spot over its height whose every tread a body walks clear of the laid solids
  (`clear_run`; none clear: the nearest, on its longest run of clear treads, else whole for `clear` to name)
  (writer.stair's, as the scene record lays it), on its first (clear) tread the way it walks, facing its last (clear) one, with `stairs` (its way, flight, last tread, rise and run) for the
  scene-made clip; never nudged onto level ground (`climbers_of`), judged where it stands.
- **Measured on the geometry, never on a box.** Bodies are cast_check's cylinders tested against the triangles of
  the seed's base layer (FCL); a point instancer's prototypes are left out (they stand only where it copies them).
- **Do not import tools/characters at load.** Its `cast_check` on the path or in `sys.modules` joins the assembly's
  code version through `tools/usd/reach.py` and moves every place's assembly key: `measure.characters()` imports
  `cast` and `cast_check` inside the make and the gates, and the stage declares both files as inputs. Constants
  copied from them (body sizes) are checked in `test_people_stand_clear_or_are_named.py`.
- **`made` reads the SOMA-shell route's dress rows.** A look is made when its dress row (`people-dress-<look>`,
  `-in-<surface>` where the person's design row wears a fabric of its own: `../people_clothes.py`) stands usable; the cast reads them as optional
  inputs (`Stage.optional`), so a look with none stays not made, named: `made` passes with it as a finding (an accepted gap carried
  down, never a stop: the owner's rule, 2026-10-13), and complete's people check fails it by name.
  `drapes` is retired (2026-10-13): the SOMA-shell rig replaced the drapes route (owner, 2026-10-12 21:40), and the
  people rows' per-clip, shell and outline gates judge the cloth now.
- **A crowd's palettes are its look's dress variants** (`people_rows.crowd_record`, `CROWD_VARIANTS`): each copy
  wears one variant's dressed body (`people-dress-<look>-v<n>`, the scene library's surfaces, baked), a prototype per
  clip, phase and variant (`layer.lay_crowd`); never cast.py's flat palette colours. A variant with no usable body is
  named missing and its copies left out, never worn in another's body.
- **The characters layer** (`layer.py`, row `characters-layer@<place>`) lays each person of the accepted cast in
  their own look's accepted dressed body (`people-dress-<look>`); a person whose cast names no look, or whose look has
  no usable body (its dress rows are optional reads, `Stage.optional`), is left out, named in `characters.json`,
  and the row fails its `bodies` gate naming each person with no body (`driven.judge_bodies`; the owner's GAP rule,
  2026-11-05: a place with a person with no body fails, so a body never made cannot pass silently; it replaced the
  overseer's pass-with-findings of 2026-10-13; in driven.py, not layer.py's `laid`, which the cast, scene-record and
  scene-clips rows import); a crowd with no copy stood is the cast's `counted` gate's. Each finding starts
  "<name>: ", so a place's recorded gap (`stages.GAP_GATES["characters-layer"]`, `data/checks/gaps/<place>.json`)
  moves its bodiless people to complete's people check by name and the place's line goes on (2026-11-10: the people
  ship as named fails). Never lay a stand-in body.
- **A person moves by its sim body** (`driven.py`, #65, PRD #56): where the place's `sim-body` row stands (an
  optional read of the characters layer, with `people-clips-made`'s rig), each person's skeleton plays its sim body's
  joints and root path and the sim body is laid beside it; one without keeps its clip, named. Gate `on its sim body`:
  feet within `FEET_WITHIN`. Never tune the gate to pass: the sim body is built at the person's own size (its
  `size`), and the skin's Hips are sized by the skin's size over it.
- `test_people_stand_clear_or_are_named.py` stands people on a toy place of its own (a floor and a crate), runs the
  crowd rules on small crowds and plans, and makes the characters layer with no dressed body (every gap named).
