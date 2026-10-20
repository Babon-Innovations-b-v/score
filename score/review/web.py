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
(`google_month`, into the month's books, refused in an agent's process by compute itself) come the same way; the
spend override (a yes for a run outside the runner) stays terminal-only, except his concept review's draw button.

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

`stop` is his money yes from the cockpit's checkout: the signed-in owner on the trusted cockpit counts as the owner
at his terminal (`python -m score.review stop`, C22), and the line is written by the same guard.set_line, which
refuses in any process an agent started, so no agent can trigger it by any route through here.
"""
from score import graph, review
from score.store import RUNNER

DECISIONS = ("accept", "reject")


def checked_by(by):
    """The owner's user name, refused when empty or the runner's."""
    name = (by or "").strip()
    if not name or name == RUNNER:
        raise review.Refused(f"a decision needs the signed-in owner's own name, not {by!r}")
    return name


def decide(store, node, output, decision, by, reason="", worse_reason=None):
    """Record the owner's accept or reject of one output of a node, by his signed-in name; what was written.
    review.Refused when the output may not be taken so (it did not pass, it is worse with no reason, a reject with no
    reason, it is not the accepted output)."""
    name = checked_by(by)
    if decision == "reject":
        return review.reject(store, node, output, name, reason)
    if decision == "accept":
        return review.accept(store, node, output, name, reason, worse_reason=worse_reason or None)
    raise review.Refused(f"a decision is one of {', '.join(DECISIONS)}, not {decision!r}")


def books_now():
    """The books as they stand ({month, bill, ledger, google}), read for an environment's first stop line only."""
    from score.adapters import compute
    return compute.books_now()


def stop(store, world, euros, reason, by, books=None):
    """Write the environment's new stop line at `euros` by the signed-in owner's name, his reason with it; the record. A
    environment's first line counts its spend from `books()` (default books_now). review.Refused for an empty or the runner's
    name;
    PermissionError in a process an agent started (guard.set_line)."""
    from score.adapters.compute import guard
    name = checked_by(by)
    baseline = None if guard.current(store, world) else (books or books_now)()
    return guard.set_line(store, world, euros, reason, name, graph.now(), baseline)


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


def waived(store, node, output, check, by, reason):
    """The owner's waiver of one check of the output he saw, under that output's key, by his signed-in name; the
    waiver. review.Refused when the output has no record here, the check was not judged or the reason is empty;
    PermissionError in a process an agent started (the store's own barrier)."""
    name = checked_by(by)
    record = review.record_of(store, node, output)
    if record is None:
        raise review.Refused(f"{node} has no output {output[:12]} here")
    return review.waive(store, node, record["key"], check, name, reason)


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
