# score/dashboard/previews/

A picture for every step card whose output holds no image of its own making (a texture or sound packaged in an
`assets/` folder is not one: `state/files.packaged`), drawn from that output's own files on the store's machine: the
plan from above with its items labelled (`maps.plan_picture`), a settle's objects at rest (`maps.settle_picture`),
the painted takes three-quarter (`paint.py`, .ply pieces named by library surfaces), a surface check's library colour
over its baked colour (`checks.py`), the surfaces a finish list names as swatches (`swatches.py`, colours from
`data/library/materials.json` and `design/tokens/tokens.json`), a .wav sound's waveforms, what a USD layer places
and moves (each animated translate as a route) or a JSON output's placed things over the place's plan, the models an
output names by hash (`meshes.py`, found one level under the work folder and checked against the hash), the
pictures its records point at, cut to their boxes (`crops.py`), else a tile per thing it names (`sheets.py`).
`__init__.draw` picks the drawer from the files. Plans and whole OpenUSD stages (a top-level .usda that sublayers
others) are drawn large with their labels spaced so none covers another (`labels.py`). `films.py` cuts pictures from
a place's accepted film with ffmpeg, no render: the board tile's middle still, and an accepted gap's things ringed in the
frame that shows them best (their points carried through that frame's camera from the film's views.json);
`state/accepted_gaps.py` falls back to them ringed on the plan, then to the gap's step picture.

Rules:

- **Local only.** `state/local.py` imports this package inside its methods; the hosted process never does
  (`tests/hosted_light_test.py` fails on `score.dashboard.previews` or matplotlib in a hosted process). Previews
  reach the hosted cockpit as exported pictures, never as code.
- **Pick by file, never by stage name.** A new kind of output gets a drawer keyed on what its files hold.
- **Made once, kept.** `<home>/previews/<VERSION>/<output>.png`, one at a time, one thread. `VERSION` carries the
  drawers' code version (`state/versions.py`), so a change to any drawer draws every kept picture again. Served and exported under `preview.png` with
  `preview_id(output)`, 64 hex, so `/files` and `/thumbs` serve it like any listed picture.
- **Never write the store**, never name a provider (`tests/test_no_provider_is_named_here.py`), never move a paid row: nothing
  here is in a stage's code key (`python -m score.stages.moved origin/main`).
