# score/dashboard/

- **Look before you say done (owner, 2026-10-20).** A cockpit change is done only after its pages were opened in a real browser (headless Chromium; its libraries are under /tmp/cockpit-check, LD_LIBRARY_PATH) and the screenshots were looked at: a play button that plays, a surface that shows its surface, a model that shows its model. Tests that read JSON or HTML are not enough.
SCORE's dashboard: one ASGI app (`site/asgi.py`): Django renders the pages, sign-in and admin; FastAPI serves a typed
JSON API under `/api` and the file routes (`/files`, `/thumbs`, `/web`, `/healthz`); one sign-in for both. Commands in
`__main__.py` (`serve`, `owner`, `export`, `sync`, `check`, `web3d`: a place's 3D web copy for the viewer at `/view/<place>`,
`basket`: what a run on main would buy and its items' free details, `basket-item`: a department's item, its words and
questions, `basket-answers`: the owner's answers, `proposals/`). The environment shown: environment -> engine -> style
(a look in `data/definitions/place.json`) -> place with its OpenUSD index -> layer -> step (node),
grouped in `state/groups.py` from the stage table; no new framework level.

- **`state/`** where the pages read from. `local.py` reads the store beside it, read-only, through `index.py` (the
  small areas walked once with os.scandir, every folder store of that root answering `keys` from it, rebuilt when
  older than 60 s); `exported.py` reads a pushed state export; both give the pydantic models of `models.py`.
  A card a scene of the design (`local.scenes`: the places of the build, `stages.places`, the scenes of the tree as
  his kept plans lay out within.json, its shells and the kept environment concept's places, less the removed, merged
  and parts; a draw alone makes no scene: the old `ship`, drawn and then taken out, 2026-10-20), so a scene in design
  keeps its card and concept page before it is a place.
  A place's problems are its stopped steps, its accepted gaps and every standalone check's findings
  (`WORK/checks/<check>/<place>/findings.json`, `check_findings`, read while the outputs it judged stay accepted).
  Its gaps (CONTEXT.md "gap") are the gaps check's findings (`score/stages/complete/gaps`), listed apart
  (`gaps`, `gaps_total`). Their price is the runner's (`score price world1 --gaps`, its record
  `WORK/checks/gaps-price/<world>.json` read as `GapsPrice`): `gaps.py` only sums it, every paid node of any
  gap's chain once, each basis in its own bucket (measured runs, per unit × counted, per unit × forecast, the
  guesses with the file and line each is written on, never a price; the nodes with neither are unknown); no price
  is made and no unit counted here. A place never checked is named, never read as nothing to pay. A record made on
  another commit, on code not committed or on other per-unit prices than this checkout's (`priced_on`,
  `code_moved`), or older than any accept or reject or any gaps check shows no number (`price_stale`, the rule of
  `current_findings`); the gaps, their total and their price are read again as soon as a gaps findings or the
  price record is written (`gaps_written`, a stat each per request), never after the 60 s index. `per_place` gives
  each place's row (gaps by kind, worst first: lost input, route step, missing, gate; its chains' paid nodes once,
  `own` the ones no other place's chain has); `plan_of` the runner's milestones (`score/stages/complete/gaps/
  milestones.py`) in its order with the remake's total, the set budgets apart (never in a figure); the time is the
  record's `eta` (the runner's `gaps/schedule.py`), shown only when every step has measured minutes. No plan is
  made or reordered here. Places and steps are said by their titles (`groups.place_title`, `groups.label`), never
  their keys. `present.prim_tree` gives a place's gaps layer as a tree (no accepted assembly gives a whole scene
  tree yet), `present.gap_marks` the boxes the viewer outlines (`/view/<place>?gaps=1&gap=<id>`, gaps alone over
  a grid while no web copy exists).
  `files.py` serves only a sha a page listed, with cached JPEG thumbnails; `costs.py` only says minutes in words (the
  cockpit prices nothing: every price is the runner's, ADR-0006); `accepted_gaps.py` gives each accepted gap its step and a
  picture of what it names (local source only), `plain.py` says each problem in one plain sentence (the step
  pages' and the viewer's; the five screens show numbers).
- **The screens' data (#42): one small JSON object a screen, numbers, states, names and links, no sentences**
  (`state/screens.py`, routes in `api/routes.py`, signed in, GET):
  - `/api/screens/environment`: `money` {month, cloud, models (None: not read, never the call ledger alone), total,
    whole, stop (the last batch's: its high plus 10%; None before one), against_stop (spent since the first stop line
    plus in flight), in_flight, refused}; `remake` {likely, high (only the places whose design is approved,
    `screens.approved_parts`, owner 2026-10-20: "design decides inventory", so a price on the old inventories says
    nothing; None before one is: prepare's prop route there, each stage's price shared by its takes, takes waiting on
    lost inputs counted, plus the gaps price of every paid step off it there), approved, in_design, route {likely, high, unpriced, takes, bought,
    made, library (from the library: only models made under today's route or locked, prepare's rule; an older match
    is remade and counted bought), predicted_gaps, blocked}, rest {likely, high, priced, unpriced}, unpriced, eta {likely_minutes,
    high_minutes (None unless every step is timed; all None until every design is approved: the runner times the
    whole remake only), at_least_minutes, untimed}, made_at, stale [why], estimate (`screens.estimate`, owner
    2026-10-21: prepare's whole figure from the places' current scene inventory readings, before any design is
    approved; None before prepare read them) {likely, high (None while stale), unpriced [stage], places (read),
    waiting (on inventory, no euros), eta, stale}}; the Environment's remake tile and the Buy screen's After design
    show it (`c/estimate.html`: EUR likely to high, the ETA or its floor, "N of M places", "+ K unpriced") while no
    design is approved, never buyable; `batch` carries it too; `gaps`
    {kind: count}; `places` [{place, title, status, picture (its concept's thumbnail link; None when its concept is
    lost, never a render instead: owner, 2026-10-20), picture_from (concept, None), design (`screens.design_state`:
    draw, review, read, or None once its scene inventory counts), progress {made, needed} (its line's steps accepted;
    None, like gaps, while its inventory does not count), complete, gaps, worst (lost, route, missing, gate), takes (prepare's, by status),
    within (the outside place or shell holding it, None for an outside one)}], `shells` {shell: short name} (the
    outside shells that are no place of their own). The hierarchy is `data/places/within.json` (shapes first: each
    place's `within` and the data it was read from; `parts`, a part of a place's own outside that is no place to the creator, the Street's square and launch view, sits within that place), read on the store's machine into the WorldState
    (`within`, `shells`), so the export carries it; a place it does not name is an outside place. The concepts are
    each place's or shell's concept review draws (its picked draw, else its newest; the old index of the filed plans'
    pictures, `data/places/concepts.json`, was retired on 2026-10-21), read into the WorldState's `concepts`
    {node: FileRef}; the export carries their thumbnails before every other picture.
  - `/api/screens/place/<place>`: picture, `web3d` (`/web/<place>/<place>.glb`, else the library place entry's GLB at
    `/library-files/files/<sha>`) and `web3d_from`, `view`, progress, complete, gaps, worst, takes, `steps` [{node,
    stage, label, state, paid, thumb}], `items` (its gaps, the scene tree's leaves by `prim` path) [{id, prim, kind,
    row, node, paid, work, picture}], `prices` {node: {likely, high, priced, unpriced}} (each filling node's chain
    once; None while the gaps price is stale), price_stale.
  - `/api/screens/buy`: `items` [{id, title, place, places, layers, likely, high, guessed, nodes, unmeasured,
    blocked, choice (buy, later, None; a choice on another version is None)}], `chosen`, `total` (the chosen items,
    each node once) and `basket` (every item) {likely, high, guessed, nodes, unmeasured}, `eta` {likely_minutes,
    high_minutes, untimed}, `stop` (what the yes would write: the high with the guesses, plus 10%), `money`; `design`
    (`screens.design`, CONTEXT.md "design", prepare's `design.py` record carried in the Remake) {places [{place,
    design {concept (missing, drawn, picked: a lock), plan (remake, made, approved), output, hint} (None: prepare names it
    not), game (its gaps' `complete/game` gate: its layout still from the source game)}], approved}; `batch`
    (`screens.batch(world, items, made_at)`, the Buy screen's one batch, owner 2026-10-20: "what Buy buys must be exactly the
    total shown") {now {likely, high, guessed, guesses, no_price {layer: steps}, stop, steps, places, eta {likely_minutes,
    high_minutes, untimed, at_least_minutes, at_least_high_minutes (the timed steps' span: a floor), untimed_kinds {kind of step: steps}}} (the basket items `screens.now_items` gives: not the Benchmarks, none waiting on a missing
    input, only at places whose design is approved, none before one is, a line no place owns (the people's) with the
    approved places whose line holds it: the item's `for`, each buy's in `score plan`, `rebuy.held_for`; exactly what the Buy yes buys, priced as its
    checkout records it: `pricing.totals` of those nodes, high the cleared high with the guesses, stop that plus 10%,
    flow.write_line's; `no_price` the bought steps with neither price nor guess, outside the figure), `made_at` the
    basket's, `refused` [why] (`screens.buy_refusals`: the prices stale, or the basket older than prepare's record or the
    gaps price, or of unknown age; the Buy shows disabled with the first why), `approved`, `in_design`, waiting {steps, why [reason]} (what this Buy does not buy, counted with no euros, owner 2026-10-24: one figure: prepare's prop route take by take,
    a take's stage at a place the Buy buys counted there; every other
    paid step of the gaps price), total (the sum of the lines, equal to now: measured, estimated and guessed
    parts of its high, `no_price` the kinds of step with none), gets [{place, made, after, needed, complete,
    layers}] (each place's steps before and after Buy now), layers [{layer (`screens.LAYERS`), make, library,
    waiting, why {reason: count} (plain words: `local.WAITS` for a take's lost input, an earlier step first, inputs
    missing, not in the last plan), models, steps (its units: the route's takes, steps at places),
    makes (its widest route stage's takes plus its steps at places), likely, high, guessed, no_price {kind: count}}], eta, stale, plants {rows, objects, crops, beds, places} (every plant of the designs, `WorldState.plants` from `design_layers.plants_of`; None when none grows: the Buy's Plants line, owner 2026-10-24)}.
  - `/api/screens/stats`: money, `bill_days` [{day, cloud, models}] (the bills as read each day on the store's
    machine), `days` (the ledgers' own counts, low), `prices` {measured, steps, by_basis, stale}, `remake_layers`,
    gaps, `places` {complete, total}.
  - `/api/screens/library`: `kinds` [{kind, count, draft, locked, withdrawn, pictured, scored}], `total`; a branch's
    children and an item stay `/api/library/list` and `/api/library/entry`, pictures `/library-files/thumbs/<sha>.jpg`.
  The library's bytes come from its blob folder, else the library cache the sync pass fills (`$PROPS_HOME/cache/
  library/score_lib/`); `SCORE_LIB_ROOT` defaults to the score_lib checkout beside score's.
- **`auth/`** `proxy.py` the outermost guard (only a trusted proxy may send `Remote-User`/`Remote-Email`; an
  underscore spelling is refused from every peer), `backends.py` the allow-list, `owner.py` the local owner account
  (a terminal, a 12+ character password, loopback bind only without a proxy).
- **`pages/`** the Django app (label `dashboard`): views, templates, static CSS/JS, its own SQLite records (change
  requests, basket, plans, launches, sync requests; never a mirror of the store). `actions.py` does what a request
  asks, one function each.
- **The cockpit app (#42): five screens under one top nav** (`templates/pages/base.html`), under the home: **Home** `/`
  (`pages/environment.py` `home`, `home.html`, owner 2026-10-21): the environments (environment 1 only today), each opening
  its environment concept page, and the hub of what spans them (the month's spent, Stats, Library, Buy); **Environment
  concept** `/environments/<world>/` (see below), its Places button opening **Environment** `/places/`
  (`environment.html`: the month spent (the lines read, "at least" while one is not, each line as hover text; no
  stop shown), the remake's euros and hours for the approved designs, the Buy page's own `batch.now` (`cockpit.remake`, `views.batch_of`; owner 2026-10-24: one figure on every page; its ETA at least its timed steps while one is untimed) and how many places are in design (only that
  count before one is approved), a Review and buy
  button, a tile per outside place or shell (shapes first, `cockpit.tiles`: one holding places sums their progress
  and gaps, shows what sits directly inside that holds places itself over its concept ("Hangar, 8 rooms": a shell's or an inside place's places are its rooms) and "+N"
  for the rest, and opens to them at `/places/?in=<place or shell>`, headed by that place or shell itself (`cockpit.head`: its concept, ring, gaps, Review or
  Draw and, for a place, Open to its Place screen; CONTEXT.md "place": never an "Outside" card beside its inside
  places, owner 2026-10-20) over its inside places' tiles only, with a trail back up; the leaves open the Place screen), **Place** `/place/<place>/` (`place.html`: its concept as the header, the 3D view,
  the scene tree with gap dots, a side panel), **Buy** `/buy/` (`buy.html`, owner 2026-10-20, CONTEXT.md "design":
  design first: how many places' designs are approved and a row a place, its concept and plan state, "game layout"
  where its layout still takes the source game's numbers, its old lock as hover text, linking to the place, where
  the design is made (its concept review, outside any batch: no concept is bought here), and a Plan link to its plan
  review once its design is approved (the lock is the approval, owner 2026-10-21: no Approve); then After design: how many places await design while none is
  approved (no euros, no layers), else Buy now: what Buy buys (`batch.now`: EUR likely to high, the guessed euros and
  steps, the stop, the ETA or, while a step is untimed, "ETA ≥" its timed steps' span with the untimed kinds of step named, its unpriced layers outside the figure, "+ N steps wait" (what this Buy does not buy, why as hover text, no euros: the Waits box went, owner 2026-10-24), the basket's
  made_at), and a line a layer, how many it makes and its euros (what Buy buys of it), no step's own name and no dropdown; its Buy only
  once a design is approved, buying only those places, disabled with why while `batch.refused` holds any; the owner's books buttons only while needed: the read-back while paid work is refused, the model calls'
  month figure while it is not read, its button named by their cost line's label; no Basket link, no stop control:
  the Buy yes sets the batch's stop), **Stats** `/stats/`
  (`stats.html`: numbers only, no controls, three groups: money this month (cloud, AI calls, total, no stop; the
  remake's spend so far once a batch's stop line is written; a bar a day on one labelled scale, `cockpit.spend_by_day`:
  the bills' growth over a day read that day and the day before, else the ledgers' count when above 0 as a paler
  bar, else a gap, never 0, and the euros on no day), progress (places complete, the gaps by kind in plain words,
  each opening the Environment at `/places/?kind=<kind>`: only the tiles holding that kind, counting it) and prices (paid
  steps measured, the remake's measured share)) and **Library** `/library/` (`pages/library.py`: every kind of
  `state/library.KINDS` with its count, a branch's children only when it opens (a withdrawn entry in none), `/api/library/children?node=&page=`,
  `PAGE` at a time with a "more" branch; an item's page `/library/<kind>/<id>/<version>/` is the item on its own
  (owner, 2026-10-20: "experiencing the item in isolation"), live and free in its kind's viewer (CONTEXT.md "item
  preview": never a paid render, owner 2026-10-22; an old record's `clip` is ignored) (`library.view_of`,
  `viewer_of`): a model, kit or character's web copy turned in `static/pages/item3d.js` (its light copy, then its
  whole copy where this cockpit holds it, a model's close-up, the picture it was made from, beside it (its `closeup`
  file, owner 2026-10-20); a kit as its place lays it (its own set where it lays the kit again in places of its
  own), an inside one cut open, beside its kinds of piece with counts, each opening one piece alone; a copy's clips
  on a time scrubber), a surface
  on a lit sphere and tile with palette colour, shine, wear and seed sliders (a preview's variants, not its recipe's
  bake), an effect played from its settings with a scrubber, a sky (kind `light`, shown as Skies: a sky is no light,
  owner 2026-10-20) as its dome looked around in from inside or a planet's backdrop as its globe, a place's lamps (the
  Lamps shelf: a `light.<place>` layer, `library.shelf_of`; its `lamps.json`) at their spots over a neutral test
  scene, a sound's takes as waveforms played side by side (`static/pages/takes.js`), a place or layer's place viewer
  in a frame, an algorithm's own work on one real example (the kind `algorithm` is the Physics shelf, physics setups only, CONTEXT.md "physics setup"; the one other code entry, the surface recipes, sits on Surfaces in a "Made by code" folder, `library.CODE_SHELF`, its page saying made by code; a layer's placement, layout, terrain, sky, light, sound and film code is the framework's own steps, withdrawn from the library, owner 2026-10-21; `static/pages/demo.js`: its steps played on a plan, a side
  chart or a raised relief, a path flown as a camera, a slider showing its output at another setting; the demo made
  on the store's machine by `score/stages/library/demos.py`, read from the library cache's `demos.json`, hosted
  the export's `library/demos.json`), else a plain diagram of what it reads and makes, with why there is no example
  as hover text; else its picture. Every entry is named in everyday words (`state/names.py`: no asides, brackets or
  technical terms; the library's own title is the name's hover text, ids unchanged). Beside it at most four numbers
  of its kind (`numbers_of`, a demo's own; hover text each; size and clips filled once its copy loads) and its score
  only where its kind's score means something (`library.SCORE_MEANS`, what it measures and its parts as hover text;
  never an algorithm's, which measures its code snapshot); its versions, 3D link and the owner's lock, withdraw and refine kept small. No file list, ids or blobs on the
  page (they stay in `/api/library/entry`). What a viewer plays is the entry's `facts` (`state/library.py`
  `kind_facts`, `viewer_facts`: read from the record, and from a surface's material, an effect's settings or a
  light's OpenUSD in the blob folder or library cache, which the sync pass fills: `score.stages.library.pictures`
  `viewed`); hosted, the same from the export's `library/entries.json` and `library/palette.json`, the light copies,
  prints and first takes in `library/files/`, never a whole copy). Place draws its
  tree's top level only; each deeper branch loads as it opens from `/place/<place>/branch/?path=<names below the root>` (`views.
  place_branch`, `cockpit.branch_rows`), and an item's panel holds its picture, gap kind, its chain's price
  (`cockpit.chain_words`: "unknown" while a paid step of it has no measured price) and, for the owner, one action on
  the step that fills it (`cockpit.gap_action`: accept its waiting output, reject one failing a check, waive the
  failed check of its accepted one, as his JSON request to `/api/decisions` or `/api/waivers`); opening it frames
  the gap in the 3D view (a `{gap}` message to the viewer frame). Buy shows the one batch (CONTEXT.md "batch"): the remake
  (`screens.batch`), a layer with a step that has neither a measured price nor a guess the runner reserves marked "+"
  (a guess shows only as "*"); its Buy button posts `/buy/yes/`
  {key, batch: now} (`basket.buy_yes`, `batch_items`: exactly the approved places' items, `screens.now_items`, through
  the same checkout as the basket's, hosted queued; what waits is in the figure, not buyable); `{batch: benchmarks}` still buys the Benchmarks item, with no button on this screen; no choice
  an item is asked, so the nav's count is only the steps queued by hand and the refines; no last-batch card (owner, 2026-10-24: "this needs to be deleted"): the monitor opens on the Buy's yes and Home links to it. **Batch** `/buy/run/` (the run monitor,
  `pages/run_monitor.py`, `run_monitor.html`, owner 2026-10-24: "make the monitor page for after buy ... easy to
  understand and scan"): the Buy's yes opens it (`data-go` on its yes form) and Home links to it while a batch lives
  (`run_monitor.live_batch`). The newest checkout's batch (`checkout/watched.newest`: the record, its launch polled,
  every row any run of it planned: a relaunch goes on where it was, a row done once its accept is newer than the checkout) read from its files by `state/batch_run.py` (the run's detached log: heartbeats, each
  finished row's line, the pool it opened, its result line; a row's own log written since the start: running; each
  done row's batch gaps; `$PROPS_HOME/cloud/pools/<run>/`: plan, cards, closed, collector.log), live locally
  (`LocalSource.batch_run`), hosted from the export's `batch-run.json`, or the newer one the listener sent each minute (`ExportedSource.batch_run`), with its age; a
  hosted Buy not answered yet shows as sent. One screen: state chip (starting, running, waiting for machines,
  stopped, finished), started and elapsed from the checkout's first run (a relaunch goes on its clock), the ETA left
  from the checkout's runner minutes ("at least" while a bought step is untimed), rows done of total, the owner's Stop
  everything (asked twice) while it lives; spent (the checkout's: the last heartbeat of each of its runs, each its
  rows', its warm pool's, its cards idle now and its model calls, `score/__main__.py` `spent_by_run`) on one bar
  against likely, high and stop; a row a scene, parent before child
  (`within`), its rows done, what runs now, a chip, a done scene linking to its 3D copy or scene page; the warm pool's
  cards and processor machines as squares (busy, idle, to come; waiting for stock; once released, "N still renting"
  for the machines its pools hold parked, `cloud/parked/`); problems (a failed row in one
  plain sentence with the rows it holds back, a row's batch gaps, the batch stopped), newest first. Times in the
  viewer's clock; it reads itself again every 20 s locally, 60 s hosted, while the batch lives. The numbers come
  from `pages/cockpit.py` (`month_money`, `remake`, `tiles`, `branch_rows`, `gaps_by_kind`, `places_complete`,
  `measured_prices`, `spend_by_day`, `day_chart`), each None where the runner gives none, shown as a grey "unknown", never 0; the
  views are `views.environment`, `stats`, `buy`, `place_page` over `views.overview_of`. The components, each an
  include of `templates/pages/c/` with these arguments (every one ends without a newline, so it sits inline):
  - `dot.html` `tone` (done, idle, bad, review, gap-lost, gap-route, gap-missing, gap-gate: the `.tone-*`
    classes of dash.css), `tip`.
  - `ring.html` `done`, `total`, `tip`: a progress ring with done/total in it.
  - `number.html` `label`, `value` (None: grey "unknown" with `unknown_tip`), `unit` ("EUR": to the cent), `of` a
    denominator, `bar` a percent under it, `tone` a dot beside the label, `tip`. Pass every argument (None where
    unused): an include inherits its caller's names.
  - `tile.html` `href`, `picture` (the concept; none: "concept missing"), `busy`, `refused`, `holds` [{name, picture, count, unit}],
    `more`, `name` (the place's short name, place.json `short`; its look's long words are
    `tip`), `made`, `needed`, `made_tip` ("made 0 of 30"), `gaps` (None: "?", not checked) with a gap icon in its
    `tone` and "781 gaps" as hover text, `tone`, `tip`.
  - `tree.html` `nodes` [{label, count, tone, tip, href, picture (a thumbnail link), open, panel, children,
    children_url}]: `children` drawn now,
    `children_url` fetched (GET, JSON [node] of the same fields) only when its branch first opens (dash.js); a
    failed load turns its dot red and goes to the console. `panel` {title, state, tone, price, picture, gap,
    action, action_label, body, reason} opens the side panel on a click or Enter. Its open branches and the page's
    and tree box's scroll are kept in the page's own history step (`history.state`, replaced), so back, forward and
    a reload open them again.
  - `panel.html` `id` (default "panel"): one a page, filled by dash.js from the opener's data-title, data-state,
    data-tone, data-price ("unknown" grey), data-picture, data-action (a link, or with data-body the JSON its button
    posts; data-reason asks why), data-action-label, and data-gap sent to `iframe[data-frames]`; Escape or its
    close button shuts it. An open panel is a history step of its own (`#item=<its gap, else its title>`, pushed;
    another item while one is open replaces it; shutting it steps back), so back shuts it and a reload shows it. Any `form[data-yes]` (data-url, data-body, data-reload) posts the same way: a green or
    red dot, the answer as hover text, never on the page.
  Hover text is the native `title` attribute: every component takes `tip`; an explanation goes there, never on
  the page.
- **No number from an inventory that does not count** (CONTEXT.md "scene inventory", owner 2026-10-20: "inventory
  can't exist" before the lock): a place's scene inventory counts only while it was read from its locked draw
  (its reading, else its design's kept inventory `{home}/design/inventory/<place>.json`, `concept_pick.sha256` equal to the lock's sha: `screens.inventory_current`, the
  store's `WorldState.inventories` read by `score/review/concepts.inventory_read`; prepare's `design.py` the same rule,
  its `inventory` state), and its numbers only once its gaps findings are not older than the lock (`screens.counted`,
  `local.inventory_reads` `checked`: earlier ones were read from an older inventory). Until then its tile and head
  show its design steps done as pips and a number (`pages/c/steps.html`, `screens.design_steps`: concept locked,
  inventory read, plan made; owner 2026-10-21, numbers not prose), its design state in words (`cockpit.DESIGN_WORDS`:
  to draw, in review, inventory to read, plan to make, gaps to check, in design for a tile none of whose places count) as their
  hover text, in place of the ring and gaps, a Plan button once it has a plan, its tile opens its concept page and
  its head has no Open (owner, 2026-10-20), its Place screen shows only its concept, that state and a link to its
  concept page (no scene tree, no 3D, no gaps), and its gaps are in no total (`views.overview_of` rows,
  `local.gaps_total`: only `counted_places`). An unlock makes it out of date at once (no
  write: the rule is read against the lock standing). The concept page shows a locked place's inventory file as made
  (its rows) or to read (and whether the one there is older). A lock starts its scene inventory reading on its own
  (`score/review/reading.py`, `web.reading_started`, no yes asked: owner, 2026-10-21), kept in the store
  (`inventory-readings/`, `WorldState.inventory_readings` and `inventory_spend`); the concept page shows the reading
  of the locked draw beside its picture (`concepts.reading_view`: rows numbered, each instance found boxed on the
  picture; the gaps one line a row, its name and what is unclear in plain words, a click lighting its boxes; a
  "skipped N, merged M" note listing what the readers' agreement left out as hover text, and "show skipped" drawing
  those faint and dashed, each saying why on hover; a row and its boxes light together on hover), and
  every reading's euros in sum show on the Environment's top bar under spent and on Stats. Prepare's remake figure
  reads the readings (its `estimate`); the gaps check reads the design's kept inventories (`{home}/design/inventory/`).
- **The environment concept** (CONTEXT.md "environment concept", owner 2026-10-21; `pages/environment.py`,
  `environment_concept.html`, `static/pages/environment.js`): `/environments/<world>/` shows four cards (owner
  2026-10-21: "this page is confusing"): Style (its line), Setting (CONTEXT.md "setting", `pages/setting_picture.py`,
  owner 2026-10-21: "this won't tell anyone anything"; never a raw table: a picture, then a short plain card a thing:
  its bodies drawn round the one they orbit, the orbits round it to scale with one another, sizes and moons' orbits
  enlarged to read and said so under it, each site a dot on its body; a plot from above at its metres with each far
  light's path over its sky; a card a body, light, backdrop or ground with one line in plain words ("Moon: orbits
  Earth every 27 days ...") and the sites on it, every raw number only as hover text; while unlocked its values in a
  wrapping form, a row's values it shows no field for riding in its `data-keep`, a field left empty taking the
  reference table's again; no horizontal scroll), Reference pictures (each with its
  place and what it is for) and Places (what each may hold inside); plain text while locked, fields only while
  unlocked, explanations as hover text. The set interview shows only while unlocked, beside them: the fixed questions
  (`QUESTIONS`, the same as `score/review/environment_concept.QUESTIONS`) one at a time, "Question N of 5" with the
  one before and after as links (`?q=<topic>`, `steps_around`, so back and forward step through them; no tabs), his answers and each answer's proposed fields with its price and a Take. Send is his
  spend yes for that one model call at the price it shows (`WorldState.environment_ask_euros`, the measured
  ask; `web.environment_ask`, refused when it moved), Save, Take, Lock and Unlock each a new version (`web.environment_saved`),
  Add a reference picture into the private bucket's references/ and his local copy, never this repository
  (`web.environment_reference`). Locked it is for looking at; Unlock opens a second, in-page ask (no `confirm()`:
  the viewer has none) that every place's concept made from it goes out of date, and does exactly that (the store's
  rule: every draw and lock records the version it was made under). Every click is a SyncRequest of
  `applying.ENVIRONMENT_KINDS`, applied here at once locally (an ask or a picture in a thread) and by the listener when
  hosted; hosted, his versions and pictures since the export show at once (`environment.shown`, `pictures`). Environment
  1's is today's data shown locked until he keeps a version (`WorldState.environment_concept`, read by
  `local.environment_concept`; its reference pictures in the export beside the concepts).
- **The concept review** (CONTEXT.md "concept review", owner 2026-10-20; `pages/concepts.py`, `concept.html`,
  `static/pages/concept.js`): each Environment card whose concept is not locked carries a Review (Draw while it has
  none) button to `/concept/<place or shell>/`: the shown draw with areas marked by dragging, a note each and one for
  the whole, one draw button with its price per click (Draw concept while it has none; then, with no mark and
  no note, Draw fresh: a new first draw from the place's current first-draw wording, no base; with any, Redraw with
  notes: the prompt model corrects the shown draw's prompt by them, then one draw repaints it, two calls at
  `WorldState.concept_redraw_euros`, the corrected prompt then the place's own wording; the owner, 2026-10-20; the
  locked concepts the draw is drawn on show beside it (`ConceptWording.context`), marked too, their boxes P1, P2, ...; Discuss beside it, CONTEXT.md "discussion", owner 2026-10-21: his note as a question with
  his marks, one prompt-model call at `WorldState.concept_discuss_euros` (SyncRequest `concept-discuss`, `web.concept_discuss`, local in a thread, hosted the listener), its answer under
  the note (`concepts.thread_of`: the store's `concept_discussions`, hosted with those answered since the export; faint once a draw follows), an open one making the button Redraw with notes,
  which sends it to the prompt rewrite; every call's measured cost sums as `discuss_spend` on the top bar and Stats) (`WorldState.concept_draw_euros`: the measured Nano Banana Pro
  picture at the standard tier, `score/review/concepts.draw_euros`), the place's draws, Lock (locks it: the card loses
  the button) and Unlock. A click is the owner's request (SyncRequest `concept-draw`, `concept-pick`), applied on the
  store's machine through `actions.concept_draw` / `concept_pick` and `score.review.web` (his yes for that one call
  at the price shown, refused when the price moved, then the call as its own process inside it; the store refuses
  both in an agent's process): local at once (a draw in a thread), hosted by the listener. The store keeps the draws
  and locks (`score/review/concepts.py`), each draw copied to the private bucket as it is made
  (`concept-draws/<sha>`), and a lock or unlock is handed to score_lib (`score-lib concept`: the locked draw locked as
  `concept/<place>`, withdrawn on an unlock), whose entry the Library shows in its place's folder on the Places shelf
  (`shelf_of`); the lock's answer says what the library did. A place's card shows its locked draw, else its newest unless every draw is from an older wording (then none: out of date). The page asks `/concept/<place>/state/` until the draw is answered. Hosted, the
  answered draw (its record as the request's detail, its pictures in `SCORE_HOME/request-files`, served by
  `ExportedSource` beside the export's) and a lock since the export show at once; the cards follow at the next export.
  A place's page names the places listed inside it that its draw is asked to hold (`asked_to_hold`). Under the
  picture the page shows, editable, word for word what Draw fresh or Draw concept sends (`WorldState.concept_wordings`,
  `ConceptWording`: the wording `score/review/concepts.py` `generated` makes by its one rule for every place, or the
  creator's own; the owner, 2026-10-20), the pictures sent with it in order (`pictures`: a crop of the locked concept of
  the place it sits within to what holds it, then the locked concept of each place beside it that it opens into, then its references), why it waits
  (`refused`: Draw disabled with it as hover text; `unpickable`: Lock the same; both refused on the store's machine
  by `concepts.step_refusal`, the design steps' one rule), a part of another place's outside (within.json `parts`, the
  Launch of the Square) no card, no Draw and no Draw all entry, and, folded, what Redraw with notes sends (its notes as
  placeholders). A first draw sent with the box edited sends exactly that text (his note after it) and the store's
  machine keeps it as the place's own wording (`concepts/<place>/wordings/`, his process only), used by every later
  first draw and Draw all and by the stale rule (`current_draw`), so his edit puts the old draw out of date on the
  card; "back to generated" (SyncRequest `concept-wording`, `/concept/<place>/generated/`) drops it. Hosted, his
  wording since the export shows at once (`wording_of`). No batch: the batch rules start once the design is approved. The
  Environment's top bar carries **Draw all N, EUR X** for the owner (owner, 2026-10-20; `concepts.draw_all`, hidden
  at N 0): every place or shell with no draw from its current wording yet whose first draw can be made now (`WorldState.concept_undrawn`, read
  on the store's machine by `score/review/concepts.undrawn`, layer by layer: one within a place not yet locked, or
  whose reference is not on the PC, waits, counted in the hover) and none on its way, X = N times the per-draw price. Its click (`/concepts/draw-all/`,
  refused when the list or the total moved) is his one spend yes for exactly those first draws: N `concept-draw`
  requests at the per-draw price, each with the Draw all's count and total (`all`), each written as its own override
  yes saying so and refused on the store's machine once the price moved or its place has a draw from its current wording (`web.concept_draw`
  `first`); local in a thread each, hosted the listener answers a held call's requests side by side. The cards show a
  draw as it lands (`concepts.newest_pictures`, hosted with those answered since the export) and the screen reads
  itself again every 3 s while any draw is on its way (dash.js `reread`: `[data-reread][data-drawing]` swapped in
  place, no reload). While one is, the Draw all button is a disabled "Drawing N..." (N the open draws; the click
  turns it so at once, `data-busy`), a card whose draw, or a place within it whose draw, is on its way carries a
  spinner over its picture and one whose newest draw was refused a red "refused" with the reason as hover text
  (`concepts.card_state`); the concept review shows the same spinner over its picture while its draw is on its way.
- **The plan review** (CONTEXT.md "plan review", owner 2026-10-21; `pages/plans.py`, `plan.html`,
  `static/pages/plan.js`, the store side `score/review/plans.py`): `/plan/<place>/`, reached from its card's and
  head's Plan button and its concept page once its scene inventory counts. The plan, made from the lock with no
  Approve (the lock is the approval), drawn as an architect's plan in an SVG laid out like the picture the prompt
  model is sent (`static/pages/plan.js`: hatched walls with their thickness, doors with their swing, windows, stairs
  with the way up, level marks, terrain contours and spot heights, roofs dashed overhead, each item in its own shape,
  dimension lines, north arrow, scale bar, and a section A-A under it at the same scale; every colour a token in
  `dash.css`), beside the locked concept: hover a thing for its details; he drags and resizes items, zones and inside
  places (one dropped on a building stands in it: no row dropdown, owner 2026-10-21), moves doors along their walls and
  standing spots (a person spot, a people row's, drawn as a small person mark, never a box); the inside places by name only (rename, remove, add place); the drop rule (owner 2026-10-21,
  CONTEXT.md "shared room", "thing in a room"): a box dropped fully inside a room is a thing in it (`things` on its
  hold, listed under it), a room dropped on or resized over another is one shared room (`name` on the kept hold),
  anywhere else a box is a child scene, each with an undo; its gaps said plainly where they are,
  a click lighting each on the drawing (no counts line, owner 2026-10-21); marks on the plan or
  the concept with a note each. While its plan is the rough one (`how` derived) Make plan (`plan-write`,
  `WorldState.plan_write_euros`) writes it (score/review/plan_writing.py: on its own after a reading under the
  standing allowance, `plan_automatic`; with that off his click is the spend yes); every writing's euros sum on the
  Environment's top bar and Stats beside the readings' (`plan_spend`). Keep (SyncRequest `plan-edit`) keeps his plan as his own and where the plan stage
  reads it; Correct with notes (`plan-revise`) is one prompt-model call at `WorldState.plan_revise_euros` (the measured
  answer), his click its spend yes (`web.plan_revise`, an override yes like a concept draw). The concept page names
  inside places up front (`plan-named`, `static/pages/inside.js`). Hosted, a plan kept since the export shows at once
  (`plans.review_of`); the listener answers all four (`applying.PLAN_KINDS`). What sits inside what is within.json
  with each holder's inside places as his newest kept plan lays them out (`plans.overlaid`, the one rule: the
  hierarchy here and `concepts.tree(store)` on the store's side); an inside place only his plan names (no line yet)
  gets a design-only tile opening its concept page (`cockpit.designed`, `local.design_nodes`). A place his kept plans no longer lay out, or one within.json's `merged` names (merged into another), is `removed` (`plans.removed`): no card anywhere, never an outside place, hosted too. A draw made on another room than the plan above gives the place now (moved, resized, merged: `plans.moved_draws`, each first draw recording its `room`) is out of date, so Draw all offers it again; a place whose lock, else every draw, is one is in `WorldState.plan_changed` (owner 2026-10-21): its card shows no picture, "plan changed" and Redraw, its design state is `draw`, and its design page flags it. The sync pass writes every place's plan
  where the plan stage reads it and makes the plan row again, detached, for those that changed (`client.plans_kept`,
  before prepare).
- **The design page is a cockpit** (owner, 2026-10-21: "all open by default but the page designed a bit more as an
  actual cockpit"; `concept.html`, `static/pages/design.js`): the concept review, the inventory and the plan review
  are one page, `/concept/<place>/` (`/plan/<place>/` leads to `#plan-part`), all open: a grid of panels on the full
  width (concept with its draws strip, inventory, the top-down drawing, plan with its section; a long plan takes the
  whole width) beside one action rail (draw, lock or unlock, notes, inside places, the plan's places, gaps, notes and
  Make plan, Keep, Correct, each with its price). On a screen at least 1100 x 600 px it is one screen, an instrument
  panel with no page scroll (owner, 2026-10-21: "doesnt function as a dashboard/cockpit yet"): concept and top-down
  drawing over the inventory, the plan a column as wide as its drawing at the height it gets (`--plan-aspect`, a long
  plan a row across the bottom) with its section under it at a small height, the rail full height with the gaps list
  taking what is left; narrower or lower the panels flow down the page, one column below 860 px. Inside places show by
  their names (place.json `short`, `plan_names`), their ids only in the plan and the words Correct sends; Correct with
  no note and no mark sends his edits (this visit's, else his kept edit against the plan made without him,
  `score/review/plans.note_of`, refused before any spend when there are none); a refusal older than the plan shown is
  not shown. Every
  panel's enlarge button fills the screen with it in place (marks, hover and drags the same), a history step of its
  own (`#focus=<panel>`, pushed; back, Escape or the button shut it; a reload shows it). The plan and section are
  zoom views: fitted at their aspect, the wheel zooms at the pointer (Ctrl+wheel outside an enlarged panel), Space+drag
  or the middle button pans (a plain drag on the section), "fit" puts them back. Once locked, the plan's P marks are
  drawn on the concept panel's picture. The inventory shows one row at a time: the row hovered in the list, else the
  row held, else the smallest box under the pointer (they stack); a click holds it, clicking again at one spot steps
  through the boxes stacked there; every other box dims ("one at a time" hides them), the kind buttons keep the
  objects, structure (`local.inventory_readings` `structural`, `reading.structural`) or terrain rows, "skipped" draws
  what the agreement left out; each row's number sits in a corner of its first box, moved where it would cover another.
- **The environment's plan** (CONTEXT.md "environment plan", owner 2026-10-21; `pages/environment_plan.py`,
  `environment_plan.html`, `static/pages/environment_plan.js`, the store side `score/review/environment_plan.py`):
  `/environments/<world>/plan/`, the Plan button beside Places on the environment concept page, laid out as the design
  cockpit (design.js: panels, enlarge, zoom; owner 2026-10-23: "these blockouts and plans look shit"): a panel a
  ground of the setting, the one with most sites the big one, its map in true metres (`environment_plan.js`): each
  top scene's own plan drawn at its site by plan.js's own sheet (`window.planSheet`, read-only; the plan its plan page
  shows, `plans.review_of`), largest first so a site standing on another shows, every name over them linked to its
  plan, the true metres between sites, a north arrow and a scale bar. The rail: Write and Keep, the gaps (an overlap of
  two sites the creator placed himself among them; any other two are parted on settle), and a row a site: its size (its plan's, never a field), where it stands (the setting's, set
  on the concept page), its scene time (a field for the owner) with the Sun's height and every other body above its
  horizon as hover text (worked out from the setting, never typed). Keep (SyncRequest `env-plan-edit`) keeps his times
  as his own; Write (`env-plan-write`) has the plan writer write it again under the owner's standing allowance; both
  `applying.PLAN_KINDS`, so the listener answers them hosted.
- **`api/`** the routes and `deps.py` (the Django session read for FastAPI, CSRF on every write, owner-only routes).
- **`launch/`** the compute backend interface (`backend.py`: plan, spend, price, launch, poll, ledgered; chosen by
  `SCORE_COMPUTE_BACKEND=module:Class`), the shipped `localrun.py` (the `score` CLI), and `guard.py` (groups, the plan priced by the
  runner through `checkout/pricing.totals`, every launch refusal in words).
- **`checkout/`** the owner's one checkout of the basket items he bought, also under `/api/checkout`: each item's
  plan checked against what was priced, the environment's stop line at the basket's high plus 10% (the batch's own
  stop, `flow.BUFFER`; no stop is set any other way, CONTEXT.md "batch"), one batch through the backend. Its own overlay has the rules.
- **`previews/`** a picture for each step whose output has none of its own, drawn from its files on the store's
  machine, kept per output, never imported by a hosted process.
- **`sync/`** hosted mode: `building.py` the export, `endpoints.py` the hosted side (token only), `client.py` and
  `applying.py` the store side's pass. The store's machine always calls out. The export goes content-addressed: only
  the files the hosted side lacks, thumbnails first, one 2 MiB gzip chunk a request, then a commit swaps it in whole, never while a record (a .json) is still to come; the upload's time counts from the end of the build.
  Each pass first runs the library sweep (`score.stages.library.sweep`, the environment against its library), so its
  problems are in the export by construction; a failed sweep is said in the pass's words and the pass goes on.
  The gaps (`score.stages.complete.gaps`, in a process of its own: it reads OpenUSD) are written right after it,
  the same way, then prepare's remake figure (`score.stages.complete.prepare`, `remake_prepared`), its benchmarks as
  the basket's one Benchmarks item (`proposals/benchmarks.py`, `basket_benchmarks`) and the library's
  place pictures into the library cache (`score.stages.library.pictures`, `library_pictures`), each a line. A pass syncs nothing, and says why, from a checkout with tracked changes or a commit origin's main
  does not hold (`tree_refusal`), or when the runner's price after the gaps (`score price <environment> --gaps`,
  `runner_price`) fails, so no stale plan or price is ever sent. Once the price stands, the pass makes the basket
  again from the runner's plan on this checkout (`basket_made`, `proposals/make.py` plan only, free; its index says
  when, on which commit and in which checkout), then fails a checkout left launching by a process that is gone and
  takes an ended batch's stop line back (`checkouts_tidied`, `checkout/flow.tidied`); a pass whose checkout moved to another commit
  while it ran still pushes its export, so his locks and designs reach the cockpit, with the price shown stale and Buy waiting for the next pass, and still applies requests (a Buy is left waiting then: `buy_waits`). The owner's money buttons and his waiver
  (`applying.OWNER_FIGURES`: the books' figure, the read-back, a waiver) are applied
  like his decisions: only when the request's user is this machine's `SCORE_OWNER`, through the same
  `pages/actions.py` function as the local cockpit, which refuses in an agent's process. Never tell the owner to
  type a command: an owner-only action is a button (#39). Each request is claimed once (`/requests/<id>/claim`), so
  the pass and the listener never both apply it. The listener (`listen.py`, `python -m score.dashboard listen`, the
  owner's systemd service `score-listen.service` beside the timer, restarted hourly onto the pulled code) holds one
  call open (`/requests?kind=...&wait=25`) and answers the concept review's requests within a second of the click,
  sending a draw's pictures back (`/request-files/`) before its report. It answers a hosted Buy (`checkout`) the same
  way (owner, 2026-10-24: "can we make that delay less for the following runs"), unless `client.buy_waits` says its
  price needs a fresh pass (a pass holding `pricing_now`, `tree_refusal`, `figures_moved`: the price, prepare's figure
  or the basket on another commit, the basket older than prepare): then it notes why on the request
  (`/requests/<id>/note`), skips it (`&skip=`) and the pass applies it, under the same check; a launch is followed by
  either (`tracked_changed`, locked). While a batch lives it sends `batch-run.json` every `PUSH_SECONDS` (60) and once
  as it ends (`PUT /batch-run`, kept in `request-files/`; `ExportedSource.batch_run` takes the newer read_at). The owner's timer (`timer.py`, `install-sync`, the
  deploy templates) reads the token by name from his secret manager each pass, inline, through the reader his env
  file names; it installs only once the cockpit runs this checkout's dashboard. `release.py` (`release`) moves the
  hosting repository's pinned `SCORE_COMMIT` to a pushed commit, from a worktree of its own, in the host's commit
  style; never run by a test against a real host (`tests/release_test.py` makes its repositories). The release stays
  the coordinating session's job on the owner's PC, even once the store's machine is the conductor (the always-on
  cloud machine of our own; the PC then runs only a browser, the sessions and the release). `/api/sync/pin` (token
  only) reports the `commit` the image was built at (`SCORE_COMMIT`, the Dockerfile's ARG set as ENV; the hosting
  repository's Dockerfile must set it the same way), the one pin the conductor's score-update timer follows;
  `/healthz` says it too, but babon's Caddy answers `/healthz` with its own body, so nothing outside reads it there.
  `install-sync` renders the same templates for user `score` on the conductor: without `--host` it checks the commit
  `/api/sync/pin` reports, and `--no-pull` puts the conductor's update (`tools/cloud/conductor/update.py`, the system
  python) in place of the sync unit's `git pull` (ExecStartPre), so every pass starts on the cockpit's pin.
- **The store's machine** (`state/machine.py`, `sync/one_store.py`, `pages/machine.py`): the export carries
  `machine.json` right after the state: the machine's own record (`$PROPS_HOME/machine.json`, else its host name),
  `score.conductor.health.read()` and `score.conductor.logs.tails(TAIL_LINES)` cut to `TAIL_BYTES` (the largest
  tail's oldest lines first; the tails left out over the export's cap), each import guarded: off a conductor the
  health is `{missing: "not on a conductor"}`. The manifest names the machine and every sync call carries its name
  (`X-Score-Machine`). The hosted side records the machine of the first export naming one (`store-machine.json`);
  another machine's export is shown but each of its claims is refused (423), so it applies nothing, until the owner's
  'This is the store's machine now' (`/api/machine/confirm`, owner only, CSRF, `sure` from the page's second ask, only
  for a machine an export came from); no request kind and no sync token moves the record. The Machine card
  on Home (`machine_card.html`) and `/machine/` (its health in numbers, the units, the tails as folds) show the name,
  size and state, the backup's age (red past `BACKUP_LATE_MINUTES`), the export's age (hosted, red past
  `EXPORT_LATE_MINUTES`: "the store's machine is not reaching the cockpit") and the conductor's own month's bill
  (`health.bill`, its own project: never a batch's spend or stop). The kill switch (`applying.MACHINE_KINDS`, owner
  only, asked twice, `/api/machine/stop` and `/api/machine/allow-paid`): Stop everything is a SyncRequest
  `stop-everything` the listener applies at once through `score.conductor.kill.stop_all(asked_by, words)`, its report
  as the answer the card counts; Allow paid work again (`allow-paid`, shown while `health.free_only`) through
  `kill.allow_paid(asked_by, words)`; both refused for anyone else, in an agent's process and off a conductor.
- **`proposals/`** the basket's details (its own overlay): what a run on main would buy (the runner's plan), grouped
  into items by place and by what changes (a department's declared item may span places), each place's free after
  assembled over the store's accepted outputs as a 3D web copy, what changes read from the two stages, each paid
  step's inputs, in `$SCORE_DASHBOARD_HOME/proposals/`; the export carries them through `proposals/exporting.py`, the
  API at `/api/basket` and `/basket-file/<place>/`. The owner reads them on the **Basket** (`/basket/`,
  `pages/basket.py`): a tile an item under its place, each opening (`/basket/item/<id>/`) to the place in 3D with
  what it changes outlined and a before and after switch (`/view/<place>?item=<id>`), the list of what changes, what
  it is made from, the price and his questions with our recommended answers; his buy or not now (`BasketChoice`) and
  his answers (`BasketAnswer`; kept in `answers.json` on the store's machine, hosted through a SyncRequest of kind
  `answer`). The page's lower part keeps the steps he queued by hand.
- **`films/`** the film script (its own overlay): the top bar's Film, the design step after the scenes and before
  Buy (`/film/`, the environment's default film; his Lock its approval, which the environment-film row reads and Buy
  waits for, "film script not locked" on the Buy screen), the FILM pages' editor, free three.js preview on the web copies and
  films, and render items priced from measured frames; scripts saved in `$SCORE_DASHBOARD_HOME/films/`, starters in
  `data/films/`; `film-preview <film>` renders its free preview end to end (screen takes, setting animation, scale
  zoom), which the FILM page plays and the export carries.
- **`deploy/`** templates only, every host and name a `<placeholder>`; `Dockerfile` and `docker-compose.yml` beside.

Rules:

- **Read only, except the owner's own decisions.** The dashboard writes its SQLite and `$SCORE_DASHBOARD_HOME`
  (thumbs, inbox, plans, status snapshots, exports, `bill-days.json`: the month's bills as read each day). The store and the books are written only
  through `score.review.web` (`decide`, `waived`, `stop`, `google_month`, `concept_draw`, `concept_pick`), which the store, the guard and the books
  refuse in a process an agent started. Never call `Runner.drive`, `rebuy.buys`,
  `compute.clearance` or `rejudged_accepted` in the web process: plans, spend and freshness are subprocesses of the
  `score` command.
- **Never launch from a test or an agent against the real runner.** Tests use `tests/fixture.py:FakeBackend` (one
  exception: `launch_test`'s start-line test runs the real `score run --detach` on a run with nothing to make, in the
  test's own `PROPS_HOME`, so `localrun.STARTED` and the runner's line cannot drift apart); a launch
  needs the owner signed in, room under the stop his last checkout's yes wrote and every refusal of
  `guard.refusals` clear; there is no stop he sets (no month's stop, no stop button: owner, 2026-10-20); the dashboard
  never stops a run itself: the owner's kill switch (Stop everything) hands it to `score.conductor.kill`.
- **No module on sys.path, no stage imports this package.** Import dotted from `score.dashboard`; never a bare
  `views`, `models`, `urls`, `settings`, `apps` or `admin` (they would be hashed into stage keys). Do not edit
  `tools/review/*` (the viewer is served as a file) or add web tokens to `design/tokens/tokens.json`.
- **One dark theme on design tokens** (owner, 2026-10-20, #25; built like babon's design system, none of its brand):
  the colours are `design/tokens/colours.css`, type, space and radii `scale.css`, the font Poppins
  `design/fonts/poppins/` (OFL), all served at `/static/design/` and linked by `pages/tokens.html` before
  `dash.css`, whose short names only alias them; the 3D views read them through `static/pages/tokens.js`. No template
  or static file writes a colour, every token named is defined, text holds WCAG AA (`tests/theme_test.py`). A hosted
  build may replace `colours.css` whole with its own colours on the same names (babon's does).
- **No provider here.** Nothing in this package imports `tools.*` or `score.adapters` or names a provider
  (`tests/no_provider_test.py`). Hosted mode never imports `score.stages`, `score.store`, numpy or usd-core
  (`tests/hosted_light_test.py`).
- **Numbers, not prose** (owner, 2026-10-20, #42): the runner gives numbers and states; a screen shows numbers,
  colours, pictures, progress and buttons, at most one short line of text a block, explanations only as hover text,
  never a raw error or traceback (a red state and a short label; the detail to the log). Mark data (a number, a
  name, a state) with `data-v`: `tests/pages_test.py` (`prose`, `WORD_BUDGET`) fails a screen with more than 40
  words of anything else. Node ids only inside a `details class="ids"` fold. Money is the total against the one stop
  line, never per-piece prices alone; a provider is named only by its cost line's label (`no_provider_test.py`).
- Tests: `make tests TESTS="score/dashboard/tests/*_test.py score/review/web_test.py"` (temp `PROPS_HOME` and
  dashboard home, `tests/conftest.py`). `tests/real_store_smoke.py` runs by hand against the real store, read-only.
  `tests/viewer_look.py` runs by hand too, free: the 3D viewer in headless Chromium from each film shot's and light
  look's camera beside that picture (difference, structure, brightness, pink and black, its `THRESHOLDS`); run it on
  new web copies, or `--hosted <export>` on the export the hosted site serves, before calling the viewer fixed.
  The Place screen's click test (`pages_test`, `tests/screens_click.mjs`) drives the same Chromium; it is skipped
  where that Chromium cannot load its libraries (`ldd`; point `LD_LIBRARY_PATH` at them to run it).
