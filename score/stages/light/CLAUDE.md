# score/stages/light/

The light stage (experimental, PRD #6; paper-vs-world-1 items 9 and 17) as three rows of the stage table:
`light-layer@<place>` (free: `layers/light.usda` over the round-three seed from today's scene record, `layer.py`),
`light-passes@<place>` (paid: the seed with that layer rendered on its own scene record's views, every own lamp in a
Cycles light group of its own, `inside/light_passes.py`) and `light@<place>` (free: the sweep on the passes, `mix.py`;
the strengths written into the layer; the gates). A row of every place with a scene record (`applies`), ship places
too (through the table's wrappers); `needs.py` gives the gaps check what a place needs lit and its sky (#27). Run with `python -m score run world1 --place <place> --stage light
--detach`. `__init__.py`'s docstring has the rows and the gates; `lightkit` (kit.py, the square's proscenium) keeps
its own runner (`python -m score.stages.light run lightkit`).

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
  frames are not inputs): a floodlight's head, beam and veil with its lamps off and on, against K04; the Earth's
  smooth share against C4; an outdoor place's sky colour against its own concepts' sky; every view's black and blown
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
- **The light data** (`data/light/<place>.json`) holds the light stage's own additions, never the scene record's:
  lamps on a kit kind's lenses, the camera's glow the record left out, and kit kinds the seed laid where the kit no
  longer has them (`kit_moves`: the launch's pad floodlights moved to concept K01's far side, 2026-10-12, because
  seen from the balcony the old ones stood 70 to 170 degrees off their own beams and never glared).
- **Never edit what a running light node reads** (its layer code, the place's and its neighbours' records, kits and
  light data): the runner stores nothing for a node whose input changed while it ran (2026-10-12: six renders lost).
  The rows declare each place's own files, never a whole data folder.
- **A shown place keeps its pictures** (2026-10-18): its light layer is written beside the lit tree and taken in, never
  written into its seed copy (the writer moves assets/textures into assets/light, and ten places' neighbours drew
  magenta). The lit tree is refused when it names a missing picture, and the render rows gate on the looks'
  missing-texture magenta (`passes.judge_magenta`).
- `light_test.py` checks the measures, the sweep and the layer on pictures, passes and a stage made in the test.
