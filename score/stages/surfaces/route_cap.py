"""The finish route's trial cap (owner, 2026-10-20: the route's test, EUR 5 in total): while the route is on trial its
paid rows (list, recheck) run only on the takes the runner's object filter names (`score run --object`), and every
Gemini ask they send is refused once the route's asks on the Google ledger (callers `finish-route-*`, every month)
and the next ask's estimate would pass TRIAL_EUROS. An ask asked before is read back free and never refused.

Counted as google_spend.month_euros counts: a finished call at its price (its model's estimate when unpriced), a call
started with no finished line (failed, killed, still going) at its estimate.
"""
import json

import finish_ask  # noqa: F401  (puts google_spend's folder on the path)

TRIAL_EUROS = 5.0
CALLERS = ("finish-route-list", "finish-route-recheck")


def require_filtered(params, row):
    """Refuse a paid route row with no object filter: on trial it runs only on named takes."""
    if not params.get("objects"):
        raise ValueError(f"{row}: the finish route is on trial (EUR {TRIAL_EUROS:g} in total); name the takes with "
                         "`score run --object <take>`")


def route_euros():
    """Every route ask on the Google ledger, in euros."""
    import google_spend
    if not google_spend.LEDGER.exists():
        return 0.0
    lines = [json.loads(line) for line in google_spend.LEDGER.read_text().splitlines() if line.strip()]
    lines = [line for line in lines if line.get("caller") in CALLERS]
    finished = {line.get("call") for line in lines if line.get("state", "finished") == "finished"}
    total = sum(google_spend.estimate(line["model"]) if line.get("euros") is None else line["euros"]
                for line in lines if line.get("state", "finished") == "finished")
    return total + sum(line["estimate"] for line in lines
                       if line.get("state") == "started" and line["call"] not in finished)


def require_room(model, body):
    """Refuse an ask not asked before when the route's asks so far and its estimate would pass TRIAL_EUROS."""
    import google_spend
    if google_spend.cache_path(model, body).exists():
        return
    spent, next_ask = route_euros(), google_spend.estimate(model)
    if spent + next_ask > TRIAL_EUROS:
        raise RuntimeError(f"the finish route's trial cap: EUR {spent:.2f} spent on its asks, the next would pass "
                           f"EUR {TRIAL_EUROS:g}")
