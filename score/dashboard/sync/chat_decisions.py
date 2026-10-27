"""The owner's decisions made in a Claude Code session (root CLAUDE.md, owner 2026-10-27: "i hate the rule that i cant
make discisions in chat aswell"), applied exactly like his click. The session asks him with its question tool, naming
what the decision applies to; his yes is recorded here, quoted, and applied once through the request code his cockpit
click makes on the store's machine (applying.apply, so every check of his click runs), never by writing store files.

    record(decision, target, answer, question, store, **given)
                        his yes {id, purpose "decide", decision, target, given, answer, question, at, by}, kept once in
                        the store (grants/decide/<id>.json, score.review.web): `target` what it applies to as it stands
                        at the question (state_of), `given` his words for it: reason, worse_reason, check
    apply(yes id, store)
                        his decision under that yes, once: refused when there is no quoted yes, it was used already
                        (grants/decide-used/<id>.json, written before it is applied, so a refused one needs a new
                        yes), it is a go (carried by its run, never applied here), or its target changed since the
                        question (another output accepted, another concept locked, the film's script edited), like a
                        changed basket refuses a Buy; then the cockpit's own request kind (request_of) by his name

Decisions and what each names: an accept or a reject names a node and one output, with the node's accepted output
then; a waiver a node, one output and its check; lock-concept a place and one draw's sha, with its lock then;
lock-film a film and the sha256 of its script as his editor shows it; go an environment: a run he started himself,
tagged score.review.web.OWNERS_GO, counts as a bought batch for review.IN_BATCH (owner, 2026-10-27, his "sure").

Reached from the agents' door (tools/cloud/conductor/agent_door.py `decide-yes`, `decide`) and, for a run on this PC,
tools/cloud/this_pc.py's own. The records are the cockpit's own (his accept, reject, waiver or lock by his name), so
the cockpit shows a decision made in chat as his. Agents never invent a yes: it is written only from the answer the
session's question tool got from him. A barrier, not a lock.
"""
import datetime
import hashlib
import json

from django.conf import settings
from django.http import Http404

from score import review
from score.dashboard import state
from score.dashboard.sync import applying

DECISIONS = ("accept", "reject", "waive", "lock-concept", "lock-film", "go")


class Refused(RuntimeError):
    """A decision yes that may not be recorded, or applied, with why."""


def output_state(store, node, output):
    """{node, output, accepted}: the output as it stands; Refused when the store has no such output."""
    if not output or review.record_of(store, node, output) is None:
        raise Refused(f"{node} has no output {str(output)[:12] or '(none named)'} here")
    return {"node": node, "output": output, "accepted": store.accepted(node)}


def concept_state(store, place, sha):
    """{place, sha, locked}: the draw and the place's lock as they stand."""
    from score.review import concepts
    if not sha:
        raise Refused("a concept lock names the draw's sha")
    return {"place": place, "sha": sha, "locked": concepts.picked(store, place)}


def film_script(film):
    """The film's script as his editor shows it (pages/films.script_or_404); Refused when it has none."""
    from score.dashboard.pages import films
    try:
        return films.script_or_404(film)[0]
    except Http404 as missing:
        raise Refused(f"no film script {film}: {missing}") from None


def script_sha(found):
    return hashlib.sha256(json.dumps(found, sort_keys=True).encode()).hexdigest()


def state_of(decision, target, given, store):
    """What the decision applies to as it stands now; the same call at the question and at the apply."""
    if decision in ("accept", "reject"):
        return output_state(store, target, given.get("output"))
    if decision == "waive":
        if not given.get("check"):
            raise Refused("a waiver names the check it waives")
        return {**output_state(store, target, given.get("output")), "check": given["check"]}
    if decision == "lock-concept":
        return concept_state(store, target, given.get("sha"))
    if decision == "lock-film":
        return {"film": target, "script": script_sha(film_script(target))}
    return {"world": target}


def record(decision, target, answer, question, store=None, **given):
    """Write his quoted yes to one decision on `target` as it stands now; the yes. Refused without an owner here, an
    answer and a question both, a decision of DECISIONS, a reason for a reject or waiver, or a target as named."""
    from score.review import web
    if not str(answer or "").strip() or not str(question or "").strip():
        raise Refused("a decision made in chat quotes the owner's answer and the question he answered, both")
    if not settings.SCORE_OWNER:
        raise Refused("no owner is set here (SCORE_OWNER)")
    if decision not in DECISIONS:
        raise Refused(f"a decision is one of {', '.join(DECISIONS)}, not {decision!r}")
    if decision in ("reject", "waive") and not str(given.get("reason") or "").strip():
        raise Refused(f"a {decision} says why, in his words: --reason")
    store = store or state.source().store
    given = {name: value for name, value in given.items() if value}
    moment = datetime.datetime.now(datetime.timezone.utc)
    return web.decision_yes_written(store, {
        "id": moment.strftime("%Y%m%dT%H%M%S%fZ"), "at": moment.isoformat(timespec="seconds"), "purpose": "decide",
        "decision": decision, "target": state_of(decision, target, given, store), "given": given,
        "answer": str(answer), "question": str(question), "by": settings.SCORE_OWNER})


def request_of(yes):
    """The cockpit request his click makes for this decision: {kind, user, payload}, as applying.apply takes it."""
    target, given, user = yes["target"], yes.get("given") or {}, yes["by"]
    if yes["decision"] in ("accept", "reject"):
        return {"kind": "decision", "user": user, "payload": {
            "node": target["node"], "output": target["output"], "decision": yes["decision"],
            "reason": given.get("reason", ""), "worse_reason": given.get("worse_reason", "")}}
    if yes["decision"] == "waive":
        return {"kind": "waiver", "user": user, "payload": {
            "node": target["node"], "output": target["output"], "check": target["check"],
            "reason": given.get("reason", "")}}
    if yes["decision"] == "lock-concept":
        return {"kind": "concept-pick", "user": user, "payload": {"place": target["place"], "sha": target["sha"]}}
    return {"kind": "film-lock", "user": user, "payload": {"film": target["film"],
                                                          "script": film_script(target["film"])}}


def target_name(yes):
    target = yes["target"]
    return target.get("node") or target.get("place") or target.get("film") or target.get("world")


def refusal(yes, yes_id, store):
    """Why the yes `yes_id` may not be applied now, in words, or None."""
    from score.review import web
    if not yes or yes.get("purpose") != "decide" or not yes.get("answer") or not yes.get("question"):
        return f"{yes_id} is no quoted decision yes: ask him with the question tool and record his answer first"
    if yes["decision"] == "go":
        return f"{yes_id} is a go: its run carries it ({web.OWNERS_GO}={yes_id}), nothing is applied here"
    if web.decision_yes_used(store, yes_id):
        return f"the yes {yes_id} was used already: one yes, one decision; ask him again"
    try:
        now = state_of(yes["decision"], target_name(yes), {**(yes.get("given") or {}), **yes["target"]}, store)
    except Refused as gone:
        return f"what he decided on is gone since the question: {gone}"
    if now != yes["target"]:
        return (f"{target_name(yes)} changed since he answered at {yes['at']} (then {yes['target']}, now {now}): a "
                "changed target needs a new yes")
    return None


def apply(yes_id, store=None):
    """His decision under the yes `yes_id`, once (module docstring); the Applied of the cockpit's own request code.
    Refused before the yes is marked used, nothing written."""
    from score.review import web
    source = state.source()
    store = store or source.store
    yes = web.decision_yes(store, yes_id)
    why = refusal(yes, yes_id, store)
    if why:
        raise Refused(why)
    request = request_of(yes)
    try:
        web.decision_yes_spent(store, yes_id, {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(
            timespec="seconds"), "request": {"kind": request["kind"], "user": request["user"]}})
    except FileExistsError:
        raise Refused(f"the yes {yes_id} was used already: one yes, one decision; ask him again") from None
    with web.as_owner_deciding(store, yes_id):
        return applying.apply(request, source)
