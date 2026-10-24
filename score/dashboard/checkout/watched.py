"""The newest checkout as the run monitor reads it (state/batch_run.py), on the store's machine: its record, its launch
polled (launch/guard.polled: the run's state from its log and process) and every row its run plans, as plain data.
Read only, but for the Launch row's state, which polling keeps (the dashboard's own SQLite)."""
from score.dashboard.launch import guard
from score.dashboard.pages.models import Checkout


def planned_nodes(plan_body):
    """Every row the batch's run plans, bought or free, in the order the runner's plan lists them: what it makes now
    (`to_run`), what waits on earlier rows (`blocked`) and what it buys."""
    found = {}
    for group in plan_body.get("groups", []):
        for node in [*group.get("to_run", {}), *group.get("blocked", {}), *(buy["node"] for buy in group.get("buys", []))]:
            found.setdefault(node, None)
    return list(found)


def launch_of(launch):
    """The launch polled, as plain data: {at, state, result, logs}; None for none."""
    if launch is None:
        return None
    launch = guard.polled(launch)
    return {"at": launch.at.isoformat(), "state": launch.state, "result": launch.result,
            "logs": [handle["log"] for handle in launch.handles if handle.get("log")]}


def newest():
    """The newest checkout, its launch and its run's planned rows (the bought rows alone before it launched), as
    plain data for batch_run.gathered; None before one."""
    record = Checkout.objects.select_related("launch__plan").first()
    if record is None:
        return None
    bought = sorted({node for item in record.items for node in item["nodes"]})
    planned = planned_nodes(record.launch.plan.body) if record.launch else []
    return {"checkout": record.pk, "at": record.at.isoformat(), "by": record.by, "state": record.state,
            "detail": record.detail, "totals": record.totals, "stop_line": record.stop_line,
            "launch": launch_of(record.launch), "nodes": planned or bought}
