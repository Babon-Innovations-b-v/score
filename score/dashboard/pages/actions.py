"""What the pages and the API do on a user's request, one function each: record a change request, decide, queue,
plan, launch, read the spend and the freshness snapshot. Local mode acts here; hosted mode queues a SyncRequest for
the store's machine (score/dashboard/sync)."""
import datetime
import json
import os
import shlex
import subprocess
import sys
import threading
import time

from django.conf import settings

from score.dashboard import state
from score.dashboard.launch import guard
from score.dashboard.pages import seen
from score.dashboard.pages.models import BasketItem, ChangeRequest, Launch, Plan, SyncRequest, is_owner
from score.dashboard.state.models import Spend

SPEND_SECONDS = 600
_spend = {"at": 0.0, "value": None, "reading": False}
_spend_lock = threading.Lock()
SNAPSHOT_LOCK = "status.lock"


def hosted():
    return settings.SCORE_MODE == settings.HOSTED


def agent_started():
    """True when this server runs in an agent's process: the store refuses owner decisions there."""
    from score.store import running_under_agent
    return running_under_agent()


def decisions_off_why():
    """Why the decide buttons are absent here, or None."""
    if hosted():
        return None  # hosted decisions are queued for the store's machine, applied by the owner's own timer
    if not settings.SCORE_STORE_WRITABLE:
        return "decisions are off: the store is read-only here (SCORE_STORE_WRITABLE=0)"
    if agent_started():
        return "decisions are off: this server was started from an agent's shell"
    return None


def decisions_on():
    return decisions_off_why() is None


# --- the owner's money figures: each his signed-in request, applied on the store's machine ----------------------

def euro_amount(euros):
    """A figure of euros at least 0 and under a million, or None."""
    try:
        amount = float(euros)
    except (TypeError, ValueError):
        return None
    return amount if 0 <= amount < 1_000_000 else None


def queued_for_store(kind, user, payload, words):
    """Queue an owner's request for the store's machine (hosted); what the page says."""
    SyncRequest.objects.create(kind=kind, user=user, payload=payload)
    return f"queued: the store's machine {words} on its next sync"


def owner_figure_off_why(user):
    """Why the owner's money figure cannot be applied in this process, or None: not the owner, or a server an agent
    started (the store, the guard and the books refuse there too)."""
    if not is_owner_name(user):
        return f"refused: {user} is not this store's owner"
    if agent_started():
        return "refused: this server was started from an agent's shell: only the owner's own process sets a figure"
    return None


def set_books_figure(user, euros):
    """The owner's figure for the model calls' month before their ledger began again, into the month's books
    (score.review.web.google_month), in words: local written, hosted queued."""
    amount = euro_amount(euros)
    if amount is None:
        return f"refused: {euros!r} is not an amount in euros"
    if hosted():
        return queued_for_store("books-figure", user, {"euros": amount}, "writes it into the month's books")
    why = owner_figure_off_why(user)
    if why:
        return why
    from score import review
    from score.review import web
    try:
        books = web.google_month(amount, by=user)
    except review.Refused as refused:
        return f"refused: {refused}"
    _spend["at"] = 0.0
    return f"books known for {books['month']}: EUR {amount:.2f} entered by {user}"


def read_books_back(user):
    """Read the month's bills back into the books (`score spend --read-back`, read-only, free), in words: local run
    here, hosted queued."""
    if hosted():
        return queued_for_store("read-back", user, {}, "reads the bills back")
    if not is_owner_name(user):
        return f"refused: {user} is not this store's owner"
    done = subprocess.run([sys.executable, "-m", "score", "spend", "--read-back"], cwd=settings.SCORE_REPO,
                          capture_output=True, text=True)
    if done.returncode != 0:
        return f"refused: the read-back failed: {(done.stderr.strip().splitlines() or ['no output'])[-1]}"
    _spend["at"] = 0.0
    books = json.loads(done.stdout.strip().splitlines()[-1])
    unread = books.get("google_unread")
    return f"bills read back: the books are {books.get('state')}" + (f" ({unread})" if unread else "")


def waive_check(user, place, stage, output, check, reason):
    """The owner's waiver of one check of an output he saw (score.review.web.waived), in words: local written,
    hosted queued."""
    node = node_of(place, stage)
    if not reason.strip():
        return "refused: say why this check is wrong here"
    if hosted():
        return queued_for_store("waiver", user, {"node": node, "output": output, "check": check,
                                                 "reason": reason.strip()}, f"waives {check}")
    why = decisions_off_why()
    if why:
        return why
    from score import review
    from score.review import web
    source = state.source()
    try:
        web.waived(source.store, node, output, check, by=user, reason=reason.strip())
    except (review.Refused, PermissionError, FileExistsError) as refused:
        return f"refused: {refused}"
    source.refresh()
    return f"waived {check} of {output[:12]} of {node}"


def read_spend():
    """Read the backend's spend now and keep it."""
    try:
        _spend["value"] = guard.backend().spend()
    except Exception as error:  # shown on the money bar in words
        _spend["value"] = Spend(note=f"spend not read: {type(error).__name__}: {error}")
    _spend["at"] = time.time()
    _spend["reading"] = False


def spend():
    """The month's spend for the money bar: hosted from the export; local from the backend, read in the background
    at most every SPEND_SECONDS (the first page says it is being read)."""
    if hosted():
        return state.source().spend()
    with _spend_lock:
        stale = time.time() - _spend["at"] > SPEND_SECONDS
        if stale and not _spend["reading"]:
            _spend["reading"] = True
            threading.Thread(target=read_spend, daemon=True).start()
    return _spend["value"] or Spend(note="the month's spend is being read")


# --- the freshness snapshot -------------------------------------------------------------------------------------

def snapshot_folder():
    folder = settings.SCORE_HOME / "status"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def snapshot_states():
    """The newest freshness snapshot: {made_at, nodes: {node: state}}, or {} when none was made."""
    found = sorted(snapshot_folder().glob("*.json"))
    if not found:
        return {}
    body = json.loads(found[-1].read_text())
    return {"made_at": body.get("made_at"),
            "nodes": {node: node_state for line in body.get("lines", {}).values()
                      for node, node_state in line.get("nodes", {}).items()}}


def run_snapshot(lock):
    """`score status world1 --json` into status/<time>.json, then free the lock."""
    try:
        done = subprocess.run([sys.executable, "-m", "score", "status", "world1", "--json"], cwd=settings.SCORE_REPO,
                              capture_output=True, text=True)
        if done.returncode == 0:
            made = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            (snapshot_folder() / f"{made}.json").write_text(done.stdout.strip().splitlines()[-1])
    finally:
        lock.unlink(missing_ok=True)


def start_snapshot():
    """Start one freshness snapshot in the background; words for the page."""
    if hosted():
        return "the freshness snapshot is made on the store's machine"
    lock = snapshot_folder() / SNAPSHOT_LOCK
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return "a freshness snapshot is already being worked out"
    os.close(descriptor)
    threading.Thread(target=run_snapshot, args=(lock,), daemon=True).start()
    return "working out freshness (about 3 minutes for the whole environment)"


# --- change requests, decisions, the basket --------------------------------------------------------------------

def node_of(place, stage):
    return f"{stage}@{place}" if place else stage


def inbox_write(change):
    """A change request as JSON in the dashboard's inbox (outside data/ and the repo: it moves no key)."""
    folder = settings.SCORE_HOME / "inbox"
    folder.mkdir(parents=True, exist_ok=True)
    body = {"id": change.pk, "user": change.user, "place": change.place, "stage": change.stage, "node": change.node,
            "output_seen": change.output_seen, "words": change.words, "created": change.created.isoformat()}
    (folder / f"{change.pk}.json").write_text(json.dumps(body, indent=1))


def record_change(user, place, stage, output, words):
    """Record a change request; local: into the inbox too, hosted: queued for the store's machine as well."""
    change = ChangeRequest.objects.create(user=user, place=place or "", stage=stage, node=node_of(place, stage),
                                          output_seen=output, words=words)
    if hosted():
        SyncRequest.objects.create(kind="change", user=user, payload={
            "place": place or "", "stage": stage, "node": change.node, "output_seen": output, "words": words,
            "change_id": change.pk})
    else:
        inbox_write(change)
    return change


def decide(user, place, stage, output, decision, reason, worse_reason):
    """The owner's accept or reject, in words: local through score.review.web.decide, hosted queued."""
    node = node_of(place, stage)
    if hosted():
        SyncRequest.objects.create(kind="decision", user=user, payload={
            "node": node, "output": output, "decision": decision, "reason": reason, "worse_reason": worse_reason})
        return f"queued: the store's machine applies the {decision} on its next sync"
    why = decisions_off_why()
    if why:
        return why
    from score import review
    from score.review import web
    source = state.source()
    try:
        web.decide(source.store, node, output, decision, by=user, reason=reason, worse_reason=worse_reason or None)
    except (review.Refused, PermissionError, FileExistsError) as refused:
        return f"refused: {refused}"
    source.refresh()
    return f"{'accepted' if decision == 'accept' else 'rejected'} {output[:12]} of {node}"


def advance(user, place, stage, output):
    """The owner's advance of a step's output, in words: local recorded here, hosted queued for the store's machine
    too (its launches read the mark there). Refused in a server an agent started: agents never advance."""
    node = node_of(place, stage)
    if not hosted() and agent_started():
        return "advance is off: this server was started from an agent's shell"
    if not output:
        return "nothing to advance: this step has no output"
    seen.advance(user, node, output)
    if hosted():
        SyncRequest.objects.create(kind="advance", user=user, payload={"node": node, "output": output})
    return f"advanced {node}: the paid steps after it may be launched"


def queue(user, place, stages, source):
    """Add steps to the basket; the stage names added (a step already queued, or not at this place, is skipped)."""
    added = []
    for stage in stages:
        if source.step_detail(place, stage) is None:
            continue
        _, made = BasketItem.objects.get_or_create(place=place or "", stage=stage, defaults={"added_by": user})
        if made:
            added.append(stage)
    return added


def basket_cards(items):
    """The basket's items grouped by place, each place with its hero picture."""
    source = state.source()
    found = {}
    for item in items:
        found.setdefault(item.place, []).append(item)
    cards = []
    for place, queued in sorted(found.items()):
        hero = source.place_card(place).hero if place else None
        cards.append({"place": place or "whole environment", "hero": hero, "items": queued})
    return cards


# --- plan and launch -------------------------------------------------------------------------------------------

def start_plan(user, jobs):
    """Start working out the basket's plan in the background; words for the page."""
    items = list(BasketItem.objects.all())
    if not items:
        return "the basket is empty"
    if hosted():
        return "the plan is worked out on the store's machine when the launch is picked up"
    if Plan.objects.filter(state="working").exists():
        return "a plan is already being worked out"
    plan = Plan.objects.create(basket_hash=guard.basket_hash(items), made_by=user,
                               body={"jobs": max(1, min(32, int(jobs or guard.DEFAULT_JOBS)))})
    guard.work_out_soon(plan, items)
    return "working out the plan"


def running_launch():
    return any(guard.polled(item).state in ("starting", "running") for item in Launch.objects.filter(
        state__in=("starting", "running")))


def unseen(plan):
    """(paid node, read node) pairs of the plan the owner has not advanced."""
    if plan.state != "ready":
        return []
    source = state.source()
    return seen.unseen_reads(plan.body.get("buys", []), source.reads_of, source.accepted_output)


def launch_refusals(user, plan, confirmed, rebuy_reason):
    return guard.refusals(plan, is_owner(user), guard.basket_hash(BasketItem.objects.all()),
                          running_launch(), confirmed, rebuy_reason, unseen(plan))


def launch(user, plan, confirmed, rebuy_reason):
    """(Launch or None, words): hosted queues the basket; local checks every refusal again, then starts it."""
    if hosted():
        if not confirmed:
            return None, "tick \"I launch this\""
        SyncRequest.objects.create(kind="launch", user=user, payload={
            "items": [{"place": item.place, "stage": item.stage} for item in BasketItem.objects.all()],
            "jobs": plan.body.get("jobs", guard.DEFAULT_JOBS), "rebuy_reason": rebuy_reason})
        return None, "queued: the store's machine plans and checks it again, then launches it"
    refused = guard.refusals(plan, True, guard.basket_hash(BasketItem.objects.all()), running_launch(), confirmed,
                             rebuy_reason, unseen(plan))
    if not is_owner_name(user):
        refused.insert(0, "only the owner launches")
    if refused:
        return None, "refused: " + "; ".join(refused)
    record = Launch.objects.create(plan=plan, by=user, jobs=plan.body.get("jobs", guard.DEFAULT_JOBS),
                                   rebuy_reason=rebuy_reason.strip())
    guard.launch_soon(record, plan)
    return record, "launching: the runner's own clearance checks every paid step again"


def is_owner_name(user):
    return bool(settings.SCORE_OWNER) and user == settings.SCORE_OWNER


def command_words(group, jobs):
    from score.dashboard.launch.localrun import run_command
    return shlex.join(["python", *run_command(group, jobs, None)[1:]])


# --- the concept review (CONTEXT.md "concept review"): the owner's draws and picks, on the store's machine ---------

def concept_draw(user, payload):
    """One draw of a place's concept, his click its spend yes (score.review.web.concept_draw: his yes for that call
    at the price his button showed, then the call in a process of its own); (words, the draw's record or None)."""
    why = owner_figure_off_why(user)
    if why:
        return why, None
    from score import review
    from score.review import web
    source = state.source()
    try:
        asked = {"marks": payload.get("marks") or [], "context_marks": payload.get("context_marks") or [],
                 "note": str(payload.get("note") or ""),
                 "base": payload.get("base") or None, "wording": payload.get("wording") or None}
        place, together = str(payload["place"]), payload.get("all")
        record = web.concept_draw(source.store, place, asked, float(payload["euros"]), by=user, first=bool(together),
                                  purpose=together and (f"concept review: Draw all, {int(together['count'])} first "
                                                        f"draws for EUR {float(together['euros']):.2f}: one of {place}"))
    except (review.Refused, PermissionError, FileExistsError, KeyError, TypeError, ValueError,
            subprocess.TimeoutExpired) as refused:
        return f"refused: {refused}", None
    source.refresh()
    kept = "" if record.get("offsite") else f"; not copied off this PC: {record.get('offsite_refused')}"
    return f"drawn: {record['sha'][:12]} for EUR {record['euros']:.2f}{kept}", record


def concept_discuss(user, payload):
    """His Discuss on a place's shown draw, his click its spend yes (score.review.web.concept_discuss); (words, the
    discussion entry or None)."""
    why = owner_figure_off_why(user)
    if why:
        return why, None
    from score import review
    from score.review import web
    source = state.source()
    try:
        asked = {"base": payload.get("base") or None, "question": str(payload.get("question") or ""),
                 "marks": payload.get("marks") or [], "context_marks": payload.get("context_marks") or []}
        entry = web.concept_discuss(source.store, str(payload["place"]), asked, float(payload["euros"]), by=user)
    except (review.Refused, PermissionError, FileExistsError, KeyError, TypeError, ValueError,
            subprocess.TimeoutExpired) as refused:
        return f"refused: {refused}", None
    source.refresh()
    return f"answered for EUR {entry['euros']:.2f}", entry


def concept_generated(user, payload):
    """His "back to generated": the place's own draw wording dropped (score.review.web.concept_generated); in words."""
    why = owner_figure_off_why(user)
    if why:
        return why
    from score import review
    from score.review import web
    source = state.source()
    try:
        web.concept_generated(source.store, str(payload["place"]), by=user)
    except (review.Refused, PermissionError, FileExistsError, KeyError) as refused:
        return f"refused: {refused}"
    source.refresh()
    return "back to the generated wording"


def concept_pick(user, payload):
    """His Pick of a place's concept draw (`sha`), or his unlock (`sha` None); in words."""
    why = owner_figure_off_why(user)
    if why:
        return why
    from score import review
    from score.review import web
    source = state.source()
    try:
        record = web.concept_pick(source.store, str(payload["place"]), payload.get("sha") or None, by=user)
    except (review.Refused, PermissionError, FileExistsError, KeyError) as refused:
        return f"refused: {refused}"
    source.refresh()
    return (f"locked {record['sha'][:12]}" if record["sha"] else "unlocked") + f"; {record['library']}"


# --- the environment concept (CONTEXT.md "environment concept"): the owner's interview, versions and references ----

def environment_ask(user, payload):
    """One answer of the environment concept's set interview, his Send its spend yes (score.review.web.
    environment_ask: his yes for that one call at the price his Send showed); (words, the ask's record or None)."""
    why = owner_figure_off_why(user)
    if why:
        return why, None
    from score import review
    from score.review import web
    source = state.source()
    try:
        asked = {"topic": str(payload["topic"]), "answer": str(payload["answer"]), "concept": payload["concept"]}
        record = web.environment_ask(source.store, str(payload["world"]), asked, float(payload["euros"]), by=user)
    except (review.Refused, PermissionError, FileExistsError, KeyError, TypeError, ValueError,
            subprocess.TimeoutExpired) as refused:
        return f"refused: {refused}", None
    return f"answered for EUR {record['euros']:.2f}", record


def environment_save(user, payload):
    """His Save, Accept, Lock or Unlock of the environment concept: a new version (score.review.web.
    environment_saved); in words."""
    why = owner_figure_off_why(user)
    if why:
        return why
    from score import review
    from score.review import web
    source = state.source()
    try:
        record = web.environment_saved(source.store, str(payload["world"]), payload["concept"],
                                       bool(payload["locked"]), by=user)
    except (review.Refused, PermissionError, FileExistsError, KeyError) as refused:
        return f"refused: {refused}"
    source.refresh()
    return "locked" if record["locked"] else "saved"


def environment_reference(user, payload):
    """His new reference picture (score.review.web.environment_reference: the private bucket, its local copy, a new
    version holding it); (words, the picture's path as the concept names it, or None)."""
    why = owner_figure_off_why(user)
    if why:
        return why, None
    import base64
    import binascii
    from score import review
    from score.review import web
    source = state.source()
    try:
        data = base64.b64decode(str(payload["data"]), validate=True)
        record = web.environment_reference(source.store, str(payload["world"]), data, str(payload["name"]),
                                           str(payload.get("shows") or ""), payload.get("place") or None, by=user)
    except (review.Refused, PermissionError, FileExistsError, KeyError, binascii.Error) as refused:
        return f"refused: {refused}", None
    source.refresh()
    return "added", record["concept"]["references"][-1]["picture"]

# --- the plan review (score/review/plans.py): the owner's plan edits, named inside places, corrections -----------

def plan_said(user, call, done):
    """Run one of his plan review clicks on the store's machine (`call(store, by)`, a score.review.web function);
    `done(record)` in words, or why it was refused."""
    why = owner_figure_off_why(user)
    if why:
        return why
    from score import review
    source = state.source()
    try:
        record = call(source.store, user)
    except (review.Refused, PermissionError, FileExistsError, KeyError, TypeError, ValueError,
            subprocess.TimeoutExpired) as refused:
        return f"refused: {refused}"
    source.refresh()
    return done(record)


def plan_edit(user, payload):
    """His plan as he left it on its page, kept as his own (score.review.web.plan_edit); in words."""
    from score.review import web
    return plan_said(user, lambda store, by: web.plan_edit(store, str(payload["place"]), payload["plan"], by),
                     lambda record: f"kept {len(record['plan']['items'])} items")


def environment_plan_edit(user, payload):
    """His environment's plan as he left it on its page (score.review.web.environment_plan_edit); in words."""
    from score.review import web
    return plan_said(user, lambda store, by: web.environment_plan_edit(store, payload["plan"], by),
                     lambda record: f"kept, {len(record['plan']['gaps'])} gaps")


def environment_plan_write(user, payload):
    """His Write on the environment's plan page (score.review.web.environment_plan_write); in words."""
    from score.review import web
    return plan_said(user, lambda store, by: web.environment_plan_write(store, by),
                     lambda record: f"written, {len(record['plan']['gaps'])} gaps, EUR {record['euros'] or 0:.3f}")


def plan_named(user, payload):
    """The inside places he named on a concept page (score.review.web.plan_named); in words."""
    from score.review import web
    names = payload.get("names") or []
    return plan_said(user, lambda store, by: web.plan_named(store, str(payload["place"]), names, by),
                     lambda record: f"{len(record['names'])} child scenes named")


def plan_write(user, payload):
    """His Make plan: the place's plan written by the prompt model (score.review.web.plan_write; his click its spend
    yes unless the standing allowance covers it); in words."""
    from score.review import web
    return plan_said(user, lambda store, by: web.plan_write(store, str(payload["place"]), float(payload["euros"]), by),
                     lambda record: f"written: {record.get('items', 0)} items, {record.get('gaps', 0)} gaps"
                     if "refused" not in record else f"refused: {record['refused']}")


def plan_revise(user, payload):
    """His Correct with notes, his click its spend yes (score.review.web.plan_revise); in words."""
    from score.review import web
    asked = {"marks": payload.get("marks") or [], "context_marks": payload.get("context_marks") or [],
             "note": str(payload.get("note") or "")}
    return plan_said(user, lambda store, by: web.plan_revise(store, str(payload["place"]), asked,
                                                             float(payload["euros"]), by),
                     lambda record: f"corrected at {record['at']}")

