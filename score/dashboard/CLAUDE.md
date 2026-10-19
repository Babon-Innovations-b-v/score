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
  `files.py` serves only a sha a page listed, with cached JPEG thumbnails; `costs.py` prices a plan from measured
  runs only; `gaps.py` gives each named gap its step and a picture of what it names (local source only), `plain.py`
  says each problem in one plain sentence.
- **`auth/`** `proxy.py` the outermost guard (only a trusted proxy may send `Remote-User`/`Remote-Email`; an
  underscore spelling is refused from every peer), `backends.py` the allow-list, `owner.py` the local owner account
  (a terminal, a 12+ character password, loopback bind only without a proxy).
- **`pages/`** the Django app (label `dashboard`): views, templates, static CSS/JS, its own SQLite records (change
  requests, basket, plans, launches, sync requests; never a mirror of the store). `actions.py` does what a request
  asks, one function each.
- **`api/`** the routes and `deps.py` (the Django session read for FastAPI, CSRF on every write, owner-only routes).
- **`launch/`** the compute backend interface (`backend.py`: plan, spend, measured, launch, poll; chosen by
  `SCORE_COMPUTE_BACKEND=module:Class`), the shipped `localrun.py` (the `score` CLI), and `guard.py` (groups, plan,
  every launch refusal in words).
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
  (thumbs, inbox, plans, status snapshots, exports). The store is written only through `score.review.web.decide`,
  which the store itself refuses in a server an agent started. Never call `Runner.drive`, `rebuy.buys`,
  `compute.clearance` or `rejudged_accepted` in the web process: plans, spend and freshness are subprocesses of the
  `score` command.
- **Never launch from a test or an agent against the real runner.** Tests use `tests/fixture.py:FakeBackend`; a launch
  needs the owner signed in, `SCORE_MONTH_EUROS` set and every refusal of `guard.refusals` clear; the dashboard
  never stops a run.
- **No module on sys.path, no stage imports this package.** Import dotted from `score.dashboard`; never a bare
  `views`, `models`, `urls`, `settings`, `apps` or `admin` (they would be hashed into stage keys). Do not edit
  `tools/review/*` (the viewer is served as a file) or add web tokens to `design/tokens/tokens.json`.
- **No provider here.** Nothing in this package imports `tools.*` or `score.adapters` or names a provider
  (`tests/no_provider_test.py`). Hosted mode never imports `score.stages`, `score.store`, numpy or usd-core
  (`tests/hosted_light_test.py`).
- **Pages are visual first:** a picture per piece, labelled plans, few words; node ids only inside the
  `details` fold (`tests/pages_test.py`). Money is the projected total against the stop, never per-piece prices alone.
- Tests: `make tests TESTS="score/dashboard/tests/*_test.py score/review/web_test.py"` (temp `PROPS_HOME` and
  dashboard home, `tests/conftest.py`). `tests/real_store_smoke.py` runs by hand against the real store, read-only.
  `tests/viewer_look.py` runs by hand too, free: the 3D viewer in headless Chromium from each film shot's and light
  look's camera beside that picture (difference, structure, brightness, pink and black, its `THRESHOLDS`); run it on
  new web copies, or `--hosted <export>` on the export the hosted site serves, before calling the viewer fixed.
