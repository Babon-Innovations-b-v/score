# score/dashboard/previews/

A picture for every step card whose output holds no image of its own, drawn from that output's own files on the
store's machine: the plan from above with its items labelled (`maps.plan_picture`), a settle's objects at rest
(`maps.settle_picture`), the painted takes three-quarter (`paint.py`, .ply pieces named by library surfaces), the
surfaces a finish list names as swatches (`swatches.py`, colours from `data/library/materials.json` and
`design/tokens/tokens.json`), a .wav sound's waveforms, a USD layer's prims or a JSON output's placed things over
the place's plan, else a tile per thing it names (`sheets.py`). `__init__.draw` picks the drawer from the files.

Rules:

- **Local only.** `state/local.py` imports this package inside its methods; the hosted process never does
  (`tests/hosted_light_test.py` fails on `score.dashboard.previews` or matplotlib in a hosted process). Previews
  reach the hosted cockpit as exported pictures, never as code.
- **Pick by file, never by stage name.** A new kind of output gets a drawer keyed on what its files hold.
- **Made once, kept.** `<home>/previews/<VERSION>/<output>.png`, one at a time, one thread. Raise `VERSION` when a
  drawer changes, so every kept picture is drawn again. Served and exported under `preview.png` with
  `preview_id(output)`, 64 hex, so `/files` and `/thumbs` serve it like any listed picture.
- **Never write the store**, never name a provider (`tests/no_provider_test.py`), never move a paid row: nothing
  here is in a stage's code key (`python -m score.stages.moved origin/main`).
