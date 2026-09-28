# tools/sound

The sounds the game makes itself (#35): base hum, radio clicks and static, suit breathing and fans,
the warning tone, the geiger ticks, the low oxygen beep. `bash tools/sound/run.sh` writes them to
`game/sound/made/`.

- **Plain Python, nothing installed**, like `tools/kit`: runs on a bare box's python3.
- **Deterministic.** Each sound draws from its own fixed seed, so a rerun writes the same bytes and
  changing one sound leaves the others alone.
- **Loops join without a click**: tones fit whole cycles, noise is filtered as a ring, breaths and
  ticks are silent or wrapped at the join. A loop carries a `smpl` chunk so Godot loops it itself.
- **Quiet by default.** Only the warning tone is written near full scale; nothing else gets its level.
- **Every file it writes is on `game/sound/licences/licences.json`** as made for this game, or the
  licence gate fails. A new sound here gets its entry there in the same change.
- **Nothing replaces a take the owner has not heard.** Render with `--out` to listen first.
