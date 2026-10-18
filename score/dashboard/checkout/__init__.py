"""The owner's basket of fix branches and his one checkout (the creator cockpit as a shopping list).

    offers   every fix branch, priced: the paid rows it moves from where it left main (score.stages.moved), each paid
             node at the runner's likely and high euros and minutes and its cards (score price, C19)
    basket   the branches he added, each with the commit and preview hash he saw; totals and time
    checkout his signed-in money yes, once: refused if any reviewed preview changed; lands the branches on main in a
             fixed order; writes the world's stop line at the basket's high (score.review.web.stop, C22); launches
             one batch through the compute backend, whose runner clears every paid node again
    results  per item its nodes' real cost from the ledger against their forecast, time, gate verdicts, new outputs

`git.py` the git side, `pricing.py` the prices, `previews.py` the preview hash, `flow.py` the checkout, `results.py` the
results feed, `routes.py` the API under /api/checkout.
"""
import os

REMOTE = os.environ.get("SCORE_LAND_REMOTE", "origin")
MAIN = "main"
FIX_PREFIX = os.environ.get("SCORE_FIX_PREFIX", "fix-")
WORLD = "world1"
