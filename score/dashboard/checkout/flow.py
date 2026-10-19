"""The owner's one checkout of the basket items he chose to buy. His signed-in checkout is his money yes: refused
before anything happens when any reason below holds; then, in order, the runner's own plan of each item is checked to
buy only the nodes he saw priced, the environment's stop line is written at the spend so far plus the basket's high
total (score.review.web.stop, refused in an agent's process), the runner's own spend reading must show room for it,
and ONE batch launches through the compute backend (a run command an item, side by side), whose runner clears every
paid node again. Nothing here stops a run once started.
"""
import datetime
import threading

from django.conf import settings
from django.db import IntegrityError, transaction

from score.dashboard import state
from score.dashboard.checkout import WORLD, pricing
from score.dashboard.launch import guard
from score.dashboard.launch.backend import RunGroup
from score.dashboard.pages import actions
from score.dashboard.pages.basket import basket_root
from score.dashboard.pages.models import Checkout, Launch, Plan, is_owner
from score.dashboard.proposals import records

ACTIVE = ("launching",)
_checking_out = threading.Lock()


def label(item):
    """An item in words: a declared item's title, else its place and what it changes."""
    if item.get("title"):
        return item["title"]
    return f"{(item.get('place') or 'the environment').replace('_', ' ')}: {', '.join(item['layers'])}"


# --- the checkout's refusals --------------------------------------------------------------------------------------

def place_refusals():
    """Why this cockpit cannot check out at all, in words."""
    found = []
    if settings.SCORE_MODE != settings.LOCAL:
        found.append("this cockpit is hosted: check out on the store's machine's cockpit")
    elif actions.agent_started():
        found.append("this cockpit was started from an agent's shell: only the owner's own server checks out")
    if not settings.SCORE_STORE_WRITABLE:
        found.append("the store is read-only here (SCORE_STORE_WRITABLE=0)")
    if not settings.SCORE_MONTH_EUROS:
        found.append("the month's stop is not set (SCORE_MONTH_EUROS): nothing launches without it")
    return found


def bought_items(seen):
    """(the items he bought as they stand now, why any of them is not what he saw): `seen` [{id, version}]."""
    found, changed = [], []
    for chosen in seen:
        now = records.item(basket_root(), chosen["id"])
        if now is not None and not now["nodes"]:
            changed.append(f"{label(now)}: a run on main does not buy it yet")
        elif now is None:
            changed.append(f"{chosen['id']} is no longer in the basket: a run would not buy it now")
        elif now["version"] != chosen["version"]:
            changed.append(f"{label(now)} changed since you chose it: look again and choose again")
        else:
            found.append(now)
    return found, changed


def item_refusals(items):
    """Why the items cannot be bought as they stand, in words."""
    found = []
    for item in items:
        if item["missing"]:
            found.append(f"{label(item)}: inputs are missing ({'; '.join(item['missing'][:3])})")
        unpriced = pricing.totals(item["nodes"])["unpriced"]
        if unpriced:
            found.append(f"{label(item)}: the runner could not price {', '.join(unpriced[:5])}")
    return found


def refusals(user, seen, items, changed, confirmed):
    """Every reason the checkout is refused, in words; empty when it may go."""
    found = [] if is_owner(user) else ["only the owner checks out"]
    found += place_refusals()
    if not seen:
        found.append("choose Buy on at least one item first")
    found += changed + item_refusals(items)
    if Checkout.objects.filter(state__in=ACTIVE).exists():
        found.append("another checkout is still launching")
    if actions.running_launch():
        found.append("a launch from this cockpit is still running")
    if not confirmed:
        found.append("tick \"I buy these\"")
    return found


# --- the checkout -------------------------------------------------------------------------------------------------

def snapshot(items):
    """The items as bought: id, version, place, layers, priced nodes and totals."""
    return [{"id": item["id"], "version": item["version"], "title": item.get("title"), "place": item["place"],
             "places": item["places"], "layers": item["layers"], "nodes": item["nodes"],
             "totals": pricing.totals(item["nodes"])} for item in items]


def start(user, key, confirmed, seen, at_once=False):
    """(Checkout or None, words): the same checkout again for a key already used; else every refusal checked, then
    the checkout recorded and run in the background, or in this thread when `at_once` (a sync pass applying the
    owner's hosted checkout, whose process ends with the pass). `seen` [{id, version}] the items he bought."""
    with _checking_out:
        found = Checkout.objects.filter(key=key).first()
        if found is not None:
            return found, f"checkout {found.pk} was already made with this key: {found.state}"
        items, changed = bought_items(seen)
        refused = refusals(user, seen, items, changed, confirmed)
        if refused:
            return None, "refused: " + "; ".join(refused)
        bought = snapshot(items)
        try:
            with transaction.atomic():
                record = Checkout.objects.create(key=key, by=user.username, items=bought, state="launching",
                                                 totals=pricing.totals(pricing.basket_prices(bought)))
        except IntegrityError:
            record = Checkout.objects.get(key=key)
            return record, f"checkout {record.pk} was already made with this key: {record.state}"
        record.before = accepted_before(record)
        record.save()
    if at_once:
        run(record)
        record.refresh_from_db()
        return record, f"checkout {record.pk}: {record.state}: {record.detail}"
    run_soon(record)
    return record, f"checkout {record.pk}: planning {len(bought)} item{'s' if len(bought) != 1 else ''}"


def run_soon(record):
    threading.Thread(target=run, args=(record,), daemon=True).start()


def ended(record, state_name, words):
    record.state, record.detail = state_name, words
    record.save()
    return record


def run(record, chosen=None):
    """The checkout's steps in order, in this thread; the Checkout row updated at each."""
    chosen = chosen or guard.backend()
    try:
        planned = planned_items(record, chosen)
        refused = plan_refusals(record, planned)
        if refused:
            return ended(record, "refused", "nothing launched: " + "; ".join(refused))
        if not any(plan.buys for _, plan in planned):
            return ended(record, "done", "the run buys nothing now: no stop line written, nothing launched")
        write_line(record, chosen)
        refused = room_refusals(record, chosen)
        if refused:
            return ended(record, "refused", "the stop line written; nothing launched: " + refused)
        return launch(record, planned, chosen)
    except Exception as error:  # the page shows where the checkout stopped and why
        return ended(record, "failed", f"{record.detail} stopped: {type(error).__name__}: {error}".strip())


def nodes_of(record):
    return sorted(pricing.basket_prices(record.items))


def accepted_before(record):
    """{node: its accepted output} before the batch: the results show what came new."""
    source = state.source()
    return {node: source.accepted_output(node) for node in nodes_of(record)}


def item_group(item):
    """One item's runner command: its places (none for the environment's own rows) and its nodes' stages."""
    return RunGroup(places=tuple(item["places"]), stages=tuple(sorted({node.split("@")[0] for node in item["nodes"]})),
                    world=WORLD)


def planned_items(record, chosen):
    """[(group, the runner's plan of it)] an item."""
    return [(group, chosen.plan(group)) for group in (item_group(item) for item in record.items)]


def plan_refusals(record, planned):
    """Why the runner's own plans are not what was priced, in words."""
    found, bought = [], set(nodes_of(record))
    for _, plan in planned:
        if plan.missing:
            found.append(f"inputs are missing: {', '.join(plan.missing[:5])}")
    extra = sorted({buy["node"] for _, plan in planned for buy in plan.buys} - bought)
    if extra:
        found.append(f"the run would also buy {', '.join(extra[:6])}, which the basket's price leaves out: look at "
                     "the basket again and check out again")
    return found


def spend_now(chosen):
    """(spent, reserved) since the environment's first stop line, nothing for an environment with none; RuntimeError when the
    runner could not read them (a line too low would refuse the batch, one too high would let more through)."""
    spend = chosen.spend()
    if spend.ceiling is None:
        return 0.0, 0.0
    if spend.spent is None or spend.reserved is None:
        raise RuntimeError(f"the spend could not be read: {spend.note or 'no figure'}")
    return float(spend.spent), float(spend.reserved)



def cleared_high(totals):
    """What the runner clears the basket at: its measured high and, for every node not measured yet, its stage's
    estimate (the runner's clearance reserves that guess, so the stop line must hold it)."""
    return round(totals["high_euros"] + totals.get("guessed_euros", 0.0), 2)


def write_line(record, chosen):
    """The owner's money yes: the environment's stop line at the spend so far, what is in flight and the basket's high
    (cleared_high: the guessed nodes' estimates with it)."""
    from score.review import web
    spent, reserved = spend_now(chosen)
    euros = round(spent + reserved + cleared_high(record.totals), 2)
    bought = ", ".join(label(item) for item in record.items)
    line = web.stop(state.source().store, WORLD, euros, f"checkout {record.pk}: {bought}", by=record.by)
    record.stop_line = {"euros": line["euros"], "before": line["before"], "at": line["at"], "spent": spent,
                        "reserved": reserved, "high": cleared_high(record.totals)}
    record.save()


def room_refusals(record, chosen):
    """Why the runner's own spend reading, after the line, has no room for the basket's high, or ""."""
    spend = chosen.spend()
    if None in (spend.ceiling, spend.spent, spend.reserved):
        return f"the runner reads no stop line: {spend.note or 'the spend could not be read'}"
    room = round(spend.ceiling - spend.spent - spend.reserved, 2)
    if cleared_high(record.totals) > room:
        return f"cannot finish under the stop: high EUR {cleared_high(record.totals):.2f}, room EUR {room:.2f}"
    return ""



def plan_body(record, planned):
    groups = [guard.group_body(group, plan) for group, plan in planned]
    return {"groups": groups, "buys": guard.unique_buys(groups), "jobs": guard.DEFAULT_JOBS,
            "nodes": nodes_of(record), "checkout": record.pk,
            "money": {"high": record.totals["high_euros"], "likely": record.totals["likely_euros"],
                      "guessed": record.totals.get("guessed_euros", 0.0)},
            "time": {"likely_minutes": record.totals["likely_minutes"],
                     "high_minutes": record.totals["high_minutes"]}, "rebuys": 0.0}


def launch(record, planned, chosen):
    """Launch the one batch through the backend; the Checkout row, launched or refused by the runner."""
    plan = Plan.objects.create(basket_hash=f"checkout-{record.pk}", made_by=record.by, state="ready",
                               body=plan_body(record, planned),
                               finished=datetime.datetime.now(datetime.timezone.utc))
    reason = f"the owner's checkout {record.pk}: {', '.join(label(item) for item in record.items)}"
    started = Launch.objects.create(plan=plan, by=record.by, jobs=guard.DEFAULT_JOBS, rebuy_reason=reason)
    started = guard.launch(started, plan, chosen)
    record.launch = started
    if started.state == "refused":
        return ended(record, "refused", f"the stop line written; the runner refused: {started.result}")
    return ended(record, "launched", f"launched one batch of {len(nodes_of(record))} paid nodes")
