"""The launch basket's plan and its guard: queued steps grouped into the fewest runner commands, each group planned
by the compute backend, priced by the runner (`score price` through the backend, summed by checkout/pricing: the
runner is the only pricer, ADR-0006) against the environment's stop line, and every launch check in words.

Never starts what cannot finish under the stop: the plan's high estimate must fit the room left (ceiling - spent -
reserved). The runner's own per-node clearance stays the authority; this is the basket-level guard before it.
"""
import datetime
import hashlib
import json
import threading

from django.conf import settings
from django.utils import timezone

from score.dashboard.checkout import pricing
from score.dashboard.launch.backend import RunGroup, load

PLAN_MINUTES = 15
REBUY_LIMIT = 5.0
DEFAULT_JOBS = pricing.DEFAULT_JOBS
MONTH_UNSET = "the month's stop is not set (on the money card): nothing launches without it"
_planning = threading.Lock()
_launching = threading.Lock()


def backend():
    return load(settings.SCORE_COMPUTE_BACKEND)


def month_file():
    return settings.SCORE_HOME / "month-stop.json"


def month_record():
    """The owner's month's stop as he set it on the cockpit ({euros, by, at}), kept on the store's machine, or None."""
    path = month_file()
    return json.loads(path.read_text()) if path.exists() else None


def month_stop():
    """The month's stop that switches launching on and caps the runner's month, in euros as text: the owner's figure
    from the cockpit (month_record), else SCORE_MONTH_EUROS; None when neither is set."""
    record = month_record()
    return f"{record['euros']:g}" if record else settings.SCORE_MONTH_EUROS


def basket_hash(items):
    """The hash of the basket's (place, stage) pairs, so a plan knows when the basket changed under it."""
    pairs = sorted((item.place or "", item.stage) for item in items)
    return hashlib.sha256(json.dumps(pairs).encode()).hexdigest()


def run_groups(items, world="world1"):
    """The basket as runner groups: places with identical stage sets together; environment stages as one group."""
    by_place = {}
    for item in items:
        by_place.setdefault(item.place or "", set()).add(item.stage)
    found = {}
    for place, staged in by_place.items():
        if place:
            found.setdefault(tuple(sorted(staged)), []).append(place)
    groups = [RunGroup(places=tuple(sorted(places)), stages=staged, world=world) for staged, places in found.items()]
    if "" in by_place:
        groups.append(RunGroup(places=(), stages=tuple(sorted(by_place[""])), world=world))
    return sorted(groups, key=lambda group: (group.places, group.stages))


def group_body(group, planned):
    return {"places": list(group.places), "stages": list(group.stages), "missing": planned.missing,
            "buys": planned.buys, "refusal": planned.refusal, "to_run": planned.to_run, "blocked": planned.blocked}


def unique_buys(groups):
    """Each paid node once across the groups (an environment node two groups read is bought once)."""
    found = {}
    for group in groups:
        for buy in group["buys"]:
            found.setdefault(buy["node"], buy)
    return list(found.values())


def plan_body(items, chosen, jobs=DEFAULT_JOBS, world="world1"):
    """Work out the plan of a basket: each group's runner plan, its buys priced by the runner, the money against the
    stop and the time. High is what the runner clears (pricing.cleared_high: the unmeasured nodes' estimates in it)."""
    groups = [group_body(group, chosen.plan(group)) for group in run_groups(items, world)]
    buys = unique_buys(groups)
    totals = pricing.totals(chosen.price(world, [buy["node"] for buy in buys]) if buys else {}, jobs)
    spend = chosen.spend()
    nodes = sorted({node for group in groups for node in [*group["to_run"], *(buy["node"] for buy in group["buys"])]})
    ceiling = spend.ceiling  # the environment's stop line; SCORE_MONTH_EUROS only switches launching on, never raises it
    room = None if None in (ceiling, spend.spent, spend.reserved) else round(ceiling - spend.spent - spend.reserved, 2)
    return {"groups": groups, "buys": buys, "jobs": jobs, "nodes": nodes,
            "money": {"high": pricing.cleared_high(totals), "likely": totals["likely_euros"],
                      "guessed": totals["guessed_euros"], "not_measured": totals["unmeasured"], "spent": spend.spent,
                      "reserved": spend.reserved, "ceiling": ceiling, "room": room, "as_of": spend.as_of, "note": spend.note},
            "time": {"likely_minutes": totals["likely_minutes"], "high_minutes": totals["high_minutes"]},
            "rebuys": round(sum(float(buy["euros"]) for buy in buys if buy.get("again")), 2)}


def work_out(plan, items, chosen=None):
    """Fill a Plan row (state working) with its body, in this thread; one plan at a time."""
    with _planning:
        try:
            plan.body = plan_body(items, chosen or backend(), plan.body.get("jobs", DEFAULT_JOBS))
            plan.state = "ready"
        except Exception as error:  # the page shows why the plan could not be worked out
            plan.state, plan.error = "failed", f"{type(error).__name__}: {error}"
        plan.finished = timezone.now()
        plan.save()
    return plan


def work_out_soon(plan, items):
    """work_out in a background thread."""
    threading.Thread(target=work_out, args=(plan, list(items)), daemon=True).start()


def unseen_words(unseen):
    """The paid steps held because the owner has not advanced what they read, in words."""
    if not unseen:
        return []
    shown = ", ".join(f"{paid} (reads {read})" for paid, read in unseen[:6])
    return [f"not seen by owner: look at and advance what these paid steps read first: {shown}"
            f"{' ...' if len(unseen) > 6 else ''}"]


def refusals(plan, user_is_owner, current_hash, running, confirmed, rebuy_reason, unseen=(), now=None):
    """Every reason a launch of `plan` is refused, in words; empty when it may start. `unseen`: (paid node, read
    node) pairs the owner has not advanced (pages/seen.py), each one holding the launch."""
    now = now or timezone.now()
    found = []
    if not user_is_owner:
        found.append("only the owner launches")
    if settings.SCORE_MODE != settings.LOCAL:
        found.append("this dashboard is hosted: a launch is queued for the store's machine, not started here")
    if not settings.SCORE_STORE_WRITABLE:
        found.append("the store is read-only here (SCORE_STORE_WRITABLE=0)")
    if not month_stop():
        found.append(MONTH_UNSET)
    if plan.state != "ready":
        found.append("the plan is not worked out")
        return found
    if now - plan.finished > datetime.timedelta(minutes=PLAN_MINUTES):
        found.append(f"the plan is older than {PLAN_MINUTES} minutes: work it out again")
    if plan.basket_hash != current_hash:
        found.append("the basket changed since the plan: work it out again")
    found += money_refusals(plan.body)
    found += unseen_words(list(unseen))
    if any(group["refusal"] for group in plan.body["groups"]) and not (rebuy_reason or "").strip():
        found.append(f"it buys accepted outputs again for EUR {plan.body['rebuys']:.2f}, over EUR {REBUY_LIMIT:.0f}: "
                     "write the reason")
    if running:
        found.append("another launch from this dashboard is still running")
    if not confirmed:
        found.append("tick \"I launch this\"")
    return found


def money_refusals(body):
    """The plan's missing inputs and its high estimate against the room under the stop, in words."""
    found = []
    missing = sorted({item for group in body["groups"] for item in group["missing"]})
    if missing:
        found.append(f"inputs are missing: {', '.join(missing[:5])}{' ...' if len(missing) > 5 else ''}")
    money = body["money"]
    if money["room"] is None:
        found.append(f"no room under a stop is known: {money.get('note') or 'the spend could not be read'}")
    elif money["high"] > money["room"]:
        found.append(f"cannot finish under the stop: high EUR {money['high']:.2f}, room EUR {money['room']:.2f}")
    return found


def launch(record, plan, chosen=None):
    """Start each group of the plan through the backend, in this thread; the Launch row updated."""
    chosen = chosen or backend()
    with _launching:
        handles = []
        for group in run_groups_of(plan.body):
            handle = chosen.launch(group, record.jobs, record.rebuy_reason or None)
            handles.append({"command": handle.command, "pid": handle.pid, "log": handle.log,
                            "refused": handle.refused, "places": list(group.places), "stages": list(group.stages)})
        record.handles = handles
        record.state = "refused" if all(item["refused"] is not None for item in handles) else "running"
        record.result = "\n".join(item["refused"] for item in handles if item["refused"])
        record.save()
    return record


def run_groups_of(body):
    return [RunGroup(places=tuple(group["places"]), stages=tuple(group["stages"])) for group in body["groups"]]


def launch_soon(record, plan):
    threading.Thread(target=launch, args=(record, plan), daemon=True).start()


def polled(record, chosen=None):
    """The Launch row's state from its handles: refused, running while any runs, else failed or stopped if any
    did, else done; each handle's result and log tail kept."""
    from score.dashboard.launch.backend import LaunchHandle
    if record.state in ("starting", "refused"):
        return record
    chosen = chosen or backend()
    states = []
    for item in record.handles:
        found = chosen.poll(LaunchHandle(command=item["command"], pid=item["pid"], log=item["log"],
                                         refused=item["refused"]))
        item.update(state=found.state, result=found.result, log_tail=found.log_tail)
        states.append(found.state)
    for state in ("running", "failed", "stopped", "refused"):
        if state in states:
            record.state = state
            break
    else:
        record.state = "done"
    record.result = "\n".join(item.get("result") or "" for item in record.handles).strip()
    record.save()
    return record
