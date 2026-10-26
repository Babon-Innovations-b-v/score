"""Paid work starts only inside a clearance the runner gave, priced on measured numbers, and only while its money
has room: the environment's stop line (or a benchmark grant's balance, or the owner's reading allowance) with
everything already spent since the line and everything in flight counted, under one lock; a started job is never
stopped halfway except as a runaway. No cloud: the job store is a folder, the ledger and the bill are set by each
test, the stop lines and grants live in a sandbox store.

Each test's break (applied once, seen red, reverted), in score/adapters/compute/__init__.py unless named:
- prerequisite failed: clearance's `except graph.Blocked` catches KeyError instead (Blocked leaks, no Refused).
- submitted without a typed yes: submit writes `"node_key": None`.
- needs its estimate: run_forecast's `if euros is None:` becomes `if False:`.
- measured high: run_forecast's measured euros take `run["euros"]` (the median) for `run["high_euros"]`.
- rent point outside a run: require_cleared's `if found[-1] is None:` becomes `if False:`.
- judge timeout: judge_timeout ignores SCORE_JUDGE_TIMEOUT.
- priced on measured runs: run_price's likely euros take `run["high_euros"]`.
- per unit counted: per_unit drops `or stage in entry["also"]`.
- per unit × forecast: run_price's `if forecast is not None:` becomes `if False:`.
- timed by the card rule: unit_minutes caps cards at 1 for a machine stage.
- settle not timed below: unit_minutes' high job seconds read the likely ones.
- pixal finish: then_minutes' `if "unit_seconds" not in then:` becomes `if True:`.
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
- owner's yes keeps the start: guard.set_line writes the new baseline.
- stop command: guard.current reads the oldest line (`keys[0]`), not the newest.
- spend across months: guard.spent_since takes the baseline as every month's start.
- framework store with no line: stop_refusal returns None for any store.
- trial store: covering_store returns the trial's own store.
- clearance whose run ended: require_cleared's ended-run check becomes `if False:`.
- reservation open: still_open trusts a holder mark without guard.alive.
- override in flight: stop_refusal leaves the open overrides out of in flight.
- unreadable pre-flights: Watch.forecast_minutes lets ValueError through.
- waiting for a pool card: Watch.check adds no waited time.
- grant at most EUR 20: grant_benchmark drops `figure > GRANT_EUROS`.
- grant's google month: grant_benchmark never writes the Google month.
- grant holds its balance: settle_grant draws the hold's reserve instead of the real spend.
- pool on a grant: pool_clearance asks no grant_refusal under a grant (`None if grant_id`).
- pool beyond the rows: pool_reserve returns the whole holding.
- pool held longer: extend_pool replaces the reservation's euros instead of adding.
- heartbeat: score/__main__.py extend_pool extends whenever a plan exists.
- pool longer under a grant: extend_pool takes no further hold on the grant.
- gemini callers: GOOGLE_CALLERS loses `body-face-`.
- balance left: grant_refusal leaves out GRANT_BUFFER.
- reading allowance: reading_clearance drops the per-place euros limit.
- unquoted or too dear grant: grant_refusal drops `<= GRANT_EUROS`.
- restored grant: restore_grant skips settle_grant.

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

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score import checks, contracts, graph, review  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.adapters.compute import guard  # noqa: E402
from score.store import AGENT_MARKERS, Store  # noqa: E402

# the root conftest's sandbox test (its system temp folder, not this run's own temp folder inside it: own_temp)
SANDBOX = runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))
BOOKS = compute.ledger()
BOOKS.open_books_for_tests(tempfile.mkdtemp())  # this month's books known: paid paths open
MONTH = BOOKS.this_month()
START = {"month": MONTH, "bill": 100.0, "ledger": 90.0, "google": 0.0}
import capacity  # noqa: E402  (on the path compute.ledger() set)
import google_spend  # noqa: E402  (on the path compute.ledger() set)

google_spend.LEDGER = pathlib.Path(tempfile.mkdtemp()) / "google-ledger.jsonl"  # each test's Google month: empty  # each test's Google month: empty
BILL = {"euros": 0.0}
compute.cloud_bill = lambda: BILL["euros"]  # no cloud: the provider's bill is set by each test


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


def a_job(runner, euros=0.8):
    job_store = compute.job_contract.stores.FolderStore(tempfile.mkdtemp())
    spec = {"kind": "blender", "image": "img", "command": ["true"], "euros": euros}
    return job_store, lambda: compute.submit(runner, "render@hangar", job_store, "run1", "job1", spec)


def test_a_node_whose_prerequisite_failed_or_is_not_accepted_is_refused():
    month_spent(0)
    failed = a_runner("   ")
    assert "brief@hangar answered fail" in refused(a_job(failed)[1])
    rejected = a_runner("a hall")
    output = rejected.store.accepted("brief@hangar")
    review.reject(rejected.store, "brief@hangar", output, "owner", "the wrong hall")
    assert "is not accepted" in refused(a_job(rejected)[1])


def test_a_cleared_run_is_submitted_without_a_typed_yes():
    """Fault (the owner, 2026-10-11, 'why are you asking this?'): step 0 cleared a run only on his typed spend yes, so
    every paid run stalled asking him. The runner clears it now, and keeps the clearance."""
    month_spent(0)
    runner = a_runner("a hall")
    job_store, send = a_job(runner)
    written = send()
    key = runner.ticket("render@hangar")["key"]
    job = compute.job_contract.stores.read_json(job_store, written)
    assert job["node"] == "render@hangar" and job["node_key"] == key
    assert runner.store.spend_yes("render@hangar", key) is None
    assert [cleared["euros"] for cleared in runner.store.clearances("render@hangar", key)] == [0.8]


def test_a_paid_run_needs_its_estimate_and_no_month_total_refuses_it():
    """The owner, 2026-10-20: there is no month's ceiling; a month far past the old EUR 3,000 clears a run."""
    runner = a_runner("a hall")
    month_spent(10_000.0)
    assert "needs its estimate" in refused(a_job(runner, euros=None)[1])
    assert a_job(runner, euros=5.0)[1]()


def measured_runs(stage, euros, minutes=20.0):
    """The ledger with one batch each of four paid runs of `stage`, at these euros, this month."""
    BOOKS.entries = lambda: [{"ticket": f"{stage}@place{number} key{number}", "started": BOOKS.this_month(),
                              "kind": "blender", "batch": f"blender-{number}", "euros": cost, "wall_minutes": minutes,
                              "machines": []} for number, cost in enumerate(euros)]


def test_a_measured_stage_is_cleared_at_its_measured_high_not_its_hand_estimate():
    """Fault (2026-10-18): a film's estimate was a hand-written EUR 0.7 while its runs cost EUR 1.3 to 16; every
    clearance and every budget sum was built on the hand figure."""
    runner = a_runner("a hall")
    measured_runs("render", [1.0, 1.2, 1.4, 6.0])
    job_store, send = a_job(runner, euros=0.7)
    send()
    cleared = runner.store.clearances("render@hangar", runner.ticket("render@hangar")["key"])[-1]
    assert cleared["estimate"] == 0.7 and cleared["measured"] == 4 and cleared["minutes"] == 20.0
    assert 1.4 < cleared["euros"] < 6.0  # the high: the 90th percentile of its runs
    assert a_job(runner, euros=None)[1]()  # measured runs stand in for a missing estimate


def test_a_rent_point_refuses_outside_a_cleared_run_or_the_owners_override():
    """Fault (design of 2026-10-11, section 6): blender_cloud.py, detached.py, the runners and demo.py rented with no
    gate, so a run that skipped the runner could spend. Every rent point now asks require_cleared first."""
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


def test_the_judge_timeout_is_an_operational_setting_outside_every_key():
    """120 s by default, SCORE_JUDGE_TIMEOUT read when the call is made; the models adapter's keyed record holds no
    time limit (a limit decides whether an answer comes back, never what it says)."""
    from score.adapters import models
    saved = os.environ.pop(compute.JUDGE_TIMEOUT, None)
    try:
        assert compute.judge_timeout() == 120.0
        os.environ[compute.JUDGE_TIMEOUT] = "90"
        assert compute.judge_timeout() == 90.0
    finally:
        os.environ.pop(compute.JUDGE_TIMEOUT, None)
        if saved is not None:
            os.environ[compute.JUDGE_TIMEOUT] = saved
    assert not any("timeout" in setting for setting in models.api_record("gemini-judge"))



def run_line(number, euros, minutes):
    """One paid run of the render stage on one card with two jobs."""
    machine = {"cards": 1, "minutes": minutes, "euros": euros, "unit_seconds": [60, 60], "setup_minutes": 1.0}
    return {"ticket": f"render@place{number} {number}", "kind": "blender", "batch": f"blender-{number}",
            "machines": [machine], "euros": euros, "wall_minutes": minutes}


def test_a_paid_node_is_priced_on_its_stages_measured_runs_else_its_estimate():
    """The cockpit's price is the runner's: likely the median run, high what the clearance reserves, cards from
    the run's sizing; an unmeasured stage has no price, its estimate kept apart as the guess, with no minutes."""
    saved = BOOKS.entries
    try:
        BOOKS.entries = lambda: [run_line(number, euros, minutes)
                                 for number, (euros, minutes) in enumerate([(1.0, 10), (2.0, 20), (3.0, 30)])]
        price = compute.run_price("render@hangar", 9.0)
        assert price["likely_euros"] == 2.0 and price["likely_minutes"] == 20 and price["runs"] == 3
        assert price["high_euros"] == compute.run_forecast("render@hangar", 9.0)["euros"] > 2.0
        assert price["cards"] == 2  # two 1-minute jobs a run on a 1-minute set-up: a card each
        BOOKS.entries = lambda: []
        assert compute.run_price("render@hangar", 9.0) == {
            "likely_euros": None, "high_euros": None, "guess_euros": 9.0, "likely_minutes": None, "high_minutes": None,
            "cards": None, "runs": 0, "basis": "not measured yet", "minutes_why": "not measured yet"}
        assert compute.run_forecast("render@hangar", 9.0)["euros"] == 9.0  # the clearance still reserves the guess
    finally:
        BOOKS.entries = saved


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


def test_a_stage_measured_per_unit_is_priced_at_its_units_and_a_node_with_none_to_count_is_a_guess():
    """A stage with measured per-unit numbers (PER_UNIT) is priced at them times the units its node's accepted output
    made, likely and high both, and cleared at its high; a stage that shares its unit (`also`) is priced the same;
    a node with no accepted output to count is not measured yet, its estimate only a guess."""
    saved, kept = BOOKS.entries, compute.PER_UNIT
    folder = pathlib.Path(tempfile.mkdtemp())
    compute.PER_UNIT = folder / "per-unit.json"
    compute.PER_UNIT.write_text(json.dumps({"stages": {"render": {
        "stage": "render", "unit": "model", "count": {"json_keys": "takes.json"}, "also": ["crops-render"],
        "likely_euros": 0.2, "high_euros": 0.5, "runs": 40, "sources": {}}}}))
    outputs = Outputs({"render@hangar": {"takes.json": {"a": 1, "b": 2, "c": 3}, "contract.json": {}},
                       "crops-render@hangar": {"takes.json": {"a": 1}}})
    try:
        BOOKS.entries = lambda: []
        price = compute.run_price("render@hangar", 9.0, outputs)
        share = compute.BILL_SHARE  # a card stage's ledger euros on the provider's bill (no Google calls)
        assert (price["likely_euros"], price["high_euros"], price["units"], price["runs"], price["basis"]) == (
            round(0.6 * share, 4), round(1.5 * share, 4), 3, 40, "per unit × counted"), price
        assert compute.run_forecast("render@hangar", 9.0, outputs) == {"euros": round(1.5 * share, 4), "minutes": None,
                                                                       "high_minutes": None, "measured": 40}
        assert compute.run_price("crops-render@hangar", 2.0, outputs)["likely_euros"] == round(0.2 * share, 4)
        unseen = compute.run_price("render@lab", 9.0, outputs)
        assert unseen["likely_euros"] is None and unseen["guess_euros"] == 9.0 and unseen["runs"] == 0
        assert compute.run_price("bake@hangar", 3.0, outputs)["basis"] == "not measured yet"
    finally:
        BOOKS.entries, compute.PER_UNIT = saved, kept


def test_a_node_not_made_yet_is_priced_per_unit_times_its_forecast_units_else_it_is_a_guess_that_says_where():
    """Units forecast before a make (gaps' price) give per unit times them, a basis of their own, before the units
    an older accepted output counted (the gap's make makes what it adds, not what the last make made); a stage with no forecast rule, an `also` stage, or no units is a guess with the
    file and line its row names its estimate on."""
    saved, kept = BOOKS.entries, compute.PER_UNIT
    folder = pathlib.Path(tempfile.mkdtemp())
    compute.PER_UNIT = folder / "per-unit.json"
    rule = {"rule": "models", "source": "the place's takes"}
    compute.PER_UNIT.write_text(json.dumps({"stages": {
        "render": {"stage": "render", "unit": "model", "count": {"json_keys": "takes.json"}, "also": ["crops-render"],
                   "likely_euros": 0.2, "high_euros": 0.5, "runs": 40, "sources": {}, "forecast": rule},
        "bake": {"stage": "bake", "unit": "job", "count": {"one": True}, "also": [], "likely_euros": 1.0,
                 "high_euros": 2.0, "runs": 3, "sources": {}, "forecast": None, "forecast_why": "no batch"}}}))
    outputs = Outputs({"render@hangar": {"takes.json": {"a": 1}}})
    try:
        BOOKS.entries = lambda: []
        share = compute.BILL_SHARE  # a card stage's ledger euros on the provider's bill (no Google calls)
        price = compute.run_price("render@lab", 9.0, outputs, units=4, guess_from="score/stages/x.py:12")
        assert (price["likely_euros"], price["high_euros"], price["units"], price["basis"], price["unit_source"]) == (
            round(0.8 * share, 4), round(2.0 * share, 4), 4, "per unit × forecast", "the place's takes"), price
        again = compute.run_price("render@hangar", 9.0, outputs, units=4)  # an accept of 1 take, 4 forecast
        assert (again["units"], again["basis"], again["likely_euros"]) == (
            4, "per unit × forecast", round(0.8 * share, 4)), again
        assert compute.run_price("render@hangar", 9.0, outputs)["basis"] == "per unit × counted"  # no forecast given
        for node, units in (("bake@lab", 4), ("crops-render@lab", 4), ("render@lab", 0), ("render@lab", None)):
            found = compute.run_price(node, 3.0, outputs, units=units, guess_from="score/stages/x.py:12")
            assert found["likely_euros"] is None and found["guess_euros"] == 3.0, (node, units, found)
            assert found["guess_from"] == "score/stages/x.py:12" and found["basis"] == "not measured yet"
        assert "guess_from" not in compute.run_price("bake@lab", 3.0)
        # the clearance reserves what the plan priced: the forecast's high, never the guess, where it is measured
        assert compute.run_forecast("render@lab", 9.0, outputs, units=4)["euros"] == price["high_euros"]
        assert compute.run_forecast("render@lab", 9.0, outputs)["euros"] == 9.0  # nothing counted: the estimate
    finally:
        BOOKS.entries, compute.PER_UNIT = saved, kept


def test_a_per_unit_price_is_timed_on_its_stages_measured_time_by_the_runners_card_rule():
    """Minutes come from the stage's measured time (PER_UNIT `time`) on the runner's own card rule, likely on the
    median unit and high on the HIGH one, cards capped at the run's cap; a stage of calls holds no cards; a stage with
    no measured time keeps its price and says why it has no minutes."""
    saved, kept = BOOKS.entries, compute.PER_UNIT
    folder = pathlib.Path(tempfile.mkdtemp())
    compute.PER_UNIT = folder / "per-unit.json"
    rule = {"rule": "models", "source": "the place's takes"}
    timed = {"unit_seconds": {"likely": 600.0, "high": 1200.0}, "setup_minutes": {"likely": 10.0, "high": 14.0},
             "slots": 1, "holds": "machines"}
    stage = {"unit": "model", "count": None, "also": [], "likely_euros": 0.2, "high_euros": 0.5, "runs": 40,
             "sources": {}, "forecast": rule}
    compute.PER_UNIT.write_text(json.dumps({"stages": {
        "render": {**stage, "stage": "render", "time": timed},
        "ask": {**stage, "stage": "ask", "time": {**timed, "setup_minutes": {"likely": 0.0, "high": 0.0}, "slots": 4,
                                                   "holds": "calls"}},
        "bake": {**stage, "stage": "bake", "time": {"why": "no line timed it"}},
        "drop": {**stage, "stage": "drop", "time": {**timed, "setup_minutes": {"why": "no set-up timed"}}}}}))
    try:
        BOOKS.entries = lambda: []
        price = compute.run_price("render@lab", 9.0, units=4)
        # a 10-minute job on a 10-minute set-up: a card each, set-up then one job; high on the high set-up
        assert (price["cards"], price["likely_minutes"], price["high_minutes"]) == (4, 20.0, 34.0), price
        many = compute.run_price("render@lab", 9.0, units=500)
        cap = capacity.run_cap()  # the run's cap: the largest class quota (#20)
        assert many["cards"] == cap, many
        assert many["likely_minutes"] == 10 + math.ceil(500 / cap) * 10, many
        asked = compute.run_price("ask@lab", 9.0, units=8)
        assert (asked["cards"], asked["likely_minutes"], asked["high_minutes"]) == (None, 20.0, 40.0), asked
        unknown = compute.run_price("bake@lab", 9.0, units=4)
        assert unknown["likely_euros"] == round(0.8 * compute.BILL_SHARE, 4) and unknown["likely_minutes"] is None
        assert unknown["minutes_why"] == "no line timed it"
        untimed = compute.run_price("drop@lab", 9.0, units=4)
        assert untimed["likely_minutes"] is None and untimed["minutes_why"] == "no set-up timed", untimed
    finally:
        BOOKS.entries, compute.PER_UNIT = saved, kept


def test_a_measured_settle_run_is_not_timed_below_the_runs_it_is_read_from():
    """The repository's per-unit file on the paper ledger's settle lines: one drop run's likely minutes within a
    minute of the runs' median wall minutes, and its high at or above their HIGH quantile (the set-up in the machine
    counted, not only the start wait)."""
    sys.path.insert(0, str(compute.REPO / "tools/costs"))
    import per_unit
    paper = compute.REPO / "paper/evidence/cloud/ledger.jsonl"
    walls = [line["wall_minutes"] for line, _ in per_unit.ledger_lines([paper])
             if per_unit.matches(line, per_unit.SPECS["settle"]["cloud"])]
    timed = compute.unit_minutes("settle", 1)
    assert abs(timed["likely_minutes"] - statistics.median(walls)) <= 1.0, (timed, sorted(walls))
    assert timed["high_minutes"] >= per_unit.quantile(walls, per_unit.HIGH), (timed, sorted(walls))


def test_pixal_s_time_holds_its_finish_of_every_take():
    """Buy of 2026-10-24: pixal finished its takes on machines of their own after its batch, and the forecast held
    the batch alone. The per-unit file's pixal time holds its finish step (`then`), read from the blender lines its
    node ran, and unit_minutes adds that step on its own machines: at least a set-up and a finish job more."""
    sys.path.insert(0, str(compute.REPO / "tools/costs"))
    import per_unit
    then = compute.per_unit("pixal")["time"]["then"]
    assert then["kind"] == per_unit.SPECS["pixal"]["then"]["kind"] and "unit_seconds" in then, then
    with_finish = compute.unit_minutes("pixal", 20)
    likely, high = compute.then_minutes(then, 20)
    assert likely >= then["setup_minutes"]["likely"] + then["unit_seconds"]["likely"] / 60, (likely, then)
    assert high >= likely and compute.then_minutes({"why": "none"}, 20) == (0.0, 0.0)
    line = {"kind": "blender", "ticket": "pixal@yard k", "jobs": ["a", "b"], "machines": [
        {"started": True, "start_wait_minutes": 0.5, "setup_minutes": 1.0, "unit_seconds": [40.0, 50.0]}]}
    found = per_unit.then_times([(line, "test line 1"), ({**line, "ticket": "settle@yard k"}, "test line 2")],
                                "pixal", "blender")
    assert found["lines"] == 1 and found["unit_seconds"]["likely"] == 45.0, found
    assert with_finish["likely_minutes"] is not None, with_finish


def test_a_stage_row_says_where_its_estimate_is_written():
    """A paid row records the line that builds it (through a helper that hands its euros on), so a guess names it;
    a row made from another by dataclasses.replace keeps the first's line unless its estimate changed."""
    def row(name, **more):
        return graph.Stage(name, "place", make_nothing, TEXT, **more)

    built = row("render", paid=True, euros=2.0)
    line = sys._getframe().f_lineno - 1
    assert built.euros_from == f"score/adapters/compute/test_paid_work_starts_only_inside_its_clearance.py:{line}", built.euros_from
    assert dataclasses.replace(built, name="render-again").euros_from == built.euros_from
    moved = dataclasses.replace(built, euros=3.0)
    assert moved.euros_from == f"score/adapters/compute/test_paid_work_starts_only_inside_its_clearance.py:{sys._getframe().f_lineno - 1}"
    assert RENDER.euros_from is None  # no estimate, nothing to say


def test_each_count_rule_counts_the_units_an_output_made():
    """The count rules read the output as the stages write it: files by pattern, one file a take, a JSON's keys or
    field, every map attempt of a take."""
    take_map = {"front": {"attempts": [{}, {}]}, "views": {"t15-090": {"attempts": [{}]}, "t15-180": {"attempts": []}}}
    names = {"finishes": [{"by": "the list"}]}
    outputs = Outputs({"out": {"contract.json": {}, "a-s1.json": names, "b-s1.json": names, "a-s1/map.json": take_map,
                               "passes/p-0.views.json": {}, "passes/p-1.views.json": {}, "passes/p-0/look.png": None,
                               "closeups.json": {"pro_pictures": 4}}})
    rules = [({"one": True}, 1), ({"files": "passes/*.views.json"}, 2), ({"take_files": ".json"}, 3),
             ({"json_field": ["closeups.json", "pro_pictures"]}, 4), ({"map_attempts": "map.json"}, 3),
             ({"json_keys": "missing.json"}, None)]
    for count, units in rules:
        assert compute.counted_units(outputs, "out", count) == units, (count, units)


def test_a_count_of_zero_is_free_only_where_its_rule_counts_zero():
    """A place whose sound takes all stand made counts 0 takes: EUR 0 and no time (COUNTED_ZERO); any other rule's
    0 is nothing counted, so no price (unknown, never free)."""
    sound = compute.forecast_price("sound@airlock", 0)
    assert (sound["likely_euros"], sound["high_euros"], sound["units"]) == (0.0, 0.0, 0), sound
    assert compute.unit_minutes("sound", 0) == {"likely_minutes": 0.0, "high_minutes": 0.0, "cards": 0}
    assert compute.forecast_price("pixal@airlock", 0) is None and compute.forecast_price("sound@airlock", None) is None


def test_the_owners_google_month_is_refused_in_an_agents_process():
    """Only the owner knows what Google billed before its ledger began again (#13): an agent's figure opens nothing."""
    kept = BOOKS.BOOKS
    BOOKS.BOOKS = pathlib.Path(tempfile.mkdtemp()) / "books.json"
    os.environ["CLAUDECODE"] = os.environ.get("CLAUDECODE", "1")
    try:
        compute.owners_google_month(400.0)
    except compute.Refused as refusal:
        assert "owner" in str(refusal)
    else:
        raise AssertionError("an agent wrote the owner's Google month")
    finally:
        written, BOOKS.BOOKS = BOOKS.BOOKS.exists(), kept
    assert not written


def test_the_cockpits_google_line_is_the_bill_else_the_owners_figure_else_no_figure():
    """The cockpit's Google month (`score spend`'s line): the billing export's bill once read back, else the owner's
    books figure plus the ledger since, else no figure at all, never the call ledger alone (it showed EUR 0.00 for a
    month Google billed about EUR 1,030)."""
    from score import __main__ as command
    kept = BOOKS.BOOKS
    BOOKS.BOOKS = pathlib.Path(tempfile.mkdtemp()) / "books.json"
    month = BOOKS.this_month()
    try:
        BOOKS.write_books({"month": month, "state": "lost", "google_unread": "the export holds no rows yet"})
        unread = command.google_line()
        assert unread["euros"] is None and unread["partial"] and unread["origin"] == "the export holds no rows yet"
        BOOKS.write_books({"month": month, "state": "known", "google_before": 1030.0, "google_at": "t"})
        assert command.google_line()["euros"] == 1030.0 + google_spend.month_euros(month)
        BOOKS.write_books({"month": month, "state": "known", "google_bill": 1031.5, "google_bill_at": "t",
                           "google_before": 1030.0})
        billed = command.google_line()
        assert billed["euros"] == 1031.5 and not billed["partial"] and "billing export" in billed["origin"]
        days = command.ledger_days(month)
        assert days[0]["day"] == f"{month}-01" and set(days[-1]) == {"day", "cloud", "models"}
    finally:
        BOOKS.BOOKS = kept




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


def test_a_job_that_would_pass_the_stop_is_refused_before_it_starts():
    """Fault (environment 1, 2026-10-12 to 18): the stop was a figure in a watcher script that killed runs halfway, and it
    was raised 13 times. Now the clearance refuses a job whose forecast cannot finish under it, and says so once."""
    runner = a_runner("a hall")
    stop_at(runner, 20.0)
    ledger({"euros": 90.0}, {"euros": 15.0})  # the ledger grew EUR 15 since the line
    BILL["euros"] = 110.0  # the bill only 10: it lags, the ledger counts
    job_store, dear = a_job(runner, euros=6.0)  # 15 + 6 > 20
    refusal = refused(dear)
    assert "EUR 15.00 spent" in refusal and "pass the EUR 20.00 stop" in refusal and job_store.keys("") == []
    assert refused(dear) and len(outbox(runner)) == 1 and "Free work goes on" in outbox(runner)[0]
    assert a_job(runner, euros=4.0)[1]()  # 15 + 4 fits under 20
    runner.run_node(BRIEF, "hangar")  # free work goes on


def test_a_batch_over_its_own_stop_is_refused_one_within_it_clears_whatever_the_month_cost():
    """The owner, 2026-10-20: a batch's own stop is the only spend cap; no month's ceiling. A month at EUR 10,000
    (past the old EUR 3,000 ceiling) clears a job within the stop and refuses one over it."""
    runner = a_runner("a hall")
    month = {"month": MONTH, "bill": 10_000.0, "ledger": 10_000.0, "google": 0.0}
    stop_at(runner, 5.0, baseline=month)
    ledger({"euros": 10_000.0})
    BILL["euros"] = 10_000.0
    assert "pass the EUR 5.00 stop" in refused(a_job(runner, euros=6.0)[1])
    assert a_job(runner, euros=4.0)[1]()
    BILL["euros"] = 0.0


def clear_in_a_process(runner, ready, sending):
    ready.wait()
    try:
        compute.clearance(runner, "render@hangar", 1.0)
        sending.send("cleared")
    except compute.Refused:
        sending.send("refused")


def test_lines_clearing_at_once_never_both_spend_the_stops_last_euros():
    """Fault (the coordinator, 2026-10-11): lines run side by side and the ledger records a batch only once it is
    done, so two lines cleared at once could both spend the last euros; the clearing lock and reservations hold."""
    runner = a_runner("a hall")
    stop_at(runner, 1.5)
    ledger({"euros": 90.0})
    BILL["euros"] = 0.0
    fork = multiprocessing.get_context("fork")
    ready, pipes = fork.Event(), [fork.Pipe(duplex=False) for _ in range(6)]
    processes = [fork.Process(target=clear_in_a_process, args=(runner, ready, sending)) for _, sending in pipes]
    for process in processes:
        process.start()
    for _, sending in pipes:
        sending.close()  # a process that dies fails the test with EOFError instead of hanging it
    ready.set()
    answers = sorted(receiving.recv() for receiving, _ in pipes)
    for process in processes:
        process.join()
    assert answers == ["cleared"] + ["refused"] * 5, answers


def test_everything_in_flight_counts_less_what_it_already_ledgered():
    runner = a_runner("a hall")
    stop_at(runner, 10.0)
    ledger({"euros": 90.0})
    BILL["euros"] = 0.0
    ticket = compute.clearance(runner, "render@hangar", 6.0)  # in flight: EUR 6 of the 10 left
    assert "pass" in refused(lambda: compute.clearance(runner, "render@hangar", 5.0))
    ledger({"euros": 90.0}, {"euros": 4.0, "ticket": f"render@hangar {ticket['key']}",  # 4 of its 6 ledgered
                             "started": graph.now()})
    assert compute.clearance(runner, "render@hangar", 3.9)  # 4 spent + 2 in flight + 3.9 fits
    compute.release(ticket)


def test_a_started_job_runs_on_as_the_bill_nears_the_stop_and_stops_only_as_a_runaway():
    """No paid job is killed halfway: past the stop it finishes; only past twice its forecast minutes it is ended."""
    folder, stopped, clock = pathlib.Path(tempfile.mkdtemp()), [], [0.0]
    watch = guard.Watch("render@hangar k", 30.0, folder, stop=lambda: stopped.append(1), clock=lambda: clock[0])
    BILL["euros"] = 10_000.0  # far past any stop: nothing in the watch reads it
    clock[0] = 59 * 60
    assert not watch.check() and stopped == []
    clock[0] = 61 * 60
    assert watch.check() and watch.check() and stopped == [1]
    assert "runaway render@hangar k" in (folder / guard.OUTBOX).read_text()
    unknown = guard.Watch("render@hangar k", None, folder, stop=lambda: stopped.append(2), clock=lambda: 1e9)
    assert not unknown.check() and stopped == [1]
    sized = guard.Watch("render@hangar j", 300.0, folder, batches=lambda: [{"high_minutes": 20.0}] * 2,
                        stop=lambda: stopped.append(3), clock=lambda: clock[0])
    clock[0] = 81 * 60 + sized.started  # its batches' pre-flights say 40 min high: past 80 it is a runaway
    assert sized.check() and stopped == [1, 3]
    BILL["euros"] = 0.0


def test_a_runaway_ends_the_makes_own_children_not_the_run():
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        assert child.pid in guard.children(os.getpid())
        guard.stop_children()
        assert child.wait(timeout=10) != 0
    finally:
        child.kill()


def test_the_owners_yes_writes_the_new_line_and_keeps_the_worlds_start():
    """Fault (environment 1): a yes in chat and the guard line an agent typed later disagreed. His yes writes the line."""
    runner = a_runner("a hall")
    first = stop_at(runner, 250.0)
    raised = stop_at(runner, 680.0, baseline={"month": MONTH, "bill": 999.0, "ledger": 999.0, "google": 0.0},
                     at="2026-10-18T12:00:00+00:00")
    assert raised["baseline"] == first["baseline"] and raised["before"] == 250.0
    assert guard.current(runner.store, runner.world.name)["euros"] == 680.0
    try:
        as_agent(lambda: guard.set_line(runner.store, runner.world.name, 900.0, "more", "agent",
                                        "2026-10-18T13:00:00+00:00", START))
        raise AssertionError("an agent's process wrote a stop line")
    except PermissionError:
        pass


def test_the_owners_stop_command_writes_the_line_the_next_clearance_reads():
    """C22: his money yes and the guard line are one step: `score.review stop` writes the line, and the very next
    clearance is held to it. Without a terminal, or in an agent's process, it writes nothing."""
    from score.review import __main__ as review_command
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


def test_spend_counts_from_the_worlds_start_across_months():
    later = {"bill": 30.0, "ledger": 25.0, "google": 2.0}
    months = {"2026-10": {"bill": None, "ledger": 300.0, "google": 5.0}, "2026-11": later}
    start = {"month": "2026-10", "bill": 120.0, "ledger": 100.0, "google": 1.0}
    assert guard.spent_since(start, months) == (200.0 + 4.0) + (30.0 + 2.0)


def test_the_framework_store_refuses_a_world_with_no_line():
    """In the framework's store an environment must carry the owner's money figure before any paid job starts."""
    assert SANDBOX["sandbox_refusal"](os.environ) is None, "run in a sandbox home"
    store = Store.default()
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "hangar.txt").write_text("a hall")
    runner = graph.Runner([BRIEF, RENDER], graph.Environment("toy-framework", 1, {"data": data}),
                          store)
    runner.run_node(BRIEF, "hangar")
    ledger({"euros": 0.0})
    assert "has no stop line" in refused(lambda: compute.clearance(runner, "render@hangar", 1.0))


def test_a_trials_own_store_in_the_home_is_held_to_the_worlds_stop_and_counted_in_flight():
    """Fault (2026-10-18 review): compare.py's trial store had no stop line of its own, so its paid rows (close-ups,
    pixal, likeness) skipped the stop, and their reservations sat in the trial's store where no clearance counted them."""
    trial = Store.in_folder(compute.PROPS_HOME / "trial-test/store")  # as compare.py's, a store inside the home
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "hangar.txt").write_text("a hall")
    runner = graph.Runner([BRIEF, RENDER], graph.Environment("toy-trial", 1, {"data": data}),
                          trial)
    runner.run_node(BRIEF, "hangar")
    ledger({"euros": 90.0})
    BILL["euros"] = 0.0
    (Store.default().cache.parent / "reservations.json").unlink(missing_ok=True)  # earlier tests' runs, in the sandbox
    assert "has no stop line" in refused(lambda: compute.clearance(runner, "render@hangar", 1.0))
    as_owner(lambda: guard.set_line(Store.default(), "toy-trial", 10.0, "the trial", "owner",
                                    "2026-10-18T09:00:00+00:00", START))
    ticket = compute.clearance(runner, "render@hangar", 6.0)
    assert pathlib.Path(ticket["reservations"]).parent == Store.default().cache.parent
    assert "pass the EUR 10.00 stop" in refused(lambda: compute.clearance(runner, "render@hangar", 5.0))
    with compute.spending(ticket):
        assert compute.require_cleared("a batch")["euros"] == 6.0  # the clearance is read from the trial's store
    assert compute.clearance(runner, "render@hangar", 5.0)  # released: in flight no more


def test_a_rent_point_refuses_a_clearance_whose_run_has_ended():
    """Fault (2026-10-18 review): any earlier clearance passed a rent point, so a ticket reused after its run ended
    started paid work that no stop check and no in-flight sum saw."""
    runner = a_runner("a hall")
    ledger({"euros": 0.0})
    ticket = compute.clearance(runner, "render@hangar", 1.0)
    with compute.spending(ticket):
        assert compute.require_cleared("a batch", runner.store)["euros"] == 1.0
    os.environ[compute.TICKET] = f"render@hangar {ticket['key']}"
    try:
        assert "has ended" in refused(lambda: compute.require_cleared("a batch", runner.store))
    finally:
        os.environ.pop(compute.TICKET)


def test_a_reservation_stays_open_while_its_run_lives_or_until_its_runaway_limit():
    """Fault (2026-10-18 review): a reservation was dropped after 4 h whether or not its run had ended."""
    hours_ago = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=5)).isoformat()
    now = datetime.datetime.now(datetime.timezone.utc)
    assert compute.still_open(hours_ago, {"holder": guard.process_mark(os.getpid())}, now)
    assert not compute.still_open(hours_ago, {"holder": f"{os.getpid()} 0"}, now)  # a pid since given to another
    assert not compute.still_open(hours_ago, {"high_minutes": 60.0}, now)
    assert compute.still_open(hours_ago, {"high_minutes": 200.0}, now)  # twice 200 min is past 5 h


def test_an_override_still_going_counts_in_flight():
    runner = a_runner("a hall")
    stop_at(runner, 10.0)
    ledger({"euros": 90.0})
    BILL["euros"] = 0.0
    runner.store.write_spend_yes(compute.OVERRIDE, "repaint", {"node": compute.OVERRIDE, "key": "repaint",
                                                               "euros": 7.0, "by": "owner", "at": graph.now()})
    assert "pass the EUR 10.00 stop" in refused(lambda: compute.clearance(runner, "render@hangar", 4.0))
    assert compute.clearance(runner, "render@hangar", 2.0)


def test_a_watch_whose_preflights_cannot_be_read_falls_back_to_its_stages_forecast():
    """A half written pre-flight line must not end the watch: the run would have no runaway stop left."""
    def unreadable():
        raise ValueError("a line half written")
    stopped, clock = [], [0.0]
    watch = guard.Watch("render@hangar u", 30.0, pathlib.Path(tempfile.mkdtemp()), batches=unreadable,
                        stop=lambda: stopped.append(1), clock=lambda: clock[0])
    clock[0] = 61 * 60
    assert watch.check() and stopped == [1]


def test_a_run_waiting_for_a_warm_pool_card_is_no_runaway():
    """Benchmark of 2026-10-23: a rough model (12 measured minutes) waited on the pool's first card in a stock
    trough; the wait is not the run's work, and its minutes count again once a card is taken."""
    stopped, clock, waits = [], [0.0], [True]
    watch = guard.Watch("rough-model@hub u", 12.0, pathlib.Path(tempfile.mkdtemp()), stop=lambda: stopped.append(1),
                        clock=lambda: clock[0], waiting=lambda: waits[0])
    for minute in range(1, 91):  # an hour and a half waiting
        clock[0] = minute * 60
        assert not watch.check()
    waits[0] = False
    clock[0] = 90 * 60 + 20 * 60
    assert not watch.check()
    clock[0] = 90 * 60 + 25 * 60
    assert watch.check() and stopped == [1]


QUESTION = "Approve one benchmark batch, P1, of at most EUR 10?"


def refused_grant(**given):
    """Why grant_benchmark refused these arguments."""
    arguments = {"answer": "Yes", "question": QUESTION, "euros": 10.0, "store": Store.in_folder(tempfile.mkdtemp()),
                 **given}
    return refused(lambda: compute.grant_benchmark(**arguments))


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


def test_a_grant_is_a_quoted_benchmark_of_at_most_20_euros():
    """The owner's standing rule of 2026-10-20: benchmarks only, at most EUR 20, his answer and the question quoted."""
    assert "at most EUR 20" in refused_grant(euros=20.01)
    assert "at most EUR 20" in refused_grant(euros=0) and "at most EUR 20" in refused_grant(euros=float("nan"))
    assert "benchmark only" in refused_grant(purpose="a film")
    assert "quotes" in refused_grant(answer="  ") and "quotes" in refused_grant(question="")
    store = Store.in_folder(tempfile.mkdtemp())
    grant = compute.grant_benchmark("Yes", QUESTION, 20, store=store)
    assert store.read(f"grants/benchmark/{grant['id']}.json") == grant
    assert grant["answer"] == "Yes" and grant["question"] == QUESTION and grant["euros"] == 20.0
    assert "expires" not in grant and grant["google_month"] is None


def test_a_grant_may_carry_the_owners_google_month():
    kept = BOOKS.BOOKS
    BOOKS.BOOKS = pathlib.Path(tempfile.mkdtemp()) / "books.json"
    try:
        assert "finite figure" in refused_grant(google_month=-1)
        assert not BOOKS.BOOKS.exists()
        grant = compute.grant_benchmark("Yes, and Google is at 412", QUESTION, 5, google_month=412.0,
                                        store=Store.in_folder(tempfile.mkdtemp()))
        books = BOOKS.this_months_books()
        assert books["state"] == "known" and books["google_before"] == 412.0 and grant["id"] in books["google_by"]
    finally:
        BOOKS.BOOKS = kept


def billed(ticket, euros):
    """Add a cloud ledger line of `euros` under a cleared run's ticket, started as it was cleared, to the fake ledger;
    a second later, so the next clearance of the same node starts after it (the ledger counts in seconds)."""
    lines = BOOKS.entries()
    BOOKS.entries = lambda: [*lines, {"started": ticket["clearance"]["at"][:19] + "Z", "euros": euros,
                                      "ticket": f"{ticket['node']} {ticket['key']}"}]
    time.sleep(1.05)


def test_a_grant_holds_its_balance_across_runs_and_each_run_draws_its_real_spend():
    """The owner, 2026-10-22: a grant is not used up by a run that fails after spending cents; it holds its euros until
    they are spent. Each run holds its high plus 10% while it goes and draws its real spend when it ends, failed too."""
    runner = a_runner("a hall")
    ledger({"euros": 90.0})
    BILL["euros"] = 100.0  # nothing spent since the line
    stop_at(runner, 1.0)
    grant = compute.grant_benchmark("Yes", QUESTION, 10.0, store=runner.store)["id"]
    clear = lambda euros: lambda: compute.clearance(runner, "render@hangar", euros)  # noqa: E731
    assert "pass the EUR 1.00 stop" in refused(clear(6.0))  # not tagged: the stop line as ever
    first = as_benchmark(grant, "run-a", clear(6.0))  # holds 6.60 of 10
    assert first["clearance"]["grant"] == grant
    assert "EUR 3.40 left" in refused(lambda: as_benchmark(grant, "run-a", clear(4.0)))
    billed(first, 0.25)
    compute.release(first)  # the first run fails after spending 0.25: it draws that, never its hold
    draws = runner.store.objects.keys(f"grants/draws/{grant}/")
    assert len(draws) == 1 and runner.store.read(draws[0])["euros"] == 0.25
    assert runner.store.read(draws[0])["balance"] == 9.75
    second = as_benchmark(grant, "run-b", clear(8.0))  # another run under the same grant: 8.80 fits in 9.75
    assert "EUR 0.95 left" in refused(lambda: as_benchmark(grant, "run-b", clear(1.0)))
    billed(second, 1.5)
    compute.release(second)
    assert compute.grant_balance(runner.store, grant, {}) == 8.25
    assert "one score run" in refused(lambda: as_benchmark(grant, None, clear(0.5)))
    assert "no benchmark grant" in refused(lambda: as_benchmark("20991231T000000", "run-c", clear(0.5)))


def test_a_runs_warm_pool_holds_its_cost_on_the_grant_and_draws_what_its_cards_billed():
    """The owner, 2026-10-23: the pool's idle time is the run's own cost, counted in its grant's balance."""
    runner = a_runner("a hall")
    ledger({"euros": 90.0})
    BILL["euros"] = 100.0
    stop_at(runner, 1.0)
    alone = [({"gpu-24gb": 1}, 6.0)]
    assert "pass the EUR 1.00 stop" in refused(lambda: compute.pool_clearance(runner, "run-p", alone, 4))
    grant = compute.grant_benchmark("Yes", QUESTION, 10.0, store=runner.store)["id"]
    choices = [({"gpu-24gb": 2, "cpu-64c": 3}, 23.0), ({"gpu-24gb": 2}, 6.0), ({"gpu-24gb": 1}, 3.0)]
    opened = as_benchmark(grant, "run-p", lambda: compute.pool_clearance(runner, "run-p", choices, 4, beside=2.0))
    assert opened["sizes"] == {"gpu-24gb": 2}  # 23 + 2 passes the EUR 10 grant; 6 + 2 fits, never failing the run
    assert opened["node"] == compute.POOL and opened["key"] == "run-p" and opened["clearance"]["grant"] == grant
    assert "EUR 3.40 left" in refused(lambda: as_benchmark(grant, "run-p", clear_render(runner, 4.0)))
    os.environ[compute.TICKET], os.environ[compute.STORE] = f"{compute.POOL} run-p", str(runner.store.cache.parent)
    try:
        assert compute.require_cleared("a pool card", runner.store)["node"] == compute.POOL
    finally:
        os.environ.pop(compute.TICKET), os.environ.pop(compute.STORE)
    billed(opened, 1.25)
    compute.release(opened)
    assert compute.grant_balance(runner.store, grant, {}) == 8.75


def test_a_warm_pool_reserves_only_its_holding_beyond_the_rows_whose_machine_time_it_bills():
    """Fault, 2026-10-24 Buy: rows high EUR 360.40 under a EUR 396.46 stop; the pool's whole 4 h holding was reserved
    beside the rows' high, which already holds the machine time those pool machines run, so 5 of 10 machines opened.
    Now the pool reserves its holding less the rows it bills (never below nothing), opens whole when that fits, still
    shrinks when it does not, and what it reserves with the rows covers the most it and they can bill."""
    runner = a_runner("a hall")
    ledger({"euros": 90.0})
    BILL["euros"] = 100.0
    stop_at(runner, 396.46)
    full, half, one = {"gpu-24gb": 10, "cpu-64c": 3}, {"gpu-24gb": 3, "cpu-64c": 2}, {"gpu-24gb": 1}
    choices = [(full, 72.0), (half, 36.0), (one, 3.6)]
    opened = compute.pool_clearance(runner, "run-buy", choices, 4, beside=360.40, covered=300.0)
    assert opened["sizes"] == full and opened["clearance"]["euros"] == 0.0 and opened["clearance"]["holding"] == 72.0
    # what is reserved (pool and rows) covers the pool's whole holding and the rows it does not bill
    assert opened["clearance"]["euros"] + 360.40 >= 72.0 + (360.40 - 300.0)
    assert "pass the EUR 396.46 stop" in refused(lambda: clear_render(runner, 400.0)())
    compute.release(opened)
    tight = compute.pool_clearance(runner, "run-tight", choices, 4, beside=360.40, covered=20.0)
    assert tight["sizes"] == half and tight["clearance"]["euros"] == 16.0  # 52 + 360.40 passes; 16 + 360.40 fits
    compute.release(tight)
    assert compute.pool_reserve(72.0, 300.0) == 0.0 and compute.pool_reserve(72.0, 20.0) == 52.0


def test_a_warm_pool_held_longer_clears_the_more_in_its_one_reservation():
    """Batch 1 of 2026-10-24: the pool closed at its cleared 4 h with ~550 rows queued, and every finish after failed.
    Its run's heartbeat holds it longer (extend_pool): each further holding checked against the stop line with every
    reservation, added to the pool's own one, and refused once the run's money has no room."""
    runner = a_runner("a hall")
    ledger({"euros": 90.0})
    BILL["euros"] = 100.0
    stop_at(runner, 20.0)
    opened = compute.pool_clearance(runner, "run-long", [({"gpu-24gb": 1}, 6.0)], 4)
    assert compute.extend_pool(runner, opened, 6.0, 4) == 12.0
    mine = compute.open_reservations(pathlib.Path(opened["reservations"]))[opened["clearance"]["at"]]
    assert mine["euros"] == 12.0 and mine["holding"] == 12.0 and mine["high_minutes"] == 480
    assert "pass the EUR 20.00 stop" in refused(lambda: compute.extend_pool(runner, opened, 10.0, 4))
    assert "pass the EUR 20.00 stop" in refused(clear_render(runner, 9.0))  # 12 held + 9
    compute.release(opened)
    assert "has ended" in refused(lambda: compute.extend_pool(runner, opened, 1.0, 4))


def test_the_runs_heartbeat_holds_its_pool_longer_only_near_its_end_and_within_its_money():
    from score import __main__ as command
    runner = a_runner("a hall")
    ledger({"euros": 90.0})
    BILL["euros"] = 100.0
    stop_at(runner, 13.0)
    opened = compute.pool_clearance(runner, "run-beat", [({"gpu-24gb": 1}, 6.0)], 4)
    plan, extended = {"deadline": time.time() + 7200}, []
    fake = types.SimpleNamespace(current=lambda run_id: plan, holding_euros=lambda sizes, hours: 6.0,
                                 extend=lambda run_id, deadline, euros: extended.append((deadline, euros)))
    kept = command.cloud_tool, os.environ.get(compute.RUN_ID)
    command.cloud_tool, os.environ[compute.RUN_ID] = (lambda name: fake), "run-beat"
    command.POOL_TICKET[:] = [opened]
    try:
        command.extend_pool(runner)
        assert not extended  # two hours left: not yet
        plan["deadline"] = time.time() + 600
        command.extend_pool(runner)
        hours = compute.ledger().BATCH_HOURS
        assert extended == [(plan["deadline"] + hours * 3600, 12.0)], extended
        command.extend_pool(runner)  # 12 held + 6 passes the EUR 13 stop: the pool ends at its cleared end
        assert len(extended) == 1 and "pass the EUR 13.00 stop" in opened["refused"]
    finally:
        command.cloud_tool, command.POOL_TICKET[:] = kept[0], []
        os.environ.pop(compute.RUN_ID) if kept[1] is None else os.environ.update({compute.RUN_ID: kept[1]})
        compute.release(opened)


def test_a_warm_pool_held_longer_under_a_grant_holds_the_more_and_draws_its_spend_once():
    runner = a_runner("a hall")
    ledger({"euros": 90.0})
    BILL["euros"] = 100.0
    stop_at(runner, 1.0)
    grant = compute.grant_benchmark("Yes", QUESTION, 10.0, store=runner.store)["id"]
    opened = as_benchmark(grant, "run-g", lambda: compute.pool_clearance(runner, "run-g", [({"gpu-24gb": 1}, 3.0)], 4))
    as_benchmark(grant, "run-g", lambda: compute.extend_pool(runner, opened, 3.0, 4))  # 3.30 more held: 3.40 left
    assert "EUR 3.40 left" in refused(
        lambda: as_benchmark(grant, "run-g", lambda: compute.extend_pool(runner, opened, 4.0, 4)))
    billed(opened, 1.25)
    compute.release(opened)
    assert compute.grant_balance(runner.store, grant, {}) == 8.75  # both holds ended, its spend drawn
    draws = [runner.store.read(key) for key in runner.store.objects.keys(f"grants/draws/{grant}/")]
    assert [draw["euros"] for draw in draws] == [1.25], draws  # its real spend, once


def clear_render(runner, euros):
    return lambda: compute.clearance(runner, "render@hangar", euros)


def test_a_run_draws_its_stages_gemini_calls_in_its_time_under_the_callers_they_carry():
    """A body face's call is ledgered as caller body-face, a close-up's as pro; a call started and never finished
    counts at its estimate; another stage's call, or one outside the run's time, is not its own."""
    import google_spend
    kept, google_spend.LEDGER = google_spend.LEDGER, pathlib.Path(tempfile.mkdtemp()) / "google-ledger.jsonl"
    try:
        ledger({"euros": 0.0})
        lines = [("10:00:30+02:00", "finished", "body-face", 0.03), ("10:00:40+02:00", "finished", "pro", 0.14),
                 ("10:00:50+02:00", "started", "body-face", None), ("10:05:00+02:00", "finished", "body-face", 9.0)]
        google_spend.LEDGER.write_text("".join(json.dumps(
            {"time": f"2026-10-22T{at}", "call": f"c{index}", "state": state, "caller": caller, "euros": euros,
             "model": "gemini-3.1-pro-preview", "estimate": 0.05}) + "\n" for index, (at, state, caller, euros)
            in enumerate(lines)))
        hold = {"node": "body-face-earth", "key": "k", "at": "2026-10-22T08:00:00+00:00"}
        store = Store.in_folder(tempfile.mkdtemp())
        assert compute.run_spend(store, hold, "2026-10-22T08:01:00+00:00")["google"] == 0.08
        assert compute.run_spend(store, {**hold, "node": "closeup@hall"}, "2026-10-22T08:01:00+00:00")["google"] == 0.14
    finally:
        google_spend.LEDGER = kept


def test_a_run_whose_high_does_not_fit_the_balance_left_is_refused():
    runner = a_runner("a hall")
    ledger({"euros": 0.0})
    grant = compute.grant_benchmark("Yes", QUESTION, 2.0, store=runner.store)["id"]
    clear = lambda euros: lambda: compute.clearance(runner, "render@hangar", euros)  # noqa: E731
    spent = as_benchmark(grant, "run-a", clear(1.0))
    billed(spent, 1.2)  # ran over its high: it draws what it spent
    compute.release(spent)
    assert "EUR 0.80 left" in refused(lambda: as_benchmark(grant, "run-b", clear(0.75)))
    assert as_benchmark(grant, "run-b", clear(0.7))  # 0.77 fits


def test_a_scene_inventory_reading_is_cleared_under_the_owners_allowance_alone():
    """The owner, 2026-10-21: readings run without asking. Cleared with no stop line and no yes, in an agent's process
    too; its node is the reading's only, within READING_EUROS a place; a grant, when tagged, counts it."""
    runner = a_runner("a hall")
    ledger({"euros": 0.0})
    ticket = as_agent(lambda: compute.reading_clearance(runner.store, ["hall"], 0.3))
    assert ticket["node"] == compute.READING and "2026-10-21" in ticket["clearance"]["by"]
    assert runner.store.clearances(compute.READING, ticket["key"])[0]["places"] == ["hall"]
    with compute.spending(ticket):
        assert compute.require_cleared("a SAM 3 card", runner.store)["node"] == compute.READING
    assert "outside the allowance" in refused(lambda: compute.reading_clearance(runner.store, ["a"], 1.5))
    assert "outside the allowance" in refused(lambda: compute.reading_clearance(runner.store, [], 0.1))
    writing = as_agent(lambda: compute.reading_clearance(runner.store, ["hall"], 0.05, node=compute.PLAN_WRITING))
    assert "plan writing runs without asking" in writing["clearance"]["by"]
    assert "no standing allowance" in refused(
        lambda: compute.reading_clearance(runner.store, ["hall"], 0.05, node="render@hall"))
    grant = compute.grant_benchmark("Yes", QUESTION, 1.0, store=runner.store)["id"]
    clear = lambda euros: lambda: compute.reading_clearance(runner.store, ["a", "b"], euros)  # noqa: E731
    assert as_benchmark(grant, "reading-1", clear(0.6))["clearance"]["grant"] == grant
    assert "EUR 0.34 left" in refused(lambda: as_benchmark(grant, "reading-1", clear(0.6)))


def test_an_unquoted_or_too_dear_grant_clears_nothing():
    runner = a_runner("a hall")
    ledger({"euros": 0.0})
    clear = lambda: compute.clearance(runner, "render@hangar", 1.0)  # noqa: E731
    forged = {"id": "forged", "purpose": "benchmark", "euros": 10.0, "answer": "", "question": QUESTION,
              "at": graph.now(), "single_use": True}
    runner.store.write_once("grants/benchmark/forged.json", forged)
    assert "not a quoted benchmark grant" in refused(lambda: as_benchmark("forged", "run-a", clear))
    runner.store.write_once("grants/benchmark/dear.json", {**forged, "id": "dear", "answer": "Yes", "euros": 50.0})
    assert "not a quoted benchmark grant" in refused(lambda: as_benchmark("dear", "run-a", clear))
    assert runner.store.objects.keys("clearances/") == []


def test_a_grant_used_up_under_the_single_use_rule_holds_its_balance_once_restored():
    """Before 2026-10-22 a grant's first run took it whole; the owner's yes of that day, applied to one, makes each of
    its old clearances draw what it really spent and leaves the rest to spend."""
    runner = a_runner("a hall")
    ledger({"euros": 0.0})
    grant = compute.grant_benchmark("Yes", QUESTION, 20.0, store=runner.store)["id"]
    old = compute.clearance(runner, "render@hangar", 1.5)  # a test store has no stop line
    compute.release(old)
    billed(old, 0.16)
    # as the single-use rule left it: a used mark and its clearance counted
    runner.store.write_once(f"grants/used/{grant}.json", {"run": "run-a", "at": old["clearance"]["at"]})
    runner.store.write_once(f"grants/spent/{grant}/1.json",
                            {field: old["clearance"][field] for field in ("node", "key", "euros", "at")})
    clear = lambda: compute.clearance(runner, "render@hangar", 1.0)  # noqa: E731
    assert "single-use rule" in refused(lambda: as_benchmark(grant, "run-b", clear))
    assert "quotes" in refused(lambda: compute.restore_grant(grant, "", QUESTION, runner.store))
    restored = compute.restore_grant(grant, "yes", "hold the EUR 20 until it is spent?", runner.store)
    assert restored["balance"] == 19.84 and runner.store.read(f"grants/restored/{grant}.json") == restored
    assert as_benchmark(grant, "run-b", clear)



if __name__ == "__main__":
    SANDBOX["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
