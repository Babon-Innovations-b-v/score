# score/dashboard/checkout/

The owner's one checkout of the basket: the items he chose to buy (what a run on main would buy, `proposals/make.py`),
his money yes for them. Read the package's `CLAUDE.md` one level up first; its rules hold here.

- **The checkout is the owner's money yes, nobody else's.** Owner only, signed in, CSRF (api/deps.py), one key per
  checkout (a second press with the same key is the same checkout; `flow.checking_out` holds the home's
  `checkout.lock`, so the local cockpit and a sync pass never both pass the checks), refused if any item's version moved since he
  chose it (`flow.bought_items`). The stop line is written only through `score.review.web.stop`, which refuses in any
  process an agent started; never write it any other way, never from a test against the real store.
- **The basket must be this checkout's and current** (`flow.stale_basket`): refused when made in another checkout
  than the cockpit's (an agent's worktree) or before the design last changed (`flow.design_changed`: the newest
  lock, plan, plan writing, scene inventory reading, environment plan or concept version in the store). Each sync
  pass makes it again (`sync/client.basket_made`).
- **Order is fixed:** the runner plans the whole batch ONCE and it must buy only the priced nodes -> the month's
  books must be known (`flow.books_words`: else refused, naming Read the bills) -> stop line at spend so far + in
  flight + the basket's high plus 10% (`flow.BUFFER`: a batch's stop is its own high plus the buffer, set by his
  yes; there is no stop he sets, CONTEXT.md "batch") -> the runner's spend must show room -> ONE run command through
  the compute backend holding every bought node (`flow.batch_groups`: each node in `--stage`, so no two runs of one
  batch make the same upstream node, which graph/runs.py refuses). A refusal or failure after the line, and a batch
  that ended, write it back at spent plus in flight (`flow.closed`, only while it is still this checkout's line); a
  checkout left launching by a process that is gone (`Checkout.pid`) is failed (`flow.abandoned`). Nothing here
  stops a run once started. The Benchmarks item (`proposals/benchmarks.py`) is
  priced at prepare's estimate and launched as its own batch (`RunGroup.benchmarks`), which plans each benchmark
  itself; its stop is its high, guesses in, plus 10% like any item's.
- **Prices are the runner's.** Each node's likely and high euros, minutes and cards come from the runner's own plan
  (`score plan`, C19) through the backend; nothing here guesses a number. A node the runner has not measured has no
  price (likely and high None): `pricing.totals` keeps its stage's estimate apart as `guessed_euros`, the pages say
  it as a guess, and the stop line holds it beside the high (`pricing.cleared_high`, the launch guard's high too), since the runner's clearance
  reserves that estimate.
- **A Buy approved in a session** (`chat_yes.py`, root CLAUDE.md, owner 2026-10-25): `buy-yes` records his quoted
  answer and question, the high and stop he approved and the Buy screen's basket (grants/buy/<id>.json, written by
  score.review.web); `buy <id>` runs `flow.start` as his click, once (grants/buy-used/<id>.json written before it),
  refused on another basket, a high or stop above his (`flow.yes_refusals`, again in `write_line`), code off the
  pin, the latch or a live run. The checkout's `by` and `chat_yes` name the yes; the monitor and Buy page show it.
  `buy <id>` again under a yes that launched a checkout is a retry of its batch (`chat-<id>-retry-N`), no new ask,
  held to the batch's budget.
- **One budget a batch, across its tries** (root CLAUDE.md, owner 2026-10-26: "those budget asks should become per
  batch tho, not per try"). `flow.batch_budget` (in `write_line`): the batch's start is what its first try's line was
  written over (`batch_from`, else that line's spent plus reserved); its budget the newest try's, raised by a click or
  a new yes to what the batch spent so far plus what he approved (the yes's stop, else the try's high plus BUFFER)
  when that is more; the line is start plus budget, so the guard (score.adapters.compute) stops at the budget less
  what earlier tries spent. A retry under a used yes keeps the budget and is refused when its high plus BUFFER does
  not fit what is left. Each line records `batch_from`, `batch_budget` and `batch_used`; `watched.newest` gives the
  budget, and the monitor and Buy page show what the batch spent, every try and its pool time, of it and what is left.
- **Tests never launch.** `checkout/test_a_batch_buys_only_what_the_owner_approved.py` uses `FakeBackend`, a temp basket and a temp store.
- One function, one purpose; no provider names; no imports of `tools.*` or `score.adapters` (`score.review.web` reaches
  the guard for us).
