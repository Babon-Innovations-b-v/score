# score/stages/light/

The light stage (experimental, PRD #6; paper-vs-world-1 items 9 and 17) as three rows of the stage table:
`light-layer@<place>` (free: `layers/light.usda` over the round-three seed from today's scene record, `layer.py`),
`light-passes@<place>` (paid: the seed with that layer rendered on its own scene record's views, every own lamp in a
Cycles light group of its own, `inside/light_passes.py`) and `light@<place>` (free: the sweep on the passes, `mix.py`;
the strengths written into the layer; the gates). The paid `light-haze` row (the same render with the shafts off)
was retired on 2026-10-22: it applied nowhere, since a design lays no kit piece. A row of every designed place (the table's `designed("light")`, `stages/design_layers.py`), ship
places too, its record the scene-record row's (a place that row writes none for is refused by name,
`passes.place_of`); `needs.py` gives the gaps check what a place needs lit and its sky (#27), from its plan;
`sky.py` its sky from the environment concept's physics. Run with
`python -m score run world1 --place <place> --stage light --detach`. `__init__.py`'s docstring has the rows and the
gates.

- **The design decides, never a hand-kept list** (2026-10-21, the hand-written-inputs sweep). A row reads the place's
  scene record from the scene-record row's output only (`passes.record_of`), never `data/scene/<place>.json` (the old
  game-transcribed records, which only scene-record's `seed-matched` reads); the places rendered with it are the ones
  its accepted record shows (`passes.neighbours`: its doors' places and what its views see over the made ground),
  each lit by its own record read beside (`scene-record@<name>`) on its earth seed (`stages.SHOWN_SEEDED`);
  the floodlight heads are the glow parts of the kinds whose lamps light a shaft (`haze.shafted_kinds`: the glowing
  rows, by row kind, its plan aims, the library's aimed lamp with its shaft; a floodlight's shaft is its row's, never
  a hand-kept lamp of one place), the place's and its shown places', read from each one's design kit (earth-seed's
  kit.json, the rows' `kit` and `kit <place>`), never data/kit (retired, 2026-10-21). Never add a place name, a kind name or a picture's pixels to decide what a row does.

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json` that names the place, the prim or pattern, what it is, why it is not from the
  library, who allowed it and when. Every finish is a library surface (`data/library`, the ProcFunc recipes and
  palette tokens): never a picture's own texture, a model's baked-in colour, a default grey or anything else; a
  picture-made model keeps its geometry and gets its finish replaced. The library check
  (`score/stages/complete/library`) lists what does not trace; bible `architecture/components`.
- **Strengths are measured, never the game's numbers.** One render gives every lamp's light alone; light is linear in
  a lamp's strength, so the look at any strengths is mixed from the passes through the view's own tone curve (fitted on
  the render's look against its light). The sweep's scale brings the place's brightness to its concept's; a blown-out
  lamp is turned down; a floodlight with a shaft keeps the strength its shaft sweep set (2026-10-11).
- **The views come from the place's own scene record, never a copy** (#27, 2026-10-20: the demo's copies under
  `work/demo` were lost with the old disk and left eight ship places with no views): the light layer writes
  `views.json` from the record it reads (its accepted scene-record output where it has one), and the passes and the
  sweep read it there (`passes.record_views`, `views_of`). A place is lit and judged on its own views in its own frame.
- **One shot** (#21, #27): every view rendered once, at `passes.CHECK_SIZE` only (nothing ships from the passes; a
  film renders its frames at their final size once), on one card class (`passes.CARDS`, the L4 Blender was timed on),
  never a fallback to a larger card; a failed job is a gap, a new batch to buy. The sweeps (`mix.sweep`,
  `floodlight_sweep`) are free: they mix the one render, they never render again.
- **A rule is set before any picture it judges is made** (mix.py's docstring holds the brightness and lamp rules, the
  module's constants the old faults' rules); a rule changed later says why where it is set.
- **Every fault is measured on the looks mixed from the node's own passes**, never on an older render (the demo's
  frames are not inputs): a floodlight's head, beam and veil with its lamps off and on, against the rules set on
  K04; each face-drawn sky body present where a view frames it and lit from its sun (the rules set 2026-10-22,
  before any was rendered); an outdoor place's sky colour against its own concepts' sky; every view's black and blown
  shares against its concepts' (`exposure`, the owner's "no black or blown areas").
- **A mixed look is clean** (owner, 2026-10-20: the Library's Camp picture full of specks): only the render's
  combined light is denoised, never a lamp group, so a look's mix ratio is smoothed on the rendered look
  (`mix.smoothed`, a guided filter) before it scales the look, and the table's grain check
  (`score/checks/grain.py`, `stages.GRAIN_PICTURES`) fails a grainy look by name.
- **Lamps are measured where they shine** (2026-10-13): a lamp inside its fixture moves out of it when the fixture's
  solid parts stop 90% of its rays, or stands just outside its lens otherwise (`layer.lamps_through_fixtures`, each
  lamp's rule in lamps.json); under the open sky the suns are swept after the lamps when the lamps cannot reach the
  concept.
- **The layer holds live lights.** The owner's plan is baked per-lamp layers mixed live; the passes are that idea on
  the views only, nothing is baked into the surfaces yet. Say so wherever the layer is shown.
- **The assembly takes the layer just over the seed's base** (under the motion, effects and edit layers, so a light
  the motion layer keys keeps its keys): `layers/light.usda` and `assets/light/`, as `lit_tree` puts them. The
  layer's pictures live in `assets/light/`, never `assets/textures/`, where the seed's own pictures of the same names
  are.
- **Strengths are measured on the round-three seeds' layouts** (2026-10-12, tonight's cut): the passes render the
  seed with the layer, not the final assembly; once the assembly takes the layer the measurement moves onto it.
- **No per-place light file** (2026-10-21: `data/light/` is gone). A lamp is its glowing inventory row's (row kind,
  on its kit glow part; its numbers the library's lamp, a row the plan `aims` its aimed spot), the pad floodlights'
  shaft too; the camera's glow is written only from a record environment that holds one (the scene record, from
  the design alone, holds none: the old sky record was retired, 2026-10-21); the kit pieces stand where the earth
  seed lays them from the design, never re-laid here.
- **Never edit what a running light node reads** (its layer code, the place's and its neighbours' records, kits and
  light data): the runner stores nothing for a node whose input changed while it ran (2026-10-12: six renders lost).
  The rows declare each place's own files, never a whole data folder.
- **A shown place keeps its pictures** (2026-10-18): its light layer is written beside the lit tree and taken in, never
  written into its seed copy (the writer moves assets/textures into assets/light, and ten places' neighbours drew
  magenta). The lit tree is refused when it names a missing picture, and the render rows gate on the looks'
  missing-texture magenta (`passes.judge_magenta`).
- **A designed place is measured against its locked concept** (`{home}/design/concepts/<place>.png`, as
  rough-model reads it; `concept_pictures`, `light_files`). The K04 and C4 reference measures (fixed pixels of two
  environment-1 pictures, lost with the old disk) are gone (2026-10-21). A shown place the design has no plan for
  (the far city) is left out of the render (`passes.neighbours`); the neighbours row names it a gap.
- **The sky is the environment concept's physics** (the owner, 2026-10-21: no fixed sky; CONTEXT.md "physics"):
  `sky.py` writes what overhead.py says is overhead at the scene's site at its scene time (each light over the horizon a distant light, one under it none,
  a shining body's disc and every other body a ball at its true direction and size, each backdrop), from the scene's
  kept sky inputs (`{home}/design/sky/<scene>.json`, `score/review/scene_sky.py`, kept by `python -m
  score.review.plans keep`; a room takes its top scene's site), and turns the seed's and the record's old sky off. The
  light-layer gate `sky bodies` holds the layer's geometry to overhead.py; unknown while the scene has no site or
  scene time on the environment's plan. Every body's ball is drawn from its face as its `body-face-<body>` row made it (the layer reads and waits on each, so a place's line makes its sky's faces first, `sky.faces_of`; never by a library name or a picture of its own: the Earth's NASA picture was retired 2026-10-22), a shining body's disc `<body>_disc`, the library's glowing recipe
  in the black body's colour at its light's kelvin (`sky.disc_material`; it had no surface until 2026-10-25 and
  failed `stage_no_worse` in 21 places), or named missing, never grey.
- `light_test.py` checks the measures, the sweep and the layer on pictures, passes and a stage made in the test;
  `sky_test.py` the sky against skies worked out by hand.
