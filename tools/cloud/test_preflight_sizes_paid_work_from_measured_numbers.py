"""Invariant of preflight.py: under a runner's ticket whose stage the ledger has measured (at least 3 machines that
worked its jobs, one kind of batch), a batch's cards, minutes and euros come from those measured numbers whatever
minutes the runner guessed, and the pre-flight is kept beside the store; a whole node's run is forecast from its
stage's measured runs; outside a ticket or for an unmeasured stage the runner's own rule stands (owner, 2026-10-18: a
film sized by hand ran EUR 16 on 8 cards against a EUR 0.7 estimate).

Every expected number is worked out by hand in the test from the ledger lines it writes. The break that turns each
red (applied once, seen red, reverted):

- test_a_measured_stage_picks_its_cards_whatever_the_runner_guessed: in capacity.py `machines_for`, `if flight:` ->
  `if False:` (the runner's guess sizes the batch).
- test_a_set_up_longer_than_a_job_shares_a_card: in `cards_for`, `span = max(numbers["setup_minutes"], job_minutes)`
  -> `span = job_minutes` (a card a job, each mostly setting up).
- test_the_high_forecast_takes_the_slow_jobs: in `batch`, `numbers["high_job_seconds"], numbers["setup_minutes"]` ->
  `numbers["job_seconds"], numbers["setup_minutes"]`.
- test_a_taken_or_parked_card_sets_no_numbers: in `setup_minutes`, `if not row.get("adopted")` -> `if True` (a taken
  card's zero set-up halves the median); or in `worked_machines`, drop `and not row.get("parked_idle")` (a parked
  card's idle row counts as a fifth machine).
- test_outside_a_ticket_or_unmeasured_the_runners_rule_stands: `MEASURED_MACHINES = 3` -> `MEASURED_MACHINES = 1`.
- test_a_stage_whose_batches_are_of_two_kinds_is_sized_by_neither: in `measured`, `len(kinds) != 1` -> `not kinds`.
- test_a_nodes_run_is_forecast_from_its_stages_runs: in `run_costs`, `euros + entry.get("euros", 0.0) + pooled` ->
  `euros + pooled` (a run's own euros left out).
- test_a_whole_run_is_sized_on_its_stages_median_jobs_under_the_cap: in `cards_for`, `min(wanted, math.ceil(jobs /
  slots), cap)` -> `min(wanted, math.ceil(jobs / slots))`.
- test_a_run_waits_only_while_a_claims_mark_is_fresh: in `is_waiting`, `now - mark.stat().st_mtime < fresh_seconds`
  -> `True` (a killed process's mark counts for ever).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import capacity  # noqa: E402
import ledger  # noqa: E402
import preflight  # noqa: E402

TICKET = "demo-film@garage 0123abcd"
CARD_EUROS, CARD_MINUTES = 0.16, 12.0  # each measured card: EUR 0.16 for 12 min held


def card(seconds, set_up=1.0, **more):
    """One measured card's ledger row: its jobs' seconds, 0.5 min waiting for it, `set_up` minutes setting up."""
    return {"type": "L4-1-24G", "cards": 1, "started": True, "start_wait_minutes": 0.5, "setup_minutes": set_up,
            "work_minutes": CARD_MINUTES - 1.5, "minutes": CARD_MINUTES, "euros": CARD_EUROS,
            "unit_seconds": list(seconds), **more}


def line(ticket, machines, wall=17.0, **more):
    """One ledger line of a batch paid under `ticket`."""
    return {"ticket": ticket, "started": "2026-10-18T10:00:00Z", "kind": "blender", "batch": "blender-1",
            "machines": machines, "euros": sum(row["euros"] for row in machines), "wall_minutes": wall, **more}


def films(ticket="demo-film@hub 1", seconds=600):
    """A film's batch on four cards, one 600 s job each."""
    return line(ticket, [card([seconds]) for _ in range(4)])


def under(monkeypatch, tmp_path, ticket, entries):
    """`ticket` named for this process, its store in tmp_path, the ledger holding `entries`."""
    monkeypatch.setenv(preflight.TICKET, ticket)
    monkeypatch.setenv(preflight.STORE, str(tmp_path))
    monkeypatch.setattr(ledger, "entries", lambda: entries)
    monkeypatch.delenv("SCORE_RUN_ID", raising=False)


def test_a_measured_stage_picks_its_cards_whatever_the_runner_guessed(monkeypatch, tmp_path):
    """Fault (2026-10-18): the airlock ran 175 min on 8 hand-picked cards for EUR 16 against EUR 0.7."""
    under(monkeypatch, tmp_path, TICKET, [films(), films("demo-film@lab 2")])
    # 600 s jobs against a 1.5 min set-up: a card a job, whether the runner said 0.5 or 90 minutes a job
    assert capacity.machines_for(8, 0.5, 8) == 8 and capacity.machines_for(8, 90, 8) == 8
    kept = preflight.kept(TICKET)
    assert len(kept) == 2 and kept[0]["cards"] == 8
    assert kept[0]["minutes"] == 11.5  # 1.5 set-up and one 10-minute job
    assert abs(kept[0]["euros"] - 11.5 * 8 * CARD_EUROS / CARD_MINUTES) < 1e-3
    assert (tmp_path / "forecasts" / "demo-film@garage" / "0123abcd.jsonl").exists()


def test_a_set_up_longer_than_a_job_shares_a_card(monkeypatch, tmp_path):
    under(monkeypatch, tmp_path, TICKET, [line("demo-film@hub 1", [card([60], set_up=9.5) for _ in range(4)])])
    assert capacity.machines_for(20, 30, 1) == 2  # 20 one-minute jobs over 10-minute set-ups: two cards


def test_the_high_forecast_takes_the_slow_jobs():
    numbers = preflight.measured([line("demo-film@hub 1", [card([600] * 9 + [6000]) for _ in range(3)])], "demo-film")
    flight = preflight.batch(3, numbers, cap=20)
    # 27 jobs of 600 s and 3 of 6000 s: the inclusive 90th percentile sits at 26.1 of 29, 600 + 0.1 * 5400 = 1140 s
    assert flight["cards"] == 3 and flight["minutes"] == 11.5 and flight["high_minutes"] == 1.5 + 1140 / 60
    assert abs(flight["high_euros"] - 20.5 * 3 * CARD_EUROS / CARD_MINUTES) < 1e-4


def test_a_taken_or_parked_card_sets_no_numbers():
    rows = [card([600], set_up=5.0), card([600], set_up=5.0), card([600], adopted=1.0, set_up=0.0),
            card([600], adopted=1.0, set_up=0.0), card([600], parked_idle=True)]
    numbers = preflight.measured([line("demo-film@hub 1", rows)], "demo-film")
    assert numbers["machines"] == 4 and numbers["setup_minutes"] == 5.5  # the two fresh cards' 0.5 + 5.0


def test_outside_a_ticket_or_unmeasured_the_runners_rule_stands(monkeypatch, tmp_path):
    under(monkeypatch, tmp_path, TICKET, [films()])
    monkeypatch.delenv(preflight.TICKET)
    assert capacity.machines_for(8, 0.5, 8) == 1  # the runner's rule: 4 job-minutes, less than one set-up
    under(monkeypatch, tmp_path, "terrain@world 9", [films()])  # a stage the ledger has no machines for
    assert capacity.machines_for(8, 0.5, 8) == 1 and preflight.kept("terrain@world 9") == []
    under(monkeypatch, tmp_path, TICKET, [line("demo-film@hub 1", [card([600])])])  # one machine: not measured
    assert capacity.machines_for(8, 0.5, 8) == 1


def test_a_stage_whose_batches_are_of_two_kinds_is_sized_by_neither():
    """The surfaces rows pay for turntables (blender) and models (pixal) under one stage, and the renting code is
    not told which a batch is."""
    entries = [films("surfaces@hub 1"), {**films("surfaces@hub 1"), "kind": "pixal"}]
    assert preflight.measured(entries, "surfaces") is None
    assert preflight.measured(entries[:1], "surfaces")["kind"] == "blender"


def test_a_nodes_run_is_forecast_from_its_stages_runs():
    entries = [films(f"demo-film@place{number} {number}") for number in range(5)]
    entries.append({"ticket": "demo-film@place0 0", "kind": "disk-and-address", "batch": "disk-and-address-1",
                    "machines": [], "euros": 0.02})
    run = preflight.node_run(entries, "demo-film")
    # five runs of EUR 0.64 (four cards at 0.16), place0's 0.66 with its disk: high at 3.6 of 4, 0.64 + 0.6 * 0.02
    assert run["runs"] == 5 and run["minutes"] == 17.0 and abs(run["high_euros"] - 0.652) < 1e-9
    assert run["euros"] == 0.64
    assert preflight.node_run(entries[:2], "demo-film") is None


def test_a_whole_run_is_sized_on_its_stages_median_jobs_under_the_cap():
    """Four 600 s jobs a run on a 1.5 min set-up: a card a job, never over the cap."""
    entries = [films(f"demo-film@place{number} {number}") for number in range(3)]
    assert preflight.run_jobs(entries, "demo-film") == 4
    assert preflight.run_cards(entries, "demo-film", cap=20) == 4
    assert preflight.run_cards(entries, "demo-film", cap=2) == 2
    assert preflight.run_cards(entries[:2], "demo-film", cap=20) is None


def test_a_run_waits_only_while_a_claims_mark_is_fresh(monkeypatch, tmp_path):
    """Benchmark of 2026-10-23: a rough model waiting on the pool's first card would have been stopped as a
    runaway; a mark left by a killed process must not hold the watch off for ever."""
    monkeypatch.setenv(preflight.TICKET, "rough-model@hub key1")
    monkeypatch.setenv(preflight.STORE, str(tmp_path))
    assert not preflight.is_waiting("rough-model@hub key1")
    preflight.mark_waiting()
    assert preflight.is_waiting("rough-model@hub key1") and not preflight.is_waiting("rough-model@hub key2")
    assert not preflight.is_waiting("rough-model@hub key1", fresh_seconds=0)
    preflight.unmark_waiting()
    assert not preflight.is_waiting("rough-model@hub key1")
