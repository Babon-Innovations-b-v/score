"""Nothing reaches the job store without the runner's clearance: a key for a node whose prerequisites passed and stand
accepted, and room under the month's ceiling for its estimate. No typed yes is needed. No cloud: the job store is a
folder, and the ledger's month is set by each test.

Run: .venv/bin/python score/adapters/compute/compute_test.py
"""
import json
import math
import multiprocessing
import os
import pathlib
import statistics
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score import checks, contracts, graph, review  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.store import Store  # noqa: E402

BOOKS = compute.ledger()
compute.ledger().open_books_for_tests(tempfile.mkdtemp())  # this month's books known: paid paths open
import capacity  # noqa: E402  (on the path compute.ledger() set)
import google_spend  # noqa: E402  (on the path compute.ledger() set)

google_spend.LEDGER = pathlib.Path(tempfile.mkdtemp()) / "google-ledger.jsonl"  # each test's Google month: empty
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


def test_the_month_counts_the_providers_bill_when_it_is_higher():
    """Fault (2026-10-12): Scaleway billed EUR 1,554 for October while the ledger held EUR 1,387 (disks, addresses and
    storage were never in it); the month's check read only the ledger."""
    month_spent(100.0)
    BILL["euros"] = BOOKS.MONTH_EUROS - 50.0
    try:
        assert compute.month_refusal(60.0) is not None
        assert compute.month_refusal(40.0) is None
    finally:
        BILL["euros"] = 0.0


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


def test_a_run_the_months_ceiling_has_no_room_for_is_refused():
    runner = a_runner("a hall")
    month_spent(BOOKS.MONTH_EUROS - 1)
    job_store, dearer = a_job(runner, euros=5.0)
    assert "ceiling" in refused(dearer) and job_store.keys("") == []
    assert "needs its estimate" in refused(a_job(runner, euros=None)[1])
    assert a_job(runner, euros=0.5)[1]()


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


def test_google_calls_count_in_the_month_lost_ones_at_their_estimate():
    """Fault (2026-10-12): Google billed EUR 549 for Oct 11 while its ledger held EUR 30 and the month's check read
    only the cloud ledger. The check now adds Google's month, a call started and never finished at its estimate."""
    runner = a_runner("a hall")
    month_spent(BOOKS.MONTH_EUROS - 2)
    assert a_job(runner, euros=0.5)[1]()
    for _ in range(20):  # twenty pictures asked and never answered: EUR 3 at their estimate
        google_spend.started("gemini-3-pro-image", "test")
    try:
        assert "ceiling" in refused(a_job(runner, euros=0.5)[1])
    finally:
        google_spend.LEDGER.unlink()


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


def test_a_clearance_holds_its_estimate_until_its_run_ends():
    """Fault (the coordinator, 2026-10-11): lines run side by side now, and the ledger records a batch only once it is
    done, so two lines cleared at once could both spend the month's last euros."""
    runner = a_runner("a hall")
    month_spent(BOOKS.MONTH_EUROS - 1.5)
    first = compute.clearance(runner, "render@hangar", 1.0)
    assert "EUR 1.00 cleared for runs still going" in refused(lambda: compute.clearance(runner, "render@hangar", 1.0))
    with compute.spending(first):
        pass  # the run ended: its cost is the ledger's now
    assert compute.clearance(runner, "render@hangar", 1.0)["clearance"]["euros"] == 1.0


def clear_in_a_process(runner, ready, sending):
    ready.wait()
    try:
        compute.clearance(runner, "render@hangar", 1.0)
        sending.send("cleared")
    except compute.Refused:
        sending.send("refused")


def test_lines_clearing_at_once_never_both_spend_the_months_last_euros():
    runner = a_runner("a hall")
    month_spent(BOOKS.MONTH_EUROS - 1.5)
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
        assert (price["likely_euros"], price["high_euros"], price["units"], price["runs"], price["basis"]) == (
            0.6, 1.5, 3, 40, "per unit × counted"), price
        assert compute.run_forecast("render@hangar", 9.0, outputs) == {"euros": 1.5, "minutes": None,
                                                                       "high_minutes": None, "measured": 40}
        assert compute.run_price("crops-render@hangar", 2.0, outputs)["likely_euros"] == 0.2
        unseen = compute.run_price("render@lab", 9.0, outputs)
        assert unseen["likely_euros"] is None and unseen["guess_euros"] == 9.0 and unseen["runs"] == 0
        assert compute.run_price("bake@hangar", 3.0, outputs)["basis"] == "not measured yet"
    finally:
        BOOKS.entries, compute.PER_UNIT = saved, kept


def test_a_node_not_made_yet_is_priced_per_unit_times_its_forecast_units_else_it_is_a_guess_that_says_where():
    """Units forecast before a make (holes' price) give per unit times them, a basis of their own, before the units
    an older accepted output counted (the hole's make makes what it adds, not what the last make made); a stage with no forecast rule, an `also` stage, or no units is a guess with the
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
        price = compute.run_price("render@lab", 9.0, outputs, units=4, guess_from="score/stages/x.py:12")
        assert (price["likely_euros"], price["high_euros"], price["units"], price["basis"], price["unit_source"]) == (
            0.8, 2.0, 4, "per unit × forecast", "the place's takes"), price
        again = compute.run_price("render@hangar", 9.0, outputs, units=4)  # an accept of 1 take, 4 forecast
        assert (again["units"], again["basis"], again["likely_euros"]) == (4, "per unit × forecast", 0.8), again
        assert compute.run_price("render@hangar", 9.0, outputs)["basis"] == "per unit × counted"  # no forecast given
        for node, units in (("bake@lab", 4), ("crops-render@lab", 4), ("render@lab", 0), ("render@lab", None)):
            found = compute.run_price(node, 3.0, outputs, units=units, guess_from="score/stages/x.py:12")
            assert found["likely_euros"] is None and found["guess_euros"] == 3.0, (node, units, found)
            assert found["guess_from"] == "score/stages/x.py:12" and found["basis"] == "not measured yet"
        assert "guess_from" not in compute.run_price("bake@lab", 3.0)
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
        assert unknown["likely_euros"] == 0.8 and unknown["likely_minutes"] is None
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


def test_a_stage_row_says_where_its_estimate_is_written():
    """A paid row records the line that builds it (through a helper that hands its euros on), so a guess names it;
    a row made from another by dataclasses.replace keeps the first's line unless its estimate changed."""
    def row(name, **more):
        return graph.Stage(name, "place", make_nothing, TEXT, **more)

    built = row("render", paid=True, euros=2.0)
    line = sys._getframe().f_lineno - 1
    assert built.euros_from == f"score/adapters/compute/compute_test.py:{line}", built.euros_from
    import dataclasses
    assert dataclasses.replace(built, name="render-again").euros_from == built.euros_from
    moved = dataclasses.replace(built, euros=3.0)
    assert moved.euros_from == f"score/adapters/compute/compute_test.py:{sys._getframe().f_lineno - 1}"
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


def test_the_owners_google_month_is_refused_in_an_agents_process():
    """Only the owner knows what Google billed before its ledger began again (#13): an agent's figure opens nothing."""
    kept = BOOKS.BOOKS
    BOOKS.BOOKS = pathlib.Path(tempfile.mkdtemp()) / "books.json"
    os.environ["CLAUDECODE"] = os.environ.get("CLAUDECODE", "1")
    try:
        compute.owners_google_month(400.0)
    except compute.Refused as refused:
        assert "owner" in str(refused)
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


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
