# score/stages/scene_record/

The scene-record stage (experimental, PRD #6): a place's scene record made by SCORE from its plan and concept, not
transcribed from the game. `__init__.py`'s docstring has the rows; `plan.py`, `writer.py` and `gates.py` theirs.

- **The plan is the input** (`data/plans/<place>.json`): its walls, doors, items and standing spots, plus what the
  writer needs that the old plans lacked, written into the plan itself: `leads` (each door's side: `to` a place,
  `outside` or `sealed`, `why`, and for a joined door `joins` and `door`, for a leafed one `leaves`), `rows` (each
  plan item's inventory rows; a zone names none) and `elements` (the concept read element by element: `rows`, a plan
  `door`, or a `drop` with its reason). A place has the rows only when its plan has `leads` (`written`).
- **The writer never reads the old record.** `data/scene/<place>.json` is an unverified seed that only `seed-matched`
  reads; a seed entry the writer leaves out on purpose needs a reason in `gates.SEED_REASONS`, never a quiet drop.
  Numbers that moved are shown on the page, never judged.
- **Nothing cites the game** (`game-free`): every `from` names the plan element, inventory row, ground seat or world
  record it was made from. The world's sky and room fill come from `data/definitions/sky.json`, itself an unverified
  seed (the old records' shared numbers) until the light stage's sweep sets them against each concept.
- **Neighbours come from the made ground's seats** (the terrain stage's ground records), the ball's curve turning each
  (`rotation`); a door joined to another place's door stands the tube's stage between the two doorways, stretched
  to the run. A place with no seat on a made ground cannot be judged outside: `openings` fails it by name.
- **Two shell writers so far**, by the plan's `shell`: `domed` (walls with a dome: room_walls, room_deck, dome_roof,
  doors in each wall's middle) and `kit` (`kit_shell.py`: the Earth's rooms and open places, whose kit holds their
  walls and floors; the record adds the block round a room, a light at each lamp of the sky record's lamp rows the kit
  lays, the body's night, moon, glow and harbour, the plan's `objects` and `shows`). A kit shell's plan stands in the
  kit's frame by its `frame` (an anchor, and a `toward` for a plan drawn down a view); its doors are the kit's
  doorways (`plan-matched` holds each to the plan within 0.05 m along its wall), a door's fifth number its sill's
  level, its lead `<side>@<level>` where a wall has doors at several levels. Another kind of place (the hangar's flat
  roof, the hub's facets) needs its own shell writer here before it gets the rows; the writer refuses it.
- **The plan's inventory** is `data/inventory/<place>.json`, or the plan's `inventory` name (the prologue's rooms keep
  `prologue_flat`, `prologue_stairwell`). Never add inventory rows for a record: every place's assembly declares the
  whole inventory folder, so one changed file makes them all again; a concept element still waiting on rows is a
  `drop` with that reason.
- **No assembly reads the record yet.** It lands in the store as `record/<place>.json` (today's schema, so
  tools/usd/scene.py builds it unchanged); the assembly takes it when its builder from records is wired.
- Run the proof with `python -m score run world1 --place garage --stage scene-record --detach`; the test is
  `scene_record_test.py` (the garage's plan and record and the stairwell's record, each gate's fault).
