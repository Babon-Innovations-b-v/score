"""The basket and the owner's one checkout. His signed-in checkout is his money yes for the basket: refused before
anything happens when any reason below holds; then, in order, the chosen branches land on main (a conflict refuses
before anything is pushed), the run's own plan is checked to buy only what was priced, the environment's stop line is
written at the spend so far plus the basket's high total (score.review.web.stop, refused in an agent's process), the
runner's own spend reading must show room for it, and ONE batch launches through the compute backend, whose runner
clears every paid node again. Nothing here stops a run once started.
"""
import datetime
import threading

from django.conf import settings
from django.db import IntegrityError, transaction

from score.dashboard import state
from score.dashboard.checkout import MAIN, WORLD, git, previews, pricing
from score.dashboard.launch import guard
from score.dashboard.launch.backend import RunGroup
from score.dashboard.pages import actions
from score.dashboard.pages.models import BasketBranch, Checkout, Launch, Plan, is_owner

ACTIVE = ("landing", "launching")
_checking_out = threading.Lock()


# --- the basket -------------------------------------------------------------------------------------------------

def price_view(record):
    """A BranchPrice row as the pages read it."""
    if record is None:
        return {"state": "not priced", "nodes": {}, "totals": None, "error": ""}
    return {"state": record.state, "nodes": record.body.get("nodes", {}), "totals": record.body.get("totals"),
            "rows": record.body.get("rows", {}), "error": record.error}


def offer(branch):
    """A fix branch as an item on offer: its commit now, its preview hash, its price at that commit."""
    repo = settings.SCORE_REPO
    commit = git.head(repo, branch)
    return {"branch": branch, "head": commit, "preview_hash": previews.preview_hash(branch, commit),
            "in_basket": BasketBranch.objects.filter(branch=branch).exists(),
            "price": price_view(pricing.current(branch))}


def offers():
    """Every fix branch on offer, by name."""
    from score.dashboard.checkout import FIX_PREFIX
    return [offer(branch) for branch in git.fix_branches(settings.SCORE_REPO, FIX_PREFIX)]


def basket_item(entry):
    """A basket entry with what changed since the owner added it: its commit and its preview."""
    now = offer(entry.branch)
    return {**now, "seen_head": entry.head, "seen_preview_hash": entry.preview_hash, "added_by": entry.added_by,
            "added_at": entry.added_at.isoformat(), "changed": changed_words(entry, now)}


def changed_words(entry, now):
    """Why the item is not what the owner reviewed, or ""."""
    if now["head"] != entry.head:
        return f"{entry.branch} has a new commit since you looked: look again and add it again"
    if now["preview_hash"] != entry.preview_hash:
        return f"{entry.branch}'s preview changed since you looked: look again and add it again"
    return ""


def basket():
    """{items, totals}: the basket's items, and the totals of their nodes, each node once."""
    items = [basket_item(entry) for entry in BasketBranch.objects.all()]
    priced = [{"nodes": item["price"]["nodes"]} for item in items]
    return {"items": items, "totals": pricing.totals(pricing.basket_prices(priced))}


def add(user, branch, preview_hash):
    """Put a branch in the basket as the owner saw it (its preview hash); words. Pricing starts if it has not."""
    now = offer(branch)
    if preview_hash != now["preview_hash"]:
        return f"refused: {branch}'s preview changed while you looked at it: look again"
    BasketBranch.objects.update_or_create(branch=branch, defaults={
        "head": now["head"], "preview_hash": preview_hash, "added_by": user})
    pricing.start(branch)
    return f"{branch} is in the basket"


def remove(branch):
    deleted, _ = BasketBranch.objects.filter(branch=branch).delete()
    return f"{branch} taken out" if deleted else f"{branch} was not in the basket"


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


def item_refusals(items):
    """Why the basket's items cannot be bought as they stand, in words."""
    if not items:
        return ["the basket is empty"]
    found = [item["changed"] for item in items if item["changed"]]
    for item in items:
        price = item["price"]
        if price["state"] != "ready":
            why = f": {price['error']}" if price["error"] else ""
            found.append(f"{item['branch']} is not priced yet ({price['state']}{why})")
        elif price["totals"]["unpriced"]:
            found.append(f"{item['branch']}: the runner could not price {', '.join(price['totals']['unpriced'][:5])}")
    return found


def refusals(user, items, confirmed):
    """Every reason the checkout is refused, in words; empty when it may go."""
    found = [] if is_owner(user) else ["only the owner checks out"]
    found += place_refusals() + item_refusals(items)
    if Checkout.objects.filter(state__in=ACTIVE).exists():
        found.append("another checkout is still landing or launching")
    if actions.running_launch():
        found.append("a launch from this cockpit is still running")
    if not confirmed:
        found.append("tick \"I buy this basket\"")
    return found


# --- the checkout -------------------------------------------------------------------------------------------------

def snapshot(items):
    """The items as bought: branch, the commit and preview he saw, its priced nodes."""
    return [{"branch": item["branch"], "head": item["seen_head"], "preview_hash": item["seen_preview_hash"],
             "nodes": item["price"]["nodes"], "totals": item["price"]["totals"]} for item in items]


def start(user, key, confirmed, at_once=False):
    """(Checkout or None, words): the same checkout again for a key already used; else every refusal checked, then
    the checkout recorded and run in the background, or in this thread when `at_once` (a sync pass applying the
    owner's hosted checkout, whose process ends with the pass)."""
    with _checking_out:
        found = Checkout.objects.filter(key=key).first()
        if found is not None:
            return found, f"checkout {found.pk} was already made with this key: {found.state}"
        items = basket()["items"]
        refused = refusals(user, items, confirmed)
        if refused:
            return None, "refused: " + "; ".join(refused)
        bought = snapshot(items)
        try:
            with transaction.atomic():
                record = Checkout.objects.create(key=key, by=user.username, items=bought,
                                                 totals=pricing.totals(pricing.basket_prices(bought)))
        except IntegrityError:
            record = Checkout.objects.get(key=key)
            return record, f"checkout {record.pk} was already made with this key: {record.state}"
    if at_once:
        run(record)
        record.refresh_from_db()
        return record, f"checkout {record.pk}: {record.state}: {record.detail}"
    run_soon(record)
    return record, f"checkout {record.pk}: landing {len(bought)} branches"


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
        stopped = land(record)
        if stopped:
            return stopped
        if not nodes_of(record):
            return ended(record, "landed", "landed; the branches move no paid row: nothing to buy, nothing launched")
        group, planned = planned_batch(record, chosen)
        refused = plan_refusals(record, planned)
        if refused:
            return ended(record, "refused", "landed; nothing launched: " + "; ".join(refused))
        if not planned.buys:
            return ended(record, "landed", "landed; the run buys nothing: no stop line written, nothing launched")
        write_line(record, chosen)
        refused = room_refusals(record, chosen)
        if refused:
            return ended(record, "refused", "landed and the stop line written; nothing launched: " + refused)
        return launch(record, group, planned, chosen)
    except Exception as error:  # the page shows where the checkout stopped and why
        return ended(record, "failed", f"{record.detail} stopped: {type(error).__name__}: {error}".strip())


def land(record):
    """Land the items' branches on main and bring the runner's checkout to it; None when done, else the Checkout row
    ended (refused) with why."""
    repo = settings.SCORE_REPO
    refused = git.clean_main_refusal(repo)
    if refused:
        return ended(record, "refused", f"nothing landed: {refused}")
    try:
        done = git.land(repo, {item["branch"]: item["head"] for item in record.items})
    except git.Conflict as conflict:
        return ended(record, "refused", f"nothing landed: {conflict}")
    git.fast_forward(repo, done["main_after"])
    record.main_before, record.main_after, record.landed = done["main_before"], done["main_after"], done["landed"]
    record.before = accepted_before(record)
    record.state, record.detail = "launching", f"landed {len(done['landed'])} branches on {MAIN}"
    record.save()
    return None


def nodes_of(record):
    return sorted(pricing.basket_prices(record.items))


def accepted_before(record):
    """{node: its accepted output} before the batch: the results show what came new."""
    source = state.source()
    return {node: source.accepted_output(node) for node in nodes_of(record)}


def batch_group(nodes):
    """The one runner command for every node: their places and stages together (a stage the change did not move at a
    place keys the same there, so the runner makes nothing of it)."""
    places = sorted({node.split("@")[1] for node in nodes if "@" in node})
    stages = sorted({node.split("@")[0] for node in nodes})
    return RunGroup(places=tuple(places), stages=tuple(stages), world=WORLD)


def planned_batch(record, chosen):
    group = batch_group(nodes_of(record))
    return group, chosen.plan(group)


def plan_refusals(record, planned):
    """Why the run's own plan, on the landed code, is not what was priced, in words."""
    found = []
    if planned.missing:
        found.append(f"inputs are missing: {', '.join(planned.missing[:5])}")
    extra = sorted({buy["node"] for buy in planned.buys} - set(nodes_of(record)))
    if extra:
        found.append(f"the run would also buy {', '.join(extra[:6])}, which the basket's price leaves out: price "
                     "again and check out again")
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


def write_line(record, chosen):
    """The owner's money yes: the environment's stop line at the spend so far, what is in flight and the basket's high."""
    from score.review import web
    spent, reserved = spend_now(chosen)
    euros = round(spent + reserved + record.totals["high_euros"], 2)
    branches = ", ".join(item["branch"] for item in record.items)
    line = web.stop(state.source().store, WORLD, euros, f"checkout {record.pk}: {branches}", by=record.by)
    record.stop_line = {"euros": line["euros"], "before": line["before"], "at": line["at"], "spent": spent,
                        "reserved": reserved, "high": record.totals["high_euros"]}
    record.save()


def room_refusals(record, chosen):
    """Why the runner's own spend reading, after the line, has no room for the basket's high, or ""."""
    spend = chosen.spend()
    if None in (spend.ceiling, spend.spent, spend.reserved):
        return f"the runner reads no stop line: {spend.note or 'the spend could not be read'}"
    room = round(spend.ceiling - spend.spent - spend.reserved, 2)
    if record.totals["high_euros"] > room:
        return f"cannot finish under the stop: high EUR {record.totals['high_euros']:.2f}, room EUR {room:.2f}"
    return ""


def plan_body(record, group, planned):
    return {"groups": [guard.group_body(group, planned)], "buys": planned.buys, "jobs": guard.DEFAULT_JOBS,
            "nodes": nodes_of(record), "checkout": record.pk,
            "money": {"high": record.totals["high_euros"], "likely": record.totals["likely_euros"]},
            "time": {"likely_minutes": record.totals["likely_minutes"],
                     "high_minutes": record.totals["high_minutes"]}, "rebuys": 0.0}


def launch(record, group, planned, chosen):
    """Launch the one batch through the backend; the Checkout row, launched or refused by the runner."""
    plan = Plan.objects.create(basket_hash=f"checkout-{record.pk}", made_by=record.by, state="ready",
                               body=plan_body(record, group, planned),
                               finished=datetime.datetime.now(datetime.timezone.utc))
    reason = f"the owner's checkout {record.pk}: {', '.join(item['branch'] for item in record.items)}"
    started = Launch.objects.create(plan=plan, by=record.by, jobs=guard.DEFAULT_JOBS, rebuy_reason=reason)
    started = guard.launch(started, plan, chosen)
    record.launch = started
    if started.state == "refused":
        return ended(record, "refused", f"landed and the stop line written; the runner refused: {started.result}")
    return ended(record, "launched", f"launched one batch of {len(nodes_of(record))} paid nodes")
