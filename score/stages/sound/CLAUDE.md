# score/stages/sound/

The sound stage (the paper's Methods, "The canonical scene": sound, and "Shape and surface apart": sound by MOSS;
experimental, PRD #6, until the owner has heard it): row `sound`, one per designed scene (`score/stages/design_layers.py`,
the stage table's and the assembly's one answer: every scene with a design has its sound, and its assembly waits on
it; `beds.places` are the scenes a bed is worked out for). It makes
the place's sound layer data, `sound.json` and its files under `files/`, which the place's assembly writes into its
OpenUSD stage (`tools/usd/sound.py`'s layout). `__init__.py`'s docstring has the make and the gates; `gates.py` the
gates; `takes.py` the paid part.

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json` that names the place, the prim or pattern, what it is, why it is not from the
  library, who allowed it and when. Every finish is a library surface (`data/library`, the ProcFunc recipes and
  palette tokens): never a picture's own texture, a model's baked-in colour, a default grey or anything else; a
  picture-made model keeps its geometry and gets its finish replaced. The library check
  (`score/stages/complete/library`) lists what does not trace; bible `architecture/components`.
- **A scene's bed comes from its design, never a list per scene** (`beds.py`, the owner's agnostic rule): how it is
  heard (a room by its plan, a top scene held by none outside unless its plan says `inside`: the Moon base round
  its modules; outside, through the suit where its body's surface pressure, `data/physics/bodies.json`
  cited or the setting's own, is under the Armstrong limit, else the open air; its body the site's of the outside place
  holding it, `data/physics/setting.json` up `data/places/within.json`), then the library beds whose brief's `bed`
  (`data/sound/sounds.json`: heard, air, shell, ground, shape, nouns, row kinds) fits it: every fitting `layer` and one
  `tone`, the first that asks more than how it is heard, else the first plain one. A new kind of room gets a library
  bed with its own `bed` brief, never a place name; what the design lacks (no plan, no site, no surface pressure) is a
  named gap, never a guess, and fails the row's `bed` gate.
- **Every source has a sound.** A place's sources are its bed, its objects' sounds (each scene inventory row whose
  row kind sounds plays its kind's `sound` from `data/checks/row-kinds.json` at that row), its people's voice
  (`data/sound/voices.json` on the first person its design stands, `data/people/rows.json`), the sounds
  `data/sound/moving.json` gives the motion row's moving things (its `moves.json`, read through the row's `after`) by
  their row kind (`score/stages/row_kinds.py`) and move, never by
  a place's or a prim's name (`moving.py`: a door's latch as it swings open, a vehicle's drive over its path, timed off
  the record's own moves, so a moving thing that stops moving stops sounding; things moving as one, about one named pivot, sound once; things only moving alike, two doors of a row, each sound) and the whole
  surface bank (`data/sound/surfaces.json`). Those tables name library briefs (moving.json a brief for each part of a kind's move, voices.json
  `crew_talk`), each made fresh in the batch like every other sound (all old picks are retired, owner, 2026-10-21); a
  take that does not come back is a batch gap that names the moving thing's event or the person it leaves silent, so
  `events` and `voices` move those faults to it (`stages.BATCH_GATES`, try 4 of 2026-10-25: unnamed tables failed 22
  places' events and 15 places' voices and stopped their lines). A part or voice naming no sound is silent with no gap
  and still fails. A new source gets its brief (`pick` with `prompts`) in `data/sound/sounds.json`, its
  category setting its loudness, and the stage makes it; never a file by hand.
- **Every old pick is retired** (owner, 2026-10-21: every old library sound withdrawn from score_lib, all remade
  fresh): `data/sound/sounds.json` keeps each brief and `catalogue.json` how each sound plays (bus, loop, reach), but no
  file, level or `chosen`; `licences.json` and `loudness.json` are empty. So every sound a scene plays is a brief this
  row makes in the remake batch (priced by `sound_takes`), and a sound with no brief is a gap.
- **A sound picked already is taken as it is** (from the library, tools/library; its credit off `data/sound/licences.json`, its CLAP
  score `chosen.clap` measured when it was made); only one whose files are off its category's loudness is levelled
  here, its volume moved so it plays as loud as before. Only briefs no environment file answers are made, MOSS on one rented
  card in the moss image (`takes.py`, through `tools/cloud/images/prove.py`), chosen by the picker's rule.
- **Takes are kept in `~/.cache/farm-factory/sound-picker/moss/stage/`** named by sound, the hash of prompt, length and
  weights, and seed, with their CLAP scores: the same brief is never paid for twice. Change a prompt to get new takes.
- **One batch, one take a sound** (#21, #29): the library match and the loudness are decided free before it (a
  sound with a library file is taken, levelled here); each sound still to make is one job, its brief's first prompt
  at seed 1 (`takes.SEED`), made once, the card's deadline its takes' minutes. Each failure is a batch gap
  (`take_gaps`, `batch-gaps.json`, `score/stages/batch_gaps.py`) and the row passes: a take of this batch under
  `CLAP_FLOOR` plays and fails `likeness`, its fault moved to the gap (`stages.BATCH_GATES`); a take that did not
  come back usable has no sound, its uses left out of the record (so the assembly plays nothing there) and named in
  its gap. A picked sound under the floor is no take of the batch and still fails. A new take (another seed, the
  brief's next prompt) is a new batch, never inside this one.
- **One take across places** (#29): a brief several places play (a voice, wherever people stand) is one take. Each take is
  locked while its batch runs (`takes.held`), so the first line to reach it makes it on its card and the others wait
  and read it; a take its batch asked for and did not get (lost, failed, no card) is a named failure and a gap on
  every place that plays it, never asked again by a waiting line (`takes.asked_here`: one ask a take a score run, the
  run's `SCORE_RUN_ID`); new spend on it is a new batch, another run. `environment_takes` (free) lists the environment's takes still to make, each once with the places that
  play it (only scenes with a sound row, `needs.sounded`: a scene with an old plan and no design buys nothing, and its
  gaps name work, never a `sound@` node the table lacks), and the price's `sound_takes` forecast rule counts each at its first place, so it is priced once.
- **One sound, one name** (#46): a surface's steps are `footsteps_<surface>` in `data/sound/surfaces.json` and
  `sounds.json`; a sound two names would play the same files under is one name, so the library holds it once.
- **What a place needs is worked out free** (`needs.py`, #29): its bed (`beds.py`), one event sound for each row
  of its scene inventory whose kind moves and a voice where its design stands people
  (`data/sound/voices.json`, on its first person, played at `/<place>/Characters/<name>`).
  Each need is answered from the library, by a brief this row makes, or not at all; the gaps check shows the last
  two (`score/stages/complete/gaps/layers.py`), and the `events` and `voices` gates fail a place's output that
  leaves one silent. Keep needs generic: read them off the records, never a list of places.
- **The design decides, never a list** (owner, 2026-10-21: the framework is agnostic): the row's places, its objects'
  sounds and its people's voice come from the design (plan and scene inventory, kept under `{home}/design` where the
  creator's are, else `data/`; its people, `data/people/rows.json`; its moves, the motion row's) and general rules
  (row kinds, voices.json); no per-place or per-object table.
  What the people say (a speech, a radio call) is not in the design, so the voice is one sound for every place's
  people until a rule or a recorded model call reads it from the concept.
- **Unit cost: measured** in `data/costs/per-unit.json` over the takes each batch's ledger line names (`takes.plan_for`
  writes them; tools/costs/per_unit.py `SOUND_TAKES` holds the airlock's and the square's, written before): two runs
  so far, the airlock's one take EUR 0.23 and the square's 11 for EUR 0.05. Before them (the 2026-10-06
  game batch, 244 takes on one L4 in 122.9 card minutes with set-up, timed none; environment 1's run of 2026-10-12,
  about 4 min to the first take and about 28 s a take of 10 to 15 s, EUR 0.72 for 56 takes, was written here, its
  ledger lost with the old disk). The benchmark that settles it is on #29.
- **The owner's recordings** (2026-10-06: the breathing, the sliding doors and the steel footsteps were better
  than the generated takes) went with every old pick on 2026-10-21 (his word: all old retired); the rule stands for
  a pick of his again. `no freesound` passes them by their `chosen.by` owner with his decision and lists them,
  and passes a Freesound recording under CC0 with its licence row in `data/sound/licences.json` (the owner's
  exception, 2026-10-20, #29; the row read from that file, never the record's own credit); any other Freesound file
  fails it. Replacing them is his call, not the stage's.
- **Never lower `gates.CLAP_FLOOR` to pass a sound**: write a better prompt (what it is, its size, material and
  place, and what is not in it). The floor is the tenth percentile of the environment's 55 MOSS picks.
- `test_a_place_is_heard_as_its_design_says.py` works out toy scenes' beds from their design alone, runs the make and
  the gates on toy records (nothing rented), sounds a new scene from its design alone, and breaks each gate once.
