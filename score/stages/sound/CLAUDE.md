# score/stages/sound/

The sound stage (the paper's Methods, "The canonical scene": sound, and "Shape and surface apart": sound by MOSS;
experimental, PRD #6, until the owner has heard it): row `sound`, one per place in `data/sound/places.json`. It makes
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
- **Every source has a sound.** A place's sources are its room tones, what the suit lets through, its `objects` and
  `voices` (`data/sound/places.json`), its inventory rows' `sound`, its motions' `sounds`, the sounds
  `data/sound/moving.json` gives its moving things and silent motions (`moving.py`: a hatch's latch as it opens, a rover's
  drive over its drive, timed off the record's own moves, so a moving thing that stops moving stops sounding) and the whole
  surface bank (`data/sound/surfaces.json`). That table names only picked sounds; one still to make is in its
  `wanted` until its brief is written and made. A new source gets its brief (`pick` with `prompts`) in `data/sound/sounds.json`, its
  category setting its loudness, and the stage makes it; never a file by hand.
- **A sound picked already is taken as it is** (from the library, tools/library; its credit off `data/sound/licences.json`, its CLAP
  score `chosen.clap` measured when it was made); only one whose files are off its category's loudness is levelled
  here, its volume moved so it plays as loud as before. Only briefs no environment file answers are made, MOSS on one rented
  card in the moss image (`takes.py`, through `tools/cloud/images/prove.py`), chosen by the picker's rule.
- **Takes are kept in `~/.cache/farm-factory/sound-picker/moss/stage/`** named by sound, the hash of prompt, length and
  weights, and seed, with their CLAP scores: the same brief is never paid for twice. Change a prompt to get new takes.
- **One batch, one take a sound** (#21, #29): the library match and the loudness are decided free before it (a
  sound with a library file is taken, levelled here); each sound still to make is one job, its brief's first prompt
  at seed 1 (`takes.SEED`), made once, the card's deadline its takes' minutes. The gates sort: a take under
  `CLAP_FLOOR` fails `likeness`, a take that did not come back leaves its sound without one and fails `sources`;
  either is a hole, and a new take (another seed, the brief's next prompt) is a new batch, never inside this one.
- **One take across places** (#29): a brief several places play (crew_talk, in eight) is one take. Each take is
  locked while its batch runs (`takes.held`), so the first line to reach it makes it on its card and the others wait
  and read it; a take its batch asked for and did not get (lost, failed, no card) is a named failure and a hole on
  every place that plays it, never asked again by a waiting line (`takes.asked_here`: one ask a take a score run, the
  run's `SCORE_RUN_ID`); new spend on it is a new batch, another run. `environment_takes` (free) lists the environment's takes still to make, each once with the places that
  play it, and the price's `sound_takes` forecast rule counts each at its first place, so it is priced once.
- **One sound, one name** (#46): a surface's steps are `footsteps_<surface>` in `data/sound/surfaces.json` and
  `sounds.json`; a sound two names would play the same files under is one name (the fallback footstep is
  `footsteps_steel_plate`), so the library holds it once.
- **What a place needs is worked out free** (`needs.py`, #29): its bed (room tones), one event sound for each thing
  that moves (its motion and moving things records; things moving exactly together are one event) and a voice where its
  cast stands people (`voices` in `data/sound/places.json`, each on a person, played at `/<place>/Characters/<name>`).
  Each need is answered from the library, by a brief this row makes, or not at all; the holes check shows the last
  two (`score/stages/complete/holes/layers.py`), and the `events` and `voices` gates fail a place's output that
  leaves one silent. Keep needs generic: read them off the records, never a list of places.
- **Unit cost: unknown** in `data/costs/per-unit.json`: no take's work seconds are on a ledger in git (the 2026-10-06
  game batch, 244 takes on one L4 in 122.9 card minutes with set-up, timed none; environment 1's run of 2026-10-12,
  about 4 min to the first take and about 28 s a take of 10 to 15 s, EUR 0.72 for 56 takes, was written here, its
  ledger lost with the old disk). The benchmark that settles it is on #29.
- **The owner's recordings stay** (2026-10-06: the breathing, the sliding doors and the steel footsteps were better
  than the generated takes). `no freesound` passes them by their `chosen.by` owner with his decision and lists them,
  and passes a Freesound recording under CC0 with its licence row in `data/sound/licences.json` (the owner's
  exception, 2026-10-20, #29; the row read from that file, never the record's own credit); any other Freesound file
  fails it. Replacing them is his call, not the stage's.
- **Never lower `gates.CLAP_FLOOR` to pass a sound**: write a better prompt (what it is, its size, material and
  place, and what is not in it). The floor is the tenth percentile of the environment's 55 MOSS picks.
- `sound_test.py` runs the make and the gates on the hub and the airlock (nothing rented: the airlock's voice, still
  to make, left out) and breaks each gate once.
