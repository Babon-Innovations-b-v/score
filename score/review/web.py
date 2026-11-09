"""The owner's accept and reject from a signed-in web user (the dashboard, score/dashboard), beside his terminal's.

    web.decide(store, node, output, "accept", by="joey", reason="", worse_reason=None)
    web.decide(store, node, output, "reject", by="joey", reason="the lamp floats")
    web.stop(store, "world1", 412.5, "checkout 7: fix-sound, fix-film-cut", by="joey")   # his checkout's money yes
    web.waived(store, node, output, "resting", by="joey", reason="the cairn leans on purpose")
    web.google_month(120.0, by="joey")   # what Google billed this month before its ledger began again

The dashboard proves who the owner is by its own sign-in (the trusted proxy's single sign-on, or its owner account)
in place of the terminal check of `python -m score.review` (owner_at_terminal), and passes his user name as `by`.
`by` is never empty and never the runner's name: an accept by the runner skips the store's agent barrier. The store's
own barrier still refuses these writes in a process an agent started (Store.write_once), so a dashboard started from
an agent's shell records nothing. His waiver (`waived`, one check of the output he saw) and his Google month
(`google_month`, into the month's books, refused in an agent's process by compute itself, or his yes in a session)
come the same way; the
spend override (a yes for a run outside the runner, `spend_override`) comes from his terminal, his concept review's
draw button, or his yes in a session (chat_decisions, below).

    web.spend_override(store, "relight-hangar", 4.0, by="joey", purpose="one relight of the hangar")

    web.concept_draw(store, "airlock", {"marks": [...], "note": "", "base": sha}, 0.15, by="joey")
    web.concept_pick(store, "airlock", sha, by="joey")    # sha None: unlocked again
    web.concept_generated(store, "airlock", by="joey")    # his own wording dropped: worded from its data again
    web.environment_ask(store, "world1", {"topic": "style", "answer": "...", "concept": {...}}, 0.05, by="joey")
    web.environment_saved(store, "world1", concept, True, by="joey")   # his Save, Lock (True) or Unlock (False)
    web.environment_reference(store, "world1", png_bytes, "dock.png", "the dock's look", "hangar", by="joey")

`environment_ask` is his Send in the environment concept's set interview (CONTEXT.md "environment concept"): his yes
for that one model call at the price his Send showed, the same way as a concept draw.

`concept_draw` is his click on a concept review's Draw button (CONTEXT.md "concept review", owner 2026-10-20: the
click is the spend yes): his yes for exactly that one call at the price the button showed (refused when the measured
price moved since), written as an override (node `override`, key `concept-<place>-<time>`, its purpose said), then the
one draw run as its own process inside it (score/review/concepts.py). The store refuses the yes in an agent's process.

    web.plan_edit(store, "airlock", plan, by="joey")              # his plan kept as his own (plans.py)
    web.plan_named(store, "hangar", ["galley", "lab"], by="joey") # inside places named on the concept page
    web.plan_revise(store, "airlock", {"marks": [...], "note": ""}, 0.05, by="joey")   # his yes, then one Gemini call

`stop` is his money yes from the cockpit's checkout: the signed-in owner on the trusted cockpit counts as the owner
at his terminal (`python -m score.review stop`, C22), and the line is written by the same guard.set_line, which
refuses in any process an agent started, so no agent can trigger it by any route through here but one: his Buy
approved in a Claude Code session (root CLAUDE.md, owner 2026-10-25), his answer and the question quoted.

    web.buy_yes_written(store, yes)     # his quoted yes, grants/buy/<id>.json (score/dashboard/checkout/chat_yes.py)
    web.buy_yes_spent(store, yes_id, record)   # marked used once, grants/buy-used/<id>.json: one yes, one checkout
    with web.as_owner_under(store, yes_id): ...   # that one checkout run as his: the agent markers lifted

Every other owner-only decision may be made in a Claude Code session the same way (root CLAUDE.md, owner 2026-10-27:
"i hate the rule that i cant make discisions in chat aswell"): his quoted yes to one accept, reject, waiver, concept
lock, film lock, spend override or Google month (`books_of`: the books as they stood at the question), or his go
for a run (score/dashboard/sync/chat_decisions.py), applied once through the cockpit's own request code.

    web.decision_yes_written(store, yes)   # grants/decide/<id>.json
    web.decision_yes_spent(store, yes_id, record)   # grants/decide-used/<id>.json: one yes, one decision
    with web.as_owner_deciding(store, yes_id): ...   # that one decision applied as his: the agent markers lifted
    web.owners_go(store, go_id, world)     # his go for a run of `world` (a run tagged OWNERS_GO), or None
"""
import contextlib
import os

from score import graph, review
from score.store import AGENT_MARKERS, RUNNER

BUY_YESES, BUY_USED = "grants/buy", "grants/buy-used"
DECISION_YESES, DECISION_USED = "grants/decide", "grants/decide-used"
# A refused apply hands its yes back (2026-11-05: a film lock the cockpit refused, its script's captions out of date,
# left the owner's yes used, so the same yes could not be applied after the fix): one record an attempt, so the yes is
# used while its attempts outnumber what was handed back.
DECISION_RETURNED = "grants/decide-returned"
# A run the owner started himself, by his go recorded in a session (owner, 2026-10-27, his "sure"): it names the go's
# id, and the runner treats it as a bought batch for the in-batch accept (review.IN_BATCH).
OWNERS_GO = "SCORE_OWNERS_GO"
# The decision that enters his provider's month figure into the books (google_month), as a session names it; named
# here, outside the cockpit's package, which names no provider (score/dashboard overlay, "No provider here").
BOOKS_MONTH = "google-month"

DECISIONS = ("accept", "reject")


def checked_by(by):
    """The owner's user name, refused when empty or the runner's."""
    name = (by or "").strip()
    if not name or name == RUNNER:
        raise review.Refused(f"a decision needs the signed-in owner's own name, not {by!r}")
    return name


def decide(store, node, output, decision, by, reason="", worse_reason=None, takes=(), hand=False):
    """Record the owner's accept or reject of one output of a node, by his signed-in name; what was written.
    review.Refused when the output may not be taken so (it did not pass, it is worse with no reason, a reject with no
    reason, it is not the accepted output). `takes`: a reject's takes to remake (review.reject). `hand`: an accept
    starts the library handover of environment 1 (hand_accept), as the cockpit with a library does."""
    name = checked_by(by)
    if decision == "reject":
        return review.reject(store, node, output, name, reason, takes)
    if decision == "accept":
        written = review.accept(store, node, output, name, reason, worse_reason=worse_reason or None)
        if hand:
            hand_accept(store)
        return written
    raise review.Refused(f"a decision is one of {', '.join(DECISIONS)}, not {decision!r}")


def hand_accept(store, world="world1"):
    """Start the library handover after the owner's accept (score/stages/library/handed.py); its words. One that cannot
    start is said and left to the next sync pass: the accept stands either way."""
    from score.stages.library import handed
    try:
        return handed.start(store, world)
    except Exception as error:  # said in the words, the accept stands, status and the sync pass take it up
        return f"library handover not started: {type(error).__name__}: {error}"


def books_now():
    """The books as they stand ({month, bill, ledger, google}), read for an environment's first stop line only."""
    from score.adapters import compute
    return compute.books_now()


def stop(store, world, euros, reason, by, books=None, replaces=None):
    """Write the environment's new stop line at `euros` by the signed-in owner's name, his reason with it; the record. A
    environment's first line counts its spend from `books()` (default books_now). With `replaces` (the `at` of the
    line this one takes back), None and nothing written once the newest line is another. Read and written under one
    lock (guard.writing), its time taken inside it, so a try taking its line back never writes over the line the next
    try wrote meanwhile (2026-11-04: checkout 19's line under a closed one, the runner read room EUR -0.00).
    review.Refused for an empty or the runner's name; PermissionError in a process an agent started (guard.set_line)."""
    from score.adapters.compute import guard
    name = checked_by(by)
    with guard.writing(store, world):
        latest = guard.current(store, world)
        if replaces is not None and (latest or {}).get("at") != replaces:
            return None
        baseline = None if latest else (books or books_now)()
        return guard.set_line(store, world, euros, reason, name, graph.now(), baseline)


def buy_yes_written(store, yes):
    """Keep his Buy approved in a session once (grants/buy/<id>.json); the yes. review.Refused unless it quotes his
    answer and the question he answered."""
    if not str(yes.get("answer") or "").strip() or not str(yes.get("question") or "").strip():
        raise review.Refused("a Buy approved in chat quotes the owner's answer and the question he answered, both")
    store.write_once(f"{BUY_YESES}/{yes['id']}.json", yes)
    return yes


def buy_yes(store, yes_id):
    """His Buy yes `yes_id` as written, or None."""
    return store.read(f"{BUY_YESES}/{yes_id}.json")


def buy_yes_used(store, yes_id):
    """Whether the yes `yes_id` launched its one checkout already (or was spent on one that was refused)."""
    return store.objects.exists(f"{BUY_USED}/{yes_id}.json")


def buy_yes_spent(store, yes_id, record):
    """Mark the yes `yes_id` used, once (`record` what it was spent on); FileExistsError when it was already."""
    store.write_once(f"{BUY_USED}/{yes_id}.json", record)


@contextlib.contextmanager
def as_owner_under(store, yes_id):
    """This process as the owner's own for the one checkout his yes `yes_id` covers, once it is marked used
    (buy_yes_spent): the agent markers lifted, so guard.set_line writes his line, and put back after.
    PermissionError for a yes not marked used."""
    if not buy_yes(store, yes_id) or not buy_yes_used(store, yes_id):
        raise PermissionError(f"no spent Buy yes {yes_id}: only his quoted yes, marked used, runs his checkout")
    with markers_lifted():
        yield


@contextlib.contextmanager
def markers_lifted():
    """The agent markers taken off this process, and put back after."""
    kept = {name: os.environ.pop(name) for name in AGENT_MARKERS if name in os.environ}
    try:
        yield
    finally:
        os.environ.update(kept)


def decision_yes_written(store, yes):
    """Keep his decision approved in a session once (grants/decide/<id>.json); the yes. review.Refused unless it
    quotes his answer and the question he answered."""
    if not str(yes.get("answer") or "").strip() or not str(yes.get("question") or "").strip():
        raise review.Refused("a decision made in chat quotes the owner's answer and the question he answered, both")
    store.write_once(f"{DECISION_YESES}/{yes['id']}.json", yes)
    return yes


def decision_yes(store, yes_id):
    """His decision yes `yes_id` as written, or None."""
    return store.read(f"{DECISION_YESES}/{yes_id}.json")


def decision_attempts(store, yes_id):
    """(the attempts made under the yes `yes_id`, those handed back after a refused apply)."""
    first = int(store.objects.exists(f"{DECISION_USED}/{yes_id}.json"))
    later = len(list(store.objects.keys(f"{DECISION_USED}/{yes_id}/")))
    return first + later, len(list(store.objects.keys(f"{DECISION_RETURNED}/{yes_id}/")))


def decision_yes_used(store, yes_id):
    """Whether the yes `yes_id` is used: applied, or being applied now (an attempt not handed back)."""
    made, handed_back = decision_attempts(store, yes_id)
    return made > handed_back


def decision_yes_spent(store, yes_id, record):
    """Mark the decision yes `yes_id` used for one attempt, once each (the first at DECISION_USED/<id>.json, a later
    one after a refused apply handed it back at DECISION_USED/<id>/<n>.json); FileExistsError when it is used now."""
    made, handed_back = decision_attempts(store, yes_id)
    if made > handed_back:
        raise FileExistsError(f"{DECISION_USED}/{yes_id}")
    store.write_once(f"{DECISION_USED}/{yes_id}.json" if made == 0 else f"{DECISION_USED}/{yes_id}/{made + 1}.json",
                     record)


def decision_yes_returned(store, yes_id, record):
    """Hand the yes `yes_id` back after its apply was refused, nothing decided: the attempt it is used for now gets a
    record of why (DECISION_RETURNED/<id>/<n>.json), so the same yes may be applied again; FileExistsError when it is
    not used now."""
    made, handed_back = decision_attempts(store, yes_id)
    if made <= handed_back:
        raise FileExistsError(f"{DECISION_RETURNED}/{yes_id}: not used now")
    store.write_once(f"{DECISION_RETURNED}/{yes_id}/{made}.json", record)


@contextlib.contextmanager
def as_owner_deciding(store, yes_id):
    """This process as the owner's own for the one decision his yes `yes_id` covers, once it is marked used
    (decision_yes_spent): the agent markers lifted, so the store takes his accept, reject, waiver or lock, and put back
    after. PermissionError for a yes not marked used."""
    if not decision_yes(store, yes_id) or not decision_yes_used(store, yes_id):
        raise PermissionError(f"no spent decision yes {yes_id}: only his quoted yes, marked used, applies his decision")
    with markers_lifted():
        yield


def owners_go(store, go_id, world):
    """His go recorded in a session for a run of `world` (a decision yes of decision "go"), or None."""
    yes = decision_yes(store, go_id) if go_id else None
    if yes and yes.get("decision") == "go" and (yes.get("target") or {}).get("world") == world:
        return yes
    return None


def google_month(euros, by):
    """Write the owner's Google month into the month's books by his signed-in name (compute.owners_google_month, his
    `score spend --google-month` from the cockpit); the books. review.Refused for an empty or the runner's name, in a
    process an agent started and for a figure that is not finite and at least 0 (compute's refusal, in its words)."""
    from score.adapters import compute
    name = checked_by(by)
    try:
        return compute.owners_google_month(euros, by=name)
    except compute.Refused as refused:
        raise review.Refused(str(refused)) from refused


def books_of(month):
    """(this month, the books as written for `month`): the month as YYYY-MM, in UTC like the ledger's times, and the
    month's books ({} when none were written for `month`)."""
    from score.adapters import compute
    books = compute.ledger()
    found = books.read_books()
    return books.this_month(), (found if found.get("month") == month else {})


def waived(store, node, output, check, by, reason):
    """The owner's waiver of one check of the output he saw, under that output's key, by his signed-in name; the
    waiver. review.Refused when the output has no record here, the check was not judged or the reason is empty;
    PermissionError in a process an agent started (the store's own barrier)."""
    name = checked_by(by)
    record = review.record_of(store, node, output)
    if record is None:
        raise review.Refused(f"{node} has no output {output[:12]} here")
    return review.waive(store, node, record["key"], check, name, reason)


def spend_override(store, name, euros, by, purpose):
    """The owner's override yes for one run outside the runner under `name` (node `override`, the run carrying
    SCORE_SPEND_TICKET="override <name>"), at his euros and for his purpose, by his signed-in name; the yes.
    FileExistsError when the name holds a yes already; PermissionError in a process an agent started (the store's own
    barrier)."""
    from score.adapters import compute
    return review.spend(store, compute.OVERRIDE, name, euros, checked_by(by), purpose=purpose)


def override_yes(store, name):
    """His override yes under `name` as written, or None."""
    from score.adapters import compute
    return store.spend_yes(compute.OVERRIDE, name)


def cap_now(name):
    """The newest record of the cap `name` (env1's, guard.current_cap in the SCORE object store), or None."""
    from score.adapters.compute import guard
    return guard.current_cap(guard.cap_book(), name)


def cap_figure(name="env1"):
    """The cap `name`'s spend for the pages, from the same records its guard reads (guard.current_cap and the
    watcher's newest reading in the SCORE object store): {name, euros (the owner's cap), line (its stop), counter (the
    newest reading's: the whole bill, every project, less babon's own services, or the watcher's own meter when
    higher), at (that reading's time), unread (why the newest pass could not read, else None), open}; None while no
    cap was ever set. {unread: why} when the records cannot be read (the page says so, never a figure)."""
    from score.adapters.compute import guard
    try:
        book = guard.cap_book()
        cap_record, reading = guard.current_cap(book, name), guard.cap_newest(book, "readings", name)
    except Exception as error:  # noqa: BLE001 - shown as unread on the money card, never a crash of the page
        return {"name": name, "unread": f"{type(error).__name__}: {error}"}
    if cap_record is None:
        return None
    reading = reading or {}
    return {"name": name, "euros": float(cap_record["euros"]), "line": float(cap_record["line"]),
            "counter": None if reading.get("counter") is None else round(float(reading["counter"]), 2),
            "at": reading.get("good_at") if reading.get("unread") else reading.get("at"),
            "unread": reading.get("unread") if reading else "no reading yet", "open": bool(cap_record.get("open"))}


def cap(name, figures, by, replaces=None, baseline=None):
    """Write the owner's cap `name` by his signed-in name (`figures`: euros, line, start, month_cap, finish,
    standing_per_day, open; a close keeps the current cap's figures, open False); the record, or None once the newest
    cap is no longer the one it `replaces` (its `at`; None for a first). Its baseline is the whole bill's counted lines
    as read now (compute.cap_baseline; `baseline` given in tests). review.Refused for an empty or the runner's name;
    PermissionError in a process an agent started (guard.set_cap)."""
    from score.adapters import compute
    from score.adapters.compute import guard
    name_by = checked_by(by)
    book = guard.cap_book()
    current = guard.current_cap(book, name)
    if (current or {}).get("at") != replaces:
        return None
    if figures.get("open") is False:
        record = {**{field: value for field, value in current.items() if field not in ("at", "by", "open")},
                  "open": False}
    else:
        record = {**figures, "baseline": baseline or compute.cap_baseline()}
    return guard.set_cap(book, {**record, "by": name_by, "at": graph.now()}, name)


def stop_line(store, world):
    """The environment's newest stop line, or None when it has none."""
    from score.adapters.compute import guard
    return guard.current(store, world)


def concept_draw(store, place, request, euros, by, run=None, first=False, purpose=None):
    """His click on a concept review's Draw button: his yes for exactly its calls at `euros` (the price the button
    showed: one draw, or a Redraw with notes' prompt correction and draw), then the draw as its own process inside it; the draw's record. `first` (his Draw all: one of the first
    draws its total covered) refuses once the place has a draw; `purpose` says the click in the yes. review.Refused
    for an empty or the runner's name, a price that moved, or a draw refused (its words); PermissionError in an
    agent's process."""
    import json
    import os
    import subprocess
    import sys
    from score.review import concepts
    name = checked_by(by)
    redraw = bool(request.get("base"))
    price = concepts.redraw_euros() if redraw else concepts.draw_euros()
    if price is None or abs(float(euros) - price) > 0.005:
        shown = "not measured" if price is None else f"EUR {price:.2f}"
        raise review.Refused(f"the price shown, EUR {float(euros):.2f}, is not today's measured price ({shown}): "
                             "read the page again")
    if first and concepts.current_draw(store, place, concepts.wording_now(store, place)):
        raise review.Refused(f"{place} has a draw from its current wording since the click: the places to draw "
                             "changed; read the page again")
    key = concepts.yes_key(place, review.now())
    review.spend(store, "override", key, price, name, purpose=purpose or (
        f"concept review: one redraw of {place} (its prompt corrected by Gemini, then one draw)" if redraw
        else f"concept review: one draw of {place}"))
    asked = store.cache / concepts.AREA / "asked" / f"{key}.json"
    asked.parent.mkdir(parents=True, exist_ok=True)
    asked.write_text(json.dumps(request))
    env = {**os.environ, "SCORE_SPEND_TICKET": f"override {key}", "SCORE_SPEND_STORE": str(store.cache.parent)}
    done = (run or subprocess.run)([sys.executable, "-m", "score.review.concepts", place, str(asked), name],
                                   env=env, capture_output=True, text=True,
                                   timeout=concepts.TIMEOUT * (2 if redraw else 1) + 60)
    if done.returncode != 0:
        raise review.Refused((done.stderr.strip().splitlines() or ["the draw failed"])[-1].removeprefix("refused: "))
    return json.loads(done.stdout.strip().splitlines()[-1])


def concept_generated(store, place, by):
    """His "back to generated" on a concept review: the place's own wording dropped, so its first draws are worded
    from its data again; the record. review.Refused for an empty or the runner's name or a place with no own
    wording; PermissionError in an agent's process."""
    from score.review import concepts
    name = checked_by(by)
    if concepts.own_wording(store, place) is None:
        raise review.Refused(f"{place} has no wording of its own")
    return concepts.worded(store, place, None, name)


def concept_pick(store, place, sha, by):
    """His Pick (or, with sha None, his unlock) of a place's concept, then the place handed to the creator's library
    (concepts.handed_over); the record with what the library did in words (`library`). review.Refused for an empty
    or the runner's name or a sha that is no draw of the place; PermissionError in an agent's process."""
    from score.review import concepts
    name = checked_by(by)
    try:
        record = concepts.pick(store, place, sha, name)
    except concepts.Refused as refused:
        raise review.Refused(str(refused)) from refused
    return {**record, "library": concepts.handed_over(store, place),
            **({"reading": reading_started(store, place, name)} if sha else {})}


def reading_started(store, place, by, start=None):
    """His pick starts the scene inventory reading of the picked draw on its own (score/review/reading.py; the
    owner's standing allowance of 2026-10-21: no yes asked), a process of its own that outlives this one; its log's
    path."""
    import os
    import shutil
    import subprocess
    import sys
    from score.review import concepts, reading
    from score.store import stamp_key
    log = store.cache / reading.AREA / "logs" / f"{place}-{stamp_key(concepts.now())}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    # Under a systemd service (the listener) in a scope of its own, so the listener's hourly restart does not kill it.
    scope = (["systemd-run", "--user", "--scope", "--quiet", "--collect"]
             if os.environ.get("INVOCATION_ID") and shutil.which("systemd-run") else [])
    with log.open("w") as out:
        (start or subprocess.Popen)([*scope, sys.executable, "-m", "score.review.reading", place, "--by", by],
                                    env={**os.environ, "SCORE_SPEND_STORE": str(store.cache.parent)}, stdout=out,
                                    stderr=subprocess.STDOUT, start_new_session=True, cwd=str(concepts.REPO))
    return str(log)


def concept_discuss(store, place, request, euros, by, run=None):
    """His Discuss on a concept review: his yes for exactly that one Gemini call at `euros` (the price his button
    showed; refused when the measured price moved since), then the call as its own process inside it
    (score/review/discuss.py); the discussion entry. review.Refused for an empty or the runner's name, a price that
    moved, or a Discuss refused (its words); PermissionError in an agent's process."""
    import json
    import os
    import subprocess
    import sys
    from score.review import concepts, discuss
    name = checked_by(by)
    price = discuss.price()
    if price is None or abs(float(euros) - price) > 0.005:
        shown = "not measured" if price is None else f"EUR {price:.2f}"
        raise review.Refused(f"the price shown, EUR {float(euros):.2f}, is not today's measured price ({shown}): "
                             "read the page again")
    key = discuss.yes_key(place, review.now())
    review.spend(store, "override", key, price, name, purpose=f"concept review: one Discuss of {place}'s draw (Gemini)")
    asked = store.cache / concepts.AREA / "asked" / f"{key}.json"
    asked.parent.mkdir(parents=True, exist_ok=True)
    asked.write_text(json.dumps(request))
    env = {**os.environ, "SCORE_SPEND_TICKET": f"override {key}", "SCORE_SPEND_STORE": str(store.cache.parent)}
    done = (run or subprocess.run)([sys.executable, "-m", "score.review.discuss", place, str(asked), name],
                                   env=env, capture_output=True, text=True, timeout=concepts.TIMEOUT + 60)
    if done.returncode != 0:
        raise review.Refused((done.stderr.strip().splitlines() or ["the Discuss failed"])[-1]
                             .removeprefix("refused: "))
    return json.loads(done.stdout.strip().splitlines()[-1])


def environment_ask(store, world, request, euros, by, run=None):
    """His Send in the environment concept's set interview: his yes for exactly that one model call at `euros` (the
    price his Send showed; refused when the measured price moved since), then the ask as its own process inside it
    (score/review/environment_concept.py); the ask's record with the fields it proposes. review.Refused for an empty
    or the runner's name, a price that moved, or an ask refused (its words); PermissionError in an agent's process."""
    import json
    import os
    import subprocess
    import sys
    from score.review import concepts, environment_concept
    name = checked_by(by)
    price = environment_concept.ask_euros()
    if price is None or abs(float(euros) - price) > 0.005:
        shown = "not measured" if price is None else f"EUR {price:.2f}"
        raise review.Refused(f"the price shown, EUR {float(euros):.2f}, is not today's measured price ({shown}): "
                             "read the page again")
    key = environment_concept.yes_key(world, review.now())
    review.spend(store, "override", key, price, name,
                 purpose=f"environment concept: one interview answer ({request.get('topic')}) for {world}")
    asked = store.cache / environment_concept.AREA / "asked" / f"{key}.json"
    asked.parent.mkdir(parents=True, exist_ok=True)
    asked.write_text(json.dumps(request))
    env = {**os.environ, "SCORE_SPEND_TICKET": f"override {key}", "SCORE_SPEND_STORE": str(store.cache.parent)}
    done = (run or subprocess.run)([sys.executable, "-m", "score.review.environment_concept", world, str(asked),
                                    name], env=env, capture_output=True, text=True, timeout=concepts.TIMEOUT + 60)
    if done.returncode != 0:
        raise review.Refused((done.stderr.strip().splitlines() or ["the ask failed"])[-1].removeprefix("refused: "))
    return json.loads(done.stdout.strip().splitlines()[-1])


def environment_saved(store, world, concept, locked, by):
    """His Save, Lock or Unlock of the environment concept: a new version, locked or not; the record. Unlocking puts
    every place's concept made under the old version out of date (environment_concept.version). review.Refused for
    an empty or the runner's name or a concept out of shape; PermissionError in an agent's process."""
    from score.review import environment_concept
    name = checked_by(by)
    try:
        return environment_concept.saved(store, world, concept, locked, name)
    except environment_concept.Refused as refused:
        raise review.Refused(str(refused)) from refused


def environment_reference(store, world, data, name, shows, place, by):
    """His new reference picture: into the private bucket and its local copy, then added to the unlocked environment
    concept as a new version; the version. review.Refused for an empty or the runner's name, no picture or a locked
    concept; PermissionError in an agent's process."""
    from score.review import environment_concept
    by_name = checked_by(by)
    try:
        return environment_concept.referenced(store, world, data, name, shows, place, by_name)
    except environment_concept.Refused as refused:
        raise review.Refused(str(refused)) from refused


# --- the plan review (score/review/plans.py): his edits, named inside places, notes through Gemini ---------------

def plan_edit(store, place, plan, by):
    """His plan for `place` as he left it on its plan page, kept as his own; the record."""
    from score.review import plans
    try:
        return plans.edited(store, place, plan, checked_by(by))
    except plans.Refused as refused:
        raise review.Refused(str(refused)) from refused


def environment_plan_edit(store, plan, by):
    """His environment's plan as he left it on its page (score/review/environment_plan.py), kept as his own; the
    record."""
    from score.review import environment_plan
    try:
        return environment_plan.edited(store, plan, checked_by(by))
    except environment_plan.Refused as refused:
        raise review.Refused(str(refused)) from refused


def environment_plan_write(store, by):
    """His Write on the environment's plan page: one Gemini writing under the owner's standing allowance for plan
    writing (score/review/environment_plan.write); the record, refused when the answer was no plan."""
    from score.review import environment_plan
    record = environment_plan.write(store, checked_by(by))
    if record.get("refused"):
        raise review.Refused(record["refused"])
    return record


def plan_named(store, place, names, by):
    """The inside places he named up front on `place`'s concept page; the record."""
    from score.review import plans
    try:
        return plans.name_inside(store, place, names, checked_by(by))
    except plans.Refused as refused:
        raise review.Refused(str(refused)) from refused


def plan_write(store, place, euros, by, run=None):
    """His Make plan on a plan page: the place's plan written (score/review/plan_writing.py) as its own process, one
    Gemini call; with plan_writing.AUTOMATIC off his click is his yes for exactly that call at `euros` (refused when
    its price moved), on, the standing allowance clears it. Its record's line. review.Refused for an empty or the
    runner's name, a price that moved, or a writing refused (its words); PermissionError in an agent's process."""
    import json
    import os
    import subprocess
    import sys
    from score.review import concepts, plan_writing
    from score.store import stamp_key
    name = checked_by(by)
    env = {**os.environ, "SCORE_SPEND_STORE": str(store.cache.parent)}
    if not plan_writing.AUTOMATIC:
        price = plan_writing.price(store)
        if abs(float(euros) - price) > 0.005:
            raise review.Refused(f"the price shown, EUR {float(euros):.2f}, is not today's price (EUR {price:.2f}): "
                                 "read the page again")
        key = f"plan-write-{place}-{stamp_key(review.now())}"
        review.spend(store, "override", key, price, name, purpose=f"plan writing: one plan of {place} (Gemini)")
        env["SCORE_SPEND_TICKET"] = f"override {key}"
    done = (run or subprocess.run)([sys.executable, "-m", "score.review.plan_writing", place, "--by", name],
                                   env=env, capture_output=True, text=True, timeout=plan_writing.TIMEOUT + 60,
                                   cwd=str(concepts.REPO))
    if done.returncode != 0:
        raise review.Refused((done.stderr.strip().splitlines() or ["the writing failed"])[-1]
                             .removeprefix("refused: "))
    lines = done.stdout.strip().splitlines()
    return json.loads(lines[-1]) if lines else {"place": place, "written": "already"}


def plan_revise(store, place, request, euros, by, run=None):
    """His Correct with notes on a plan page: his yes for exactly that one Gemini call at `euros` (refused when the
    measured price moved), then the call as its own process inside it (score.review.plans); its record."""
    import json
    import os
    import subprocess
    import sys
    from score.review import concepts, plans
    name = checked_by(by)
    price = plans.revise_euros()
    if price is None or abs(float(euros) - price) > 0.005:
        shown = "not measured" if price is None else f"EUR {price:.2f}"
        raise review.Refused(f"the price shown, EUR {float(euros):.2f}, is not today's measured price ({shown}): "
                             "read the page again")
    request = {**request, "note": plans.note_of(store, place, request)}  # before his yes: nothing to send, no spend
    key = plans.yes_key(place, review.now())
    review.spend(store, "override", key, price, name, purpose=f"plan review: one correction of {place}'s plan by "
                                                               "the creator's notes (Gemini)")
    asked = store.cache / plans.AREA / "asked" / f"{key}.json"
    asked.parent.mkdir(parents=True, exist_ok=True)
    asked.write_text(json.dumps(request))
    env = {**os.environ, "SCORE_SPEND_TICKET": f"override {key}", "SCORE_SPEND_STORE": str(store.cache.parent)}
    done = (run or subprocess.run)([sys.executable, "-m", "score.review.plans", place, str(asked), name],
                                   env=env, capture_output=True, text=True, timeout=concepts.TIMEOUT + 60)
    if done.returncode != 0:
        raise review.Refused((done.stderr.strip().splitlines() or ["the correction failed"])[-1]
                             .removeprefix("refused: "))
    return json.loads(done.stdout.strip().splitlines()[-1])
