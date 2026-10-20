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
- **Every source has a sound.** A place's sources are its room tones, what the suit lets through, its `objects`
  (`data/sound/places.json`), its inventory rows' `sound`, its motions' `sounds`, the sounds
  `data/sound/movers.json` gives its movers and silent motions (`movers.py`: a hatch's latch as it opens, a rover's
  drive over its drive, timed off the record's own moves, so a mover that stops moving stops sounding) and the whole
  surface bank (`data/sound/surfaces.json`). That table names only picked sounds; one still to make is in its
  `wanted` until its brief is written and made. A new source gets its brief (`pick` with `prompts`) in `data/sound/sounds.json`, its
  category setting its loudness, and the stage makes it; never a file by hand.
- **A sound picked already is taken as it is** (from the library, tools/library; its credit off `data/sound/licences.json`, its CLAP
  score `chosen.clap` measured when it was made); only one whose files are off its category's loudness is levelled
  here, its volume moved so it plays as loud as before. Only briefs no environment file answers are made, MOSS on one rented
  card in the moss image (`takes.py`, through `tools/cloud/images/prove.py`), chosen by the picker's rule.
- **Takes are kept in `~/.cache/farm-factory/sound-picker/moss/stage/`** named by sound, the hash of prompt, length and
  weights, and seed, with their CLAP scores: the same brief is never paid for twice. Change a prompt to get new takes.
- **One batch, one take a prompt** (#21): each prompt once at `takes.SEED` (1; a brief's `seeds` is the picking
  page's), the card's deadline its takes' minutes. The gates sort: a take under `CLAP_FLOOR` fails `likeness`, a take
  that did not come back leaves its sound without one and fails `sources`; either is a hole, and a new take is a new
  batch, never a second seed inside this one.
- **Unit cost** (environment 1, 2026-10-12, ledger): one L4 a place, about 4 min from order to first take, about 28 s a
  take of 10 to 15 s; EUR 0.09 to 0.13 a place for one brief (8 takes), EUR 0.72 for environment 1's 7 new sounds (56 takes).
- **The owner's recordings stay** (2026-10-06: the breathing, the sliding doors and the steel footsteps were better
  than the generated takes). `no freesound` passes them by their `chosen.by` owner with his decision and lists them;
  any other Freesound file fails it. Replacing them is his call, not the stage's.
- **Never lower `gates.CLAP_FLOOR` to pass a sound**: write a better prompt (what it is, its size, material and
  place, and what is not in it). The floor is the tenth percentile of the environment's 55 MOSS picks.
- `sound_test.py` runs the make and the gates on the hub and the airlock (nothing rented) and breaks each gate once.
