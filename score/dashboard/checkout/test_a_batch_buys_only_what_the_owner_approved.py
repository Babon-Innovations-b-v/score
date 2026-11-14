"""Invariant: a batch buys only what the owner approved, at the runner's prices: his checkout (or his yes in chat)
refused in words for anything changed, waiting, unpriced, stale or not his; the runner's own plan held to what was
priced; the environment's stop line written by his name only outside an agent's process, at the batch's high plus
10% within one budget across its tries, taken back when the batch ends or is refused; ONE run command through the
backend; the results against their forecast. The launch guard (score/dashboard/launch) is this module's other way in:
its groups, its refusals in words and the local backend's command, environment, prices, ledger and result line.
Nothing launches but the real `score run --detach` of a run with nothing to make, in the sandbox home.

Breaks that turn this red (each applied once and seen red, then reverted):
- pricing.cleared_high: drop the guessed euros -> test_a_batch_buys_only_what_the_owner_approved (PRICED, WORKED
  "unmeasured ...")
- flow.place_refusals: `elif actions.agent_started():` -> `elif False:` ->
  test_a_batch_buys_only_what_the_owner_approved (PRESSES "from an agent's shell")
- flow.bought_items: the version check -> `elif False:` -> test_a_batch_buys_only_what_the_owner_approved (PRESSES
  "changed since he chose it")
- flow.left_out: `not in stages` -> `or True` -> test_a_batch_buys_only_what_the_owner_approved
  (left_out without the film)
- flow.batch_budget: `min(before, round(yes["batch_total_euros"], 2))` -> `before` -> a retry whose yes wrote no
  line takes the batch's older, larger budget -> test_a_batch_buys_only_what_the_owner_approved
  (BUDGETS "a retry under a larger line of his yes")
- flow.start: drop `items = left_out(...)` -> a Buy without the film buys the left-out rows ->
  test_a_batch_buys_only_what_the_owner_approved (CHAT_SELECTED "stages left out")
- flow.start: `phase_kept(left_out(...), ...)` -> `left_out(...)` -> a Buy by phase runs the other phase's
  pixal@alpha too -> test_a_batch_buys_only_what_the_owner_approved (CHAT_SELECTED "by phase")
- chat_yes.buy: drop `flow.basket_made()` -> a Buy in chat buys the basket an older pass saved and the run "would
  also buy" the row the runner's plan grew by ->
  test_a_batch_buys_only_what_the_owner_approved (CHAT_SELECTED's plan selections, CHAT_TRIES "his yes, ...")
- chat_yes.buy: `flow.basket_made(phase=..., places=...)` -> `flow.basket_made()`, or flow.basket_made's group
  without its phases or places, or localrun.selection without --phase -> a Buy by phase and place plans the whole
  environment ->
  test_a_batch_buys_only_what_the_owner_approved (CHAT_SELECTED's plan selections, the plan by phase and place)
- flow.start: drop the `nodes_left(...)` line -> the run names closeup@alpha under --leave-place alpha ->
  test_a_batch_buys_only_what_the_owner_approved
  (CHAT_SELECTED "--leave-place alpha")
- flow.BUFFER = 1.10 -> 1.0 -> test_a_batch_buys_only_what_the_owner_approved (PRESSES "both places: ...")
- flow.refusals: `if actions.running_launch():` -> `if False:` -> test_a_batch_buys_only_what_the_owner_approved
  (PRESSES "a second press ...")
- guard.polled: drop "refused" from the states it reads -> test_a_batch_buys_only_what_the_owner_approved (PRESSES "the
  runner refused its run")
- flow.start: the same-key early return -> `if False:` -> test_a_batch_buys_only_what_the_owner_approved (PRESSES "the
  same key again")
- flow.checking_out: the home's `fcntl.flock` -> `pass` -> test_a_batch_buys_only_what_the_owner_approved (PRESSES
  "another process checking out")
- flow.plan_refusals: `if extra:` -> `if False:` -> test_a_batch_buys_only_what_the_owner_approved (PRESSES "it would
  also buy 9 rows")
- flow.extra_buys: `sorted(set(extra) - set(gaps))` -> `...[:1]` -> only the first named ->
  test_a_batch_buys_only_what_the_owner_approved (PRESSES "it would also buy 9 rows")
- localrun.run_command: `min(int(jobs), cores ...)` -> `int(jobs)` -> a Buy of 16 jobs refused on an 8-core conductor ->
  test_a_batch_buys_only_what_the_owner_approved (RUN_COMMANDS "16 jobs on 8 cores")
- flow.cheap_taken: `if not taken:` -> `if True:` -> test_a_batch_buys_only_what_the_owner_approved (PRESSES
  "--take-cheap takes them in")
- flow.run: the buys-nothing check -> `if False:` -> test_a_batch_buys_only_what_the_owner_approved (PRESSES "it buys
  nothing now")
- flow.room_refusals: the room check -> `if False:` -> test_a_batch_buys_only_what_the_owner_approved (PRESSES "no room
  under ...")
- flow.room_refusals: drop the `spend.ceiling >= line["euros"]` return -> a try the line caps is refused over spend
  that grew after its line was written -> test_a_batch_buys_only_what_the_owner_approved
  (PRESSES "an ended try's close under the next try's line")
- flow.run: `write_line` wrapped in `except PermissionError: pass` -> test_a_batch_buys_only_what_the_owner_approved
  (PRESSES "an agent's process")
- flow.batch_groups: one RunGroup per node -> test_a_batch_buys_only_what_the_owner_approved (PRESSES "two items sharing
  ...")
- flow.stale_basket: the other-checkout check -> `if False:` -> test_a_batch_buys_only_what_the_owner_approved (PRESSES
  "made in another checkout")
- flow.spend_now: `if books and spend.paid_refused:` -> `if False:` -> test_a_batch_buys_only_what_the_owner_approved
  (PRESSES "the month's books unknown")
- flow.abandoned: `if record.pid is not None and pid_alive(...)` -> `if True:` ->
  test_a_batch_buys_only_what_the_owner_approved (PRESSES "left launching ...")
- flow.orphaned_launches: its `launch.save()` dropped -> test_a_batch_buys_only_what_the_owner_approved (PRESSES "left
  launching ...": a cut Buy's launch blocks every Buy)
- flow.batches_ended: its skip -> `if True:` -> test_a_batch_buys_only_what_the_owner_approved
  (PRESSES "an ended batch's line taken back once")
- web.stop: its `replaces` check -> `if False:` -> an ended try's close lands over the line the next try wrote while
  it read the spend, so a closed line sets the next try's room -> test_a_batch_buys_only_what_the_owner_approved
  (PRESSES "an ended try's close under the next try's line")
- localrun.LocalBackend.poll: the handed-on branch -> `if False:` -> test_a_batch_buys_only_what_the_owner_approved
  (PRESSES "stopped by the grow and resumed")
- flow.launch: drop `record.launch = started` -> test_a_batch_buys_only_what_the_owner_approved
  (PRESSES "his hosted checkout")
- results.billed_by_node: `(euros + line.euros, ...)` -> `(line.euros, ...)` ->
  test_a_batch_buys_only_what_the_owner_approved (PRESSES "his results against the forecast")
- flow.batch_groups: the Benchmarks group -> `if False:` -> test_a_batch_buys_only_what_the_owner_approved (PRESSES "the
  benchmarks: one item, ...")
- api/routes.books_figure: `user.username` -> "someone" -> test_a_batch_buys_only_what_the_owner_approved (PRESSES "his
  Google figure into the books")
- flow.by_of: `return user.username` -> test_a_batch_buys_only_what_the_owner_approved (CHAT_TRIES "his yes, ...")
- chat_yes.buy: drop `print(relations_kept(places))`, or move it after `flow.basket_made` -> a Buy plans on relations
  older than its plans while the sync is paused (Buy 91, 2026-11-12) ->
  test_a_batch_buys_only_what_the_owner_approved (CHAT_TRIES "his yes, ...")
- chat_yes.relations_kept: `not chosen or place in chosen` -> `True` -> a Buy by place derives every place's
  relations -> test_a_batch_buys_only_what_the_owner_approved (relations_kept("beta"))
- chat_yes.buy: `current_basket(approved)` -> `current_basket()` -> a Buy in chat buys at the places prepare's saved
  design record approves and the run "would also buy" beta's row ->
  test_a_batch_buys_only_what_the_owner_approved (CHAT_TRIES "his yes, ...")
- chat_yes.approved_now: its `except` dropped -> a design that cannot be worked out is no refusal in words ->
  test_a_batch_buys_only_what_the_owner_approved (CHAT_REFUSED "the design unworkable")
- chat_yes.buy: the basket check put back (yes basket != basket now -> refused) ->
  test_a_batch_buys_only_what_the_owner_approved (CHAT_REFUSED's words, CHAT_TRIES "his yes, ...")
- flow.yes_refusals: the stop check -> `if False:` ->
  test_a_batch_buys_only_what_the_owner_approved (CHAT_REFUSED "a try's stop")
- flow.batch_budget: a yes's `if used >= total:` -> `if False:` -> test_a_batch_buys_only_what_the_owner_approved
  (BUDGETS "a total the batch has spent")
- flow.batch_budget: a retry's `return start, budget` -> `budget + need` ->
  test_a_batch_buys_only_what_the_owner_approved (BUDGETS "a retry under a larger line", CHAT_TRIES "a retry")
- watched.batch_of: `batch_ended(..., nodes)` -> `batch_ended(...)` -> every checkout's rows read again for each later
  one (the door's batch-money 283 s) -> test_a_batch_buys_only_what_the_owner_approved (checkout_nodes read once)
- flow.remade_out: `count > PAID_REMAKES` -> `>=` -> test_a_batch_buys_only_what_the_owner_approved
  (REMADE "failed once: ...")
- flow.free_first: drop `free_route(node) and` -> test_a_batch_buys_only_what_the_owner_approved
  (FREE_FIRST "cloud only: no wait")
- web.cap_figure: counter from the cap's `line` -> test_a_batch_buys_only_what_the_owner_approved (env1's cap)
- flow.remade_out: `if one.at >= REMAKES_FROM` -> `if True` -> a row failed before the cap's start is a gap ->
  test_a_batch_buys_only_what_the_owner_approved (REMADE "a failure before the remakes' start")
- watched.batch_start: `return None` for a line without batch_from -> test_a_batch_buys_only_what_the_owner_approved
  (BUDGETS "counted from an older first try's line")
- flow.batch_budget and watched.batch_money take a line's `batch_budget` as written ->
  test_a_batch_buys_only_what_the_owner_approved (BUDGETS "a try once its own batch", batch_money's budget)
- flow.phase_kept: `in chosen` -> `== phase` -> test_a_batch_buys_only_what_the_owner_approved
  (phase_kept of two phases)
- flow.places_left: drop the `upstream` wait -> pixal@beta is kept; drop `node in wanted` -> the film is kept under
  --place alpha -> test_a_batch_buys_only_what_the_owner_approved (PLACES_LEFT)
- guard.run_groups: the group key also takes the place -> test_a_batch_buys_only_what_the_owner_approved (GROUPED "same
  stages join")
- guard.refusals: the age check `> timedelta(minutes=PLAN_MINUTES)` -> `>= timedelta(0)` ->
  test_a_batch_buys_only_what_the_owner_approved
  (REFUSED "a good plan")
- guard.money_refusals: the unknown-room refusal dropped -> test_a_batch_buys_only_what_the_owner_approved (REFUSED "no
  room known")
- guard.plan_body: room without `- spend.reserved` -> test_a_batch_buys_only_what_the_owner_approved (WORKED "measured")
- guard.plan_body: high `totals["high_euros"]` -> test_a_batch_buys_only_what_the_owner_approved (WORKED "unmeasured
  ...")
- guard.launch: `record.state = "refused"` always -> test_a_batch_buys_only_what_the_owner_approved (the confirm page)
- localrun.run_env: `SECRETS + RUN_TAGS` -> `SECRETS` -> test_a_batch_buys_only_what_the_owner_approved (LAUNCHED, its
  environment)
- localrun.run_env: drop the CLUSTER_DEFAULTS lines -> test_a_batch_buys_only_what_the_owner_approved (the cluster's
  home)
- localrun.LocalBackend.ledgered: drop the `>= since` filter -> test_a_batch_buys_only_what_the_owner_approved (the
  ledger by node)
- localrun.LocalBackend.poll: `if handle.refused is not None:` -> `if False:` ->
  test_a_batch_buys_only_what_the_owner_approved
  (LAUNCHED "refused before detaching")
- localrun.RESULT_STATES "stopped" -> "failed" -> test_a_batch_buys_only_what_the_owner_approved (POLLED "stopped")
- localrun.STARTED: `pid=(\\d+)` -> `pid=(\\d+)x` -> test_a_batch_buys_only_what_the_owner_approved (LAUNCHED
  "detached", the real run)
"""
import datetime
import os
import pathlib
import subprocess
import types

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from score.dashboard.checkout import flow, pricing
from score.dashboard.launch import guard, localrun
from score.dashboard.launch.backend import Billed, LaunchHandle, RunGroup
from score.dashboard.pages import basket
from score.dashboard.pages.models import BasketChoice, BasketItem, Checkout, Launch, Plan
from score.dashboard.proposals import make, records
from score.dashboard.tests import fixture
from score.dashboard.tests.fixture import FakeBackend, api
from score.graph import runs
from score.store import AGENT_MARKERS

pytestmark = pytest.mark.django_db(transaction=True)
BOOKS = {"month": "2026-10", "bill": 0.0, "ledger": 0.0}  # what a first line counts from (the fake spend reads none)


def made_now():
    """The time a basket is made, as make.py writes it."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def a_basket(settings, buys, declared=None, missing=()):
    """The basket as make.py leaves it, its items from `buys` (priced at the fake backend's numbers)."""
    settings.SCORE_HOME.mkdir(parents=True, exist_ok=True)
    priced = [{"node": node, "why": "never ran", "again": False, "price": dict(FakeBackend.price_of)} for node in buys]
    found = make.grouped(priced, {"closeup": "pieces"}, list(missing), declared or {})
    records.put_index(settings.SCORE_HOME / "proposals", {"made_at": made_now(), "checkout": str(settings.SCORE_REPO),
                                                          "items": found})
    return {item["id"]: item for item in found}


@pytest.fixture
def shop(world, settings, monkeypatch):
    """The fixture environment, a basket of alpha's and beta's close-ups, the checkout run in this thread, no agent
    marks, the owner's books."""
    monkeypatch.setattr(flow, "run_soon", lambda record: flow.run(record, FakeBackend()))
    from score.review import web
    monkeypatch.setattr(web, "books_now", lambda: dict(BOOKS))
    for name in AGENT_MARKERS:
        monkeypatch.delenv(name, raising=False)
    FakeBackend.plan_buys, FakeBackend.bill, FakeBackend.ceiling, FakeBackend.missing = None, [], 250.0, []
    FakeBackend.paid_refused = None
    world.items = a_basket(settings, ["closeup@alpha", "closeup@beta"])
    return world


def bought(shop, *idents, version=None):
    """His buy of the items, as he saw them."""
    for ident in idents:
        BasketChoice.objects.create(item=ident, version=version or shop.items[ident]["version"], choice="buy",
                                    by="joey")


def checked_out(client, key, confirmed=True):
    return client.post("/api/checkout", json={"key": key * 16, "confirmed": confirmed}).json()


def launches():
    return [call for call in FakeBackend.calls if call[0] == "launch"]


def stop_line(world):
    from score.review import web
    return web.stop_line(world.store, "world1")


LISTED = [  # prepare's record as score/stages/complete/prepare/benchmarks.listed writes it
    {"id": "pixal-l4", "what": "Pixal3D on one L4", "likely_euros": 1.5, "high_euros": 2.81, "guess_euros": None,
     "likely_minutes": 91.3, "high_minutes": 183.3, "gap": None},
    {"id": "film", "what": "the hub's film", "likely_euros": None, "high_euros": None, "guess_euros": 3.5,
     "likely_minutes": 64.0, "high_minutes": 144.0, "gap": None},
    {"id": "batch-direct", "what": "batch against direct", "gap": "no paid path asks a finish list direct"}]


def a_prepare_record(settings, listed=LISTED):
    import json
    from score.dashboard.proposals import benchmarks
    path = settings.SCORE_PROPS_HOME / benchmarks.RECORD
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"benchmarks": {"listed": listed}}))


# --- his presses of the checkout ---------------------------------------------------------------------------------

PRICED = [  # (id, the basket's nodes as make.py prices them, the runner's jobs, its totals and cleared high)
    ("each node once, the unmeasured and unpriced apart", 1,
     {"likely_euros": 4.0, "high_euros": 6.0, "guessed_euros": 5.0, "nodes": 4, "likely_minutes": 20.0,
      "high_minutes": 40.0, "cards": 4, "unmeasured": ["pixal@alpha"], "unpriced": ["odd@alpha"]}, 11.0),
    ("eight jobs: the longest line", 8, {"likely_minutes": 10.0}, 11.0)]
MEASURED = {"likely_euros": 2.0, "high_euros": 3.0, "likely_minutes": 10.0, "high_minutes": 20.0, "cards": 2, "runs": 3}
ESTIMATE = {"likely_euros": None, "high_euros": None, "guess_euros": 5.0, "likely_minutes": None, "high_minutes": None,
            "cards": None, "runs": 0, "basis": "not measured yet"}
PRICED_ITEMS = [{"nodes": {"closeup@alpha": MEASURED, "closeup@beta": MEASURED}},
                {"nodes": {"closeup@beta": MEASURED, "pixal@alpha": ESTIMATE,
                           "odd@alpha": {"error": "not a paid row"}}}]

UPSTREAM = [f"terrain@{place}" for place in "pqrstuvw"]
WAITING = (["closeup@alpha"], {"ship-room-concepts": {"title": "Ship room concepts", "nodes": ["concept-views"]}},
           ["closeup@alpha: a bake job (/x/job.json)"])
ENDED_NOW, ENDED_NONE = (f"checkouts: 0 left launching failed, {count} ended batches' lines taken back"
                         for count in (1, 0))  # a pass's words: one ended batch's line taken back, none
GROWN = ("score run: waiting for size: 16 jobs, 2 cores; registered as w1; score resume starts it at the boot on the "
         "batch size\nscore run: stopped by signal 15 while waiting for size\n"
         "detached: stopped by signal 15 exit=143 minutes=8.8 log=x outputs=y\n")
A_YES = {"id": "y", "batch_total_euros": 500.0}  # flow.yes_refusals: a batch total
PRESSES = [  # (id, the world before his presses: knobs; his presses: (key, ticked) or ("again", a yes the record runs
    # under again); what they leave: the last answer's words, the last checkout's state and detail, the newest stop
    # line (None: no line written), the runner's plans and launches, his Basket's last line)
    ("not ticked, nothing bought", {"buy": ()}, [("c", False)],
     {"said": ["choose Buy on at least one item first", "I buy these"], "checkouts": 0, "line": None, "launches": 0}),
    ("from an agent's shell", {"agent_started": True}, [("c", True)],
     {"said": ["started from an agent's shell"], "checkouts": 0, "line": None, "launches": 0}),
    ("changed since he chose it", {"version": "0" * 16}, [("k", True)],
     {"said": ["changed since you chose it: look again"], "checkouts": 0, "line": None, "launches": 0}),
    ("waiting and inputs missing", {"basket": WAITING, "buy": ("ship-room-concepts", "alpha-pieces")}, [("k", True)],
     {"said": ["Ship room concepts: a run on main does not buy it yet", "inputs are missing"], "checkouts": 0,
      "line": None, "launches": 0}),
    ("made in another checkout", {"index": {"checkout": "/home/x/score/.claude/worktrees/agent-ad171d0a"}},
     [("w", True)], {"said": ["the basket was made in /home/x/score/.claude/worktrees/agent-ad171d0a, not in this "
                              "cockpit's"], "checkouts": 0, "line": None, "launches": 0}),
    # his design changed after the basket was made (the pick stays: every later row's basket is the next pass's)
    ("made before the design changed", {"index": {"made_at": "2026-10-19T08:00:00Z"}, "pick": True}, [("w", True)],
     {"said": ["the basket was made at 2026-10-19T08:00:00Z, before the design last changed ("], "checkouts": 0,
      "line": None, "launches": 0}),
    ("both places: one run at the batch's high plus 10%", {"buy": ("alpha-pieces", "beta-pieces")}, [("d", True)],
     {"state": "launched", "line": 100.0 + 10.0 + 33.0, "reason": "alpha: pieces, beta: pieces", "high": 30.0,
      "planned": [RunGroup(("alpha", "beta"), ("closeup@alpha", "closeup@beta"))], "launches": 1, "run": "running"}),
    ("a second press while the batch runs", {}, [("r", True), ("s", True)],
     {"said": ["a launch from this cockpit is still running"], "state": "launched", "checkouts": 1, "launches": 1,
      "run": "running"}),
    ("the runner refused its run", {"log_folder": True,
                                    "result": "score run: started\ndetached: refused: the month's books are unknown\n"},
     [("u", True)], {"state": "launched", "launches": 1, "last": ["refused", "books are unknown"]}),
    ("the same key again", {}, [("e", True), ("e", True)],
     {"said": ["already made with this key"], "checkouts": 1, "launches": 1, "line": 126.5}),
    # another process of this home holds the checkout's lock for 1.5 s: this press waits for it, then launches once
    ("another process checking out", {"held": 1.5}, [("w", True)],
     {"state": "launched", "waited": 1.0, "checkouts": 1, "launches": 1}),
    ("it would also buy 9 rows", {"plan_buys": ["closeup@alpha", "closeup@beta", *UPSTREAM]}, [("g", True)],
     {"state": "refused", "detail": ["would also buy 9 rows", "closeup@beta", *UPSTREAM], "line": None,
      "launches": 0}),
    ("--take-cheap with none cheap enough", {"plan_buys": ["closeup@alpha", "closeup@beta", *UPSTREAM]},
     [("g", True), ("again", {**A_YES, "take_cheap": FakeBackend.euros - 1})],
     {"state": "refused", "detail": [f"none under EUR {FakeBackend.euros - 1:g}"], "line": None, "launches": 0}),
    ("--take-cheap takes them in", {"plan_buys": ["closeup@alpha", "closeup@beta", *UPSTREAM], "ceiling": 1000.0},
     [("g", True), ("again", {**A_YES, "take_cheap": FakeBackend.euros + 1})],
     {"state": "launched", "taken": sorted(["closeup@beta", *UPSTREAM]), "launches": 1}),
    ("it buys nothing now", {"plan_buys": []}, [("n", True)],
     {"state": "done", "detail": ["buys nothing now"], "line": None, "launches": 0}),
    # the runner still reads an older, lower line: room EUR 5 for a EUR 15 high; the line its yes wrote taken back
    # to the spend so far plus what is in flight
    ("no room under the runner's spend", {"ceiling": 115.0}, [("h", True)],
     {"state": "refused", "detail": ["cannot finish under the stop: the line gave EUR 15.00, the runner reads room "
                                     "EUR 5.00"], "line": 110.0, "before": round(110.0 + 15.0 * 1.1, 2),
      "reason": "refused", "closed": 110.0, "launches": 0}),
    # the cockpit's own check passed (patched); the guard's writer still refuses
    ("an agent's process", {"agent_env": True}, [("i", True)],
     {"state": "failed", "detail": ["PermissionError"], "line": None, "launches": 0}),
    # two items at one place read the same upstream nodes: one runner command holds both, each node named, so the
    # runner's clash check (graph/runs.py) has no second run to refuse
    ("two items sharing upstream nodes", {"basket": (["closeup@alpha", "pixal@alpha"], None, ()),
                                          "plan_buys": ["closeup@alpha", "pixal@alpha"],
                                          "buy": ("alpha-pieces", "alpha-stage-and-films")}, [("s", True)],
     {"state": "launched", "planned": [RunGroup(("alpha",), ("closeup@alpha", "pixal@alpha"))], "launches": 1,
      "line": 143.0}),
    ("the month's books unknown", {"paid_refused": "the cloud bill of 2026-10 is not read"}, [("b", True)],
     {"state": "refused", "detail": ["the month's books are not known (the cloud bill of 2026-10 is not read)",
                                     "press Read the bills on the Buy screen"], "line": None, "launches": 0}),
    # checkouts left launching by a process now gone (or from before the pid was kept), and a launch left starting
    # when its process ended before the runner had it (2026-11-04): failed, never "still launching" or "running"
    ("left launching by a gone process", {"left": True}, [("m", True)],
     {"state": "launched", "launches": 1, "run": "running"}),
    # applied on the store's machine (sync/applying.py): running with its launch's id, which the pass follows to its
    # end, and the stop line it wrote
    ("his hosted checkout", {}, [("hosted", "h")],
     {"applied": "running", "said": ["stop line EUR 126.50", "its high EUR 15.00 plus 10%"], "state": "launched",
      "checkouts": 1, "launches": 1, "line": 126.5}),
    # its run writes its result line (done): the pass takes the batch's line back to the spend, once
    ("an ended batch's line taken back once", {"log_folder": True}, [("t", True)],
     {"state": "launched", "launches": 1, "line": 126.5, "tidied": [
         (None, None, ENDED_NOW, 110.0, "closed: its batch ended done"),
         (None, None, ENDED_NONE, None, None)]}),
    # 2026-10-26, checkout 5: its run waited for size, the grow's shutdown stopped it (signal 15), score resume
    # started it again; the pass read the launch stopped and took the line back to the spend, so the resumed run was
    # refused every paid row. A launch whose run waits or was resumed is running, followed to the resumed run's end;
    # only then (or for the owner's stop) is its line taken back
    ("stopped by the grow and resumed", {"log_folder": True, "resuming": True, "result": GROWN}, [("t", True)],
     {"state": "launched", "launches": 1, "line": 126.5, "tidied": [
         (None, ({"state": runs.WAITING, "jobs": 16}, None), ENDED_NONE, 126.5, None),  # waiting for the boot
         (None, ({"state": runs.RESUMED}, "score run: started\n"), ENDED_NONE, 126.5, None),  # the resumed run goes on
         (None, ({"state": runs.RESUMED}, "score run: started\ndetached: ok exit=0 minutes=40 log=x outputs=y\n"),
          ENDED_NOW, 110.0, "closed: its batch ended done")],
      "polled": ({"state": runs.STOPPED}, "stopped")}),  # the owner's stop while it waited: ended
    # 2026-11-04: the next try wrote its line (EUR 200) while an ended try read the spend to take its own back; the
    # close landed on top, and the runner (its ceiling the store's newest line) read room EUR -0.00 for checkout 19.
    # Its room is its own line's (EUR 200 less 110), and spend that grew after the line was written (a stopped try's
    # nodes still billing: room EUR 5 under its high) is the guard's to hold, never a refusal of a try the line caps
    # (2026-11-08, checkout 60: EUR 0.99)
    ("an ended try's close under the next try's line", {"log_folder": True}, [("v", True)],
     {"state": "launched", "launches": 1, "line": 126.5, "tidied": [(200.0, None, None, None, None)],
      "superseded": True,
      "room": [None, 5.0]}),
    ("the benchmarks: one item, one batch at its high plus 10%", {"benchmarks": LISTED, "buy": ("benchmarks",)},
     [("e", True)],
     {"put": "benchmarks: EUR 1.50 to 6.31, 2 to run, 1 gaps",
      "proposal": ("benchmarks", {"title": "Benchmarks", "gaps.0.id": "batch-direct"}),
      "screen": {"items.benchmarks.likely": 1.5, "items.benchmarks.high": 2.81, "items.benchmarks.guessed": 3.5,
                 "items.benchmarks.nodes": 2, "items.benchmarks.blocked": False, "stop": round(6.31 * 1.1, 2),
                 "eta.likely_minutes": round(91.3 + 64.0, 1)},
      "state": "launched", "line": round(100.0 + 10.0 + 6.31 * 1.1, 2),  # spent, in flight, its high plus 10%
      "planned": [], "launched": [RunGroup((), (), benchmarks=True)], "launches": 1}),  # it plans each one itself
    ("his Google figure into the books", {"books_figure": True, "buy": ()}, [("figure", 1030)],
     {"status": 200, "said": ["EUR 1030.00 entered by joey"], "written": [(1030.0, "joey")], "checkouts": 0,
      "line": None, "launches": 0}),
    # what each item really cost (the ledger's lines since the checkout; an older run's line is not its), against
    # its forecast, with its new outputs and failed gates as each is made
    ("his results against the forecast", {"buy": ("alpha-pieces", "beta-pieces"), "bill": [
        ("closeup@alpha", 8.5, 25.0, None), ("closeup@alpha", 0.5, 0.0, None),
        ("closeup@beta", 99.0, 5.0, "2026-01-01T00:00:00Z")]}, [("j", True)],
     {"state": "launched", "launches": 1, "results": [
         (("alpha", (), {"tweak": 7}), {
             "euros": 9.0, "forecast.high_euros": 30.0, "items.#": 2, "items.0.id": "alpha-pieces",
             "items.0.euros": 9.0, "items.0.forecast.high_euros": 15.0, "items.0.nodes.#": 1,
             "items.0.nodes.0.new": True, "items.0.nodes.0.output": "made", "items.0.nodes.0.minutes": 25.0,
             "items.0.nodes.0.verdicts": [{"check": "looks", "answer": "pass", "reason": "0 faults"}],
             "items.1.euros": None, "items.1.nodes.0.output": None, "items.1.nodes.0.new": False}),
         (("beta", ("fail",), {"faults": 4, "tweak": 8}), {"items.1.new_outputs": 1, "items.1.failed_gates": 1})]})]

RUN_COMMANDS = [  # (id, the group, jobs, the conductor's cores, the runner command after its python)
    ("both nodes named", RunGroup(("alpha",), ("closeup@alpha", "pixal@alpha")), 8, 16,
     ["-m", "score", "run", "world1", "--place", "alpha", "--stage", "closeup@alpha", "--stage", "pixal@alpha",
      "--jobs", "8", "--detach"]),
    # a Buy's 16 jobs on an 8-core conductor run as 8, never refused (2026-11-10)
    ("16 jobs on 8 cores", RunGroup(("alpha",), ("closeup@alpha", "pixal@alpha")), 16, 8,
     ["-m", "score", "run", "world1", "--place", "alpha", "--stage", "closeup@alpha", "--stage", "pixal@alpha",
      "--jobs", "8", "--detach"]),
    ("the benchmarks' own batch", RunGroup((), (), benchmarks=True), 8, 8,
     ["-m", localrun.BENCHMARKS, "run", "--detach"])]


def counter_cleared():
    """No checkout, launch, plan or choice of an earlier press, and no backend call yet."""
    for model in (Checkout, Launch, Plan, BasketChoice, BasketItem):
        model.objects.all().delete()
    FakeBackend.calls.clear()


def world_before(shop, settings, knobs, patched, tmp_path):
    """The world his presses meet: the basket made, his choices, the backend's answers, the markers, the left rows;
    {"left": rows left launching, "put": prepare's benchmarks put twice, "written": the books' figures entered}."""
    import sys
    from score.review import concepts, web
    from score.dashboard.pages import actions
    from score.dashboard.proposals import benchmarks
    met = {"left": [], "written": []}
    shop.items = a_basket(settings, *knobs.get("basket", (["closeup@alpha", "closeup@beta"], None, ())))
    if "index" in knobs:
        root = settings.SCORE_HOME / "proposals"
        records.put_index(root, {**records.index(root), **knobs["index"]})
    if "benchmarks" in knobs:
        a_prepare_record(settings, knobs["benchmarks"])
        met["put"] = [benchmarks.put(settings.SCORE_HOME / "proposals", settings.SCORE_PROPS_HOME) for _ in "ab"]
        shop.items["benchmarks"] = records.item(settings.SCORE_HOME / "proposals", "benchmarks")
    if knobs.get("pick"):
        concepts.recorded(shop.store, "concepts/alpha/picks/20261021T090000.000000+0000.json",
                          {"place": "alpha", "sha": "a" * 64, "by": "joey", "at": "2026-10-21T09:00:00+00:00"})
    bought(shop, *knobs.get("buy", ("alpha-pieces",)), version=knobs.get("version"))
    for name in ("plan_buys", "ceiling", "paid_refused"):
        if name in knobs:
            patched.setattr(FakeBackend, name, knobs[name])
    patched.setattr(FakeBackend, "log_folder", str(tmp_path) if knobs.get("log_folder") else None)
    if knobs.get("agent_started"):
        patched.setattr(actions, "agent_started", lambda: True)
    if knobs.get("resuming"):
        patched.setattr(runs, "RUNS", tmp_path / "runs")
    if knobs.get("agent_env"):
        patched.setenv(AGENT_MARKERS[0], "1")
    if knobs.get("books_figure"):
        patched.setattr(web, "google_month", lambda euros, by: met["written"].append((euros, by)) or
                        {"month": "2026-10"})
    if not knobs.get("left"):
        return met
    gone = subprocess.Popen([sys.executable, "-c", "pass"])
    gone.wait()
    left = [Checkout.objects.create(key=key * 32, by="joey", state="launching", pid=pid)
            for key, pid in (("p", gone.pid), ("q", None))]  # None: a row from before the pid was kept
    stuck = Launch.objects.create(plan=Plan.objects.create(basket_hash=f"checkout-{left[0].pk}", made_by="joey",
                                                           state="ready", body={}), by="joey", jobs=1,
                                  state="starting")
    met["left"] = [*left, stuck]
    return met


def next_line_meanwhile(world, patched, euros):
    """The next try's line (EUR `euros`) written between an ended try's close check and its write, as checkout 19's
    was; the next try, once written."""
    from score.review import web
    reading, next_try = flow.spend_now, []
    ended_try = Checkout.objects.order_by("-pk").first()

    def spend_now(chosen, books=False):
        if not next_try:
            line = web.stop(world.store, "world1", euros, "checkout next: alpha", by="joey")
            next_try.append(Checkout.objects.create(
                key="w" * 32, by="joey", state="launching", totals=ended_try.totals,
                stop_line={"euros": line["euros"], "at": line["at"], "spent": 100.0, "reserved": 10.0}))
        return reading(chosen, books)
    patched.setattr(flow, "spend_now", spend_now)
    return next_try


def dug(found, path):
    """The value at a dotted path: a digit indexes a list, another name finds its item by id, "#" counts."""
    for part in path.split("."):
        if part == "#":
            return len(found)
        if isinstance(found, list) and not part.isdigit():
            found = next(each for each in found if each["id"] == part)
            continue
        found = found[int(part)] if isinstance(found, list) else found[part]
    return found


def pressed(client, presses, held, settings):
    """His presses in order ("again": the last checkout run again under a yes; "hosted": his checkout of what he
    chose, applied on the store's machine; "figure": his Google figure entered); (the last answer, the checkout ids
    each key gave, the seconds they took)."""
    import sys
    import time
    from score.dashboard.sync import applying
    holder = held and subprocess.Popen(
        [sys.executable, "-c", "import fcntl, sys, time; held = open(sys.argv[1], 'a'); fcntl.flock(held, "
         "fcntl.LOCK_EX); print('held', flush=True); time.sleep(float(sys.argv[2]))",
         str(settings.SCORE_HOME / "checkout.lock"), str(held)], stdout=subprocess.PIPE, text=True)
    try:
        assert not holder or holder.stdout.readline().strip() == "held"
        began, answer, ids = time.monotonic(), {}, {}
        for key, ticked in presses:
            if key == "again":
                found = Checkout.objects.order_by("-pk").first()
                found.chat_yes, found.state = ticked, "launching"
                flow.run(found, FakeBackend())
                continue
            if key == "hosted":
                seen = [{"id": each.item, "version": each.version} for each in BasketChoice.objects.all()]
                applied = applying.apply_checkout({"id": 3, "kind": "checkout", "user": "joey",
                                                   "payload": {"key": ticked * 32, "items": seen}})
                answer = {"said": applied.detail, "applied": applied.state, "launch_id": applied.launch_id}
                continue
            if key == "figure":
                given = client.post("/api/money/books-figure", json={"euros": ticked})
                answer = {**given.json(), "status": given.status_code}
                continue
            answer = checked_out(client, key, ticked)
            if answer.get("checkout"):
                ids.setdefault(key, set()).add(answer["checkout"]["id"])
        return answer, ids, time.monotonic() - began
    finally:
        if holder:
            holder.wait(timeout=10)


class Resuming(FakeBackend):
    """The fake backend reading its runs as the local backend does: a waiting or resumed run is running."""
    poll, handed_on = localrun.LocalBackend.poll, localrun.LocalBackend.handed_on


def registered(entry, resumed_log, folder):
    """The runner's registry entry w1 as `entry` says; resumed into this process, `resumed_log` written, when given."""
    resumed = {}
    if resumed_log is not None:
        (folder / "resumed.log").write_text(resumed_log)
        resumed = {"resumed": {"pid": os.getpid(), "log": str(folder / "resumed.log")}}
    runs.written(runs.RUNS / "w1.json", {"id": "w1", **entry, **resumed})


# --- a Buy approved in chat (checkout/chat_yes.py) ----------------------------------------------------------------

QUESTION = "Batch 1: EUR 0 spent so far; this try likely EUR 20, high EUR 30, its stop EUR 33. Batch total EUR 33?"


def chat_world(settings, door, tmp_path):
    """The shop as the conductor's door sees it: the owner set, the code on a pin read just now, no latch, no run, the
    agent markers set, the design approving alpha and beta, the runner's plan buying their close-ups; the kept plans
    of both places, their relations derived from an older plan; [how many plans each keeping of relations came
    after]."""
    import json
    from score import conductor
    from score.conductor import health
    from score.dashboard.checkout import chat_yes
    from score.dashboard.state import screens
    from score.review import holders
    from score.stages.complete.prepare import design
    settings.SCORE_OWNER = "joey"
    door.setattr(health, "code", lambda: {"checkout": "582df3eb" * 5, "pin": "582df3eb", "pin_at": chat_yes.now(),
                                          "matches": True})
    door.setattr(conductor, "FREE_ONLY_LATCH", tmp_path / "free-only")
    door.setattr(runs, "RUNS", tmp_path / "runs")
    door.setattr(screens, "approved_places", lambda world: ["alpha", "beta"])
    door.setattr(design, "designs", lambda store, data, places: {"places": {}, "approved": ["alpha", "beta"]})
    door.setattr(FakeBackend, "plan_buys", ["closeup@alpha", "closeup@beta"])
    door.delenv("SCORE_FREE_ONLY", raising=False)
    for name in AGENT_MARKERS:
        door.setenv(name, "1")
    for name in ("KEPT_PLANS", "KEPT_INVENTORY", "KEPT"):
        door.setattr(holders, name, tmp_path / name)
        (tmp_path / name).mkdir()
    for place in ("alpha", "beta"):
        (tmp_path / "KEPT_PLANS" / f"{place}.json").write_text(json.dumps({"w": 20.0, "d": 12.0, "items": [],
                                                                            "rows": {}, "shapes": {}}))
        (tmp_path / "KEPT_INVENTORY" / f"{place}.json").write_text(json.dumps({"rows": []}))
    kept_at, keep = [], holders.keep
    door.setattr(holders, "keep", lambda places: kept_at.append(
        sum(call[0] == "plan" for call in FakeBackend.calls)) or keep(places))
    return kept_at


def door_changed(knobs, door, tmp_path):
    """The door's world as a CHAT_REFUSED row's `knobs` say: the code against its pin, the owner's kill switch or a
    free-only process, a run claimed on the store, the design's approval unworkable."""
    from score import conductor
    from score.conductor import health
    from score.stages.complete.prepare import design
    code = health.code()
    door.setattr(health, "code", lambda: {**code, **knobs.get("code", {})})
    if knobs.get("latch") == "file":
        door.setattr(conductor, "FREE_ONLY_LATCH", tmp_path / "latched")
        conductor.FREE_ONLY_LATCH.write_text("")
    if knobs.get("latch") == "env":
        door.setenv("SCORE_FREE_ONLY", "1")
    if knobs.get("claimed"):
        door.setattr(runs, "RUNS", tmp_path / "claimed")
        assert runs.claim("abc", ["closeup@alpha"], os.getpid(), folder=runs.RUNS) is None
    if knobs.get("design"):
        door.setattr(design, "designs", unworkable)


def unworkable(store, data, places):
    raise OSError("the store's plans could not be read")


def given_yes(store, given):
    """The id of the yes a CHAT_REFUSED row quotes: "fresh" his yes now, "older" a yes naming a try's stop (before
    batch totals), else that id with no yes behind it."""
    from score.review import web
    if given == "fresh":
        return a_yes()["id"]
    if given == "older":
        older = {**a_yes(), "id": "20261025T000001Z", "stop_euros": 33.0}
        older.pop("batch_total_euros")
        web.buy_yes_written(store, older)
        return older["id"]
    return given


def chat_buy(yes_id, **given):
    """(Checkout or None, words or the refusal)."""
    from score.dashboard.checkout import chat_yes
    try:
        return chat_yes.buy(yes_id, **given)
    except chat_yes.Refused as refused:
        return None, f"refused: {refused}"


def a_yes(total=33.0, high=30.0, leave_out=()):
    from score.dashboard.checkout import chat_yes
    return chat_yes.record(total, high, "Yes, buy it", QUESTION, leave_out=leave_out)


YES_UNRECORDED = [  # (id, his yes as chat_yes.record takes it, the refusal's words)
    ("a total not above 0", ("nan", 30.0, "Yes, buy it", QUESTION), "above EUR 0"),
    ("no answer quoted", (33, 30, "", QUESTION), None)]
CHAT_REFUSED = [  # (id, the door's world, the yes he quotes, the refusal's words): refused before the yes is spent
    ("no yes behind the id", {}, "20261025T000000Z", "no quoted Buy yes"),
    ("a try's stop, not a batch total", {}, "older", "names a try's stop, not the batch total"),
    ("code off the pin", {"code": {"matches": False, "checkout": "0" * 40}}, "fresh",
     "is not the cockpit's pin 582df3eb"),
    ("the pin read long ago", {"code": {"pin_at": "2026-10-01T00:00:00+00:00"}}, "fresh", "not in the last 30 minutes"),
    ("his kill switch latched", {"latch": "file"}, "fresh", "latched off"),
    ("a free-only process", {"latch": "env"}, "fresh", "latched off"),
    ("a run active on the store", {"claimed": True}, "fresh", "a run is active"),
    # the design's approval now cannot be worked out: refused with its cause
    ("the design unworkable", {"design": True}, "fresh",
     "the approved places could not be worked out now: OSError: the store's plans")]
TWO_PHASES = ["closeup@alpha", "pixal@alpha"]  # the basket of two phases' rows
THREE_ROWS = ["closeup@alpha", "closeup@beta", "pixal@beta"]
CHAT_SELECTED = [  # (id, the basket's rows, the stages his yes leaves out, the Buy's --phase/--place/--leave-place,
    # the stages its one run names (() nothing launched) or the refusal's words, the plan's selection it asked for
    # (None: refused before planning), the field its checkout's yes names)
    ("stages left out: nothing left is no launch", ["closeup@alpha", "closeup@beta"], ("closeup",), {}, (),
     {"phase": None, "places": None}, None),
    # by phase (owner, 2026-11-06, CONTEXT.md "phase"): only that phase's nodes, under the same yes and batch total
    ("an unknown phase", TWO_PHASES, (), {"phase": "lighting"}, "lighting is no phase", None, None),
    ("by phase", TWO_PHASES, (), {"phase": "models"}, ("closeup@alpha",), {"phase": "models", "places": None},
     ("phase", "models")),
    # by place (the door's buy --place / --leave-place; `score run --place` its model): a left-out place's rows are
    # neither bought nor a "would also buy" refusal (which rows: PLACES_LEFT)
    ("an unknown place", THREE_ROWS, (), {"places": "gamma"}, "gamma is no place", {"phase": None, "places": "gamma"},
     None),
    ("--leave-place alpha", THREE_ROWS, (), {"leave_places": "alpha"}, ("closeup@beta",),
     {"phase": None, "places": None}, ("leave_places", "alpha")),
    ("--place alpha", THREE_ROWS, (), {"places": "alpha"}, ("closeup@alpha",), {"phase": None, "places": "alpha"},
     ("places", "alpha"))]
CHAT_TRIES = [  # (id, the spend now with what is in flight, what his Buy under the one yes (EUR 100) leaves: its
    # state, its words, the stop line, the batch's (budget, used) on its line, the next question's figures after it,
    # its run ended after it, the places prepare's saved design record approves). His yes is the batch's budget
    # (owner, 2026-10-26: "those budget asks should become per batch tho, not per try"): the stop line the batch's
    # start plus it, a retry needing no new ask and keeping it, launched while any is left even when its stop needs
    # more (owner, 2026-10-27: "not just stop when u got to the limit, like ur supposed to"), refused once none is
    # left
    ("his yes, the basket grown since", 100.0,
     {"state": "launched", "line": 110.0 + 100.0, "budget": (100.0, 0.0), "saved": ["alpha"]}),
    ("the same yes while its run runs", 100.0, {"said": "still running", "line": 210.0, "ended": True}),
    ("a retry: the same budget, 80 left", 120.0,
     {"state": "launched", "key": "-retry-1", "line": 210.0, "budget": (100.0, 20.0), "figures": {
         "batch": 1, "tries": 2, "retry": True, "try.stop": 33.0, "fits": 53.0, "click": 100.0, "may_stop": False,
         "money.budget": 100.0, "money.spent": 10.0, "money.in_flight": 10.0, "money.left": 80.0}}),
    ("10 left for a try needing 33: it stops at the line", 190.0,
     {"state": "launched", "said": "may stop at the batch limit", "line": 210.0, "figures": {"may_stop": True}}),
    ("nothing left", 200.0, {"state": "refused", "said": "the batch budget is spent: EUR 100.00", "line": 210.0})]

# --- the batch's one budget, its remakes and what a basket keeps (judged on their own) -----------------------------

FIRST = {"euros": 553.08, "spent": 0.0, "reserved": 0.0}
SPLIT = {"euros": 665.18, "spent": 297.18, "reserved": 0.0, "batch_from": 297.18, "batch_budget": 368.0}
BEFORE_BUDGETS = {"euros": 596.76, "spent": 300.0, "reserved": 0.0, "high": 100.0}  # Batch 1's first line
BUDGETED = {"euros": 665.18, "batch_from": 0.0, "batch_budget": 665.18}
HIS_RETRY = {"id": "y", "retry": 1, "batch_total_euros": 462.0}
BUDGETS = [  # (id, the batch's tries as (stop line, his yes's id), this try last; the spend now with what is in
    # flight; this try's need; his yes; (start, budget) or the refusal's words)
    # a batch whose first try wrote its line before budgets counts from what that line was written over
    ("counted from an older first try's line", [(BEFORE_BUDGETS, None), ({}, None)], 710.0, 250.0,
     {"batch_total_euros": 740.0}, (300.0, 740.0)),
    # a total under the spend plus this try's stop still launches: the try stops at the line (owner, 2026-10-27)
    ("a total under the spend plus its stop", [(BEFORE_BUDGETS, None), ({}, None)], 710.0, 250.0,
     {"batch_total_euros": 659.99}, (300.0, 659.99)),
    ("a total the batch has spent", [(BEFORE_BUDGETS, None), ({}, None)], 710.0, 250.0,
     {"batch_total_euros": 410.0}, "the batch total he approved is spent: EUR 410.00"),
    ("a new batch: its own stop", [({}, None)], 710.0, 33.0, None, (710.0, 33.0)),
    # a try once counted as a batch of its own (2026-10-26, checkouts 5 and 6 from EUR 297.18): its budget is read
    # from the batch's start, so the total stays the line, EUR 665.18
    ("a try once its own batch", [(FIRST, None), (SPLIT, None), ({}, None)], 300.0, 33.0, None, (0.0, 665.18)),
    # 2026-11-03: his yes's first checkout was refused before its line (books unknown); the next try under it sets
    # the total he approved, never the batch's older, larger budget, and a retry never goes above that total
    ("his yes's first try refused before its line", [(BUDGETED, None), ({}, "y"), ({}, "y")], 289.6, 180.52,
     HIS_RETRY, (0.0, 462.0)),
    ("a retry under a larger line of his yes",
     [(BUDGETED, None), ({"euros": 700.0, "batch_from": 0.0, "batch_budget": 700.0}, "y"), ({}, "y")], 289.6, 180.52,
     HIS_RETRY, (0.0, 462.0))]

FAILED = {1: {"sound@alpha", "settle@alpha"}, 2: {"sound@alpha", "settle@alpha", "closeup@beta"}}
TRIED = ((1, 1), (2, 3))  # (checkout, hours after the remakes' start)
REMADE = [  # (id, the tries, the nodes each failed, the results that are gaps now): one paid remake, then a gap
    ("failed twice: gaps", TRIED, FAILED, ["settle@alpha", "sound@alpha"]),
    ("failed once: its one paid remake still to come", TRIED[:1], FAILED, []),
    ("a failure before the remakes' start", ((3, -24), (2, 3)), {3: {"settle@alpha"}, 2: {"settle@alpha"}}, [])]
FREE_FIRST = [  # (id, the nodes each try failed, the hours after the start this PC's free pass of settle@alpha
    # came, the waits' words): a try stopped on a stage this PC runs free waits for that pass (B6)
    ("stopped on a free stage", FAILED, None, ["checkout 2 stopped on settle@alpha, which this PC runs free"]),
    ("its free pass came since", FAILED, 4, []),
    ("cloud only: no wait", {1: set(), 2: {"closeup@beta"}}, None, [])]

PRICE = {"likely": 1.0, "high": 2.0}
FILM_ITEMS = [{"id": "a", "nodes": {"closeup@a": PRICE, "demo-film@a": PRICE}},
              {"id": "f", "nodes": {"demo-film-extra@b": PRICE}}]
NEEDS = {"closeup@alpha": set(), "closeup@beta": set(), "pixal@beta": {"closeup@alpha"}, "sky": set(),
         "film": {"closeup@alpha", "closeup@beta"}, "light@alpha": {"sky"}}
BY_PLACE = [{"id": "a", "nodes": dict.fromkeys(NEEDS, PRICE)},
            {"id": "bench", "benchmarks": True, "nodes": {"benchmark-1": PRICE}}]
PLACES_LEFT = [  # (id, the places chosen, the places left out, the nodes left out of the Buy): a left-out place's
    # rows, a row needing one, and under --place every environment row its places do not need
    ("--leave-place alpha", set(), {"alpha"}, {"closeup@alpha", "light@alpha", "pixal@beta", "film"}),
    ("--place alpha", {"alpha"}, set(), {"closeup@beta", "pixal@beta", "film", "benchmark-1"}),
    ("--place alpha,beta", {"alpha", "beta"}, set(), {"benchmark-1", "film"}),
    ("every place", set(), set(), set())]


# --- the launch guard and the local backend ----------------------------------------------------------------------

def basket_of(*pairs):
    """Basket entries as the guard reads them: (place, stage), place "" for an environment stage."""
    return [types.SimpleNamespace(place=place, stage=stage) for place, stage in pairs]


GROUPED = [  # (id, the basket, the runner groups it is launched as)
    ("same stages join", basket_of(("alpha", "closeup"), ("beta", "closeup"), ("", "terrain")),
     [RunGroup((), ("terrain",)), RunGroup(("alpha", "beta"), ("closeup",))]),
    ("other stages apart", basket_of(("alpha", "closeup"), ("beta", "closeup"), ("beta", "plan"), ("", "terrain")),
     [RunGroup((), ("terrain",)), RunGroup(("alpha",), ("closeup",)), RunGroup(("beta",), ("closeup", "plan"))])]

UNMEASURED = {"likely_euros": None, "high_euros": None, "guess_euros": 7.5, "runs": 0}
WORKED = [  # (id, the basket, the runner's price of each node, the plan's money and time as the guard works it out)
    ("measured", GROUPED[0][1], FakeBackend.price_of,
     {"high": 2 * 15.0, "likely": 2 * 10.0, "not_measured": [], "room": 250.0 - 100.0 - 10.0},
     {"likely_minutes": 30.0, "high_minutes": 45.0}),  # one line each, 4 jobs at once
    ("unmeasured held at its estimate in the high only", basket_of(("alpha", "closeup")), UNMEASURED,
     {"high": 7.5, "likely": 0.0, "not_measured": ["closeup@alpha"]}, None)]

REFUSED = [  # (id, edits to the worked-out plan, refusals' arguments, the store writable, every refusal in words)
    ("a good plan", {}, {}, True, []),
    ("not the owner", {}, {"user_is_owner": False}, True, ["only the owner launches"]),
    ("the basket changed", {}, {"current_hash": "other"}, True,
     ["the basket changed since the plan: work it out again"]),
    ("a launch still running", {}, {"running": True}, True, ["another launch from this dashboard is still running"]),
    ("not ticked", {}, {"confirmed": False}, True, ["tick \"I launch this\""]),
    ("over the room", {"money.high": 200.0}, {}, True,
     ["cannot finish under the stop: high EUR 200.00, room EUR 140.00"]),
    ("no room known", {"money.room": None, "money.note": "no bill"}, {}, True,
     ["no room under a stop is known: no bill"]),
    ("older than 15 minutes", {"age_minutes": 16}, {}, True,
     [f"the plan is older than {guard.PLAN_MINUTES} minutes: work it out again"]),
    ("inputs missing", {"groups.0.missing": ["data/kit/alpha.json"]}, {}, True,
     ["inputs are missing: data/kit/alpha.json"]),
    ("a re-buy without its reason", {"groups.0.refusal": "refused: re-buys", "rebuys": 9.0}, {}, True,
     [f"it buys accepted outputs again for EUR 9.00, over EUR {guard.REBUY_LIMIT:.0f}: write the reason"]),
    ("a re-buy with its reason", {"groups.0.refusal": "refused: re-buys", "rebuys": 9.0},
     {"rebuy_reason": "the lamp changed"}, True, []),
    ("a read-only store", {}, {}, False, ["the store is read-only here (SCORE_STORE_WRITABLE=0)"])]


def edited(plan, edits):
    """A copy of the plan with dotted-path edits to its body (`age_minutes` ages its finish instead)."""
    import copy
    found = copy.deepcopy(plan)
    for path, value in edits.items():
        if path == "age_minutes":
            found.finished = timezone.now() - datetime.timedelta(minutes=value)
            continue
        *parents, last = path.split(".")
        held = found.body
        for part in parents:
            held = held[int(part)] if part.isdigit() else held[part]
        held[last] = value
    return found


def runner_answer(code, stdout):
    """A runner command's answer, as subprocess.run gives it."""
    return lambda command: subprocess.CompletedProcess(command, code, stdout, "")


LAUNCHED = [  # (id, the runner's answer to `score run --detach`, the handle's pid, log and refusal, its state)
    ("detached", runner_answer(0, "paid rows ...\ndetached: started pid=4242 log=/tmp/x.log\n"),
     (4242, "/tmp/x.log", None), None),
    ("refused before detaching", runner_answer(1, "refused: this run would buy accepted outputs again"),
     (None, None, "refused: this run would buy accepted outputs again"), "refused")]

POLLED = [  # (id, the run's log, its pid still alive, the state the backend reads)
    ("ok", "working\ndetached: ok exit=0 minutes=3 log=x\n", False, "done"),
    ("failed", "working\ndetached: failed exit=1\n", False, "failed"),
    ("stopped", "working\ndetached: stopped by signal 15 exit=143\n", False, "stopped"),
    ("refused", "working\ndetached: refused: another run holds the store exit=1\n", False, "refused"),
    ("still going", "working\n", True, "running"),
    ("gone without its result line", "working\n", False, "failed")]


def test_a_batch_buys_only_what_the_owner_approved(shop, settings, tmp_path, monkeypatch, capsys):
    """His checkout, one world all through: the basket's prices (each node once, the unmeasured and unpriced apart);
    the batch's one budget across its tries, its paid remakes and free waits, env1's cap and what a Buy without the
    film, by phase or by place keeps, each judged on its table's rows;
    each press of his against a counter cleared of the last one's checkouts, refused in words, launched as one run at
    the batch's high plus 10%, or refused, failed or done after its line, as the PRESSES row says (pressed here or
    applied on the store's machine; the Benchmarks item one batch of its own; his Google figure into the books),
    then each pass's taking back of an ended batch's line and his results against the forecast. Then his Buys in
    chat at the conductor's door: a yes refused in words for all he did not approve, his Buys by stage, phase and
    place, and one yes's tries of its batch under its one budget. Then the launch
    guard's way in, one basket all through: it groups the basket for the runner, works its plan out
    from the backend (the runner prices; an unmeasured node held at its estimate in the high only), refuses a
    launch in words for every reason, launches through the confirm page only when ticked and follows the run to
    its result; the local backend under it gives the runner its command and an environment without the dashboard's
    secrets, prices through `score price`, reads the ledger by node since the batch, and reads each result line as
    its state. The real `score run --detach` of a run with nothing to make and nothing paid (the camp's physics
    layer: a stage for the places with physics data only, so the run holds no node at all) runs beside the rest in
    this test's own PROPS_HOME and ends on its result line."""
    import json
    import time
    from score.dashboard import __main__ as commands
    from score.dashboard.checkout import chat_yes, watched
    from score.review import holders, web
    real = localrun.LocalBackend()
    started = real.launch(RunGroup(("camp",), ("physics-layer",)), 1, None)  # before this test's environment
    assert started.refused is None and started.pid and pathlib.Path(started.log).is_file(), started
    for name, jobs, totals, cleared in PRICED:
        found = pricing.totals(pricing.basket_prices(PRICED_ITEMS), jobs=jobs)
        assert {key: found[key] for key in totals} == totals and pricing.cleared_high(found) == cleared, (name, found)
    for name, tries, spent, need, his, expected in BUDGETS:  # the batch's one budget across its tries
        batch = [Checkout(stop_line=dict(line), chat_yes={"id": yes} if yes else {}) for line, yes in tries]
        try:
            found = flow.batch_budget(batch, spent, need, his)
        except flow.Refused as refused:
            found = f"refused: {refused}"
        assert found == expected if isinstance(expected, tuple) else expected in found, (name, found)
    # the guard's measure reads the budget from the batch's start too; env1's cap shows the bill's figure the watcher
    # read (the plan of 2026-11-09, B7): the cap record's, on the door
    lined = [Checkout(stop_line=dict(FIRST)), Checkout(stop_line=dict(SPLIT))]
    reading = types.SimpleNamespace(spent=300.0, reserved=0.0, parts={}, as_of="now")
    assert watched.batch_money(lined, reading)["budget"] == 665.18
    with monkeypatch.context() as capped:
        capped.setenv("SCORE_CAP_BOOK", str(tmp_path / "caps"))  # the guard's folder book, never the object store
        assert web.cap_figure() is None  # no cap set: none shown
        for part, record in (("lines", {"at": "2026-11-09T18:40:00+00:00", "name": "env1", "open": True,
                                        "euros": 300.0, "line": 255.0, "start": "2026-11-09T18:40:00+00:00",
                                        "baseline": {}}),
                             ("readings", {"at": "2026-11-10T08:00:00+00:00", "unread": None, "counter": 41.237})):
            (tmp_path / "caps" / "caps" / "env1" / part).mkdir(parents=True)
            (tmp_path / "caps" / "caps" / "env1" / part / "20261110T080000-1.json").write_text(json.dumps(record))
        cap = web.cap_figure()
    assert (cap["counter"], cap["euros"], cap["line"], cap["unread"]) == (41.24, 300.0, 255.0, None)
    assert watched.batch_money(lined, reading, cap)["cap"] == cap
    assert commands.cap_words(cap).startswith("env1: EUR 41.24 of 300 (bill, all projects), stop line EUR 255")
    def tried(each):
        return [Checkout(pk=pk, at=flow.REMAKES_FROM + datetime.timedelta(hours=hours)) for pk, hours in each]
    for name, tries, failed, gaps in REMADE:
        assert flow.remade_out(tried(tries), failed) == gaps, name
    tries = tried(TRIED)
    for name, failed, hours, waits in FREE_FIRST:
        passed = None if hours is None else (flow.REMAKES_FROM + datetime.timedelta(hours=hours)).isoformat()
        found = flow.free_first(tries, failed, lambda node, passed=passed: passed if node == "settle@alpha" else None)
        assert len(found) == len(waits) and all(words in each for words, each in zip(waits, found)), (name, found)
    assert [flow.free_route(node) for node in ("settle@alpha", "sound@alpha", "people-body-pilot-made")] == \
        [True, False, False]
    items = [{"id": "a", "nodes": {"settle@alpha": {}, "pixal@alpha": {}}}, {"id": "b", "nodes": {"sound@alpha": {}}}]
    assert flow.nodes_left(items, {"settle@alpha", "sound@alpha"}) == [{"id": "a", "nodes": {"pixal@alpha": {}}}]
    # without the film (owner, 2026-11-03): its stages' rows are taken out of the items, so neither priced nor bought
    assert flow.left_out(FILM_ITEMS, chat_yes.NO_FILM) == [{"id": "a", "nodes": {"closeup@a": PRICE}}]
    assert flow.left_out(FILM_ITEMS, ()) == FILM_ITEMS
    # by phase (owner, 2026-11-06, CONTEXT.md "phase"): only that phase's nodes, several phases at once their queues
    # side by side in one run; an unknown stage or phase refused
    assert flow.phase_kept(FILM_ITEMS, "film") == [{"id": "a", "nodes": {"demo-film@a": PRICE}},
                                                   {"id": "f", "nodes": {"demo-film-extra@b": PRICE}}]
    assert flow.phase_kept(FILM_ITEMS, None) == FILM_ITEMS
    kept = {phase: {node for item in flow.phase_kept(FILM_ITEMS, phase) for node in item["nodes"]}
            for phase in ("film", "models", "film,models")}
    assert kept["film,models"] == kept["film"] | kept["models"] and kept["film"] and kept["models"], kept
    assert chat_yes.known_stages("closeup,pixal") == ["closeup", "pixal"]
    for known, given in ((chat_yes.known_stages, "closeup,no-such-stage"),
                         (chat_yes.known_phase, "models,no-such-phase")):
        with pytest.raises(chat_yes.Refused):
            known(given)
    for name, chosen, out, left in PLACES_LEFT:  # by place (the door's buy --place / --leave-place)
        assert flow.places_left(BY_PLACE, chosen, out, NEEDS.__getitem__) == left, name
    client = api()
    for name, knobs, presses, left in PRESSES:
        counter_cleared()
        before = stop_line(shop)
        with monkeypatch.context() as patched:
            met = world_before(shop, settings, knobs, patched, tmp_path)
            screen = client.get("/api/screens/buy").json() if "screen" in left else {}
            assert all(dug(screen, path) == value for path, value in left.get("screen", {}).items()), (name, screen)
            assert "put" not in left or met["put"][0] == left["put"], (name, met["put"])
            if "proposal" in left:
                ident, fields = left["proposal"]
                root = settings.SCORE_HOME / "proposals"
                assert [each["id"] for each in records.items(root)].count(ident) == 1, name  # a second put replaces
                assert all(dug(records.item(root, ident), path) == value for path, value in fields.items()), name
            answer, ids, took = pressed(client, presses, knobs.get("held"), settings)
            record, line = Checkout.objects.order_by("-pk").first(), stop_line(shop)
            assert all(words in answer.get("said", "") for words in left.get("said", ())), (name, answer)
            assert left.get("checkouts", Checkout.objects.count()) == Checkout.objects.count(), name
            assert all(len(given) == 1 for given in ids.values()), (name, ids)  # the same key, the same checkout
            assert "state" not in left or record.state == left["state"], (name, record.state, record.detail)
            assert all(words in record.detail for words in left.get("detail", ())), (name, record.detail)
            assert left.get("line", 0) is not None or line == before, (name, line)  # no line written
            if left.get("line"):
                assert line["at"] != (before or {}).get("at") and line["by"] == "joey", (name, line)
                assert line["euros"] == left["line"] and left.get("reason", "") in line["reason"], (name, line)
                assert left.get("before", line["before"]) == line["before"], (name, line)
            written = record.stop_line if record is not None else {}
            assert "closed" not in left or written["closed"]["euros"] == left["closed"], (name, written)
            assert "high" not in left or written["high"] == left["high"], (name, written)
            planned = [call[1] for call in FakeBackend.calls if call[0] == "plan"]
            assert left.get("planned", planned) == planned, (name, planned)
            assert len(launches()) == left["launches"], (name, launches())
            assert all("the owner's checkout" in call[3] for call in launches()), name
            assert "planned" not in left or [call[1] for call in launches()] == left.get("launched", planned), name
            if record is not None and record.state == "launched":
                assert record.launch is not None, name
                assert [item["id"] for item in record.items if item["id"] != "take-cheap"] == \
                    list(knobs.get("buy", ("alpha-pieces",))), (name, record.items)
            taken = next((item for item in getattr(record, "items", ()) if item["id"] == "take-cheap"), None)
            assert "taken" not in left or (sorted(taken["nodes"]) == left["taken"] and record.totals["nodes"] == 10), \
                (name, record.items)
            assert "run" not in left or basket.batch_state(record)[0] == left["run"], (name, basket.batch_state(record))
            assert took >= left.get("waited", 0), (name, took)
            for each in met["left"]:
                each.refresh_from_db()
                assert each.state == "failed", (name, each)
                assert isinstance(each, Launch) or f"(pid {each.pid}) ended before it launched" in each.detail, name
            if "result" in knobs:
                pathlib.Path(record.launch.handles[0]["log"]).write_text(knobs["result"])
            shown = basket.last_checkout()
            assert "last" not in left or shown.startswith(f"Checkout {record.pk}: {left['last'][0]}."), (name, shown)
            assert all(words in shown for words in left.get("last", ())[1:]), (name, shown)
            assert "applied" not in left or (answer["applied"], answer["launch_id"]) == \
                (left["applied"], record.launch_id) and record.launch_id is not None, (name, answer)
            assert left.get("status", answer.get("status")) == answer.get("status"), (name, answer)
            assert met["written"] == left.get("written", []), (name, met["written"])
            next_try, chosen = [], Resuming() if knobs.get("resuming") else FakeBackend()
            for meanwhile, run, said, euros, reason in left.get("tidied", ()):
                next_try = next_try or meanwhile and next_line_meanwhile(shop, patched, meanwhile)
                if run:
                    registered(*run, tmp_path)
                found = flow.tidied(chosen)
                line = stop_line(shop)
                assert said is None or found == said, (name, found)
                assert euros is None or line["euros"] == euros, (name, line)
                assert reason is None or f"checkout {record.pk} {reason}" in line["reason"], (name, line)
            if "polled" in left:
                registered(left["polled"][0], None, tmp_path)
                handle = LaunchHandle(command=[], log=record.launch.handles[0]["log"])
                assert Resuming().poll(handle).state == left["polled"][1], name
            if left.get("superseded"):
                record.refresh_from_db()
                assert line["at"] == next_try[0].stop_line["at"] and record.stop_line["closed"]["superseded"], \
                    (name, line, record.stop_line)
            for room in left.get("room", ()):  # the runner's ceiling: the store's newest line
                patched.setattr(FakeBackend, "ceiling", line["euros"])
                patched.setattr(FakeBackend, "spent",
                                FakeBackend.spent if room is None else line["euros"] - FakeBackend.reserved - room)
                assert flow.room_refusals(next_try[0], FakeBackend()) == "", (name, room)
            if "bill" in knobs:
                since = record.at.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                patched.setattr(FakeBackend, "bill", [Billed(node, euros, minutes, at or since)
                                                      for node, euros, minutes, at in knobs["bill"]])
            for (place, extra, options), fields in left.get("results", ()):
                new = fixture.made(shop.store, shop.root / "work", "closeup", place, *extra, minutes_ago=0, **options)
                shop.source.refresh()  # the cockpit reads the store's index again within a minute; the test at once
                found = client.get(f"/api/checkout/{record.pk}/results").json()
                assert all(dug(found, path) == (new if value == "made" else value)
                           for path, value in fields.items()), (name, place, found)
            assert "results" not in left or \
                client.get(f"/api/checkout/{record.pk + 999}/results").status_code == 404, name
    # his Buy approved in chat (checkout/chat_yes.py), at the conductor's door: a yes refused in words for what he
    # did not approve, then his Buys by stage, phase and place, then one yes's tries of its batch
    counter_cleared()
    before = stop_line(shop)
    with monkeypatch.context() as door:
        kept_at = chat_world(settings, door, tmp_path)
        for name, given, words in YES_UNRECORDED:
            with pytest.raises(chat_yes.Refused, match=words):
                chat_yes.record(*given)
        for name, knobs, given, words in CHAT_REFUSED:
            with monkeypatch.context() as changed:
                door_changed(knobs, changed, tmp_path)
                yes_id = given_yes(shop.store, given)
                record, said = chat_buy(yes_id)
            assert record is None and words in said and not web.buy_yes_used(shop.store, yes_id), (name, said)
        assert not Checkout.objects.exists() and not launches() and stop_line(shop) == before
        with monkeypatch.context() as selecting:
            from score import stages
            from score.graph import chain
            from score.stages import phases
            made = []  # the plan's selection each Buy asks for
            selecting.setattr(flow, "basket_made", lambda **given: made.append(given))
            selecting.setattr(FakeBackend, "plan_buys", None)  # the run's plan buys the close-ups its --stage names
            selecting.setattr(FakeBackend, "log_folder", tmp_path)  # each run writes its result line: done
            selecting.setattr(phases, "PHASES", (("models", ("closeup",)), ("surfaces", ("pixal",))))
            selecting.setattr(phases, "NAMES", ("models", "surfaces"))
            selecting.setattr(stages, "runner", lambda: types.SimpleNamespace(
                world=None, store=None, nodes_named=lambda names: list(names)))
            selecting.setattr(stages, "places", lambda world, store: ["alpha", "beta"])
            selecting.setattr(chain, "upstream", lambda runner, starts: NEEDS[starts[0]])
            for name, rows, leave_out, given, bought, asked, named in CHAT_SELECTED:
                shop.items, ran, plans = a_basket(settings, rows), len(launches()), len(made)
                yes = a_yes(leave_out=leave_out)
                assert yes.get("leave_out", []) == list(leave_out), (name, yes)
                record, said = chat_buy(yes["id"], **given)
                assert made[plans:] == ([asked] if asked else []), (name, made)
                if isinstance(bought, str):
                    assert record is None and bought in said and not web.buy_yes_used(shop.store, yes["id"]), \
                        (name, said)
                elif bought:
                    assert record is not None and record.state == "launched", (name, said)
                    assert len(launches()) == ran + 1 and launches()[-1][1].stages == bought, (name, launches())
                    assert record.chat_yes[named[0]] == named[1], (name, record.chat_yes)
                else:
                    assert len(launches()) == ran and (record is None or record.state != "launched"), (name, said)
                    assert chat_yes.basket_totals(chat_yes.current_basket(), yes["leave_out"])["high_euros"] == 0
        # one yes's batch: the kept relations older than their plans (the sync paused, 2026-11-12: Buy 91 built 4
        # places' scene records from them), the saved basket alpha's alone, at its first try the design's saved
        # record beta unapproved; the runner's plan grew by beta's row since (free work moved it due, 2026-11-05)
        # and the design now approves it: the Buy derives the relations again before it plans, makes the basket
        # again from the plan now and buys it under his yes, its high EUR 30 above his 15, no new ask and no "would
        # also buy" (owner, 2026-11-05: "A BUY IS TILL THE END OF THE BUDGET OR UNTIL THE END GOAL ENV1 DONE IS
        # COMPELTED")
        counter_cleared()
        kept_at.clear()
        for place in ("alpha", "beta"):
            (tmp_path / "KEPT" / f"{place}.json").write_text("{}")
        capsys.readouterr()
        door.setattr(FakeBackend, "log_folder", None)
        shop.items = a_basket(settings, ["closeup@alpha"])
        yes = a_yes(total=100.0, high=15.0)
        assert [item["id"] for item in yes["basket"]["items"]] == ["alpha-pieces"] and yes["by"] == "joey"
        assert [item["id"] for item in records.items(settings.SCORE_HOME / "proposals")] == ["alpha-pieces"]
        from score.dashboard.state import screens
        tries, kept_first = [], None
        for name, spent, left in CHAT_TRIES:
            door.setattr(FakeBackend, "spent", spent)
            door.setattr(screens, "approved_places", lambda world, saved=left.get("saved", ["alpha", "beta"]): saved)
            record, said = chat_buy(yes["id"])
            line = stop_line(shop)
            assert "state" not in left or (record is not None and record.state == left["state"]), (name, said)
            assert left.get("said", "") in said and line["euros"] == left["line"], (name, said, line)
            assert line["by"] == f"joey, approved in chat at {yes['at']}", (name, line)
            assert record is None or record.key.endswith(left.get("key", "")), (name, record.key)
            assert "budget" not in left or \
                (record.stop_line["batch_budget"], record.stop_line["batch_used"]) == left["budget"], (name, record)
            found = chat_yes.figures(FakeBackend().spend)  # what the next question names: the batch's, not the try's
            assert {path: dug(found, path) for path in left.get("figures", {})} == left.get("figures", {}), name
            assert "figures" not in left or found["money"] == watched.newest(reading=FakeBackend().spend)["money"]
            tries += [record] if "state" in left else []
            kept_first = list(kept_at) if kept_first is None else kept_first  # his first Buy's keeps: one, before plan
            if left.get("ended"):  # a retry of its batch never while it runs; its run ends, the later ones' at once
                assert len(launches()) == 1 and Checkout.objects.count() == 1, name
                Launch.objects.update(state="done")
                door.setattr(FakeBackend, "log_folder", tmp_path)
        first = tries[0]
        assert kept_first == [0] and "relations kept before the plan: alpha, beta changed" in capsys.readouterr().out
        assert json.loads((tmp_path / "KEPT/alpha.json").read_text())["plan"] == holders.plan_sha(
            (tmp_path / "KEPT_PLANS/alpha.json").read_text())
        (tmp_path / "KEPT/alpha.json").write_text("{}")  # a Buy by place keeps that place's relations only
        (tmp_path / "KEPT/beta.json").write_text("{}")
        assert chat_yes.relations_kept("beta") == "relations kept before the plan: beta changed"
        assert chat_yes.relations_kept() == "relations kept before the plan: alpha changed"
        assert chat_yes.relations_kept() == "relations kept before the plan: none changed"
        assert [item["id"] for item in first.items] == ["alpha-pieces", "beta-pieces"]
        assert launches()[0][1].stages == ("closeup@alpha", "closeup@beta")
        assert first.by == f"joey, approved in chat at {yes['at']}"
        assert first.chat_yes["answer"] == "Yes, buy it" and first.chat_yes["question"] == QUESTION
        assert len(launches()) == 3 and all(os.getenv(name) == "1" for name in AGENT_MARKERS)  # back once launched
        assert watched.newest()["yes"]["answer"] == "Yes, buy it"
        assert flow.batch_budget(tries, 200.0, 33.0, None) == (110.0, 123.0)  # a click raises the budget
        # each checkout's rows are read once a pass over the checkouts (2026-11-09: 51 tries, 4,549 plan reads, 283 s)
        read, nodes_of = [], watched.checkout_nodes
        door.setattr(watched, "checkout_nodes", lambda one: read.append(one.pk) or nodes_of(one))
        assert watched.batch_of(list(Checkout.objects.order_by("at")), lambda node: None)[0] == 1
        assert sorted(read) == sorted(each.pk for each in tries[:3]), read
        # a Buy without --phase or --place plans the whole environment; with them, only those (2026-11-11: a phase's
        # Buy planned every place for over 50 minutes), the runner's own --phase and --place
        planned = [call[1] for call in FakeBackend.calls if call[0] == "plan"]
        assert planned[0].places == () and planned[0].phases == () and planned[0].stages == (), planned
        flow.basket_made(phase="models,surfaces", places="alpha")
        asked = [call[1] for call in FakeBackend.calls if call[0] == "plan"][-1]
        assert asked.places == ("alpha",) and asked.phases == ("models", "surfaces") and asked.stages == (), asked
        assert localrun.plan_command(asked)[4:] == ["world1", "--place", "alpha", "--phase", "models", "--phase",
                                                    "surfaces", "--json"]
    for name, group, jobs, cores, tail in RUN_COMMANDS:
        assert localrun.run_command(group, jobs, None, cores=cores)[1:] == tail, name
    counter_cleared()
    for name, entries, groups in GROUPED:
        assert guard.run_groups(entries) == groups, name
    worked = {}
    for name, entries, price, money, minutes in WORKED:
        backend = FakeBackend()
        backend.price_of = dict(price)
        plan = Plan.objects.create(basket_hash=guard.basket_hash(entries), made_by="joey", body={"jobs": 4})
        guard.work_out(plan, entries, backend)
        plan.refresh_from_db()
        assert plan.state == "ready", (name, plan.error)
        assert {key: plan.body["money"][key] for key in money} == money, (name, plan.body["money"])
        assert minutes is None or plan.body["time"] == minutes, (name, plan.body["time"])
        worked[name] = plan
    assert ("price", "world1", ("closeup@alpha", "closeup@beta")) in FakeBackend.calls  # the runner prices, not us
    plan = worked["measured"]
    for name, edits, given, writable, words in REFUSED:
        settings.SCORE_STORE_WRITABLE = writable
        arguments = {"user_is_owner": True, "current_hash": plan.basket_hash, "running": False, "confirmed": True,
                     "rebuy_reason": None, **given}
        assert guard.refusals(edited(plan, edits), **arguments) == words, name
    settings.SCORE_STORE_WRITABLE = True
    # the confirm page: its basket the plan's, launched only once ticked, followed to its result line
    monkeypatch.setattr(FakeBackend, "log_folder", str(tmp_path))
    for each in GROUPED[0][1]:
        BasketItem.objects.create(place=each.place, stage=each.stage, added_by="joey")
    client = Client()
    client.force_login(get_user_model().objects.get(username="joey"))
    assert client.post(f"/basket/confirm/{plan.pk}/", {}).status_code == 200  # not ticked
    assert not Launch.objects.exists()
    monkeypatch.setattr(guard, "launch_soon", lambda record, chosen: guard.launch(record, chosen, FakeBackend()))
    answer = client.post(f"/basket/confirm/{plan.pk}/", {"confirm": "yes"})
    launched = Launch.objects.get()
    assert answer.status_code == 302 and launched.state == "running", launched.result
    assert guard.polled(launched, FakeBackend()).state == "done"
    assert [call[1:] for call in launches()] == [(group, 4, None) for group in GROUPED[0][2]]
    # the local backend: the runner's command and environment for the plan's run of both places
    monkeypatch.setenv("SCORE_DASHBOARD_SECRET_KEY", "secret")
    monkeypatch.setenv("SCORE_SYNC_TOKEN", "token")
    for tag in localrun.RUN_TAGS:  # a grant or cap in the sync service's environment never reaches the owner's batch
        monkeypatch.setenv(tag, "inherited")
    seen, answers = [], {}

    def run(command, **options):
        seen.append({"command": command, **options})
        return answers["now"](command)
    both = guard.run_groups_of(plan.body)[1]
    handles = {}
    for name, answered, (pid, log, refusal), state in LAUNCHED:
        answers["now"] = answered
        handle = handles[name] = localrun.LocalBackend(run=run).launch(both, 4, "lamp changed")
        assert seen[-1]["command"][1:] == ["-m", "score", "run", "world1", "--place", "alpha", "--place", "beta",
                                           "--stage", "closeup", "--jobs", "4", "--detach", "--rebuy-reason",
                                           "lamp changed"], name
        assert "SCORE_DASHBOARD_SECRET_KEY" not in seen[-1]["env"] and "SCORE_SYNC_TOKEN" not in seen[-1]["env"]
        assert not set(localrun.RUN_TAGS) & set(seen[-1]["env"]) and seen[-1]["cwd"] == settings.SCORE_REPO, name
        assert (handle.pid, handle.log) == (pid, log) and (handle.refused is None) == (refusal is None), (name, handle)
        assert refusal is None or refusal in handle.refused, (name, handle)
        assert state is None or localrun.LocalBackend().poll(handle).state == state, name
    # a Buy's own caps reach its run as SCORE_MAX_MACHINES (the door's buy --max-machines, 2026-11-06). Break: in
    # localrun.run_env, drop the LAUNCH_CAPS lines
    monkeypatch.setenv(localrun.LAUNCH_CAPS, "cpu-64c-128gb=10")
    assert localrun.run_env()["SCORE_MAX_MACHINES"] == "cpu-64c-128gb=10"
    assert localrun.LAUNCH_CAPS not in localrun.run_env()
    # on the cluster's home a run's CPU makes go to the cluster (the box's queue, pod makes, the runner workers'
    # class) unless its own environment says otherwise; elsewhere none of it. Break: in localrun.run_env, drop the
    # CLUSTER_DEFAULTS lines
    from score.conductor import cluster
    monkeypatch.setattr(cluster, "RECORD", tmp_path / "no-cluster.json")
    assert not set(localrun.CLUSTER_DEFAULTS) & set(localrun.run_env())
    monkeypatch.setattr(cluster, "RECORD", tmp_path / "cluster.json")
    cluster.RECORD.write_text("{}")
    monkeypatch.setenv("SCORE_K8S_POD", "0")
    on_cluster = localrun.run_env()
    assert (on_cluster["SCORE_K8S_QUEUE"], on_cluster["SCORE_K8S_POD"], on_cluster["SCORE_POD_CLASSES"]) == \
        ("1", "0", "gpu-24gb")
    # its prices through `score price`, its bill from the ledger by node since the batch began
    answers["now"] = runner_answer(0, "reading the ledger\n" + json.dumps(
        {"world": "world1", "nodes": {"closeup@alpha": {"likely_euros": 1.0, "high_euros": 2.0}}}))
    found = localrun.LocalBackend(run=run).price("world1", ["closeup@alpha"])
    assert found == {"closeup@alpha": {"likely_euros": 1.0, "high_euros": 2.0}}
    assert seen[-1]["command"][1:] == ["-m", "score", "price", "world1", "--node", "closeup@alpha", "--json"]
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("\n".join(json.dumps(row) for row in (
        {"ticket": "closeup@alpha k1", "euros": 3.0, "wall_minutes": 9, "started": "2026-10-18T12:00:00Z"},
        {"ticket": "closeup@alpha k0", "euros": 7.0, "wall_minutes": 9, "started": "2026-10-17T12:00:00Z"},
        {"ticket": "closeup@beta k2", "euros": 5.0, "wall_minutes": 9, "started": "2026-10-18T12:00:00Z"})) + "\n")
    settings.SCORE_LEDGER_FILES = [ledger]
    (line,) = localrun.LocalBackend(run=run).ledgered(["closeup@alpha"], "2026-10-18T00:00:00Z")
    assert (line.node, line.euros, line.minutes) == ("closeup@alpha", 3.0, 9)
    # each result line read as its state; a log with none is running while its process lives, else failed
    for name, text, alive, state in POLLED:
        log = tmp_path / f"{name}.log"
        log.write_text(text)
        handle = LaunchHandle(command=[], pid=os.getpid() if alive else None, log=str(log))
        assert real.poll(handle).state == state, name
    deadline = time.time() + 60
    while (ended := real.poll(started)).state == "running" and time.time() < deadline:
        time.sleep(1)
    assert ended.state == "done" and ended.result.startswith("detached: ok exit=0"), ended
