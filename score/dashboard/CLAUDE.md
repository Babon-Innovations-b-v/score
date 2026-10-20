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
    whole remake only), at_least_minutes, untimed}, made_at, stale [why]}; `gaps`
    {kind: count}; `places` [{place, title, status, picture (its concept's thumbnail link; None when its concept is
    lost, never a render instead: owner, 2026-10-20), picture_from (concept, None), progress {made, needed}
    (its line's steps accepted), complete, gaps, worst (lost, route, missing, gate), takes (prepare's, by status),
    within (the outside place or shell holding it, None for an outside one)}], `shells` {shell: short name} (the
    outside shells that are no place of their own). The hierarchy is `data/places/within.json` (shapes first: each
    place's `within` and the data it was read from; `parts`, a part of a place's own outside that is no place to the creator, the Street's square and launch view, sits within that place), read on the store's machine into the WorldState
    (`within`, `shells`), so the export carries it; a place it does not name is an outside place. The concepts are
    `data/places/concepts.json` (each place's or shell's concept picture: its sha256 in the store's blobs and where
    its bytes were found, hash-checked; the lost ones named with why), read into the WorldState's `concepts`
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
    design {concept (missing, drawn, picked), plan (remake, made, approved), output, hint} (None: prepare names it
    not), game (its gaps' `complete/game` gate: its layout still from the source game)}], approved}; `batch`
    (`screens.batch(world, items)`, the Buy screen's one batch, owner 2026-10-20: "what Buy buys must be exactly the
    total shown") {now {likely, high (the guesses the runner reserves in it), guessed, guesses, stop (high plus 10%),
    steps, places, eta} (the basket items `screens.now_items` gives: not the Benchmarks, none waiting on a missing
    input, only at places whose design is approved, none before one is; exactly what the Buy yes buys), waiting {likely, high, why [reason]} (prepare's prop route take by take,
    a take's stage at a place the Buy buys counted there, the rest with its share of the stage's price; every other
    paid step of the gaps price), total (now plus waiting, the sum of the lines: measured, estimated and guessed
    parts of its high, `no_price` the kinds of step with none), gets [{place, made, after, needed, complete,
    layers}] (each place's steps before and after Buy now), layers [{layer (`screens.LAYERS`), make, library,
    waiting, why {reason: count} (plain words: `local.WAITS` for a take's lost input, an earlier step first, inputs
    missing, predicted to fail, not in the last plan), models, steps (its units: the route's takes, steps at places),
    makes (its widest route stage's takes plus its steps at places), likely, high, guessed, no_price {kind: count}}], eta, stale}.
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
- **The cockpit app (#42): five screens under one top nav** (`templates/pages/base.html`): **Environment** `/`
  (`environment.html`: the month spent (the lines read, "at least" while one is not, each line as hover text; no
  stop shown), the remake's euros and hours for the approved designs and how many places are in design (only that
  count before one is approved), a Review and buy
  button, a tile per outside place or shell (shapes first, `cockpit.tiles`: one holding places sums their progress
  and gaps, shows what sits directly inside that holds places itself over its concept ("Ship, 8 rooms") and "+N"
  for the rest, and opens to them at `/?in=<place or shell>`, a place's own tile first, named Outside (no tile holds a card of its own name), with a
  trail back up; the leaves open the Place screen), **Place** `/place/<place>/` (`place.html`: its concept as the header, the 3D view,
  the scene tree with gap dots, a side panel), **Buy** `/buy/` (`buy.html`, owner 2026-10-20, CONTEXT.md "design":
  design first: how many places' designs are approved and a row a place, its concept and plan state, "game layout"
  where its layout still takes the source game's numbers, its old pick as hover text, linking to the place, where
  the design is made (its concept review, outside any batch: no concept is bought here), and the owner's Approve
  once its plan is made (his accept of `plan@<place>` through `/api/decisions`); then After design: how many places await design while none is
  approved (no euros, no layers), else the approved places' figure and a line a layer, how many it makes and its euros, no step's own name and no dropdown; its Buy only
  once a design is approved, buying only those places; the owner's books buttons only while needed: the read-back while paid work is refused, the model calls'
  month figure while it is not read, its button named by their cost line's label; no Basket link, no stop control:
  the Buy yes sets the batch's stop), **Stats** `/stats/`
  (`stats.html`: numbers only, no controls, three groups: money this month (cloud, AI calls, total, no stop; the
  remake's spend so far once a batch's stop line is written; a bar a day on one labelled scale, `cockpit.spend_by_day`:
  the bills' growth over a day read that day and the day before, else the ledgers' count when above 0 as a paler
  bar, else a gap, never 0, and the euros on no day), progress (places complete, the gaps by kind in plain words,
  each opening the Environment at `/?kind=<kind>`: only the tiles holding that kind, counting it) and prices (paid
  steps measured, the remake's measured share)) and **Library** `/library/` (`pages/library.py`: every kind of
  `state/library.KINDS` with its count, a branch's children only when it opens (a withdrawn entry in none), `/api/library/children?node=&page=`,
  `PAGE` at a time with a "more" branch; an item's page `/library/<kind>/<id>/<version>/` is the item on its own
  (owner, 2026-10-20: "experiencing the item in isolation"), its preview clip first where the cockpit holds one
  (CONTEXT.md "preview clip": rendered as the films render, so what it plays is what ships; owner, 2026-10-20), its
  kind's viewer the second tab (`?tab=3d`), else its kind's viewer first (`library.view_of`,
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
  in a frame, an algorithm's own work on one real example (the kind `algorithm` is the Physics shelf, physics setups only, CONTEXT.md "physics setup"; code that makes something else sits on the shelf of what it makes in a "Made by code" folder, `library.CODE_SHELF`, its page saying made by code, Films holding the camera paths; `static/pages/demo.js`: its steps played on a plan, a side
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
  an item is asked, so the nav's count is only the steps queued by hand and the refines; the last batch's stop (its
  high plus 10%, `basket.last_batch`) shows after it. The numbers come
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
  - `tile.html` `href`, `picture` (the concept; none: "concept missing"), `holds` [{name, picture, count, unit}],
    `more`, `name` (the place's short name, place.json `short`; its look's long words are
    `tip`), `made`, `needed`, `made_tip` ("made 0 of 30"), `gaps` (None: "?", not checked) with a gap icon in its
    `tone` and "781 gaps" as hover text, `tone`, `tip`.
  - `tree.html` `nodes` [{label, count, tone, tip, href, picture (a thumbnail link), open, panel, children,
    children_url}]: `children` drawn now,
    `children_url` fetched (GET, JSON [node] of the same fields) only when its branch first opens (dash.js); a
    failed load turns its dot red and goes to the console. `panel` {title, state, tone, price, picture, gap,
    action, action_label, body, reason} opens the side panel on a click or Enter.
  - `panel.html` `id` (default "panel"): one a page, filled by dash.js from the opener's data-title, data-state,
    data-tone, data-price ("unknown" grey), data-picture, data-action (a link, or with data-body the JSON its button
    posts; data-reason asks why), data-action-label, and data-gap sent to `iframe[data-frames]`; Escape or its
    close button shuts it. Any `form[data-yes]` (data-url, data-body, data-reload) posts the same way: a green or
    red dot, the answer as hover text, never on the page.
  Hover text is the native `title` attribute: every component takes `tip`; an explanation goes there, never on
  the page.
- **The concept review** (CONTEXT.md "concept review", owner 2026-10-20; `pages/concepts.py`, `concept.html`,
  `static/pages/concept.js`): each Environment card whose concept is not locked carries a Review (Draw while it has
  none) button to `/concept/<place or shell>/`: the shown draw with areas marked by dragging, a note each and one for
  the whole, one draw button with its price per click (Draw concept while it has none; then, with no mark and
  no note, Draw fresh: a new first draw from the place's current first-draw wording, no base; with any, Redraw with
  notes: the shown draw repainted as they say; the owner, 2026-10-20) (`WorldState.concept_draw_euros`: the measured Nano Banana Pro
  picture at the standard tier, `score/review/concepts.draw_euros`), the place's draws, Pick (locks it: the card loses
  the button) and Unlock. A click is the owner's request (SyncRequest `concept-draw`, `concept-pick`), applied on the
  store's machine through `actions.concept_draw` / `concept_pick` and `score.review.web` (his yes for that one call
  at the price shown, refused when the price moved, then the call as its own process inside it; the store refuses
  both in an agent's process): local at once (a draw in a thread), hosted by the listener. The store keeps the draws
  and picks (`score/review/concepts.py`), each draw copied to the private bucket as it is made
  (`concept-draws/<sha>`), and a pick or unlock is handed to score_lib (`score-lib concept`: the picked draw locked as
  `concept/<place>`, withdrawn on an unlock), whose entry the Library shows in its place's folder on the Places shelf
  (`shelf_of`); the pick's answer says what the library did. A place's card shows its picked draw, else its newest, else
  `data/places/concepts.json`'s. The page asks `/concept/<place>/state/` until the draw is answered. Hosted, the
  answered draw (its record as the request's detail, its pictures in `SCORE_HOME/request-files`, served by
  `ExportedSource` beside the export's) and a pick since the export show at once; the cards follow at the next export.
  An outside place's or shell's page names the inside places its draw is asked to hold (`asked_to_hold`; the wording
  is `score/review/concepts.py` `shell_wording`: each at its plan's size, joined as laid out, recognisable from
  outside, and its outside's parts). No batch: the batch rules start once the design is approved.
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
  the files the hosted side lacks, thumbnails first, one 2 MiB gzip chunk a request, then a commit swaps it in whole.
  Each pass first runs the library sweep (`score.stages.library.sweep`, the environment against its library), so its
  problems are in the export by construction; a failed sweep is said in the pass's words and the pass goes on.
  The gaps (`score.stages.complete.gaps`, in a process of its own: it reads OpenUSD) are written right after it,
  the same way, then prepare's remake figure (`score.stages.complete.prepare`, `remake_prepared`), its benchmarks as
  the basket's one Benchmarks item (`proposals/benchmarks.py`, `basket_benchmarks`) and the library's
  place pictures into the library cache (`score.stages.library.pictures`, `library_pictures`), each a line. A pass syncs nothing, and says why, from a checkout with tracked changes or a commit origin's main
  does not hold (`tree_refusal`), or when the runner's price after the gaps (`score price <environment> --gaps`,
  `runner_price`) fails, so no stale plan or price is ever sent; a pass whose checkout moved to another commit
  while it ran pushes no export (prepare's and the price's records would read stale) and still applies requests. The owner's money buttons and his waiver
  (`applying.OWNER_FIGURES`: the books' figure, the read-back, a waiver) are applied
  like his decisions: only when the request's user is this machine's `SCORE_OWNER`, through the same
  `pages/actions.py` function as the local cockpit, which refuses in an agent's process. Never tell the owner to
  type a command: an owner-only action is a button (#39). Each request is claimed once (`/requests/<id>/claim`), so
  the pass and the listener never both apply it. The listener (`listen.py`, `python -m score.dashboard listen`, the
  owner's systemd service `score-listen.service` beside the timer, restarted hourly onto the pulled code) holds one
  call open (`/requests?kind=...&wait=25`) and answers the concept review's requests within a second of the click,
  sending a draw's pictures back (`/request-files/`) before its report. The owner's timer (`timer.py`, `install-sync`, the
  deploy templates) reads the token by name from his secret manager each pass, inline, through the reader his env
  file names; it installs only once the cockpit runs this checkout's dashboard. `release.py` (`release`) moves the
  hosting repository's pinned `SCORE_COMMIT` to a pushed commit, from a worktree of its own, in the host's commit
  style; never run by a test against a real host (`tests/release_test.py` makes its repositories).
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
- **`films/`** the film script (its own overlay): the FILM pages' editor, free three.js preview on the web copies and
  films, and render items priced from measured frames; scripts saved in `$SCORE_DASHBOARD_HOME/films/`, starters in
  `data/films/`.
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
  never stops a run.
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
