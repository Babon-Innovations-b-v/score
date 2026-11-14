"""Paid work starts only inside a clearance the runner gave, priced on measured numbers, and only while its money
has room: the environment's stop line (or a benchmark grant's balance, or the owner's reading allowance) with
everything already spent since the line and everything in flight counted, under one lock; a started job is never
stopped halfway except as a runaway. No cloud: the job store is a folder, the ledger and the bill are set by each
test, the stop lines and grants live in a sandbox store.

Each break (applied once, seen red, reverted), in score/adapters/compute/__init__.py unless named:
- prerequisite failed: clearance's `except graph.Blocked` catches KeyError instead (Blocked leaks, no Refused).
- submitted without a typed yes: submit writes `"node_key": None`.
- needs its estimate: run_forecast's `if euros is None:` becomes `if False:`.
- measured high: run_forecast's measured euros take `run["euros"]` (the median) for `run["high_euros"]`.
- rent point outside a run: require_cleared's `if found[-1] is None:` becomes `if False:`.
- override's balance: override_refusal leaves out GRANT_BUFFER; or override_spent counts no open machine; or
  tools/cloud/ledger.py batch_cap returns BATCH_EUROS under an override, or holds an override's room to BATCH_EUROS.
- judge timeout: judge_timeout ignores SCORE_JUDGE_TIMEOUT.
- priced on measured runs: run_price's likely euros take `run["high_euros"]`.
- per unit counted: per_unit drops `or stage in entry["also"]`.
- per unit × forecast: run_price's `if forecast is not None:` becomes `if False:`.
- timed by the card rule: unit_minutes caps cards at 1 for a machine stage.
- settle not timed below: unit_minutes' high job seconds read the likely ones.
- pixal finish: then_minutes' `if "unit_seconds" not in then:` becomes `if True:`.
- retake priced for its takes: planned_forecast's `if takes:` becomes `if False:` (every take its accepted output
  made drawn instead).
- retake's Buy price: score/__main__.py selected_price passes None for the retake's units.
- row says where: score/graph/__init__.py keeps no earlier row's line (`kept = False`).
- count rules: counted_units' rule "one" counts 2.
- count of zero: counted drops the COUNTED_ZERO case.
- google month refused for an agent: owners_google_month's agent check becomes `if False:`.
- cockpit google line: score/__main__.py google_line skips the read-back bill (`if False:`).
- refused before it starts: guard.refusal leaves out `spent`.
- no month ceiling: stop_refusal counts the month's whole ledger (`books_now()["ledger"]`) instead of the spend since
  the line.
- lines clearing at once: clearance writes no reservation (keep_reservations skipped).
- in flight less ledgered: guard.in_flight counts the whole clearance, not less what it ledgered.
- runs on, stops as a runaway: guard.runaway at once its forecast minutes, not RUNAWAY times.
- runaway ends children: guard.stop_children signals nothing.
- long but inside its deadline: Watch.check drops `and not self.within_deadline()` (light-passes@campgrounds stopped
  at 7 min of its Jobs' 150); past its deadline: Watch.within_deadline returns True whatever the time.
- owner's yes keeps the start: guard.set_line writes the new baseline.
- stop command: guard.current reads the oldest line (`keys[0]`), not the newest.
- a line recorded on this PC: tools/cloud/provider.py billing returns `cloud` whatever its NAME (the line's start
  takes this PC's EUR 0 bill and the cloud's guard reads the cloud's whole bill as spend).
- spend across months: guard.spent_since takes the baseline as every month's start.
- credits never negative spend: in guard.spent_parts, `max(0.0, books["google"] - start["google"])` ->
  `books["google"] - start["google"]`.
- framework store with no line: stop_refusal returns None for any store.
- trial store: covering_store returns the trial's own store.
- clearance whose run ended: require_cleared's ended-run check becomes `if False:`.
- reservation open: still_open trusts a holder mark without guard.alive.
- override in flight: stop_refusal leaves the open overrides out of in flight.
- unreadable pre-flights: Watch.forecast_minutes lets ValueError through.
- waiting for a pool card: Watch.check adds no waited time.
- free work before the paid: Watch.check counts the time `paying()` said no paid work went (`if self.waits():` alone);
  or guard.runs_cloud_runner counts any process below the make (`return bool(arguments)`: a CoACD split too).
- grant at most EUR 20: grant_benchmark drops `figure > GRANT_EUROS`.
- grant's google month: grant_benchmark never writes the Google month.
- grant holds its balance: settle_grant draws the hold's reserve instead of the real spend.
- pool on a grant: pool_clearance asks no grant_refusal under a grant (`None if grant_id`).
- pool beyond the rows: pool_reserve returns the whole holding; pool beside the likely: pool_clearance's
  `stop_refusal(runner, POOL, beside, held)` (the rows' high alone) becomes `True`, or its `*likely` `beside, covered`.
- pool held longer: extend_pool replaces the reservation's euros instead of adding.
- heartbeat: score/__main__.py extend_pool extends whenever a plan exists.
- pool longer under a grant: extend_pool takes no further hold on the grant.
- gemini callers: GOOGLE_CALLERS loses `body-face-`.
- balance left: grant_refusal leaves out GRANT_BUFFER.
- reading allowance: reading_clearance drops the per-place euros limit.
- unquoted or too dear grant: grant_refusal drops `<= GRANT_EUROS`.
- listing walks only its prefix: compute.narrowed_keys's `folder = way[-1] if way else folders.root` becomes
  `folder = folders.root.parent`.
- restored grant: restore_grant skips settle_grant.
- the env1 cap: require_cloud's `why = cap_refusal(None, 0.0, env1=env1, own=(node, key))` becomes `why = None`;
  or guard.cap_refusal's stale check compares only the reading's own time; or cap_stop's env1 ignores GRANT.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python score/adapters/compute/test_paid_work_starts_only_inside_its_clearance.py
"""
import dataclasses
import datetime
import json
import math
import multiprocessing
import os
import pathlib
import runpy
import statistics
import subprocess
import sys
import tempfile
import time
import types

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score import checks, contracts, graph, review  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.adapters.compute import guard  # noqa: E402
from score.store import AGENT_MARKERS, Store  # noqa: E402

# the root conftest's sandbox test (its system temp folder, not this run's own temp folder inside it: own_temp)
SANDBOX = runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))
BOOKS = compute.ledger()
BOOKS_FOLDER = tempfile.mkdtemp()
MONTH = BOOKS.this_month()
START = {"month": MONTH, "bill": 100.0, "ledger": 90.0, "google": 0.0}
import capacity  # noqa: E402  (on the path compute.ledger() set)
import google_spend  # noqa: E402  (on the path compute.ledger() set)
import provider  # noqa: E402  (on the path compute.ledger() set)

GOOGLE_LEDGER = pathlib.Path(tempfile.mkdtemp()) / "google-ledger.jsonl"  # each test's Google month: empty
BILL = {"euros": 0.0}
CLOUD_BILL = compute.cloud_bill  # the real one, before each test's fake


def no_cloud_and_books_open(monkeypatch):
    """No cloud: the provider's bill is set by each test; this month's books known, so paid paths open."""
    monkeypatch.setattr(BOOKS, "BOOKS", BOOKS.BOOKS)  # recorded: open_books_for_tests moves it
    BOOKS.open_books_for_tests(BOOKS_FOLDER)
    monkeypatch.setattr(google_spend, "LEDGER", GOOGLE_LEDGER)
    monkeypatch.setattr(compute, "cloud_bill", lambda: BILL["euros"])


@pytest.fixture(autouse=True)
def no_cloud_and_books_open_for_each_test(monkeypatch):
    """Patched per test under pytest, so the next test file gets the real ones back."""
    no_cloud_and_books_open(monkeypatch)


def make_brief(inputs, out, seed, params):
    (out / "brief.txt").write_text(inputs["brief"].read_text())


def judge_brief(output, inputs, evidence):
    text = (output / "brief.txt").read_text()
    return checks.Verdict("said", checks.PASS if text.strip() else checks.FAIL, "a brief was written")


TEXT = contracts.Contract("toy-text", 1, lambda folder: [])


def make_nothing(inputs, out, seed, params):
    raise AssertionError("a paid stage's make is not run by these tests")


BRIEF = graph.Stage("brief", "place", make_brief, TEXT, (checks.Check("said", judge_brief),),
                    files={"brief": "{data}/{place}.txt"})
RENDER = graph.Stage("render", "place", make_nothing, TEXT, after={"brief": ("toy-text", 1)}, paid=True)


def month_spent(euros):
    """Set the ledger's month to have cost `euros` so far."""
    BOOKS.entries = lambda: [{"started": BOOKS.this_month(), "euros": euros}]


def a_runner(text):
    """A runner whose brief stage ran once (a passing brief is accepted by the runner then)."""
    data, store = pathlib.Path(tempfile.mkdtemp()), Store.in_folder(tempfile.mkdtemp())
    (data / "hangar.txt").write_text(text)
    runner = graph.Runner([BRIEF, RENDER], graph.Environment("toy", 1, {"data": data}), store)
    runner.run_node(BRIEF, "hangar")
    return runner


def refused(call):
    try:
        call()
    except compute.Refused as refusal:
        return str(refusal)
    raise AssertionError("taken")


def test_a_rent_point_refuses_outside_a_cleared_run_or_the_owners_override(monkeypatch):
    """Fault (design of 2026-10-11, section 6): blender_cloud.py, detached.py, the runners and demo.py rented with no
    gate, so a run that skipped the runner could spend. Every rent point now asks require_cleared first. Fault
    (labval-motor-20261106, 2026-11-06): an override's euros were never held against what was booked under it, so
    a run with EUR 2.47 left could spend EUR 5; now a run under one clears only while what its lines booked (its
    open machines to their deadlines) and the run's high plus 10% fit, and a batch under it may spend only what is
    left less 10% (ledger.batch_cap, the machines' deadline and the cluster's stop), past the EUR 60 batch cap too
    (#98: MOTOR's 720-trial validation is one run)."""
    month_spent(0)
    runner = a_runner("a hall")
    os.environ.pop(compute.TICKET, None)
    assert "nothing rents outside a cleared run" in refused(lambda: compute.require_cleared("a batch", runner.store))
    ticket = runner.ticket("render@hangar")
    with compute.spending(ticket):  # a key the runner hands out, but never cleared
        assert os.environ[compute.TICKET] == f"render@hangar {ticket['key']}"
        assert "did not clear" in refused(lambda: compute.require_cleared("a batch", runner.store))
    with compute.spending(compute.clearance(runner, "render@hangar", 1.0)):
        assert compute.require_cleared("a batch", runner.store)["euros"] == 1.0
        # a rent point told no store (a batch's own process) finds the clearance in the runner's store, a trial's too
        assert compute.require_cleared("a batch")["euros"] == 1.0
    assert compute.TICKET not in os.environ and compute.STORE not in os.environ
    runner.store.write_spend_yes(compute.OVERRIDE, "repaint-six", {"euros": 3.0, "at": graph.now()})
    with compute.spending({"node": compute.OVERRIDE, "key": "repaint-six"}):
        assert compute.require_cleared("a batch", runner.store)["euros"] == 3.0
    began = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    BOOKS.entries = lambda: [  # EUR 2 booked, a machine open 30 min at EUR 0.01 a minute, another ticket's EUR 9
        {"started": began, "ticket": "override repaint-six", "batch": "sim-1", "euros": 2.0},
        {"started": began, "ticket": "override repaint-six", "kind": BOOKS.RENT_STARTED, "batch": "rent-m1",
         "run": "sim-2", "name": "m1", "price": 0.01, "deadline": BOOKS.moment(began) + 1800, "euros": 0.0},
        {"started": began, "ticket": "run-7 surfaces-paint", "batch": "paint", "euros": 9.0}]
    monkeypatch.setenv(compute.STORE, str(runner.store.cache.parent))
    with compute.spending({"node": compute.OVERRIDE, "key": "repaint-six"}):
        assert compute.override_room() == {"name": "repaint-six", "euros": 3.0, "spent": 2.3, "left": 0.7}
        assert compute.require_cleared("a batch", runner.store, high=0.6)["euros"] == 3.0  # 0.66 fits 0.70
        assert "EUR 0.70 left" in refused(lambda: compute.require_cleared("a batch", runner.store, high=0.65))
        cap, words = BOOKS.batch_cap()
        assert round(cap, 4) == round(0.7 / 1.1, 4) and "repaint-six" in words
        assert round(BOOKS.minutes_allowed(0.01), 1) == 63.6  # its machines' watchdogs delete them at EUR 0.64
        assert "repaint-six" in BOOKS.refusal(65, 0.01)
    BOOKS.entries = lambda: [{"started": began, "ticket": "override repaint-six", "batch": "sim-1", "euros": 3.0}]
    with compute.spending({"node": compute.OVERRIDE, "key": "repaint-six"}):
        assert "EUR 0.00 left" in refused(lambda: compute.require_cleared("a batch", runner.store))
        assert BOOKS.minutes_allowed(0.01) == 0.0
    runner.store.write_spend_yes(compute.OVERRIDE, "whole-validation", {"euros": 330.0, "at": graph.now()})
    with compute.spending({"node": compute.OVERRIDE, "key": "whole-validation"}):  # one run past the EUR 60 cap
        assert round(BOOKS.batch_cap()[0], 4) == 300.0
    assert BOOKS.batch_cap()[0] == BOOKS.BATCH_EUROS  # outside an override the batch cap stands
    # the env1 cap (the plan of 2026-11-09, B2): the whole bill's counter past the line refuses every rent point, an
    # override or a grant with euros left is refused while the cap is open, a start whose high (plus 10% and the
    # standing to the finish) would pass the line is refused, an unread or stale bill refuses (fails closed), and the
    # stop lines keep their batch project's baseline beside the whole bill
    book, now, written = guard.FolderBook(os.environ[guard.CAP_BOOK]), time.time(), []
    monkeypatch.setattr(guard, "running_under_agent", lambda: False)

    def iso(seconds):
        return datetime.datetime.fromtimestamp(seconds, datetime.timezone.utc).isoformat()

    def reading(counter, **more):
        written.append(1)  # each newer than the last, so it is the newest
        guard.cap_write(book, "readings", {"at": iso(now - 60 + len(written) / 100), "unread": None,
                                           "counter": counter, "whole": 2500.0, **more})
    guard.set_cap(book, {"euros": 300.0, "line": 255.0, "start": iso(now - 3600), "by": "joey",
                         "at": iso(now - 3600), "baseline": {"whole": 2000.0, "lines": {}},
                         "finish": iso(now + 86400), "standing_per_day": 10.0, "month_cap": 2970.0})
    try:
        assert "has no reading" in refused(lambda: compute.clearance(runner, "render@hangar", 1.0))
        reading(100.0)
        with compute.spending(compute.clearance(runner, "render@hangar", 1.0)):
            assert compute.require_cloud("a batch")["euros"] == 1.0
            reading(256.0)  # a babon-platform SCORE line grew past the cap
            assert "255.00 stop line" in refused(lambda: compute.require_cloud("a batch"))
            assert "255.00 stop line" in compute.cap_stop()  # the cluster's poll stops too
            reading(100.0)
            with monkeypatch.context() as later:  # no pass for 20 minutes
                later.setattr(time, "time", lambda: now + 20 * 60)
                assert "fails closed" in refused(lambda: compute.require_cloud("a batch"))
            reading(100.0, unread="Unread: no line", good_at=iso(now - 20 * 60))
            assert "fails closed" in refused(lambda: compute.require_cloud("a batch"))
            reading(100.0, whole=2970.0)
            assert "November cap" in refused(lambda: compute.require_cloud("a batch"))
        reading(200.0)
        assert "this start's high EUR 50.00" in refused(lambda: compute.clearance(runner, "render@hangar", 50.0))
        with compute.spending({"node": compute.OVERRIDE, "key": "whole-validation"}):  # euros left, cap open: C10
            assert "no other paid run" in refused(lambda: compute.require_cloud("a batch"))
            assert "no other paid run" in compute.cap_stop()
        monkeypatch.setenv(compute.GRANT, "grant-1")  # a benchmark grant's run with its balance left: C10 too
        assert "no other paid run" in compute.cap_stop()
        monkeypatch.delenv(compute.GRANT)
        assert guard.spent_since(START, {MONTH: {"bill": 150.0, "ledger": 90.0, "google": 0.0, "bill_all": 9e3}}) \
            == 50.0  # a stop line's spend: its batch project's bill, never the whole bill beside it
        monkeypatch.setattr(provider, "billing", lambda: types.SimpleNamespace(NAME="plain"))
        assert compute.cloud_bill_all() == {"bill_all": None, "bill_all_unread": "the plain backend reads no whole bill"}
    finally:
        guard.set_cap(book, {**guard.current_cap(book), "open": False, "at": iso(time.time() + 1)})
    assert compute.cap_refusal(runner.store, 1e6) is None  # a closed cap refuses nothing


def run_line(number, euros, minutes):
    """One paid run of the render stage on one card with two jobs."""
    machine = {"cards": 1, "minutes": minutes, "euros": euros, "unit_seconds": [60, 60], "setup_minutes": 1.0}
    return {"ticket": f"render@place{number} {number}", "kind": "blender", "batch": f"blender-{number}",
            "machines": [machine], "euros": euros, "wall_minutes": minutes}


class Outputs:
    """A store's read side for the per-unit price: accepted outputs as {node: {file: content}}."""

    def __init__(self, made):
        self.made = made

    def accepted(self, node):
        return node if node in self.made else None

    def listing(self, output):
        return {name: "sha" for name in self.made[output]}

    def read_file(self, output, name):
        return self.made[output].get(name)


def make_takes(inputs, out, seed, params):
    (out / "takes.json").write_text(json.dumps({"a-s1": 1, "b-s1": 2, "c-s1": (inputs["brief"] / "brief.txt").read_text()}))


MADE_TAKES = graph.Stage("render", "place", make_takes, TEXT, (checks.Check("said", lambda *_: checks.Verdict(
    "said", checks.PASS, "made")),), after={"brief": ("toy-text", 1)}, retakes=True)  # a retake's stage, unpaid
PAID_TAKES = dataclasses.replace(MADE_TAKES, paid=True)
SPENT_PIXAL = {"kind": "blender", "ticket": "pixal@yard k", "jobs": ["a", "b"], "machines": [
    {"started": True, "start_wait_minutes": 0.5, "setup_minutes": 1.0, "unit_seconds": [40.0, 50.0]}]}


def ledger(*lines):
    """The fake ledger: these lines (a machine's batch under a ticket, or a month's sum), this month."""
    BOOKS.entries = lambda: [{"started": f"{MONTH}-18T10:00:00Z", **line} for line in lines]


def as_owner(call):
    """Run `call` as the owner's own terminal would: without the agent's marks."""
    saved = {name: os.environ.pop(name) for name in AGENT_MARKERS if name in os.environ}
    try:
        return call()
    finally:
        os.environ.update(saved)


def as_agent(call):
    """Run `call` as an agent's process: with Claude Code's mark, whoever runs the test."""
    saved = os.environ.get(AGENT_MARKERS[0])
    os.environ[AGENT_MARKERS[0]] = "1"
    try:
        return call()
    finally:
        if saved is None:
            os.environ.pop(AGENT_MARKERS[0])
        else:
            os.environ[AGENT_MARKERS[0]] = saved


def stop_at(runner, euros, baseline=START, at="2026-10-18T09:00:00+00:00"):
    """The owner's stop line for the runner's environment."""
    return as_owner(lambda: guard.set_line(runner.store, runner.world.name, euros, "the films", "owner", at, baseline))


def outbox(runner):
    path = runner.store.cache.parent / guard.OUTBOX
    return path.read_text().splitlines() if path.exists() else []


def clear_in_a_process(runner, ready, sending):
    ready.wait()
    try:
        compute.clearance(runner, "render@hangar", 1.0)
        sending.send("cleared")
    except compute.Refused:
        sending.send("refused")


def test_the_owners_stop_command_writes_the_line_the_next_clearance_reads(monkeypatch):
    """C22: his money yes and the guard line are one step: `score.review stop` writes the line, and the very next
    clearance is held to it. Without a terminal, or in an agent's process, it writes nothing. A first line recorded on
    this PC (SCORE_CLOUD=local, his yes in chat through this_pc.py) starts from the cloud's bill, so the cloud's guard
    finds exactly its euros of room."""
    from score.review import __main__ as review_command
    from score.review import web
    assert SANDBOX["sandbox_refusal"](os.environ) is None, "run in a sandbox home"
    world = "toy-stop"
    try:
        review_command.main(["stop", world, "5", "--reason", "films"])  # no terminal here
        raise AssertionError("written without a terminal")
    except SystemExit as refusal:
        assert "own terminal" in str(refusal)
    store = Store.default()
    assert guard.current(store, world) is None
    review_command.owner_at_terminal = lambda: None  # his own terminal
    try:
        as_agent(lambda: review_command.main(["stop", world, "5", "--reason", "films"]))
        raise AssertionError("an agent's process wrote a stop line")
    except SystemExit as refusal:
        assert "only the owner" in str(refusal)
    ledger({"euros": 40.0})
    BILL["euros"] = 50.0
    as_owner(lambda: review_command.main(["stop", world, "5", "--reason", "films"]))
    line = guard.current(store, world)
    assert line["euros"] == 5.0 and line["baseline"]["bill"] == 50.0 and line["reason"] == "films"
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "hangar.txt").write_text("a hall")
    runner = graph.Runner([BRIEF, RENDER], graph.Environment(world, 1, {"data": data}), store)
    runner.run_node(BRIEF, "hangar")
    assert "pass the EUR 5.00 stop" in refused(lambda: compute.clearance(runner, "render@hangar", 6.0))
    as_owner(lambda: review_command.main(["stop", world, "8", "--reason", "films, raised"]))
    assert compute.clearance(runner, "render@hangar", 6.0)  # the yes is the line: no one copies it anywhere
    BILL["euros"] = 0.0
    scaleway = types.SimpleNamespace(NAME="scaleway", account=lambda: "ours", month_spend=lambda account: 388.73)
    this_pc = types.SimpleNamespace(NAME="local", account=lambda: "this-pc", month_spend=lambda account: 0.0)
    monkeypatch.setattr(compute, "cloud_bill", CLOUD_BILL)
    monkeypatch.setattr(provider, "load", lambda name=None: scaleway)
    monkeypatch.setattr(provider, "cloud", this_pc)  # the yes recorded on this PC
    as_owner(lambda: web.stop(store, "toy-stop-pc", 10.0, "his yes in chat", "joey"))
    monkeypatch.setattr(provider, "cloud", scaleway)  # checked by the cloud's guard
    pc_runner = graph.Runner([BRIEF, RENDER], graph.Environment("toy-stop-pc", 1, {"data": data}), store)
    assert compute.stop_room(pc_runner, store, 10.0, {})[1:] == (0.0, None)
    assert "pass the EUR 10.00 stop" in compute.stop_room(pc_runner, store, 10.01, {})[2]


QUESTION = "Approve one benchmark batch, P1, of at most EUR 10?"


def as_benchmark(grant_id, run, call):
    """Run `call` as a node of the `score run` named `run`, tagged with the benchmark grant `grant_id`."""
    os.environ[compute.GRANT] = grant_id
    if run:
        os.environ[compute.RUN_ID] = run
    try:
        return call()
    finally:
        os.environ.pop(compute.GRANT)
        os.environ.pop(compute.RUN_ID, None)


def billed(ticket, euros):
    """Add a cloud ledger line of `euros` under a cleared run's ticket, started as it was cleared, to the fake ledger;
    a second later, so the next clearance of the same node starts after it (the ledger counts in seconds)."""
    lines = BOOKS.entries()
    BOOKS.entries = lambda: [*lines, {"started": ticket["clearance"]["at"][:19] + "Z", "euros": euros,
                                      "ticket": f"{ticket['node']} {ticket['key']}"}]
    time.sleep(1.05)


def measured_lines(stage, euros, minutes=20.0):
    """The ledger lines of one batch each of four paid runs of `stage`, at these euros, this month."""
    return [{"ticket": f"{stage}@place{number} key{number}", "started": BOOKS.this_month(), "kind": "blender",
             "batch": f"blender-{number}", "euros": cost, "wall_minutes": minutes, "machines": []}
            for number, cost in enumerate(euros)]


SHARE = compute.BILL_SHARE  # a card stage's ledger euros on the provider's bill (no Google calls)
CAP = capacity.run_cap()  # the run's cap: the largest class quota (#20)
ABSENT = "not in the answer"
RESERVED = "what the clearance reserves"  # a price's field equal to run_forecast's euros for the same ask
WHERE = "score/stages/x.py:12"  # the file and line a row names its estimate on


class Exactly(dict):
    """An expected answer that is the whole answer, not some of its fields."""


def per_unit_stage(stage, **more):
    """A PER_UNIT stage measured at EUR 0.2 likely and 0.5 high a model over 40 runs, counted by takes.json's keys."""
    return {"stage": stage, "unit": "model", "count": {"json_keys": "takes.json"}, "also": [], "likely_euros": 0.2,
            "high_euros": 0.5, "runs": 40, "sources": {}, **more}


MODELS = {"rule": "models", "source": "the place's takes"}
TIMED = {"unit_seconds": {"likely": 600.0, "high": 1200.0}, "setup_minutes": {"likely": 10.0, "high": 14.0},
         "slots": 1, "holds": "machines"}
TAKE_MAP = {"front": {"attempts": [{}, {}]}, "views": {"t15-090": {"attempts": [{}]}, "t15-180": {"attempts": []}}}
NAMES = {"finishes": [{"by": "the list"}]}
OWN = "the row's grant"  # a step tagged with the grant its row made
SPENT_10K = {"month": MONTH, "bill": 10_000.0, "ledger": 10_000.0, "google": 0.0}
FULL, HALF, ONE_CARD = {"gpu-24gb": 10, "cpu-64c": 3}, {"gpu-24gb": 3, "cpu-64c": 2}, {"gpu-24gb": 1}
POOLS = [(FULL, 72.0), (HALF, 36.0), (ONE_CARD, 3.6)]  # a warm pool's choices, largest first, each its 4 h holding
ROWS = [{"likely_euros": 2.0, "high_euros": 5.0, "cards": 1},  # one measured row, one guessed
        {"likely_euros": None, "high_euros": None, "guess_euros": 90.0}]


class Says(str):
    """An expected field that holds these words, not only them."""


class Holds(str):
    """An expected field that holds this, as words or as a list's item (OWN: the grant at hand)."""


ASLEEP = [sys.executable, "-c", "import time; time.sleep(60)"]
WALL = 1000.0  # a watch's wall clock (epoch seconds) at its start; it runs on with the watch's own clock
LISTED = ("clearances/n/k/a.json", "clearances/n/k/b.json", "clearances/n/kk/c.json", "accepts/x.json", "real/d.json",
          "blobs/e.partial")


def a_listing():
    """A folder store holding LISTED, with `link` a link to its `real` folder."""
    root = pathlib.Path(tempfile.mkdtemp())
    for key in LISTED:
        (root / key).parent.mkdir(parents=True, exist_ok=True)
        (root / key).write_text("{}")
    (root / "link").symlink_to(root / "real")
    return compute.runtime_store.FolderStore(root)


def books_text():
    """The books file as it stands, or None while there is none."""
    return BOOKS.BOOKS.read_text() if BOOKS.BOOKS.exists() else None


def a_stage_row(name, **more):
    """A row of the render stage's shape, built through a helper that hands its euros on."""
    return graph.Stage(name, "place", make_nothing, TEXT, **more)


GEMINI = "gemini-3.1-pro-preview"
RUN_CALLS = [("2026-10-22T10:00:30+02:00", "finished", "body-face", 0.03),  # a run's calls: 08:00 to 08:01 UTC
             ("2026-10-22T10:00:40+02:00", "finished", "pro", 0.14),
             ("2026-10-22T10:00:50+02:00", "started", "body-face", None),  # never finished: at its estimate
             ("2026-10-22T10:05:00+02:00", "finished", "body-face", 9.0)]  # after the run's time


# One row a world: its brief, the owner's stop line (euros, baseline) or none, the ledger's lines, the bill, an
# override or a benchmark grant standing; then its steps against the clearance, each answered by the real entry point:
#   ("submit"|"clear", euros, grant tag, run, expected): a job through compute.submit, or a run through
#     compute.clearance; expected is the refusal's words (a string or a tuple of them), or the cleared record's fields
#     (a value, a (low, high) range it lies strictly inside, or Says: words it holds)
#   ("pool", choices, grant tag, run, expected, given): a warm pool of 4 h through compute.pool_clearance (`given` its
#     beside, covered and likely); ("reading", euros, grant tag, run, expected, given): a scene inventory reading
#     through compute.reading_clearance in an agent's process (`given` its places and node); expected the refusal's
#     words, or the answer's fields as above (nested: the clearance's own)
#   ("extend", euros, grant tag, run, expected): the newest pool held 4 h longer (compute.extend_pool); expected the
#     refusal's words, or its one reservation's fields after (the call answering its holding)
#   ("fits", choices, beside, covered, likely, room, expected): compute.pool_fits worked out dry, (sizes, by, words
#     of its refusal or None), the reservations untouched
#   ("rows", given, euros): the Buy's rows' high (score.__main__.rows_high) of ROWS
#   ("race", processes, cleared): that many processes ask a EUR 1 clearance at once; how many are cleared
#   ("bill", euros): the newest cleared run's ledger line (billed)
#   ("release",): the newest cleared run ends (compute.release)
#   ("used", run): the grant as the single-use rule left it, used up by `run` on the newest clearance
#   ("restore", answer, question, expected): compute.restore_grant of the row's grant; the refusal's words or fields
#   ("rent", store given, expected): a rent point (compute.require_cleared) asked under the newest cleared run, told
#     the runner's store or none; inside compute.spending while the run is open (its reservation ends with it), else
#     with only its ticket named; expected is the refusal's words or the found clearance's fields
#   ("stop", euros, baseline, who, expected): the owner (or an agent, refused) writes the world's stop line now;
#     expected the line's fields, the world's current line then
#   ("price"|"forecast", node, estimate, asked, expected): compute.run_price or compute.run_forecast on the row's
#     accepted outputs (its "outputs") and per-unit file (its "per_unit" stages), `asked` its units or guess_from;
#     expected the answer's fields (ABSENT: not there; RESERVED: the run_forecast euros of the same ask; a range), or
#     Exactly the whole answer
#   ("count", output, rule, units): compute.counted_units of the row's output by the count rule
#   ("unit_price", node, units, expected): compute.forecast_price, its fields or None; ("minutes", stage, units,
#     expected): compute.unit_minutes, the whole answer
#   ("watch", forecast minutes, given, ticks, words): a started run's guard.Watch (`given` its batches' pre-flights,
#     or "unreadable", and its jobs' deadlines in minutes); each tick (minute, {waiting, paying}, a runaway, stops so
#     far) one check at that minute of its own clock, its wall clock WALL on; the outbox then holds `words`
#   ("children",): a plain sleeper and a cloud runner started below this process; guard.stop_children ends both
#   ("open", hours ago, held, expected): compute.still_open of a reservation (holder "alive": this process's mark,
#     "reused": its pid on another start)
#   ("spent", start, months, since, parts): guard.spent_since and guard.spent_parts
#   ("grant", given, expected, books): compute.grant_benchmark into the row's store; the refusal's words, or the
#     grant's fields and then the books' (None: the books untouched)
#   ("forge", id, fields): a grant record written straight into the store, unquoted or too dear
#   ("listing", prefix, keys): a folder store's narrowed listing is the whole walk's, and these keys where given
#   ("timeout", setting, seconds): compute.judge_timeout with SCORE_JUDGE_TIMEOUT at that setting (None: unset);
#     the models adapter's keyed record holds no time limit
#   ("row", fields, replaced, line): a stage row built with these fields, then dataclasses.replace'd; the line the
#     replaced row names ("built", "replaced", or None: no estimate, nothing named)
#   ("heartbeat", run, seconds left, euros, refused): the run's heartbeat (score.__main__.extend_pool) on the newest
#     pool with its plan's end that far off; the holdings it extends by now, and the words its refusal left or None
#   ("drawn", node, euros): the Google euros compute.run_spend draws for a run of `node` from 08:00 to 08:01 UTC
#     on 2026-10-22, on the row's "google_calls" (time, state, caller, euros)
#   ("google_month", euros, words): an agent's process gives the owner's Google month: refused, the books untouched
#   ("google_line", books, expected): this month's books written so, the cockpit's Google line (score.__main__)
#   ("days",): the cockpit's ledger days of this month, from its first day, each its cloud and models
#   ("retake", takes, euros): a paid retake's stage on the row's "takes" makes: compute.retake_takes, then the
#     clearance's planned_forecast and the Buy's selected_price (its plan counting 3 takes) both at `euros`
#   ("reject takes", takes): the owner's reject of the accepted make names these takes
#   ("ledger timed", stage): the repository's unit_minutes against the paper ledger's runs of that stage
#   ("finish", stage, units): the repository's per-unit finish step (`then`) and the minutes it adds
#   ("then", then, units, minutes): compute.then_minutes; ("then times", lines, stage, count, likely): the per-unit
#     tool's finish times read from these ledger lines
# A trial row's store is a trial's own inside the home (compare.py's): its stop line and reservations are the
# framework store's, every cleared run's reservations kept there.
# and what stands after: the outbox's lines, the grant's draws (euros, balance) and balance.
ASKS = [
    pytest.param({"text": "   ", "ledger": [{"euros": 0.0}],
                  "steps": [("submit", 0.8, None, None, "brief@hangar answered fail")]}, id="prerequisite failed"),
    pytest.param({"text": "a hall", "reject": True, "ledger": [{"euros": 0.0}],
                  "steps": [("submit", 0.8, None, None, "brief@hangar has not run on its current inputs")]},
                 id="prerequisite rejected: its key moved on to an again key, made again first"),
    # the owner, 2026-10-11, 'why are you asking this?': the runner clears a run, never his typed spend yes
    pytest.param({"text": "a hall", "ledger": [{"euros": 0.0}], "steps": [("submit", 0.8, None, None, {"euros": 0.8})]},
                 id="cleared without a typed yes"),
    # the owner, 2026-10-20: no month's ceiling; a month far past the old EUR 3,000 clears a run
    pytest.param({"text": "a hall", "ledger": [{"euros": 10_000.0}],
                  "steps": [("submit", None, None, None, "needs its estimate"),
                            ("submit", 5.0, None, None, {"euros": 5.0, "estimate": 5.0})]},
                 id="needs its estimate, no month total"),
    # 2026-10-18: a film's hand-written EUR 0.7 against runs of EUR 1.3 to 16; cleared at the high, the 90th percentile
    pytest.param({"text": "a hall", "ledger": measured_lines("render", [1.0, 1.2, 1.4, 6.0]),
                  "steps": [("submit", 0.7, None, None, {"estimate": 0.7, "measured": 4, "minutes": 20.0,
                                                         "euros": (1.4, 6.0)}),
                            ("submit", None, None, None, {"estimate": None, "measured": 4, "euros": (1.4, 6.0)})]},
                 id="measured high, not the hand estimate"),
    # environment 1, 2026-10-12 to 18: the stop killed runs halfway and was raised 13 times; now refused before the
    # start, said once, and free work goes on. The ledger grew EUR 15 since the line, the lagging bill only 10.
    pytest.param({"text": "a hall", "stop": 20.0, "ledger": [{"euros": 90.0}, {"euros": 15.0}], "bill": 110.0,
                  "steps": [("submit", 6.0, None, None, ("EUR 15.00 spent", "pass the EUR 20.00 stop")),
                            ("submit", 6.0, None, None, "pass the EUR 20.00 stop"),
                            ("submit", 4.0, None, None, {"euros": 4.0})],
                  "outbox": (1, "Free work goes on")}, id="past the stop, refused before it starts"),
    pytest.param({"text": "a hall", "stop": 5.0, "baseline": SPENT_10K, "ledger": [{"euros": 10_000.0}],
                  "bill": 10_000.0, "steps": [("submit", 6.0, None, None, "pass the EUR 5.00 stop"),
                                              ("submit", 4.0, None, None, {"euros": 4.0})]},
                 id="a batch's own stop, whatever the month cost"),
    pytest.param({"text": "a hall", "stop": 10.0, "ledger": [{"euros": 90.0}],
                  "steps": [("clear", 6.0, None, None, {"euros": 6.0}),  # in flight: EUR 6 of the 10 left
                            ("clear", 5.0, None, None, "pass the EUR 10.00 stop"),
                            ("bill", 4.0),  # 4 of its 6 ledgered
                            ("clear", 3.9, None, None, {"euros": 3.9})]},  # 4 spent + 2 in flight + 3.9 fits
                 id="in flight, less what it ledgered"),
    pytest.param({"text": "a hall", "stop": 10.0, "ledger": [{"euros": 90.0}], "override": 7.0,
                  "steps": [("clear", 4.0, None, None, "pass the EUR 10.00 stop"),
                            ("clear", 2.0, None, None, {"euros": 2.0})]}, id="an override still going in flight"),
    pytest.param({"text": "a hall", "framework": "toy-framework", "ledger": [{"euros": 0.0}],
                  "steps": [("clear", 1.0, None, None, "has no stop line")]}, id="framework store with no line"),
    # the owner, 2026-10-22: a grant holds its euros until spent; each run holds its high plus 10% while it goes and
    # draws its real spend when it ends, failed too
    pytest.param({"text": "a hall", "stop": 1.0, "ledger": [{"euros": 90.0}], "bill": 100.0, "grant": 10.0,
                  "steps": [("clear", 6.0, None, None, "pass the EUR 1.00 stop"),  # not tagged: the stop line
                            ("clear", 6.0, OWN, "run-a", {"grant": OWN}),  # holds 6.60 of 10
                            ("clear", 4.0, OWN, "run-a", "EUR 3.40 left"),
                            ("bill", 0.25), ("release",),  # fails after spending 0.25: draws that, never its hold
                            ("clear", 8.0, OWN, "run-b", {"grant": OWN}),  # 8.80 fits in 9.75
                            ("clear", 1.0, OWN, "run-b", "EUR 0.95 left"),
                            ("bill", 1.5), ("release",),
                            ("clear", 0.5, OWN, None, "one score run"),
                            ("clear", 0.5, "20991231T000000", "run-c", "no benchmark grant")],
                  "draws": [(0.25, 9.75), (1.5, 8.25)], "balance": 8.25}, id="a grant holds its balance across runs"),
    pytest.param({"text": "a hall", "ledger": [{"euros": 0.0}], "grant": 2.0,
                  "steps": [("clear", 1.0, OWN, "run-a", {"grant": OWN}),
                            ("bill", 1.2), ("release",),  # ran over its high: it draws what it spent
                            ("clear", 0.75, OWN, "run-b", "EUR 0.80 left"),
                            ("clear", 0.7, OWN, "run-b", {"grant": OWN})],  # 0.77 fits
                  "draws": [(1.2, 0.8)]}, id="a high past the grant's balance left"),
    # 2026-10-18 review: any earlier clearance passed a rent point, so a ticket reused after its run ended started paid
    # work that no stop check and no in-flight sum saw
    pytest.param({"text": "a hall", "ledger": [{"euros": 0.0}],
                  "steps": [("clear", 1.0, None, None, {"euros": 1.0}),
                            ("rent", True, {"euros": 1.0}),
                            ("rent", True, "has ended")]}, id="a rent point after its run ended"),
    # 2026-10-18 review: compare.py's trial store had no stop line of its own, so its paid rows (close-ups, pixal,
    # likeness) skipped the stop, and their reservations sat in the trial's store where no clearance counted them
    pytest.param({"text": "a hall", "trial": "toy-trial", "ledger": [{"euros": 90.0}],
                  "steps": [("clear", 1.0, None, None, "has no stop line"),
                            ("stop", 10.0, START, "owner", {"euros": 10.0}),
                            ("clear", 6.0, None, None, {"euros": 6.0}),
                            ("clear", 5.0, None, None, "pass the EUR 10.00 stop"),
                            ("rent", False, {"euros": 6.0}),  # the clearance read from the trial's store
                            ("clear", 5.0, None, None, {"euros": 5.0})]},  # released: in flight no more
                 id="a trial's own store held to the world's stop"),
    # the cockpit's price is the runner's: likely the median run, high what the clearance reserves, cards from the
    # run's sizing (two 1-minute jobs a run on a 1-minute set-up: a card each)
    pytest.param({"text": "a hall", "ledger": [run_line(number, euros, minutes)
                                               for number, (euros, minutes) in enumerate([(1.0, 10), (2.0, 20),
                                                                                          (3.0, 30)])],
                  "steps": [("price", "render@hangar", 9.0, {}, {"likely_euros": 2.0, "likely_minutes": 20, "runs": 3,
                                                                 "high_euros": RESERVED, "cards": 2}),
                            ("forecast", "render@hangar", 9.0, {}, {"euros": (2.0, math.inf)})]},
                 id="priced on its stage's measured runs"),
    # an unmeasured stage has no price, its estimate kept apart as the guess with no minutes; the clearance still
    # reserves the guess
    pytest.param({"text": "a hall", "ledger": [],
                  "steps": [("price", "render@hangar", 9.0, {}, Exactly({
                      "likely_euros": None, "high_euros": None, "guess_euros": 9.0, "likely_minutes": None,
                      "high_minutes": None, "cards": None, "runs": 0, "basis": "not measured yet",
                      "minutes_why": "not measured yet"})),
                            ("forecast", "render@hangar", 9.0, {}, {"euros": 9.0})]},
                 id="unmeasured, its estimate a guess"),
    # measured per unit: its units of the node's accepted output, likely and high both, cleared at its high; an
    # `also` stage priced the same; a node with no accepted output to count is not measured yet. The count rules
    # read the output as the stages write it: files by pattern, one file a take, a JSON's keys or field, every map
    # attempt of a take.
    pytest.param({"text": "a hall", "ledger": [], "per_unit": {"render": per_unit_stage("render", also=["crops-render"])},
                  "outputs": {"render@hangar": {"takes.json": {"a": 1, "b": 2, "c": 3}, "contract.json": {}},
                              "crops-render@hangar": {"takes.json": {"a": 1}},
                              "out": {"contract.json": {}, "a-s1.json": NAMES, "b-s1.json": NAMES,
                                      "a-s1/map.json": TAKE_MAP, "passes/p-0.views.json": {},
                                      "passes/p-1.views.json": {}, "passes/p-0/look.png": None,
                                      "closeups.json": {"pro_pictures": 4}}},
                  "steps": [("price", "render@hangar", 9.0, {}, {
                                "likely_euros": round(0.6 * SHARE, 4), "high_euros": round(1.5 * SHARE, 4),
                                "units": 3, "runs": 40, "basis": "per unit × counted"}),
                            ("forecast", "render@hangar", 9.0, {}, Exactly({
                                "euros": round(1.5 * SHARE, 4), "minutes": None, "high_minutes": None,
                                "measured": 40})),
                            ("price", "crops-render@hangar", 2.0, {}, {"likely_euros": round(0.2 * SHARE, 4)}),
                            ("price", "render@lab", 9.0, {}, {"likely_euros": None, "guess_euros": 9.0, "runs": 0}),
                            ("price", "bake@hangar", 3.0, {}, {"basis": "not measured yet"}),
                            ("count", "out", {"one": True}, 1),
                            ("count", "out", {"files": "passes/*.views.json"}, 2),
                            ("count", "out", {"take_files": ".json"}, 3),
                            ("count", "out", {"json_field": ["closeups.json", "pro_pictures"]}, 4),
                            ("count", "out", {"map_attempts": "map.json"}, 3),
                            ("count", "out", {"json_keys": "missing.json"}, None)]},
                 id="per unit times its counted units"),
    # units forecast before a make (gaps' price) give per unit times them, before the units an older accepted output
    # counted (the gap's make makes what it adds); a stage with no forecast rule, an `also` stage, or no units is a
    # guess naming the file and line its row writes its estimate on; the clearance reserves the forecast's high
    pytest.param({"text": "a hall", "ledger": [],
                  "per_unit": {"render": per_unit_stage("render", also=["crops-render"], forecast=MODELS),
                               "bake": {"stage": "bake", "unit": "job", "count": {"one": True}, "also": [],
                                        "likely_euros": 1.0, "high_euros": 2.0, "runs": 3, "sources": {},
                                        "forecast": None, "forecast_why": "no batch"}},
                  "outputs": {"render@hangar": {"takes.json": {"a": 1}}},
                  "steps": [("price", "render@lab", 9.0, {"units": 4, "guess_from": WHERE}, {
                                "likely_euros": round(0.8 * SHARE, 4), "high_euros": round(2.0 * SHARE, 4),
                                "units": 4, "basis": "per unit × forecast", "unit_source": "the place's takes"}),
                            ("forecast", "render@lab", 9.0, {"units": 4}, {"euros": round(2.0 * SHARE, 4)}),
                            ("forecast", "render@lab", 9.0, {}, {"euros": 9.0}),  # nothing counted: the estimate
                            ("price", "render@hangar", 9.0, {"units": 4}, {  # an accept of 1 take, 4 forecast
                                "units": 4, "basis": "per unit × forecast", "likely_euros": round(0.8 * SHARE, 4)}),
                            ("price", "render@hangar", 9.0, {}, {"basis": "per unit × counted"}),
                            *[("price", node, 3.0, {"units": units, "guess_from": WHERE}, {
                                "likely_euros": None, "guess_euros": 3.0, "guess_from": WHERE,
                                "basis": "not measured yet"})
                              for node, units in (("bake@lab", 4), ("crops-render@lab", 4), ("render@lab", 0),
                                                  ("render@lab", None))],
                            ("price", "bake@lab", 3.0, {"store": None}, {"guess_from": ABSENT})]},
                 id="per unit times its forecast units, else a guess that says where"),
    # minutes from the stage's measured time on the runner's card rule: likely on the median unit, high on the HIGH
    # one, cards capped at the run's cap; a stage of calls holds no cards; no measured time keeps its price and says why
    pytest.param({"text": "a hall", "ledger": [],
                  "per_unit": {"render": per_unit_stage("render", count=None, forecast=MODELS, time=TIMED),
                               "ask": per_unit_stage("ask", count=None, forecast=MODELS, time={
                                   **TIMED, "setup_minutes": {"likely": 0.0, "high": 0.0}, "slots": 4,
                                   "holds": "calls"}),
                               "bake": per_unit_stage("bake", count=None, forecast=MODELS,
                                                      time={"why": "no line timed it"}),
                               "drop": per_unit_stage("drop", count=None, forecast=MODELS, time={
                                   **TIMED, "setup_minutes": {"why": "no set-up timed"}})},
                  "steps": [  # a 10-minute job on a 10-minute set-up: a card each; high on the high set-up
                      ("price", "render@lab", 9.0, {"units": 4}, {"cards": 4, "likely_minutes": 20.0,
                                                                  "high_minutes": 34.0}),
                      ("price", "render@lab", 9.0, {"units": 500}, {
                          "cards": CAP, "likely_minutes": 10 + math.ceil(500 / CAP) * 10}),
                      ("price", "ask@lab", 9.0, {"units": 8}, {"cards": None, "likely_minutes": 20.0,
                                                               "high_minutes": 40.0}),
                      ("price", "bake@lab", 9.0, {"units": 4}, {"likely_euros": round(0.8 * SHARE, 4),
                                                                "likely_minutes": None,
                                                                "minutes_why": "no line timed it"}),
                      ("price", "drop@lab", 9.0, {"units": 4}, {"likely_minutes": None,
                                                                "minutes_why": "no set-up timed"})]},
                 id="timed on its measured time by the runner's card rule"),
    # the coordinator, 2026-10-11: lines run side by side and the ledger records a batch only once it is done, so two
    # lines cleared at once could both spend the last euros; the clearing lock and reservations hold
    pytest.param({"text": "a hall", "stop": 1.5, "ledger": [{"euros": 90.0}], "steps": [("race", 6, 1)]},
                 id="lines clearing at once never both spend the stop's last euros"),
    # environment 1: a yes in chat and the guard line an agent typed later disagreed; his yes writes the line, the
    # world's start kept
    pytest.param({"text": "a hall", "ledger": [{"euros": 0.0}],
                  "steps": [("stop", 250.0, START, "owner", {"euros": 250.0, "baseline": START}),
                            ("stop", 680.0, SPENT_10K, "owner", {"euros": 680.0, "baseline": START, "before": 250.0}),
                            ("stop", 900.0, START, "agent", None)]}, id="the owner's yes writes the line"),
    # Before 2026-10-22 a grant's first run took it whole; his yes of that day, applied to one, makes each of its old
    # clearances draw what it really spent and leaves the rest to spend
    pytest.param({"text": "a hall", "ledger": [{"euros": 0.0}], "grant": 20.0,
                  "steps": [("clear", 1.5, None, None, {"euros": 1.5}),  # a test store has no stop line
                            ("release",), ("bill", 0.16), ("used", "run-a"),
                            ("clear", 1.0, OWN, "run-b", "single-use rule"),
                            ("restore", "", "hold the EUR 20 until it is spent?", "quotes"),
                            ("restore", "yes", "hold the EUR 20 until it is spent?", {"balance": 19.84}),
                            ("clear", 1.0, OWN, "run-b", {"grant": OWN})]},
                 id="a grant used up under the single-use rule holds its balance once restored"),
    # the owner, 2026-10-21: readings run without asking. Cleared with no stop line and no yes, in an agent's process;
    # its node is the reading's or the plan writing's only, within READING_EUROS a place; a grant, when tagged, counts it
    pytest.param({"text": "a hall", "ledger": [{"euros": 0.0}], "grant": 1.0,
                  "steps": [("reading", 0.3, None, None, {"node": compute.READING, "clearance": {
                                "by": Says("2026-10-21"), "places": ["hall"]}}, {"places": ["hall"]}),
                            ("rent", True, {"node": compute.READING}),
                            ("reading", 1.5, None, None, "outside the allowance", {"places": ["a"]}),
                            ("reading", 0.1, None, None, "outside the allowance", {"places": []}),
                            ("reading", 0.05, None, None, {"clearance": {"by": Says("plan writing runs without asking")}},
                             {"places": ["hall"], "node": compute.PLAN_WRITING}),
                            ("reading", 0.05, None, None, "no standing allowance",
                             {"places": ["hall"], "node": "render@hall"}),
                            ("reading", 0.6, OWN, "reading-1", {"clearance": {"grant": OWN}}, {"places": ["a", "b"]}),
                            ("reading", 0.6, OWN, "reading-1", "EUR 0.34 left", {"places": ["a", "b"]})]},
                 id="a scene inventory reading under the owner's allowance alone"),
    # the owner, 2026-10-23: the pool's idle time is the run's own cost, held on its grant, drawn as its cards billed
    pytest.param({"text": "a hall", "stop": 1.0, "ledger": [{"euros": 90.0}], "bill": 100.0, "grant": 10.0,
                  "steps": [("pool", [(ONE_CARD, 6.0)], None, "run-p", "pass the EUR 1.00 stop"),
                            # 23 + 2 passes the EUR 10 grant; 6 + 2 fits, never failing the run
                            ("pool", [({"gpu-24gb": 2, "cpu-64c": 3}, 23.0), ({"gpu-24gb": 2}, 6.0), (ONE_CARD, 3.0)],
                             OWN, "run-p", {"sizes": {"gpu-24gb": 2}, "node": compute.POOL, "key": "run-p",
                                            "clearance": {"grant": OWN}}, {"beside": 2.0}),
                            ("clear", 4.0, OWN, "run-p", "EUR 3.40 left"),
                            ("bill", 1.25),
                            ("rent", True, {"node": compute.POOL})],  # a pool card's rent point; the pool ends
                  "draws": [(1.25, 8.75)], "balance": 8.75}, id="a run's warm pool on its grant"),
    # 2026-10-24 Buy: rows high EUR 360.40 under a EUR 396.46 stop; the pool's whole 4 h holding was reserved beside the
    # rows' high, which already holds the machine time those pool machines run, so 5 of 10 machines opened. Now the
    # pool reserves its holding less the rows it bills (never below nothing), opens whole when that fits, still shrinks
    # when it does not. 2026-11-05: rows' high alone past the line, a try that may stop at it, sizes its pool beside
    # the rows' likely. 2026-11-06: a phase's preflight works the same choice out dry, against the room its Buy leaves
    # (an ended batch's line written back at its spend left no room); the likely counts a not-measured row at nothing
    # (checkout 33: its estimates in the likely too, EUR 430 against a likely EUR 99.07, and no pool fit)
    pytest.param({"text": "a hall", "stop": 396.46, "ledger": [{"euros": 90.0}], "bill": 100.0,
                  "steps": [("pool", POOLS, None, "run-buy", {"sizes": FULL, "clearance": {"euros": 0.0, "holding": 72.0}},
                             {"beside": 360.40, "covered": 300.0}),
                            ("clear", 400.0, None, None, "pass the EUR 396.46 stop"),
                            ("release",),
                            ("pool", POOLS, None, "run-tight", {"sizes": HALF, "clearance": {  # 52 + 360.40 passes
                                "euros": 16.0, "beside": "high"}},  # 16 + 360.40 fits, the likely unread
                             {"beside": 360.40, "covered": 20.0, "likely": (40.0, 30.0)}),
                            ("release",),
                            ("fits", POOLS, 360.40, 20.0, (40.0, 30.0), None, (HALF, "high", None)),
                            ("fits", POOLS, 400.0, 300.0, (40.0, 30.0), None, (FULL, "likely", None)),
                            ("fits", POOLS, 400.0, 0.0, (395.0, 0.0), None, (None, None, "pass the EUR 396.46 stop")),
                            ("fits", POOLS, 400.0, 0.0, (395.0, 0.0), 900.0, (FULL, "high", None)),
                            ("fits", POOLS, 400.0, 0.0, (395.0, 0.0), 10.0, (None, None, "the phase's Buy leaves")),
                            ("pool", POOLS, None, "run-stop", {"sizes": FULL, "clearance": {"beside": "likely",
                                                                                          "euros": 42.0}},
                             {"beside": 400.0, "covered": 300.0, "likely": (40.0, 30.0)}),
                            ("clear", 360.0, None, None, "pass the EUR 396.46 stop"),  # 42 + 360 passes
                            ("release",),
                            ("pool", POOLS, None, "run-shrunk", {"sizes": HALF},  # 72 + 340 passes, 36 + 340 fits
                             {"beside": 400.0, "likely": (340.0, 0.0)}),
                            ("release",),
                            ("pool", POOLS, None, "run-none", "pass the EUR 396.46 stop",  # not one beside the likely
                             {"beside": 400.0, "likely": (395.0, 0.0)}),
                            ("pool", POOLS, None, "run-fits", "pass the EUR 396.46 stop",  # the high fits alone
                             {"beside": 395.0, "likely": (40.0, 0.0)}),
                            ("rows", {}, 95.0), ("rows", {"field": "likely_euros"}, 2.0),
                            ("rows", {"pooled": True, "field": "likely_euros"}, 2.0)]},
                 id="a warm pool reserves only its holding beyond the rows it bills"),
    # Batch 1 of 2026-10-24: the pool closed at its cleared 4 h with ~550 rows queued, and every finish after failed.
    # Its run's heartbeat holds it longer: each further holding checked against the money with every reservation,
    # added to the pool's own one, refused once the money has no room or the pool has ended; under a grant the more
    # is held on it and its spend drawn once
    pytest.param({"text": "a hall", "stop": 20.0, "ledger": [{"euros": 90.0}], "bill": 100.0,
                  "steps": [("pool", [(ONE_CARD, 6.0)], None, "run-long", {"sizes": ONE_CARD}),
                            ("extend", 6.0, None, None, {"euros": 12.0, "holding": 12.0, "high_minutes": 480}),
                            ("extend", 10.0, None, None, "pass the EUR 20.00 stop"),
                            ("clear", 9.0, None, None, "pass the EUR 20.00 stop"),  # 12 held + 9
                            ("release",),
                            ("extend", 1.0, None, None, "has ended")]}, id="a warm pool held longer"),
    pytest.param({"text": "a hall", "stop": 1.0, "ledger": [{"euros": 90.0}], "bill": 100.0, "grant": 10.0,
                  "steps": [("pool", [(ONE_CARD, 3.0)], OWN, "run-g", {"clearance": {"grant": OWN}}),
                            ("extend", 3.0, OWN, "run-g", {"holding": 6.0}),  # 3.30 more held: 3.40 left
                            ("extend", 4.0, OWN, "run-g", "EUR 3.40 left"),
                            ("bill", 1.25), ("release",)],
                  "draws": [(1.25, 8.75)], "balance": 8.75}, id="a warm pool held longer under a grant"),
    # environment 1, 2026-10-12 to 18: no paid job is killed halfway; past the stop it finishes (the bill far past any
    # stop: nothing in the watch reads it), and only past twice its forecast minutes (its batches' pre-flights when
    # readable, a half written line falling back to the forecast) and past every deadline its jobs declared it is
    # ended, its make's own children signalled. 2026-11-09: light-passes@campgrounds rendered past twice its 3 min
    # forecast inside its Jobs' 150 min and was stopped twice. Benchmark of 2026-10-23: a rough model (12 minutes)
    # waited an hour and a half for the pool's first card; 2026-11-08: settle@garage (8 minutes) worked 15 free
    # minutes before its one cluster job: only the minutes a cloud runner runs count
    pytest.param({"text": "a hall", "ledger": [{"euros": 0.0}], "bill": 10_000.0,
                  "steps": [("watch", 30.0, {}, [(59, {}, False, 0), (61, {}, True, 1), (61, {}, True, 1)],
                             ["runaway render@hangar k"]),
                            ("watch", None, {}, [(1e9 / 60, {}, False, 0)], []),
                            ("watch", 300.0, {"batches": [{"high_minutes": 20.0}] * 2},
                             [(79, {}, False, 0), (81, {}, True, 1)], []),
                            ("watch", 30.0, {"batches": "unreadable"}, [(61, {}, True, 1)], []),
                            ("watch", 3.0, {"deadlines": [150]}, [(120, {}, False, 0), (151, {}, True, 1)],
                             ["past every deadline its jobs declared"]),
                            ("watch", 12.0, {}, [*[(minute, {"waiting": True}, False, 0) for minute in range(1, 91)],
                                                 (110, {}, False, 0), (115, {}, True, 1)], []),
                            ("watch", 8.0, {}, [*[(minute, {"paying": False}, False, 0) for minute in range(1, 21)],
                                                (36, {}, False, 0), (37, {}, True, 1)], []),
                            ("children",)]}, id="a started job runs on and stops only as a runaway"),
    # 2026-10-18 review: a reservation was dropped after 4 h whether or not its run had ended
    pytest.param({"text": "a hall", "ledger": [{"euros": 0.0}],
                  "steps": [("open", 5, {"holder": "alive"}, True), ("open", 5, {"holder": "reused"}, False),
                            ("open", 5, {"high_minutes": 60.0}, False),
                            ("open", 5, {"high_minutes": 200.0}, True)]},  # twice 200 min is past 5 h
                 id="a reservation stays open while its run lives or until its runaway limit"),
    # spend counts from the world's start across months, its parts the cockpit names (the bill over the ledger is cloud
    # less ledger). 2026-11-02: credits given back on October's Google bill made Batch 1 read EUR -635.25 spent and the
    # guard's room grew past its budget; a month's book that fell since the baseline counts 0, never less
    pytest.param({"text": "a hall", "ledger": [{"euros": 0.0}],
                  "steps": [("spent", {"month": "2026-10", "bill": 120.0, "ledger": 100.0, "google": 1.0},
                             {"2026-10": {"bill": None, "ledger": 300.0, "google": 5.0},
                              "2026-11": {"bill": 30.0, "ledger": 25.0, "google": 2.0}},
                             (200.0 + 4.0) + (30.0 + 2.0), {"cloud": 230.0, "ledger": 225.0, "google": 6.0}),
                            ("spent", {"month": "2026-10", "bill": 120.0, "ledger": 100.0, "google": 900.0},
                             {"2026-10": {"bill": 150.0, "ledger": 140.0, "google": 61.07},
                              "2026-11": {"bill": 10.0, "ledger": 8.0, "google": 3.5}},
                             53.5, {"cloud": 40.0 + 10.0, "ledger": 40.0 + 8.0, "google": 0.0 + 3.5})]},
                 id="spend counts from the world's start across months"),
    # a place whose sound takes all stand made counts 0 takes: EUR 0 and no time (COUNTED_ZERO); any other rule's 0 is
    # nothing counted, so no price (unknown, never free)
    pytest.param({"text": "a hall", "ledger": [],
                  "steps": [("unit_price", "sound@airlock", 0, {"likely_euros": 0.0, "high_euros": 0.0, "units": 0}),
                            ("minutes", "sound", 0, {"likely_minutes": 0.0, "high_minutes": 0.0, "cards": 0}),
                            ("unit_price", "closeup@airlock", 0, None), ("unit_price", "sound@airlock", None, None)]},
                 id="a count of zero is free only where its rule counts zero"),
    # the owner's standing rule of 2026-10-20: benchmarks only, at most EUR 20, his answer and the question quoted, no
    # expiry (2026-10-23); a Google month he gave in the same answer goes into the books as his
    pytest.param({"text": "a hall", "ledger": [{"euros": 0.0}], "fresh_books": True,
                  "steps": [*[("grant", given, words, None) for given, words in (
                                ({"euros": 20.01}, "at most EUR 20"), ({"euros": 0}, "at most EUR 20"),
                                ({"euros": float("nan")}, "at most EUR 20"), ({"purpose": "a film"}, "benchmark only"),
                                ({"answer": "  "}, "quotes"), ({"question": ""}, "quotes"),
                                ({"google_month": -1}, "finite figure"))],
                            ("grant", {"euros": 20}, {"answer": "Yes", "question": QUESTION, "euros": 20.0,
                                                      "expires": ABSENT, "google_month": None}, None),
                            ("grant", {"answer": "Yes, and Google is at 412", "euros": 5, "google_month": 412.0},
                             {"euros": 5.0}, {"state": "known", "google_before": 412.0, "google_by": Holds(OWN)})]},
                 id="a grant is a quoted benchmark of at most EUR 20, its Google month the owner's"),
    # a grant record that does not quote his answer, or is dearer than EUR 20, clears nothing. The store's listing walks
    # only the prefix's folder and answers as the whole walk did, a link on the way walked whole (2026-11-06: 16 bake
    # clients walked every blob for one node's clearances)
    pytest.param({"text": "a hall", "ledger": [{"euros": 0.0}],
                  "steps": [("forge", "forged", {"answer": ""}),
                            ("clear", 1.0, "forged", "run-a", "not a quoted benchmark grant"),
                            ("forge", "dear", {"euros": 50.0}),
                            ("clear", 1.0, "dear", "run-a", "not a quoted benchmark grant"),
                            ("listing", "clearances/n/k/", ["clearances/n/k/a.json", "clearances/n/k/b.json"]),
                            *[("listing", prefix, None) for prefix in ("clearances/n/k", "clearances/", "", "link/",
                                                                       "missing/x/", "blobs/")]]},
                 id="an unquoted or too dear grant clears nothing"),
    # a time limit decides whether an answer comes back, never what it says: read when the call is made
    pytest.param({"text": "a hall", "ledger": [{"euros": 0.0}],
                  "steps": [("timeout", None, 120.0), ("timeout", "90", 90.0), ("timeout", None, 120.0)]},
                 id="the judge timeout is an operational setting outside every key"),
    # a paid row records the line that builds it, so a guess names it; a row made from another by dataclasses.replace
    # keeps the first's line unless its estimate changed
    pytest.param({"text": "a hall", "ledger": [{"euros": 0.0}],
                  "steps": [("row", {"paid": True, "euros": 2.0}, {"name": "render-again"}, "built"),
                            ("row", {"paid": True, "euros": 2.0}, {"euros": 3.0}, "replaced"),
                            ("row", {"paid": True}, {"name": "render-again"}, None)]},
                 id="a stage row says where its estimate is written"),
    # its run's heartbeat holds the pool longer only once its end is near, and only while the money has room
    pytest.param({"text": "a hall", "stop": 13.0, "ledger": [{"euros": 90.0}], "bill": 100.0,
                  "steps": [("pool", [(ONE_CARD, 6.0)], None, "run-beat", {"sizes": ONE_CARD}),
                            ("heartbeat", "run-beat", 7200, [], None),  # two hours left: not yet
                            ("heartbeat", "run-beat", 600, [12.0], None),
                            # 12 held + 6 passes the EUR 13 stop: the pool ends at its cleared end
                            ("heartbeat", "run-beat", 600, [], "pass the EUR 13.00 stop")]},
                 id="the run's heartbeat holds its pool longer only near its end and within its money"),
    # a body face's call is ledgered as caller body-face, a close-up's as pro; a call started and never finished counts
    # at its estimate; another stage's call, or one outside the run's time, is not its own
    pytest.param({"text": "a hall", "ledger": [{"euros": 0.0}], "google_calls": RUN_CALLS,
                  "steps": [("drawn", "body-face-earth", 0.08), ("drawn", "closeup@hall", 0.14)]},
                 id="a run draws its stage's Gemini calls in its time under the callers they carry"),
    # only the owner knows what Google billed before its ledger began again (#13): an agent's figure opens nothing.
    # The cockpit's Google month is the billing export's bill once read back, else the owner's books figure plus the
    # ledger since, else no figure, never the call ledger alone (it showed EUR 0.00 for a month billed about 1,030)
    pytest.param({"text": "a hall", "ledger": [{"euros": 0.0}], "fresh_books": True,
                  "google_calls": [(f"{MONTH}-02T09:00:00+00:00", "finished", "pro", 2.5)],
                  "steps": [("google_month", 400.0, "owner"),
                            ("google_line", {"state": "lost", "google_unread": "the export holds no rows yet"},
                             {"euros": None, "partial": True, "origin": "the export holds no rows yet"}),
                            ("google_line", {"state": "known", "google_before": 1030.0, "google_at": "t"},
                             {"euros": 1032.5}),
                            ("google_line", {"state": "known", "google_bill": 1031.5, "google_bill_at": "t",
                                             "google_before": 1030.0},
                             {"euros": 1031.5, "partial": False, "origin": Says("billing export")}),
                            ("days",)]},
                 id="the owner's Google month is his, the cockpit's line the bill else his figure else none"),
    # #36, 2026-10-30: a retake remakes only the takes the owner's reject names, yet its clearance drew per unit times
    # every take the output accepted before the rejected one made (pixal@cockpit: 11 takes, EUR 2.58, for one at EUR
    # 0.23), and the Buy's price the same. A make that is no retake keeps that price
    pytest.param({"text": "a hall", "ledger": [], "takes": ("a hall", "a wide hall"),
                  "per_unit": {"render": per_unit_stage("render", forecast={"rule": "one", "source": "a toy's"})},
                  "steps": [("retake", None, round(1.5 * SHARE, 4)),
                            ("reject takes", ("b-s1",)),
                            ("retake", ["b-s1"], round(0.5 * SHARE, 4))]},
                 id="a retake is cleared and priced for its own takes, not every take of its place"),
    # the repository's per-unit file: a settle run's likely minutes within a minute of the paper ledger's settle runs'
    # median wall minutes and its high at or above their HIGH quantile (the set-up in the machine counted, not only the
    # start wait). Buy of 2026-10-24: pixal finished its takes on machines of their own after its batch and the forecast
    # held the batch alone; pixal's time holds its finish step (`then`), read from the blender lines its node ran, and
    # unit_minutes adds it: at least a set-up and a finish job more
    pytest.param({"text": "a hall", "ledger": [],
                  "steps": [("ledger timed", "settle"), ("finish", "pixal", 20), ("then", {"why": "none"}, 20, (0.0, 0.0)),
                            ("then times", [SPENT_PIXAL, {**SPENT_PIXAL, "ticket": "settle@yard k"}], "pixal", 1, 45.0)]},
                 id="a stage is timed on the runs it is read from, pixal's finish of every take too"),
]


def a_world(row):
    """The row's runner: its brief made (and rejected where the row says), in a test store or the framework's."""
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "hangar.txt").write_text(row["text"])
    store = (Store.default() if "framework" in row else
             Store.in_folder(compute.PROPS_HOME / "trial-test/store") if "trial" in row else
             Store.in_folder(tempfile.mkdtemp()))
    if "trial" in row:
        (Store.default().cache.parent / "reservations.json").unlink(missing_ok=True)  # earlier tests' runs
    world = row.get("framework", row.get("trial", "toy"))
    runner = graph.Runner([BRIEF, RENDER], graph.Environment(world, 1, {"data": data}), store)
    runner.run_node(BRIEF, "hangar")
    for text in row.get("takes", ()):  # accepted makes of a retake's stage: a reject puts the earlier one back
        (data / "hangar.txt").write_text(text)
        made = graph.Runner([BRIEF, MADE_TAKES], runner.world, store)
        made.run_node(BRIEF, "hangar")
        made.run_node(MADE_TAKES, "hangar")
    if row.get("reject"):
        review.reject(store, "brief@hangar", store.accepted("brief@hangar"), "owner", "the wrong hall")
    return runner


def agrees(found, expected, grant):
    """Whether `found` holds the expected fields: nested dicts field by field, OWN the row's grant, Says words it
    holds, a (low, high) range it lies strictly inside, else the value itself."""
    if isinstance(expected, dict):
        return isinstance(found, dict) and all(agrees(found.get(field, ABSENT), value, grant)
                                               for field, value in expected.items())
    if isinstance(expected, Says):
        return isinstance(found, str) and expected in found
    if isinstance(expected, Holds):
        return isinstance(found, (str, list, tuple)) and (grant if expected == OWN else str(expected)) in found
    if isinstance(expected, tuple):
        return expected[0] < found < expected[1]
    return found == (grant if expected == OWN else expected)


@pytest.mark.parametrize("row", ASKS)
def test_paid_work_starts_only_inside_its_clearance(row):
    """Every paid start asks the runner's clearance: refused (and nothing written) while a prerequisite failed or is
    not accepted, the run has no estimate or measure, its high would pass the world's stop line with what was spent
    since the line and everything in flight (less what it ledgered, open overrides and warm pools too, however many
    ask at once), or a benchmark grant's balance; else cleared at its measured high, kept in the store with no typed
    yes, the job keyed to it. A warm pool clears its holding beyond the rows it bills, shrinking to fit, and is held
    longer only while the money has room; a reading clears under the owner's allowance alone; a grant draws each
    run's real spend, a restored one too; only the owner writes the stop line, the world's start kept. That high is
    the price the cockpit shows: its measured runs, else per unit times the units counted or forecast, timed on the
    card rule, else a guess at the estimate that names where it is written; a retake's price its own takes alone.
    The run's heartbeat holds its pool longer near its end within the money; a run draws only its own Gemini calls;
    the Google month is the owner's alone and the cockpit's line the bill else his figure; the judge's time limit
    stays outside every key."""
    assert SANDBOX["sandbox_refusal"](os.environ) is None, "run in a sandbox home"
    runner = a_world(row)
    if "stop" in row:
        stop_at(runner, row["stop"], baseline=row.get("baseline", START))
    ledger(*row["ledger"])
    BILL["euros"] = row.get("bill", 0.0)
    if "override" in row:
        runner.store.write_spend_yes(compute.OVERRIDE, "repaint", {"node": compute.OVERRIDE, "key": "repaint",
                                                                   "euros": row["override"], "by": "owner",
                                                                   "at": graph.now()})
    grant = compute.grant_benchmark("Yes", QUESTION, row["grant"], store=runner.store)["id"] if "grant" in row else None
    home = Store.default() if "trial" in row else runner.store  # the store holding the world's line and reservations
    tickets, cleared, newest = [], 0, None
    outputs, kept, kept_books, listing = Outputs(row["outputs"]) if "outputs" in row else None, compute.PER_UNIT, \
        BOOKS.BOOKS, None
    if row.get("fresh_books"):
        BOOKS.BOOKS = pathlib.Path(tempfile.mkdtemp()) / "books.json"
    kept_calls, beats = google_spend.LEDGER, {"plan": {}, "extended": []}
    if "google_calls" in row:
        google_spend.LEDGER = pathlib.Path(tempfile.mkdtemp()) / "google-ledger.jsonl"
        google_spend.LEDGER.write_text("".join(json.dumps(
            {"time": at, "call": f"c{index}", "state": state, "caller": caller, "euros": euros, "model": GEMINI,
             "estimate": 0.05}) + "\n" for index, (at, state, caller, euros) in enumerate(row["google_calls"])))
    if "per_unit" in row:
        compute.PER_UNIT = pathlib.Path(tempfile.mkdtemp()) / "per-unit.json"
        compute.PER_UNIT.write_text(json.dumps({"stages": row["per_unit"]}))
    try:
        for number, step in enumerate(row["steps"]):
            if step[0] == "timeout":
                from score.adapters import models
                _, setting, seconds = step
                saved = os.environ.pop(compute.JUDGE_TIMEOUT, None)
                try:
                    if setting is not None:
                        os.environ[compute.JUDGE_TIMEOUT] = setting
                    assert compute.judge_timeout() == seconds, step
                finally:
                    os.environ.pop(compute.JUDGE_TIMEOUT, None)
                    if saved is not None:
                        os.environ[compute.JUDGE_TIMEOUT] = saved
                assert not any("timeout" in name for name in models.api_record("gemini-judge")), step
                continue
            if step[0] == "row":
                _, fields, replaced, named = step
                here = "score/adapters/compute/test_paid_work_starts_only_inside_its_clearance.py"
                built, built_at = a_stage_row("render", **fields), f"{here}:{sys._getframe().f_lineno}"
                moved, moved_at = dataclasses.replace(built, **replaced), f"{here}:{sys._getframe().f_lineno}"
                assert built.euros_from == (built_at if "euros" in fields else None), (step, built.euros_from)
                assert moved.euros_from == {"built": built_at, "replaced": moved_at, None: None}[named], (
                    step, moved.euros_from)
                continue
            if step[0] == "heartbeat":
                from score import __main__ as command
                _, run, seconds, euros, words = step
                beats["plan"]["deadline"] = time.time() + seconds
                before = len(beats["extended"])
                fake = types.SimpleNamespace(current=lambda run_id: beats["plan"] if run_id == run else None,
                                             holding_euros=lambda sizes, hours: 6.0,
                                             extend=lambda run_id, deadline, more: beats["extended"].append(
                                                 (run_id, deadline, more)))
                saved = command.cloud_tool, os.environ.get(compute.RUN_ID)
                command.cloud_tool, os.environ[compute.RUN_ID] = (lambda name: fake), run
                command.POOL_TICKET[:] = [newest]
                try:
                    command.extend_pool(runner)
                finally:
                    command.cloud_tool, command.POOL_TICKET[:] = saved[0], []
                    os.environ.pop(compute.RUN_ID) if saved[1] is None else os.environ.update({compute.RUN_ID: saved[1]})
                hours = compute.ledger().BATCH_HOURS
                assert beats["extended"][before:] == [(run, beats["plan"]["deadline"] + hours * 3600, more)
                                                      for more in euros], (step, beats["extended"])
                assert ("refused" not in newest if words is None else words in newest.get("refused", "")), (
                    step, newest.get("refused"))
                continue
            if step[0] == "drawn":
                hold = {"node": step[1], "key": "k", "at": "2026-10-22T08:00:00+00:00"}
                assert compute.run_spend(runner.store, hold, "2026-10-22T08:01:00+00:00")["google"] == step[2], step
                continue
            if step[0] == "retake":
                from score.__main__ import selected_price
                from score.stages.complete.gaps import price
                _, takes, euros = step
                paid = graph.Runner([BRIEF, PAID_TAKES], runner.world, runner.store)
                assert compute.retake_takes(paid, "render@hangar") == takes, step
                assert compute.planned_forecast(paid, "render@hangar", 9.0)["euros"] == euros, step
                planned, price.planned_units = price.planned_units, lambda *_: 3  # the Buy's plan: the place's every take
                try:
                    buy = types.SimpleNamespace(node="render@hangar", euros=9.0)
                    assert selected_price(paid, buy)["high_euros"] == euros, step
                finally:
                    price.planned_units = planned
                continue
            if step[0] == "reject takes":
                review.reject(runner.store, "render@hangar", runner.store.accepted("render@hangar"), "owner", "a block",
                              takes=step[1])
                continue
            if step[0] in ("ledger timed", "finish", "then", "then times"):
                sys.path.insert(0, str(compute.REPO / "tools/costs"))
                import per_unit
            if step[0] == "ledger timed":
                paper = compute.REPO / "paper/evidence/cloud/ledger.jsonl"
                walls = [line["wall_minutes"] for line, _ in per_unit.ledger_lines([paper])
                         if per_unit.matches(line, per_unit.SPECS[step[1]]["cloud"])]
                timed = compute.unit_minutes(step[1], 1)
                assert abs(timed["likely_minutes"] - statistics.median(walls)) <= 1.0, (timed, sorted(walls))
                assert timed["high_minutes"] >= per_unit.quantile(walls, per_unit.HIGH), (timed, sorted(walls))
                continue
            if step[0] == "finish":
                _, stage, units = step
                then = compute.per_unit(stage)["time"]["then"]
                assert then["kind"] == per_unit.SPECS[stage]["then"]["kind"] and "unit_seconds" in then, then
                likely, high = compute.then_minutes(then, units)
                assert likely >= then["setup_minutes"]["likely"] + then["unit_seconds"]["likely"] / 60, (likely, then)
                assert high >= likely and compute.unit_minutes(stage, units)["likely_minutes"] is not None, step
                continue
            if step[0] == "then":
                assert compute.then_minutes(step[1], step[2]) == step[3], step
                continue
            if step[0] == "then times":
                _, lines, stage, count, likely = step
                found = per_unit.then_times([(line, f"test line {index}") for index, line in enumerate(lines)], stage,
                                            "blender")
                assert found["lines"] == count and found["unit_seconds"]["likely"] == likely, found
                continue
            if step[0] == "google_month":
                kept_text = books_text()
                assert step[2] in refused(lambda: as_agent(lambda: compute.owners_google_month(step[1]))), step
                assert books_text() == kept_text, (step, books_text())
                continue
            if step[0] == "google_line":
                from score import __main__ as command
                BOOKS.write_books({"month": MONTH, **step[1]})
                line = command.google_line()
                assert agrees(line, step[2], grant), (step, line)
                continue
            if step[0] == "days":
                from score import __main__ as command
                days = command.ledger_days(MONTH)
                assert days[0]["day"] == f"{MONTH}-01" and set(days[-1]) == {"day", "cloud", "models"}, days
                continue
            if step[0] == "count":
                _, output, rule, units = step
                assert compute.counted_units(outputs, output, rule) == units, step
                continue
            if step[0] == "unit_price":
                _, node, units, expected = step
                answer = compute.forecast_price(node, units)
                assert (answer is None if expected is None else agrees(answer, expected, grant)), (step, answer)
                continue
            if step[0] == "minutes":
                assert compute.unit_minutes(step[1], step[2]) == step[3], step
                continue
            if step[0] == "watch":
                _, forecast, given, ticks, words = step
                folder, clock, state, stops = pathlib.Path(tempfile.mkdtemp()), [0.0], {}, []

                def batches():
                    if given.get("batches") == "unreadable":
                        raise ValueError("a line half written")
                    return given.get("batches", [])
                watch = guard.Watch("render@hangar k", forecast, folder, batches=batches,
                                    stop=lambda: stops.append(1), clock=lambda: clock[0],
                                    waiting=lambda: state.get("waiting", False), paying=lambda: state.get("paying", True),
                                    deadlines=lambda: [WALL + minutes * 60 for minutes in given.get("deadlines", [])],
                                    wall=lambda: WALL + clock[0])
                for minute, now, ran_away, stopped in ticks:
                    clock[0] = minute * 60
                    state.clear()
                    state.update(now)
                    assert watch.check() == ran_away and len(stops) == stopped, (step[:3], minute, stops)
                told = (folder / guard.OUTBOX).read_text() if (folder / guard.OUTBOX).exists() else ""
                assert all(said in told for said in words), (step[:3], told)
                continue
            if step[0] == "children":
                plain, cloud = subprocess.Popen(ASLEEP), None
                try:
                    assert not guard.cloud_work_below()
                    cloud = subprocess.Popen([*ASLEEP, str(compute.REPO / "tools/cloud/blender_cloud.py")])
                    assert guard.cloud_work_below() and not guard.cloud_work_below(plain.pid)
                    assert {plain.pid, cloud.pid} <= set(guard.children(os.getpid()))
                    guard.stop_children()
                    assert plain.wait(timeout=10) != 0 and cloud.wait(timeout=10) != 0
                finally:
                    for child in (plain, cloud):
                        if child is not None:
                            child.kill()
                continue
            if step[0] == "open":
                _, hours, held, expected = step
                now = datetime.datetime.now(datetime.timezone.utc)
                marks = {"alive": guard.process_mark(os.getpid()), "reused": f"{os.getpid()} 0"}
                held = {**held, **({"holder": marks[held["holder"]]} if "holder" in held else {})}
                assert compute.still_open((now - datetime.timedelta(hours=hours)).isoformat(), held, now) == expected, \
                    step
                continue
            if step[0] == "spent":
                _, start, months, since, parts = step
                assert guard.spent_since(start, months) == since, step
                assert guard.spent_parts(start, months) == parts, step
                continue
            if step[0] == "grant":
                _, given, expected, books = step
                arguments = {"answer": "Yes", "question": QUESTION, "euros": 10.0, "store": runner.store, **given}
                kept_grants, kept_text = runner.store.objects.keys("grants/"), books_text()
                if isinstance(expected, dict):
                    made = compute.grant_benchmark(**arguments)
                    assert runner.store.read(f"grants/benchmark/{made['id']}.json") == made, step
                    assert agrees(made, expected, made["id"]), (step, made)
                    assert (books_text() == kept_text if books is None else
                            agrees(BOOKS.this_months_books(), books, made["id"])), (step, books_text())
                else:
                    assert expected in refused(lambda: compute.grant_benchmark(**arguments)), step
                    assert runner.store.objects.keys("grants/") == kept_grants and books_text() == kept_text, step
                continue
            if step[0] == "forge":
                _, name, fields = step
                runner.store.write_once(f"grants/benchmark/{name}.json", {
                    "id": name, "purpose": "benchmark", "euros": 10.0, "answer": "Yes", "question": QUESTION,
                    "at": graph.now(), "single_use": True, **fields})
                continue
            if step[0] == "listing":
                _, prefix, keys = step
                listing = listing or a_listing()
                assert compute.narrowed_keys(listing, prefix) == compute.WHOLE_WALK(listing, prefix), step
                assert keys is None or listing.keys(prefix) == keys, step
                continue
            if step[0] in ("price", "forecast"):
                via, node, estimate, given, expected = step
                asked = {"store": outputs, **given}
                answer = (compute.run_price if via == "price" else compute.run_forecast)(node, estimate, **asked)
                assert not isinstance(expected, Exactly) or answer == expected, (step, answer)
                for field, value in expected.items():
                    if value == RESERVED:
                        value = compute.run_forecast(node, estimate, asked["store"], asked.get("units"))["euros"]
                    found = answer.get(field, ABSENT)
                    if isinstance(value, tuple):
                        assert value[0] < found < value[1], (step, field, answer)
                    else:
                        assert found == value, (step, field, answer)
                continue
            if step[0] == "rows":
                from score.__main__ import rows_high
                assert rows_high(ROWS, **step[1]) == step[2], step
                continue
            if step[0] == "fits":
                _, choices, beside, covered, likely, room, (sizes, by, words) = step
                reservations = compute.covering_store(runner.store).cache.parent / "reservations.json"
                before = reservations.read_text() if reservations.exists() else None
                found = compute.pool_fits(runner, choices, beside, covered, likely, room=room)
                assert found[:2] == (sizes, by) and (found[2] is None if words is None else words in found[2]), (
                    step, found)
                assert (reservations.read_text() if reservations.exists() else None) == before, step
                continue
            if step[0] == "race":
                fork = multiprocessing.get_context("fork")
                ready, pipes = fork.Event(), [fork.Pipe(duplex=False) for _ in range(step[1])]
                processes = [fork.Process(target=clear_in_a_process, args=(runner, ready, sending))
                             for _, sending in pipes]
                for process in processes:
                    process.start()
                for _, sending in pipes:
                    sending.close()  # a process that dies fails the test with EOFError instead of hanging it
                ready.set()
                answers = sorted(receiving.recv() for receiving, _ in pipes)
                for process in processes:
                    process.join()
                assert answers == ["cleared"] * step[2] + ["refused"] * (step[1] - step[2]), answers
                continue
            if step[0] == "bill":
                billed(newest, step[1])
                continue
            if step[0] == "release":
                compute.release(tickets.pop())
                continue
            if step[0] == "used":  # as the single-use rule left a grant: a used mark and its clearance counted
                runner.store.write_once(f"grants/used/{grant}.json", {"run": step[1], "at": newest["clearance"]["at"]})
                runner.store.write_once(f"grants/spent/{grant}/1.json",
                                        {field: newest["clearance"][field] for field in ("node", "key", "euros", "at")})
                continue
            if step[0] == "restore":
                _, answer, question, expected = step
                if isinstance(expected, dict):
                    restored = compute.restore_grant(grant, answer, question, runner.store)
                    assert agrees(restored, expected, grant), (step, restored)
                    assert runner.store.read(f"grants/restored/{grant}.json") == restored, step
                else:
                    assert expected in refused(lambda: compute.restore_grant(grant, answer, question, runner.store))
                continue
            if step[0] == "stop":
                _, euros, baseline, who, expected = step
                at = f"2026-10-18T{9 + number:02d}:00:00+00:00"
                was = guard.current(home, runner.world.name)
                write = lambda: guard.set_line(home, runner.world.name, euros, "the row", who, at, baseline)  # noqa: E731
                if expected is None:  # an agent's process writes no stop line
                    with pytest.raises(PermissionError):
                        as_agent(write)
                    assert guard.current(home, runner.world.name) == was, step
                else:
                    assert agrees(as_owner(write), expected, grant), step
                    assert guard.current(home, runner.world.name)["euros"] == euros, step
                continue
            if step[0] == "rent":
                _, given, expected = step
                rent = lambda: compute.require_cleared("a batch", *([runner.store] if given else []))  # noqa: E731
                if newest in tickets:
                    tickets.remove(newest)
                    with compute.spending(newest):
                        said = rent() if isinstance(expected, dict) else refused(rent)
                else:
                    os.environ[compute.TICKET] = f"{newest['node']} {newest['key']}"
                    try:
                        said = rent() if isinstance(expected, dict) else refused(rent)
                    finally:
                        os.environ.pop(compute.TICKET)
                if isinstance(expected, dict):
                    assert all(said[field] == value for field, value in expected.items()), (step, said)
                else:
                    assert expected in said, (step, said)
                continue
            tagged = grant if step[2] == OWN else step[2]
            if step[0] == "extend":
                _, euros, _, run, expected = step
                extend = lambda: compute.extend_pool(runner, newest, euros, 4)  # noqa: E731
                if isinstance(expected, dict):
                    holding = as_benchmark(tagged, run, extend) if tagged else extend()
                    mine = compute.open_reservations(pathlib.Path(newest["reservations"]))[newest["clearance"]["at"]]
                    assert holding == mine["holding"] and agrees(mine, expected, grant), (step, holding, mine)
                else:
                    said = refused(lambda: as_benchmark(tagged, run, extend) if tagged else extend())
                    assert expected in said, (step, said)
                continue
            via, what, _, run, expected, *more = step
            given = more[0] if more else {}
            job_store = compute.job_contract.stores.FolderStore(tempfile.mkdtemp())
            spec = {"kind": "blender", "image": "img", "command": ["true"], "euros": what}
            ask = {"submit": lambda: compute.submit(runner, "render@hangar", job_store, "run1", "job1", spec),
                   "clear": lambda: compute.clearance(runner, "render@hangar", what),
                   "pool": lambda: compute.pool_clearance(runner, run, what, 4, **given),
                   "reading": lambda: as_agent(lambda: compute.reading_clearance(
                       runner.store, given["places"], what, node=given.get("node", compute.READING)))}[via]
            if isinstance(expected, dict):
                answer = as_benchmark(tagged, run, ask) if tagged else ask()
                if via in ("submit", "clear"):
                    cleared += 1
                    key = runner.ticket("render@hangar")["key"]
                    records = runner.store.clearances("render@hangar", key)
                    assert len(records) == cleared, (step, records)
                    assert agrees(records[-1], expected, grant), (step, records[-1])
                    assert runner.store.spend_yes("render@hangar", key) is None, step
                else:
                    records = runner.store.clearances(answer["node"], answer["key"])
                    assert agrees(answer, expected, grant), (step, answer)
                if via == "submit":
                    job = compute.job_contract.stores.read_json(job_store, answer)
                    assert job["node"] == "render@hangar" and job["node_key"] == key, (step, job)
                else:
                    assert answer["clearance"] == records[-1], step
                    assert pathlib.Path(answer["reservations"]).parent == home.cache.parent, (step, answer)
                    tickets.append(answer)
                    newest = answer
            else:
                written = runner.store.objects.keys("clearances/")
                said = refused(lambda: as_benchmark(tagged, run, ask) if tagged else ask())
                for words in (expected,) if isinstance(expected, str) else expected:
                    assert words in said, (step, said)
                assert job_store.keys("") == [] and runner.store.objects.keys("clearances/") == written, step
        if "outbox" in row:
            count, words = row["outbox"]
            assert len(outbox(runner)) == count and words in outbox(runner)[0], outbox(runner)
        runner.run_node(BRIEF, "hangar")  # free work goes on
        if "draws" in row:
            draws = [runner.store.read(key) for key in runner.store.objects.keys(f"grants/draws/{grant}/")]
            assert [(draw["euros"], draw["balance"]) for draw in draws] == row["draws"], draws
        if "balance" in row:
            assert compute.grant_balance(runner.store, grant, {}) == row["balance"]
    finally:
        compute.PER_UNIT, BOOKS.BOOKS, google_spend.LEDGER = kept, kept_books, kept_calls
        for ticket in tickets:
            compute.release(ticket)
        BILL["euros"] = 0.0


if __name__ == "__main__":
    SANDBOX["refuse_outside_sandbox"]()
    no_cloud_and_books_open(pytest.MonkeyPatch())  # this process only: never undone
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            marks = [mark for mark in getattr(test, "pytestmark", []) if mark.name == "parametrize"]
            for case in [param.values for param in marks[0].args[1]] if marks else [None]:
                patch = pytest.MonkeyPatch()  # a test that takes pytest's monkeypatch gets its own, undone after it
                try:
                    test(*case) if case else test(*[patch for _ in test.__code__.co_varnames[:test.__code__.co_argcount]])
                finally:
                    patch.undo()
            print("ok", name)
