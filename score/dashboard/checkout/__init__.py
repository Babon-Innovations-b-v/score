"""The owner's basket checkout (the creator cockpit's money yes).

    basket   the items he chose to buy on the basket page (pages/basket.py, BasketChoice), each as he saw it (its
             version); the items themselves are what a run on main would buy (proposals/make.py), priced at the
             runner's numbers (C19)
    checkout his signed-in money yes, once: refused if any item changed since he chose it; the runner's own plan of
             each item must buy only what was priced; writes the environment's stop line at the basket's high
             (score.review.web.stop, C22); launches one batch through the compute backend, whose runner clears every
             paid node again
    results  per item its nodes' real cost from the ledger against their forecast, time, gate verdicts, new outputs

`pricing.py` the totals, `flow.py` the checkout, `results.py` the results feed, `routes.py` the API under
/api/checkout.
"""
WORLD = "world1"
