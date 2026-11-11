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
from score.dashboard.state import batch_run, screens

ACTIVE = ("launching",)
BUFFER = 1.10  # a batch's stop is its high plus 10%, set by the owner's yes, never a figure he sets (owner, 2026-10-20)
# The store's areas a design change writes (score/review: a plan, its writing, a scene inventory reading, the
# environment's plan and concept); a lock or unlock is a record under concepts/<place>/picks/.
DESIGN_AREAS = ("plans", "plan-writings", "inventory-readings", "environment-plans", "environment-concept")
ENDED_RUNS = ("done", "failed", "stopped", "refused")
# The paid stages with no free route on this PC: their jobs need more card than its 16 GB (the close-up judge 30 GB,
# the people's bodies and dresses, their mesh parts 24 GB, the MOSS sound takes), so a try that stopped on one is
# retried in the cloud under its one paid remake (the plan of 2026-11-09, A3, C8); a stage named with a closing "-"
# is every stage it begins.
NO_FREE_ROUTE = ("closeup", "sound", "people-body-", "people-dress-", "people-look-parts-")
PAID_REMAKES = 1  # a result's paid remakes inside its batch; after them it is a gap (C8, K11)
# The tries counted for it: those from the env1 cap's start on (the plan's counter), so a row that failed before
# then, on code fixed since, is no gap.
REMAKES_FROM = datetime.datetime(2026, 11, 9, 18, 40, tzinfo=datetime.timezone.utc)
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


def left_out(items, stages):
    """The `items` with the nodes of `stages` taken out of each (a Buy approved without the demo films, chat_yes
    NO_FILM; owner, 2026-11-03: Batch 1 bought with the film left out), an item left with none dropped. The run names
    only the nodes kept (batch_groups), so a left-out row is neither bought nor made."""
    return nodes_kept(items, lambda stage: stage not in stages)


def phase_kept(items, phase):
    """The `items` with only the nodes of the phase `phase`'s stages kept (score/stages/phases; a Buy by phase, the
    door's `buy <yes id> --phase`, CONTEXT.md "phase"; several phases a comma list, their queues side by side in one
    run: owner, 2026-11-06), an item left with none dropped; every item without a phase."""
    if not phase:
        return items
    from score.stages import phases
    chosen = set(phase.split(","))
    return nodes_kept(items, lambda stage: phases.phase_of(stage) in chosen)


def places_left(items, chosen, left, upstream):
    """The nodes of `items` a Buy by place leaves out (the door's `buy <yes id> --place P,...` and `--leave-place
    P,...`; `score run --place` its model: the places' own rows and only the environment rows they read): a node at a
    place `chosen` (place names) does not hold, or `left` does; with `chosen` given, a Benchmarks node (no runner
    node) and an environment node (no place) no kept place's node needs; and every node whose `upstream(node)` (the
    nodes not standing it needs made first, graph/chain.upstream) holds a left-out place's node, which waits for that
    place's Buy, so the run never "would also buy" a left-out place's row (plan_refusals)."""
    def outside(node):
        place = node.partition("@")[2]
        return place in left or bool(chosen and place and place not in chosen)
    benchmarks = {node for item in items if item.get("benchmarks") for node in item["nodes"]}
    nodes = {node for item in items if not item.get("benchmarks") for node in item["nodes"]}
    needs = {node: set(upstream(node)) for node in nodes if not outside(node)}
    kept = {node for node, needed in needs.items() if not any(outside(other) for other in needed)}
    if chosen:
        wanted = {other for node in kept if node.partition("@")[2] for other in needs[node]}
        kept = {node for node in kept if node.partition("@")[2] or node in wanted}
    return (nodes - kept) | (benchmarks if chosen else set())


def nodes_kept(items, keeps):
    """The `items` with only the nodes whose stage `keeps(stage)` holds, an item left with none dropped."""
    found = []
    for item in items:
        nodes = {node: price for node, price in item["nodes"].items() if keeps(node.partition("@")[0])}
        if nodes:
            found.append({**item, "nodes": nodes})
    return found


def nodes_left(items, nodes):
    """The `items` with the nodes `nodes` taken out of each, an item left with none dropped."""
    found = []
    for item in items:
        kept = {node: price for node, price in item["nodes"].items() if node not in nodes}
        if kept:
            found.append({**item, "nodes": kept})
    return found


def free_route(node):
    """Whether this PC runs the node's stage free (NO_FREE_ROUTE names those it cannot)."""
    stage = node.partition("@")[0]
    return not any(stage.startswith(name) if name.endswith("-") else stage == name for name in NO_FREE_ROUTE)


def failed_rows(record):
    """The rows a checkout's runs stopped on: a row whose line in their logs names a fault report."""
    if not record.launch:
        return set()
    planned = set(watched.checkout_nodes(record))
    rows = batch_run.tried_rows(watched.checkout_runs(record), {}, planned)
    return {node for node, (state, _, _) in rows.items() if state == "failed"}


def remade_out(earlier, failed):
    """The rows that have had their one paid remake inside the batch (C8, owner 2026-11-08: one paid remake without
    asking): failed in more than PAID_REMAKES of the `earlier` tries made from REMAKES_FROM on (`failed` {checkout pk:
    rows}). A gap now, not bought again by this batch."""
    counts = {}
    for one in earlier:
        for node in failed.get(one.pk, ()) if one.at >= REMAKES_FROM else ():
            counts[node] = counts.get(node, 0) + 1
    return sorted(node for node, count in counts.items() if count > PAID_REMAKES)


def free_first(earlier, failed, accepted_at):
    """Why the next try waits, in words: the newest of the `earlier` tries that stopped on rows (`failed` {checkout
    pk: rows}) stopped on one whose stage this PC runs free, and it has not passed there since (no accept newer than
    that try: `accepted_at(node)`, ISO). A cloud retry of it waits for that free pass (C8: no cloud retry loop)."""
    stopped = [one for one in earlier if failed.get(one.pk)]
    if not stopped:
        return []
    last = stopped[-1]
    waiting = sorted(node for node in failed[last.pk] if free_route(node)
                     and not (watched.moment(accepted_at(node)) or last.at) > last.at)
    if not waiting:
        return []
    return [f"checkout {last.pk} stopped on {', '.join(waiting[:6])}{' and more' if len(waiting) > 6 else ''}, "
            "which this PC runs free: run it there until it passes (this_pc.py env1), then buy again"]


def retry_of(items, accepted_at):
    """(the `items` less the rows remade_out, those rows, the free_first refusals) for a Buy now: the batch's earlier
    tries read from the checkouts so far, as watched.batch_of counts them; the items as they are for a new batch."""
    records = list(Checkout.objects.order_by("at"))
    if not records:
        return items, [], []
    ahead = Checkout(at=datetime.datetime.now(datetime.timezone.utc))
    tries = watched.batch_of([*records, ahead], accepted_at)[1][:-1]
    failed = {one.pk: failed_rows(one) for one in tries}
    gaps = remade_out(tries, failed)
    return nodes_left(items, set(gaps)), gaps, free_first(tries, failed, accepted_at)


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


def basket_made(chosen=None, phase=None, places=None):
    """The basket made again from the runner's own plan now (proposals/make.py, plan only: free, no place assembled,
    as each sync pass makes it), so a Buy under his yes in chat buys what a run here buys at launch, not the basket an
    older pass saved (2026-11-05: free work after that pass moved more rows due and the run "would also buy" them);
    its index. A Buy's `phase` and `places` (comma lists, the door's --phase and --place) are the plan's own --phase
    and --place, so it plans only what it may buy, never the whole environment (2026-11-11: a phase's Buy planned
    every place for over 50 minutes). Refused, in words, when the runner could not plan."""
    from score.dashboard.proposals import make
    group = RunGroup(places=tuple(name for name in (places or "").split(",") if name), stages=(), world=WORLD,
                     phases=tuple(name for name in (phase or "").split(",") if name))
    try:
        return make.make(settings.SCORE_HOME, settings.SCORE_PROPS_HOME / "store", chosen=chosen or guard.backend(),
                         plan_only=True, group=group)
    except RuntimeError as failed:
        raise Refused(f"the basket could not be made again from the runner's plan now: {failed}") from failed


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
    a yes recorded as one try's stop before batch totals; none without a yes. A try whose high or stop is above what
    he was asked is no refusal, nor is a changed basket: a Buy holds till the batch total or the goal (owner,
    2026-11-05: "A BUY IS TILL THE END OF THE BUDGET OR UNTIL THE END GOAL ENV1 DONE IS COMPELTED"); the line is the
    total and the guard stops the try there (owner, 2026-10-27: "not just stop when u got to the limit, like ur
    supposed to"); whether the batch has room left is batch_budget's, where the spend is read."""
    if not yes or yes.get("retry"):  # a retry under a used yes is held to the batch's budget (batch_budget)
        return []
    if yes.get("batch_total_euros") is None:
        return [f"the yes {yes.get('id')} names a try's stop, not the batch total (owner, 2026-10-26: \"the stop "
                "should be a total of the batch, not per try\"): ask him again with batch-money's figures"]
    return []


def accepted_at(node):
    """When the node's standing accept in the store was given (ISO), or None."""
    return (state.source().store.current_accept(node) or {}).get("at")


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
        items = phase_kept(left_out(items, (yes or {}).get("leave_out", ())), (yes or {}).get("phase"))
        items = nodes_left(items, set((yes or {}).get("place_left", ())))  # a Buy by place (chat_yes.place_left)
        items, gaps, waits = retry_of(items, accepted_at)
        bought = snapshot(items)
        totals = {**pricing.totals(pricing.basket_prices(bought)), "gaps": gaps}
        refused = refusals(user, seen, items, changed, confirmed) + waits + yes_refusals(yes, totals)
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
        cheap_taken(record, planned, chosen)
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


def extra_buys(record, planned):
    """(the nodes the runner's plans buy that the basket's price leaves out, those of them that are gaps now): every
    one, so one refusal names them all (2026-11-11: one a refusal cost a re-plan of 20 to 30 minutes each)."""
    extra = sorted({buy["node"] for _, plan in planned for buy in plan.buys} - set(nodes_of(record)))
    gaps = sorted(set(extra) & set(record.totals.get("gaps") or ())) if extra else []
    return sorted(set(extra) - set(gaps)), gaps


def plan_refusals(record, planned):
    """Why the runner's own plans are not what was priced, in words, every node named."""
    found = []
    for _, plan in planned:
        if plan.missing:
            found.append(f"inputs are missing: {', '.join(plan.missing[:5])}")
    extra, gaps = extra_buys(record, planned)
    if gaps:
        found.append(f"{', '.join(gaps)} had {'their' if len(gaps) > 1 else 'its'} one paid remake in this batch "
                     "and is a gap now, but a row bought reads it: leave that row out (buy --phase) or fix it free")
    if extra:
        cheap = (record.chat_yes or {}).get("take_cheap")
        found.append(f"the run would also buy {len(extra)} row{'s' if len(extra) != 1 else ''} the basket's price "
                     f"leaves out: {', '.join(extra)}{f' (none under EUR {cheap:g} each)' if cheap else ''}: look "
                     "at the basket again and check out again, or buy --take-cheap <euros> to take the cheap ones in")
    return found


def cheap_taken(record, planned, chosen):
    """With the yes's `take_cheap` euros (the door's `buy <yes id> --take-cheap EUR`), the extra nodes the runner's
    plans buy (extra_buys, never a gap) each priced under it taken into the basket as one item, priced by the runner
    (`score price`) and the totals made again, instead of refused; the nodes taken."""
    limit = (record.chat_yes or {}).get("take_cheap")
    extra, _ = extra_buys(record, planned) if limit else ([], [])
    euros = {buy["node"]: buy.get("euros") for _, plan in planned for buy in plan.buys}
    taken = sorted(node for node in extra if euros.get(node) is not None and euros[node] < limit)
    if not taken:
        return []
    prices = chosen.price(WORLD, taken)
    record.items = [*record.items, {
        "id": "take-cheap", "version": 0, "title": f"upstream rows under EUR {limit:g} each, taken in",
        "place": None, "places": sorted({node.partition("@")[2] for node in taken} - {""}), "layers": [],
        "nodes": prices, "why": {}, "benchmarks": False, "totals": pricing.totals(prices)}]
    record.totals = {**pricing.totals(pricing.basket_prices(record.items)), "gaps": record.totals.get("gaps") or []}
    record.save()
    return taken


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
    should be a total of the batch, not per try"), and a retry under a yes already used (`retry`) asks nothing new
    and keeps the budget its own yes set, never above the total that yes approved: either launches while the batch
    has room left, a try that needs more stopping at the line (owner, 2026-10-27: "not just stop when u got to the
    limit, like ur supposed to"); refused with none left. A yes whose earlier checkouts wrote no line (refused before
    it: 2026-11-03, checkout 12 on unknown books) set no budget yet, so its next try sets the total he approved, never
    the batch's older budget (checkout 13 took October's EUR 665.18 over his EUR 462 and was stopped at once)."""
    lined = [one.stop_line for one in tries[:-1] if "euros" in one.stop_line]
    start = watched.batch_start(lined[0]) if lined and watched.batch_start(lined[0]) is not None else spent
    # the newest budget as the line holds it from this batch's start (a try once counted as its own batch's kept
    # another start: checkouts 5 and 6, 2026-10-26)
    before = next((round(line["euros"] - start, 2) for line in reversed(lined) if "batch_budget" in line), None)
    used = round(spent - start, 2)
    own = [one.stop_line for one in tries[:-1]
           if yes and yes.get("id") and (one.chat_yes or {}).get("id") == yes["id"] and "euros" in one.stop_line]
    if yes and yes.get("retry") and own:
        budget = before if yes.get("batch_total_euros") is None else min(before, round(yes["batch_total_euros"], 2))
        if used >= budget:
            raise Refused(f"the batch budget is spent: EUR {used:.2f} spent with what is in flight of EUR "
                          f"{budget:.2f}: ask him again for a higher total")
        return start, budget
    if yes and yes.get("retry") and yes.get("batch_total_euros") is None:
        raise Refused(f"the yes {yes['id']} set no budget of this batch: ask him again")
    if yes:
        total = round(yes["batch_total_euros"], 2)
        if used >= total:
            raise Refused(f"the batch total he approved is spent: EUR {used:.2f} spent with what is in flight of EUR "
                          f"{total:.2f}: ask him again for a higher total")
        return start, total
    return start, round(max(before or 0.0, used + need), 2)


def room_refusals(record, chosen):
    """Why the runner's own spend reading, after the line, has less room than the line gave this try (the basket's
    high, or what the batch has left when that is less: the try then stops at the line), or ""."""
    spend = chosen.spend()
    if None in (spend.ceiling, spend.spent, spend.reserved):
        return f"the runner reads no stop line: {spend.note or 'the spend could not be read'}"
    room = round(spend.ceiling - spend.spent - spend.reserved, 2)
    line = record.stop_line
    gave = min(pricing.cleared_high(record.totals), round(line["euros"] - line["spent"] - line["reserved"], 2))
    if spend.ceiling >= line["euros"] and room > 0:
        return ""  # the runner reads this line; spend since it was written is the guard's to hold (2026-11-08,
        # checkout 60: refused over EUR 0.99 a stopped try's cluster nodes billed while the next one priced)
    if gave > room:
        return f"cannot finish under the stop: the line gave EUR {gave:.2f}, the runner reads room EUR {room:.2f}"
    return ""


# --- the line taken back ------------------------------------------------------------------------------------------

def close_line(record, chosen, why):
    """Write the environment's stop line back at the spend so far plus what is in flight, so nothing more is cleared
    under this checkout's yes; kept on the record as `closed`. Only while the newest line is still the one this
    checkout wrote (a later yes's line stands, one written while the spend was read too: web.stop's `replaces`);
    said as `superseded` otherwise."""
    from score.review import web
    store = state.source().store
    newest = web.stop_line(store, WORLD)
    if newest is None or newest.get("at") != record.stop_line.get("at"):
        return superseded(record, why)
    spent, reserved = spend_now(chosen)
    line = web.stop(store, WORLD, round(spent + reserved, 2), f"checkout {record.pk} closed: {why}", by=record.by,
                    replaces=record.stop_line["at"])
    if line is None:
        return superseded(record, why)
    record.stop_line = {**record.stop_line, "closed": {"euros": line["euros"], "at": line["at"], "why": why}}
    record.save()
    return record


def superseded(record, why):
    """The record's line left standing under a later try's, said as `superseded`; the record."""
    record.stop_line = {**record.stop_line, "closed": {"superseded": True, "why": why}}
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
    orphaned_launches()
    return found


def orphaned_launches():
    """Fail each launch still `starting` whose checkout is no longer launching: its process ended between making the
    launch and handing it to the runner, and a `starting` launch is never polled, so it held every later Buy off as
    "a launch from this cockpit is still running" (2026-11-04: a Buy cut off with its ssh); the ones failed."""
    failed = []
    for launch in Launch.objects.filter(state="starting", plan__basket_hash__startswith="checkout-"):
        number = launch.plan.basket_hash.removeprefix("checkout-")
        if number.isdigit() and Checkout.objects.filter(pk=int(number), state__in=ACTIVE).exists():
            continue
        launch.state, launch.result = "failed", "its checkout ended before the launch reached the runner"
        launch.save()
        failed.append(launch)
    return failed


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
                                     f"{record.stop_line['euros']:.2f}{may_stop_words(record)}{gap_words(record)}")


def gap_words(record):
    """The rows this try left out as gaps after their one paid remake (retry_of), in words; "" for none."""
    gaps = record.totals.get("gaps") or []
    if not gaps:
        return ""
    return f"; left out as gaps after their one paid remake: {', '.join(gaps[:6])}{' and more' if len(gaps) > 6 else ''}"


def may_stop_words(record):
    """That this try may stop at the batch limit, when what its line left the batch is under its high plus BUFFER;
    "" otherwise."""
    line = record.stop_line
    left = round(line["euros"] - line["spent"] - line["reserved"], 2)
    need = round(pricing.cleared_high(record.totals) * BUFFER, 2)
    if left >= need:
        return ""
    return (f"; this try may stop at the batch limit before every step is made (EUR {left:.2f} left, its high plus "
            f"10% EUR {need:.2f})")
