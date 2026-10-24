"""Checks for the capacity lists, the order a fleet takes offers in, the ledger's machine rows and the report,
without renting anything."""
import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
os.environ.pop("SCORE_RUN_ID", None)  # these checks hold one process's caps; the run-wide one has its own processes

import batch  # noqa: E402
import capacity  # noqa: E402
import ledger  # noqa: E402
import provider  # noqa: E402
import secret_store  # noqa: E402

L4, L40S, H100 = 0.013125, 0.024498, 0.047775


STOCK_WORDS = ("available", "scarce", "shortage")


def offer(per_card, stock, machine_class, zone, order=0):
    return provider.Offer(per_card, stock, f"{machine_class}-type{order}", zone,
                          per_card * max(1, provider.cards(machine_class)), machine_class, order, STOCK_WORDS[stock])


def test_every_kind_names_capability_classes():
    for kind, classes in capacity.KINDS.items():
        assert classes and all(provider.cards(machine_class) for machine_class in classes), kind
    assert provider.cards("cpu-32c-128gb") == 0 and provider.cards("gpu-80gb-x2") == 2
    assert provider.card_gb("gpu-48gb") == 48
    for wrong in ("L4-1-24G", "gpu"):
        try:
            provider.cards(wrong)
        except SystemExit as refused:
            assert "capability class" in str(refused)
        else:
            raise AssertionError(f"{wrong} was taken for a capability class")
    try:
        capacity.classes_for("nothing")
    except SystemExit as refused:
        assert "no capability classes" in str(refused)
    else:
        raise AssertionError("an unknown kind was given classes")


def test_a_run_takes_the_cheapest_card_not_out_of_stock_and_spreads_over_zones():
    offers = [offer(L4, 2, "gpu-24gb", "zone-a"), offer(L4, 2, "gpu-24gb", "zone-b"),
              offer(L4, 2, "gpu-24gb", "zone-c"), offer(H100, 2, "gpu-80gb", "zone-b")]
    assert capacity.next_offer(offers, []).machine_class == "gpu-24gb"
    rented = [{"zone": "zone-c"}]
    assert capacity.next_offer(offers, rented).zone != "zone-c"
    rented += [{"zone": "zone-a"}, {"zone": "zone-b"}]
    assert capacity.next_offer(offers, rented).machine_class == "gpu-24gb"
    # A bigger card in stock goes before a 24 GB card out of stock, never before a scarce one (owner, 2026-10-12).
    assert capacity.next_offer(offers + [offer(H100, 0, "gpu-80gb", "zone-a")], []).machine_class == "gpu-80gb"
    assert capacity.next_offer([offer(H100, 0, "gpu-80gb", "zone-a"), offer(L4, 1, "gpu-24gb", "zone-a")],
                               []).machine_class == "gpu-24gb"
    assert capacity.next_offer([offer(H100, 2, "gpu-80gb", "zone-b"), offer(L40S, 2, "gpu-48gb", "zone-b")],
                               []).machine_class == "gpu-48gb"
    # Within a class, the backend's own order.
    assert capacity.next_offer([offer(H100, 2, "gpu-80gb-x2", "zone-a", 1), offer(H100, 2, "gpu-80gb-x2", "zone-b", 0)],
                               []).order == 0
    assert capacity.next_offer([], []) is None


def test_each_kind_takes_cards_in_its_own_order():
    offers = [offer(L4, 2, "gpu-24gb", "zone-a"), offer(H100, 2, "gpu-80gb", "zone-a"),
              offer(L40S, 2, "gpu-48gb", "zone-a")]
    # The cheapest card per job first (measured, KIND_ORDER): an L4 for Pixal3D and the mesh splitting, an L40S for
    # the judge, an H100 only for the 20B picture model; bakes never take an H100.
    assert capacity.next_offer(offers, [], "pixal").machine_class == "gpu-24gb"
    assert capacity.next_offer(offers, [], "meshparts").machine_class == "gpu-24gb"
    assert capacity.next_offer(offers, [], "judge").machine_class == "gpu-48gb"
    assert capacity.next_offer(offers, [], "pictures-20b").machine_class == "gpu-80gb"
    assert capacity.next_offer(offers, [], "library").machine_class == "gpu-24gb"
    assert capacity.next_offer(offers, [], "parts").machine_class == "gpu-24gb"
    assert "gpu-80gb" not in capacity.classes_for("library") and not capacity.late_for("library")
    # Blender never takes an H100, whatever its caller's classes name; nothing else to be had is no machine.
    assert capacity.next_offer(offers[1:], [], "blender").machine_class == "gpu-48gb"
    assert capacity.next_offer(offers[1:2], [], "blender") is None


def test_a_late_class_is_taken_only_after_the_wait():
    taken = []

    def claim_from(run, account, offers, number, kind, disk_gb=batch.DISK_GB):
        taken.append(sorted({item.machine_class for item in offers}))
        return None if "gpu-80gb" not in taken[-1] else "machine"
    kept_claim, kept_sleep, kept_minutes = batch.claim_from, batch.time.sleep, capacity.LATE_MINUTES
    batch.claim_from, batch.time.sleep, capacity.LATE_MINUTES = claim_from, lambda seconds: None, 0
    capacity.LATE["library"] = ("gpu-80gb",)  # the rule, on a kind given a late class (none has one today)
    try:
        offers = [offer(L4, 2, "gpu-24gb", "zone-a"), offer(H100, 2, "gpu-80gb", "zone-a")]
        assert batch.claim(None, None, offers, 1, "library") == "machine"
        assert taken == [["gpu-24gb"], ["gpu-80gb"]]
        taken.clear()
        assert batch.claim(None, None, offers, 1, "pixal") == "machine" and taken == [["gpu-24gb", "gpu-80gb"]]
    finally:
        batch.claim_from, batch.time.sleep, capacity.LATE_MINUTES = kept_claim, kept_sleep, kept_minutes
        del capacity.LATE["library"]


def test_a_big_card_runs_several_jobs_at_once():
    assert capacity.runs_at_once("pixal", "gpu-24gb") == 3
    assert capacity.runs_at_once("pixal", "gpu-48gb") == 6
    assert capacity.runs_at_once("pixal", "gpu-80gb") == 10
    assert capacity.runs_at_once("parts", "gpu-80gb") == 1


def test_every_backend_class_is_a_capability_class():
    for machine_class in provider.cloud.CLASSES:
        provider.cards(machine_class)


def test_a_secret_comes_from_the_environment_first():
    import os
    os.environ["SCORE_SECRET_SOME_API_KEY"] = "from-the-environment"
    try:
        assert secret_store.environment_name("some-api-key") == "SCORE_SECRET_SOME_API_KEY"
        assert secret_store.secret("some-api-key") == "from-the-environment"
    finally:
        del os.environ["SCORE_SECRET_SOME_API_KEY"]


def test_hourly_machines_are_billed_by_the_started_hour():
    assert ledger.cost(1.2, L4) == 2 * L4
    assert abs(ledger.cost(61, 1.221 / 60, 60) - 2 * 1.221) < 1e-9


def test_a_machine_row_says_how_long_it_waited_and_worked():
    machine = {"type": "L40S-1-48G", "zone": "fr-par-2", "cards": 1, "price": L40S, "created": 1000.0,
               "ready": 1150.0, "deleted": 1750.0, "unit_seconds": [200.0, 210.0]}
    row = ledger.machine_row(machine)
    assert row["started"] and row["start_wait_minutes"] == 2.5 and row["work_minutes"] == 10.0
    assert row["minutes"] == 12.5 and row["euros"] == 13 * L40S and row["unit_seconds"] == [200.0, 210.0]
    silent = ledger.machine_row(dict(machine, ready=None, deleted=1300.0))
    assert not silent["started"] and silent["start_wait_minutes"] == 5.0 and silent["work_minutes"] == 0.0
    record = ledger.machines_record([machine], [silent, batch.refused_row(offer(L4, 2, "gpu-24gb", "zone-a"), "out of stock")],
                                    started=900.0)
    assert len(record["attempts"]) == 2 and record["start_wait_minutes"] == 250 / 60
    assert record["euros"] == row["euros"] + silent["euros"]


def test_the_report_groups_by_kind_and_card():
    entries = [{"started": "2026-09-30T10:00:00Z", "machines": [{"type": "L4-1-24G", "zone": "pl-waw-2",
                                                                 "minutes": 30.0, "euros": 0.4}]},
               {"started": "2026-10-08T10:00:00Z", "kind": "pixal",
                "machines": [{"type": "L40S-1-48G", "zone": "fr-par-2", "started": True, "start_wait_minutes": 2.0,
                              "work_minutes": 20.0, "minutes": 22.0, "euros": 0.54,
                              "unit_seconds": [300.0, 320.0, 340.0]}],
                "attempts": [{"type": "L4-1-24G", "zone": "pl-waw-2", "started": False, "minutes": 0.0,
                              "euros": 0.0}]}]
    table = capacity.summarise(capacity.machine_rows(entries))
    by = {(row["kind"], row["type"]): row for row in table}
    assert by[("pixal", "L4-1-24G")]["machines"] == 1 and by[("pixal", "L4-1-24G")]["failed_starts"] == 1
    l40s = by[("pixal", "L40S-1-48G")]
    assert l40s["units"] == 3 and l40s["seconds_a_unit"] == 320.0 and abs(l40s["euros_a_unit"] - 0.18) < 1e-9
    assert len(capacity.summarise(capacity.machine_rows(entries, since="2026-10-01"))) == 2
    assert {row["type"] for row in capacity.summarise(capacity.machine_rows(entries[:1]))} == {"L4-1-24G"}


def report_output(arguments, entries, report_path):
    """What `capacity.py report <arguments>` prints over `entries`, its table written to `report_path`."""
    saved = (sys.argv, capacity.ledger.entries, capacity.REPORT)
    sys.argv = ["capacity.py", "report", *arguments]
    capacity.ledger.entries, capacity.REPORT = (lambda: entries), report_path
    try:
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            capacity.main()
    finally:
        sys.argv, capacity.ledger.entries, capacity.REPORT = saved
    return printed.getvalue()


def test_the_report_prints_one_line_and_writes_its_table():
    entries = [{"started": "2026-10-08T10:00:00Z", "kind": "pixal",
                "machines": [{"type": "L40S-1-48G", "zone": "fr-par-2", "minutes": 22.0, "euros": 0.54}],
                "attempts": [{"type": "L4-1-24G", "zone": "pl-waw-2", "started": False, "euros": 0.1}]}]
    table = capacity.table_text(capacity.summarise(capacity.machine_rows(entries)))
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder) / "report.txt"
        printed = report_output([], entries, path)
        assert printed == (f"capacity report: 1 job kinds on 2 card types, 1 machines, 1 failed starts, €0.64; "
                           f"table: {path}\n"), printed
        assert path.read_text() == table and "L40S-1-48G" in table and len(table.splitlines()) == 3
        assert report_output(["--verbose"], entries, pathlib.Path(folder) / "unused.txt") == table
        assert not (pathlib.Path(folder) / "unused.txt").exists()


def test_a_batch_leaves_out_cards_the_limits_cannot_hold():
    found = [offer(L4, 1, "gpu-24gb", "zone-a"), offer(H100, 2, "gpu-80gb", "zone-b")]
    kept = batch.affordable(found, minutes=180, cards=20)
    assert [item.machine_class for item in kept] == ["gpu-24gb"]
    assert batch.affordable(found, minutes=30, cards=2) == found


# Two batch processes of one `score run`: each rents fake machines as fast as next_offer gives offers and lets some go,
# writing how many the two hold together into one file.
RENTER = """
import fcntl, json, os, pathlib, random, sys, time
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


def test_two_batches_of_one_run_hold_the_runs_cap_together():
    """Fault (2026-10-17): every --jobs node and parallel batch held run_cap machines of its own."""
    home = pathlib.Path(tempfile.mkdtemp(prefix="run-cap-"))
    held = home / "held.json"
    held.write_text("")
    environment = {**os.environ, "PROPS_HOME": str(home), "PROPS_WORK": str(home / "work"),
                   "SCORE_RUN_ID": "test-run", "SCORE_MAX_MACHINES": "all=4"}
    renters = [subprocess.Popen([sys.executable, "-c", RENTER, str(pathlib.Path(capacity.__file__).parent), str(held)],
                                env=environment) for _ in range(2)]
    assert [renter.wait(timeout=120) for renter in renters] == [0, 0]
    counts = json.loads(held.read_text())
    assert counts["most"] == 4, counts  # the cap was reached, never passed: 8 without the run-wide count


def test_a_run_counts_its_parked_machines_and_forgets_its_counts_at_its_end():
    home = pathlib.Path(tempfile.mkdtemp(prefix="run-parked-"))
    check = """
import json, os, sys
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
assert capacity.RUNS.parent == park.PARKED.parent
"""
    done = subprocess.run([sys.executable, "-c", check, str(pathlib.Path(capacity.__file__).parent)],
                          env={**os.environ, "PROPS_HOME": str(home), "PROPS_WORK": str(home / "work"),
                               "SCORE_RUN_ID": "test-run", "SCORE_MAX_MACHINES": "all=4"},
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr[-2000:]


def test_a_run_at_its_cap_says_so_once_rather_than_out_of_stock():
    """Review of C7 (2026-10-17): a batch held back by the run-wide cap logged only "no machine of ... in stock;
    asking again" (batch.claim's line), the wrong reason."""
    home = pathlib.Path(tempfile.mkdtemp(prefix="run-cap-said-"))
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
    done = subprocess.run([sys.executable, "-c", check, str(pathlib.Path(capacity.__file__).parent)],
                          env={**os.environ, "PROPS_HOME": str(home), "PROPS_WORK": str(home / "work"),
                               "SCORE_RUN_ID": "test-run", "SCORE_MAX_MACHINES": "all=2"},
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr[-2000:]
    said = [line for line in done.stderr.splitlines() if "cap" in line]
    assert len(said) == 2 and "the run holds its cap of 2 machines" in said[0], done.stderr  # once each time it fills


# A batch process of a `score run` that is given a slot (next_offer chose an offer) and then either rents nothing (the
# offer was out of stock, refused or never answered; argv[3] "fails") or rents a machine, whose watchdog it starts as
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
# Another process of the same run asking for a slot at once, and again once a slot given argv[2] seconds ago has
# lapsed with no machine behind it; it prints the two answers.
SLOT_ASKER = """
import sys, time
sys.path.insert(0, sys.argv[1])
import capacity
capacity.RESERVE_SECONDS = float(sys.argv[2])
first = capacity.reserve_run_slot(0)
time.sleep(float(sys.argv[2]) + 1.5)
print(first, capacity.reserve_run_slot(0))
"""


def slot_answers(taker):
    """What a second process of a run with a cap of one is told, at once and after the slot lapsed, while a first
    process holds the slot it was given and did `taker` with it."""
    import time

    home = pathlib.Path(tempfile.mkdtemp(prefix="run-slot-"))
    here = str(pathlib.Path(capacity.__file__).parent)
    environment = {**os.environ, "PROPS_HOME": str(home), "PROPS_WORK": str(home / "work"),
                   "SCORE_RUN_ID": "test-run", "SCORE_MAX_MACHINES": "all=1"}
    first = subprocess.Popen([sys.executable, "-c", SLOT_TAKER, here, str(home), taker], env=environment,
                             start_new_session=True)
    try:
        deadline = time.time() + 60
        while not (home / "ready").exists() and time.time() < deadline:
            time.sleep(0.05)
        asked = subprocess.run([sys.executable, "-c", SLOT_ASKER, here, "1"], env=environment, capture_output=True,
                               text=True, timeout=60)
        assert asked.returncode == 0, asked.stderr[-2000:]
        return asked.stdout.split()
    finally:
        os.killpg(first.pid, 9)


def test_a_slot_whose_rent_gave_no_machine_is_freed_for_the_runs_other_processes():
    """Review of C7 (2026-10-17): a slot counted for an offer that then gave no machine stayed counted for the rest of
    the batch, holding the run's other processes back for a machine that did not exist."""
    assert slot_answers("fails") == ["False", "True"]


def test_a_slot_whose_rent_gave_a_machine_stays_counted():
    assert slot_answers("rents") == ["False", "False"]


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, check in list(globals().items()):
        if name.startswith("test_"):
            check()
    print("capacity_test: ok")
