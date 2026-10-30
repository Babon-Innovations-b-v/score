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
  face's seen colour, NaN when none is measured). Another method replaces the method's rows and writes it; the
  framework's rows (`place_line.py`: paint, bake, check) do not change.
- **The finish-map method is gone** (2026-10-20, #26): the crops are the places' own takes and the people's line
  runs the route's rows (`../people/line.py`), so its turntable, maps, names and SegviGen rows and modules were
  deleted. `finish_parts.py` keeps the route's shared steps on a take's faces and the finish check; `finish_ask.py`
  the list ask and what the route shares of it.
- **The line is the finish route** (owner, 2026-10-20, #18; library first): every surface that faces the air is a
  library material carrying the look (palette colour, wear, shine, seed), so there is no paid paint step and no
  finish-map picture. Rows, in `ROWS` (`__init__.py`), on every painting place's line: `finish-route-views` (free,
  `route_views.py`), `finish-route-list` (paid, `route_list.py`), `finish-route-split` (free, `route_split.py`),
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
  counted (`unseen_faces`) and the split walks its nearest seen face's finish onto it. Each view's colour regions:
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
  object's wear and dirt pattern is its own), a new surface only when none fits with any settings; its wear the
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
  measure names the colour faults before it. `place_line.make_paint` (rented) stays the people's. Check:
  `route_check.py`, bake_check's against the bake's specs.json, a surface with its own wear held at that wear
  (`own_wear_checked`). Recheck (paid, one batch, the one-shot sort after the bake): a take the parts left off
  its colour is a gap with no ask; the rest are drawn from every view, each part flat in its library surface's
  colour (its token's where it has settings), and asked once against the close-up; all match passes, else "no
  library surface fits" names it (`gate:finish-route-recheck/library surface fits:<take>`), Gemini's token,
  roughness and metal kept as the gap's `suggested`, never applied. The list's settings never edit
  materials.json.
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
  row's gate "colour against the close-up" by name. A finish is measured on its label's brighter half, a
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
  airlock's locker lamp built 0.046 m across its 0.1 m box, outline 0.813 built, 0.409 baked fitted; a Pixal3D take's
  width for its height its own where both its row's SAM 3 box, read from the hand-in its job is sent, and its take
  disagree with its row by more than the model gate's spread, only its width moving (a row no wider than tall), its
  height and depth the row's: `bake_job.boxed`, owner 2026-10-29, "Yes, land the rule"; a height moved too grew 22
  low things' tops seen from above against their pictures, 2026-10-29), at near density (`route.NEAR`,
  `route.CHUNKY_FACES`), the specs every library variant (`palette_library.specs`, at the scene palette's wear and
  dirt), so a variant added anywhere re-keys every bake. A take standing tumbled in its turn is stood square first (`route_bake.stood_square`, `tumble.py`, #36: 154 of env1's 406 baked models stood tumbled, base's module 32 degrees): its oriented box set on the frame the way that keeps its row's proportions, a Pixal3D take only when that turned pose outlines its own close-up at least as well as its made pose (`take_outline.py`, the likeness gate's outline in numpy, scipy and PIL so the card scores it; the close-up rides the job; lab's desk_divider outlined 0.467 as made, 0.296 turned 20 degrees), else kept as made, saying why; then measured again as it bakes (`route_bake.squared_again`: make_chunky `--shapes` writes its cut-down copy fitted, remeshed and its feet levelled, `square-again` measures it with the check's own measure and turns it again, at most `SQUARE_ROUNDS` times; a turned take still over 10 degrees off takes back the pose it was made in, saying why: habitat's stove, 7 degrees on its take, baked 12.6). One guard list (`tumble.keeps_pose`, by row kind, anchor and words) keeps a row's pose and leaves it out of the SAM-box width rule (`bake_job.boxed`, `likeness_row.drawn_size`): a person (the people route; he keeps his take's own width for his row's height), a row leaning or lying (stance.json, `leans`), hanging (the resting rules' hanging words, or its anchor the ceiling), with no up (ground debris, cable) or a code build (its take's code.json route "code": the bake turned quarters' string lights 34 degrees off the lean its build gave it, outline 0.544 to 0.101, #36); the paint leaves the same rows' feet as made (`place_line.stands`, `feet_rows`); surfaces-check's `stands square` leaves the same rows out and fails one still tumbled by name with its angle (likeness's outline cannot see pose). A holder model a moving door stands on gets that door's
  recess (`route_bake.recessed`, #72; in route_bake.py, which the bake alone hashes): the place's relations file (score/review/holders `recess`, a bake input once
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
- **A base that slopes as one piece is brought down level** in the paint (`place_line.flattened_base`, after the legs):
  each footprint quadrant of the bottom quarter over 1% of the size up comes down its whole gap at its lowest point,
  spread by inverse squared distance and faded over the band; over 15% is a model fault, refused. Then an underside
  that is one sloping plane (`sloped_base`: 80% of its cells within 1% of the plane fitted to them, rising over 1%)
  comes down by the plane's height, never past the lowest point: the quadrants miss a ramp whose low strip runs
  through the middle (the square's guard hut, 2026-10-14: 14 cm across, it stood on a strip and tipped). Last, the face
  it rests on (`resting_base`: its convex hull's face under its weight) comes down level when it rises over 1% of its
  footprint's diagonal: the quadrants and cells miss a plinth rim under a level floor (the garage's control cabinet,
  2026-10-15: 2.1 degrees over). Wear and dirt are
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
  tipping the model: its own up is the reference (the water tank's top lay level within 0.25 degrees). The bake
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
