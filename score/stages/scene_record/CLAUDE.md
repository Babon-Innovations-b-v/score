# score/stages/scene_record/

The scene-record stage (experimental, PRD #6): a place's scene record made by SCORE from its plan and concept, not
transcribed from the game. `__init__.py`'s docstring has the rows; `plan.py`, `writer.py` and `gates.py` theirs.

- **The plan is the input** (`data/plans/<place>.json`): its walls, doors, items and standing spots, plus what the
  writer needs that the old plans lacked, written into the plan itself: `leads` (each door's side: `to` a place,
  `outside` or `sealed`, `why`, and for a joined door `joins` and `door`), `rows` (each
  plan item's inventory rows; a zone names none) and `elements` (the concept read element by element: `rows`, a plan
  `door`, or a `drop` with its reason). A place has the rows only when its plan has `leads` (`written`).
- **The writer never reads the old record.** `data/scene/<place>.json` is an unverified seed that only `seed-matched`
  reads; a seed entry the writer leaves out on purpose needs a reason in `gates.SEED_REASONS`, never a quiet drop.
  Numbers that moved are shown on the page, never judged.
- **Nothing cites the game** (`game-free`): every `from` names the plan element, inventory row, ground seat or environment
  record it was made from. The environment's sky and room fill come from `data/definitions/sky.json`, itself an unverified
  seed (the old records' shared numbers) until the light stage's sweep sets them against each concept.
- **Neighbours come from the made ground's seats** (the terrain stage's ground records), the ball's curve turning each
  (`rotation`); a door joined to another place's door stands the tube's stage between the two doorways, stretched
  to the run. A place with no seat on a made ground cannot be judged outside: `openings` fails it by name. Only the
  neighbours the place's own views see stay in its record (`seen.py`: in a view's frame, at least 0.5 degrees across,
  nothing of the place's own seed or made ground between; glass, windows and portholes seen through), and the nearest
  place of each stage a doorway opens onto; of the base the old station's views see only the hangar (2026-10-13).
- **Shell writers**, by the plan's `shell`: `domed` (walls with a dome: room_walls, room_deck, dome_roof,
  doors in each wall's middle) and `kit` (`kit_shell.py`: the Earth's rooms and open places, whose kit holds their
  walls and floors; the record adds the block round a room, a light at each lamp of the sky record's lamp rows the kit
  lays, the body's night, moon, glow and harbour, the plan's `objects` and `shows`). A kit shell's plan stands in the
  kit's frame by its `frame` (an anchor, and a `toward` for a plan drawn down a view); its doors are the kit's
  doorways (`plan-matched` holds each to the plan within 0.05 m along its wall), a door's fifth number its sill's
  level, its lead `<side>@<level>` where a wall has doors at several levels. `outdoor` (`outdoor.py`: the wreck, the
  old station, the camp grounds, the camp) has no walls of the record's: the plan's w and d are its site, laid by its `frame`; the record
  holds the body's outdoor sky from `sky.json` (its ways in the body's own frame, turned into each place's by its
  seat: suns, the Earth over the Moon, Mars's air, dust and sky dome) and the plan's `lamps`, `decals`, `beams`,
  `blocks` and `objects` stood on their rows' laid spots over the made ground; its views and the `openings` viewers
  stand on the made ground. The camp is `outdoor` with `inside`: its kit holds its domes, its lamps are lit where the
  kit hangs them, its furniture is plan `objects` (the released camp models) on its own floor, its views stand on its
  deck. A domed plan's `shape` picks its writer:
  none, a capsule (glazed when the room layout says `glass_dome`: the greenhouse); `faceted` (the hub: facets,
  apothem, `turn`, `pit`; walls, pyramid_roof, the deck round its sunken pit, the pit's walls and floor; doors
  `[bearing, wide, what]`, leads by bearing); `tube` (a walkway tube: radius, axis, length, `glass` bands; hull arcs,
  glass, deck; its two open ends `near` and `far`, its frame anchored at the near end). A sloped item outside (`2.5 m
  at 20 deg`, the airlock's ramp) is a plain plate, a `plot` item soil in a curb (it names no rows; an element may
  name it as `item`), and an inventory row made by the route at its own spots (the hub's console) or naming an environment
  release model (`release_model`: the airlock's suit) an object, as is a door leaf a lead names (`leaf`: the airlock's
  outer door, which its cycle's motion moves and copies for the inner door). `flat` (the hangar: capsule walls and deck, a roof of
  four slabs on the walls' top round the room layout's door `opening`, a `roof_door` plan item naming no rows; its roof
  leaves are the hangar's own objects, row `roof_leaf`, laid by its kit, never places of the record).
- **An object carries what its kit model stands on it** (`writer.kit_children`: the kit model's `children`, each with
  its glow parts, its row the inventory's, less removed rows): the camp's rack cases, desk screens and radio, the hub
  console's screens and tools. `seed-matched` compares a matched seed entry's children by model, so a dropped child
  fails by name (the camp's rack cases went missing unseen, 2026-10-13).
- **A plan may remove rows the concept does not show** (`removes`: row, date, why): the record carries them as
  `coordinator_removed` (`rows`), and the assembly's relay_kit takes every seed object of those rows out of the base (the
  old station's cables, 2026-10-13).
- **A plan object stands on what holds it up**, not at the plan's level: its model's lowest point (scaled to its
  `height`) on the top of the kit's floor pieces under its middle (else the plan's floor at its level), or on the made
  ground outside (`kit_shell.support`, `model_low`; the launch's rocket stood 6 mm into its pad, 2026-10-13).
- **The far ground is the plan's** (`far_ground`: reach, step, the ball's surface, why): a place that sees the ground
  to its horizon (the outdoor places, the camp's domes, the hub's portholes, the greenhouse's glass) gets the
  record's `planned_ground`, so the export draws the made ground out past its near patch and the ball under it; left
  out, the horizon renders as a flat haze band (the camp, 2026-10-13). A plan beam may stand on another place's row
  (`place`: the camp sees the camp grounds' mast beam), on the first piece of it that place's kit lays.
- **A lead may stand its leaf open** (`moves`: the kit piece's node, `by`, why; the record's `moved`, as the
  motion stage's `rests: open` expects): the flat's balcony leaf, 1.4 m south. `plan-matched` sweeps each moved
  piece's box along its path and fails on any other kit piece deeper than 1 cm in it (the leaf slid north ran
  into the TV, 2026-10-13).
- **Seed reasons can name a family** (`<section>/<start>_`, kept to one place with `<place>:`), so the greenhouse's
  old bed boxes need one reason and it never excuses another room's.
- **The plan's inventory** is `data/inventory/<place>.json`, or the plan's `inventory` name (the prologue's rooms keep
  `prologue_flat`, `prologue_stairwell`). Never add inventory rows for a record: every place's assembly declares the
  whole inventory folder, so one changed file makes them all again; a concept element still waiting on rows is a
  `drop` with that reason.
- **No assembly reads the record yet.** It lands in the store as `record/<place>.json` (today's schema, so
  tools/usd/scene.py builds it unchanged); the assembly takes it when its builder from records is wired.
- Run the proof with `python -m score run world1 --place garage --stage scene-record --detach`; the test is
  `scene_record_test.py` (the garage's plan and record and the stairwell's record, each gate's fault).
