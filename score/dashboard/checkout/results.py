"""What a checkout brought back, per item: each of its paid nodes with its forecast, what it really cost and how long
it took (the ledger lines its run wrote since the checkout), its gates' verdicts and whether its output is new, and
the item's real cost against its forecast. Read from the store (through the cockpit's index, so a new output shows
within its 60 s rebuild) and the ledger, never judged again here."""
import datetime

from score.dashboard import state
from score.dashboard.launch import guard


def since(record):
    """The checkout's time as the ledger writes its own: UTC, to the second."""
    return record.at.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def billed_by_node(record, chosen):
    """{node: (euros, minutes)} the ledger holds for the checkout's nodes since it was made."""
    nodes = sorted({node for item in record.items for node in item["nodes"]})
    found = {}
    for line in chosen.ledgered(nodes, since(record)):
        euros, minutes = found.get(line.node, (0.0, 0.0))
        found[line.node] = (euros + line.euros, minutes + (line.minutes or 0.0))
    return found


def verdicts(source, record):
    """[{check, answer, reason}] of the record's newest judgement."""
    judgement = source.judgement_of(record)
    if not judgement:
        return []
    return [{"check": name, "answer": verdict.get("answer"), "reason": verdict.get("reason", "")}
            for name, verdict in sorted(judgement.get("verdicts", {}).items())]


def finished_at(record):
    return datetime.datetime.fromisoformat(record["finished"]) if record.get("finished") else None


def made_since(source, node, at):
    """The newest finish record of the node made since `at`, accepted or not, or None."""
    found = [record for record in source.store.records(node) if (finished_at(record) or at) > at]
    return max(found, key=finished_at) if found else None


def node_result(source, node, price, before, billed, at):
    """One node's result: its forecast, real cost and time, the output made since the checkout (None while none
    is) and its gates."""
    shown = made_since(source, node, at)
    output = shown.get("output") if shown else None
    euros, minutes = billed.get(node, (None, None))
    return {"node": node, "forecast": price, "euros": euros, "minutes": minutes, "before": before,
            "output": output, "accepted": source.accepted_output(node), "new": bool(output) and output != before,
            "finished": shown.get("finished") if shown else None, "verdicts": verdicts(source, shown)}


def item_result(source, item, before, billed, at):
    """An item's nodes' results and its real cost against its forecast."""
    nodes = [node_result(source, node, price, before.get(node), billed, at)
             for node, price in sorted(item["nodes"].items())]
    real = [node["euros"] for node in nodes if node["euros"] is not None]
    return {"id": item["id"], "place": item["place"], "layers": item["layers"], "nodes": nodes, "forecast": item["totals"],
            "euros": round(sum(real), 2) if real else None,
            "minutes": round(sum(node["minutes"] or 0.0 for node in nodes), 1),
            "new_outputs": sum(node["new"] for node in nodes),
            "failed_gates": sum(any(verdict["answer"] == "fail" for verdict in node["verdicts"]) for node in nodes)}


def results(record, chosen=None):
    """{checkout, state, items, euros, forecast}: the checkout's results, each item apart and in total."""
    chosen = chosen or guard.backend()
    source, billed = state.source(), billed_by_node(record, chosen)
    items = [item_result(source, item, record.before, billed, record.at) for item in record.items]
    real = [item["euros"] for item in items if item["euros"] is not None]
    return {"checkout": record.pk, "state": record.state, "items": items, "forecast": record.totals,
            "euros": round(sum(real), 2) if real else None, "stop_line": record.stop_line}
