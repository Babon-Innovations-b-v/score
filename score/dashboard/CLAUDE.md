# score/dashboard/

The creator cockpit's pages, web app, sign-in, 3D web copies, hosted side and its sync went on 2026-11-16 (owner:
"cockpit can also go"; #128). What stays is what the owner's chat decisions and Buys apply through, reached only from
the agents' door (`tools/cloud/conductor/agent_door.py`) and `tools/cloud/this_pc.py` (commands in `__main__.py`):

- **`sync/chat_decisions.py`** `decide-yes` / `decide`: his quoted yes recorded once, then applied once through
  `sync/applying.apply` (the request code his cockpit click once made, every check kept), refused when its target
  changed since the question. Root `CLAUDE.md` ("The owner may make every owner-only decision in chat").
- **`checkout/`** `buy-yes`, `buy`, `batch-money` (`chat_yes.py`): his Buy under one batch total; `flow.py` the one
  checkout (each item's plan checked against what was priced, the stop line, one batch through the backend),
  `watched.batch_money` and `flow.batch_budget` the batch's money. Its own overlay has the rules.
- **`launch/`** the compute backend interface (`backend.py`: plan, spend, price, launch, poll, ledgered; chosen by
  `SCORE_COMPUTE_BACKEND=module:Class`), the shipped `localrun.py` (the `score` CLI), and `guard.py` (groups, the plan priced by the
  runner through `checkout/pricing.totals`, every launch refusal in words).
- **`sync/client.py`** the store's upkeep pass (`sync`, the conductor's `score-sync` CronJob): disk sweep, library
  handover and sweep, the free design steps, gaps, prepare's figure, the runner's price, the basket (`proposals/`), the
  checkouts tidied, the USD check. `sync/timer.py` (`install-sync`) installs it as a systemd user timer on a VM or PC.
- **`proposals/`** the basket a Buy buys from: the runner's plan grouped into items (its own overlay).
- **`films/`** the film script and its lock (`pages/films.py` `film_locked`, a chat `lock-film`); its own overlay.
- **`pages/`** the Django app (label `dashboard`) holding the records the decisions and Buys write (`models.py`, its
  migrations) and the request code (`actions.py`, `basket.py`, `library_actions.py`, `seen.py`, `films.py`); no view.
- **`state/`** the store as read (`local.py` through `index.py`), the groups, money and screens figures the checkout
  and the basket read; `previews/` draws a step's picture for it. Both still carry cockpit-era parts (#128).
- **Read only, except the owner's own decisions.** The dashboard writes its SQLite and `$SCORE_DASHBOARD_HOME`
  (proposals, films, `bill-days.json`: the month's bills as read each day). The store and the books are written only
  through `score.review.web` (`decide`, `waived`, `stop`, `google_month`, `concept_draw`, `concept_pick`), which the store, the guard and the books
  refuse in a process an agent started. Never call `Runner.drive`, `rebuy.buys`,
  `compute.clearance` or `rejudged_accepted` in the web process: plans, spend and freshness are subprocesses of the
  `score` command.
- **Never launch from a test or an agent against the real runner.** Tests use `tests/fixture.py:FakeBackend` (one
  exception: `checkout/test_a_batch_buys_only_what_the_owner_approved.py`'s start-line test runs the real `score run --detach` on a run with nothing to make, in the
  test's own `PROPS_HOME`, so `localrun.STARTED` and the runner's line cannot drift apart); a launch
  needs the owner's recorded yes, room under the stop his last checkout's yes wrote and every refusal of
  `guard.refusals` clear; there is no stop he sets (no month's stop, no stop button: owner, 2026-10-20); the dashboard
  never stops a run itself: the owner's kill switch (Stop everything) hands it to `score.conductor.kill`.
- **No module on sys.path, no stage imports this package.** Import dotted from `score.dashboard`; never a bare
  `models`, `settings` or `apps` (they would be hashed into stage keys).
