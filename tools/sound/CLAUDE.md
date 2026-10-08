# tools/sound

The game's sound tools (#35). `made.py`: the sounds the game makes itself (base hum, radio static, the warning
tone, the geiger ticks, the low oxygen beep); `bash tools/sound/run.sh` writes them to `game/sound/made/`.
`picker/`: every sound the game needs, made by MOSS on a rented card (`tools/props/cloud/moss_sound.py game`),
then scored, levelled and put in (`run.sh auto game`); the page to listen and swap is optional. `loudness/`: the
loudness rule every take and every game file is held to (`run.sh loudness` measures them all again).

- **Plain Python, nothing installed**, like `tools/kit`: runs on a bare box's python3.
- **Deterministic.** Each sound draws from its own fixed seed, so a rerun writes the same bytes and
  changing one sound leaves the others alone.
- **Loops join without a click**: tones fit whole cycles, noise is filtered as a ring, beeps and
  ticks are silent or wrapped at the join. A loop carries a `smpl` chunk so Godot loops it itself.
- **Quiet by default.** Every sound is written well under full scale, the warning tone too (a pure tone sounds far louder than a recording at the same peak); the catalogue keeps the warning the loudest level.
- **Every file it writes is on `game/sound/licences/licences.json`** as made for this game, or the
  licence gate fails. A new sound here gets its entry there in the same change.
- **Nothing replaces a take the owner has not heard.** Render with `--out` to listen first.

The picker and the loudness rule:

- **Nothing loud reaches the owner or the game.** Every take goes through `loudness.normalise` (its category's
  LUFS target, true peak under -3 dBTP, short fades) or is dropped; the page is not written if any file it plays
  measures over the limits. Never hand the owner a raw fetched file.
- **Every sound the game names has a brief** in `data/sound/sounds.json` with its prompts (`run.sh needs` lists any
  without; the picker's check fails on one). Write a prompt from the thing's description, size, material and place,
  in the base's theme, and say what is not in it ("no other sounds", "no clicks") for a loop.
- **Chosen without the owner** (`picker/choose.py`): its CLAP match to its prompt less its faults. A take with no
  prompt score (a recording) ranks under any generated one.
- **Every credit names where it came from**: a generated take's model, prompt and seed; a recording's page, author
  and CC0, read off its own page. The Freesound API key, when made, is the Scaleway secret `freesound-api-key`.
- **A source is one class** (`picker/sources.py`: `name`, `search(need, count)`, `similar(candidate, count)`); a new
  one is added there and to `finders_for` in `picker.py`. MOSS and the recording before are the default.
- Pages build outside the repo (`~/.cache/farm-factory/sound-picker/pages/` by default) and are published as an
  Artifact with their `takes/` and the `db` capability; the owner's swaps are read back with ArtifactData and
  applied with `run.sh apply DIR swaps.json`.
- After `made.py` or any file change under `game/sound/`, run `bash tools/sound/run.sh loudness`.
