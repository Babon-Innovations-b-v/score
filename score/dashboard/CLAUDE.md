# score/dashboard/

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
  A place's problems are its stopped steps, its named gaps and every standalone check's findings
  (`WORK/checks/<check>/<place>/findings.json`, `check_findings`, read while the outputs it judged stay accepted).
  Its holes (CONTEXT.md "hole") are the holes check's findings (`score/stages/complete/holes`), listed apart
  (`holes`, `holes_total`). Their price is the runner's (`score price world1 --holes`, its record
  `WORK/checks/holes-price/<world>.json` read as `HolesPrice`): `holes.py` only sums it, every paid node of any
  hole's chain once, each basis in its own bucket (measured runs, per unit × counted, per unit × forecast, the
  guesses with the file and line each is written on, never a price; the nodes with neither are unknown); no price
  is made and no unit counted here. A place never checked is named, never read as nothing to pay. A record made on
  another commit, on code not committed or on other per-unit prices than this checkout's (`priced_on`,
  `code_moved`), or older than any accept or reject or any holes check shows no number (`price_stale`, the rule of
  `current_findings`); the holes, their total and their price are read again as soon as a holes findings or the
  price record is written (`holes_written`, a stat each per request), never after the 60 s index. `per_place` gives
  each place's row (holes by kind, worst first: lost input, route step, missing, gate; its chains' paid nodes once,
  `own` the ones no other place's chain has); `plan_of` the runner's milestones (`score/stages/complete/holes/
  milestones.py`) in its order with the remake's total, the set budgets apart (never in a figure); the time is the
  record's `eta` (the runner's `holes/schedule.py`), shown only when every step has measured minutes. No plan is
  made or reordered here. Places and steps are said by their titles (`groups.place_title`, `groups.label`), never
  their keys. `present.prim_tree` gives a place's holes layer as a tree (no accepted assembly gives a whole scene
  tree yet), `present.hole_marks` the boxes the viewer outlines (`/view/<place>?holes=1&hole=<id>`, holes alone over
  a grid while no web copy exists).
  `files.py` serves only a sha a page listed, with cached JPEG thumbnails; `costs.py` only says minutes in words (the
  cockpit prices nothing: every price is the runner's, ADR-0006); `gaps.py` gives each named gap its step and a
  picture of what it names (local source only), `plain.py` says each problem in one plain sentence (the step
  pages' and the viewer's; the five screens show numbers).
- **`auth/`** `proxy.py` the outermost guard (only a trusted proxy may send `Remote-User`/`Remote-Email`; an
  underscore spelling is refused from every peer), `backends.py` the allow-list, `owner.py` the local owner account
  (a terminal, a 12+ character password, loopback bind only without a proxy).
- **`pages/`** the Django app (label `dashboard`): views, templates, static CSS/JS, its own SQLite records (change
  requests, basket, plans, launches, sync requests; never a mirror of the store). `actions.py` does what a request
  asks, one function each.
- **The cockpit app (#42): five screens under one top nav** (`templates/pages/base.html`): **Environment** `/`
  (`environment.html`: the month spent against the stop line, the remake's euros and hours, a Review and buy
  button, a tile per place), **Place** `/place/<place>/` (`place.html`: the 3D view, the scene tree with gap dots, a
  side panel), **Buy** `/buy/` (`buy.html`: the batch's list, total, ETA and the Buy button; the owner's books
  buttons while paid work is refused; no stop control: the Buy yes sets the batch's stop), **Stats** `/stats/`
  (`stats.html`: numbers only, no controls) and **Library** `/library/`. Step 1 built the shell, Environment and
  Stats; Place, Buy and Library hold `c/todo.html` placeholders (`data-step2`) that step 2 fills. The numbers come
  from `pages/cockpit.py` (`month_money`, `remake`, `tiles`, `scene_tree`, `gaps_by_kind`, `places_complete`,
  `measured_prices`, `timeline`), each None where the runner gives none, shown as a grey "unknown", never 0; the
  views are `views.environment`, `stats`, `buy`, `place_page` over `views.overview_of`. The components, each an
  include of `templates/pages/c/` with these arguments (every one ends without a newline, so it sits inline):
  - `dot.html` `tone` (done, idle, bad, review, hole-lost, hole-route, hole-missing, hole-gate: the `.tone-*`
    classes of dash.css), `tip`.
  - `ring.html` `done`, `total`, `tip`: a progress ring with done/total in it.
  - `number.html` `label`, `value` (None: grey "unknown" with `unknown_tip`), `unit` ("EUR": to the cent), `of` a
    denominator, `bar` a percent under it, `tone` a dot beside the label, `tip`. Pass every argument (None where
    unused): an include inherits its caller's names.
  - `tile.html` `href`, `picture`, `name`, `made`, `needed`, `gaps` (None: "?", not checked), `tone`, `tip`.
  - `tree.html` `nodes` [{label, count, tone, tip, href, open, panel, children, children_url}]: `children` drawn now,
    `children_url` fetched (GET, JSON [node] of the same fields) only when its branch first opens (dash.js); a
    failed load turns its dot red and goes to the console. `panel` {title, state, tone, price, action,
    action_label} opens the side panel on a click or Enter.
  - `panel.html` `id` (default "panel"): one a page, filled by dash.js from the opener's data-title, data-state,
    data-tone, data-price, data-action, data-action-label; Escape or its close button shuts it.
  - `todo.html` `label`: a step-2 placeholder.
  Hover text is the native `title` attribute: every component takes `tip`; an explanation goes there, never on
  the page.
- **`api/`** the routes and `deps.py` (the Django session read for FastAPI, CSRF on every write, owner-only routes).
- **`launch/`** the compute backend interface (`backend.py`: plan, spend, price, launch, poll, ledgered; chosen by
  `SCORE_COMPUTE_BACKEND=module:Class`), the shipped `localrun.py` (the `score` CLI), and `guard.py` (groups, the plan priced by the
  runner through `checkout/pricing.totals`, every launch refusal in words).
- **`checkout/`** the owner's one checkout of the basket items he bought, also under `/api/checkout`: each item's
  plan checked against what was priced, the environment's stop line at the basket's high (`score.review.web.stop`),
  one batch through the backend. Its own overlay has the rules.
- **`previews/`** a picture for each step whose output has none of its own, drawn from its files on the store's
  machine, kept per output, never imported by a hosted process.
- **`sync/`** hosted mode: `building.py` the export, `endpoints.py` the hosted side (token only), `client.py` and
  `applying.py` the store side's pass. The store's machine always calls out. The export goes content-addressed: only
  the files the hosted side lacks, thumbnails first, one 2 MiB gzip chunk a request, then a commit swaps it in whole.
  Each pass first runs the library sweep (`score.stages.library.sweep`, the environment against its library), so its
  problems are in the export by construction; a failed sweep is said in the pass's words and the pass goes on.
  The holes (`score.stages.complete.holes`, in a process of its own: it reads OpenUSD) are written right after it,
  the same way. A pass syncs nothing, and says why, from a checkout with tracked changes or a commit origin's main
  does not hold (`tree_refusal`), or when the runner's price after the holes (`score price <environment> --holes`,
  `runner_price`) fails, so no stale plan or price is ever sent. The owner's money buttons and his waiver
  (`applying.OWNER_FIGURES`: the stop line, the month's stop, the books' figure, the read-back, a waiver) are applied
  like his decisions: only when the request's user is this machine's `SCORE_OWNER`, through the same
  `pages/actions.py` function as the local cockpit, which refuses in an agent's process. Never tell the owner to
  type a command: an owner-only action is a button (#39). The owner's timer (`timer.py`, `install-sync`, the
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
  (thumbs, inbox, plans, status snapshots, exports, the month's stop). The store and the books are written only
  through `score.review.web` (`decide`, `waived`, `stop`, `google_month`), which the store, the guard and the books
  refuse in a process an agent started. Never call `Runner.drive`, `rebuy.buys`,
  `compute.clearance` or `rejudged_accepted` in the web process: plans, spend and freshness are subprocesses of the
  `score` command.
- **Never launch from a test or an agent against the real runner.** Tests use `tests/fixture.py:FakeBackend`; a launch
  needs the owner signed in, the month's stop set (`guard.month_stop`: his money card's figure, kept on the store's
  machine in `$SCORE_DASHBOARD_HOME/month-stop.json`, else `SCORE_MONTH_EUROS`) and every refusal of
  `guard.refusals` clear; the dashboard
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
