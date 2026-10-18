"""The guard at the runner's clearance, with a fake bill and fake machines: a paid job whose forecast, with what was
spent since the world's first stop line and everything in flight, would pass the stop is refused before it starts
(one outbox line, free work going on); a job once started is never stopped as the bill nears the stop, only past
twice its forecast minutes; and a world with no line in the framework's store is refused. No cloud.

Run: .venv/bin/python score/adapters/compute/guard_test.py   (make tests runs it in a sandbox home)
"""
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
    """The owner's stop line for the runner's world."""
    return as_owner(lambda: guard.set_line(runner.store, runner.world.name, euros, "the films", "owner", at, baseline))


def outbox(runner):
    path = runner.store.cache.parent / guard.OUTBOX
    return path.read_text().splitlines() if path.exists() else []


def test_a_job_that_would_pass_the_stop_is_refused_before_it_starts():
    """Fault (world 1, 2026-10-12 to 18): the stop was a figure in a watcher script that killed runs halfway, and it
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
    """Fault (world 1): a yes in chat and the guard line an agent typed later disagreed. His yes writes the line."""
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
    runner = graph.Runner([compute_test.BRIEF, compute_test.RENDER], graph.World(world, 1, {"data": data}), store)
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
    """In the framework's store a world must carry the owner's money figure before any paid job starts."""
    home = pathlib.Path(os.environ["PROPS_HOME"]).resolve()
    assert home.is_relative_to(pathlib.Path(tempfile.gettempdir()).resolve()), "run in a sandbox home"
    store = Store.default()
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "hangar.txt").write_text("a hall")
    runner = graph.Runner([compute_test.BRIEF, compute_test.RENDER], graph.World("toy-framework", 1, {"data": data}),
                          store)
    runner.run_node(compute_test.BRIEF, "hangar")
    ledger({"euros": 0.0})
    assert "has no stop line" in compute_test.refused(lambda: compute.clearance(runner, "render@hangar", 1.0))


if __name__ == "__main__":
    if not os.environ.get("PROPS_HOME"):
        raise SystemExit("refused: run in a sandbox home (make tests TESTS=score/adapters/compute/guard_test.py)")
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
