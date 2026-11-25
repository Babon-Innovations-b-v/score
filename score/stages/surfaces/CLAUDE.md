# score/stages/surfaces/

The surface stage (R4, the paper's core contribution: shape and surface apart, every part one surface of the shared
library), step 1 of PRD #6, as rows of environment 1's stage table (`__init__.py`, `ROWS`). Bible: `architecture/components`
and `architecture/experimental`; method: the paper's Methods, "Shape and surface apart".

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json` that names the place, the prim or pattern, what it is, why it is not from the
  library, who allowed it and when. Every finish is a library surface (`data/library`, the ProcFunc recipes and
  palette tokens): never a picture's own texture, a model's baked-in colour, a default grey or anything else; a
  picture-made model keeps its geometry and gets its finish replaced. The library check
  (`score/stages/complete/library`) lists what does not trace; bible `architecture/components`.
- **One line per place, run by the runner**: `python -m score run world1 --place <place> --detach` (score's overlay:
  never walk the rows by hand). Every row is place grain (`surfaces-inputs@greenhouse` ... `surfaces-check@greenhouse`);
  no place waits on another.
- **The method sits behind one interface**: its rows end in the contract `surfaces-parts` v1 (`parts.json`: per model
  its parts, each with the library surface the method named (`judge`), its words, a proposed new surface or null;
  `finish` null when nothing is measured; `<take>/parts.npy` one part per welded face; `<take>/colours.npy` each
  face's seen colour, NaN when none is measured; `<take>/texels.npz`, where the model has a picture, one part per
  texel of it: `route_texels.py`, #159, the look's borders on the texture's colour edges, the faces' parts
  unchanged; the paint writes it into its labelled take as each surface's texel mask on the raw take's own UVs,
  `labelled/<take>/texels/`, which make_chunky mixes each recipe by, #182). Another method replaces the method's rows and writes it; the
  framework's rows (`place_line.py`: paint, bake, check) do not change.
- **Decals and scuffs** (#164): a printed mark is a library decal (score_lib surface, family `decal`), never a
  picture of the model. `finish-route-list` lists the marks with their decal (`finish_ask.marks_of`, offered by
  `decal_library.catalogue`); `surfaces-parts` places each on its part through the close-up's camera
  (`route_parts.decal_placements`, parts.json `decals` and `decal_gaps`; a stand-in close-up places none, each a gap)
  and writes each part's own `wear`; `surfaces-bake` ships each decal's picture and prints it in its part's finish
  (`route_bake.decals_on`, make_chunky `decals_on`, `recipes.decal_layer`); a decal the library does not hold stops
  the bake. **Text and numbers** (#171; owner, 2026-11-23: "TRELLIS isnt able to do text and numbers tho") are never a
  route's texture: the list reads each text mark's words and look, and each plain printed line, as a mark (asked always,
  decals in the library or not); `surfaces-parts` draws it as a text decal in the library's face of that look
  (`text_decals.py`: data/fonts, SIL OFL; score_lib holds no font yet) at its cast size, written beside parts.npy as its
  placement's `picture`, and the faces of the list's print finish under the mark (seen in its grown box, and those
  the close-up hides at most as deep behind the face shown as the box is grown: TRELLIS.2 raises its garbled letters
  over the plate, `hidden_under`) take the finish and part it is printed on (`route_parts.covered_prints`; a library
  picture decal over a print covers it too, `covering`). The texels follow (#185): a print texel on a face under the
  mark takes that part and every texel is numbered as the faces are (`covered_texels`), else the look and the bake
  draw TRELLIS.2's garbled print from its texels (tc4r's sign: a "C" for "03"). **Small text** (#196, #159 round 8: the
  cockpit cases' ON, OFF and ARM, 2.5 mm tall, read as glyphs): a line under 1 cm is drawn `text_decals.TEXT_PX` tall
  (`density`, kept as the placement's `px_per_m`, which bake.sharp_slots bakes its part at); the print's whole island
  under a mark is covered (`print_islands`: its letters lie off their ink by the fitted camera's error), with the
  texels its reach carried (`route_texels.carried_from`); and the print reaches the raised letters its ink was seen on
  (ink_extent's `depth`, recipes.decal_depth). **Timber's grain** (#159, the coffee station's walnut drawn a flat
  stipple, its boards merged): the list reads each timber finish's grain way (up, across, deep by the named views) and
  its boards' width off the close-up (route_list.timber_settings, told the model's size), a timber it read none of runs
  along its part's long axis (route_parts.grained), and the settings carry both to the recipe (route_settings
  `grain`, `board`; recipes.grained_wood). **Lit parts** (finish_parts.LIT_FAMILIES, glowing and screen) are the
  close-up's: a texture cannot show light, so a face it labels lit takes that finish (`route_split.close_up_only`),
  kept through the smoothing as parts of its own (`lit_laid`), its texels following the close-up's own edges
  (route_views `close_up_texels`, each texel's close-up region at its point; route_texels.texel_parts); a lit face
  seen in a drawn mark's box is the mark's ink (covered_prints). A close-up with no camera of its own (TRELLIS.2's) gets one fitted from
  the model's outline (`close_up_fit.py`; a camera file's `look` is read before Pixal3D's +Z rule). Scuffs are the
  recipe's `scuffs` setting (0 by default), never a picture. **Vent patterns** (#210, #159 round 12: TRELLIS.2 draws a
  locker's vent holes, a battery's slots and a humidifier's ribs as blobby bumps with black smears) are library work
  too: the list reads each patch of openings as a mark of shape `pattern` (its opening, rows, columns, stagger,
  outline, opening share, the way it runs, the token inside it; asked when score_lib holds surfaces of family
  `pattern`, `decal_library.patterns`, whose tags give the opening's shape, length share, relief and roughness), its
  library pattern's address its `decal`; `surfaces-parts` places it as a decal sized by its openings' ink on its
  part's plate (`pattern_facing`, `near_plate`: not what its holes show behind; `plate_probed`: a probe whose ray
  went through one of TRELLIS.2's holes is laid on the plate, #159 r15) and draws it tiled inside its outline
  (`pattern_decals.py`); the bake prints its openings in the token's ink and sinks them by its `relief`
  (recipes.decal_relief); the route's own openings finish under it is covered as a print under a text mark is.
  **The made shape under a mark is flat and closed** (#214, #159 round 13: the pattern drawn over TRELLIS.2's 4 mm
  bumps and the bars it cut through the locker's doors): the parts row holds every placement to its part's plate
  (`decal_plates.py`, route_parts.on_plates: a grid of rays at its box gives the plate, a fitted plane, and its seams
  and edges); a pattern crossing a seam is moved clear of it or is a gap, and takes the take's own up; its `closed`
  region (box, pressed height, plate point) is pressed flat and covered by one card in the plate's finish where the
  look and the place's bake draw it (tools/props/library/inside/bake.pressed_under, cards_over); a mark whose plate is not flat
  is left `open`. A hole TRELLIS.2 cut through a closed mark's plate outside every closed region (r13's black dot above
  each locker vent) is closed too, a box of its own in the nearest mark's `also` (`holes_closed`, a plate cast once);
  so is one of any size right through a light plate the close-up shows plain there (`shown`, route_parts.lightness_seen:
  r15f's band 1 locker's 14 cm bars through its doors), never one the close-up cannot tell from a dark plate.
  **Printed panels** (#159 round 15, r14's gas stove: its red and white control panel drawn as torn white and red
  pieces with a grey box): a printed area of several inks on one flat face is one mark of shape `panel`
  (finish_ask.PANEL), its words still text marks. `surfaces-parts` covers every face under it that faces its plate
  (route_parts.panel_covered: its box first drawn in to its print, `print_box`; a hardware piece's and a lit finish
  kept), frames it on its plate (panel_decals.framed) and draws its picture from the close-up's own pixels rectified
  onto that plate (panel_decals.drawn: what stands in front filled, a placed text mark's ink taken out, clear where it
  shows the plate's own finish, its colours mapped to the list's tokens by `unlit`), laid under every other mark with
  a print `reach` of 8 mm (recipes.decal_depth). A word whose library face lacks a glyph is a gap (text_decals.missing:
  the stove's 爐), so the panel's own pixels show it. A hardware cut inside a panel tears none of its finishes
  (hardware_pieces.panel_finishes) and is closed in the panel's part (route_parts.in_panel).
  **Small hardware** (#212: TRELLIS.2 turns a locker's small hex cam locks into big round blobs, a stove's knobs into
  lumps) is laid as library pieces: score_lib's `model` entries of family `hardware` (`score-lib hardware cut`, a
  lock, knob, handle, hinge or latch cut from an adopted NVIDIA model, its credit carried; `decal_library.hardware`)
  are offered to the list, which reads each piece as a mark of shape `hardware` (its kind, the library piece most like
  it, the finish it is mounted on and the finish it is); `surfaces-parts` lays it (`hardware_pieces.py`, parts.json's
  `hardware` and `hardware_gaps`): its box measured again on the close-up (`piece_box`), its face read round it, its
  library piece stood on that face and fitted to the box (`fitted`: its size and spot the close-up's, its depth seen
  aslant included), the model's own blob beside it found and cut (`blob_cut`, stopping short of the face's edge; a blob joined low to a
  door's raised edge parted from it standing higher, `parted`, r15f) and
  closed on its plate as a mark's is (the cut's `closed`, `decal_plates.closed_round`: pressed straight onto the
  plate, one card over it short of a seam, the blob's core pressed past it; closed to a point in r13 it drew white
  cracks and starbursts), the blob's faces covered as a print under a mark is, onto the part it is laid on
  (`cut_marks`). A piece is laid only where its cut leaves the print round it whole (`torn`, #159 round 13: r13's
  stove knobs, library dials too small for their blobs, tore the panel's print): a face the cut covers outside the
  piece's box in another finish than the face's, the piece's or the blob's makes the mark a gap, TRELLIS.2's blob
  kept; a vent pattern's openings' finish is no print (`pattern_finishes`, #159 r15). The bench's look draws it (tools/props/bench/run); a
  place's bake does not yet, nor do the physics and parts steps add the piece (a gap on #212).
  parts.json stays contract
  v1: its new fields are additive, so no accepted parts or paid bake is invalidated.
- **The finish-map method is gone** (2026-10-20, #26): the crops are the places' own takes and the people's line
  runs the route's rows (`../people/line.py`), so its turntable, maps, names and SegviGen rows and modules were
  deleted. `finish_parts.py` keeps the route's shared steps on a take's faces and the finish check; `finish_ask.py`
  the list ask and what the route shares of it.
- **The line is the finish route** (owner, 2026-10-20, #18; library first): every surface that faces the air is a
  library material carrying the look (palette colour, wear, shine, seed), so there is no paid paint step and no
  finish-map picture. Rows, in `ROWS` (`__init__.py`), on every painting place's line: `finish-route-views` (free,
  `route_views.py`), `finish-route-list` (paid, `route_list.py`; a part's colour read off the close-up, each region's colour there
  given beside the texture's and each token's L* and chroma beside its words, #198), `finish-route-split` (free, `route_split.py`),
  `surfaces-parts` (free, `route_parts.py`: the method's interface), `surfaces-bake` (paid, `route_bake.py`: the
  paint and the bake in one job), `surfaces-paint` (free, `route_paint.py`: the bake's painted takes, the paint's
  gates; a take a gate fails is a batch gap, as a model the check fails is: `route_paint.item_gaps`), `finish-route-recheck` (paid, `route_recheck.py`; `surfaces-check` reads it, so a failed
  recheck stops the line before the check), `surfaces-check`. Each route row selects (`score run --object <take>`).
  A take's model is its raw take (`route_data.py`); one with none here, or whose faces the paint loads differently, is
  named by the views gate before anything is asked. Its close-up is its own, else a **stand-in close-up** (the model's
  own texture from the front, `route_data.STAND_IN`), named so in every output, question and verdict that reads it.
  First the **scene palette** (CONTEXT.md; owner, 2026-10-21: every scene from its design alone):
  `finish-route-palette` (paid, `scene_palette.py`, one Gemini 3.1 Pro ask a scene in the Batch API) reads the
  scene's palette tokens (each a name and a `#rrggbb` colour it coins from the concept, never an old game token),
  wear level, dirt and dirt token off its locked concept and every take's close-up (`palette_files`, every take of
  the place whatever the object filter keeps, the row waiting on the Pixal3D row: asked over the concepts alone at
  768 px, the people's palette had no brown and astronaut-made's brown trousers, close-up L* 39, took moon-dust,
  L* 59, 2026-10-23; with no close-up the ask reads as before) (`{home}/design/concepts/<place>.png`; a line no scene owns,
  the people's, over every locked concept, asked for what its own objects wear and not the scenes', its people
  included; its dirt token the dust's or grime's own colour, added to the palette when no token is it: asked for
  the scenes with their people left out, the people's palette had no dark grey and its dirt was the hull's white,
  so astronaut-made's boots took glass-grey and baked L* 65.5 against their close-up's 33, 2026-10-23); no rule could
  (the concept's pixels named shadows and the people's skin and missed the accents, measured 2026-10-21). Then the
  **material step**, `surface-library` (paid,
  `scene_library.py`, one Gemini 3.1 Pro ask a scene in the Batch API; owner, 2026-10-21: every old material
  retired, the library starts empty): the scene's surfaces made fresh from its concept, palette, its takes' kinds and the shell its locked plan lays (`shell_kinds`: an enclosed place's floor, walls and roof are the plan's, no take's)
  by today's method (each a `recipes.py` recipe with token, roughness, metal, colour settings, seed and sound
  surface; a patterned recipe, a quilt, tiles, a grid or boards, only where the picture shows that pattern: asked
  with no such word, the people's library made its one fabric `quilted` twice and the astronaut's plain overalls took
  a light grid, 2026-10-23), written as `materials.json` in the loader's form, gated on every kind covered and everything the method's
  and the palette's. Every row after it (list, parts, bake, recheck, check) reads both through `palette_library.py`
  (`read` adds the scene library's path): that library filtered by the palette, the kind's own list (`kinds`) on
  top, the scene's wear and dirt in the list's question, the bake's job and the check. With no scene library a reader
  gets `library.LibraryEmpty` ("surface library empty: run surface-library first"), a missing input named, never a
  KeyError. No route row reads `data/definitions/place.json` (`materials`, `palette`, `wear`): the old route's and the
  kit routes' readers still do, and with the repository's library empty they name the missing input.
  Views (free, this PC's processor, no Blender): trimesh and Embree ray cast, orthographic, 384 px
  (`route_cast.py`), the six `BASE` sides (front is the close-up's, back, right, left, top, bottom), then the
  coverage check before the render (`route_views.covering_views`): from `CANDIDATES` the angle that sees the most area
  no chosen view sees, again, until every face is seen, none sees more or `MOST_VIEWS`; a face no angle can see is
  counted (`unseen_faces`) and the split gives it the finish of the voted face nearest it in space, mostly a shell's
  outer side a wall behind it (`route_split.behind`; walked along the surface, TRELLIS.2's inner walls took a rim's
  finish, #173), a hidden part joining its finish's nearest voted one (`hidden_joined`). Each view's colour regions:
  the model's own texture under each pixel in groups of distinct colour (at most eight, the same in every view); the
  texture is measured, never painted. The take's own close-up, where its camera's cast fits it
  (`route_cast.CLOSE_UP_FIT`), is laid on the model through that camera, one more view of the regions
  (`route_views.CLOSE_UP`): the raw texture often lacks the small parts the close-up shows, so k-means over the texture
  spent all eight groups on shading and rust and the list could label no region with the close-up's red label, decal,
  screen glow or valve paint (greenhouse desk's eight were seven greys from L* 21 to 62 and one paper yellow,
  2026-10-29). The groups are fitted finer (`FINE`), a group added for each colour far from all of them
  (`ACCENT_DE`, at least `ACCENT_LEAST` pixels), and the nearest merged down to eight, so shading steps merge first and
  a small saturated area keeps its region. In the split the laid close-up votes as the front does, and a finish only
  it labels (no texture view shows it) takes the faces it labels (`route_split.close_up_only`); never a whole part
  painted to pass a check. List (paid): one Gemini 3.1 Pro answer a take, all the place's takes in one batch through
  Google's Batch API at half price (`route_ask.py`, `tools/cloud/google_batch.py`), seeing the close-up, every
  view and every region view: the complete finish list, each finish matched FIRST to a library surface with settings
  (a library token, roughness, metal, its own seed: `take_seed`, the node's moved by the take's name, so each
  object's wear and dirt pattern is its own; the token the part's own colour under even light, told that every colour
  shown is lifted by light, a metal's its surface's own unless clearly tinted, a dark part's darker than it reads:
  read off the lit texture, tc2's toaster took #e0e0e0 steel and #383838 plastic for NVIDIA's albedo 0.33 and 0.013,
  #172), a new surface only when none fits with any settings; its wear the
  place's level, or its own library level where the views show a cause (walked paths, edges, round doors; owner,
  2026-10-20), level and cause both or neither, listed in `questions.json`; and a label for each region in each
  view. Split (free): by the labels alone (the paper, "Surfaces: the finish route": the views are split into colour
  regions only so the list can label them); no colour is judged there. The split's own colour check against the raw
  texture's regions (VIEW_DELTA_E, owner 2026-10-20, and its recolour, 2026-10-22) is gone (owner, 2026-10-25: "how is
  that possible with our finish lib and segmentation method read paper"): the texture carries the picture's baked
  light, and Batch 1 try 4 lost 134 takes to it at dE 32 to 41. Then the labels voted
  across views (`route_split.squared_votes`: each view's vote weighed by the cosine between the face's normal and the
  way to its eye, the front counting double); a seen face no label reaches is unassigned, a gap named in "one finish a
  face"; faces whose views disagree (no finish over half their votes) are a split decision, never a gap (owner,
  2026-10-28; the unmeasured 1% limit is gone, the share still recorded): each takes the finish its views weigh most,
  a tie the finish round it (the walk); the rest smoothed, strays given
  the finish round them (`without_strays`: an island under patchy.py's `STRAY_ISLAND` of a finish that has a larger
  one, not a whole piece; voted by larger islands only) and crumbs joined (`cleaned`, `merged_islands`), each island
  a part. A face no view sees is no gap (a raw take's inner shell: 71% of astronaut-made-s1), but its walked paint
  left jagged islands of the dark joints (stray 0.054, 2026-10-23), so a take still patchy (`patchiness`, patchy.py
  with each part its own region, as the paint measures it, and each island of a detail finish, decals, stickers, labels, notes, fittings or rubber by its family or words, a part of its own: `detail_finish`) is a gap in "one finish a face" before any bake. Parts (free): each finish checked against its colour in
  the close-up (`route_parts.close_up_colours`: the raw take cast through the close-up's own camera, Pixal3D's
  `transforms.json` beside it, a `camera <take>` input of the parts row alone; each inner pixel takes the finish of
  the face under it; a take with no own close-up or camera, or a cast under `CLOSE_UP_FIT` of the close-up's outline,
  is measured on its views' texture, named in `colour_from`), the paper's dE 32 (`finish_parts.checked_finishes`: the nearest surface of its family or the room's kit
  surface that fits, else off its colour with a proposal, which the paint's gate fails by name), then each part its
  finish's surface (`part_rows`), with the list's settings where its finish kept the listed surface
  (`route_settings.applied`); a light built in code (a light bar, strip or string from `props/thin_straight.py`, its mark a `code <take>` input of the parts row alone) is its light: every finish of a lit family (glass, screen, light: `finish_parts.SEEN_THROUGH_FAMILIES`), or every finish when none is, takes the scene library's glowing surface nearest its concept crop's colour, the rest (a light bar's metal end caps, given their own part since its build carries its crop, 2026-10-29) keeping their own (`route_parts.lit_finishes`, its files `route_parts.files` set by the table, `stages.code_marked`), else is off its colour by name; the takes the split made gaps are `left_out`. Bake (paid, `route_bake.py`; #18,
  2026-10-20: nothing heavy on this PC, whose prop environment is capped at 14 GB and crane-r1's paint peaked at 34.8
  GB): one job a take on the bake's warm card through `blender_cloud.py` (`inside/paint_bake.py`), carrying its own
  take's parts (`own_parts`, a copy beside the output) and specs alone and only the world files it reads, so its kept
  job (`tools/cloud/kept.py`) moves only with its own take (#36, 2026-10-30): the take painted
  by `place_line.paint_take` (as the rented paint), its models' make_chunky entries over the labelled take
  (`bake_job_step`), then make_chunky; priced at the bake's warm figure. Here first, free: the proposals into the
  registry, and the specs (a part with settings paints and bakes as `route_settings.settings_name`: its variant's
  spec in the list's token colour, roughness, metal, seed and own wear; specs.json in the output). The bake applies
  them: `recipes.arguments` takes a spec's own seed and wear over the job's (2026-10-20). Paint (free, after the bake): the
  bake's labelled takes and painted.json copied over, so every reader of the paint stays, with its gates (one
  surface a part, colour against the close-up, feet), which now judge after the bake: the parts' "off colour"
  measure names the colour faults before it. The colour gate also holds what the bake made (`baked_colour.py`, the
  table's `baked_colour_checked`): each baked model measured in the prop environment on the bake's own base colour
  map, each triangle named by the bake's ray, per surface the share of its area whose a*b* lies over `OFF_AB` from
  its close-up's (lightness free: the light moves L*), over `OFF_SHARE` a fault of its take, written per take into
  painted.json (`baked_colours`); a token judged alone passed the hub's consoles grey while the bake laid rust over half of them
  (recipe rusted_metal's bare at the scene's wear, 2026-11-05), found first at likeness. A take whose models carry
  no measure is unknown. `place_line.make_paint` (rented) stays the people's. Check:
  `route_check.py`, bake_check's against the bake's specs.json, a surface with its own wear held at that wear
  (`own_wear_checked`). Recheck (paid, one batch, the one-shot sort after the bake): a take the parts left off
  its colour is a gap with no ask; the rest are drawn from every view, each part flat in its library surface's
  colour (its token's where it has settings), and asked once against the close-up; all match passes, else "no
  library surface fits" names it (`gate:finish-route-recheck/library surface fits:<take>`), Gemini's token,
  roughness and metal kept as the gap's `suggested`. The list's settings never edit materials.json.
- **The recheck's picks are applied before the parts** (#118 point 3; a list asked again returns its cached mis-pick):
  `finish-route-picks` (`recheck_picks.py`, set in the table by `stages.picks_applied`, Claude on this PC at EUR 0,
  never Gemini) drafts the parts as surfaces-parts makes them and asks the recheck's own question of them (the recheck
  row's request, so its cached answer). A failed take is picked only when the answer names a library token, roughness
  and metal for every finish it failed and each token lies within `COLOUR_DELTA_E` of that finish's close-up colour;
  else it is not picked, its reason kept (a take the free colour check failed, no token, no colour measured, a token
  off the close-up). surfaces-parts then makes the list with the picks over it (`recheck_picks.make_parts`: token,
  roughness, metal, seed and own wear kept, `picked` on the finish), so the parts' colour check, bake, paint gates and
  the recheck after the bake judge a pick as they judge the list's own; with no pick the parts come out the same, so
  nothing after them moves. One pick a take: a take the recheck after the bake fails again is a gap. A take the free
  colour check failed, which the recheck never asks, is picked too (`colour_picks.py`, the picks row's make, #118 group
  C): each finish off its colour takes the scene library's token nearest its close-up colour within `COLOUR_DELTA_E`
  among those keeping what the list meant (`finish_parts.hue_kept`: the colour its words name, else its listed hue;
  its recipe, roughness and metal kept); a finish with no such token, or whose nearest is its own (off by order),
  leaves the take unpicked, a gap by name.
- **Claude asks the palette, library, list and recheck** (coordinator for the owner, 2026-10-27, after the
  side-by-side on #36: Claude matched or beat Gemini on each, every gate passed): the table wraps their makes
  (`score/stages/__init__.py`, `claude_asks.asking_claude` on `claude_asks.ROWS`): the module's own make runs with its
  `ask` sending Gemini's request as it was to
  `score/adapters/models/claude_code.py` (`claude -p`, claude-opus-5-5, the owner's subscription, EUR 0, cached and
  ledgered), never route_ask's Batch API. The switch sits there and in the framework's table, not in scene_palette.py,
  scene_library.py or this folder's `__init__.py`, because body_faces.py and ground-join read those: editing them would
  re-key rows that do not switch. Environment 1 runs on the owner's PC
  (`tools/cloud/this_pc.py`); on a machine with no Claude Code (the conductor) the row stops with "runs on this PC",
  never asking Gemini instead. Their `paid` and `euros` in the table still read as Gemini's until a measured run.
  body-face stays on Gemini (no reference to judge a face by). Where the rest of this overlay says Gemini or the
  Batch API for these four rows, read Claude.
- **The bodies' faces are environment rows, one a body** (`body_faces.py`, `body-face-<body>`, paid, 2026-10-22: score_lib
  withdrew every old surface, so nothing made `earth_face` and the like): each body of the environment concept's
  setting that does not shine gets one Gemini 3.1 Pro ask in the Batch API, from the concept in force alone (its style
  line, the body's physics filled from `data/physics/bodies.json`), answered as its own palette and one variant of the
  natural ground its physics call for by rule (`score/stages/natural_grounds.py`, the row's `ground` param, never
  asked), `<body>_face` (face.json, materials.json). surface-library gives each terrain row of a scene's kept inventory
  its natural ground by the same rule (its words, else its body's physics at the kept site), in the question and
  its gate. The light layer's sky (`light/sky.py faces_of`) and the
  films (`body_faces` in the cockpit state) read that output, never a library name. Guess-priced from surface-library's
  one measured ask until a face run is measured. Wired in `score/stages/__init__.py` (`BODY_FACES`), so no surface row's
  code version moves.
- **Every paid ask runs once: the finishes layer is a batch** (CONTEXT.md, the owner, 2026-10-20; #21). The finish
  route's asks go as one Batch API job a row run (`google_batch.py`: a started line each before the send, the job's
  name kept so a run cut off mid-wait picks up the same job, never sends it again; a failed, cancelled or expired
  job, an error answer or a send cut off is its takes' gaps). A list ask (`finish_ask.finish_list`, the prop batch's finish pick) is made once, no ask again
  after a timeout or a dropped connection (`finish_ask.generated`): Google may bill a call cut off mid-way, and
  `google_spend` counts it at its estimate. Only a refusal that did no work (HTTP 429, 500, 503 or 504) is asked again, the
  wait doubling, at most `REFUSED_ASKS` times; a Batch API job that answers a poll with 404 is gone: its takes are
  gaps at once, never polled again. An ask with no usable answer
  (`finish_ask.UNANSWERED`: a timeout, a lost connection, refused every time, a reply that does not parse) makes its
  take a gap, named in its row's gate (`judge_list`, `judge_recheck`); the takes
  after it are still asked once, and new spend on it is a new batch and a new ask. Any other HTTP status (400, 401,
  403, 404) is a set-up fault, not an output's: it stops the row once instead of making every take a gap and a
  ledger line. A refused send is on the Google ledger as started then failed and counted at its estimate
  (`month_euros`) though Google billed nothing: the books lean high until Google's billing
  export (#13) reads the month; `google_spend.py` stays unedited (an edit re-keys the close-up rows). The list ask
  (`finish_ask.finish_list`) takes the close-up's measured colours (`finish_ask.REGIONS`), with thinking held low and
  on the flex tier (`LIST_TIER`, half price, a 900 s timeout: the request's own `serviceTier`, never set in
  `google_spend`). 
- **Each such gap is a batch gap carried down the line** (`../batch_gaps.py`, score's overlay): the list (no usable
  answer, or a list off the library), the split (any fault), the bake (a take's job that brought nothing back) and
  the recheck name theirs in `batch-gaps.json`, each with those of the rows they read; the views leave out a take the
  prop route's gaps name, the split leaves out the list's, the parts list them as left out, and the table moves only
  those takes' faults from each row's gate (`stages.BATCH_GATES`). The rows after the views declare a take's raw
  files only where they are there (`surface_data.take_files`), so a gap's missing take stops none of them; the
  cockpit still finds a lost take through `take_patterns`.
- **A library change re-keys only the rows that read the library** (the route's list, split (its palette
  tokens), parts, paint, bake, recheck and check: `route_data.library_files`, `surface_data.line_files`); its views declare none
  (`route_data.shape_files`), so a new surface re-asks the list and leaves the renders where they stood. On 2026-10-12 the making folder in `job.json` and card renders that differed run to run made one library change
  re-render every place and re-draw every view map (about EUR 50).
  Before pushing a change, list the rows it moves with `python -m score.stages.moved <base> [<head>]` (code versions
  and every declared file: a code-only check missed the turntables' declared `blender_cloud.py`, 2026-10-14);
  `score run` lists the re-buys again before it starts and refuses over EUR 5 without `--rebuy-reason`.
- **The paint and bake rows (and the people's paint) key only what they read of the library**
  (`library_reads.py`, set in the table by `score/stages/__init__.py` `library_narrowed`): the bake job's specs
  (every variant), with their recipes, families, pictures and the kinds' details; nothing of place.json (2026-10-21:
  the scene palette, an input, gives the wear and tokens). A surface added for one place re-keys no other place's paint (2026-10-13: the
  hub's assembly wanted about EUR 60 of re-buys). Before making one, the runner keeps its accepted output under the
  new key when nothing it reads changed (`carry.py`: the library parts rebuilt from git at the record's commit, a
  committed record only); a row whose own code changed carries only with a proof stored as evidence on the output
  (`carry.proof_fault`: every changed file named with why, the free rows before it remade to their accepted outputs).
  `python -m score.stages.surfaces.carry` lists what carries and why not.
- **Each finish's surface is checked against the close-up's colour** (`finish_parts.checked_finishes`,
  `COLOUR_DELTA_E` 32 CIE76, set on round 4's six models): the colour only chooses among library surfaces (the
  nearest of the listed one's family); a finish none fits gets a tinted proposal in the registry and fails the paint
  row's gate "colour against the close-up" by name. Every surface taken over the listed one (the family's nearest,
  the room's kit surface, the order's) keeps the list's meaning (`meaning_kept`; the audit of 2026-11-04: by colour
  and family alone the kit took 161 finishes, handrails as floor grating, counters as tiles, rusted steel as clean
  paint, and the re-pick took gold foil to silver, red cables to black hose, glows to glass): the same recipe (so a
  glow stays a glow and a floor pattern stays off what the list did not pattern), and the hue its finish's colour
  words name (`COLOUR_WORDS`, `HUES`), else within `HUE_DE` 10 of the listed colour in a*b*, lightness free; none
  such, it is off its colour. The parts row's gate "kept the list's meaning" (`route_parts.judge_meaning`, wired in
  the table, `stages.meaning_checked`) fails a moved finish whose painted look (`looks`) lost them, and a take whose
  largest finish moved off the colour its row's name names. A finish is measured on its label's brighter half, a
  dark one (library L* under `DARK_L` 35) on all its pixels: the light lifts blacks' brighter half to L* 40 to 45.
  Glass, screen glow, lamp light and print off the lit colour keep their surface (owner, #8: judged by their own
  colour), and so does a see-through finish of another family (`coloured_cover`: the garage beacon's red transparent
  dome, its pixels its highlights and what lies behind it). A finish the close-up shows over 10 L* lighter than another whose surface lies over 3 L* lighter in the
  library takes the nearest surface of its family that keeps the order, else the darker finish does, else fails the
  gate by its order (`in_close_up_order`). Lighter
  by 3 or less, the pair is reordered only by a surface nearer its finish's close-up colour (`reordered`): the bake
  moves L* on its own (the hangar's parts shelving: plastic_grey 1.5 under galvanized_steel baked 4.5 under it). A finish's close-up pixels
  whose first face from the camera is a see-through part (glass, light, screen, transparent or translucent words) are
  left out of its measure (`behind_left_out`). A finish drawn within one see-through finish (its outline at least
  90% that cover, `seen_within`) is laid as the cover, in every map: the model is the cover's shell with nothing
  inside, so the maps drew what lies behind it on the cover's own faces (the garage beacon's reflector on its red
  dome). Paint-row gate changes go here, in the parts row: a paint check's file is in the paint
  row's key, so an edit there repaints and rebakes every place.
- **New library surfaces are made the library's own way** (a recipe variant in a scene palette's token, by the
  surface-library row), never a picture's colour. `data/library/materials.json` is the method alone (wear levels,
  recipes' defaults, the colour settings each recipe names): never add a family there.
- **The bake takes today's library and the method's paint only**: every spec the library knows (painted, and the job's
  decals and screens) from the library, an old job's `regions` boxes dropped; a spec left naming a missing picture
  stops the bake before anything is rented. The job is written from git inside the bake (`bake_job.py`, 2026-10-19:
  the job files lived in the work folder and went with the old disk): each model's entry is the one its data writes
  out (a design's, prepare's hand-in, written without a turn, turned 0 or 90 degrees by its labelled take's footprint
  against its row: `bake_job.measured_turn`; the people line's as written; a slender row's, or a code build's (its
  take's code.json route "code", sent with its job: `bake_job.code_built`), at its labelled take's own proportions,
  one scale, its longest side the row's, never fitted side by side to its box: `bake_job.laid_size`, 2026-10-29,
  airlock's locker lamp built 0.046 m across its 0.1 m box, outline 0.813 built, 0.409 baked fitted; such a take
  standing on its longest side while its row lies is turned by its row (`tumble.square_turn`), its long side along
  the wall or floor it runs on, never up (hangar's wall pipes stood 22.7 m in a 15 m hangar, #36, 2026-10-31); a Pixal3D take at its own
  proportions, laid by the two sides that read (`bake_job.fit_within`, #128, 2026-11-15: all but its row's thinnest,
  that free side at most 3 times its row's and never past the row's next side, each side then stretched toward its
  row's by `STRETCH_MOST` 20% at most; scaled as one to its tightest side, a door's or monitor's thin depth bound it,
  workshop's monitors 0.16 m for their 0.4 m row) (`bake_job.laid_size`, `fitted_size`; 2026-11-08,
  #10: the plan wins on space, the model on shape; stretched to its row by axis, 264 of 386 baked takes were more than
  20% off their own shape, old_station's tunnel outline 0.70 as made, 0.466 stretched); a flat row's (the model gate's
  shape class "flat") by its face, its depth held apart at most 3 times its row's depth and never held under 5 cm
  (`flat_fit.py`, run by `inside/paint_fit.py` in route_bake's stead so bake_job.py and route_bake.py move no row,
  2026-11-12: fitted as one, its depth bound the face, quarters' picture frame laid 6% of its face), laid again so when the stand
  turns it square (`bake_job.refitted`), a person at his take's own width for his row's height (`person_size`), at near density (`route.NEAR`,
  `route.CHUNKY_FACES`), the specs every library variant (`palette_library.specs`, at the scene palette's wear and
  dirt), so a variant added anywhere re-keys every bake. A take standing tumbled in its turn is stood square first (`route_bake.stood_square`, `tumble.py`, #36: 154 of env1's 406 baked models stood tumbled, base's module 32 degrees): its oriented box set on the frame the way that keeps its row's proportions, a Pixal3D take only when that turned pose outlines its own close-up at least as well as its made pose (`take_outline.py`, the likeness gate's outline in numpy, scipy and PIL so the card scores it; the close-up rides the job; lab's desk_divider outlined 0.467 as made, 0.296 turned 20 degrees), else kept as made, saying why; then measured again as it bakes (`route_bake.squared_again`: make_chunky `--shapes` writes its cut-down copy fitted, remeshed and its feet levelled, `square-again` measures it with the check's own measure and turns it again, at most `SQUARE_ROUNDS` times; a turned take still over 10 degrees off takes back the pose it was made in, saying why: habitat's stove, 7 degrees on its take, baked 12.6). One guard list (`tumble.keeps_pose`, by row kind, anchor and words) keeps a row's pose and leaves it out of the SAM-box width rule (`bake_job.boxed`, `likeness_row.drawn_size`): a person (the people route, or a take its surface data names a person: the people line's looks, `bake_job.person_take`; he keeps his take's own width for his row's height and stands in his raw take's pose, the finish's stand undone, `bake_job.person_turn`: the stand had turned the A-pose looks a quarter round and leaned, pilot's outline 0.465 baked, 0.917 so laid, #36 2026-10-31), a row leaning or lying (stance.json, `leans`), hanging (the resting rules' hanging words, or its anchor the ceiling), with no up (ground debris, cable) or a code build (its take's code.json route "code": the bake turned quarters' string lights 34 degrees off the lean its build gave it, outline 0.544 to 0.101, #36); the paint leaves the same rows' feet as made (`place_line.stands`, `feet_rows`); surfaces-check's `stands square` leaves the same rows out and fails one still tumbled by name with its angle (likeness's outline cannot see pose). A holder model a moving door stands on gets that door's
  recess (`route_bake.recessed`, #72; in route_bake.py, which the bake alone hashes): the place's recesses file (`{home}/design/recesses/<place>.json`, score/review/holders `keep` writes it beside the relations, never the whole relations file, so a holder change that moves no recess keys no bake; a bake input once
  derived, sent with each job) cut into its entry when the job is written, never into `design/surfaces/` (Pixal3D
  keys that file): a box on the face the relation names, kept within the face's span less `RECESS_BACK` at each end (a
  side wall beside it: flush, base's recess cut its module's W wall away), lined before it is cut (make_chunky
  `lining`: a wall on its back, sides and top out to the model's front found by ray, so a hollow take keeps a pocket,
  not a hole into its inside),
  as deep as the door's motion needs (its swing's sweep, or its thickness and slide room) and widened beside it (a swing's hinge side by its thickness, so it lies clear of the side wall at full open; a slide's way by its width and thickness) and never through the
  model (`RECESS_BACK`: a recess with a back). Nothing else is read for an entry: the kit rooms' and
  outside places' own entries (old kits, inventories, the kinds' details, composites) went with them on 2026-10-21. A
  model its data writes no entry for (`bake_job.refusal`, entry_of's own checks run without the take) is declared as
  a file that is never there, naming it (`library_reads.bake_refusals`), so the run refuses before anything is
  cleared; the crops bake too.
- **The people's paint runs on rented processor machines, a job a take** (the place lines' paint runs in
  their bake's card job, `route_bake.py`; `make_paint`, `inside/paint_take.py` through
  `blender_cloud.py`; paid, cleared like the bake): heavy steps run in the cloud (owner, 2026-10-12); measured up there,
  campgrounds' takes peak at 1.5 to 3.4 GB and crane-r1 at 34.8 GB (the PC's cap is 14 GB). Up there Blender's own
  Python runs `place_line.py paint-take` with the prop environment's pinned packages and says its peak memory and any
  signal; the registry proposals are written here first. `tools/props/heavy.py` refuses the step anywhere the
  cloud runner's mark (FARM_LOCAL_MODELS=1) is not set. prop_env.py is left alone: an edit there re-keys every row that
  hands over to it.
- **The check holds a bake against its surface worn and dirtied as its place wears and dirties it**
  (`bake_check.on_surface`: the library colour worn toward its recipe's `bare` as far as the place's wear, then
  toward the place's dirt colour as far as its dirt; the wreck's whites bake to L* 69 in regolith at 0.6 and pass,
  the engine room's thin hazard trim, worn 0.8, baked a third bare steel and passes, a wrong surface still fails). A part's baked colour is its triangles'
  area-weighted median on each of L*, a*, b* (`bake_check.area_median`), never the triangle at the median L*: lab's
  junction_box_1 (2026-10-14) baked its crane yellow right on 56% of its area, and the grey panel triangle at the
  same L* that L* alone picked failed it at dE 37.
- **A standing model stands level** (`bake_check.judge_stance`, gate "stands level"): each footprint quadrant of its
  lowest quarter ends within 3 cm of its lowest point (the hangar's rack stood on a middle part, its legs 22 cm up;
  the paint's feet check, in shares of size, let it pass). A model its paint did not level (no floor or held row) or
  whose inventory row names a lying class (`data/checks/stance.json`: torn wreckage) is left out. Glass, glow, lamp
  light and print skip the close-up comparison (#8), and so does a coloured see-through cover the paint judged by its
  own colour (`cover`: the garage beacon's red_plastic dome), left out of `close_up_colours`; other finishes judged
  by their own colour stay in it for the order and one-look checks. `close_up_colours` keys each colour by the name
  the surface bakes as (`route_settings.settings_name` where the finish keeps the list's settings, as
  `route_bake.named_records` names the parts): keyed by the variant alone, every surface with settings was compared
  with nothing in the close-up, order and one-look checks (found 2026-10-23 on astronaut-made).
- **The check is its own module** (`bake_check.py`, so its edits move the check row alone; wired in
  `score/stages/__init__.py` until the 2026-10-12 fan-out ends). Each baked triangle is named by the bake's own ray (`bake_check.ray_surfaces`:
  from its middle make_chunky's reach out along its normal, inward, the first labelled face hit), never the nearest
  part: the cut-down copy stands a wall proud, and beside a thin post the post lay nearer than the facade the bake
  met (far_city's pencil tower, 2026-10-13: post_dark failed at dE 45, baked right); the ray starts where the bake
  wrote the texel the check samples (`sampled_points`: its centre's point, often on a neighbour of a triangle under a
  texel; the flat's bowl stack's glass rims failed at dE 66.6, baked right). A near-black triangle is a blotch only when its colour lies over
  `BLOTCH_DELTA_E` from every surface within its reach: on a border it may bake its neighbour (the seed tray's paper
  label on black plastic passes), a black smudge along the border still fails. It also fails a model whose surfaces
  bake to one grey look its close-up does not have (`one_look_faults`: no two told apart at the place's view distance,
  by Stone, Szafir and Setlur's measured ND(50) for their size in degrees from the nearest view (`seen_degrees`, the
  kit's spots, the scene record's objects, the machines record's machines and the scene record's eyes; owner, 2026-10-13: a fixed 12 failed the wreck's access cover on a step he
  sees), each near neutral, the close-up's over 24 apart; a model with no view distance is named; the greenhouse's water tank and crop crate, 2026-10-12: the check of bake against
  library alone passed them at dE 0), two opaque surfaces whose lightness order the bake reverses (`order_faults`:
  seen over 10 L* lighter, baked over 3 darker; the light moves L* but keeps the order), and a part baked over 32
  from its close-up colour (kept at 32: the close-up's light lifts right surfaces 15 to 30 L*, so a tighter number
  fails right blacks; compare a model's surfaces with each other instead).
- **The bake's texture layout is checked** (`uv_layout.py`, gate "texture layout sound", `uv_layout.judge_layout`,
  recorded by `route_check.layout_measured`, never in `bake_check.py`, which the people's dress reads; #92, after
  marso-skills' Apache-2.0 `audit_uv.py` and `measure_uv_quality.py`, rewritten in numpy over the baked .gltf): per
  model, its surface outside the picture, mirrored, stretched over `STRETCH` one way, under `DENSITY_FALL` of its
  median texels a metre, in charts under `THIN_TEXELS` wide, and its texels written by two faces, each failing over
  `LEAST` (1%, the check's PART_LEAST; outside on any share), by model and measure; a batch gate
  (`stages.BATCH_GATES`), so a failing model is a gap of its take. Measured 2026-11-05 on env1's 439 baked models: 31
  fail, 15 by shared texels (smart_project's folds on lumpy takes, the faces sharing a texel 6 to 13% of the model's
  size apart), 17 by sub-texel charts on small pictures. The back-face fault (a face toward the kit's back packed at a
  twentieth of the density) is ruled out: `inside/bake.py` no longer shrinks any face (removed 2026-11-23), and no model's density facing any axis is under 0.7 of another's (doors included). A model of one surface has no
  thin-chart fault (`ONE_SURFACE`, 2026-11-12): a thin chart takes its neighbours' colour, all its own finish; on env1's
  38 models failing it every thin strip is geometry under a texel at the model's own density, not the packer.
  The bake lays a layout that would fail again before it bakes (`inside/layout_fit.py`, run in make_chunky's place
  by `inside/paint_fit.py`, paint_bake.py's job with that last step, the card job's script set by `bake_fitted.py`
  on the bake row alone, `stages.layout_fitted`, 2026-11-12: paint_bake.py and what it starts are declared by every
  row whose code reaches route_bake.py, 28 rows, 11 paid): each single piece's packed
  layout measured as the check measures it and, only past the check's limit (`LIMIT`), laid again: faces on a
  shared texel (every one of env1's folds lies inside one smart_project chart, its layers 13 to 22% of the model
  apart, normals about 30 degrees apart) projected again on their own at 30, 15, then 8 degrees (`UNFOLD_ANGLES`), a
  round kept only when it shares fewer; then the picture's side doubled while the thin share is over `TARGET` (0.5%),
  up to bake.LARGEST. A layout the check passes, or one no laying again brings under the limit, is baked as
  make_chunky bakes it, so a bake moves only where it is fixed. Its measure is its own copy, so an edit of uv_layout.py moves no bake.
- **Every place's models are sized from its own scene record** (`stages.seen_from_record`, 2026-11-12): read
  beside wherever the scene-record row writes one, the earth places' too; with only the ship places', 46 earth
  models failed "baked matches its surfaces" on no view distance alone.
- **A base that slopes as one piece is brought down level** in the paint (`place_line.flattened_base`, after the legs):
  each footprint quadrant of the bottom quarter over 1% of the size up comes down its whole gap at its lowest point,
  spread by inverse squared distance and faded over the band; over 15% is a model fault, refused. Then an underside
  that is one sloping plane (`sloped_base`: 80% of its cells within 1% of the plane fitted to them, rising over 1%)
  comes down by the plane's height, never past the lowest point: the quadrants miss a ramp whose low strip runs
  through the middle (the square's guard hut, 2026-10-14: 14 cm across, it stood on a strip and tipped). Last, the face
  it rests on (`resting_base`: its convex hull's face under its weight) comes down level when it rises over 1% of its
  footprint's diagonal: the quadrants and cells miss a plinth rim under a level floor (the garage's control cabinet,
  2026-10-15: 2.1 degrees over). In the bake each step's 1% is at most 3 cm through the take's standing height, as
  the feet's is (`base_level.py`, run by `inside/paint_fit.py` in place_line's stead so place_line.py moves no row,
  2026-11-12: base's large hangar's 1% was 0.84 m, corners 34 to 60 cm up stayed and "stands level" failed it); the
  plane step capped only where the uncapped one found no plane (its 1% is also how near the plane its cells lie).
  A take the feet step stood on three feet or more (`base_level.ON_FEET`) has its base left as its feet stand: the
  base steps are for a base that is one piece, and beside feet a quadrant with none is an overhang (old_station's
  rover, on its wheels and docking leg, had its tube's underside brought 11.7% of its size down to the floor, a sheet
  hanging off its front, score #156, 2026-11-22). The bake's copy then comes down only by how far the remesh moved a
  quadrant over the full model's own (`make_chunky.copy_drops`), and "stands level" holds such a model to three
  quadrants on the floor (`bake_check.on_stance`). A take whose feet but its lowest, four or more (`base_level.FLOOR_FEET`), lie in one
  plane within the feet's tolerance stands on that plane: it is turned level onto it (at most `FLOOR_TURN`, 10
  degrees) and its lone lower foot cut at it (`base_level.on_floor`), never the others stretched down to it; its faces
  are kept within its finished box turned with it (`boxed`). Three feet always share a plane, so the rule below
  (never level by tipping) holds for them. The rover's four wheels lay within 0.17% of its size of a plane 7.5
  degrees off level, its docking leg 9.6% under it; stretched down to the leg they baked as teardrops (score #156,
  2026-11-22).
  Wear and dirt are
  the room's setting, applied where they have a cause (owner): a per-model amount read off the close-up is a
  picture-derived look (tried 2026-10-13, reverted). The one exception is the finish route's own wear: a library
  level the list gives a finish only with a cause the views show (owner, 2026-10-20).
- **The paint levels a take's feet before its bake** (`place_line.levelled_feet`, `tools/props/library/feet.py`):
  a take a row stands on the floor or ground (`stands_on_feet`, from the scene inventory and the resting rules,
  declared in the table, `stages.paint_inventory`: a designed place's hand-in, its rows naming their take and standing
  on a floor its reading made a row of (`on_floor`, `is_floor`: the reading's floor piece, group "kit: floor",
  whatever it is mounted on, as the cockpit's plates on its hull; its ground; or terrain or a slab resting on the
  floor, the ground or another floor), else the old inventory; never mounted on another object, part of the room's shell, fixed, hung, laid tilted on purpose (`leans`) or a pile of ground
  debris; a word of a description, such as a cabinet's "cables", is no class) has its short legs stretched onto the level plane through its lowest foot, in its own frame; a foot
  over a tenth of its size up is a missing leg and fails the gate "feet in one plane" by name. Never level by
  tipping the model: its own up is the reference (the water tank's top lay level within 0.25 degrees), but for
  a take on its floor in the bake's paint (above, `base_level.on_floor`). The bake
  levels such a take's cut-down copy again (`make_chunky.levelled_feet`, the take's `stands` from its labels through
  `library_bake.stands`): the remesh's voxels and the cut move feet apart (the hangar's 31 m ship, level in its
  paint, baked a front foot 22.2 cm up at 10 cm voxels), and the paint's 1% of size lets a 4 m piece keep 3.4 cm
  (the campgrounds' ice drill); each quadrant over the check's 3 cm comes down as `flattened_base` brings it.
- **Painting is 3D parts plus the shared library, only.** A picture's colours never reach a model: a map's label
  colours only name finishes, each part is painted from its finish's library surface.
- **The finish registry is a store item** (`registry.py`; `registry/surfaces/` in the store): append-only, the new
  library surfaces a method proposed, each standing as first proposed for the owner to accept into the library or
  not; until then the part keeps the nearest library surface the method named (`stands_in`). The paint writes it
  outside its key.
- **Per-place data is environment data** (`surface_data.py`, `data/surfaces/<place>.json`): the takes a place paints, the
  library name, the bake (model per take, the entries the route's own would not give written out), and `elsewhere`: the
  models it lays that another place claims. Everything is repainted, the owner's picks included (a pick chooses the
  model, never its old paint: owner, 2026-10-12); each take is painted by one place only, and a place reads a claimed
  model from the claiming place's bake (`elsewhere.json` in its bake output; the bake gate fails a claim the other
  place does not bake). A place with no file blocks at `surfaces-inputs`; one with no `bake` blocks at
  `surfaces-bake` before anything is cleared. A place with nothing to paint (code-built pieces only: the
  tube) has a file with no takes and a `nothing` line; its line has no surface rows (`Stage.applies`).
- **Gates never crash or pass on what is missing** (`surface_gates.guarded`: unknown with the missing file named).
- Steps needing trimesh run in the prop environment through their module's command line (`prop_env.py`), each make
  defined in its step's own module so that module is its code version. Tests: one file,
  `test_every_part_takes_a_library_surface_and_is_held_to_it.py` (the framework side, the finish route with Google
  and the paint's step faked, the method's steps, the bake job, the bodies' faces, the library keys), on the
  framework's Python.
- **Two rows are made through a module of their own, set in the table** (`stages.kit_and_lit_kept`,
  `stages.bake_checked`), so no row reading finish_parts.py, route_parts.py or bake_check.py (the bake, the recheck,
  the people's dress: 193 accepted rows) moves for them: `parts_kept.py` (surfaces-parts: a shell surface further
  from the close-up than the finish's own never takes it over; a code-built light's finish listed on a glowing surface
  is its lit one) and `check_seen.py` (surfaces-check: a ship place's view distance from a kit laid from its own
  scene record, sized by the bake). Fold them into finish_parts.py, route_parts.py and bake_check.py when a change
  there re-makes those rows anyway. So is surfaces-paint (`stages.feet_checked`, `feet_stand.py`): a take refused on
  its resting face alone (place_line.resting_base's rise across the band) passes "feet in one plane" when its baked
  model stands by the resting check's measure (cockpit's pilot seat, 2026-11-12), so place_line.py, in the bake's and
  84 paid rows' code, does not move; fold it into place_line.judge_feet when place_line.py moves anyway.
