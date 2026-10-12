"""Nothing reaches the job store without the runner's clearance: a key for a node whose prerequisites passed and stand
accepted, and room under the month's ceiling for its estimate. No typed yes is needed. No cloud: the job store is a
folder, and the ledger's month is set by each test.

Run: .venv/bin/python score/adapters/compute/compute_test.py
"""
import multiprocessing
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score import checks, contracts, graph, review  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.store import Store  # noqa: E402

BOOKS = compute.ledger()
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
    runner = graph.Runner([BRIEF, RENDER], graph.World("toy", 1, {"data": data}), store)
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


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
