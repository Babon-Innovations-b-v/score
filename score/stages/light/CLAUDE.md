# score/stages/light/

The light stage (experimental, PRD #6; paper-vs-world-1 items 9 and 17) as three rows of the stage table:
`light-layer@<place>` (free: `layers/light.usda` over the place as the assembly lays it, `layer.py`),
`light-passes@<place>` (paid: that stage with the layer rendered on its own scene record's views, every own lamp in a
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
- **Views stand in free air on what is made** (2026-11-04). The scene record places its views on the plan's
  footprints; the made models stand at their built sizes, so its views looked into flat's wardrobe, street's police
  car, square's and base's blobs (2026-11-02). The layer's views.json is the record's views cleared on the stage it
  lights (`cleared_views`, `camera_paths.cleared_view`: turned, else moved out, else left out with why in
  `left_out`), and its `views clear` gate measures each again (`camera_paths.view_faults`) before light-passes is
  bought. Never loosen LOOK_CLEAR or NEAR_MOST to pass a place: move the view.
- **Strengths are measured, never the game's numbers.** One render gives every lamp's light alone; light is linear in
  a lamp's strength, so the look at any strengths is mixed from the passes through the view's own tone curve (fitted on
  the render's look against its light). The sweep's scale brings the place's brightness to its concept's; a blown-out
  lamp is turned down; a floodlight with a shaft keeps the strength its shaft sweep set (2026-10-11). One order (mix.py's
  docstring): the lamps, the suns with the fill where the lamps cannot, the fill alone raised from the sweep's floor
  only as far as the views need (every view within x2.5, none more black or blown than its concept; 2026-10-30:
  hangar's floor in the ship's shadow, base's shaded walls), each blown lamp turned down, the floodlights last. A sun
  blowing a view past its concept is stepped down before the fill's sweep, only as far as that needs with the place
  and every view kept within (`mix.sun_down`; 2026-10-31: camp's sunlit shell, 2.2-4.3% blown in seven views).
  A sun is the physics': never swept past `mix.SUN_MOST` (its physical strength), and a lamp-lit place (inside, its
  concept's light showing no daylight: `light.lamp_lit`) has its suns at the sweep's floor while its lamps are swept;
  the gate `light source` fails a sun past SUN_MOST and a lamp-lit place its own lamps give under
  `mix.LAMP_SHARE_LEAST` of the light (2026-11-04, the light audit: hangar's sun at x19 in a night hangar, its
  lamps 8%; airlock's, garage's, tube's and hub's lamps at the 1/32 floor). A lamp-lit place's lamps are swept up to `mix.LAMP_SCALES`' top (x1024), every
  other's to `mix.SCALES`' (x32); a share is read on each group's whole-view sum, never on the pixels, where the
  denoised combined less the undenoised groups is noise (2026-11-10: hangar's lamps stopped at x32 at 14%, tube's
  noise read as half its light). The gate `colour` holds the lit
  surfaces' cast (`measure.surface_cast`: the mid-tones' balance, brightness taken out) within `CAST_MOST` levels of
  the concept's (2026-11-04: the lab lit green by its screens, quarters' warm room cool), a cutaway concept's flat
  backdrop left out (`measure.backdrop`; 2026-11-10: quarters' grey backdrop read its warm room neutral). A lamp's
  light carries its colour into the mixed look (`mix.tint`, 2026-11-10: the look kept the render's colour under any
  scales, so greenhouse's lamps x25 and sun x1/32 read its sunlit render's colour): a white lamp the concept paints in
  a saturated glow (within `mix.WHITE_DUV` of the Planckian locus) throws its black body's light at the colour
  temperature nearest its paint (`mix.lamp_light`), a faint emitter or a coloured part (a grow light, a screen) its
  own hue, written into the layer by the light row (`light.colours_written`, never layer.py, which the paid passes
  row's key holds; the strength kept); after the suns and the fill, the lamps of each colour, each sun and the fill
  are balanced against each other to the concept's cast at the brightness the sweep gave (`light.colour_balance`,
  `mix.balance`; every light within SCALES, the suns only turned down; a faint emitter, held at x1 by the sweep
  (`mix.capped`), a class of its own, never past a whole lamp of its mount, `light.emitter_most`; its estimate
  brought back to the swept brightness only as far as those caps let the looks, `balanced_cast`'s `room`, 2026-11-10:
  greenhouse's estimate lit it with its screens past their cap and never tried its grow light up), kept only where
  its looks read nearer the concept and no rule the sweep kept breaks (`light.look_gap`), never a lamp recoloured to
  the concept. An inside place whose
  views see sky has its sky judged too, against its sky rows' boxes on its concept, on the sky's own flat colour there (`row_skies`; camp's domes).
  A view's sky is where its render met no surface less what it sees through the place's doorways (`open_sky`, on the
  views its passes rendered): a door leads to a place, never the sky (2026-11-10: hub's and hangar's door openings
  read as their sky).
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
  combined light is denoised, never a lamp group, so the groups' change is smoothed on the rendered look
  (`mix.smoothed`, a guided filter) before it scales the light, and the table's grain check
  (`score/checks/grain.py`, `stages.GRAIN_PICTURES`) fails a grainy look by name. The light is mixed at full
  precision, never the 8-bit look scaled (2026-10-30: engineroom's look swept 32 times up made every level step of
  Blender's dither a speck): the render's float colour times its mixed light, through Blender's own view transform
  (light-passes' `view-transform.npz`, a table Blender made on its own look's save, `mix.displayed`), 8 bits once.
- **Lamps are measured where they shine** (2026-10-13): a lamp inside its fixture moves out of it when the fixture's
  solid parts stop 90% of its rays (with no lens, toward an inside place's shell middle, never the stage's bound:
  2026-10-30, walkway's ducts over its ceiling sent its ceiling lamps up into it), or stands just outside its lens
  otherwise (`layer.lamps_through_fixtures`, each lamp's rule in lamps.json); a lamp inside a larger mesh, a model
  baked whole with its head, is judged on that mesh's part within HEAD_REACH of it and moved out of that part when it
  stops 90% (`layer.out_of_model_head`; 2026-10-31: round 34's bake fused square's and street's lamp posts into one
  4 m mesh, the head closed round the lamp, 20 lamps dark); the suns, an inside place's too (its sun shines in through its openings), each in a
  light group, are swept after the lamps when the lamps cannot reach the concept or their sweep stops at an end of its
  range (2026-10-30). Lamps at one spot are one lamp; one outside an inside place's shell (past its record's floor
  box or over its ceiling) stands in no view and is not judged unlit.
- **The layer holds live lights.** The owner's plan is baked per-lamp layers mixed live; the passes are that idea on
  the views only, nothing is baked into the surfaces yet. Say so wherever the layer is shown.
- **The assembly takes the layer just over the seed's base** (under the motion, effects and edit layers, so a light
  the motion layer keys keeps its keys): `layers/light.usda` and `assets/light/`, as `lit_tree` puts them. The
  layer's pictures live in `assets/light/`, never `assets/textures/`, where the seed's own pictures of the same names
  are.
- **Strengths are measured on what ships** (2026-10-29; on the round-three seeds' layouts from 2026-10-12 until then):
  the rows light the place as the assembly lays it before its layers (`passes.source`): the seed with its scene
  record, the surface line's bake over its models and its waiting entries, its made ground, each laid by the
  assembly's own code (`assembly/grounded.take_bakes`, `record.take_ground`), never a copy. The rows read the bake,
  the paint and the ground as the assembly does (`passes.LAID`) and wait on them. Before, every design object waited
  on its bake: base drew nothing and rendered black, airlock was a bare shell its lamps needed x17 to light. A stage
  drawing nothing outside its sky fails the layer's `drawn` gate before the paid render. The made ground is laid finished
  (2026-11-04, the eyes review of env1: the rows laid it with its finish named missing and the campgrounds', base's,
  square's and street's ground rendered a white sheet): bound to the surface its scene library gives its row by the
  assembly's own code (`assembly/ground_finish.py`), the rows reading the place's surface library after and each
  scene finishing its ground beside (`passes.read_beside`: base's for the airlock; a scene read only for that is
  never rendered as shown, `shown_in`). The layer's `surfaced` gate (`bare.py`) fails, before the paid render, a
  drawn ground, water or shell mesh with no library surface and an outdoor place whose sky holds nothing. A bake another place makes
  for this one (its surface data's `elsewhere`) is not read beside yet: no place claims one today.
- **No per-place light file** (2026-10-21: `data/light/` is gone). A lamp is its glowing inventory row's (row kind,
  or its concept showing it glow, as the reading's concept light says: `{home}/design/light/<place>.json`,
  `reading.concept_light`, in the colour and at the brightness the concept shows; on its kit glow part; its numbers
  the library's lamp, a row the plan `aims` its aimed spot), the pad floodlights' shaft too. Where the concept shows
  light falling from no source in view (its `unseen`), beside a sun over the horizon too (2026-10-30: base's sun, its
  only light, left its shaded walls 53% black), the layer adds the library's fill (`layer.write_fill`, lamps.json
  `fill`) in the concept's colour, inside over the middle of its record's floor box under its ceiling (never the stage's bound, which holds the
  sky), swept after the lamps as a sun is (owner, 2026-10-25: "the frame work should solve this, look at the
  concept"); `lit` names a concept showing daylight with no sun up at the scene time (the environment plan's);
  the camera's glow is written only from a record environment that holds one (the scene record, from
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
  a shining body's beam coloured by its share through the site's dusty air, the record's `sky_dome` dust,
  delta-Eddington, `sky.through_dust`: 2026-11-10, campgrounds' sun 9.8 degrees up shone at its top-of-air white;
  a shining body's disc and every other body a ball at its true direction and size, each backdrop), from the scene's
  kept sky inputs (`{home}/design/sky/<scene>.json`, `score/review/scene_sky.py`, kept by `python -m
  score.review.plans keep`; a room takes its top scene's site), and turns the seed's and the record's old sky off. The
  light-layer gate `sky bodies` holds the layer's geometry to overhead.py; unknown while the scene has no site or
  scene time on the environment's plan. Every body's ball is drawn from its face as its `body-face-<body>` row made it (the layer reads and waits on each, so a place's line makes its sky's faces first, `sky.faces_of`; never by a library name or a picture of its own: the Earth's NASA picture was retired 2026-10-22), a shining body's disc `<body>_disc`, the library's glowing recipe
  in the black body's colour at its light's kelvin (`sky.disc_material`; it had no surface until 2026-10-25 and
  failed `stage_no_worse` in 21 places), or named missing, never grey.
- **The night is physics too** (2026-11-10: square, street, stairwell and flat rendered under a black sky with only
  their warm lamps). Past its star's astronomical twilight on a body whose air `data/physics/night.json` has,
  `night.py` adds the Moon's light (its star's lux, albedo, distance and phase law through the air: a distant light
  `night_<body>`, held at x1 by the sweep as the glow beside it is, never floored as a sun: `strengths`'
  `night_lights`) and the air's glow as the scene's environment (the moonlit air, Krisciunas and
  Schaefer 1991; a measured city skyglow where the site stands in one; the setting's backdrops), colours from spectra
  through the CIE observer, as the eye adapted to the lit place takes them (Jensen et al. 2001's rod blue shift
  by its adapting luminance, CIE 191:2010, never the sky's own: 2026-11-10, the square's sky read too blue), on the views' scale by the light an eye at the lit place stands in (EN 13201 / EN 12464). Every number
  is a cited measurement or standard: never fit one on a concept. `make_layer` writes it (night.write_layer). The
  light row sees a night place with that eye's colour too (`night_adapted`, 2026-11-10: flat rendered [162, 128, 93]
  as a daylight camera sees a tungsten room, its concept about neutral): CIECAM02's adaptation (CAT02 von Kries, its
  degree D from the lux the eye stands in) to the light its views take from its groups as swept, before any balance,
  applied to every group's shipped colour, to the light no group holds (`mix.REST`) and to the night air's dome and
  background in the layer (`environment_adapted`); an eye outside with the night sky as its surround (CIE 159's F by the
  surround ratio, `mix.surround_factor`), one inside with its room's. The sky keeps its rendered light in the mixed look
  (`look_at`), never its neighbours' gain. An inside place's cutaway concept sky is judged as its room's eye sees it
  (`seen_inside`, the layer's night `scale` over `outside_scale`: the stairwell's windows, 2026-11-10). A finish darker
  than the 18% grey card is judged black on its light read on the card (`on_card`, the passes' `surface`: the
  street's black police car, 2026-11-10).
- `test_light_measured_against_design.py` checks the sky against skies worked out by hand, and the measures, the
  sweep and the layer on pictures, passes and a stage made in the test.
