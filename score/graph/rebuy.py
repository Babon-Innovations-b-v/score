"""What a run would buy, before it starts paid work, and the refusal of a dear re-buy without its reason.

    bought = rebuy.buys(runner, nodes)    # [Buy], in table order: every paid node the drive would make
    rebuy.refusal(bought, reason)         # why the run is refused, or None

Worked out against the store, running nothing: a node is made when it has no record on its current key, or when a
node it reads will be made and may give another output. A paid one is a re-buy when it already has an accepted
output; a node never made before is a plain buy. Each counts at its estimate (`Stage.euros`), except a Google row
that would ask exactly what its accepted output asked (same_requests): google_spend's cache answers it, EUR 0, and
its output stays the same, so nothing after it is made for it. Over LIMIT in re-buys a run is refused unless it gives
a reason (`score run ... --rebuy-reason "<text>"`), written to the run's log and the cloud ledger. Why: on 2026-10-12
one library change re-rendered every place and re-drew every view map, about EUR 50, with nothing saying so first.
"""
import datetime
import subprocess
from dataclasses import dataclass

from score import review
from score.graph import Blocked, _code, code_functions, node_name

LIMIT = 5.0
GOOGLE = _code.REPO / "tools/props/cloud/google_spend.py"
# The files a Google row's request bodies are built from (wording, models, settings), besides its inputs. google_spend's
# cache key is pinned by google_spend_test, so google_spend.py itself changes no request.
REQUEST_BUILDERS = ("score/stages/surfaces/finish_ask.py", "tools/props/cloud/gemini_judge.py",
                    "tools/props/closeup/pro.py", "score/adapters/models/__init__.py")
SAME_PARTS = ("contract", "expects", "params", "seed", "files", "after", "models")
OWN_PARTS = ("code", "contract", "expects", "params", "seed", "files", "models")


@dataclass
class Buy:
    node: str
    euros: float
    why: str
    again: bool  # it has an accepted output: a re-buy


def builders_changed(commit):
    """True when a request builder differs between `commit` and the working tree (or git cannot tell)."""
    found = subprocess.run(["git", "-C", str(_code.REPO), "diff", "--quiet", commit, "--", *REQUEST_BUILDERS],
                           capture_output=True)
    return found.returncode != 0


def accepted_record(runner, node):
    """The finish record of the node's accepted output, or None."""
    accepted = runner.store.accepted(node)
    return review.record_of(runner.store, node, accepted) if accepted else None


def asks_google(stage):
    """True for a stage whose code asks Google (it imports google_spend)."""
    return GOOGLE in _code.source_files(code_functions(stage))


def same_requests(runner, stage, node, parts):
    """True when a Google row made again would send exactly the requests its accepted output sent: every key part
    but its code is the same, and none of REQUEST_BUILDERS changed since the commit it was made at (a record made
    from a tree with changes not committed cannot say, so it counts as changed)."""
    if not parts or not asks_google(stage):
        return False
    record = accepted_record(runner, node)
    if record is None or record.get("uncommitted", True) or not record.get("commit"):
        return False
    if any(record.get(part, {}) != parts.get(part, {}) for part in SAME_PARTS):
        return False
    return not builders_changed(record["commit"])


def to_make(runner, stage, place, pending, remade):
    """The node's key parts when a drive would make it, else None: it has no record on its current key; or a node it
    reads is made first and may give another output ({}: its parts are known only then); or those are made again the
    same and its own parts moved from its accepted output's."""
    node = node_name(stage, place)
    try:
        keyed = runner.key(stage, place)
        return keyed if runner.store.record(node, keyed["key"]) is None else None
    except Blocked:  # it reads a node not made on its current inputs yet, or one that blocks it
        if not pending:
            return None
    if any(remade[name] for name in pending):
        return {}
    try:
        own = runner.own_parts(stage, place)
    except Blocked:
        return None
    record = accepted_record(runner, node)
    if record is None:
        return {**own, "after": {}}
    if all(record.get(part) == own[part] for part in OWN_PARTS):
        return None
    return {**own, "after": record["after"], **({"beside": record["beside"]} if "beside" in record else {})}


def buys(runner, nodes):
    """[Buy] of every paid node among `nodes` (in table order) a drive would make, running nothing."""
    found, remade = [], {}  # remade: {node made first: True when its output may change}
    with runner.still():
        for stage, place in nodes:
            node = node_name(stage, place)
            pending = [name for name in (node_name(*before) for before in runner.read_nodes(stage, place))
                       if name in remade]
            parts = to_make(runner, stage, place, pending, remade)
            if parts is None:
                continue
            cached = stage.paid and same_requests(runner, stage, node, parts)
            remade[node] = not cached
            if stage.paid:
                moving = [name for name in pending if remade[name]]
                why = (f"reads {', '.join(moving)}" if not parts
                       else ", ".join(runner.stale_reasons(stage, place, parts)))
                found.append(Buy(node, 0.0 if cached else float(stage.euros or 0),
                                 why + ("; the same Google requests: cached" if cached else ""),
                                 runner.store.accepted(node) is not None))
    return found


def listing(bought):
    """The lines a run prints before it starts: each paid node it would buy, and the totals."""
    again = sum(buy.euros for buy in bought if buy.again)
    lines = [f"  {'re-buy' if buy.again else 'buy'} {buy.node}: EUR {buy.euros:.2f} ({buy.why})" for buy in bought]
    return "\n".join([f"paid rows this run would buy: {len(bought)}, about EUR {sum(b.euros for b in bought):.2f}; "
                      f"re-buys of accepted outputs: {sum(b.again for b in bought)}, about EUR {again:.2f}", *lines])


def refusal(bought, reason):
    """Why the run is refused (re-buys over LIMIT and no reason given), or None."""
    again = sum(buy.euros for buy in bought if buy.again)
    if again > LIMIT and not (reason or "").strip():
        return (f"refused: this run would buy accepted outputs again for about EUR {again:.2f}, over EUR {LIMIT:.0f}. "
                f"Run again with --rebuy-reason \"<why they are bought again>\" if it should.")
    return None


def ledger_entry(bought, reason):
    """The cloud ledger's line for a run that re-buys with its reason (no cost of its own: the runs it clears are
    on the ledger as they finish)."""
    return {"started": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "kind": "rebuy",
            "euros": 0, "reason": reason, "estimate": round(sum(buy.euros for buy in bought if buy.again), 2),
            "rebuys": {buy.node: buy.euros for buy in bought if buy.again}}
