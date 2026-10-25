"""The owner's Buy approved in a Claude Code session (root CLAUDE.md, owner 2026-10-25: "i should be able to confirm my
buy with u aswell, u just click the button"). The session asks him with its question tool, naming the basket's price
(likely, high) and its stop; his yes is recorded here, quoted, and launches the checkout his Buy button makes
(flow.start, every refusal of his click), once.

    record(stop, high, answer, question)  his yes {id, purpose, stop_euros, high_euros, answer, question, at, by,
                                          basket {commit, made_at, items [{id, version}]}}, the basket the Buy screen
                                          buys now; kept once in the store, grants/buy/<id>.json (score.review.web)
    buy(yes id)                           his Buy under that yes, refused when: no quoted yes, used already (one yes
                                          launches at most one checkout: grants/buy-used/<id>.json, written once
                                          before the checkout, so a checkout refused after that needs a new yes),
                                          the basket differs from the one he approved, its high above his high or
                                          its stop (the high with the guesses plus 10%, flow.BUFFER) above his stop
                                          (flow.yes_refusals, checked again where the line is written), this
                                          machine's code off the cockpit's pin, paid work latched off, or a run
                                          active; then flow.start as his click, by "<owner>, approved in chat at
                                          <time>", the yes on the checkout (Checkout.chat_yes)

Reached from the agents' door (tools/cloud/conductor/agent_door.py `buy-yes`, `buy`). Agents never invent a yes: it is
written only from the answer the session's question tool got from him. A barrier, not a lock: every yes quotes who
said it and when, and every checkout names its yes.
"""
import datetime
import math
import os

from django.conf import settings
from django.contrib.auth import get_user_model

from score import conductor
from score.conductor import health
from score.dashboard import state
from score.dashboard.checkout import flow, pricing
from score.dashboard.pages import basket
from score.dashboard.pages.models import Checkout
from score.dashboard.proposals import records
from score.graph import runs

PIN_MINUTES = 30  # score-update reads the pin every 5 minutes and before every sync pass; older is not known now


class Refused(RuntimeError):
    """A yes that may not be recorded, or a Buy it may not launch, with why."""


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def euros_of(value, what):
    """`value` as euros above 0; Refused otherwise."""
    try:
        figure = float(value)
    except (TypeError, ValueError):
        figure = math.nan
    if not math.isfinite(figure) or figure <= 0:
        raise Refused(f"the {what} he approved is a figure above EUR 0, not {value!r}")
    return round(figure, 2)


def current_basket():
    """{commit, made_at, items}: the basket as the Buy screen's button buys it now (basket.batch_items "now")."""
    root = basket.basket_root()
    found = records.index(root)
    return {"commit": found.get("commit"), "made_at": found.get("made_at"),
            "items": sorted(basket.batch_items(records.items(root), "now"), key=lambda item: item["id"])}


def record(stop, high, answer, question, store=None):
    """Write his quoted yes to the current basket at his `high` and `stop` euros; the yes. Refused without an owner
    here, an answer and a question both, figures above 0, or a basket to buy."""
    from score.review import web
    if not str(answer or "").strip() or not str(question or "").strip():
        raise Refused("a Buy approved in chat quotes the owner's answer and the question he answered, both")
    if not settings.SCORE_OWNER:
        raise Refused("no owner is set here (SCORE_OWNER)")
    approved = current_basket()
    if not approved["items"]:
        raise Refused("the Buy screen buys nothing now: no basket to approve")
    moment = datetime.datetime.now(datetime.timezone.utc)
    return web.buy_yes_written(store or state.source().store, {
        "id": moment.strftime("%Y%m%dT%H%M%S%fZ"), "at": moment.isoformat(timespec="seconds"), "purpose": "buy", "stop_euros": euros_of(stop, "stop"),
        "high_euros": euros_of(high, "high"), "answer": str(answer), "question": str(question),
        "by": settings.SCORE_OWNER, "basket": approved})


# --- the Buy under a yes ------------------------------------------------------------------------------------------

def key_of(yes_id):
    return f"chat-{yes_id}"


def yes_found(store, yes_id):
    """The quoted yes `yes_id`; Refused when there is none or it was used."""
    from score.review import web
    yes = web.buy_yes(store, yes_id)
    if not yes or yes.get("purpose") != "buy" or not yes.get("answer") or not yes.get("question"):
        raise Refused(f"{yes_id} is no quoted Buy yes: ask him with the question tool and record his answer first")
    if web.buy_yes_used(store, yes_id) or Checkout.objects.filter(key=key_of(yes_id)).exists():
        raise Refused(f"the yes {yes_id} was used already: one yes launches one checkout; ask him again")
    return yes


def basket_refusals(yes, now_basket):
    """Why the basket now is not the one he approved, in words."""
    if now_basket["items"] != yes["basket"]["items"]:
        return [f"the basket changed since he approved it at {yes['at']} (then {len(yes['basket']['items'])} items, "
                f"now {len(now_basket['items'])}, or another version of one): a changed basket needs a new yes"]
    return []


def latch_refusals():
    """Why paid work is off here, in words: the owner's kill switch latch, or this process free only."""
    if conductor.free_only():
        return ["the owner's kill switch holds: paid work is latched off"]
    if os.environ.get(conductor.FREE_ONLY) not in (None, "", "0"):
        return [f"this process runs free only ({conductor.FREE_ONLY}): paid work is latched off"]
    return []


def pin_refusals(code, at=None):
    """Why this machine's code is not the cockpit's pinned commit (`code`, health.code) read in the last PIN_MINUTES,
    in words."""
    if code["matches"] is not True:
        return [f"this machine's code {code['checkout'] or 'unknown'} is not the cockpit's pin "
                f"{code['pin'] or 'unread'}"]
    read = datetime.datetime.fromisoformat(code["pin_at"]) if code.get("pin_at") else None
    at = at or datetime.datetime.now(datetime.timezone.utc)
    if read is None or (at - read).total_seconds() > PIN_MINUTES * 60:
        return [f"the cockpit's pin was last read at {code.get('pin_at') or 'never'}, not in the last {PIN_MINUTES} "
                "minutes"]
    return []


def run_refusals(folder=None):
    """Why a run is active on this store, in words (every live claim, runs/active.json)."""
    with runs.claims_locked(folder or runs.RUNS) as entries:
        active = sorted(entries)
    return [f"a run is active (pid {', '.join(active)}): wait for it to end"] if active else []


def buy(yes_id, store=None):
    """His Buy under the yes `yes_id`, once: every check of the module docstring, the yes marked used, then flow.start
    as his click, in this thread; (Checkout or None, words). Refused before the yes is marked used, nothing written."""
    from score.review import web
    store = store or state.source().store
    yes = yes_found(store, yes_id)
    now_basket = current_basket()
    items, _ = flow.bought_items(now_basket["items"])
    totals = pricing.totals(pricing.basket_prices(flow.snapshot(items)))  # flow.start checks it again, under its lock
    refused = (basket_refusals(yes, now_basket) + flow.yes_refusals(yes, totals) + latch_refusals()
               + pin_refusals(health.code()) + run_refusals())
    if refused:
        raise Refused("; ".join(refused))
    try:
        web.buy_yes_spent(store, yes_id, {"at": now(), "basket": now_basket})
    except FileExistsError:
        raise Refused(f"the yes {yes_id} was used already: one yes launches one checkout; ask him again") from None
    owner, _ = get_user_model().objects.get_or_create(username=yes["by"])
    with web.as_owner_under(store, yes_id):
        return flow.start(owner, key_of(yes_id), True, now_basket["items"], at_once=True, yes=yes)
