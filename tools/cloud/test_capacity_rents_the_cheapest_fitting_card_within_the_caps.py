"""Invariant of capacity.py (with the provider interface it reads): every job kind runs on capability classes only;
the next machine is the kind's cheapest card per job that fits, a card out of stock last and a never-class never,
spread over the zones; a batch gets enough machines to end in about its set-up and one job, never more than its jobs
nor than the caps (each class's quota, the run's cap, SCORE_MAX_MACHINES); all the processes of one `score run` hold
the run's cap together, parked machines counted, a slot whose rent gave no machine freed; and the capacity report
groups the ledger's machines by kind and card in one printed line (owner, 2026-10-12: the cheapest card that fits;
2026-10-17: every node held a cap of its own).

The expected cards and counts are worked out by hand from the offers and the rule; the run-cap checks run real
processes against one shared count. The break that turns each red (applied once, seen red, reverted):

- test_every_kind_runs_on_capability_classes_only: in `classes_for`, the unknown kind's `raise SystemExit(...)` ->
  `return ()`; or in provider.py `cards`, the last `raise SystemExit(...)` -> `return 0`.
- test_the_next_machine_is_the_cheapest_fitting_card_in_stock_spread_over_the_zones: in `next_offer`'s key, drop
  `offer.stock_word == "shortage", `; or `in_zone[offer.zone]` -> `0`; or `and offer.machine_class not in
  NEVER.get(kind, ())` -> ``.
- test_a_late_class_is_taken_only_after_the_wait: in batch.py `claim_round`, `first = [offer for offer in offers if
  offer.machine_class not in late]` -> `first = list(offers)`.
- test_a_big_card_runs_several_jobs_of_a_measured_kind_at_once: in `runs_at_once`, `// 24` -> `// 48`.
- test_a_secret_comes_from_the_environment_before_the_backend: in secret_store.py `secret`, `if
  os.environ.get(environment_name(name)):` -> `if False:`.
- test_a_batch_ends_in_about_its_set_up_and_one_job: in `machines_for`, `span = max(setup_minutes, unit_minutes)` ->
  `span = unit_minutes`.
- test_the_caps_follow_the_quotas_and_the_environment: in `caps`, `found[name] = int(number)` -> `pass`.
- test_a_machine_row_says_how_long_it_waited_worked_and_cost: in ledger.py `machine_row`, `((ready or ended) -
  began) / 60` -> `(ended - began) / 60`.
- test_the_report_groups_by_kind_and_card_and_prints_one_line: in `summarise`, `"failed_starts": len(group) -
  len(ran)` -> `"failed_starts": 0`.
- test_two_batches_of_one_run_hold_the_runs_cap_together: in `reserve_run_slot`, `room = elsewhere + live <
  run_cap()` -> `room = live < run_cap()`.
- test_a_run_counts_its_parked_machines_and_forgets_its_counts_at_its_end: in `held_elsewhere`, `held +=
  sum(json.loads(` -> `held += 0 * sum(json.loads(`.
- test_a_run_at_its_cap_says_so_once_each_time_it_fills: in `say_at_cap`, `if at_cap and not AT_CAP:` -> `if
  at_cap:`.
- test_a_slot_whose_rent_gave_no_machine_is_freed_and_one_that_gave_a_machine_stays_counted: in
  `renting_elsewhere`, `if time.time() - count["at"] < RESERVE_SECONDS:` -> `if True:`; or in `held_elsewhere`,
  `sum(parent != os.getpid() for parent in watchdogs.values())` -> `0`.
"""
import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import batch  # noqa: E402
import capacity  # noqa: E402
import ledger  # noqa: E402
import provider  # noqa: E402
import secret_store  # noqa: E402

HERE = str(pathlib.Path(capacity.__file__).parent)
L4, L40S, H100 = 0.013125, 0.024498, 0.047775
STOCK_WORDS = ("available", "scarce", "shortage")


@pytest.fixture(autouse=True)
def one_process(monkeypatch):
    """These checks hold one process's caps; the run-wide ones start processes of their own."""
    monkeypatch.delenv("SCORE_RUN_ID", raising=False)
    monkeypatch.delenv("SCORE_MAX_MACHINES", raising=False)
    monkeypatch.delenv("SCORE_SPEND_TICKET", raising=False)


def offer(per_card, stock, machine_class, zone, order=0):
    return provider.Offer(per_card, stock, f"{machine_class}-type{order}", zone,
                          per_card * max(1, provider.cards(machine_class)), machine_class, order, STOCK_WORDS[stock])


def refused(call, *arguments):
    """The SystemExit message of a call that must refuse."""
    try:
        call(*arguments)
    except SystemExit as refusal:
        return str(refusal)
    raise AssertionError(f"{call.__name__}{arguments} was taken")


def test_every_kind_runs_on_capability_classes_only():
    for kind, classes in capacity.KINDS.items():
        assert classes and all(provider.cards(machine_class) for machine_class in classes), kind
    for machine_class in provider.cloud.CLASSES:
        provider.cards(machine_class)  # every backend class reads as one
    assert provider.cards("cpu-32c-128gb") == 0 and provider.cards("gpu-80gb-x2") == 2
    assert provider.card_gb("gpu-48gb") == 48
    for wrong in ("L4-1-24G", "gpu"):  # a provider's type is never a class
        assert "capability class" in refused(provider.cards, wrong)
    assert "no capability classes" in refused(capacity.classes_for, "nothing")


def test_the_next_machine_is_the_cheapest_fitting_card_in_stock_spread_over_the_zones():
    offers = [offer(L4, 2, "gpu-24gb", "zone-a"), offer(L4, 2, "gpu-24gb", "zone-b"),
              offer(L4, 2, "gpu-24gb", "zone-c"), offer(H100, 2, "gpu-80gb", "zone-b")]
    assert capacity.next_offer(offers, []).machine_class == "gpu-24gb"
    assert capacity.next_offer(offers, [{"zone": "zone-c"}]).zone != "zone-c"
    assert capacity.next_offer(offers, [{"zone": "zone-c"}, {"zone": "zone-a"}]).zone == "zone-b"
    # a bigger card in stock goes before a 24 GB card out of stock, never before a scarce one (owner, 2026-10-12)
    assert capacity.next_offer(offers + [offer(H100, 0, "gpu-80gb", "zone-a")], []).machine_class == "gpu-80gb"
    assert capacity.next_offer([offer(H100, 0, "gpu-80gb", "zone-a"), offer(L4, 1, "gpu-24gb", "zone-a")],
                               []).machine_class == "gpu-24gb"
    # within a class, the backend's own order; none offered, no machine
    assert capacity.next_offer([offer(H100, 2, "gpu-80gb-x2", "zone-a", 1), offer(H100, 2, "gpu-80gb-x2", "zone-b", 0)],
                               []).order == 0
    assert capacity.next_offer([], []) is None
    # each kind's cheapest card per job: an L4 for Pixal3D, the mesh splitting and bakes, an L40S for the judge, an
    # H100 for the 20B picture model; Blender never an H100, and nothing else to be had is no machine
    cards = [offer(L4, 2, "gpu-24gb", "zone-a"), offer(H100, 2, "gpu-80gb", "zone-a"),
             offer(L40S, 2, "gpu-48gb", "zone-a")]
    for kind, wanted in (("pixal", "gpu-24gb"), ("meshparts", "gpu-24gb"), ("judge", "gpu-48gb"),
                         ("pictures-20b", "gpu-80gb"), ("library", "gpu-24gb"), ("parts", "gpu-24gb")):
        assert capacity.next_offer(cards, [], kind).machine_class == wanted, kind
    assert capacity.next_offer(cards[1:], [], "blender").machine_class == "gpu-48gb"
    assert capacity.next_offer(cards[1:2], [], "blender") is None


def test_a_late_class_is_taken_only_after_the_wait(monkeypatch):
    taken = []

    def claim_from(run, account, offers, number, kind, disk_gb=batch.DISK_GB):
        taken.append(sorted({item.machine_class for item in offers}))
        return None if "gpu-80gb" not in taken[-1] else "machine"
    monkeypatch.setattr(batch, "claim_from", claim_from)
    monkeypatch.setattr(batch.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(batch, "say", lambda line: None)
    monkeypatch.setattr(capacity, "LATE_MINUTES", 0)
    monkeypatch.setitem(capacity.LATE, "library", ("gpu-80gb",))  # the rule, on a kind given a late class
    offers = [offer(L4, 2, "gpu-24gb", "zone-a"), offer(H100, 2, "gpu-80gb", "zone-a")]
    assert batch.claim_round(None, None, offers, 1, "library") == "machine"
    assert taken == [["gpu-24gb"], ["gpu-80gb"]]
    taken.clear()
    assert batch.claim_round(None, None, offers, 1, "pixal") == "machine" and taken == [["gpu-24gb", "gpu-80gb"]]


def test_a_big_card_runs_several_jobs_of_a_measured_kind_at_once():
    """Three Pixal3D runs for every 24 GB of card (measured on an L4: six at once ran out of memory)."""
    assert [capacity.runs_at_once("pixal", name) for name in ("gpu-24gb", "gpu-48gb", "gpu-80gb")] == [3, 6, 10]
    assert capacity.runs_at_once("parts", "gpu-80gb") == 1  # an unmeasured kind: one


def test_a_secret_comes_from_the_environment_before_the_backend(monkeypatch):
    monkeypatch.setattr(provider.cloud, "secret", lambda name: "from-the-backend")
    monkeypatch.setenv("SCORE_SECRET_SOME_API_KEY", "from-the-environment")
    assert secret_store.secret("some-api-key") == "from-the-environment"
    monkeypatch.delenv("SCORE_SECRET_SOME_API_KEY")
    assert secret_store.secret("some-api-key") == "from-the-backend"


def test_a_batch_ends_in_about_its_set_up_and_one_job():
    assert capacity.machines_for(1, 10, 8) == 1
    assert capacity.machines_for(30, 0.15, 8) == 1  # 30 pictures of 9 s: less work than one set-up
    assert capacity.machines_for(0, 1, 8) == 1
    assert capacity.machines_for(10, 15, 8) == 10  # ten 15-minute Blender jobs: one a machine
    # 60 close-ups of 82 s on a 10 min set-up: 82 min of work over 10-minute spans, 9 machines
    assert capacity.machines_for(60, 82 / 60, 10) == 9
    assert capacity.spread_minutes(60, 82 / 60, 10, 9) == 10 + 7 * 82 / 60  # 7 rounds of the 60 over 9
    assert capacity.machines_for(100, 5, 5, slots=10) == 10  # ten at once: a tenth as many
    assert capacity.machines_for(3, 60, 8) == 3  # never more machines than jobs


def test_the_caps_follow_the_quotas_and_the_environment(monkeypatch):
    quotas = provider.cloud.QUOTAS
    assert capacity.max_machines("gpu-80gb") == quotas["gpu-80gb"]
    assert capacity.max_machines("cpu-32c-128gb") == capacity.OTHER_MACHINES
    # #20: a run holds as many machines as its largest class's quota, at least RUN_MACHINES
    assert capacity.run_cap() == max(capacity.RUN_MACHINES, *quotas.values())
    assert capacity.machines_for(500, 60, 8) == capacity.run_cap()
    monkeypatch.setenv("SCORE_MAX_MACHINES", "gpu-80gb=2, all=3")
    assert capacity.max_machines("gpu-80gb") == 2 and capacity.run_cap() == 3
    assert capacity.machines_for(500, 60, 8) == 3
    offers = [offer(H100, 0, "gpu-80gb", "zone-a"), offer(L40S, 1, "gpu-48gb", "zone-b")]
    two = [{"zone": "zone-a", "class": "gpu-80gb"}] * 2
    assert capacity.next_offer(offers, two, "judge").machine_class == "gpu-48gb"  # the H100s at their cap of 2
    assert capacity.next_offer(offers, two + [{"zone": "zone-b", "class": "gpu-48gb"}], "judge") is None  # all 3
    monkeypatch.setenv("SCORE_MAX_MACHINES", "gpu-80gb")
    assert "SCORE_MAX_MACHINES" in refused(capacity.caps)


def test_a_machine_row_says_how_long_it_waited_worked_and_cost():
    machine = {"type": "L40S-1-48G", "zone": "fr-par-2", "cards": 1, "price": L40S, "created": 1000.0,
               "ready": 1150.0, "deleted": 1750.0, "unit_seconds": [200.0, 210.0]}
    row = ledger.machine_row(machine)
    # 150 s to answer, 600 s of work, 12.5 min in all billed as 13 started minutes
    assert row["started"] and row["start_wait_minutes"] == 2.5 and row["work_minutes"] == 10.0
    assert row["minutes"] == 12.5 and row["euros"] == 13 * L40S and row["unit_seconds"] == [200.0, 210.0]
    silent = ledger.machine_row(dict(machine, ready=None, deleted=1300.0))  # never answered: 5 min billed
    assert not silent["started"] and silent["start_wait_minutes"] == 5.0 and silent["work_minutes"] == 0.0
    assert silent["euros"] == 5 * L40S
    assert abs(ledger.cost(61, 1.221 / 60, 60) - 2 * 1.221) < 1e-9  # an hourly machine: by the started hour
    record = ledger.machines_record([machine], [silent, batch.refused_row(offer(L4, 2, "gpu-24gb", "zone-a"),
                                                                         "out of stock")], started=900.0)
    assert len(record["attempts"]) == 2 and record["start_wait_minutes"] == 250 / 60  # from 900 to its 1150
    assert abs(record["euros"] - 18 * L40S) < 1e-12


def report_output(arguments, entries, report_path, monkeypatch):
    """What `capacity.py report <arguments>` prints over `entries`, its table written to `report_path`."""
    monkeypatch.setattr(sys, "argv", ["capacity.py", "report", *arguments])
    monkeypatch.setattr(capacity.ledger, "entries", lambda: entries)
    monkeypatch.setattr(capacity, "REPORT", report_path)
    with contextlib.redirect_stdout(io.StringIO()) as printed:
        capacity.main()
    return printed.getvalue()


def test_the_report_groups_by_kind_and_card_and_prints_one_line(tmp_path, monkeypatch):
    entries = [{"started": "2026-09-30T10:00:00Z", "machines": [{"type": "L4-1-24G", "zone": "pl-waw-2",
                                                                 "minutes": 30.0, "euros": 0.4}]},
               {"started": "2026-10-08T10:00:00Z", "kind": "pixal",
                "machines": [{"type": "L40S-1-48G", "zone": "fr-par-2", "started": True, "start_wait_minutes": 2.0,
                              "work_minutes": 20.0, "minutes": 22.0, "euros": 0.54,
                              "unit_seconds": [300.0, 320.0, 340.0]}],
                "attempts": [{"type": "L4-1-24G", "zone": "pl-waw-2", "started": False, "minutes": 0.0,
                              "euros": 0.1}]}]
    by = {(row["kind"], row["type"]): row for row in capacity.summarise(capacity.machine_rows(entries))}
    # the September line has no kind: Pixal3D, the only kind then; its L4 and October's failed L4 start group
    assert by[("pixal", "L4-1-24G")]["machines"] == 1 and by[("pixal", "L4-1-24G")]["failed_starts"] == 1
    l40s = by[("pixal", "L40S-1-48G")]
    assert l40s["units"] == 3 and l40s["seconds_a_unit"] == 320.0 and abs(l40s["euros_a_unit"] - 0.18) < 1e-9
    assert len(capacity.summarise(capacity.machine_rows(entries, since="2026-10-01"))) == 2
    path = tmp_path / "report.txt"
    printed = report_output([], entries[1:], path, monkeypatch)
    assert printed == ("capacity report: 1 job kinds on 2 card types, 1 machines, 1 failed starts, €0.64; "
                       f"table: {path}\n")
    assert len(path.read_text().splitlines()) == 3  # a header and a line a card type
    assert report_output(["--verbose"], entries[1:], tmp_path / "unused.txt", monkeypatch) == path.read_text()
    assert not (tmp_path / "unused.txt").exists()


def in_a_run(home, cap, run="test-run"):
    """The environment of a `score run` process with a cap of `cap` machines, its home `home`."""
    return {**os.environ, "PROPS_HOME": str(home), "PROPS_WORK": str(home / "work"), "SCORE_RUN_ID": run,
            "SCORE_MAX_MACHINES": f"all={cap}"}


# A batch process of a `score run`: it rents fake machines as fast as next_offer gives offers and lets some go,
# writing how many the run's processes hold together into one file.
RENTER = """
import fcntl, json, pathlib, random, sys, time
sys.path.insert(0, sys.argv[1])
import capacity, provider
held = pathlib.Path(sys.argv[2])
offers = [provider.Offer(0.01, 2, "gpu-24gb-type0", "zone-a", 0.01, "gpu-24gb", 0, "available")]

def together(change):
    with held.open("r+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        counts = json.loads(handle.read() or '{"now": 0, "most": 0}')
        counts["now"] += change
        counts["most"] = max(counts["most"], counts["now"])
        handle.seek(0), handle.truncate(), handle.write(json.dumps(counts))

machines, until = [], time.time() + 4
while time.time() < until:
    if capacity.next_offer(offers, machines, "pixal") is not None:
        machines.append({"zone": "zone-a", "class": "gpu-24gb", "deleted": None})
        together(1)
    live = [machine for machine in machines if not machine["deleted"]]
    if live and random.random() < 0.3:
        live[0]["deleted"] = time.time()
        together(-1)  # off the count first: the process's count lets it go at its next ask
    time.sleep(random.random() * 0.02)
"""


def test_two_batches_of_one_run_hold_the_runs_cap_together(tmp_path):
    """Fault (2026-10-17): every --jobs node and parallel batch held run_cap machines of its own."""
    held = tmp_path / "held.json"
    held.write_text("")
    renters = [subprocess.Popen([sys.executable, "-c", RENTER, HERE, str(held)], env=in_a_run(tmp_path, 4))
               for _ in range(2)]
    assert [renter.wait(timeout=60) for renter in renters] == [0, 0]
    assert json.loads(held.read_text())["most"] == 4  # reached, never passed: 8 with a cap each


def test_a_run_counts_its_parked_machines_and_forgets_its_counts_at_its_end(tmp_path):
    check = """
import json, sys
sys.path.insert(0, sys.argv[1])
import capacity, park
park.PARKED.mkdir(parents=True, exist_ok=True)
for number, run in enumerate(("test-run", "test-run", "another-run")):
    (park.PARKED / f"m{number}.json").write_text(json.dumps({"id": f"m{number}", "run": run}))
assert capacity.reserve_run_slot(1)          # 2 parked + 1 held < 4: counted, 2 held
assert not capacity.reserve_run_slot(2)      # 2 parked + 2 held: the cap
assert (capacity.RUNS / "test-run").exists()
capacity.forget_run("test-run")
assert not (capacity.RUNS / "test-run").exists()
"""
    done = subprocess.run([sys.executable, "-c", check, HERE], env=in_a_run(tmp_path, 4), capture_output=True,
                          text=True)
    assert done.returncode == 0, done.stderr[-2000:]


def test_a_run_at_its_cap_says_so_once_each_time_it_fills(tmp_path):
    """Review of C7 (2026-10-17): a batch held back by the run's cap said only "no machine ... in stock"."""
    check = """
import sys
sys.path.insert(0, sys.argv[1])
import capacity
assert capacity.reserve_run_slot(1)
assert not capacity.reserve_run_slot(2)
assert not capacity.reserve_run_slot(2)
assert capacity.reserve_run_slot(0)
assert not capacity.reserve_run_slot(2)
"""
    done = subprocess.run([sys.executable, "-c", check, HERE], env=in_a_run(tmp_path, 2), capture_output=True,
                          text=True)
    assert done.returncode == 0, done.stderr[-2000:]
    said = [line for line in done.stderr.splitlines() if "cap" in line]
    assert len(said) == 2 and "the run holds its cap of 2 machines" in said[0], done.stderr


# A process of a run given a slot that rents nothing with it ("fails") or rents a machine whose watchdog it starts as
# batch.rent does ("rents"); it says "ready" and lives on.
SLOT_TAKER = """
import pathlib, subprocess, sys, time
sys.path.insert(0, sys.argv[1])
import capacity
folder = pathlib.Path(sys.argv[2])
assert capacity.reserve_run_slot(0)
if sys.argv[3] == "rents":
    subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", str(pathlib.Path(sys.argv[1]) / "batch.py"),
                      "--watchdog", "machine-1", "zone-a", "0"])
(folder / "ready").write_text("ready")
time.sleep(60)
"""
# Another process of the run asking for a slot at once, and again once a slot given 1 s ago has lapsed.
SLOT_ASKER = """
import sys, time
sys.path.insert(0, sys.argv[1])
import capacity
capacity.RESERVE_SECONDS = 1.0
first = capacity.reserve_run_slot(0)
time.sleep(2.5)
print(first, capacity.reserve_run_slot(0))
"""


def slot_answers(home, taker):
    """What a second process of a run with a cap of one is told, at once and after the slot lapsed, while a first
    holds the slot it was given and did `taker` with it."""
    home.mkdir()
    first = subprocess.Popen([sys.executable, "-c", SLOT_TAKER, HERE, str(home), taker], env=in_a_run(home, 1),
                             start_new_session=True)
    try:
        deadline = time.time() + 60
        while not (home / "ready").exists() and time.time() < deadline:
            time.sleep(0.05)
        asked = subprocess.run([sys.executable, "-c", SLOT_ASKER, HERE], env=in_a_run(home, 1), capture_output=True,
                               text=True, timeout=60)
        assert asked.returncode == 0, asked.stderr[-2000:]
        return asked.stdout.split()
    finally:
        os.killpg(first.pid, 9)


def test_a_slot_whose_rent_gave_no_machine_is_freed_and_one_that_gave_a_machine_stays_counted(tmp_path):
    """Review of C7 (2026-10-17): a slot counted for an offer that gave no machine held the run's other processes
    back for a machine that did not exist."""
    assert slot_answers(tmp_path / "fails", "fails") == ["False", "True"]
    assert slot_answers(tmp_path / "rents", "rents") == ["False", "False"]
