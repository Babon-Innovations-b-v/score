# score/dashboard/checkout/

The owner's one checkout of the basket: the items he chose to buy (what a run on main would buy, `proposals/make.py`),
his money yes for them. Read the package's `CLAUDE.md` one level up first; its rules hold here.

- **The checkout is the owner's money yes, nobody else's.** Owner only, signed in, CSRF (api/deps.py), one key per
  checkout (a second press with the same key is the same checkout), refused if any item's version moved since he
  chose it (`flow.bought_items`). The stop line is written only through `score.review.web.stop`, which refuses in any
  process an agent started; never write it any other way, never from a test against the real store.
- **Order is fixed:** the runner's own plan of each item must buy only the priced nodes -> stop line at spend so far
  + in flight + the basket's high plus 10% (`flow.BUFFER`: a batch's stop is its own high plus the buffer, set by
  his yes; there is no stop he sets, CONTEXT.md "batch") -> the runner's spend must show room -> ONE batch through the compute backend (a
  run command an item). Nothing here stops a run once started.
- **Prices are the runner's.** Each node's likely and high euros, minutes and cards come from the runner's own plan
  (`score plan`, C19) through the backend; nothing here guesses a number. A node the runner has not measured has no
  price (likely and high None): `pricing.totals` keeps its stage's estimate apart as `guessed_euros`, the pages say
  it as a guess, and the stop line holds it beside the high (`pricing.cleared_high`, the launch guard's high too), since the runner's clearance
  reserves that estimate.
- **Tests never launch.** `tests/checkout_test.py` uses `FakeBackend`, a temp basket and a temp store.
- One function, one purpose; no provider names; no imports of `tools.*` or `score.adapters` (`score.review.web` reaches
  the guard for us).
