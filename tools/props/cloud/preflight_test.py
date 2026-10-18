"""Checks for the pre-flight (preflight.py) at the renting code's seam, capacity.machines_for: under a runner's ticket
whose stage the ledger has measured, the card count, minutes and euros come from the measured numbers whatever the
runner guessed, and the batch's pre-flight is kept beside the store; outside a ticket, or for an unmeasured stage, the
rule is the caller's as before. No cloud: the ledger lines are written by each test.

Run: .venv/bin/python tools/props/cloud/preflight_test.py   (make tests runs it in a sandbox home)
"""
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import capacity  # noqa: E402
import ledger  # noqa: E402
import preflight  # noqa: E402

TICKET = "demo-film@garage 0123abcd"


def card(seconds, set_up=1.0, minutes=12.0, euros=0.16, **more):
    """One measured card's ledger row: its jobs' seconds, its set-up and what it cost."""
    return {"type": "L4-1-24G", "cards": 1, "started": True, "start_wait_minutes": 0.5, "setup_minutes": set_up,
            "work_minutes": minutes - 1.5, "minutes": minutes, "euros": euros, "unit_seconds": list(seconds), **more}


def line(ticket, machines, wall=17.0, **more):
    """One ledger line of a batch paid under `ticket`."""
    return {"ticket": ticket, "started": "2026-10-18T10:00:00Z", "kind": "blender", "batch": "blender-1",
            "machines": machines, "euros": sum(row["euros"] for row in machines), "wall_minutes": wall, **more}


def films(ticket="demo-film@hub 1", seconds=600):
    """A film's batch on four cards, one 600 s job each by default."""
    return line(ticket, [card([seconds]) for _ in range(4)])


def sandboxed(ticket):
    """Name `ticket` for this process, its clearance's store in a fresh folder; that folder."""
    folder = pathlib.Path(tempfile.mkdtemp())
    os.environ[preflight.TICKET], os.environ[preflight.STORE] = ticket, str(folder)
    return folder


def test_a_measured_stage_picks_its_cards_whatever_the_runner_guessed():
    """Fault (2026-10-18): a film's card count was set by hand in its stage (2, then 8), and its forecast was a hand
    sum; the airlock ran 175 min on 8 cards for EUR 16 against an estimate of EUR 0.7."""
    entries = [films(), films("demo-film@lab 2")]
    ledger.entries = lambda: entries
    folder = sandboxed(TICKET)
    guessed_short, guessed_long = capacity.machines_for(8, 0.5, 8), capacity.machines_for(8, 90, 8)
    assert guessed_short == guessed_long == 8  # 600 s a job against 1.5 min set-up: a card a job
    kept = preflight.kept(TICKET)
    assert len(kept) == 2 and kept[0]["cards"] == 8
    assert kept[0]["minutes"] == 11.5 and abs(kept[0]["euros"] - 11.5 * 8 * (0.16 / 12)) < 1e-3
    assert (folder / "forecasts" / "demo-film@garage" / "0123abcd.jsonl").exists()


def test_set_up_longer_than_a_job_shares_a_card():
    entries = [line("demo-film@hub 1", [card([60], set_up=9.5) for _ in range(4)])]
    ledger.entries = lambda: entries
    sandboxed(TICKET)
    assert capacity.machines_for(20, 30, 1) == 2  # 20 one-minute jobs over 10-minute set-ups: two cards


def test_the_high_forecast_takes_the_slow_jobs():
    numbers = preflight.measured([line("demo-film@hub 1", [card([600] * 9 + [6000]) for _ in range(3)])], "demo-film")
    flight = preflight.batch(3, numbers, cap=20)
    assert flight["cards"] == 3 and flight["minutes"] == 11.5 and flight["high_minutes"] > flight["minutes"]
    assert flight["high_euros"] > flight["euros"]


def test_a_parked_cards_idle_line_and_a_taken_card_set_no_numbers():
    rows = [card([600], set_up=5.0), card([600], set_up=5.0), card([600], adopted=1.0, set_up=0.0),
            card([], parked_idle=True)]
    numbers = preflight.measured([line("demo-film@hub 1", rows)], "demo-film")
    assert numbers["machines"] == 3 and numbers["setup_minutes"] == 5.5


def test_outside_a_ticket_or_unmeasured_the_callers_rule_stands():
    ledger.entries = lambda: [films()]
    os.environ.pop(preflight.TICKET, None)
    assert capacity.machines_for(8, 0.5, 8) == 1
    sandboxed("terrain@world 9")  # a stage the ledger has no machines for
    assert capacity.machines_for(8, 0.5, 8) == 1 and preflight.kept("terrain@world 9") == []
    ledger.entries = lambda: [line("demo-film@hub 1", [card([600])])]  # one machine: not measured yet
    sandboxed(TICKET)
    assert capacity.machines_for(8, 0.5, 8) == 1


def test_a_stage_whose_batches_are_of_two_kinds_is_not_sized_by_either():
    """The surfaces rows pay for turntables (blender) and models (pixal) under one stage: the renting code is not
    told which a batch is, so neither kind's numbers size the other's cards."""
    entries = [films("surfaces@hub 1"), {**films("surfaces@hub 1"), "kind": "pixal"}]
    assert preflight.measured(entries, "surfaces") is None
    assert preflight.measured(entries[:1], "surfaces")["kind"] == "blender"


def test_a_nodes_run_is_forecast_from_its_stages_runs():
    entries = [films(f"demo-film@place{number} {number}") for number in range(5)]
    entries.append({"ticket": "demo-film@place0 0", "kind": "disk-and-address", "batch": "disk-and-address-1",
                    "machines": [], "euros": 0.02})
    run = preflight.node_run(entries, "demo-film")
    assert run["runs"] == 5 and run["minutes"] == 17.0 and abs(run["high_euros"] - 0.652) < 1e-9
    assert preflight.node_run(entries[:2], "demo-film") is None


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
