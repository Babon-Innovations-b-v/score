"""The newest checkout, a try of its batch, as the run monitor reads it (state/batch_run.py), on the store's machine: its record, its launch
polled (launch/guard.polled: the run's state from its log and process) and every row its run plans, as plain data.
Read only, but for the Launch row's state, which polling keeps (the dashboard's own SQLite)."""
import datetime

from django.db.models import Q

from score.dashboard.launch import guard
from score.dashboard.pages.models import Checkout, Launch, Plan


def planned_nodes(plan_body):
    """Every row the batch's run plans, bought or free, in the order the runner's plan lists them: what it makes now
    (`to_run`), what waits on earlier rows (`blocked`) and what it buys."""
    found = {}
    for group in plan_body.get("groups", []):
        for node in [*group.get("to_run", {}), *group.get("blocked", {}), *(buy["node"] for buy in group.get("buys", []))]:
            found.setdefault(node, None)
    return list(found)


def checkout_plans(record):
    """The plans of every run of the checkout (their bodies name it; its launch's plan always counts), oldest first."""
    return Plan.objects.filter(Q(body__checkout=record.pk) | Q(pk=record.launch.plan_id)).order_by("started")


def checkout_runs(record):
    """Every launch of the checkout's runs as {at, logs}, oldest first: a relaunch's monitor adds up what each spent
    and times the batch from the first."""
    launches = Launch.objects.filter(plan__in=checkout_plans(record)).order_by("at")
    return [{"at": launch.at.isoformat(), "logs": [handle["log"] for handle in launch.handles if handle.get("log")]}
            for launch in launches]


def checkout_nodes(record):
    """Every row any run of the checkout planned (its plans name it; its launch's plan always counts), its first
    run's order first: a relaunch plans only what is not yet accepted, so the checkout's rows stay all of them."""
    found = {}
    for plan in checkout_plans(record):
        found.update(dict.fromkeys(planned_nodes(plan.body)))
    return list(found)


def launch_of(launch):
    """The launch polled, as plain data: {at, state, result, logs}; None for none."""
    if launch is None:
        return None
    launch = guard.polled(launch)
    return {"at": launch.at.isoformat(), "state": launch.state, "result": launch.result,
            "logs": [handle["log"] for handle in launch.handles if handle.get("log")]}


def record_nodes(record):
    """The rows a checkout's runs planned, its bought rows alone before it launched."""
    planned = checkout_nodes(record) if record.launch else []
    return planned or sorted({node for item in record.items for node in item["nodes"]})


def batch_ended(tries, record, accepted_at):
    """Whether `record` begins a new batch after the checkouts `tries` (owner, 2026-10-25: "its the same batch, ur
    just retrying a failed part of it"): every row they planned made since the first of them by the time it was made,
    or the design changed since the last of them (its `design_at`)."""
    start = tries[0].at
    nodes = {node for one in tries if one.launch for node in checkout_nodes(one)}
    made = bool(nodes) and all(start < (moment(accepted_at(node)) or start) <= record.at for node in nodes)
    return made or bool(record.design_at) and moment(record.design_at) > tries[-1].at


def moment(text):
    return datetime.datetime.fromisoformat(text) if text else None


def batch_of(records, accepted_at):
    """(batch number, its checkouts oldest first) of the newest of `records` (oldest first): a checkout is another
    try of the batch before it until batch_ended."""
    number, tries = 0, []
    for record in records:
        if not tries or batch_ended(tries, record, accepted_at):
            number, tries = number + 1, []
        tries.append(record)
    return number, tries


def chat_words(yes):
    """{at, answer, question, high, total, stop} of a checkout's Buy approved in chat (checkout/chat_yes.py), for the
    pages: total the batch total he approved, stop a try's stop a yes before batch totals held; None for his click."""
    if not yes:
        return None
    return {"at": yes["at"], "answer": yes["answer"], "question": yes["question"], "high": yes["high_euros"],
            "total": yes.get("batch_total_euros"), "stop": yes.get("stop_euros")}


def batch_start(line):
    """The spend a batch counts from, by its first try's line: what it was written over; None for a line without."""
    if "batch_from" in line:
        return line["batch_from"]
    return None if line.get("spent") is None else line["spent"] + (line.get("reserved") or 0.0)


def batch_money(tries, spend):
    """The batch's money by the money guard's own measure (score.adapters.compute.guard: the environment's spend since
    its first stop line, each month the higher of the cloud bill's and the ledger's growth, plus the model calls'),
    the one spent figure the door, the Buy page and the monitor show (owner, 2026-10-26: "the stop should be a total
    of the batch, not per try, i have no clue now"): {start (the spend its first try's line was written over), spent (since
    then: every try, its pools and model calls, and whatever else was billed meanwhile: benchmarks, design calls,
    what the bill holds over the ledger), in_flight (cleared runs' forecasts not yet ledgered), budget (the batch
    total), left (budget less spent and in flight: what the guard still clears), parts (the environment's books since
    its first line, guard.spent_parts), as_of}; None before a try wrote its line or while the spend is unread.
    `tries` the batch's checkouts, oldest first; `spend` the backend's Spend."""
    lined = [one.stop_line for one in tries if "euros" in (one.stop_line or {})]
    start = batch_start(lined[0]) if lined else None
    if start is None or spend is None or spend.spent is None or spend.reserved is None:
        return None
    budget = next((line["batch_budget"] for line in reversed(lined) if "batch_budget" in line),
                  round(lined[-1]["euros"] - start, 2))
    spent = round(spend.spent - start, 2)
    return {"start": round(start, 2), "spent": spent, "in_flight": round(spend.reserved, 2), "budget": budget,
            "left": round(budget - spent - spend.reserved, 2), "parts": spend.parts, "as_of": spend.as_of}


def newest(accepted_at=lambda node: None, reading=lambda: None):
    """The newest checkout as a try of its batch (batch_of): its record and launch, every launch of every try's runs
    (checkout_runs) and the rows they plan, the rows this try makes (try_nodes), the batch's number, its tries and when its first try was made, as plain
    data for batch_run.gathered; None before one. `accepted_at(node)` the time of its standing accept; `reading()` the
    backend's Spend, for the batch's money (batch_money)."""
    records = list(Checkout.objects.select_related("launch__plan").order_by("at"))
    if not records:
        return None
    number, tries = batch_of(records, accepted_at)
    record = tries[-1]
    nodes = {}
    for one in tries:
        nodes.update(dict.fromkeys(record_nodes(one)))
    return {"checkout": record.pk, "at": record.at.isoformat(), "by": record.by, "yes": chat_words(record.chat_yes),
            "state": record.state,
            "detail": record.detail, "totals": record.totals, "stop_line": record.stop_line,
            "launch": launch_of(record.launch), "batch": number, "tries": len(tries),
            "first_at": tries[0].at.isoformat(),
            "runs": [run for one in tries if one.launch for run in checkout_runs(one)],
            "try_runs": checkout_runs(record) if record.launch else [], "nodes": list(nodes),
            "try_nodes": record_nodes(record),
            "money": batch_money(tries, reading())}
