# tools/sound

The game's sound tools (#35). `made.py`: the sounds the game makes itself (base hum, radio static, the warning
tone, the geiger ticks, the low oxygen beep); `bash tools/sound/run.sh` writes them to `game/sound/made/`.
`picker/`: the owner's picking pages (`run.sh pick <page>`, `run.sh apply <dir> <picks.json>`). `loudness/`: the
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
- **CC0 only**, read off each take's own page, and credited on the licence list when it goes in. Previews are
  Freesound's high-quality ones; the API key, when made, is the Scaleway secret `freesound-api-key`, never a file.
- **A source is one class** (`picker/sources.py`: `name`, `search(need, count)`, `similar(candidate, count)`); a new
  one is added there and to the list in `picker.py`, and the owner picks from it like the rest.
- Pages build outside the repo (`~/.cache/farm-factory/sound-picker/pages/` by default) and are published as an
  Artifact with their `takes/` and the `db` capability; the picks are read back with ArtifactData and applied.
- After `made.py` or any file change under `game/sound/`, run `bash tools/sound/run.sh loudness`.
