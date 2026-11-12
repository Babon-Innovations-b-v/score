"""The owner's Buy approved in a Claude Code session (root CLAUDE.md, owner 2026-10-25: "i should be able to confirm my
buy with u aswell, u just click the button"). The session asks him with its question tool, naming the basket's price
(likely, high) and the batch's total stop, with what the batch spent so far (owner, 2026-10-26: "the stop should be
a total of the batch, not per try, i have no clue now"); his yes is recorded here, quoted, and launches the checkout
his Buy button makes (flow.start, every refusal of his click), once.

    figures(reading, leave_out)           what the question names, read only (the door's `batch-money`): {batch,
                                          tries, retry (the next Buy tries this batch again), money (watched.
                                          batch_money: spent so far by the money guard's measure, in flight, its
                                          budget, left, the books' parts), runs (its runs' own heartbeats), try
                                          {likely, high, stop: high with guesses plus 10%}, fits (the smallest batch
                                          total holding this try), click (the total his Buy click would set),
                                          may_stop (a retry under the yes already used would stop at the batch
                                          limit before every step is made: what is left is under this try's stop),
                                          cap (env1's spend from the whole bill against its EUR 300, the plan of
                                          2026-11-09 B7: score.review.web.cap_figure)}
    record(total, high, answer, question, leave_out)
                                          his yes {id, purpose, batch_total_euros, high_euros, answer, question, at, by,
                                          basket {commit, made_at, items [{id, version}]}, leave_out}, the basket the
                                          Buy screen buys now; kept once in the store, grants/buy/<id>.json
                                          (score.review.web). `leave_out` (NO_FILM, the door's --no-film) the stages
                                          whose rows that Buy neither buys nor makes, priced without them
    buy(yes id, phase)                    with a phase (score/stages/phases), only that phase's rows of the basket
                                          (flow.phase_kept) under the same yes and batch total, the checkout's
                                          chat_yes naming it; his Buy under that yes, refused when: no quoted yes, used already (one yes
                                          launches at most one checkout: grants/buy-used/<id>.json, written once
                                          before the checkout, so a checkout refused after that needs a new yes),
                                          a yes naming a try's stop rather than a batch total (flow.yes_refusals), or
                                          nothing left of his total (flow.batch_budget, where the line is written:
                                          the line is the batch's start plus his total, and a try that needs more
                                          than is left stops at it, owner 2026-10-27), this
                                          machine's code off the cockpit's pin, paid work latched off, or a run
                                          active; then flow.start as his click on the basket made again from the
                                          runner's plan now (flow.basket_made) at the places approved now
                                          (approved_now: prepare's design rule run at launch, refused with its
                                          cause when it fails), by "<owner>, approved in chat at
                                          <time>", the yes on the checkout (Checkout.chat_yes); again under a yes
                                          that launched one, a retry of its batch held to the batch's budget
                                          (flow.batch_budget: launched while any of it is left), no new ask; a
                                          basket changed since the yes (fewer, more or other items, other
                                          versions) or a higher high is bought under it, no new ask: a Buy holds
                                          till his batch total or the goal (owner, 2026-11-05: "A BUY IS TILL THE
                                          END OF THE BUDGET OR UNTIL THE END GOAL ENV1 DONE IS COMPELTED")

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

NO_FILM = ("demo-film", "demo-film-extra")  # the demo films' paid rows (owner, 2026-11-03: Batch 1 without the film)
from score.dashboard.pages import basket
from score.dashboard.pages.models import Checkout
from score.dashboard.proposals import records
from score.dashboard.state import batch_run
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


def current_basket(approved=None):
    """{commit, made_at, items}: the basket as the Buy screen's button buys it now (basket.batch_items "now"), at the
    places `approved` (None: those prepare's design record names)."""
    root = basket.basket_root()
    found = records.index(root)
    return {"commit": found.get("commit"), "made_at": found.get("made_at"),
            "items": sorted(basket.batch_items(records.items(root), "now", approved), key=lambda item: item["id"])}


def approved_now(source=None):
    """The places whose design stands approved now, by prepare's own rule (prepare/design.designs) over the store and
    the code running, never the record a sync pass saved (2026-11-05: a fix to the design rule left 14 places of base
    and square unapproved there until the next pass); Refused with its cause when it cannot be worked out."""
    from score.stages.complete.prepare import design  # the store's machine only: hosted never imports the stages
    source = source or state.source()
    try:
        return design.designs(source.store, source.data, source.places())["approved"]
    except Exception as failed:
        raise Refused(f"the approved places could not be worked out now: {type(failed).__name__}: {failed}") from failed


def record(total, high, answer, question, store=None, leave_out=()):
    """Write his quoted yes to the current basket at this try's `high` and the batch `total` he approved (the batch's
    whole stop, every try's spend in it); the yes. Refused without an owner here, an answer and a question both,
    figures above 0, or a basket to buy."""
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
        "id": moment.strftime("%Y%m%dT%H%M%S%fZ"), "at": moment.isoformat(timespec="seconds"), "purpose": "buy",
        "batch_total_euros": euros_of(total, "batch total"),
        "high_euros": euros_of(high, "high"), "answer": str(answer), "question": str(question),
        "by": settings.SCORE_OWNER, "basket": approved, "leave_out": list(leave_out)})


def basket_totals(now_basket, leave_out=(), phase=None, place_left=()):
    """pricing.totals of the basket `now_basket` (current_basket) at the runner's prices now, the rows of the stages
    `leave_out` taken out (flow.left_out), only the phase `phase`'s rows kept when given (flow.phase_kept), the nodes
    `place_left` (place_left) taken out."""
    items, _ = flow.bought_items(now_basket["items"])
    items = flow.nodes_left(flow.phase_kept(flow.left_out(items, leave_out), phase), set(place_left))
    return pricing.totals(pricing.basket_prices(flow.snapshot(items)))


def figures(reading, leave_out=()):
    """What his question names, read only (module docstring), at the Spend `reading()` gives (the backend's now), the
    try priced without the stages `leave_out`."""
    from score.dashboard.checkout import watched
    spend = reading()
    records = list(Checkout.objects.order_by("at"))
    number, tries = watched.batch_of(records, accepted_at) if records else (0, [])
    ahead = Checkout(at=datetime.datetime.now(datetime.timezone.utc))
    retry = bool(tries) and not watched.batch_ended(tries, ahead, accepted_at)
    from score.review import web
    cap = web.cap_figure()
    money = watched.batch_money(tries, spend, cap) if retry else None
    totals = basket_totals(current_basket(), leave_out)
    need = round(pricing.cleared_high(totals) * flow.BUFFER, 2)
    run = state.source().batch_run(reading=lambda: spend) if retry else None
    return {"batch": number if retry else number + 1, "tries": watched.try_count(tries) if retry else 0, "retry": retry,
            "money": money, "runs": ((run or {}).get("money") or {}).get("runs") if retry else None,
            "try": {"likely": totals["likely_euros"], "high": pricing.cleared_high(totals), "stop": need},
            "fits": need if money is None else round(money["spent"] + money["in_flight"] + need, 2),
            "click": need if money is None else batch_run.batch_total(money, need),
            "may_stop": money is not None and money["left"] < need, "cap": cap}


def accepted_at(node):
    return (state.source().store.current_accept(node) or {}).get("at")


# --- the Buy under a yes ------------------------------------------------------------------------------------------

def key_of(yes_id, retry=0):
    return f"chat-{yes_id}" + (f"-retry-{retry}" if retry else "")


def yes_found(store, yes_id):
    """The quoted yes `yes_id`; one that launched a checkout already as a retry (`retry`: a later try of its batch,
    held to the batch's budget, flow.batch_budget; owner, 2026-10-26: "those budget asks should become per batch tho,
    not per try"); Refused when there is none, or it was used and launched nothing."""
    from score.review import web
    yes = web.buy_yes(store, yes_id)
    if not yes or yes.get("purpose") != "buy" or not yes.get("answer") or not yes.get("question"):
        raise Refused(f"{yes_id} is no quoted Buy yes: ask him with the question tool and record his answer first")
    launched = Checkout.objects.filter(key__startswith=key_of(yes_id)).count()
    if launched:
        return {**yes, "retry": launched}
    if web.buy_yes_used(store, yes_id):
        raise Refused(f"the yes {yes_id} was used already and launched nothing: ask him again")
    return yes


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


def known_phase(phase):
    """`phase` (one phase, or several as a comma list) when each is a phase of score/stages/phases; Refused naming
    the phases otherwise."""
    from score.stages import phases
    unknown = [name for name in phase.split(",") if name not in phases.NAMES]
    if unknown:
        raise Refused(f"{', '.join(unknown)} is no phase: one of {', '.join(phases.NAMES)}")
    return phase


def known_stages(names):
    """The stage names `names` (a comma list) to leave out of a Buy, each a stage of the table; Refused otherwise."""
    from score import stages
    table = {stage.name for stage in stages.STAGES}
    unknown = [name for name in names.split(",") if name not in table]
    if unknown:
        raise Refused(f"{', '.join(unknown)} is no stage of the table")
    return names.split(",")


def place_left(items, places=None, leave_places=None, runner=None):
    """The nodes of `items` a Buy by place leaves out (flow.places_left): `places` (a comma list) the places it buys,
    with the environment rows they need; `leave_places` (a comma list) the places it does not buy; a node needing a
    left-out place's row not standing waits (graph/chain.upstream over the runner's table, as `score run --place`
    walks it). Refused naming a name that is no place of the environment."""
    from score import stages
    from score.graph import chain
    runner = runner or stages.runner()
    known = set(stages.places(runner.world, runner.store))
    chosen, left = [set(names.split(",")) if names else set() for names in (places, leave_places)]
    unknown = sorted((chosen | left) - known)
    if unknown:
        raise Refused(f"{', '.join(unknown)} is no place of the environment: one of {', '.join(sorted(known))}")
    def upstream(node):
        return chain.upstream(runner, runner.nodes_named([node]))
    return sorted(flow.places_left(items, chosen, left, upstream))


def relations_kept(places=None):
    """Each kept plan's relations derived again where they changed (holders.keep, as the sync's plans pass keeps
    them: plans_pass.main), over `places` (a comma list; None: every kept plan), so a Buy never plans on relations
    older than its plans, whether the sync runs or not (2026-11-12: the sync paused, Buy 91 built 4 places' scene
    records from relations older than the night's fixes); one line naming the places whose relations changed."""
    from score.review import holders
    kept = sorted(path.stem for path in holders.KEPT_PLANS.glob("*.json"))
    chosen = {name for name in (places or "").split(",") if name}
    changed = holders.keep([place for place in kept if not chosen or place in chosen])
    return f"relations kept before the plan: {', '.join(changed) + ' changed' if changed else 'none changed'}"


def buy(yes_id, store=None, phase=None, leave_out=None, places=None, leave_places=None, take_cheap=None):
    """His Buy under the yes `yes_id`, once: every check of the module docstring, the yes marked used, then flow.start
    as his click, in this thread; (Checkout or None, words). With `phase` (score/stages/phases, the door's `--phase`)
    only that phase's rows of the basket are bought (flow.phase_kept), under the same yes and batch total, the
    checkout's chat_yes naming it; with `places` or `leave_places` (comma lists, the door's `--place` and
    `--leave-place`) only the rows place_left keeps; with `take_cheap` (euros, the door's `--take-cheap`) a row the
    run would also buy, priced under it, is taken into the basket in place of a refusal (flow.cheap_taken). Refused
    before the yes is marked used, nothing written."""
    from score.review import web
    store = store or state.source().store
    yes = yes_found(store, yes_id)
    if phase:
        yes = {**yes, "phase": known_phase(phase)}
    if take_cheap is not None:
        if take_cheap <= 0:
            raise Refused(f"--take-cheap {take_cheap:g}: give the euros a row may cost each, above 0")
        yes = {**yes, "take_cheap": take_cheap}
    if leave_out:  # stages this Buy leaves out beside the yes's own (2026-11-06: sim-body until its fixes land)
        yes = {**yes, "leave_out": [*yes.get("leave_out", ()), *known_stages(leave_out)]}
    approved = approved_now()  # the design's approval now, as the basket below is the runner's plan now
    print(relations_kept(places))  # before it plans: the scene record lays each object by these relations
    try:
        # what the runner's plan buys now at the approved places, never an older pass's basket; only the asked
        # phase's and places' rows, as `score plan --phase --place` plans them
        flow.basket_made(phase=yes.get("phase"), places=places)
    except flow.Refused as refused:
        raise Refused(str(refused)) from refused
    now_basket = current_basket(approved)
    if places or leave_places:  # a Buy by place (the door's --place, --leave-place), its left-out nodes on the yes
        items = flow.phase_kept(flow.left_out(flow.bought_items(now_basket["items"])[0], yes.get("leave_out", ())),
                                phase)
        yes = {**yes, "places": places, "leave_places": leave_places,
               "place_left": place_left(items, places, leave_places)}
    totals = basket_totals(now_basket, yes.get("leave_out", ()), phase, yes.get("place_left", ()))  # flow.start again
    refused = flow.yes_refusals(yes, totals) + latch_refusals() + pin_refusals(health.code()) + run_refusals()
    if refused:
        raise Refused("; ".join(refused))
    if not yes.get("retry"):
        try:
            web.buy_yes_spent(store, yes_id, {"at": now(), "basket": now_basket})
        except FileExistsError:
            raise Refused(f"the yes {yes_id} was used already: one yes launches one checkout; ask him again") from None
    owner, _ = get_user_model().objects.get_or_create(username=yes["by"])
    with web.as_owner_under(store, yes_id):
        return flow.start(owner, key_of(yes_id, yes.get("retry", 0)), True, now_basket["items"], at_once=True,
                          yes=yes)
