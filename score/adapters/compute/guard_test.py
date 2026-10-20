"""The guard at the runner's clearance, with a fake bill and fake machines: a paid job whose forecast, with what was
spent since the environment's first stop line and everything in flight, would pass the stop is refused before it starts
(one outbox line, free work going on); a job once started is never stopped as the bill nears the stop, only past
twice its forecast minutes; and an environment with no line in the framework's store is refused. No cloud.

Run: .venv/bin/python score/adapters/compute/guard_test.py   (make tests runs it in a sandbox home)
"""
import datetime
import multiprocessing
import os
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score import graph  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.adapters.compute import compute_test, guard  # noqa: E402
from score.store import AGENT_MARKERS, Store  # noqa: E402

BOOKS = compute.ledger()
MONTH = BOOKS.this_month()
BILL = compute_test.BILL  # the fake bill compute_test put in compute.cloud_bill
START = {"month": MONTH, "bill": 100.0, "ledger": 90.0, "google": 0.0}


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
    runner = compute_test.a_runner("a hall")
    stop_at(runner, 20.0)
    ledger({"euros": 90.0}, {"euros": 15.0})  # the ledger grew EUR 15 since the line
    BILL["euros"] = 110.0  # the bill only 10: it lags, the ledger counts
    job_store, dear = compute_test.a_job(runner, euros=6.0)  # 15 + 6 > 20
    refusal = compute_test.refused(dear)
    assert "EUR 15.00 spent" in refusal and "pass the EUR 20.00 stop" in refusal and job_store.keys("") == []
    assert compute_test.refused(dear) and len(outbox(runner)) == 1 and "Free work goes on" in outbox(runner)[0]
    assert compute_test.a_job(runner, euros=4.0)[1]()  # 15 + 4 fits under 20
    runner.run_node(compute_test.BRIEF, "hangar")  # free work goes on


def test_a_batch_over_its_own_stop_is_refused_one_within_it_clears_whatever_the_month_cost():
    """The owner, 2026-10-20: a batch's own stop is the only spend cap; no month's ceiling. A month at EUR 10,000
    (past the old EUR 3,000 ceiling) clears a job within the stop and refuses one over it."""
    runner = compute_test.a_runner("a hall")
    month = {"month": MONTH, "bill": 10_000.0, "ledger": 10_000.0, "google": 0.0}
    stop_at(runner, 5.0, baseline=month)
    ledger({"euros": 10_000.0})
    BILL["euros"] = 10_000.0
    assert "pass the EUR 5.00 stop" in compute_test.refused(compute_test.a_job(runner, euros=6.0)[1])
    assert compute_test.a_job(runner, euros=4.0)[1]()
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
    runner = compute_test.a_runner("a hall")
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
    runner = compute_test.a_runner("a hall")
    stop_at(runner, 10.0)
    ledger({"euros": 90.0})
    BILL["euros"] = 0.0
    ticket = compute.clearance(runner, "render@hangar", 6.0)  # in flight: EUR 6 of the 10 left
    assert "pass" in compute_test.refused(lambda: compute.clearance(runner, "render@hangar", 5.0))
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
    runner = compute_test.a_runner("a hall")
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
    home = pathlib.Path(os.environ["PROPS_HOME"]).resolve()
    assert home.is_relative_to(pathlib.Path(tempfile.gettempdir()).resolve()), "run in a sandbox home"
    world = "toy-stop"
    try:
        review_command.main(["stop", world, "5", "--reason", "films"])  # no terminal here
        raise AssertionError("written without a terminal")
    except SystemExit as refused:
        assert "own terminal" in str(refused)
    store = Store.default()
    assert guard.current(store, world) is None
    review_command.owner_at_terminal = lambda: None  # his own terminal
    try:
        as_agent(lambda: review_command.main(["stop", world, "5", "--reason", "films"]))
        raise AssertionError("an agent's process wrote a stop line")
    except SystemExit as refused:
        assert "only the owner" in str(refused)
    ledger({"euros": 40.0})
    BILL["euros"] = 50.0
    as_owner(lambda: review_command.main(["stop", world, "5", "--reason", "films"]))
    line = guard.current(store, world)
    assert line["euros"] == 5.0 and line["baseline"]["bill"] == 50.0 and line["reason"] == "films"
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "hangar.txt").write_text("a hall")
    runner = graph.Runner([compute_test.BRIEF, compute_test.RENDER], graph.Environment(world, 1, {"data": data}), store)
    runner.run_node(compute_test.BRIEF, "hangar")
    assert "pass the EUR 5.00 stop" in compute_test.refused(lambda: compute.clearance(runner, "render@hangar", 6.0))
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
    home = pathlib.Path(os.environ["PROPS_HOME"]).resolve()
    assert home.is_relative_to(pathlib.Path(tempfile.gettempdir()).resolve()), "run in a sandbox home"
    store = Store.default()
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "hangar.txt").write_text("a hall")
    runner = graph.Runner([compute_test.BRIEF, compute_test.RENDER], graph.Environment("toy-framework", 1, {"data": data}),
                          store)
    runner.run_node(compute_test.BRIEF, "hangar")
    ledger({"euros": 0.0})
    assert "has no stop line" in compute_test.refused(lambda: compute.clearance(runner, "render@hangar", 1.0))


def test_a_trials_own_store_in_the_home_is_held_to_the_worlds_stop_and_counted_in_flight():
    """Fault (2026-10-18 review): compare.py's trial store had no stop line of its own, so its paid rows (close-ups,
    pixal, likeness) skipped the stop, and their reservations sat in the trial's store where no clearance counted them."""
    trial = Store.in_folder(compute.PROPS_HOME / "trial-test/store")  # as compare.py's, a store inside the home
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "hangar.txt").write_text("a hall")
    runner = graph.Runner([compute_test.BRIEF, compute_test.RENDER], graph.Environment("toy-trial", 1, {"data": data}),
                          trial)
    runner.run_node(compute_test.BRIEF, "hangar")
    ledger({"euros": 90.0})
    BILL["euros"] = 0.0
    (Store.default().cache.parent / "reservations.json").unlink(missing_ok=True)  # earlier tests' runs, in the sandbox
    assert "has no stop line" in compute_test.refused(lambda: compute.clearance(runner, "render@hangar", 1.0))
    as_owner(lambda: guard.set_line(Store.default(), "toy-trial", 10.0, "the trial", "owner",
                                    "2026-10-18T09:00:00+00:00", START))
    ticket = compute.clearance(runner, "render@hangar", 6.0)
    assert pathlib.Path(ticket["reservations"]).parent == Store.default().cache.parent
    assert "pass the EUR 10.00 stop" in compute_test.refused(lambda: compute.clearance(runner, "render@hangar", 5.0))
    with compute.spending(ticket):
        assert compute.require_cleared("a batch")["euros"] == 6.0  # the clearance is read from the trial's store
    assert compute.clearance(runner, "render@hangar", 5.0)  # released: in flight no more


def test_a_rent_point_refuses_a_clearance_whose_run_has_ended():
    """Fault (2026-10-18 review): any earlier clearance passed a rent point, so a ticket reused after its run ended
    started paid work that no stop check and no in-flight sum saw."""
    runner = compute_test.a_runner("a hall")
    ledger({"euros": 0.0})
    ticket = compute.clearance(runner, "render@hangar", 1.0)
    with compute.spending(ticket):
        assert compute.require_cleared("a batch", runner.store)["euros"] == 1.0
    os.environ[compute.TICKET] = f"render@hangar {ticket['key']}"
    try:
        assert "has ended" in compute_test.refused(lambda: compute.require_cleared("a batch", runner.store))
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
    runner = compute_test.a_runner("a hall")
    stop_at(runner, 10.0)
    ledger({"euros": 90.0})
    BILL["euros"] = 0.0
    runner.store.write_spend_yes(compute.OVERRIDE, "repaint", {"node": compute.OVERRIDE, "key": "repaint",
                                                               "euros": 7.0, "by": "owner", "at": graph.now()})
    assert "pass the EUR 10.00 stop" in compute_test.refused(lambda: compute.clearance(runner, "render@hangar", 4.0))
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


QUESTION = "Approve one benchmark batch, P1, of at most EUR 10?"


def refused_grant(**given):
    """Why grant_benchmark refused these arguments."""
    arguments = {"answer": "Yes", "question": QUESTION, "euros": 10.0, "store": Store.in_folder(tempfile.mkdtemp()),
                 **given}
    return compute_test.refused(lambda: compute.grant_benchmark(**arguments))


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
    assert grant["single_use"] and grant["answer"] == "Yes" and grant["question"] == QUESTION and grant["euros"] == 20.0
    assert grant["expires"] > grant["at"] and grant["google_month"] is None


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


def test_a_benchmark_batch_spends_under_its_grant_once_within_its_amount():
    """The grant stands in for the stop line, for one score run, up to its euros."""
    runner = compute_test.a_runner("a hall")
    ledger({"euros": 90.0})
    BILL["euros"] = 100.0  # nothing spent since the line
    stop_at(runner, 1.0)
    grant = compute.grant_benchmark("Yes", QUESTION, 10.0, store=runner.store)["id"]
    clear = lambda euros: lambda: compute.clearance(runner, "render@hangar", euros)  # noqa: E731
    assert "pass the EUR 1.00 stop" in compute_test.refused(clear(6.0))  # not tagged: the stop line as ever
    ticket = as_benchmark(grant, "run-a", clear(6.0))
    assert ticket["clearance"]["grant"] == grant and runner.store.read(f"grants/used/{grant}.json")["run"] == "run-a"
    assert as_benchmark(grant, "run-a", clear(4.0))  # the same run, 10 of 10
    assert "would pass its EUR 10.00" in compute_test.refused(lambda: as_benchmark(grant, "run-a", clear(0.5)))
    assert "single use" in compute_test.refused(lambda: as_benchmark(grant, "run-b", clear(0.5)))
    assert "one score run" in compute_test.refused(lambda: as_benchmark(grant, None, clear(0.5)))
    assert "no benchmark grant" in compute_test.refused(lambda: as_benchmark("20991231T000000", "run-c", clear(0.5)))


def test_a_scene_inventory_reading_is_cleared_under_the_owners_allowance_alone():
    """The owner, 2026-10-21: readings run without asking. Cleared with no stop line and no yes, in an agent's process
    too; its node is the reading's only, within READING_EUROS a place; a grant, when tagged, counts it."""
    runner = compute_test.a_runner("a hall")
    ledger({"euros": 0.0})
    ticket = as_agent(lambda: compute.reading_clearance(runner.store, ["hall"], 0.3))
    assert ticket["node"] == compute.READING and "2026-10-21" in ticket["clearance"]["by"]
    assert runner.store.clearances(compute.READING, ticket["key"])[0]["places"] == ["hall"]
    with compute.spending(ticket):
        assert compute.require_cleared("a SAM 3 card", runner.store)["node"] == compute.READING
    assert "outside the allowance" in compute_test.refused(lambda: compute.reading_clearance(runner.store, ["a"], 1.5))
    assert "outside the allowance" in compute_test.refused(lambda: compute.reading_clearance(runner.store, [], 0.1))
    grant = compute.grant_benchmark("Yes", QUESTION, 1.0, store=runner.store)["id"]
    clear = lambda euros: lambda: compute.reading_clearance(runner.store, ["a", "b"], euros)  # noqa: E731
    assert as_benchmark(grant, "reading-1", clear(0.6))["clearance"]["grant"] == grant
    assert "would pass its EUR 1.00" in compute_test.refused(lambda: as_benchmark(grant, "reading-1", clear(0.6)))


def test_an_expired_or_unquoted_grant_clears_nothing():
    runner = compute_test.a_runner("a hall")
    ledger({"euros": 0.0})
    kept = compute.GRANT_HOURS
    compute.GRANT_HOURS = 0
    try:
        expired = compute.grant_benchmark("Yes", QUESTION, 10.0, store=runner.store)["id"]
    finally:
        compute.GRANT_HOURS = kept
    clear = lambda: compute.clearance(runner, "render@hangar", 1.0)  # noqa: E731
    assert "expired" in compute_test.refused(lambda: as_benchmark(expired, "run-a", clear))
    forged = {"id": "forged", "purpose": "benchmark", "euros": 10.0, "answer": "", "question": QUESTION,
              "at": graph.now(), "expires": "2999-01-01T00:00:00+00:00", "single_use": True}
    runner.store.write_once("grants/benchmark/forged.json", forged)
    assert "not a quoted benchmark grant" in compute_test.refused(lambda: as_benchmark("forged", "run-a", clear))
    runner.store.write_once("grants/benchmark/dear.json", {**forged, "id": "dear", "answer": "Yes", "euros": 50.0})
    assert "not a quoted benchmark grant" in compute_test.refused(lambda: as_benchmark("dear", "run-a", clear))
    assert runner.store.objects.keys("clearances/") == []


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
