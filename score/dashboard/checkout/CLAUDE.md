# score/dashboard/checkout/

The owner's basket of fix branches and his one checkout: the creator cockpit as a shopping list. Read the package's
`CLAUDE.md` one level up first; its rules hold here.

- **The checkout is the owner's money yes, nobody else's.** Owner only, signed in, CSRF (api/deps.py), one key per
  checkout (a second press with the same key is the same checkout), refused if any item's commit or preview hash
  moved since he added it (`previews.py`). The stop line is written only through `score.review.web.stop`, which
  refuses in any process an agent started; never write it any other way, never from a test against the real store.
- **Order is fixed:** land (a conflict refuses before anything is pushed) -> the runner's own plan must buy only the
  priced nodes -> stop line at spend so far + in flight + the basket's high -> the runner's spend must show room ->
  ONE batch through the compute backend. Nothing here stops a run once started.
- **Prices are the runner's.** `pricing.py` takes the moved rows from `score.stages.moved --json` and each paid node's
  likely and high euros, minutes and cards from `score price` (C19) through the backend; nothing here guesses a number.
  A node the runner has not measured has no price (likely and high None): `totals` keeps its stage's estimate apart
  as `guessed_euros`, the pages say it as a guess, and the stop line holds it beside the high (`flow.cleared_high`),
  since the runner's clearance reserves that estimate.
- **Tests never launch, never push to a real remote.** `tests/checkout_test.py` uses `FakeBackend`, a temp git repo
  with a bare remote, and a temp store; `SCORE_REPO` is pointed at the temp repo.
- One function, one purpose; no provider names; no imports of `tools.*` or `score.adapters` (`score.review.web` reaches
  the guard for us).
