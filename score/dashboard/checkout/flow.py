"""The owner's one checkout of the basket items he chose to buy. His signed-in checkout is his money yes: refused
before anything happens when any reason below holds (a basket made in another checkout, or before the design last
changed, among them); then, in order, the runner plans the whole batch once and must buy only the nodes he saw
priced, the month's books must be known, the environment's stop line is written at the spend so far plus the basket's
high total plus 10%, the batch's own stop (score.review.web.stop, refused in an agent's process), the runner's own
spend reading must show room for it, and ONE run launches through the compute backend holding every bought node
(`--stage <node>` each, so no two runs of one batch make the same upstream node), whose runner clears every paid node
again. A checkout refused or failed after its line, and a batch that ended, take the line back to the spend so far
plus what is in flight (`closed`); a checkout left launching by a process that is gone is failed (`abandoned`).
Nothing here stops a run once started.
"""
import contextlib
import datetime
import fcntl
import os
import pathlib
import threading
import time

from django.conf import settings
from django.db import IntegrityError, transaction

from score.dashboard import state
from score.dashboard.checkout import WORLD, pricing, watched
from score.dashboard.films import script
from score.dashboard.launch import guard
from score.dashboard.launch.backend import GroupPlan, RunGroup
from score.dashboard.launch.localrun import pid_alive
from score.dashboard.pages import actions
from score.dashboard.pages.basket import basket_root
from score.dashboard.pages.models import Checkout, Launch, Plan, is_owner
from score.dashboard.proposals import records
from score.dashboard.state import screens

ACTIVE = ("launching",)
BUFFER = 1.10  # a batch's stop is its high plus 10%, set by the owner's yes, never a figure he sets (owner, 2026-10-20)
# The store's areas a design change writes (score/review: a plan, its writing, a scene inventory reading, the
# environment's plan and concept); a lock or unlock is a record under concepts/<place>/picks/.
DESIGN_AREAS = ("plans", "plan-writings", "inventory-readings", "environment-plans", "environment-concept")
ENDED_RUNS = ("done", "failed", "stopped", "refused")
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
    filming = [item for item in items if any(script.films_node(node) for node in item["nodes"])]
    if filming and screens.film_waits():
        found.append(f"{label(filming[0])}: {screens.film_waits()} (the Film step)")
    return found


def design_changed(objects_root):
    """When the design last changed (UTC, to the second): the newest lock or unlock, plan, plan writing, scene
    inventory reading, environment plan or environment concept version written under the store's `objects_root`;
    None before any."""
    root = pathlib.Path(objects_root)
    folders = [*root.glob("concepts/*/picks"), *(root / area for area in DESIGN_AREAS)]
    newest = max((path.stat().st_mtime for folder in folders for path in folder.rglob("*")
                  if path.is_file() and not path.name.endswith(".partial")), default=None)
    return None if newest is None else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(newest))


def stale_basket(index, checkout, changed):
    """Why the basket (`index`, make.py's) is not what a run here would buy now, in words: none made, made in another
    checkout than `checkout` (an agent's worktree), or made before the design last changed (`changed`). Each sync
    pass makes it again."""
    if not index:
        return ["no basket is made yet: the next sync pass makes it"]
    found, made_in = [], index.get("checkout")
    if made_in is None or pathlib.Path(made_in).resolve() != pathlib.Path(checkout).resolve():
        found.append(f"the basket was made in {made_in or 'a checkout it does not name'}, not in this cockpit's "
                     f"checkout {checkout}: the next sync pass makes it again, then buy again")
    if changed and index.get("made_at", "") < changed:
        found.append(f"the basket was made at {index.get('made_at')}, before the design last changed ({changed}): "
                     "the next sync pass makes it again, then buy again")
    return found


def basket_refusals():
    """stale_basket of this cockpit's basket against its store; none while hosted (place_refusals says that)."""
    if settings.SCORE_MODE != settings.LOCAL:
        return []
    return stale_basket(records.index(basket_root()), settings.SCORE_REPO, design_now())


def design_now():
    """design_changed of this cockpit's store; "" while hosted, where no store is."""
    if settings.SCORE_MODE != settings.LOCAL:
        return ""
    return design_changed(state.source().store.objects.root) or ""


def refusals(user, seen, items, changed, confirmed):
    """Every reason the checkout is refused, in words; empty when it may go."""
    found = [] if is_owner(user) else ["only the owner checks out"]
    found += place_refusals()
    if not seen:
        found.append("choose Buy on at least one item first")
    found += basket_refusals() + changed + item_refusals(items)
    abandoned()
    if Checkout.objects.filter(state__in=ACTIVE).exists():
        found.append("another checkout is still launching")
    if actions.running_launch():
        found.append("a launch from this cockpit is still running")
    if not confirmed:
        found.append("tick \"I buy these\"")
    return found


# --- the checkout -------------------------------------------------------------------------------------------------

def snapshot(items):
    """The items as bought: id, version, place, layers, priced nodes (and why: the Benchmarks item's plan) and
    totals."""
    return [{"id": item["id"], "version": item["version"], "title": item.get("title"), "place": item["place"],
             "places": item["places"], "layers": item["layers"], "nodes": item["nodes"], "why": item.get("why", {}),
             "benchmarks": bool(item.get("benchmarks")),
             "totals": pricing.totals(item["nodes"])} for item in items]


def yes_refusals(yes, totals):
    """Why his Buy approved in a session (`yes`, checkout/chat_yes.py) does not cover a basket at `totals`, in words:
    its high above the high he approved, its stop (the high with the guesses, plus BUFFER: what write_line adds to
    the spend) above the batch total he approved, or a yes recorded as one try's stop before batch totals; none
    without a yes. Whether the try fits what the batch has left is batch_budget's, where the spend is read."""
    if not yes or yes.get("retry"):  # a retry under a used yes is held to the batch's budget (batch_budget)
        return []
    if yes.get("batch_total_euros") is None:
        return [f"the yes {yes.get('id')} names a try's stop, not the batch total (owner, 2026-10-26: \"the stop "
                "should be a total of the batch, not per try\"): ask him again with batch-money's figures"]
    found, stop = [], round(pricing.cleared_high(totals) * BUFFER, 2)
    if round(totals["high_euros"], 2) > round(yes["high_euros"], 2):
        found.append(f"its high is EUR {totals['high_euros']:.2f}, above the EUR {yes['high_euros']:.2f} he approved "
                     "in chat: a higher price needs a new yes")
    if stop > round(yes["batch_total_euros"], 2):
        found.append(f"its stop is EUR {stop:.2f}, above the batch total of EUR {yes['batch_total_euros']:.2f} he "
                     "approved in chat: a higher total needs a new yes")
    return found


def by_of(user, yes):
    """Who the checkout is by: his name, and when he approved it in chat for a Buy approved in a session."""
    return f"{user.username}, approved in chat at {yes['at']}" if yes else user.username


def start(user, key, confirmed, seen, at_once=False, yes=None):
    """(Checkout or None, words): the same checkout again for a key already used; else every refusal checked, then
    the checkout recorded and run in the background, or in this thread when `at_once` (a sync pass applying the
    owner's hosted checkout, whose process ends with the pass). `seen` [{id, version}] the items he bought; `yes`
    his Buy approved in a session (checkout/chat_yes.py), whose high and stop the basket must stay within."""
    with checking_out():
        found = Checkout.objects.filter(key=key).first()
        if found is not None:
            return found, f"checkout {found.pk} was already made with this key: {found.state}"
        items, changed = bought_items(seen)
        bought = snapshot(items)
        totals = pricing.totals(pricing.basket_prices(bought))
        refused = refusals(user, seen, items, changed, confirmed) + yes_refusals(yes, totals)
        if refused:
            return None, "refused: " + "; ".join(refused)
        try:
            with transaction.atomic():
                record = Checkout.objects.create(key=key, by=by_of(user, yes), items=bought, state="launching",
                                                 totals=totals, pid=os.getpid(), design_at=design_now(),
                                                 chat_yes=yes or {})
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


@contextlib.contextmanager
def checking_out():
    """One checkout's refusals and record at a time across this home's processes (the local cockpit and the sync pass
    applying a hosted Buy): two presses with different keys in two processes could otherwise both pass "another
    checkout is still launching" and both write a stop line and launch."""
    with _checking_out, (settings.SCORE_HOME / "checkout.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def run_soon(record):
    threading.Thread(target=run, args=(record,), daemon=True).start()


def ended(record, state_name, words):
    record.state, record.detail = state_name, words
    record.save()
    return record


def run(record, chosen=None):
    """The checkout's steps in order, in this thread; the Checkout row updated at each. Every refusal that needs no
    line comes before it is written (the month's books unknown among them: write_line); one after it, or a failure,
    takes the line back (`closed`)."""
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
            return closed(ended(record, "refused", "nothing launched: " + refused), chosen, "its checkout was refused")
        return launch(record, planned, chosen)
    except Refused as refused:
        return ended(record, "refused", f"nothing launched: {refused}")
    except Exception as error:  # the page shows where the checkout stopped and why
        failed = ended(record, "failed", f"{record.detail} stopped: {type(error).__name__}: {error}".strip())
        return closed(failed, chosen, "its checkout failed")


def nodes_of(record):
    return sorted(pricing.basket_prices(record.items))


def accepted_before(record):
    """{node: its accepted output} before the batch: the results show what came new."""
    source = state.source()
    return {node: source.accepted_output(node) for node in nodes_of(record)}


def batch_groups(items):
    """The checkout's runner commands: ONE holding every bought node of the items (their places, each node named in
    --stage, so the run makes only those and what they read: graph line_nodes), so no two runs of the batch would
    make the same upstream node (graph/runs.py refuses that clash); the Benchmarks item's own batch beside it."""
    nodes = sorted({node for item in items if not item.get("benchmarks") for node in item["nodes"]})
    places = sorted({node.partition("@")[2] for node in nodes} - {""})
    groups = [RunGroup(places=tuple(places), stages=tuple(nodes), world=WORLD)] if nodes else []
    if any(item.get("benchmarks") for item in items):
        groups.append(RunGroup(places=(), stages=(), world=WORLD, benchmarks=True))
    return groups


def benchmarks_plan(items):
    """The Benchmarks item's plan: its benchmarks as he saw them priced (their batch plans each itself, free, and
    names any whose inputs do not stand a gap: score/stages/complete/prepare/benchmarks.py)."""
    item = next(item for item in items if item.get("benchmarks"))
    buys = [{"node": node, "why": item["why"][node], "again": False} for node in item["nodes"]]
    return GroupPlan(missing=[], buys=buys, refusal=None, to_run={}, blocked={})


def planned_items(record, chosen):
    """[(group, the runner's plan of it)]: the batch's one run planned once by the runner; the Benchmarks item's own
    plan."""
    return [(group, benchmarks_plan(record.items) if group.benchmarks else chosen.plan(group))
            for group in batch_groups(record.items)]


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


class Refused(RuntimeError):
    """A reason the checkout is refused found once it runs, in words."""


def books_words(why):
    """The month's books unknown, in words naming the Buy screen's button that reads them."""
    return (f"the month's books are not known ({why}), so the runner would clear no paid step: press Read the bills "
            "on the Buy screen, then buy again")


def spend_now(chosen, books=False):
    """(spent, reserved) since the environment's first stop line, nothing for an environment with none; RuntimeError when the
    runner could not read them (a line too low would refuse the batch, one too high would let more through). With
    `books`, Refused while the month's books are not known (compute.clearance refuses every paid job then)."""
    spend = chosen.spend()
    if books and spend.paid_refused:
        raise Refused(books_words(spend.paid_refused))
    if spend.ceiling is None:
        return 0.0, 0.0
    if spend.spent is None or spend.reserved is None:
        raise RuntimeError(f"the spend could not be read: {spend.note or 'no figure'}")
    return float(spend.spent), float(spend.reserved)



def write_line(record, chosen):
    """The owner's money yes: the environment's stop line at the spend so far, what is in flight and the batch's own
    stop, its high (pricing.cleared_high: the guessed nodes' estimates with it) plus BUFFER (CONTEXT.md "batch").
    Refused, nothing written, while the month's books are not known."""
    from score.review import web
    refused = yes_refusals(record.chat_yes, record.totals)
    if refused:  # start checked it already; kept beside the one line a yes in chat may write
        raise Refused("; ".join(refused))
    spent, reserved = spend_now(chosen, books=True)
    start, budget = batch_budget(batch_tries(record), spent + reserved,
                                 round(pricing.cleared_high(record.totals) * BUFFER, 2), record.chat_yes)
    bought = ", ".join(label(item) for item in record.items)
    line = web.stop(state.source().store, WORLD, round(start + budget, 2), f"checkout {record.pk}: {bought}",
                    by=record.by)
    record.stop_line = {"euros": line["euros"], "before": line["before"], "at": line["at"], "spent": spent,
                        "reserved": reserved, "high": pricing.cleared_high(record.totals), "batch_from": start,
                        "batch_budget": budget, "batch_used": round(spent + reserved - start, 2)}
    record.save()


def batch_tries(record):
    """The checkouts of the batch `record` tries, oldest first, `record` last (watched.batch_of)."""
    store = state.source().store
    records = list(Checkout.objects.filter(at__lte=record.at).order_by("at"))
    return watched.batch_of(records, lambda node: (store.current_accept(node) or {}).get("at"))[1]


def batch_budget(tries, spent, need, yes):
    """(start, budget): the spend the batch counts from and its one budget across its tries (owner, 2026-10-26: "i
    feel like those budget asks should become per batch tho, not per try"), so the stop line is start + budget and
    every try draws from it. `tries` its checkouts, this try last; `spent` the spend now with what is in flight;
    `need` this try's high plus BUFFER; `yes` his yes in chat, if any. His click raises the budget to what the batch
    spent plus `need` when that is more; his yes in chat is the batch total he approved (owner, 2026-10-26: "the stop
    should be a total of the batch, not per try"), refused when this try does not fit it; a retry under a yes
    already used (`retry`) asks nothing new and must fit what is left. Refused otherwise."""
    lined = [one.stop_line for one in tries[:-1] if "euros" in one.stop_line]
    start = watched.batch_start(lined[0]) if lined and watched.batch_start(lined[0]) is not None else spent
    before = next((line["batch_budget"] for line in reversed(lined) if "batch_budget" in line), None)
    used = round(spent - start, 2)
    if yes and yes.get("retry"):
        if before is None or not any((one.chat_yes or {}).get("id") == yes["id"] for one in tries[:-1]):
            raise Refused(f"the yes {yes['id']} set no budget of this batch: ask him again")
        if used + need > before:
            raise Refused(f"over the batch budget: EUR {used:.2f} spent of EUR {before:.2f}, EUR {before - used:.2f} "
                          f"left, this try needs EUR {need:.2f}: ask him again")
        return start, before
    if yes:
        total = round(yes["batch_total_euros"], 2)
        if used + need > total:
            raise Refused(f"over the batch total he approved: EUR {used:.2f} spent with what is in flight, this try "
                          f"needs EUR {need:.2f}, EUR {total - used:.2f} left of EUR {total:.2f}: ask him again")
        return start, total
    return start, round(max(before or 0.0, used + need), 2)


def room_refusals(record, chosen):
    """Why the runner's own spend reading, after the line, has no room for the basket's high, or ""."""
    spend = chosen.spend()
    if None in (spend.ceiling, spend.spent, spend.reserved):
        return f"the runner reads no stop line: {spend.note or 'the spend could not be read'}"
    room = round(spend.ceiling - spend.spent - spend.reserved, 2)
    if pricing.cleared_high(record.totals) > room:
        return f"cannot finish under the stop: high EUR {pricing.cleared_high(record.totals):.2f}, room EUR {room:.2f}"
    return ""


# --- the line taken back ------------------------------------------------------------------------------------------

def close_line(record, chosen, why):
    """Write the environment's stop line back at the spend so far plus what is in flight, so nothing more is cleared
    under this checkout's yes; kept on the record as `closed`. Only while the newest line is still the one this
    checkout wrote (a later yes's line stands); said as `superseded` otherwise."""
    from score.review import web
    store = state.source().store
    newest = web.stop_line(store, WORLD)
    if newest is None or newest.get("at") != record.stop_line.get("at"):
        record.stop_line = {**record.stop_line, "closed": {"superseded": True, "why": why}}
        record.save()
        return record
    spent, reserved = spend_now(chosen)
    line = web.stop(store, WORLD, round(spent + reserved, 2), f"checkout {record.pk} closed: {why}", by=record.by)
    record.stop_line = {**record.stop_line, "closed": {"euros": line["euros"], "at": line["at"], "why": why}}
    record.save()
    return record


def closed(record, chosen, why):
    """close_line once a checkout that wrote its line ended refused or failed, or its batch ended; the record. A line
    that cannot be taken back is said on the record, never silently left."""
    if "euros" not in record.stop_line or record.stop_line.get("closed"):
        return record
    try:
        return close_line(record, chosen or guard.backend(), why)
    except Exception as error:  # said on the checkout's detail, the page shows it
        record.detail = f"{record.detail}; its stop line could not be taken back: {type(error).__name__}: {error}"
        record.save()
        return record


def abandoned(chosen=None):
    """Fail each checkout left launching by a process that is gone (a cockpit or sync pass killed mid-checkout), with
    why, its line taken back; the ones failed."""
    found = []
    for record in Checkout.objects.filter(state__in=ACTIVE):
        if record.pid is not None and pid_alive(record.pid):
            continue
        gone = f"the process running it (pid {record.pid}) ended before it launched"
        found.append(closed(ended(record, "failed", f"{record.detail} stopped: {gone}".lstrip()), chosen,
                            "its checkout failed"))
    return found


def batches_ended(chosen=None):
    """Take back the line of each launched checkout whose batch ended (done, failed, stopped or refused); the ones
    closed."""
    found = []
    for record in Checkout.objects.filter(state="launched", launch__isnull=False):
        if record.stop_line.get("closed") or guard.polled(record.launch, chosen).state not in ENDED_RUNS:
            continue
        found.append(closed(record, chosen, f"its batch ended {record.launch.state}"))
    return found


def tidied(chosen=None):
    """Each pass's care of the checkouts: abandoned ones failed, ended batches' lines taken back; in words."""
    failed, ended_batches = abandoned(chosen), batches_ended(chosen)
    return f"checkouts: {len(failed)} left launching failed, {len(ended_batches)} ended batches' lines taken back"



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
        return closed(ended(record, "refused", f"the runner refused: {started.result}"), chosen,
                      "the runner refused its run")
    return ended(record, "launched", f"launched one batch of {len(nodes_of(record))} paid nodes, stop line EUR "
                                     f"{record.stop_line['euros']:.2f}")
