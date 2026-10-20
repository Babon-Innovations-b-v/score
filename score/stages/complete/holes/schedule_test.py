"""The runner's ETA (schedule.py): rows walked in dependency order, paid rows at most `jobs` at once and their cards
under the run's cap, the longest path back through what let each row start, and a range only when every row has its
minutes. The walk's minutes are inputs of the test (no row here is said to be measured), but the one priced on the
repository's per-unit file, whose settle time is read from the paper's ledger copy.

Run: .venv/bin/python score/stages/complete/holes/schedule_test.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))

from score.adapters import compute  # noqa: E402
from score.stages.complete.holes import schedule  # noqa: E402


def row(likely, high=None, paid=True, cards=1, why=None):
    return {"paid": paid, "likely_minutes": likely, "high_minutes": likely if high is None and likely is not None
            else high, "cards": cards, "why": why}


def test_rows_wait_for_the_rows_they_read_and_the_longest_path_is_named():
    nodes = {"terrain": row(10, 20, paid=False, cards=None), "concept@a": row(5, 8), "plan@a": row(30, 40),
             "concept@b": row(1, 2)}
    edges = [("terrain", "concept@a"), ("concept@a", "plan@a"), ("terrain", "concept@b")]
    eta = schedule.schedule(nodes, edges, jobs=4, run_cap=20)
    assert (eta["likely_minutes"], eta["high_minutes"], eta["at_least_minutes"]) == (45, 68, 45), eta
    assert eta["path"] == ["terrain", "concept@a", "plan@a"] and eta["unknown"] == []


def test_at_most_jobs_paid_rows_run_at_once_and_a_free_row_never_waits_for_a_slot():
    nodes = {"first": row(10), "second": row(10), "third": row(10), "free": row(10, paid=False, cards=None)}
    eta = schedule.schedule(nodes, [], jobs=2, run_cap=20)
    assert eta["likely_minutes"] == 20 and eta["path"] == ["first", "third"], eta  # third waits for first's slot


def test_cards_held_never_pass_the_runs_cap():
    nodes = {"big": row(10, cards=15), "other": row(10, cards=10), "small": row(10, cards=5)}
    eta = schedule.schedule(nodes, [], jobs=8, run_cap=20)
    # big (15) and small (5) fill the cap; other (10) waits for one to end
    assert eta["likely_minutes"] == 20 and eta["path"][-1] == "other", eta
    assert schedule.schedule({"huge": row(10, cards=50)}, [], jobs=1, run_cap=20)["likely_minutes"] == 10


def test_a_row_without_minutes_gives_only_a_lower_bound_with_why():
    nodes = {"concept@a": row(5), "sound@a": row(None, paid=True, why="no ledger line timed it"),
             "plan@a": row(30, paid=False, cards=None)}
    eta = schedule.schedule(nodes, [("concept@a", "plan@a")], jobs=4, run_cap=20)
    assert eta["likely_minutes"] is None and eta["high_minutes"] is None and eta["at_least_minutes"] == 35
    assert eta["unknown"] == [{"node": "sound@a", "paid": True, "why": "no ledger line timed it"}]


def test_ties_go_by_the_stage_tables_order():
    nodes = {"b": row(10), "a": row(10)}
    eta = schedule.schedule(nodes, [], jobs=1, run_cap=20)
    assert eta["path"] == ["b", "a"]


def test_a_cycle_or_no_slot_is_refused():
    for nodes, edges, jobs in (({"a": row(1), "b": row(1)}, [("a", "b"), ("b", "a")], 1), ({"a": row(1)}, [], 0)):
        try:
            schedule.schedule(nodes, edges, jobs=jobs, run_cap=20)
        except ValueError:
            continue
        raise AssertionError(f"{nodes} {edges} jobs={jobs} must be refused")


def test_a_paid_row_is_timed_by_its_price_and_a_free_row_by_its_stages_makes():
    """The repository's per-unit file: settle's time from its ledger lines; no make of a free stage timed yet."""
    price = compute.run_price("settle@hangar", None, units=1)
    timed = schedule.timed_row("settle@hangar", True, price)
    assert timed["likely_minutes"] == price["likely_minutes"] is not None and timed["cards"] == 1, timed
    free = schedule.timed_row("plan@hangar", False)
    assert free["likely_minutes"] is None and "plan" in free["why"]
    unpriced = schedule.timed_row("sound@hangar", True, compute.run_price("sound@hangar", None))
    assert unpriced["likely_minutes"] is None and unpriced["why"] == "not measured yet"


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[4] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
