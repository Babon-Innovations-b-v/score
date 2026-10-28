"""What a run would buy, before it starts paid work, and the refusal of a dear re-buy without its reason.

    bought = rebuy.buys(runner, nodes)    # [Buy], in table order: every paid node the drive would make
    rebuy.refusal(bought, reason)         # why the run is refused, or None

Worked out against the store, running nothing: a node is made when it has no record on its current key, or when a
node it reads will be made and may give another output. A paid one is a re-buy when it already has an accepted
output; a node never made before is a plain buy. Each counts at its estimate (`Stage.euros`), except a Google row
that would ask exactly what its accepted output asked (same_requests): google_spend's cache answers it, EUR 0 but for
the requests its output dropped from the cache (UNCACHED, a rejected answer asked again), and with none dropped its
output stays the same, so nothing after it is made for it. Over LIMIT in re-buys a run is refused unless it gives
a reason (`score run ... --rebuy-reason "<text>"`), written to the run's log and the cloud ledger. Why: on 2026-10-12
one library change re-rendered every place and re-drew every view map, about EUR 50, with nothing saying so first.
"""
import datetime
import subprocess
from dataclasses import dataclass

from score import review
from score.graph import Blocked, _code, asks_cached, node_name

LIMIT = 5.0
# The files a Google row's request bodies are built from (wording, models, settings), besides its inputs. google_spend's
# cache key is pinned by google_spend_test, so google_spend.py itself changes no request.
REQUEST_BUILDERS = ("score/stages/surfaces/finish_ask.py", "tools/cloud/gemini_judge.py",
                    "tools/props/closeup/pro.py", "tools/props/closeup/stage.py", "tools/props/closeup/check.py",
                    "score/adapters/models/__init__.py",
                    "score/stages/surfaces/route_list.py", "score/stages/surfaces/route_recheck.py",
                    "score/stages/surfaces/route_ask.py", "score/stages/surfaces/scene_palette.py",
                    "score/stages/surfaces/scene_library.py", "tools/cloud/google_batch.py",
                    "score/stages/surfaces/body_faces.py")
# A Google row's output names here the euros of the requests it dropped from google_spend's cache (a rejected answer:
# score/stages/props/closeup_row.UNCACHED), so asking them again is priced at that, never at EUR 0.
UNCACHED = "google-uncached.json"
SAME_PARTS = ("contract", "expects", "params", "seed", "files", "after", "models")
OWN_PARTS = ("code", "contract", "expects", "params", "seed", "files", "models")


@dataclass
class Buy:
    node: str
    euros: float
    why: str
    again: bool  # it has an accepted output: a re-buy
    evidence: str = None  # a paid evidence gather on the node's output (Stage.gatherers), not the node's make


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
    """True for a stage whose code makes cached model asks (graph.asks_cached: google_spend.py is a framework file, so
    it is in no row's source files and looking for it there found none)."""
    return asks_cached(stage)


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


def uncached_euros(runner, node):
    """The euros a Google row asking its accepted output's requests again still spends: those its output dropped from
    google_spend's cache (UNCACHED, the close-up's rejected pictures, owner 2026-10-24), else EUR 0."""
    found = runner.store.read_file(runner.store.accepted(node), UNCACHED) or {}
    return float(found.get("euros", 0.0))


KEPT = "kept"  # to_make: a node the drive keeps by a proof, made again the same


def to_make(runner, stage, place, pending, remade):
    """The node's key parts when a drive would make it, else None, or KEPT when the drive keeps its accepted output
    under its new key by a proof (the nodes after it then key on that output, as when made again the same): it has no
    record on its current key; or a node it reads is made first and may give another output ({}: its parts are known
    only then); or those are made again the same and its own parts moved from its accepted output's."""
    node = node_name(stage, place)
    if any(remade[name] for name in pending if name.partition("@")[0] in stage.optional):
        return {}  # an optional read made first is read once made (Runner.unsettled): its key is known only then
    try:
        keyed = runner.key(stage, place)
        if runner.store.record(node, keyed["key"]) is not None:
            return None
        if hasattr(stage.files, "carries") and stage.files.carries(runner, stage, place, keyed):
            return KEPT  # the runner keeps its accepted output under the new key (surfaces/carry.py)
        if runner.bytecode_proof(stage, place, keyed) or runner.narrowing_proof(stage, place, keyed) or \
                runner.no_op_proof(stage, place, keyed):
            return KEPT  # the runner keeps its accepted output: only bytecode moved its key (#67), its reads are as
            # they were when it was made, or a proof
        return keyed
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


def read_first(runner, nodes):
    """The nodes in table order, each moved after every node among them it reads (its optional reads too), as the drive
    makes them (a row the table lists before a row it reads, scene-record before plan, was judged before it and counted
    as not made)."""
    named = {node_name(stage, place): (stage, place) for stage, place in nodes}
    done, order = set(), []

    def visit(name, seen):
        if name in done or name in seen:
            return
        for before in runner.read_nodes(*named[name], every=True):
            if node_name(*before) in named:
                visit(node_name(*before), seen | {name})
        done.add(name)
        order.append(named[name])
    for stage, place in nodes:
        visit(node_name(stage, place), frozenset())
    return order


def held_for(runner, nodes, places):
    """{node: the places of `places` whose line holds it}: a place's own nodes and every node they read, directly or
    through another (optional reads too), as a run of that place makes them (Runner.line_nodes), so a node of a line
    no place given owns (the people's) names each place that reads it."""
    order = read_first(runner, nodes)
    found = {node_name(stage, place): {place} if place in places else set() for stage, place in order}
    for stage, place in reversed(order):  # every reader before what it reads
        for before in runner.read_nodes(stage, place, every=True):
            if node_name(*before) in found:
                found[node_name(*before)] |= found[node_name(stage, place)]
    return found


def evidence_buys(runner, stage, place, parts):
    """[Buy] of the node's paid evidence gathers a drive would make (Stage.gatherers with euros: the likeness's
    DINOv2, the assembly's drop run), each at its estimate: every one on an output the drive makes (`parts`, to_make's,
    not None nor KEPT), else those whose missing evidence alone keeps its current output from passing
    (Runner.gatherable). Buy of 2026-10-24: they were cleared and spent at run time, in no price the owner saw."""
    paid = {name: euros for name, (_, euros) in stage.gatherers.items() if euros}
    if not paid:
        return []
    node = node_name(stage, place)
    if parts is not None and parts is not KEPT:
        wanted, why = sorted(paid), "evidence on the output this run makes"
    else:
        try:
            wanted, why = [name for name in runner.gatherable(stage, place) if name in paid], "evidence missing"
        except Blocked:
            return []
    return [Buy(node, float(paid[name]), f"{why}: {name}", False, name) for name in wanted]


def buys(runner, nodes):
    """[Buy] of every paid node among `nodes` (in table order) a drive would make, running nothing."""
    found, remade = [], {}  # remade: {node made first: True when its output may change}
    rank = {node_name(stage, place): number for number, (stage, place) in enumerate(nodes)}
    with runner.still():
        for stage, place in read_first(runner, nodes):
            node = node_name(stage, place)
            pending = [name for name in (node_name(*before) for before in runner.read_nodes(stage, place, every=True))
                       if name in remade]
            parts = to_make(runner, stage, place, pending, remade)
            found += evidence_buys(runner, stage, place, parts)
            if parts is None:
                continue
            if parts is KEPT:  # its readers key on the kept output once the drive keeps it (greenhouse, 2026-10-24)
                remade[node] = False
                continue
            cached = stage.paid and same_requests(runner, stage, node, parts)
            asked_again = uncached_euros(runner, node) if cached else 0.0  # a redrawn answer may change its output
            remade[node] = not cached or asked_again > 0
            if stage.paid:
                moving = [name for name in pending if remade[name]]
                why = (f"reads {', '.join(moving)}" if not parts
                       else ", ".join(runner.stale_reasons(stage, place, parts)))
                found.append(Buy(node, asked_again if cached else float(stage.euros or 0),
                                 why + ("; the same Google requests: cached" if cached else ""),
                                 runner.store.accepted(node) is not None))
    return sorted(found, key=lambda buy: rank[buy.node])


def listing(bought):
    """The lines a run prints before it starts: each paid node it would buy, and the totals."""
    again = sum(buy.euros for buy in bought if buy.again)
    lines = [f"  {'re-buy' if buy.again else 'buy'} {buy.node}{f' evidence {buy.evidence}' if buy.evidence else ''}: "
             f"EUR {buy.euros:.2f} ({buy.why})" for buy in bought]
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
