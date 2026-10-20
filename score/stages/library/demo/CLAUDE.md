# score/stages/library/demo/

One module an algorithm entry of the library (`<module>.py`, its `ALGORITHM` the entry's id): `made(inputs)` returns
what the cockpit's item page plays for it (`score/dashboard/pages/static/pages/demo.js`, owner 2026-10-20: "an item
page is about experiencing the item in isolation"; a still from a film is not the algorithm). The runner
(`score/stages/library/demos.py`, each sync pass) writes every module's demo into
`$PROPS_HOME/cache/library/demos.json`, which the cockpit reads and the state export carries.

- **Real data only.** A demo is the algorithm's own work on one real example: its real input (the repository's
  `data/`, a library entry's files through `inputs.library(address, file)`, fetched once into the library cache, one
  object read each) and its real output (the entry's recorded output, or the algorithm's own function run again here
  at another setting, free and local: numpy, never Blender, a GPU or a paid call). Nothing drawn by hand, no made-up
  numbers. When it cannot be made, raise `demos.NoExample("why")`: the page then shows a plain diagram of what the
  algorithm reads and makes, and says why.
- **Small.** A demo is at most `demos.MAX_BYTES` of JSON; round coordinates to centimetres, thin long lists.
- **The shape** (checked by `demos.checked`):

```
{"example": "the greenhouse",            # where the example comes from, in plain words
 "view": "plan" | "side" | "relief",     # plan: x east, y north (y = -USD z), metres; side: x across, y up
 "bounds": [x0, y0, x1, y1],             # plan and side: what the canvas frames, metres
 "axes": {"x": "hour", "y": "height above the horizon, degrees"},   # optional: a chart's axis names
 "steps": [{"label": "The beds", "shapes": [shape, ...]}, ...],      # played one after another, each kept
 "slider": {"label": "spacing", "unit": "x measured", "values": [0.6, 1.0, 1.6], "at": 1,
            "shapes": [[shape, ...], ...]},   # optional: one shape list a value, drawn in place of the last step's
 "relief": {"size": [wide, deep], "heights": [[metres, ...], ...],   # view relief only: rows north to south
            "steps": [{"label": "...", "heights": [[...]]}, ...]},   # optional: each step's heights
 "numbers": [{"label": "plants", "value": 93, "unit": "", "tip": "hover text"}]}   # optional, at most four
```

A shape is `{"kind", "points": [[x, y], ...], "tone", "label", "id", "r"}`:
`area` (a filled outline), `line`, `dots` (each point a dot `r` metres wide), `path` (a line a marker travels
along; `"look": [[dx, dy], ...]` one direction a point turns it into a camera with its view cone), `text` (`label`
at its one point), `raster` (`points` its two corners, the first row 0's first cell's, `grid` rows of values 0 to 1, or of
[r, g, b] 0 to 1). A dot's `r` is in the view's units (degrees on a sky chart).
`tone` is one of `ground`, `base`, `made`, `accent`, `warn`, `ghost`, or `c1`..`c8` (one colour a category; say which
category each is in its `label`). A shape whose `id` is in an earlier step moves from there to here when the step
plays (settle dropping into rest, a mover's path).
