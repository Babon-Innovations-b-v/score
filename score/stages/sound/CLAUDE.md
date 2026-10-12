# score/stages/sound/

The sound stage (the paper's Methods, "The canonical scene": sound, and "Shape and surface apart": sound by MOSS;
experimental, PRD #6, until the owner has heard it): row `sound`, one per place in `data/sound/places.json`. It makes
the place's sound layer data, `sound.json` and its files under `files/`, which the place's assembly writes into its
OpenUSD stage (`tools/usd/sound.py`'s layout). `__init__.py`'s docstring has the make and the gates; `gates.py` the
gates; `takes.py` the paid part.

- **Every source has a sound.** A place's sources are its room tones, what the suit lets through, its `objects`
  (`data/sound/places.json`), its inventory rows' `sound`, its motions' `sounds` and the whole surface bank
  (`data/sound/surfaces.json`). A new source gets its brief (`pick` with `prompts`) in `data/sound/sounds.json`, its
  category setting its loudness, and the stage makes it; never a file by hand.
- **A sound picked already is taken as it is** (the world's release, its credit off `data/sound/licences.json`, its CLAP
  score `chosen.clap` measured when it was made); only one whose files are off its category's loudness is levelled
  here, its volume moved so it plays as loud as before. Only briefs no world file answers are made, MOSS on one rented
  card in the moss image (`takes.py`, through `tools/cloud/images/prove.py`), chosen by the picker's rule.
- **Takes are kept in `~/.cache/farm-factory/sound-picker/moss/stage/`** named by sound, the hash of prompt, length and
  weights, and seed, with their CLAP scores: the same brief is never paid for twice. Change a prompt to get new takes.
- **The owner's recordings stay** (2026-10-06: the breathing, the sliding doors and the steel footsteps were better
  than the generated takes). `no freesound` passes them by their `chosen.by` owner with his decision and lists them;
  any other Freesound file fails it. Replacing them is his call, not the stage's.
- **Never lower `gates.CLAP_FLOOR` to pass a sound**: write a better prompt (what it is, its size, material and
  place, and what is not in it). The floor is the tenth percentile of the world's 55 MOSS picks.
- `sound_test.py` runs the make and the gates on the hub and the airlock (nothing rented) and breaks each gate once.
