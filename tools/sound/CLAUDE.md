# tools/sound

The sounds the game makes itself (#35): base hum, radio static, the warning tone, the geiger ticks,
the low oxygen beep. `bash tools/sound/run.sh` writes them to
`game/sound/made/`.

- **Plain Python, nothing installed**, like `tools/kit`: runs on a bare box's python3.
- **Deterministic.** Each sound draws from its own fixed seed, so a rerun writes the same bytes and
  changing one sound leaves the others alone.
- **Loops join without a click**: tones fit whole cycles, noise is filtered as a ring, beeps and
  ticks are silent or wrapped at the join. A loop carries a `smpl` chunk so Godot loops it itself.
- **Quiet by default.** Every sound is written well under full scale, the warning tone too (a pure tone sounds far louder than a recording at the same peak); the catalogue keeps the warning the loudest level.
- **Every file it writes is on `game/sound/licences/licences.json`** as made for this game, or the
  licence gate fails. A new sound here gets its entry there in the same change.
- **Nothing replaces a take the owner has not heard.** Render with `--out` to listen first.
