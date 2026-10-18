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
from django.utils import timezone

from score.dashboard import state
from score.dashboard.launch import guard
from score.dashboard.pages import seen
from score.dashboard.pages.models import BasketItem, ChangeRequest, Launch, OwnerCost, Plan, SyncRequest, is_owner
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


# --- the month's spend ------------------------------------------------------------------------------------------

def enter_cost(user, source, euros, words, month):
    """Keep the owner's figure for a cost source this dashboard cannot read (the model provider bill's month, the fixed
    monthly subscriptions); what was done, in words. It is shown, never used to clear or launch anything."""
    if source not in ("models", "subscriptions"):
        return f"refused: {source!r} is not a source the owner enters"
    try:
        amount = float(euros)
    except ValueError:
        return f"refused: {euros!r} is not an amount in euros"
    if not 0 <= amount < 1_000_000:
        return f"refused: EUR {amount} is not a monthly figure"
    OwnerCost.objects.create(source=source, month=month, euros=amount, words=words.strip()[:200], by=user)
    return f"entered {source} EUR {amount:.2f} for {month}"


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
    return "working out freshness (about 3 minutes for the whole world)"


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
        cards.append({"place": place or "world", "hero": hero, "items": queued})
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
    guard.work_out_soon(plan, items, state.source().stage_records)
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

