# The bible

The single source of truth for how SCORE works. One file, chaptered. A chapter ID is the slug after the `##` (for
example `architecture/system-context`); root [`CLAUDE.md`](../CLAUDE.md)'s chapter map points at it, and a link reads
`docs/bible.md#architecturesystem-context`.

Read the chapter the work touches, never the whole file. When you learn something load-bearing that a future reader
would otherwise re-derive from code, write it into its chapter in the same session. When a chapter contradicts the
code, the code wins and the chapter is fixed on the spot. Vocabulary is in [`CONTEXT.md`](../CONTEXT.md), decisions in
[`docs/adr/`](adr/), the state of ongoing work on its GitHub issue, history in git. Each directory's own rules are in
its overlay.

---

## architecture/system-context

SCORE turns what one creator decides into a complete, owned, editable environment that an engine loads; nothing is
generated while it is played.

- **The creator** decides top down in the creator cockpit: the environment concept (style and physics), then each
  scene's concept, parent before child. A lock is his approval. He buys a batch with one yes.
- **The framework** reads each locked design into a scene inventory and a plan on its own, then builds every scene's
  layers in one batch: models through the prop pipeline, materials, the base layer, effects, motion, physics, light,
  sound and people, each from the design alone, composed in OpenUSD with every parent scene holding its children.
- **Outside services it calls**: Gemini 3.1 Pro (readings, plans, prompt rewrites, finish lists, Discuss), Nano Banana
  Pro (concept and top-down drawings), Qwen-Image-Edit (close-ups), SAM 3, Pixal3D, MOSS, Kimodo and the rest on rented cloud machines that delete
  themselves (`tools/props/cloud/`, Scaleway the current cloud backend). No model runs on the coordinating machine.
- **score_lib**, the creator's library: everything a scene shows comes from it, and everything a batch accepts is
  handed to it.
- **Out**: each scene's OpenUSD stage and scene package, the environment film, the library entries. The game 2099 was
  the first user; its engine adapter stays in its own repository.

## architecture/components

Two sides: the coordinating machine runs plain Python (the design, the runner, the store, the checks, the cockpit's
store side; `.venv` from `pyproject.toml`), and every step that loads a model, bakes or renders runs on a rented cloud
machine that deletes itself. No model runs on the coordinating machine (`tools/props/local_models.refuse_here`).

- `score/graph`: the runner (`python -m score run|status|resume|plan|price|moved`). Keys every node on its computed
  code version, contract, parameters, seed, pinned models and inputs; makes a node only when its key has no finish
  record; accepts an output itself when every gate passed and nothing got worse; drives every scene's line side by
  side from a frozen copy of the code. Its overlay (`score/CLAUDE.md`) has the detail.
- `score/stages`: the stage table, one row a stage, a node a stage for one scene or for the environment.
- `score/store`: every output by content hash, written once, never overwritten, at `$PROPS_HOME/store`.
- `score/contracts`: each output's schema, version and house units (metres, seconds, degrees, Y up), checked by the
  maker and every reader. `score/checks`: gates answer pass, fail or unknown; unknown blocks like fail.
- `score/review`: the design (`architecture/design`) and each output's review page.
- `score/dashboard`: the creator cockpit (`architecture/cockpit`), the sync, the checkout, the films.
- `score/adapters`: models, compute and engines. `compute` clears a paid node (its inputs passed and stand accepted, the
  month's books known, the batch's stop has room for its forecast) and `require_cleared` refuses every rent point
  without a clearance or the owner's override; prices come from measured per-unit numbers (`data/costs/per-unit.json`,
  written by `tools/costs/per_unit.py`), and a node with none has no price, only a guess shown apart.
- `score/library`: the one reader of score_lib's entries (ADR-0007); `tools/library/library_files.py` fetches its files.
- `tools/props`: the prop pipeline (close-up, Pixal3D in a cloud batch, finish), the cloud runners
  (`tools/props/cloud/`, through the provider interface `provider.py`), the surface library's recipes
  (`tools/props/library/`).
- `tools/usd`: the OpenUSD writers and checks (export, colliders, physics, motion, sound, complete).
- `tools/characters`: rigging, clips and the characters layer; `tools/sound`: the sound picker and loudness rule;
  `tools/review`: review pages, films' checks and the viewer; `tools/blender`: headless Blender, never a window.
- `vendor/`: third-party tools as released, each pinned with its licence (ADR-0002).

**Data in git** (`data/`): the environment's shape and rules, never a scene's design. `definitions/world.json`
(environment 1's seed), `places/within.json` (which scene sits within which, merged scenes, parts),
`physics/` (the cited bodies table, materials, environment 1's starting physics), `checks/` (row kinds, measured
effects and motion speeds, library exceptions), `costs/per-unit.json`, `films/` (starter scripts), `library/` (the
recipes' method and lamps), `sound/` (catalogue, licences, loudness, moving sounds), `fonts/`, and the people
line's own records. A scene's design lives outside git, under `{home}/design/`.

**Everything from the library** (owner's hard rule, 2026-10-18). Every finish, model, kit, effect, light, sound,
character, ground and algorithm a scene shows comes from score_lib, or is a written exception in
`data/checks/library-exceptions.json` (the scene, the prim or pattern, what, why, who allowed it and when; one without
a reason or an owner is refused). Every finish is a library surface (a ProcFunc recipe coloured from the scene
palette's tokens); a picture-made model keeps its geometry and gets its finish replaced. The library check
(`score/stages/complete/library`) traces every bound material, model, emitter, light, sound and character of an
accepted assembly to an entry and lists what does not trace.

**The library starts empty** (owner, 2026-10-21: "all old stuff is retired"). Every old surface, model, sound pick,
kit and per-scene record was retired, so the batch makes everything fresh: each scene's materials by its
`surface-library@<scene>` row (one Gemini ask on the locked concept, its scene palette and its objects' kinds), its
models through the prop pipeline. A library entry is reused only when the owner locked it or it was made under today's
route (the hash of the route stages' code and contracts, stamped into each entry; `score/stages/library` `route`).

**The library handover** (`score/stages/library`, its overlay): `library@<scene>` and `library-world`, the table's
last free rows, hand every accepted output to score_lib through its own command and gate on its report
(`handover.json`). A scene is complete when its library node stands accepted. Library items are never rendered as
paid preview videos (owner, 2026-10-22: the retired `library-clips` row, a Cycles clip per new item on a rented card,
was "waste"): the cockpit's Library page shows each item live and free from its web copy (CONTEXT.md "item
preview").

**Gaps** (`score/stages/complete/gaps`, its overlay). A free standalone check (no row, so no key moves) reads the store,
the design and other checks' findings and writes each scene's gaps: an OpenUSD overlay (a guide box for every row with
nothing made, the gates each faulty object fails, the route steps the scene lacks) and `findings.json`, each gap
naming the node that fills it. The cockpit lists, outlines and prices them. What a scene needs comes only from its
design.

**Engines.** A scene's output is its OpenUSD stage and its scene package (`tools/props/library/package.py`:
`objects/<name>.gltf` and `scene.json`, metres, Y up). An engine's own import (the game 2099's Godot adapter) lives in
that engine's repository; the framework reads nothing from a game.

## architecture/design

The design is everything the creator decides before a batch: the environment concept, then for each scene, parent
before child, a concept he locks, read into a scene inventory and a plan with no further yes. The code is
`score/review/` (written only in the owner's process, or by an agent carrying his words); the cockpit's pages for it
are in `architecture/cockpit`. Terms: `CONTEXT.md`.

**The environment concept (EC)** (`environment_concept.py`, `setting.py`). Style, physics, reference pictures and the
scenes with what each may hold, filled in by a short set interview (one Gemini 3.1 Pro call an answer, his Send the
yes) and then locked. The physics, at whatever scale he sets: bodies (a real one's values from the cited table
`data/physics/bodies.json`, an invented one's radius, mass, orbit and spin), lights (a far light with no body on its day
path), backdrops (a dome or a skyline), plots (flat ground with a gravity) and sites (latitude, longitude and height on
a body, metres on a plot). Exactly one root body; there is no fixed sky. Kept as versions
(`environment-concept/<world>/versions/` in the store); while unlocked nothing is drawn or locked, and a draw, lock or
plan made under another version is out of date. Unlock asks twice. References go to the private bucket, never the repo.

**The environment plan** (`environment_plan.py`): the first parent's plan, one map a ground of the physics with each top
scene's site where the physics puts it and the ground falling away with its body's radius; the plan writer's call writes
only the scene times and terrain spots. A site's footprint, size and blocks are read from its top scene's own plan (the
one its plan page shows, `plans.current`) on every settle, never written or edited apart, so the two cannot differ (the
owner, 2026-10-23); two sites whose footprints overlap where the physics stands them are a gap. Its page draws each
site's plan with plan.js's own sheet at its true footprint and distance. What
each site sees overhead at its scene time is worked out from the physics (`overhead.seen`: every light, every other
body at its true direction, size and phase, every backdrop) and kept per scene (`scene_sky.py`, a child scene using its
top scene's site); no record, data file or constant holds a sky of its own.

**Which scenes exist.** The EC's scenes and the child scenes each parent's plan lays out
(`data/places/within.json` for the ones kept in data, his kept plans for the rest; `concepts.tree`). A part of a
scene's outside (the Square's launch) is drawn in that scene's concept and has no concept, card or build of its own. A
scene he merged or removed has no card and no build.

**The concept draw** (`concepts.py`). One Nano Banana Pro call, its wording built by one rule (`generated`): what the
scene is, its look, its doors and what it holds, its size in relative words, the fixed view, the style line; his own
edited wording, once sent, is the scene's wording. Pictures go in this order: the crop of the parent's locked
concept showing what holds it, the locked concepts of scenes it opens
into (so a shared door matches), his references.

**The chain rule for child draws** (`concepts.step_refusal`, enforced on the page and on the store's machine). A scene
is drawn or locked only once the EC is locked, its parent is locked, read and planned, and the parent's plan outlines
it. Its draw is its inside alone (its walls, floor, ceiling, doors and furniture, windows glass on a plain dark
backdrop, no hull, no text), sent the crop of what holds it, never the whole parent, and one compartment block its
siblings share word for word ("<holder> is divided into these compartments: 1. ... This concept is number N"). A
draw is current only under the current wording, the same parent locks, the same EC version and an unmoved room; anything else is out of date, and a locked one is flagged, never unlocked.

**The concept review** (the design page's concept panel). He drags marks (boxes, each with a note) and writes notes.
Redraw with notes is two calls under one yes: Gemini 3.1 Pro rewrites the prompt from the draw, the marks, the notes,
the marked parent locks and the open discussion, the rewrite becomes the scene's wording, then one draw. Discuss is one
Gemini call answering his note about the draw shown; the thread goes into the next redraw and is closed by it. Lock
picks a draw: the lock is the approval, hands the concept to score_lib and starts the reading. Every price comes from
`data/costs/per-unit.json`, and a click whose shown price no longer matches is refused.

No grey model is built in code before a concept (the blockout, retired 2026-10-23: "we have the prop pipeline to get
the rough shapes first anyway"); a scene's rough shapes are its rough model (`stages/rough_model`). Locks drawn on a
blockout keep their record's `blockout` field, which tells the plan drawing their fixed south-east view.

**The scene inventory reading** (`reading.py`; runs on its own after a lock under the standing allowance, at most EUR 1
a scene, cleared as `inventory-read`). Gemini 3.1 Pro names rows (name, noun, count, size in metres, anchor, region);
SAM 3, on one rented card for every scene of the run, looks for each row by its own words, then its noun. Duplicates are
merged first. The agreement cut-off: a row is kept only where both found it, its count SAM 3's instances. Kept as read
without SAM 3: structure, terrain, sky, and rows holding or standing in a child scene. The large-single-object rule: a
row Gemini counted once whose region covers at least 2% of the picture and is no other row's box is kept, boxed by its
region (`seen_large`). The rest is kept as skipped, never a row, a gap or a plan input. Gaps are only kept rows with no
metres or no anchor. `--again` reads a scene again with SAM 3 only.

**The plan method** (runs on its own after the reading, `plan_writing.AUTOMATIC`, cleared as `plan-write`; else his
Make plan click):

1. **Top-down drawing** (`plan_drawing.py`): one Nano Banana Pro call redraws the locked concept from straight above,
   the parent's plan sent with this scene's box marked.
2. **Written plan** (`plan_writing.py`): one Gemini 3.1 Pro call reads each element's position off that drawing (never
   packed from words), in metres from the scene's box on its parent's plan, else from the rows' metres, in the house
   schema with its architecture (outline, walls, openings with swing, levels, stairs, roofs, terrain, a section). A run
   of shelving or crates is one item with its count.
3. **Checks against the concept** (`plan_checks.py`, free): every row placed as often as it counts, inside the outline,
   no two on the floor in each other, every door and standing spot reached on foot, child scenes tiling, and the
   arrangement as the concept shows it (order, place across the view, facing).
4. **The fix step** (`plan_fixes.py`): free fixes first (people stood on spots, spread runs split, missing things
   placed where their boxes project, facings turned, overlaps parted inside the walls), then at most two automatic
   Corrects (notes rounds back to Gemini), each kept only when it leaves fewer gaps. Only what is left shows as gaps,
   each saying why.

Invariants: his plan and edits always win (a plan written after his edit is shown as an `edited` gap, never over it);
creator data wins (the ship's floor plan, `data/definitions/ship_floor.json`, is laid at its own size where the drawing
puts it); fixes and rewrites never move a locked child scene's room, only his edit does, and a moved room puts its draws
out of date; people are standing spots (`plan["people"]`, position, facing, row), never items, and a crowd gets none.

**Plan editing in the app** (`plans.py`; the page's `plan.js`). He drags, resizes, moves doors and person spots, adds,
renames or removes child scenes, marks the plan and asks for Correct with notes. Drop decides: a box in open space is a
new child scene; a box fully inside a room is a thing in that room (no scene, no card; named in
its draw's wording); a room dropped on or resized over another is one shared room round both, named from
both, keeping the id it landed on. Every one comes with an undo and saves itself as his edit (`plans/<place>/edits/`
and `named/`). Once a scene's design is done (concept locked, read, plan written or edited), the sync keeps it under
`{home}/design/` (`plans/`, `inventory/`, `concepts/`, `sky/`), which is all the build reads (`python -m
score.review.plans keep`). A scene added in the app joins the build then; until then it is a scene in design.

**The film** (`score/dashboard/films`, its overlay) is the last design step, after the scenes and before Buy. Every
environment opens on its default film (`default.py`: the owner's script's structure filled in from the environment's
own physics and scenes: the steps of the app, one unbroken scale zoom from the physics down into a top scene's rooms,
then every other top scene body by body in the environment plan's order). He edits the script and previews it free,
then locks it; the lock is the approval. `environment-film` reads only the locked script (a lock moves its key), Buy
waits while none is locked, and Unlock is refused once a batch bought a film row on it.

## architecture/lifecycles

**The design**, free apart from priced draws and asks, is `architecture/design`: EC, then each scene's concept,
lock, reading and plan, parent before child, then the film.

**Buy, the one-shot batch** (`score/dashboard/checkout`, its overlay; CONTEXT.md "batch"):

1. Each sync pass makes the basket again from the runner's plan on this checkout (free). Prepare
   (`score/stages/complete/prepare`, its overlay) reads every approved design's scene inventory into takes (sized by
   the plan, routed by noun: shell pieces, terrain, people, the rest models), prices every job once from measured
   per-unit numbers and writes each scene's hand-in (`{home}/design/props/`, `{home}/design/surfaces/`). The runner
   prices the same takes.
2. The Buy screen shows one estimate (likely and high), one ETA (only when every step is timed; else "at least"),
   what waits and why (a scene still in design, inputs missing, no locked film). Buy is disabled while the price is
   stale or the basket is older than the last design change.
3. His Buy is the one money yes. It writes the batch's stop: the high estimate plus 10%, on top of what is already spent
   and in flight. The checkout plans once and launches one runner command holding every bought node, so no two runs clash on a
   shared node. Buy buys what the runner plans now, nothing else.
4. The runner drives every scene's line side by side. A paid node runs once under its clearance; its failure is a
   batch gap, carried down the line and listed by the completion gate, never a retry (`architecture/failure`). A node
   that stops stops only its readers.
5. The run's outcome reaches the cockpit; the stop is written back at what was spent.

**One scene's line** (stage rows in `score/stages`, each with its overlay):

1. Materials: `finish-route-palette` coins the scene palette from the locked concept, `surface-library` makes its
   surfaces.
2. Models, one shared loop (`score/stages/shapes_first`): close-up, Pixal3D, the finish route (free views, one
   Gemini batch list, a free split by labels, paint and bake in one job, one recheck), the likeness gate, then each
   layer adapter's after-steps.
3. The base and layers (`architecture/layers`), the assembly, `neighbours`, `scene-tree`.
4. `complete`, then the library handover.

Environment rows: the ground (`terrain`), the people line, and `environment-film`, which films the locked script.

**Which scenes are build places** (`score/stages` `places`): every scene whose design is done (concept locked, read,
plan written or edited), parents before children. Parts of a scene's outside, merged scenes and removed scenes are
not; the scene a part belongs to builds it. A scene added in the app joins once designed.

**Accepts.** The runner accepts what passed and got no worse. The owner may reject an accepted output (it moves back to
the one before, every later node that read it goes stale, the runner never takes it again), accept a worse one with
his reason, waive one check for one key, or override with a yes for a run outside the runner. A benchmark grant is his
yes in a Claude Code session to benchmark batches of at most EUR 20 in all (`compute.grant_benchmark`, no expiry): it holds
its balance until spent, each run drawing its real spend, finished or failed (owner, 2026-10-22).

## architecture/layers

A scene is a stack of OpenUSD layers, each made by its own stage, checked and changed apart. Every layer is read off
the scene's design alone (owner, 2026-10-21: "the modules are not agnostic"): no record is written per scene, and no
branch names a scene or a world.

- **Which layers a scene has** (`score/stages/design_layers.py`): from its kept scene inventory's row kinds
  (`row_kinds.py`, `data/checks/row-kinds.json`, worked out from each row's noun, never a model call): people where a
  row acts, crops where one grows on a bed, effects where one emits, motion where one moves, settle and physics where
  one is loose; light and sound in every designed scene. The stage table (`stages.designed`) and the assembly's
  `layers` gate (`assembly.needed_layers`) read this one answer, so the gate never waits on a layer no row makes. No
  kept inventory: no layer rows, and the gate answers unknown.
- **The base layer** (`score/stages/earth_seed`, its overlay): the scene's stage from its own design. A room whose
  walls its plan holds is laid from its locked plan (`design_shell.py`: deck, walls with openings, roof).
- **The scene record** (`score/stages/scene_record`): what no model covers, written from the kept plan (outline, walls,
  openings, levels, stairs, roofs, holds), the row kinds, the library's lamp and the scene's sky inputs: the room shell
  where the base does not lay it, stairs, a lamp at each glowing item, views from each doorway and person spot, and
  the neighbours its doors lead to. Gated on `game-free`, `plan-matched` and `openings` (every doorway leads to a scene
  of the design, outside, sealed, a row or its holder).
- **The ground** (`score/stages/terrain`, one environment node): one ground for each body or plot of the physics, each
  top scene at its site and what its plan holds, on the body's true sphere raised by the plans' terrain spots (gates
  `spots` and `curve`); each scene standing on it takes its layer, and `ground-fit@<scene>` judges objects on level
  ground, none floating, no hole, doorways onto a floor, no view onto nothing.
- **Models**: every inventory row's objects from the shared loop, laid by the assembly.
- **Effects** (`score/stages/effects`): each object of an emitting row carries its kind's measured effects
  (`data/checks/effects.json`). **Motion** (`score/stages/motion/from_design.py`): each moving row by its kind's rule
  (a door swings only where somebody passes through it, a fan spins, a crane slews), speeds cited in
  `data/checks/motion.json`. **Settle and physics** (`score/stages/settling`, `score/stages/physics`): loose objects
  dropped where they stand under the gravity of the body under the scene's top site, written in UsdPhysics.
- **Light and sky** (`score/stages/light`): lamps from the inventory's glowing rows; the sky from the EC's physics
  overhead at the top scene's site and scene time (`sky.py`: each light, every other body at its true direction, size
  and phase, each backdrop), gated on `sky bodies`. A light under the horizon lights nothing.
- **Sound** (`score/stages/sound`): every source from the design (the bed, objects by row kind and move, people's
  voices), each made fresh from its brief as MOSS takes; a take under the CLAP floor is a batch gap.
- **People** (`score/stages/cast`, `people_rows.py`): each people row a look of the shared people line, a crowd one far
  look as one instancer, stood on the plan's person spots; `characters-layer` lays them.
- **Crops** (`score/stages/crops`): kinds and beds read off the design (a growing row standing on a bed).
- **The assembly** (`score/stages/assembly`): one stage per scene from every layer's accepted output (`assembly.READS`),
  gated on `layers`, placeholders, resting and `collision` (`tools/usd/colliders.py`: every wall, floor, stair and
  ground has a collider, every model its own; a body in the sky none).
- **Neighbours** (`neighbours.py`): the scenes a scene shows, each as its own accepted assembly; one no stage makes is a
  gap.
- **The scene tree** (`scene_tree.py`, `scene-tree@<scene>`, free): a parent scene holds its children in OpenUSD,
  `/<scene>/Scenes/<child>` referencing each child's own tree at the child's outline on the parent's plan; a child's
  tree is made before its parent's. Opening a top scene opens everything within it, each child still its own layer
  stack. Gated on `child scenes` (unknown with no plan read).

## architecture/cockpit

The creator cockpit (`score/dashboard`, its overlay has the detail) is the one page the creator runs SCORE from. It
reads the runner and the review tools and judges nothing itself. Words a person reads: scene (never place), physics
(never setting), lock (never pick); code, routes and stored ids keep the old words.

**Two sides.**

- **The store's machine, the conductor**: one always-on cloud machine of our own (until the move, his PC) holding the
  store, the runner, `score.review.web` (every draw, reading, plan writing and their spend), the previews, the sync
  pass (`python -m score.dashboard sync`) and the listener (`python -m score.dashboard listen`), as user `score`'s
  units, rendered by the same `install-sync` (without `--host`: the cockpit's `/healthz` names the commit it runs;
  `--no-pull`: its score-update timer follows that commit). It always calls out to the hosted side, never the other
  way, and names itself on every sync call.
- **His PC** keeps only a browser, the Claude Code sessions and the release (`score.dashboard release --host ...`,
  the coordinating session's job, from his checkout of the hosting repository).
- **One store's machine**: the hosted side records the machine of the first export that names one
  (`sync/one_store.py`). An export from another machine is shown, but none of its claims is granted, so it applies
  nothing, until the owner clicks 'This is the store's machine now' on the Machine card (owner only, asked twice).
  So during the move the PC and the conductor never both act as the store.
- **The Machine card** on Home and `/machine/`: its name, size and state, the last backup's age (red past 2 h), the
  last export's age (red past 15 min: the store's machine is not reaching the cockpit), its own month's bill (its
  own cloud project, so never in a batch's spend or stop), its health and log tails (`machine.json` in the export),
  and the owner's kill switch: Stop everything (every run stopped, parked machines deleted, paid work latched off)
  and Allow paid work again, each asked twice and applied by the listener through `score.conductor.kill`.
- **Hosted**: the same app as one ASGI process (`score/dashboard/site/asgi.py`: Django pages, FastAPI `/api`) reading
  the last pushed export (`state/exported.py`). It never imports the store, the stages, numpy or usd-core.
- **A hosted click** becomes a SyncRequest. The listener (`score-listen.service`, one long call held open) answers
  concept, environment and plan requests within about a second; the sync pass applies the rest. Both claim a request
  once and apply it through the same `pages/actions.py` function the local cockpit uses (`sync/applying.py`).

**The sync pass** (`score-sync.timer`, every 5 minutes, installed by `install-sync`; its token read by name from his
secret manager each pass): refuse a dirty or unpushed checkout, library sweep, gaps, kept plans, prepare's estimate,
the runner's price (a failed price stops the pass), the basket, push the export, apply waiting requests, report
launches. It pushes its export even when the checkout moved during the pass, so his locks and designs always arrive;
the price and estimate then name an older commit, show as stale, and Buy waits for the next pass. The export is
content-addressed and swapped whole once every file is up.

**The walk.**

- **Home** `/`: the environments, the month's spend, Stats, Library, Buy, the Machine card (`/machine/`).
- **Environment concept** `/environments/<world>/`: Style, Physics, Reference pictures and Scenes cards, Lock and
  Unlock (asked twice), a short set interview while unlocked; its Plan opens the environment plan.
- **Scenes** `/places/`: a tile per top scene, `?in=` steps into child scenes; Draw all with its price.
- **Design page** `/concept/<place>/` (`/plan/<place>/` opens at its plan): one screen of panels (the concept with its
  draws, the inventory, the top-down drawing, the plan with its section), each enlarging to fill the screen, beside
  one action rail (draw, lock, notes, child scenes, gaps, Make plan, Correct, each with its price). Its trail names
  every scene it sits within. The concept review and the plan review are this page (`architecture/design`).
- **Scene** `/place/<place>/`: its 3D view, its scene tree with gap dots, its gaps.
- **Film** `/film/`: the script editor and free preview, Lock and Unlock (`architecture/lifecycles`).
- **Buy** `/buy/`: what Buy buys now, its stop and ETA, what waits and why (`architecture/lifecycles`).
- **Money**: the month's cloud and model-call spend on every screen ("at least" while a line is unread); the books
  buttons (read the bills back, enter the model calls' month) show only while needed.
- The top bar's back and forward move up a layer and down again to the one last opened, not through browser history.

**Owner-only.** Accept, reject, advance, waivers, the books figure, the read-back and the kill switch are applied only
when the request's user is the machine's `SCORE_OWNER`; Buy answers 403 to anyone else. A draw, Discuss or plan writing is his yes at the
price shown, refused if the price moved. Agents are kept from these by a barrier, not a lock: the store refuses its
owner areas (accepts, rejects, waivers, spend yeses, clearances, stops, grants) to any process Claude Code started,
the runner's own automatic accept and clearance excepted; `python -m score.review` wants a terminal; and
`.claude/hooks/accept_guard.py` blocks the other routes. An agent's design edit is written only with his words and the
time attached (`score/review/plans.py` `kept_record`, `asked`; `workflow/loop`).

**Release.** `build/release`: the coordinating session moves the hosted pin once for a group of landed
changes.

## architecture/experimental

Built but not proven. Experimental means its code and overlay say so, and where it would run or cost money by default
it is off until a flag or a spec asks. Nothing here is a result; the paper's gaps name the same items. Each line says
what proves it.

- **The layers above** (scene record, ground, effects, motion, settle, physics trial, light passes, sound, people,
  crops, neighbours, scene tree): none has passed on a designed scene yet. Each is proven when a scene's line passes its gates and the owner has
  seen (or heard) the layer.
- **The people line** (`score/stages/people`, `tools/characters/maker`): Pixal3D bodies rigged with SOMA-X and Kimodo's
  clips. Proven when its looks pass every body gate on every clip and the owner picks them.
- **The animal route** (`tools/characters/animals/`, `make.py --experimental`). Proven when an animal moves in a scene.
- **The reach check** (`tools/usd/reach.py`): shown, not counted. Counted once the owner sets the scenery rule and it
  has caught a real unreachable row.
- **The render-and-compare** (`tools/usd/compare.py`) and **the style measure** (`tools/review/style.py`): candidate
  checks no gate reads. Proven when each ranks the owner's flagged models worst.
- **The films' past-fade ink rule** (`film_checks.py --ink-past-fade`): off by default.
- **The Kubernetes path** (`tools/cloud/k8s`, `SCORE_CLOUD=k8s`): opt-in, unused.
- **The images environment** (`score/stages/images`, `python -m score run images`): rebuilds and proves the job
  images; moss and characters-motion proven through it, the rest not yet.
- **Shapes first's later steps**: `rough-model` runs after a plan, but no plan is drawn to its rough model yet;
  `shell-split` applies only to a plan with a `split`, and today the plan's holds lay out the child scenes.

**Rows left with no work** after the old records were retired were removed on 2026-10-22: `concept-people`
(nothing read it), `demo-turntables` (its models were an old disk's takes), `demo-stills` (no definitions) and
`light-haze` (applied only where a kit lays a shafted lamp, which no design does), with their code. `surface-tiles`
went with them and came back the same day, read from the design (the locked plan's shell, `surface-library@<place>`,
`finish-route-palette@<place>`), so a designed place's shell gets its tiles; `earth-kit` and the ship kits went with the old kits on 2026-10-21. The
`tools/usd` writers (export, settle, snap, triage) and the review page's records read a kit only from the file given
(the design's `kit.json`), never `data/kit`.

## architecture/trust-boundaries

Placeholder: SCORE runs offline batches on one owner's machines, and secrets are read only by name (`Identifiers`).
The one boundary in use is the owner's: see `architecture/cockpit`, "Owner-only".

## architecture/failure

**Inside a batch.** A paid step runs once. Its failure is a batch gap (`score/stages/batch_gaps.py`): the take is
named with its failed check, left out of the rest of its scene's line and listed by the completion gate; it is never
retried, waited out or sent to a bigger card class, and fixing it is a new batch (ADR-0005). A free node that fails on
a transient fault (HTTP 5xx, a timeout, a dropped connection) runs again a few times. A node that does not end
accepted stops only the nodes that read it, directly or through another; the rest of its line runs. It leaves
`faults/<node>.txt` beside the store with the cause, every blocking check and its log's tail.

**A checkout that moves under a run.** Every `score run` drives from a frozen copy of the code (`score/graph/frozen.py`:
a git worktree under `$PROPS_HOME/frozen` at one commit, removed when the run ends and its parked machines are gone),
so agents' and the sync's pulls never reach a running batch. A run killed outright (SIGKILL, OOM) leaves its copy
behind until `git worktree remove`. A run cut off by a reboot comes back with `python -m score resume`.

**On the conductor** (`score/conductor`, the always-on cloud machine that holds the store):

- *A reboot, a resize or a maintenance.* `score resume` at boot starts every run cut off from its frozen copy, by
  the boot id and heartbeat rules above. A resize is a reboot the size timer asked for: it writes
  `conductor/resizing.json` before it asks, so a SIGTERM within 15 minutes leaves a run registered before the ask
  `running` (or `waiting-for-size`) even when systemd cannot yet say it is stopping; a run registered after it is
  stopped as the owner's. The grow waits for every live run to end; it
  is asked only for a run waiting for size, which only a run the owner started can be (an agent's run never grows the
  machine); the shrink comes after 30 idle minutes.
- *Memory.* Each detached run is its own scope in `score-runs.slice`, capped at the machine's memory less 6 GB, and a
  step's own capped scope stays inside it (`score/conductor/bin/systemd-run`), so an out-of-memory kill ends a run,
  never the listener or the sync. The drive's own memory hold (`graph.memory_room`) takes its floor per node from
  `SCORE_MIN_FREE_GB` there, when the env file sets it.
- *Kill switch.* The owner's cockpit button (`kill.stop_all`, refused in an agent's process): the free-only latch
  first (`conductor/free-only`, `SCORE_FREE_ONLY=1`, read by every `score` command; the sync pass and the listener mirror it into their
  own environment before each pass and each request, `client.free_only_followed`, and take it off once he clears it), then SIGTERM to every live run (each registers `stopped`, never resumed unasked), every waiting run stopped, every parked machine
  deleted through `park.release`. Only his second click clears the latch. The hard stop is `machine.py stop` from
  his PC.
- *Money.* The conductor bills in its own project (`score-conductor`); the stop line reads the batch project's bill
  alone, and every clearance and rent point (stop line, benchmark grant, reading, override) is refused if the two
  are ever the same project (`conductor.project_refusal`, from `machine.json` even without the size function).

**Losing `$PROPS_HOME`.** Git, the bucket (`score_lib/`, `runs/`, `inputs/`, `weights/`, `code/`, `kernels/`) and
score_lib's entries survive; the store, the spend ledgers, the runner's keys and the cockpit's records do not.
Recovery, in order:

1. Paid work stays shut until the month's spend is known. A missing ledger reads as EUR 0, so every paid point refuses
   (`ledger.books_refusal`) until `cloud/books.json` says the month is `known`: `score spend --read-back` reads the
   Scaleway bill and Google's (its billing export, `tools/props/cloud/google_bill.py`), or the owner enters the figure
   on the cockpit's money card. `batch.rent` refuses without the runner's ssh and self-delete keys; the owner makes
   them.
2. The store comes back by today's keys and gates, never by copying: `python -m score.store.restore <environment>
   --library <score_lib>` (its overlay) remakes free rows, leaves paid rows blocked and stands an old paid output
   again only when its key today equals the one it was made under, its checkout rebuilds to the same hash and today's
   gates pass. Downloading it is the owner's (`--reattach --max-gb N`).
3. Never put back by hand: records, judgements, evidence, accepts, rejects, waivers, clearances, spend yeses, the
   registry or stop lines.

**The store's backups** (`score/store/backup`, its overlay). On the store's machine (the conductor) restic writes an
encrypted, deduplicated snapshot of `$PROPS_HOME` every 30 minutes (`score-backup.timer`) into the repository
`SCORE_BACKUP_REPO` names: an Object Storage bucket in nl-ams (another region than the machine, Multi-AZ, versioning
on). It holds everything but what can be rebuilt (cache, store/cache, tmp, downloads, frozen, env, store-tests,
blender-mcp, partial writes); the cockpit's SQLite databases go in as consistent online-backup copies. Daily:
forget (48 last, 30 daily, 12 weekly; `pc-final` kept) and `restic check`, a 5% data read when none passed in 7 days.
So a lost disk now loses at most 30 minutes: restore the newest snapshot into an empty home (`python -m
score.store.backup restore --to <dir>` is the drill, compared to the snapshot's manifest when it carries one), then
step 1 above still holds (paid work shut until the books are known), and the restore of step 2 is needed only for
what the snapshot missed. The password is the secret `score-backup-restic-password`, read by name; lose it and the
repository is unreadable.

**The move of the store from the PC** (one time, the owner's; refused in an agent's process): stop the PC's
score-sync, score-listen and score-resume units; `python -m score.store.backup migrate --from-pc` (refused while one is
active or a run is alive) writes the PC home's manifest (the store's listing hash over `store/objects`, sha256 and
size of every file in design, cloud, runs, dashboard and work) and backs the home up tagged `pc-final` with the
manifest inside; on the conductor `migrate --onto-conductor` (refused into a home not empty) restores it, compares
the two manifests and stops on any difference, listing every file, then writes `$PROPS_HOME/machine.json` (name,
since, from, over the sizes record `machine.py up` piped to `SCORE_CONDUCTOR_RECORD`), the store's machine identity,
which makes it a conductor. The owner's one command for both sides is `python3 tools/cloud/conductor/machine.py move`
(from his PC after `up`, the PC's units stopped): the PC's backup, then over ssh the restore and `install-sync
--no-pull`; score-resume and score-health wait for machine.json there (`ConditionPathExists`), since both write into
the home the restore needs empty. The PC's home is then renamed read-only by the owner, and `migrate
--pc-test-home` puts back only work/ and design/, read-only, for the PC's test sandbox (env/ is bootstrap's).

## build/release

Nothing is deployed. A push to `main` publishes the source, the paper's PDF and its arXiv tree. There is no CI and no
GitHub Actions; every command runs locally.

- `make env`: the framework's Python (`.venv`, `uv sync`).
- `make tests`: every `tools/**/*_test.py` and `score/**/*_test.py` (plain scripts, or pytest when a file has `test_`
  functions and no `__main__`), `JOBS` files side by side (default 6), each under a 16 GB memory cap, in a sandbox home
  (`.claude/scripts/sandbox-home.py`: a fresh `PROPS_HOME` linking the real home's environment data, the real home
  read-only; the root `conftest.py` refuses any other home). A file over `TEST_SECONDS` (120) fails: the 2-minute
  budget is a hard rule (`workflow/module-standard`). `TESTS="..."` runs only the files named.
- `make check`: the gate. `.claude/scripts/gate-scope.py` prints `MODE none` for a change that touches only documents
  and working notes, else `full`; unknown paths, a change to the gate itself, `--full` or `GATE_FULL=1` run everything.
  Then `docs/adr/tools/check_index.py`.
- `make paper`: `paper/source/score.md` through pandoc into `paper/out/` (`score.tex`, `score.pdf`) and the arXiv tree
  `paper/arxiv/`, with `paper/out/stamp.json` hashing every input and output; `paper/build/test_paper_current.py`
  fails when they no longer match. `.githooks/pre-commit` runs it on any commit touching `paper/`.
- **The hosted cockpit** runs the dashboard at the commit its host repository pins (`SCORE_COMMIT` in the host's
  Dockerfile). After pushes that change `score/dashboard`, the coordinating session releases once for the group:
  `.venv/bin/python -m score.dashboard release --host <host repository> --dockerfile <its Dockerfile> --subject
  "<host commit subject>"`, then checks the live pages. Agents never release. The release stays on the owner's PC
  once the store's machine is the conductor. The image tells its commit at `/healthz` (`commit`, from `SCORE_COMMIT`
  set as ENV after the ARG; the host's Dockerfile needs `ENV SCORE_COMMIT=${SCORE_COMMIT}` in its final stage), the
  one pin the conductor's checkout follows, so one release moves both.

Render checks run Blender headless on a rented machine, never here; nothing here runs Godot.

## workflow/loop

**The loop.** Every conversation is a task: `grill` (orient, then interview until the plan and the domain model agree;
facts looked up, decisions asked), `to-prd` (the plan as one PRD issue, a sub-issue for work that is independently
grabbable or going to an agent), code, `close` (ship, record where the PRD stands, close only when its work is done).
A brain dump goes to `brain-dump`; an effort too big and fogged for one session goes to `wayfinder`.

**The mechanism stack.** One job each:

- **Skills** (`.claude/skills/<name>/SKILL.md`): methodology, by name or by description.
- **Overlays** (`<area>/CLAUDE.md`): one directory's rules, loaded when a file in it is touched.
- **Hooks** (`.claude/settings.json`): what must fire on a harness event. The grill protocol and worktree reaping on
  `SessionStart`; the soul rules on every prompt; `issue_guard`, `md_guard`, `wait_guard` and `accept_guard` on
  `PreToolUse`; `output_cap` on `PostToolUse`; `completion_guard` (no "done" claim for a scene its completion gate
  fails) and the memory commit on `Stop`. A hook that crashes lets the call through, so test a hook change by running
  its real command from `settings.json` on a sample event.
- **GitHub issues**: the durable backlog.

**Roles.** The overseer is the one coordinating session: it starts in this repository (so every agent gets its hooks,
tools and skills), plans each effort, splits it over parallel agents, briefs each (copying in every owner rule that
landed since the plan), checks what returns against the brief and the paper, and spends and approves nothing on an
agent's word. An agent has one role, one written brief and its own worktree; when the role is done, or the work would
change role, it commits, hands off (role, what is done with commits, what is half done, known faults, next steps,
paths) and closes. New work goes to a fresh agent, never a second job mid-run. A sub-agent does one narrow step and
returns data to its parent.

**Parallel agents** (owner, 2026-10-21):

- One agent per area at a time (the concept code, the plan code, the cockpit pages, the reading each have one owner);
  new work on an owned area waits or goes to that agent.
- An agent runs only the tests of the modules it touched, pushes and stops. It never re-runs whole suites after a
  rebase, never waits on the hosted rebuild or a sync, and never releases. A whole-suite run happens once on main after
  a group lands.
- Work that repeats per scene (readings, plan writings, fixes, checks) runs one process per scene side by side.
- Never wait in the foreground: anything that takes minutes runs in the background (root `CLAUDE.md`).

**Design edits by an agent** (owner, 2026-10-21). When the owner asks for one in chat, an agent may rename, merge, add
or remove child scenes, move and resize things on a plan, or edit an inventory row. Each is recorded as his edit with
his words quoted and the time, like a benchmark grant. Locks, accepts, rejects, waivers and spend stay his own clicks.

**The board.** One GitHub project (`.claude/scripts/setup-github.py --board`). Status is a column (`LowPriority`,
`Not started`, `In Progress`, `Review`, `Done`), set with `.claude/scripts/board-status.py <issue> "<column>"`; triage
state is a label (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`).

**Before you push.** The tests of what you touched and `python3 docs/adr/tools/check_index.py`. The repo works on
`main` only (ADR-0001), so a push is the ship. Before pushing an edit to anything a stage hashes, run `python -m score
moved`: it lists every paid row the diff would buy again; a commit that moves one on purpose names it in a
`Moved-rows: <node> ...: <reason>` trailer (`.githooks/pre-push-moved` refuses an unnamed move once the owner sets
`git config score.movedCheck true`).

**Commits.** Imperative and scoped, `module: description`; a subject that needs "and" is two commits.

**Memory.** `.claude/memory` is git-ignored (the repository is public), so it does not survive a wipe; anything
load-bearing goes into the bible, the glossary or an issue.

## workflow/module-standard

The house standard for a module, so a reader can predict the shape of code they have not seen.

- **One interface, one directory.** A module is a directory with an obvious way in; callers import the way in, never a
  file inside it. Files outside the interface are private (`_prefix` in Python).
- **Deep over shallow.** A module earns its place by hiding more than it exposes; one whose interface is nearly as
  complicated as its implementation is inlined into its caller. Vocabulary: the
  [`codebase-design`](../.claude/skills/codebase-design/SKILL.md) skill.
- **One function, one purpose.** A docstring that needs "and" between two concerns is two functions.
- **Every directory carries its overlay** (`CLAUDE.md`) once it has rules of its own.
- **Tests sit with the module**, one file a module, named for the invariant (`test_<invariant>`), driving the public
  interface. A test earns its place by catching a wrong answer:
  - It gives an input whose answer is known, worked out apart from the code (by hand, from the data, from an owner
    rule), or, where none exists, checks a property that must hold (nothing lost, totals add up, a write refused, a
    page that answers 200).
  - No shape tests (a file or page read as text for some words), except a wording check guarding an owner rule, which
    says which. No echo tests (an expectation computed by the code under test, or an assert of what was just set up).
  - Every test can fail: there is a break in the code that turns it red, else it goes.
- **A test file runs in under 2 minutes (hard rule, owner 2026-10-21).** A small fixture world built once per file,
  never the real store or home, no machine, no network, no whole-store walk, no sleeps. `make tests` fails a file at
  `TEST_SECONDS` (120).
- **Failures propagate.** A failure the caller can act on raises a typed error; one nothing can act on crashes loudly.
  Swallowing is neither.
- **A paid step's failure is a gap**, never a retry (`architecture/failure`). A retry is a mend only on a free step or
  on a read that buys nothing.

## workflow/bootstrap

1. Clone the repo and install the GitHub CLI so `gh auth status` is green (the issue and board skills need it).
2. `bash .claude/scripts/bootstrap.sh`: links Claude's memory folder to the git-ignored `.claude/memory`, runs
   `.claude/scripts/install-agent-tools.sh` (the pinned codebase-memory-mcp binary and Bun, each checked against its
   SHA-256; claude-mem's settings; the repo indexed), builds `.venv` from `uv.lock` and `PROPS_HOME`'s `env/` when
   missing, and reports anything else missing. Needs `node`, `python3`, `curl`, `uv` and the `claude` CLI. Safe to
   re-run.
3. `python3 .claude/scripts/setup-github.py --board` on a fresh repo only (labels and the board are GitHub-side).

**The runtime** lives under `PROPS_HOME` (default `~/.farm-factory-props`, kept so the ledger, keys and work carry
over): `cloud/` (the runner's ssh key, the self-delete key, the spend ledgers, `books.json`), `store/` (the store; fault reports,
logs and locks beside it), `work/` (`PROPS_WORK`: pictures and takes), `frozen/` (the runs' frozen copies),
`runs/` (the run registry), `env/` (the interpreter cloud runners call; no model runs in it). The creator's design is
kept under `{home}/design/` (locked concepts, scene inventories, plans, hand-ins, surface data). The cloud backend's
tools: for Scaleway, the `scw` CLI logged in to the project named by `SCORE_SCALEWAY_PROJECT` (by name, never an id).

The people line needs nothing installed here: every environment it runs is set up on the rented card
(`tools/props/cloud/characters_setup.sh`); it reads the secret `hf-read-token` (an account that accepted Meta's terms
for `meta-llama/Meta-Llama-3-8B-Instruct`, Kimodo's text encoder's base).

**The conductor** (`tools/cloud/conductor`, its overlay) is the store's machine as one Scaleway CPU machine of our
own instead of this PC: the owner runs `python3 tools/cloud/conductor/machine.py up` once from his terminal (it
costs money; `machine.py price` gives the month, `machine.py dry` checks it all for free). Cloud-init and `boot.sh`
make user `score` with linger, mount the data volume at `/home/score/.farm-factory-props` (so `PROPS_HOME` keeps its
default; the bare mountpoint is made immutable, so a boot without the volume never starts an empty store), install restic, uv, scw and the Google Cloud CLI pinned by SHA-256, clone this repository over https,
`uv sync`, and install the units in `tools/cloud/conductor/units/` (`score-resume`, `score-secrets`,
`score-update`, `score-health`, and the other areas' own). Its one credential on disk is
`/home/score/.config/scw/config.yaml` (mode 600, a scoped IAM key `up` pipes over ssh); every other secret is read by
name, the file-shaped ones to tmpfs only. Agents reach it only through the door (`agent_door.py`), never a shell.
`score-resume.service` is the one template for the PC too (`tools/cloud/conductor/units/`).

**What survives a wipe:** everything in git, the bucket, score_lib and, once the store lives on the conductor, the
restic backup repository (`architecture/failure`: `PROPS_HOME` to within 30 minutes). **What does not:** Claude's memory, `gh` auth,
local toolchains, `PROPS_HOME` (`architecture/failure`) and anything left uncommitted.

## Identifiers

Names and numbers a session cannot derive. Secrets live in a secret store; only their names are here.

| What | Value |
|---|---|
| Repository | `Babon-Innovations-b-v/score` |
| Project board | `9` (org project) |
| Environment ids | `world1` (environment 1), `images` (the job images). Stored ids and the runner's whole-environment grain `world` keep the old word: both are hashed into every node's key, and renaming them would make every accepted node again |
| Cloud | backend chosen by `SCORE_CLOUD` (default `scaleway`); Scaleway project named by `SCORE_SCALEWAY_PROJECT` (default `farm-factory`), machines tagged `farm-factory-batch`; Google's bill read from the billing export table named by `SCORE_GOOGLE_BILLING_TABLE`, else `$PROPS_HOME/cloud/google-billing-table` |
| Secrets | read by name with `secret_store.secret(name)`: the environment variable `SCORE_SECRET_<NAME>`, else the backend's store (Scaleway Secret Manager): `gemini-api-key`, `worldlabs-api-key`, `hf-read-token`, `freesound-api-key` (optional); read through `SCORE_SECRET_READER` (an executable outside the repo printing the secret its argument names): `score-cockpit-sync-token`, `score-backup-restic-password` (the store's backup repository, `score/store/backup`) |
| Store backups | restic repository named by `SCORE_BACKUP_REPO` (in the env file outside the repo); snapshots of the move tagged `pc-final`; the store's machine identity `$PROPS_HOME/machine.json` |
| Conductor | the store's machine in the cloud (`tools/cloud/conductor`): Scaleway project named by `SCORE_CONDUCTOR_PROJECT` (default `score-conductor`), zone fr-par-2, server, volumes, IP and security group named or tagged `score-conductor` (never `farm-factory-batch`), data volume `score-conductor-data`, backup bucket `SCORE_CONDUCTOR_BUCKET` (default `score-conductor-backup`, nl-ams), size function `score-conductor-size`, user `score` (uid 1100); its secrets by name in the project named `SCORE_SECRETS_PROJECT`: `score-conductor-size-token` (the size function's caller token), `score-conductor-size-key` (the size function's own Scaleway key, JSON), `score-lib-deploy-key` and `google-billing-reader` (written only to tmpfs, `/run/user/1100/score`) |
