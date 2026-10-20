# The runner is the only pricer

**Status:** accepted

The creator cockpit priced a launch plan itself: `score/dashboard/state/costs.py` took the measured
ledger runs, multiplied their median by a bill factor of its own (`SCORE_BILL_FACTOR`) and summed
lines into a time, while the basket and the proposals took the runner's prices (`score price`,
`compute.run_price`) through `checkout/pricing.totals`. The same work could so show two different
euros on two pages, and every pricing rule had two homes to keep in step.

We decided: the runner is the only pricer. Every euro and minute the cockpit or the paper shows is
the runner's (`score price` through the compute backend, summed by `checkout/pricing`); the cockpit
sums and says, never prices. The launch plan reads `pricing.totals` like the basket, its high is
`pricing.cleared_high` (the measured high plus the estimate the runner's clearance reserves for a
node not measured yet), and a bill factor, once the VAT question is settled, is applied in the
runner only. The measurement seam is `data/costs/per-unit.json` (written by `tools/costs/per_unit.py`)
with the cloud ledger's measured runs: change what is measured there, and every page follows.

The trade-off: the cockpit now needs a runner call (a subprocess of the `score` command) to price a
plan instead of reading the ledger files itself. We take that, because one number per basket is
worth more than a plan that works without the runner.
