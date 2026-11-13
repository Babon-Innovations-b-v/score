"""Invariant of preflight.py: under a runner's ticket whose stage the ledger has measured (at least 3 machines that
worked its jobs, one kind of batch), a batch's cards, minutes and euros come from those measured numbers whatever
minutes the runner guessed, and the pre-flight is kept beside the store; a whole node's run is forecast from its
stage's measured runs; outside a ticket or for an unmeasured stage the runner's own rule stands (owner, 2026-10-18: a
film sized by hand ran EUR 16 on 8 cards against a EUR 0.7 estimate).

Every expected number is worked out by hand in the test from the ledger lines it writes. The break that turns each
red (applied once, seen red, reverted):

- sizing row "measured, guessed 0.5" and "measured, guessed 90": in capacity.py `machines_for`, `if flight:` ->
  `if False:` (the runner's guess sizes the batch).
- the run's deadlines: `deadlines` reads another run's file (the runaway watch would judge the run by deadlines it
  never declared).
- sizing row "set-up longer than a job": in `cards_for`, `span = max(numbers["setup_minutes"], job_minutes)` ->
  `span = job_minutes` (a card a job, each mostly setting up).
- ledger row "slow tail": in `batch`, `numbers["high_job_seconds"], numbers["setup_minutes"]` ->
  `numbers["job_seconds"], numbers["setup_minutes"]`.
- ledger row "taken or parked cards": in `setup_minutes`, `if not row.get("adopted")` -> `if True` (a taken card's
  zero set-up halves the median); or in `worked_machines`, drop `and not row.get("parked_idle")` (a parked card's
  idle row counts as a fifth machine).
- sizing rows "no ticket", "unmeasured stage", "one machine": `MEASURED_MACHINES = 3` -> `MEASURED_MACHINES = 1`.
- ledger row "two kinds": in `measured`, `len(kinds) != 1` -> `not kinds`.
- ledger row "five places": in `run_costs`, `euros + entry.get("euros", 0.0) + pooled` -> `euros + pooled` (a run's
  own euros left out).
- ledger row "three places": in `cards_for`, `min(wanted, math.ceil(jobs / slots), cap)` ->
  `min(wanted, math.ceil(jobs / slots))`.
- the run's waiting mark: in `is_waiting`, `now - mark.stat().st_mtime < fresh_seconds` -> `True` (a killed process's
  mark counts for ever).
"""
import pathlib
import sys

import pytest

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


def sizing(name, ticket, entries, jobs, guess, cap, want_cards, want_kept):
    """One sizing case: the ticket the runner works under (None: none), the ledger, the runner's call to
    capacity.machines_for(jobs, guessed minutes a job, set-up minutes), the cards it must get and the pre-flight it
    must keep beside the store (a dict of fields, or [] for none)."""
    return name, ticket, entries, jobs, guess, cap, want_cards, want_kept


MEASURED = [films(), films("demo-film@lab 2")]
SIZINGS = [
    # 600 s jobs against a 1.5 min set-up: a card a job, whether the runner said 0.5 or 90 minutes a job; the
    # forecast is 1.5 set-up and one 10-minute job, at the cards' measured EUR 0.16 for 12 min
    sizing("measured, guessed 0.5", TICKET, MEASURED, 8, 0.5, 8, 8,
           {"cards": 8, "minutes": 11.5, "euros": pytest.approx(11.5 * 8 * CARD_EUROS / CARD_MINUTES, abs=1e-3)}),
    sizing("measured, guessed 90", TICKET, MEASURED, 8, 90, 8, 8,
           {"cards": 8, "minutes": 11.5, "euros": pytest.approx(11.5 * 8 * CARD_EUROS / CARD_MINUTES, abs=1e-3)}),
    # 20 one-minute jobs over 10-minute set-ups (0.5 wait + 9.5): two cards, ten jobs each after the set-up
    sizing("set-up longer than a job", TICKET, [line("demo-film@hub 1", [card([60], set_up=9.5) for _ in range(4)])],
           20, 30, 1, 2, {"cards": 2, "minutes": 20.0,
                          "euros": pytest.approx(20 * 2 * CARD_EUROS / CARD_MINUTES, abs=1e-3)}),
    # the runner's rule: 4 job-minutes, less than one set-up
    sizing("no ticket", None, [films()], 8, 0.5, 8, 1, []),
    sizing("unmeasured stage", "terrain@world 9", [films()], 8, 0.5, 8, 1, []),
    sizing("one machine", TICKET, [line("demo-film@hub 1", [card([600])])], 8, 0.5, 8, 1, []),
]


def ledger_case(name, entries, stage, **want):
    """One ledger world and what preflight reads from it for `stage`: any of the measured numbers (`measured` None
    when the stage is not measured), the batch forecast for `batch_jobs` jobs under a cap of 20 cards, the node's run
    forecast (`run` None when too few runs) and the run's median jobs and cards under caps of 20 and 2."""
    return name, entries, stage, want


PLACES = [films(f"demo-film@place{number} {number}") for number in range(5)]
DISK = {"ticket": "demo-film@place0 0", "kind": "disk-and-address", "batch": "disk-and-address-1", "machines": [],
        "euros": 0.02}
LEDGERS = [
    # 27 jobs of 600 s and 3 of 6000 s: the inclusive 90th percentile sits at 26.1 of 29, 600 + 0.1 * 5400 = 1140 s
    ledger_case("slow tail", [line("demo-film@hub 1", [card([600] * 9 + [6000]) for _ in range(3)])], "demo-film",
                batch_jobs=3, batch={"cards": 3, "minutes": 11.5, "high_minutes": 1.5 + 1140 / 60,
                                     "high_euros": pytest.approx(20.5 * 3 * CARD_EUROS / CARD_MINUTES, abs=1e-4)}),
    # a taken card's zero set-up and a parked card's idle row set no numbers: the two fresh cards' 0.5 + 5.0
    ledger_case("taken or parked cards", [line("demo-film@hub 1", [
        card([600], set_up=5.0), card([600], set_up=5.0), card([600], adopted=1.0, set_up=0.0),
        card([600], adopted=1.0, set_up=0.0), card([600], parked_idle=True)])], "demo-film",
                measured={"machines": 4, "setup_minutes": 5.5}),
    # the surfaces rows pay for turntables (blender) and models (pixal) under one stage, and the renting code is not
    # told which a batch is
    ledger_case("two kinds", [films("surfaces@hub 1"), {**films("surfaces@hub 1"), "kind": "pixal"}], "surfaces",
                measured=None),
    ledger_case("one kind", [films("surfaces@hub 1")], "surfaces", measured={"kind": "blender"}),
    # five runs of EUR 0.64 (four cards at 0.16), place0's 0.66 with its disk: high at 3.6 of 4, 0.64 + 0.6 * 0.02
    ledger_case("five places", PLACES + [DISK], "demo-film",
                run={"runs": 5, "minutes": 17.0, "euros": 0.64, "high_euros": pytest.approx(0.652, abs=1e-9)}),
    # four 600 s jobs a run on a 1.5 min set-up: a card a job, never over the cap
    ledger_case("three places", PLACES[:3], "demo-film", run_jobs=4, run_cards_20=4, run_cards_2=2),
    ledger_case("two places", PLACES[:2], "demo-film", run=None, run_cards_20=None),
]


def read(entries, stage, batch_jobs):
    """Everything preflight reads from a ledger for `stage`, by the names the ledger cases use."""
    numbers = preflight.measured(entries, stage)
    return {"measured": numbers, "batch": numbers and preflight.batch(batch_jobs, numbers, cap=20),
            "run": preflight.node_run(entries, stage), "run_jobs": preflight.run_jobs(entries, stage),
            "run_cards_20": preflight.run_cards(entries, stage, cap=20),
            "run_cards_2": preflight.run_cards(entries, stage, cap=2)}


def matches(found, want):
    """Whether `found` holds `want`: None for None, a dict's named fields for a dict, else equal."""
    if isinstance(want, dict):
        return found is not None and all(found.get(key) == value for key, value in want.items())
    return found == want


def test_paid_work_is_sized_from_measured_numbers(monkeypatch, tmp_path):
    """Fault (2026-10-18): the airlock ran 175 min on 8 hand-picked cards for EUR 16 against EUR 0.7. Each sizing case
    in its own store: the runner's call gets the measured cards and keeps its pre-flight; each ledger world: the reads
    give the measured numbers and forecasts; then a run under the ticket declares its deadlines and its waiting mark
    (benchmark of 2026-10-23: a rough model waiting on the pool's first card would have been stopped as a runaway; a
    mark left by a killed process must not hold the watch off for ever)."""
    for name, ticket, entries, jobs, guess, cap, want_cards, want_kept in SIZINGS:
        store = tmp_path / name.replace(" ", "-").replace(",", "")
        under(monkeypatch, store, ticket or TICKET, entries)
        if ticket is None:
            monkeypatch.delenv(preflight.TICKET)
            assert preflight.declare_deadline(1_700_000_000) is None, name
        assert capacity.machines_for(jobs, guess, cap) == want_cards, name
        kept = preflight.kept(ticket or TICKET)
        if want_kept:
            assert len(kept) == 1 and matches(kept[0], want_kept), (name, kept)
            node, key = ticket.split()
            assert (store / "forecasts" / node / f"{key}.jsonl").exists(), name
        else:
            assert kept == [], (name, kept)

    for name, entries, stage, want in LEDGERS:
        found = read(entries, stage, want.get("batch_jobs", 1))
        for field, expected in want.items():
            assert field == "batch_jobs" or matches(found[field], expected), (name, field, found[field])

    under(monkeypatch, tmp_path, TICKET, MEASURED)
    preflight.declare_deadline(1_700_000_000.4)  # a run's paid work declares its deadlines for its runaway watch
    preflight.declare_deadline(1_700_003_600)
    assert preflight.deadlines(TICKET) == [1_700_000_000, 1_700_003_600] and preflight.deadlines("x@y 1") == []
    assert not preflight.is_waiting(TICKET)
    preflight.mark_waiting()
    assert preflight.is_waiting(TICKET) and not preflight.is_waiting("demo-film@garage other")
    assert not preflight.is_waiting(TICKET, fresh_seconds=0)
    preflight.unmark_waiting()
    assert not preflight.is_waiting(TICKET)
